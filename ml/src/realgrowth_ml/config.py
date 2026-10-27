"""Paths and experiment constants, in one place so every number in the docs
can be traced to a line here.
"""

from __future__ import annotations

from pathlib import Path

#: ml/src/realgrowth_ml/config.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO_ROOT / "data" / "realgrowth.db"
DEFAULT_MODELS_DIR = REPO_ROOT / "data" / "models"
DEFAULT_REPORTS_DIR = REPO_ROOT / "reports"

#: Deterministic seeds for every stochastic component.
SEED = 20261027

# ------------------------------------------------------------ forecasting

TARGET_INDICATOR = "inflation_rate"
HORIZONS: tuple[int, ...] = (1, 2)

#: First origin year with enough history behind it (IMF/WB coverage broadens
#: around 1980; three lags plus a five-year window need a few years more).
FIRST_FEATURE_YEAR = 1980

#: Rolling-origin backtest. Every origin in BACKTEST_ORIGINS is forecast by a
#: model trained only on rows whose *target* year is <= the origin.
#: Hyperparameters and the champion are chosen on the validation window only;
#: the test window is reported once and never used for selection.
FIRST_BACKTEST_ORIGIN = 1995
VALIDATION_ORIGINS = range(2001, 2009)  # targets 2002-2010
FIRST_TEST_ORIGIN = 2009  # targets 2010 onwards

#: Conformal calibration: residuals from the most recent N origins whose
#: targets are already observed at forecast time.
CONFORMAL_WINDOW = 10
#: Minimum residuals per Mondrian bin before falling back to the pooled set.
CONFORMAL_MIN_BIN = 30
#: Inflation-regime bin edges (% at origin) for Mondrian conformal intervals.
REGIME_EDGES: tuple[float, ...] = (4.0, 10.0)
INTERVAL_LEVELS: tuple[float, ...] = (0.80, 0.95)

#: A forecast is only issued for a country whose latest observation is at
#: most this many years older than the panel's latest year.
MAX_STALENESS = 1

# ---------------------------------------------------------------- anomaly

#: Countries that must share a year-on-year growth ratio (to RATIO_DECIMALS)
#: for it to count as the imputation fingerprint.
FINGERPRINT_MIN_SHARED = 3
RATIO_DECIMALS = 6
#: Relative tolerance for the leave-one-out level check.
LEVEL_RTOL = 1e-6
