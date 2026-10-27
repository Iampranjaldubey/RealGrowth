"""RealGrowth modelling package.

Offline training and evaluation for the two modelling problems in the project:

* :mod:`realgrowth_ml.forecasting` — 1- and 2-year-ahead national CPI inflation
  forecasts from a global LightGBM model, evaluated against baselines with a
  rolling-origin backtest and wrapped in Mondrian conformal prediction
  intervals.
* :mod:`realgrowth_ml.anomaly` — detecting imputation artefacts in the wage
  panel, with exact ground-truth labels recovered by reverse-engineering the
  imputation algorithm.

Outputs are plain files under ``data/models/``, which the stdlib ETL loads into
the warehouse the API serves. See ``docs/MODELING.md``.
"""

__version__ = "1.0.0"
