# Forecasting national inflation

Code: `ml/src/realgrowth_ml/` · Analysis: `notebooks/analysis/02_inflation_forecasting.ipynb`
· Served: `/api/v1/forecasts/{iso3}`, the Inflation Outlook page.

## Problem

Forecast annual CPI inflation (World Bank FP.CPI.TOTL.ZG) for every country,
1 and 2 years ahead, with calibrated prediction intervals. This has practical
uses: wage negotiations, rent and contract indexation, and the purchasing-power
calculator on this site, which uses the forecast to extend beyond the latest
CPI release.

**Information set.** Annual data for year *t* is published during *t*+1. A
forecast made from origin *t* uses only values dated ≤ *t*, so the 1-year-ahead
forecast is in practice an estimate of the current year, and the 2-year-ahead
forecast is genuinely a year out.

## Target scale

Inflation runs from −18% to +23,773% in this panel. Models are trained and
selected on the signed log, `slog(x) = sign(x)·log(1+|x|)`. It is near-linear
around normal inflation, compresses hyperinflations so they don't dominate the
loss, and its errors approximate relative errors. Results are reported in
percentage points as well.

## Features (20, all dated ≤ origin)

| Group | Features |
|---|---|
| Inflation history | `infl_lag0..2`, 5-year mean and std. dev., 1-year change |
| Macro drivers | GDP-deflator inflation; broad money growth (t, t−1); depreciation vs USD; real GDP growth; unemployment; real interest rate; current account; government debt |
| Global cycle | cross-country median inflation and its change (same year only) |
| Structural | log trade openness; log GDP per capita (PPP); World Bank region |

`ml/tests/test_features.py::TestNoLookAhead` enforces no leakage by
intervention. It scrambles every observation after 2010 and asserts that every
feature of every row with origin ≤ 2010 is bit-identical. A control test checks
that targets do change, so the test cannot pass vacuously.

## Models

| id | What it is | Why it is here |
|---|---|---|
| `naive` | next = this year | The benchmark to beat. Notoriously hard (Atkeson & Ohanian, 2001) |
| `mean3` | mean of last three years | A smoothing baseline |
| `pooled_ar` | ridge on 3 lags + global median, pooled | Classical econometric benchmark |
| `lgbm_infl_only` | LightGBM, inflation and global features only | Ablation: what do macro features add? |
| `lgbm_global` | LightGBM, all features, one model for all countries | Global model, as in the M4/M5 competitions |
| `ensemble` | equal-weight mean of `pooled_ar` and `lgbm_global` | Combines a stable linear and a non-linear model |

Weights are equal rather than fitted. Estimated combination weights usually
lose to the simple average out of sample (the "forecast combination puzzle",
Stock & Watson 2004).

## Evaluation protocol

**Rolling-origin backtest.** For every origin *o* from 1995 to 2024 and each
horizon *h*, a new model is trained on rows whose **target year** `year + h ≤ o`,
then forecasts every country from origin *o*. Filtering on the target year
rather than the origin year is what prevents leakage at *h* = 2: a row with
origin *o*−1 has its target in *o*+1, which is still the future at *o*.
`TestTrainingMask` and `TestRunBacktest` pin this down. The result is 62,292
out-of-sample forecasts.

**Three windows, used once each.**

* Origins 1995-2000: burn-in (calibration history for intervals).
* **Validation**, origins 2001-2008: LightGBM hyperparameters are grid-searched
  here (12 configurations: leaves, min child samples, trees), and the champion
  is chosen here by lowest log-scale MAE at *h* = 1.
* **Test**, origins 2009-2024: reported once, never used for any decision.

All models are scored on a common sample (cells every model forecast), so the
comparison is not distorted by coverage differences.

**Significance.** Diebold-Mariano test on the loss differential **averaged per
target year**. Errors within a year are strongly correlated (2022 surprised
every model and every central bank), so treating about 3,000 country-years as
independent would overstate significance by an order of magnitude. The test
uses a Newey-West variance with *h*−1 lags, the Harvey-Leybourne-Newbold
small-sample correction, and a t-distribution with *T*−1 degrees of freedom.

## Prediction intervals: Mondrian split-conformal

