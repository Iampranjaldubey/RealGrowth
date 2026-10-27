"""Rolling-origin (expanding-window) backtest.

For each origin year ``o`` and horizon ``h`` a fresh model is trained on rows
whose *target* year ``year + h`` is ``<= o`` — exactly what had been observed
when year-``o`` data came out — and asked to forecast every country from
origin ``o``. Using the target year, not the origin year, as the cut-off is the
detail that prevents leakage for multi-step horizons: a row with origin
``o - 1`` and ``h = 2`` has a target in ``o + 1``, which is still the future.

The output is one row per out-of-sample forecast and is the raw material for
every metric, every conformal interval and every backtest chart in the project.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

import numpy as np
import pandas as pd

from realgrowth_ml.features import inv_slog
from realgrowth_ml.models import Forecaster

BACKTEST_COLUMNS = (
    "model_id",
    "iso3",
    "origin_year",
    "target_year",
    "horizon",
    "infl_origin",
    "target_log",
    "point_log",
    "actual",
    "point",
)


def training_mask(frame: pd.DataFrame, origin: int, horizon: int) -> pd.Series:
    """Rows usable to train a model that forecasts from ``origin``."""
    target = frame[f"target_h{horizon}"]
    return (frame["year"] + horizon <= origin) & target.notna()


def run_backtest(
    frame: pd.DataFrame,
    model_id: str,
    factory: Callable[[dict[str, Any]], Forecaster],
    *,
    horizon: int,
    origins: Iterable[int],
    params: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Out-of-sample forecasts for every origin in ``origins``."""
    target_col = f"target_h{horizon}"
    actual_col = f"actual_h{horizon}"
    pieces: list[pd.DataFrame] = []
    for origin in origins:
        train = training_mask(frame, origin, horizon)
        test = (frame["year"] == origin) & frame[target_col].notna()
        if not train.any() or not test.any():
            continue
        model = factory(params or {}).fit(frame[train], frame.loc[train, target_col])
        rows = frame[test]
        point_log = model.predict(rows)
        pieces.append(
            pd.DataFrame(
                {
                    "model_id": model_id,
                    "iso3": rows["iso3"].to_numpy(),
                    "origin_year": origin,
                    "target_year": origin + horizon,
                    "horizon": horizon,
                    "infl_origin": rows["infl_raw"].to_numpy(),
                    "target_log": rows[target_col].to_numpy(),
                    "point_log": point_log,
                    "actual": rows[actual_col].to_numpy(),
                    "point": np.asarray(inv_slog(point_log)),
                }
            )
        )
    if not pieces:
        return pd.DataFrame(columns=list(BACKTEST_COLUMNS))
    return pd.concat(pieces, ignore_index=True)
