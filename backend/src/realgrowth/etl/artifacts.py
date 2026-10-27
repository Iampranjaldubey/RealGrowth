"""Load offline model artefacts into the warehouse.

Training happens offline in the ``realgrowth_ml`` package (``ml/``), which
needs numpy, pandas and LightGBM. Serving must not: the API host builds its
warehouse with the standard library only. The two meet at a plain-file
contract in ``data/models/``::

    data/models/inflation/model_card.json   models, champion, metrics, features
    data/models/inflation/forecasts.csv     forward forecasts with intervals
    data/models/inflation/backtest.csv      out-of-sample backtest predictions
    data/models/inflation/contributions.csv TreeSHAP attributions per forecast
    data/models/anomaly/scores.csv          imputation-artefact scores

This is the "batch prediction" serving pattern: predictions are precomputed
and versioned alongside the data that produced them, so a served number can
always be traced back to a model card and a data snapshot.

The IMF's own WEO projections are loaded as an ``external`` model, so the API
and UI can show the benchmark next to our forecast.
"""

from __future__ import annotations

import csv
import json
import logging
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from realgrowth.etl.sources import IMF_FORECAST_SERIES, INFLATION_RATE

logger = logging.getLogger(__name__)

IMF_MODEL_ID = "imf_weo"

FORECAST_COLUMNS = (
    "model_id",
    "iso3",
    "origin_year",
    "target_year",
    "horizon",
    "point",
    "lower_80",
    "upper_80",
    "lower_95",
    "upper_95",
)
BACKTEST_COLUMNS = (
    "model_id",
    "iso3",
    "origin_year",
    "target_year",
    "horizon",
    "actual",
    "point",
    "lower_80",
    "upper_80",
)
CONTRIBUTION_COLUMNS = (
    "model_id",
    "iso3",
    "target_year",
    "feature",
    "feature_value",
    "contribution",
)
ANOMALY_COLUMNS = ("indicator_id", "iso3", "year", "score", "is_flagged")


@dataclass
class ArtifactSummary:
    """What was loaded, for the ETL log and metadata table."""

    models: int = 0
    forecasts: int = 0
    backtest: int = 0
    contributions: int = 0
    anomaly_scores: int = 0
    skipped_unknown_country: int = 0
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "models": self.models,
            "forecasts": self.forecasts,
            "backtest": self.backtest,
            "contributions": self.contributions,
            "anomaly_scores": self.anomaly_scores,
            "skipped_unknown_country": self.skipped_unknown_country,
            "notes": self.notes,
        }


def _optional_float(text: str | None) -> float | None:
    if text is None or text.strip() == "":
        return None
    return float(text)