For a forecast from origin *o*, the calibration set is the same model and
horizon's absolute log-scale errors from target years in (*o*−10, *o*], all
already observed at *o*. The interval is `point ± q` with q the
`⌈(n+1)·level⌉`-th smallest score, mapped back from the log scale, so intervals
are asymmetric in percentage points: wider on the upside, as inflation risk is.

*Mondrian* means calibration runs separately per inflation regime at the
origin (<4%, 4-10%, >10%), falling back to the pooled set when a bin has fewer
than 30 scores. A single interval would be too wide for Switzerland and too
narrow for Argentina. Tests check finite-sample coverage on exchangeable data
and that an origin never sees its own future error.

## Results (held-out test window, origins 2009-2024)

| Model | h=1 MAE (pp) | h=1 median | h=1 skill | h=2 MAE (pp) | h=2 median | h=2 skill |
|---|---|---|---|---|---|---|
| **Ensemble (champion)** | **3.46** | **1.25** | **+10.9%** | **4.35** | **1.58** | **+17.3%** |
| Pooled AR(3) | 3.56 | 1.34 | +7.8% | 4.42 | 1.67 | +15.5% |
| LightGBM global | 3.63 | 1.29 | +6.9% | 4.40 | 1.60 | +14.4% |
| LightGBM inflation-only | 3.65 | 1.32 | +5.0% | 4.49 | 1.65 | +11.3% |
| Naive | 3.75 | 1.44 | 0 | 5.21 | 2.00 | 0 |
| Three-year mean | 4.04 | 1.61 | −6.4% | 4.60 | 1.78 | +11.4% |

n = 2,932 (h=1), 2,738 (h=2). Skill = reduction in log-scale MAE vs naive.
RMSE (about 16-21 pp) is driven by a handful of hyperinflation episodes and is
roughly tied across models.

**Significance (two-sided DM, per-year losses).** The ensemble beats naive at both
horizons (p = 0.016, 0.021), the three-year mean at h=1 (p = 0.001), and the
inflation-only LightGBM at h=2 (p = 0.034). Against `pooled_ar` and
`lgbm_global` the gains are consistent in sign but not significant with 15-16
test years. The ensemble's main value over its members is robustness.

**Ablation.** The full LightGBM beats the inflation-only one at both horizons
(+1.9 and +3.1 skill points), so the macro features (money growth,
depreciation, deflator) add real information.

**Intervals.** Test coverage was 79.2% / 95.6% (h=1) and 77.7% / 93.8% (h=2)
against nominal 80% / 95%, and within a few points per regime. Conformal
guarantees *average* coverage, not coverage every year: in 2022 only 43% (h=1)
and 28% (h=2) of outcomes fell inside the 80% band. Coverage recovered to about
90% by 2024-25 as the surge entered the calibration window.

**Explanations.** TreeSHAP for LightGBM (exact, native `pred_contrib`) and exact
linear SHAP `coef·(x − E[x])` for the AR model. The ensemble's attributions are
their mean, because SHAP is linear in the model. A test verifies that
attributions sum to the prediction for every explainable model. Globally:
current inflation ≫ 5-year mean ≈ 2-year lag > 1-year lag ≈ global cycle >
depreciation ≈ deflator ≈ money growth.

**Against the IMF.** For 166 countries' next-year inflation, rank correlation
with the IMF WEO is 0.78, the median absolute difference is 1.0 pp, and the IMF
projection lies inside our 80% interval for 95% of countries. This is a
side-by-side comparison, not a backtest: historical WEO vintages could not be
downloaded by script (403).

## Limitations

* Annual data only. No monthly CPI, policy rates, commodity prices or
  expectations, so shocks are seen a year late.
* Crisis onsets (Zimbabwe 2019-20, South Sudan 2016, Venezuela, Lebanon,
  Argentina 2023-24) produce the largest errors. They are policy and
  balance-of-payments events that annual aggregates do not foresee.
* Intervals assume the next year resembles the last ten. They under-cover in
  regime changes.
* There is no hierarchical or causal structure. This is a forecasting model,
  not a model of what causes inflation.

## Reproduce

```bash
cd ml && PYTHONPATH=src python -m realgrowth_ml train      # ~3.5 min on 4 cores
PYTHONPATH=src:../backend/src pytest                        # 42 tests
```

Everything is seeded (`config.SEED`) and LightGBM runs with
`deterministic=True`. `model_card.json` records a fingerprint of the input
panel.
