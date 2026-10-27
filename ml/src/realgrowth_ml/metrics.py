"""Forecast evaluation metrics.

Point accuracy is reported on two scales:

* **percentage points** (``mae``, ``rmse``, ``median_ae``) — what a reader
  cares about, but dominated by a handful of hyperinflation country-years;
* **signed-log** (``mae_log``) — close to relative error, so a 2-point miss on
  3% inflation counts for more than a 2-point miss on 80%. Model selection uses
  this scale, which is also the scale the models are trained on.

``skill`` is ``1 - MAE_model / MAE_naive`` on the log scale (positive = better
than the random walk, the standard benchmark in the inflation-forecasting
literature since Atkeson & Ohanian, 2001).

Significance uses a Diebold-Mariano test on the per-year mean loss
differential. Averaging across countries first matters: errors within a year
are strongly correlated (2022 surprised everyone), so treating ~180
country-years as independent would overstate significance by an order of
magnitude.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from scipy import stats

from realgrowth_ml.features import slog


@dataclass(frozen=True)
class PointMetrics:
    n: int
    mae: float
    rmse: float
    median_ae: float
    mae_log: float

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


def point_metrics(actual: np.ndarray | pd.Series, point: np.ndarray | pd.Series) -> PointMetrics:
    a = np.asarray(actual, dtype=float)
    p = np.asarray(point, dtype=float)
    ok = np.isfinite(a) & np.isfinite(p)
    a, p = a[ok], p[ok]
    if a.size == 0:
        nan = float("nan")
        return PointMetrics(0, nan, nan, nan, nan)
    err = a - p
    log_err = np.asarray(slog(a)) - np.asarray(slog(p))
    return PointMetrics(
        n=int(a.size),
        mae=float(np.mean(np.abs(err))),
        rmse=float(np.sqrt(np.mean(err**2))),
        median_ae=float(np.median(np.abs(err))),
        mae_log=float(np.mean(np.abs(log_err))),
    )


def skill(model_mae: float, baseline_mae: float) -> float:
    """``1 - model / baseline``; positive means the model beats the baseline."""
    if not baseline_mae or not math.isfinite(baseline_mae):
        return float("nan")
    return 1.0 - model_mae / baseline_mae


def coverage(actual: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> tuple[float, int]:
    """Share of actuals inside ``[lower, upper]``, over rows that have an interval."""
    a, lo, hi = (np.asarray(v, dtype=float) for v in (actual, lower, upper))
    ok = np.isfinite(a) & np.isfinite(lo) & np.isfinite(hi)
    if not ok.any():
        return float("nan"), 0
    inside = (a[ok] >= lo[ok]) & (a[ok] <= hi[ok])
    return float(inside.mean()), int(ok.sum())


@dataclass(frozen=True)
class DieboldMariano:
    statistic: float
    p_value: float
    n_periods: int
    mean_loss_diff: float

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


def diebold_mariano(
    frame: pd.DataFrame,
    loss_a: str,
    loss_b: str,
    *,
    period: str = "target_year",
    horizon: int = 1,
) -> DieboldMariano:
    """Two-sided DM test that models A and B have equal expected loss.

    ``frame`` has one row per forecast with columns ``loss_a``, ``loss_b`` and
    ``period``. The loss differential is averaged within each period, then a
    Newey-West variance with ``horizon - 1`` lags is used (h-step forecasts
    have MA(h-1) errors), with the Harvey-Leybourne-Newbold small-sample
    correction and a Student-t reference distribution. Negative statistics
    mean model A has lower loss.
    """
    d = (frame[loss_a] - frame[loss_b]).groupby(frame[period]).mean().sort_index()
    t = int(d.size)
    if t < 3:
        return DieboldMariano(float("nan"), float("nan"), t, float("nan"))
    values = d.to_numpy(dtype=float)
    mean = float(values.mean())
    centred = values - mean
    lags = max(0, horizon - 1)
    gamma0 = float(np.dot(centred, centred) / t)
    variance = gamma0
    for k in range(1, lags + 1):
        gamma_k = float(np.dot(centred[k:], centred[:-k]) / t)
        variance += 2.0 * (1.0 - k / (lags + 1)) * gamma_k
    if variance <= 0:
        return DieboldMariano(float("nan"), float("nan"), t, mean)
    dm = mean / math.sqrt(variance / t)
    hln = math.sqrt((t + 1 - 2 * horizon + horizon * (horizon - 1) / t) / t)
    statistic = dm * hln
    p_value = float(2.0 * stats.t.sf(abs(statistic), df=t - 1))
    return DieboldMariano(float(statistic), p_value, t, mean)
