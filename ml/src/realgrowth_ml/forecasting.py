"""End-to-end inflation forecasting experiment.

``run_experiment`` is the single function behind ``python -m realgrowth_ml
train``. In order:

1. build the leakage-safe feature frame from the warehouse;
2. tune LightGBM on the **validation** origins only;
3. run the rolling-origin backtest for every model, horizon and origin;
4. attach Mondrian conformal intervals to every backtest forecast;
5. score each model on the validation and **test** windows, pick the champion
   on validation, and report its test performance once (with Diebold-Mariano
   tests against the baselines);
6. refit the champion on all observed data and issue forward forecasts with
   intervals and TreeSHAP attributions;
7. write the artefact contract in ``data/models/inflation/``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from realgrowth_ml import __version__
from realgrowth_ml.backtest import run_backtest, training_mask
from realgrowth_ml.config import (
    CONFORMAL_WINDOW,
    FIRST_BACKTEST_ORIGIN,
    FIRST_TEST_ORIGIN,
    HORIZONS,
    INTERVAL_LEVELS,
    MAX_STALENESS,
    REGIME_EDGES,
    SEED,
    TARGET_INDICATOR,
    VALIDATION_ORIGINS,
)
from realgrowth_ml.conformal import add_intervals, forward_intervals
from realgrowth_ml.data import Panel
from realgrowth_ml.features import FEATURES, build_feature_frame, inv_slog
from realgrowth_ml.metrics import coverage, diebold_mariano, point_metrics, skill
from realgrowth_ml.models import LGBM_GRID, MODEL_SPECS, spec

logger = logging.getLogger(__name__)

TASK = "inflation"


@dataclass
class ExperimentResult:
    card: dict[str, Any]
    backtest: pd.DataFrame
    forecasts: pd.DataFrame
    contributions: pd.DataFrame
    feature_frame: pd.DataFrame


# ----------------------------------------------------------------- tuning


def tune(
    frame: pd.DataFrame, model_id: str, horizon: int, origins: range
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Grid search on validation origins; returns best params and the full log."""
    model = spec(model_id)
    log: list[dict[str, Any]] = []
    best: tuple[float, dict[str, Any]] = (float("inf"), {})
    for params in LGBM_GRID:
        bt = run_backtest(
            frame, model_id, model.factory, horizon=horizon, origins=origins, params=params
        )
        score = point_metrics(bt["actual"], bt["point"]).mae_log
        log.append({**params, "val_mae_log": round(score, 5)})
        if score < best[0]:
            best = (score, params)
    return best[1], log


# ------------------------------------------------------------- evaluation


def _window(backtest: pd.DataFrame, name: str) -> pd.DataFrame:
    if name == "validation":
        return backtest[backtest["origin_year"].isin(list(VALIDATION_ORIGINS))]
    if name == "test":
        return backtest[backtest["origin_year"] >= FIRST_TEST_ORIGIN]
    return backtest


def score_models(backtest: pd.DataFrame) -> list[dict[str, Any]]:
    """Metrics per model x horizon x window, with skill vs the naive baseline.

    Scored on a common sample: only (country, origin, horizon) cells that every
    model forecast, so differences come from the models, not from coverage.
    """
    rows: list[dict[str, Any]] = []
    key = ["iso3", "origin_year", "horizon"]
    n_models = backtest["model_id"].nunique()
    common = backtest.groupby(key)["model_id"].transform("nunique") == n_models
    shared = backtest[common]
    for window in ("validation", "test"):
        subset = _window(shared, window)
        for horizon, by_h in subset.groupby("horizon"):
            naive = by_h[by_h["model_id"] == "naive"]
            naive_metrics = point_metrics(naive["actual"], naive["point"])
            for model_id, group in by_h.groupby("model_id"):
                m = point_metrics(group["actual"], group["point"])
                cov80, n80 = coverage(group["actual"], group["lower_80"], group["upper_80"])
                cov95, _ = coverage(group["actual"], group["lower_95"], group["upper_95"])
                width80 = float((group["upper_80"] - group["lower_80"]).median())
                rows.append(
                    {
                        "model_id": model_id,
                        "horizon": int(horizon),
                        "window": window,
                        **m.as_dict(),
                        "skill_vs_naive": skill(m.mae_log, naive_metrics.mae_log),
                        "coverage_80": cov80,
                        "coverage_95": cov95,
                        "interval_n": n80,
                        "median_width_80": width80,
                    }
                )
    return rows