def _read_rows(path: Path, columns: tuple[str, ...]) -> Iterator[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = set(columns) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        yield from reader


def _known_countries(connection: sqlite3.Connection) -> set[str]:
    return {str(row[0]) for row in connection.execute("SELECT iso3 FROM countries")}


def load_imf_benchmark(
    connection: sqlite3.Connection, api_dir: Path, summary: ArtifactSummary
) -> None:
    """Register the IMF WEO projections as an external forecasting model."""
    path = api_dir / f"{IMF_FORECAST_SERIES}.csv"
    if not path.is_file():
        summary.notes.append(f"{path.name} not found; IMF benchmark not loaded")
        return
    known = _known_countries(connection)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [(r["iso3"], int(r["year"]), float(r["value"])) for r in csv.DictReader(handle)]
    if not rows:
        return
    first_projection = min(year for _, year, _ in rows)
    origin = first_projection - 1
    connection.execute(
        """
        INSERT INTO models (id, indicator_id, name, kind, is_champion, description, card_json)
        VALUES (?, ?, ?, 'external', 0, ?, ?)
        """,
        (
            IMF_MODEL_ID,
            INFLATION_RATE,
            "IMF World Economic Outlook",
            "The IMF's published inflation projections (latest WEO vintage), shown as "
            "an external benchmark. Produced by IMF country desks, not by this project.",
            json.dumps({"vintage_first_projection_year": first_projection}),
        ),
    )
    summary.models += 1
    payload = []
    for iso3, year, value in rows:
        if iso3 not in known:
            summary.skipped_unknown_country += 1
            continue
        payload.append((IMF_MODEL_ID, iso3, origin, year, year - origin, value))
    connection.executemany(
        """
        INSERT INTO forecasts (model_id, iso3, origin_year, target_year, horizon, point)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        payload,
    )
    summary.forecasts += len(payload)


def load_forecasting_task(
    connection: sqlite3.Connection, task_dir: Path, summary: ArtifactSummary
) -> None:
    """Load one task directory written by ``python -m realgrowth_ml train``."""
    card_path = task_dir / "model_card.json"
    if not card_path.is_file():
        summary.notes.append(f"{task_dir.name}: no model_card.json; skipped")
        return
    card: dict[str, Any] = json.loads(card_path.read_text(encoding="utf-8"))
    indicator_id = str(card["indicator_id"])
    champion = card.get("champion")
    known = _known_countries(connection)

    for model in card["models"]:
        connection.execute(
            """
            INSERT INTO models (id, indicator_id, name, kind, is_champion, description, card_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                model["id"],
                indicator_id,
                model["name"],
                model["kind"],
                int(model["id"] == champion),
                model["description"],
                json.dumps(model.get("card", {})),
            ),
        )
        summary.models += 1
    connection.execute(
        "INSERT INTO etl_metadata (key, value) VALUES (?, ?)",
        (f"model_card:{task_dir.name}", json.dumps(card)),
    )

    forecasts = task_dir / "forecasts.csv"
    if forecasts.is_file():
        batch = []
        for r in _read_rows(forecasts, FORECAST_COLUMNS):
            if r["iso3"] not in known:
                summary.skipped_unknown_country += 1
                continue
            batch.append(
                (
                    r["model_id"],
                    r["iso3"],
                    int(r["origin_year"]),
                    int(r["target_year"]),
                    int(r["horizon"]),
                    float(r["point"]),
                    _optional_float(r["lower_80"]),
                    _optional_float(r["upper_80"]),
                    _optional_float(r["lower_95"]),
                    _optional_float(r["upper_95"]),
                )
            )
        connection.executemany(
            f"INSERT INTO forecasts ({', '.join(FORECAST_COLUMNS)}) "
            f"VALUES ({', '.join('?' * len(FORECAST_COLUMNS))})",
            batch,
        )
        summary.forecasts += len(batch)

    backtest = task_dir / "backtest.csv"
    if backtest.is_file():
        batch_bt = []
        for r in _read_rows(backtest, BACKTEST_COLUMNS):
            if r["iso3"] not in known:
                summary.skipped_unknown_country += 1
                continue
            batch_bt.append(
                (
                    r["model_id"],
                    r["iso3"],
                    int(r["origin_year"]),
                    int(r["target_year"]),
                    int(r["horizon"]),
                    float(r["actual"]),
                    float(r["point"]),
                    _optional_float(r["lower_80"]),
                    _optional_float(r["upper_80"]),
                )
            )
        connection.executemany(
            f"INSERT INTO backtest_predictions ({', '.join(BACKTEST_COLUMNS)}) "
            f"VALUES ({', '.join('?' * len(BACKTEST_COLUMNS))})",
            batch_bt,
        )
        summary.backtest += len(batch_bt)

    contributions = task_dir / "contributions.csv"
    if contributions.is_file():
        batch_c = []
        for r in _read_rows(contributions, CONTRIBUTION_COLUMNS):
            if r["iso3"] not in known:
                summary.skipped_unknown_country += 1
                continue
            batch_c.append(
                (
                    r["model_id"],
                    r["iso3"],
                    int(r["target_year"]),
                    r["feature"],
                    _optional_float(r["feature_value"]),
                    float(r["contribution"]),
                )
            )
        connection.executemany(
            f"INSERT INTO forecast_contributions ({', '.join(CONTRIBUTION_COLUMNS)}) "
            f"VALUES ({', '.join('?' * len(CONTRIBUTION_COLUMNS))})",
            batch_c,
        )
        summary.contributions += len(batch_c)


def load_anomaly_scores(
    connection: sqlite3.Connection, path: Path, summary: ArtifactSummary
) -> None:
    if not path.is_file():
        summary.notes.append(f"{path} not found; anomaly scores not loaded")
        return
    known = _known_countries(connection)
    indicators = {str(row[0]) for row in connection.execute("SELECT id FROM indicators")}
    batch = []
    for r in _read_rows(path, ANOMALY_COLUMNS):
        if r["iso3"] not in known or r["indicator_id"] not in indicators:
            summary.skipped_unknown_country += 1
            continue
        batch.append(
            (r["indicator_id"], r["iso3"], int(r["year"]), float(r["score"]), int(r["is_flagged"]))
        )
    connection.executemany(
        f"INSERT INTO anomaly_scores ({', '.join(ANOMALY_COLUMNS)}) VALUES (?, ?, ?, ?, ?)",
        batch,
    )
    summary.anomaly_scores += len(batch)


def load_imputation_labels(models_dir: Path | None) -> frozenset[tuple[str, int]]:
    """``(iso3, year)`` wage cells the forensic reconstruction proved imputed.

    Read from ``anomaly/labelled_cells.csv`` (column ``label``). These are
    exact labels recovered from the imputation formula, not detector scores,
    so the ETL can safely act on them. The labels depend only on wage levels
    and exchange rates, never on anything they filter, so building the
    warehouse, training, and rebuilding is deterministic, not circular.
    """
    if models_dir is None:
        return frozenset()
    path = models_dir / "anomaly" / "labelled_cells.csv"
    if not path.is_file():
        return frozenset()
    cells: set[tuple[str, int]] = set()
    for row in _read_rows(path, ("iso3", "year", "label")):
        if row["label"].strip().lower() in {"true", "1"}:
            cells.add((row["iso3"], int(row["year"])))
    return frozenset(cells)


def load_all(
    connection: sqlite3.Connection, *, api_dir: Path, models_dir: Path | None
) -> ArtifactSummary:
    """Load the IMF benchmark and every model artefact that exists."""
    summary = ArtifactSummary()
    load_imf_benchmark(connection, api_dir, summary)
    if models_dir is None or not models_dir.is_dir():
        summary.notes.append("no data/models directory; serving data without forecasts")
        return summary
    for task_dir in sorted(p for p in models_dir.iterdir() if p.is_dir()):
        if task_dir.name == "anomaly":
            load_anomaly_scores(connection, task_dir / "scores.csv", summary)
            card = task_dir / "model_card.json"
            if card.is_file():
                connection.execute(
                    "INSERT INTO etl_metadata (key, value) VALUES (?, ?)",
                    ("model_card:anomaly", card.read_text(encoding="utf-8")),
                )
        else:
            load_forecasting_task(connection, task_dir, summary)
    logger.info("model artefacts: %s", summary.as_dict())
    return summary
