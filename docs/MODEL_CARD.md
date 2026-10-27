# Model card: RealGrowth inflation forecaster

The machine-readable card (`data/models/inflation/model_card.json`, served at
`/api/v1/models/inflation/card`) is regenerated on every training run and is the
source of truth. This page summarises it for readers.

| | |
|---|---|
| **Task** | National headline CPI inflation, 1 and 2 years ahead, annual |
| **Champion** | Equal-weight ensemble of a pooled ridge AR(3) and a global LightGBM model |
| **Training data** | 7,393 country-years, 193 countries, origins 1980-2025 (World Bank WDI, IMF WEO) |
| **Outputs** | Point forecast, 80% and 95% conformal intervals, TreeSHAP attributions |
| **Coverage** | 176 countries with a recent enough inflation observation (≤1 year stale) |
| **Version** | `realgrowth_ml` 1.0.0, seed 20261027, deterministic LightGBM |

## Intended use

Indicative, transparent baseline forecasts for public-interest analysis: the
Inflation Outlook page, and extending the purchasing-power calculator one year
past the latest CPI release. Projected values are always labelled as
projections.

**Not intended for** monetary-policy, investment or wage-bargaining decisions,
or for countries with fewer than three years of recent inflation history.

## Performance (held-out test, origins 2009-2024)

| | h = 1 | h = 2 |
|---|---|---|
| MAE / median abs. error | 3.46 / 1.25 pp | 4.35 / 1.58 pp |
| Skill vs naive (log-scale MAE) | +10.9% (DM p = 0.016) | +17.3% (DM p = 0.021) |
| 80% interval coverage | 79.2% | 77.7% |
| 95% interval coverage | 95.6% | 93.8% |
| Median 80% interval width | 6.0 pp | 7.0 pp |

By inflation regime at origin (h=1): <4%, median error 0.96 pp, coverage 77%;
4-10%, 1.45 pp, 83%; >10%, 4.70 pp, 81%.

## Known failure modes

* **Regime changes.** 80% coverage fell to 43% (h=1) and 28% (h=2) in 2022.
* **Crisis onsets.** The largest errors are Zimbabwe 2020 (+502 pp), South
  Sudan 2016, Sudan 2021, Venezuela 2016 and Lebanon 2023.
* **Bias.** 56% of test forecasts under-predicted. Inflation surprises skew
  upward.

## Ethical and practical considerations

Forecasts for small or data-poor economies rest on fewer observations. Their
intervals reflect the regime, not the data quantity. The site shows the
country's own backtest next to every forecast so readers can judge the
track record for the country they care about.

## Artefact contract

Training writes, and the stdlib ETL reads:

| File | Columns |
|---|---|
| `model_card.json` | `task, indicator_id, champion, models[{id,name,kind,description,card}], metrics[], significance[], regimes[], yearly_errors[], features[], global_importance[], design{}, limitations[], …` |
| `forecasts.csv` | `model_id, iso3, origin_year, target_year, horizon, point, lower_80, upper_80, lower_95, upper_95` |
| `backtest.csv` | `model_id, iso3, origin_year, target_year, horizon, actual, point, lower_80, upper_80` |
| `contributions.csv` | `model_id, iso3, target_year, feature, feature_value, contribution` |
| `anomaly/scores.csv` | `indicator_id, iso3, year, score, is_flagged` |
| `anomaly/labelled_cells.csv` | `iso3, year, label, rule, robust_z, isolation_forest, lgbm` |
| `anomaly/model_card.json` | `labels{}, detectors{}, base_rate, feature_importance_gain[], world_index{}` |

Any new task directory with a `model_card.json` is loaded automatically.