def significance(backtest: pd.DataFrame, champion: str) -> list[dict[str, Any]]:
    """DM tests: champion vs each other model, on the test window, per horizon."""
    test = _window(backtest, "test").copy()
    test["loss"] = (test["target_log"] - test["point_log"]).abs()
    out: list[dict[str, Any]] = []
    for horizon, by_h in test.groupby("horizon"):
        wide = by_h.pivot_table(
            index=["iso3", "target_year"], columns="model_id", values="loss"
        ).dropna()
        wide = wide.reset_index()
        for other in sorted(set(wide.columns) - {"iso3", "target_year", champion}):
            dm = diebold_mariano(wide, champion, other, horizon=int(horizon))
            out.append({"horizon": int(horizon), "versus": other, **dm.as_dict()})
    return out


def regime_breakdown(backtest: pd.DataFrame, champion: str) -> list[dict[str, Any]]:
    """Test-window accuracy and interval coverage by origin inflation regime."""
    test = _window(backtest, "test")
    labels = {
        0: f"<{REGIME_EDGES[0]:g}%",
        1: f"{REGIME_EDGES[0]:g}-{REGIME_EDGES[1]:g}%",
        2: f">{REGIME_EDGES[1]:g}%",
    }
    out = []
    for (model_id, horizon, bin_index), g in test.groupby(["model_id", "horizon", "regime"]):
        if model_id not in {champion, "naive"}:
            continue
        m = point_metrics(g["actual"], g["point"])
        cov80, _ = coverage(g["actual"], g["lower_80"], g["upper_80"])
        out.append(
            {
                "model_id": model_id,
                "horizon": int(horizon),
                "regime": labels[int(bin_index)],
                "n": m.n,
                "mae": m.mae,
                "median_ae": m.median_ae,
                "mae_log": m.mae_log,
                "coverage_80": cov80,
            }
        )
    return out


def yearly_errors(backtest: pd.DataFrame) -> list[dict[str, Any]]:
    """Median absolute error per model, horizon and target year (for charts)."""
    g = backtest.assign(abs_err=(backtest["actual"] - backtest["point"]).abs())
    table = g.groupby(["model_id", "horizon", "target_year"])["abs_err"].median().reset_index()
    return [
        {
            "model_id": r.model_id,
            "horizon": int(r.horizon),
            "target_year": int(r.target_year),
            "median_ae": float(r.abs_err),
        }
        for r in table.itertuples()
    ]


# ------------------------------------------------------------ production


