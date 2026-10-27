"""Prediction intervals by split conformal prediction (Mondrian variant).

A point forecast of 4.1% is not useful without "give or take how much?".
Conformal prediction answers that without distributional assumptions: take a
calibration set of *out-of-sample* absolute errors, and the
``ceil((n + 1) * level) / n`` empirical quantile ``q`` gives an interval
``point ± q`` that contains the truth with probability at least ``level``,
provided calibration and test errors are exchangeable.

Two refinements make that assumption more plausible for inflation:

* **Rolling calibration window.** Only errors from the last
  :data:`~realgrowth_ml.config.CONFORMAL_WINDOW` target years observed by the
  forecast origin are used, so the interval adapts to the error regime (the
  2021-23 surge widened intervals automatically) and never uses the future.
* **Mondrian bins by inflation regime.** Errors are calibrated separately for
  low (<4%), moderate (4-10%) and high (>10%) origin inflation, because a model
  is far less certain about Argentina than about Switzerland. Bins with too few
  errors fall back to the pooled set.

Errors are taken on the signed-log scale and mapped back, so intervals are
asymmetric in percentage points — wider on the upside, as inflation risk is.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import pandas as pd

from realgrowth_ml.config import (
    CONFORMAL_MIN_BIN,
    CONFORMAL_WINDOW,
    INTERVAL_LEVELS,
    REGIME_EDGES,
)
from realgrowth_ml.features import inv_slog


def regime(
    infl_origin: np.ndarray | pd.Series, edges: Sequence[float] = REGIME_EDGES
) -> np.ndarray:
    """Bin index by absolute origin inflation: 0 low, 1 moderate, 2 high."""
    return np.digitize(np.abs(np.asarray(infl_origin, dtype=float)), list(edges))


def conformal_quantile(scores: np.ndarray, level: float) -> float:
    """Finite-sample-valid quantile; ``inf`` if there are too few scores."""
    n = scores.size
    if n == 0:
        return math.inf
    rank = math.ceil((n + 1) * level)
    if rank > n:
        return math.inf
    return float(np.sort(scores)[rank - 1])


def _quantiles_for(
    calibration: pd.DataFrame, bin_index: int, levels: Sequence[float], min_bin: int
) -> dict[float, float]:
    scores = calibration["abs_err_log"].to_numpy()
    in_bin = calibration["regime"].to_numpy() == bin_index
    if in_bin.sum() >= min_bin:
        scores = scores[in_bin]
    return {level: conformal_quantile(scores, level) for level in levels}


def add_intervals(
    backtest: pd.DataFrame,
    *,
    levels: Sequence[float] = INTERVAL_LEVELS,
    window: int = CONFORMAL_WINDOW,
    min_bin: int = CONFORMAL_MIN_BIN,
) -> pd.DataFrame:
    """Attach conformal intervals to every backtest row that has calibration data.

    For a row with origin ``o`` the calibration set is the same model and
    horizon's errors whose target year lies in ``(o - window, o]`` — observed by
    the time the forecast is made, never including the row itself.
    """
    out = backtest.copy()
    out["regime"] = regime(out["infl_origin"])
    out["abs_err_log"] = (out["target_log"] - out["point_log"]).abs()
    for level in levels:
        out[f"lower_{int(level * 100)}"] = np.nan
        out[f"upper_{int(level * 100)}"] = np.nan

    for (_, _), group in out.groupby(["model_id", "horizon"], sort=False):
        for origin, rows in group.groupby("origin_year"):
            calibration = group[
                (group["target_year"] <= origin) & (group["target_year"] > origin - window)
            ]
            if calibration.empty:
                continue
            for bin_index, bin_rows in rows.groupby("regime"):
                quantiles = _quantiles_for(calibration, int(bin_index), levels, min_bin)
                for level, q in quantiles.items():
                    if not math.isfinite(q):
                        continue
                    pct = int(level * 100)
                    centre = bin_rows["point_log"].to_numpy()
                    out.loc[bin_rows.index, f"lower_{pct}"] = inv_slog(centre - q)
                    out.loc[bin_rows.index, f"upper_{pct}"] = inv_slog(centre + q)
    return out


def forward_intervals(
    point_log: np.ndarray,
    infl_origin: np.ndarray,
    calibration: pd.DataFrame,
    *,
    levels: Sequence[float] = INTERVAL_LEVELS,
    min_bin: int = CONFORMAL_MIN_BIN,
) -> dict[str, np.ndarray]:
    """Intervals for live forecasts, from the latest backtest errors."""
    cal = calibration.copy()
    cal["regime"] = regime(cal["infl_origin"])
    cal["abs_err_log"] = (cal["target_log"] - cal["point_log"]).abs()
    bins = regime(infl_origin)
    result: dict[str, np.ndarray] = {}
    for level in levels:
        pct = int(level * 100)
        lower = np.full(point_log.shape, np.nan)
        upper = np.full(point_log.shape, np.nan)
        for bin_index in np.unique(bins):
            q = _quantiles_for(cal, int(bin_index), [level], min_bin)[level]
            if not math.isfinite(q):
                continue
            mask = bins == bin_index
            lower[mask] = np.asarray(inv_slog(point_log[mask] - q))
            upper[mask] = np.asarray(inv_slog(point_log[mask] + q))
        result[f"lower_{pct}"] = lower
        result[f"upper_{pct}"] = upper
    return result
