"""Feature engineering for the inflation panel.

Every row is a ``(country, origin year t)`` pair. Its features use only values
dated ``<= t`` and its target is inflation in year ``t + h``. Two rules keep it
honest, and both are pinned by tests (``ml/tests/test_features.py``):

1. **No look-ahead.** Lags and rolling windows are built by shifting the year
   axis to the right (into the future), never to the left. Changing any value
   dated after ``t`` cannot change a feature of row ``t``.
2. **Cross-country features use the same year only.** ``global_infl_median`` at
   ``t`` is the median of other countries' inflation in ``t`` — information
   that exists when year-``t`` data is published.

Information set: annual data for year ``t`` is published during year ``t + 1``
(World Bank WDI refreshes roughly quarterly), so a 1-year-ahead forecast is in
practice a forecast of the *current* year made with last year's data, and the
2-year-ahead forecast is genuinely a year out.

Inflation spans -30% to +65,000%, so models work on the signed-log scale
``slog(x) = sign(x) * log1p(|x|)``: roughly linear around normal inflation,
compressive in hyperinflations, and its errors are close to relative errors.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from realgrowth_ml.config import FIRST_FEATURE_YEAR, TARGET_INDICATOR
from realgrowth_ml.data import Panel


def slog(
    x: np.ndarray | pd.Series | pd.DataFrame | float,
) -> np.ndarray | pd.Series | pd.DataFrame | float:
    """Signed log1p: ``sign(x) * log(1 + |x|)``."""
    return np.sign(x) * np.log1p(np.abs(x))


def inv_slog(
    z: np.ndarray | pd.Series | pd.DataFrame | float,
) -> np.ndarray | pd.Series | pd.DataFrame | float:
    """Inverse of :func:`slog`."""
    return np.sign(z) * np.expm1(np.abs(z))


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    description: str
    group: str  # "inflation" | "macro" | "global" | "structural"


FEATURES: tuple[FeatureSpec, ...] = (
    FeatureSpec("infl_lag0", "CPI inflation in the origin year (slog)", "inflation"),
    FeatureSpec("infl_lag1", "CPI inflation one year before the origin (slog)", "inflation"),
    FeatureSpec("infl_lag2", "CPI inflation two years before the origin (slog)", "inflation"),
    FeatureSpec("infl_mean5", "Mean of slog inflation over the last 5 years", "inflation"),
    FeatureSpec("infl_std5", "Std. dev. of slog inflation over the last 5 years", "inflation"),
    FeatureSpec("infl_change", "Change in slog inflation over the origin year", "inflation"),
    FeatureSpec("deflator_lag0", "GDP-deflator inflation in the origin year (slog)", "macro"),
    FeatureSpec("money_growth_lag0", "Broad money growth in the origin year (slog)", "macro"),
    FeatureSpec("money_growth_lag1", "Broad money growth one year before (slog)", "macro"),
    FeatureSpec("fx_change_lag0", "Depreciation vs USD over the origin year, % (slog)", "macro"),
    FeatureSpec("gdp_growth_lag0", "Real GDP growth in the origin year, %", "macro"),
    FeatureSpec("unemployment_lag0", "Unemployment rate in the origin year, %", "macro"),
    FeatureSpec("real_interest_lag0", "Real lending rate in the origin year (slog)", "macro"),
    FeatureSpec("current_account_lag0", "Current account balance, % of GDP", "macro"),
    FeatureSpec("debt_lag0", "General government gross debt, % of GDP", "macro"),
    FeatureSpec("log_trade_openness", "log of trade (exports + imports) as % of GDP", "structural"),
    FeatureSpec("log_gdp_pc_ppp", "log GDP per capita at PPP (level of development)", "structural"),
    FeatureSpec("global_infl_median", "Cross-country median slog inflation, origin year", "global"),
    FeatureSpec("global_infl_change", "Change in the cross-country median over the year", "global"),
    FeatureSpec("region_code", "World Bank region (categorical)", "structural"),
)

FEATURE_NAMES: tuple[str, ...] = tuple(f.name for f in FEATURES)
INFLATION_ONLY: tuple[str, ...] = tuple(
    f.name for f in FEATURES if f.group in {"inflation", "global"}
)
CATEGORICAL: tuple[str, ...] = ("region_code",)


def _lag(frame: pd.DataFrame, k: int) -> pd.DataFrame:
    """Value from ``k`` years earlier, aligned to the current year column."""
    return frame.shift(k, axis=1)


def _rolling(frame: pd.DataFrame, window: int, stat: str, min_periods: int) -> pd.DataFrame:
    rolled = frame.T.rolling(window, min_periods=min_periods)
    result = rolled.mean() if stat == "mean" else rolled.std()
    return result.T


def _stack(frame: pd.DataFrame, name: str) -> pd.Series:
    series = frame.stack(future_stack=True)
    series.index = series.index.set_names(["iso3", "year"])
    return series.rename(name)


def build_feature_frame(
    panel: Panel,
    horizons: Iterable[int],
    *,
    first_year: int = FIRST_FEATURE_YEAR,
) -> pd.DataFrame:
    """One row per (iso3, origin year) with features and per-horizon targets.

    Columns: every name in :data:`FEATURE_NAMES`; ``infl_raw`` (origin-year
    inflation, %); and for each horizon ``h``: ``target_h{h}`` (slog) and
    ``actual_h{h}`` (%), NaN where the target year is not observed yet.
    """
    infl = panel.wide(TARGET_INDICATOR)
    years = list(infl.columns)
    countries = list(infl.index)

    def aligned(indicator_id: str) -> pd.DataFrame:
        frame = panel.wide(indicator_id)
        return frame.reindex(index=countries, columns=years)

    s = slog(infl)
    features: dict[str, pd.DataFrame] = {
        "infl_lag0": s,
        "infl_lag1": _lag(s, 1),
        "infl_lag2": _lag(s, 2),
        "infl_mean5": _rolling(s, 5, "mean", 3),
        "infl_std5": _rolling(s, 5, "std", 3),
        "infl_change": s - _lag(s, 1),
    }

    money = slog(aligned("broad_money_growth"))
    fx = aligned("exchange_rate")
    fx_change = 100.0 * (fx / _lag(fx, 1) - 1.0)
    features |= {
        "deflator_lag0": slog(aligned("gdp_deflator_inflation")),
        "money_growth_lag0": money,
        "money_growth_lag1": _lag(money, 1),
        "fx_change_lag0": slog(fx_change),
        "gdp_growth_lag0": aligned("gdp_growth"),
        "unemployment_lag0": aligned("unemployment_rate"),
        "real_interest_lag0": slog(aligned("real_interest_rate")),
        "current_account_lag0": aligned("current_account"),
        "debt_lag0": aligned("debt_to_gdp"),
        "log_trade_openness": np.log(aligned("trade_openness").where(lambda f: f > 0)),
        "log_gdp_pc_ppp": np.log(aligned("gdp_per_capita_ppp").where(lambda f: f > 0)),
    }

    median = s.median(axis=0, skipna=True)
    global_median = pd.DataFrame(
        np.tile(median.to_numpy(), (len(countries), 1)), index=countries, columns=years
    )
    features["global_infl_median"] = global_median
    features["global_infl_change"] = global_median - _lag(global_median, 1)

    columns = [_stack(frame, name) for name, frame in features.items()]
    columns.append(_stack(infl, "infl_raw"))
    for h in horizons:
        columns.append(_stack(s.shift(-h, axis=1), f"target_h{h}"))
        columns.append(_stack(infl.shift(-h, axis=1), f"actual_h{h}"))

    out = pd.concat(columns, axis=1)
    regions = panel.countries["region"].reindex(out.index.get_level_values("iso3"))
    codes = {name: i for i, name in enumerate(sorted(panel.countries["region"].dropna().unique()))}
    out["region_code"] = regions.map(codes).to_numpy(dtype=float)

    out = out.reset_index()
    out = out[out["year"] >= first_year]
    # Every model, baselines included, needs origin-year inflation.
    out = out[out["infl_lag0"].notna()]
    return out.sort_values(["year", "iso3"]).reset_index(drop=True)