def forward_forecasts(
    frame: pd.DataFrame,
    backtest: pd.DataFrame,
    champion: str,
    params: dict[str, dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Refit the champion on all observed data and forecast from each country's
    latest origin. Returns forecasts, TreeSHAP contributions and fit metadata.
    """
    latest_year = int(frame["year"].max())
    latest = frame.sort_values("year").groupby("iso3").tail(1)
    latest = latest[latest["year"] >= latest_year - MAX_STALENESS]

    model_spec = spec(champion)
    forecasts: list[pd.DataFrame] = []
    contributions: list[pd.DataFrame] = []
    fit_meta: dict[str, Any] = {}
    for horizon in HORIZONS:
        target = f"target_h{horizon}"
        train = frame[target].notna()
        model = model_spec.factory(params.get(f"h{horizon}", {}))
        model.fit(frame[train], frame.loc[train, target])
        fit_meta[f"h{horizon}"] = {
            "training_rows": int(train.sum()),
            "training_target_years": [
                int(frame.loc[train, "year"].min()) + horizon,
                int(frame.loc[train, "year"].max()) + horizon,
            ],
        }
        point_log = model.predict(latest)

        cal = backtest[(backtest["model_id"] == champion) & (backtest["horizon"] == horizon)]
        last_target = int(cal["target_year"].max())
        cal = cal[cal["target_year"] > last_target - CONFORMAL_WINDOW]
        intervals = forward_intervals(point_log, latest["infl_raw"].to_numpy(), cal)

        forecasts.append(
            pd.DataFrame(
                {
                    "model_id": champion,
                    "iso3": latest["iso3"].to_numpy(),
                    "origin_year": latest["year"].to_numpy(),
                    "target_year": latest["year"].to_numpy() + horizon,
                    "horizon": horizon,
                    "point": np.asarray(inv_slog(point_log)),
                    **intervals,
                }
            )
        )
        if hasattr(model, "contributions"):
            shap = model.contributions(latest)
            feature_columns = [c for c in shap.columns if c != "bias"]
            long = shap[feature_columns].stack().rename("contribution").reset_index()
            long.columns = ["row", "feature", "contribution"]
            values = latest[feature_columns].stack(future_stack=True).rename("feature_value")
            values = values.reset_index()
            values.columns = ["row", "feature", "feature_value"]
            long = long.merge(values, on=["row", "feature"], how="left")
            long["iso3"] = latest.loc[long["row"], "iso3"].to_numpy()
            long["target_year"] = latest.loc[long["row"], "year"].to_numpy() + horizon
            long["model_id"] = champion
            contributions.append(long.drop(columns="row"))

    forecasts_df = pd.concat(forecasts, ignore_index=True)
    contributions_df = (
        pd.concat(contributions, ignore_index=True) if contributions else pd.DataFrame()
    )
    return forecasts_df, contributions_df, fit_meta


def global_importance(contributions: pd.DataFrame) -> list[dict[str, Any]]:
    if contributions.empty:
        return []
    table = (
        contributions.assign(abs_c=contributions["contribution"].abs())
        .groupby("feature")["abs_c"]
        .mean()
        .sort_values(ascending=False)
    )
    return [{"feature": f, "mean_abs_shap": float(v)} for f, v in table.items()]


# --------------------------------------------------------------- pipeline


def run_experiment(panel: Panel, *, tune_models: bool = True) -> ExperimentResult:
    started = time.perf_counter()
    frame = build_feature_frame(panel, HORIZONS)
    last_year = int(frame["year"].max())
    origins = range(FIRST_BACKTEST_ORIGIN, last_year)
    logger.info(
        "feature frame: %d rows, origins %d-%d", len(frame), origins.start, origins.stop - 1
    )

    tuned: dict[str, dict[str, dict[str, Any]]] = {}
    tuning_log: dict[str, Any] = {}
    for model in MODEL_SPECS:
        tuned[model.id] = {}
        if model.params_from is not None:
            tuned[model.id] = tuned[model.params_from]
            continue
        if not (model.tunable and tune_models):
            continue
        for horizon in HORIZONS:
            best, log = tune(frame, model.id, horizon, VALIDATION_ORIGINS)
            tuned[model.id][f"h{horizon}"] = best
            tuning_log[f"{model.id}:h{horizon}"] = log
            logger.info("tuned %s h=%d -> %s", model.id, horizon, best)

    pieces = []
    for model in MODEL_SPECS:
        for horizon in HORIZONS:
            bt = run_backtest(
                frame,
                model.id,
                model.factory,
                horizon=horizon,
                origins=origins,
                params=tuned[model.id].get(f"h{horizon}"),
            )
            pieces.append(bt)
            logger.info("backtest %-15s h=%d: %d forecasts", model.id, horizon, len(bt))
    backtest = add_intervals(pd.concat(pieces, ignore_index=True))

    metrics = score_models(backtest)
    validation_h1 = [m for m in metrics if m["window"] == "validation" and m["horizon"] == 1]
    champion = min(validation_h1, key=lambda m: m["mae_log"])["model_id"]
    logger.info("champion (validation h=1 MAE on log scale): %s", champion)

    forecasts, contributions, fit_meta = forward_forecasts(
        frame, backtest, champion, tuned.get(champion, {})
    )

    # Leakage audit trail: the last origin's training set must end before it.
    audit = {
        f"h{h}": int(frame.loc[training_mask(frame, last_year - 1, h), "year"].max()) + h
        for h in HORIZONS
    }

    card = build_card(
        panel=panel,
        frame=frame,
        champion=champion,
        tuned=tuned,
        tuning_log=tuning_log,
        metrics=metrics,
        backtest=backtest,
        forecasts=forecasts,
        contributions=contributions,
        fit_meta=fit_meta,
        audit=audit,
        runtime=time.perf_counter() - started,
    )
    return ExperimentResult(card, backtest, forecasts, contributions, frame)


def _metric_lookup(
    metrics: list[dict[str, Any]], model_id: str, horizon: int, window: str
) -> dict[str, Any]:
    for m in metrics:
        if m["model_id"] == model_id and m["horizon"] == horizon and m["window"] == window:
            return m
    return {}


def build_card(**kw: Any) -> dict[str, Any]:
    panel: Panel = kw["panel"]
    frame: pd.DataFrame = kw["frame"]
    champion: str = kw["champion"]
    metrics: list[dict[str, Any]] = kw["metrics"]
    backtest: pd.DataFrame = kw["backtest"]
    forecasts: pd.DataFrame = kw["forecasts"]
    importance = global_importance(kw["contributions"])

    models = []
    for model in MODEL_SPECS:
        models.append(
            {
                "id": model.id,
                "name": model.name,
                "kind": model.kind,
                "description": model.description,
                "card": {
                    "params": kw["tuned"].get(model.id, {}),
                    "test": {
                        f"h{h}": _metric_lookup(metrics, model.id, h, "test") for h in HORIZONS
                    },
                },
            }
        )

    champion_test = {f"h{h}": _metric_lookup(metrics, champion, h, "test") for h in HORIZONS}
    fingerprint = hashlib.sha256(
        pd.util.hash_pandas_object(frame[["iso3", "year", "infl_raw"]], index=False).to_numpy()
    ).hexdigest()[:16]

    return {
        "task": TASK,
        "indicator_id": TARGET_INDICATOR,
        "title": "National CPI inflation, 1 and 2 years ahead",
        "champion": champion,
        "package_version": __version__,
        "trained_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "runtime_seconds": round(kw["runtime"], 1),
        "seed": SEED,
        "data": {
            "warehouse_built_at": panel.built_at,
            "panel_fingerprint": fingerprint,
            "feature_rows": len(frame),
            "countries": int(frame["iso3"].nunique()),
            "origin_years": [int(frame["year"].min()), int(frame["year"].max())],
        },
        "design": {
            "horizons": list(HORIZONS),
            "target_transform": "slog(x) = sign(x) * log1p(|x|)",
            "backtest": "rolling origin, expanding window; train on target year <= origin",
            "first_backtest_origin": FIRST_BACKTEST_ORIGIN,
            "validation_origins": [VALIDATION_ORIGINS.start, VALIDATION_ORIGINS.stop - 1],
            "first_test_origin": FIRST_TEST_ORIGIN,
            "selection_rule": "lowest validation MAE (log scale) at h=1",
            "intervals": (
                f"Mondrian split conformal on log-scale absolute errors; rolling "
                f"{CONFORMAL_WINDOW}-year calibration window; bins by origin inflation "
                f"{list(REGIME_EDGES)}"
            ),
            "interval_levels": list(INTERVAL_LEVELS),
            "leakage_audit_last_training_target_year": kw["audit"],
        },
        "features": [
            {"name": f.name, "description": f.description, "group": f.group} for f in FEATURES
        ],
        "global_importance": importance,
        "models": models,
        "metrics": metrics,
        "champion_test": champion_test,
        "significance": significance(backtest, champion),
        "regimes": regime_breakdown(backtest, champion),
        "yearly_errors": yearly_errors(backtest),
        "tuning": kw["tuning_log"],
        "forecast_summary": {
            "rows": len(forecasts),
            "countries": int(forecasts["iso3"].nunique()),
            "target_years": sorted(int(y) for y in forecasts["target_year"].unique()),
            "fit": kw["fit_meta"],
        },
        "intended_use": (
            "Indicative, transparent baseline forecasts of headline CPI inflation for "
            "public-interest analysis and for the purchasing-power tools on the site."
        ),
        "limitations": [
            "Annual data only: the model cannot see monthly inflation releases, so it "
            "reacts to shocks a year later than a central-bank nowcast would.",
            "Data for year t is published during year t+1, so the 1-year-ahead forecast is "
            "effectively a current-year estimate.",
            "Hyperinflation episodes are rare in training data; intervals in the >10% "
            "regime are wide by design and point forecasts there should not be relied on.",
            "No structural information (policy rates, commodity prices, elections). "
            "Large policy regime changes are not anticipated.",
            "Historical IMF WEO vintages are not freely downloadable by script, so the IMF "
            "comparison is side-by-side for current forecasts, not a backtest.",
        ],
        "not_intended_for": [
            "Monetary-policy, investment or wage-bargaining decisions.",
            "Countries with fewer than three years of recent inflation history.",
        ],
    }


# ------------------------------------------------------------ persistence


def _round(frame: pd.DataFrame, digits: int = 4) -> pd.DataFrame:
    out = frame.copy()
    numeric = out.select_dtypes(include="number").columns
    out[numeric] = out[numeric].round(digits)
    return out


def _clean(obj: Any) -> Any:
    """JSON-safe: NaN/inf -> None, numpy scalars -> Python."""
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_clean(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, float | np.floating):
        value = float(obj)
        return None if not np.isfinite(value) else round(value, 6)
    return obj


def write_artifacts(result: ExperimentResult, models_dir: Path) -> Path:
    out = models_dir / TASK
    out.mkdir(parents=True, exist_ok=True)
    (out / "model_card.json").write_text(
        json.dumps(_clean(result.card), indent=2) + "\n", encoding="utf-8"
    )
    bt = result.backtest[
        [
            "model_id",
            "iso3",
            "origin_year",
            "target_year",
            "horizon",
            "actual",
            "point",
            "lower_80",
            "upper_80",
        ]
    ]
    _round(bt).to_csv(out / "backtest.csv", index=False)
    _round(result.forecasts).to_csv(out / "forecasts.csv", index=False)
    if not result.contributions.empty:
        c = result.contributions[
            ["model_id", "iso3", "target_year", "feature", "feature_value", "contribution"]
        ]
        _round(c, 5).to_csv(out / "contributions.csv", index=False)
    return out
