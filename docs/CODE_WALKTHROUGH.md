# Code walkthrough

A reading order for someone new to the codebase. Each step names the files to
open and what to look for.

## 1. Follow one number end to end (30 min)

Pick "India's forecast inflation for 2026" and trace it back.

1. **`backend/src/realgrowth/ingest/connectors.py` → `fetch_worldbank`.** Pages
   through `api.worldbank.org/v2/country/all/indicator/FP.CPI.TOTL.ZG`, maps
   codes to the registry, and drops aggregates the registry does not know.
   `http.py` adds retries with exponential backoff, and `snapshot.py` writes
   `data/raw/api/inflation_rate.csv` with a SHA-256 in `manifest.json`.
2. **`backend/src/realgrowth/etl/transform.py` → `load_api_source`.** Reads the
   snapshot and range-checks every value against `sources.INDICATORS`.
3. **`etl/pipeline.py` → `run_etl`.** Orchestrates everything and writes
   `data/realgrowth.db`.
4. **`ml/src/realgrowth_ml/data.py` → `load_panel`.** The ML side reads the
   same warehouse.
5. **`features.py` → `build_feature_frame`.** One row per (country, origin
   year). Note `shift(k, axis=1)`: lags shift values *forward* in time, so a
   feature can only see the past.
6. **`backtest.py` → `training_mask`.** The one-line rule that prevents
   leakage: `year + horizon <= origin`.
7. **`models.py` → `Ensemble`**, then **`conformal.py` → `forward_intervals`**,
   then **`forecasting.py` → `forward_forecasts`**, which writes
   `data/models/inflation/forecasts.csv`.
8. **`backend/src/realgrowth/etl/artifacts.py` → `load_forecasting_task`.**
   Loads that CSV into the `forecasts` table.
9. **`repository.py` → `get_country_forecast`**, served by
   **`api/forecasts.py`**.
10. **`frontend/src/pages/ForecastPage.tsx`** calls `useCountryForecast`
    (`api/queries.ts`), and **`lib/forecast.ts` → `buildForecastChartData`**
    shapes it for **`components/charts/ForecastChart.tsx`**.

## 2. Module map

### `backend/src/realgrowth/`

| Module | Responsibility |
|---|---|
| `ingest/http.py` | urllib GET, retries on 429/5xx only, identifying User-Agent, injectable transport for tests |
| `ingest/catalog.py` | Which series come from which API |
| `ingest/connectors.py` | World Bank (paginated JSON), IMF DataMapper (history/projection split), OWID (CSV) |
| `ingest/snapshot.py` | Long CSV + manifest; `verify()` detects hand edits |
| `etl/registry.py` | Name → ISO3, strict, no fuzzy matching |
| `etl/sources.py` | Indicator catalogue: units, ranges, provenance, categories |
| `etl/transform.py` | Wide legacy CSV and long API snapshot → `Observation`s |
| `etl/derive.py` | LCU wage → nominal growth (with imputed-input and plausibility filters) → real growth |
| `etl/quality.py` | Coverage and issue report |
| `etl/warehouse.py` | Schema v2 and bulk inserts |
| `etl/artifacts.py` | Loads model outputs, the IMF benchmark and imputation labels |
| `repository.py` | Every query the API can run, as plain SQL |
| `stats.py` | Pearson, OLS, p-values, Fisher-z CI (stdlib) |
| `api/*.py` | Thin FastAPI routers; `schemas.py` defines every response |

### `ml/src/realgrowth_ml/`

| Module | Responsibility |
|---|---|
| `config.py` | Every experiment constant (windows, seeds, bins) |
| `features.py` | `slog`, feature catalogue, leakage-safe feature frame |
| `models.py` | Baselines, LightGBM, ensemble; SHAP for each |
| `backtest.py` | Rolling-origin backtest |
| `conformal.py` | Mondrian split-conformal intervals (backtest and forward) |
| `metrics.py` | MAE / median / log-MAE, skill, coverage, Diebold-Mariano |
| `forecasting.py` | The experiment: tune → backtest → intervals → select → refit → card |
| `anomaly.py` | Label reconstruction, detector features, detector comparison |
| `__main__.py` | `python -m realgrowth_ml {train,anomaly,all}` |

## 3. Tests worth reading

| Test | What it proves |
|---|---|
| `ml/tests/test_features.py::TestNoLookAhead` | Scrambling the future cannot change any past feature |
| `ml/tests/test_forecasting.py::TestTrainingMask` | No training target is after the origin, at either horizon |
| `ml/tests/test_forecasting.py::TestConformal` | Nominal coverage on exchangeable data; no peeking at own error |
| `ml/tests/test_forecasting.py::test_contributions_sum_to_prediction` | SHAP local accuracy for every model |
| `ml/tests/test_anomaly.py::TestReconstruction` | Exact recovery of simulated imputation |
| `backend/tests/test_derive.py::test_depreciation_does_not_look_like_a_pay_cut` | Why wages are computed in local currency |
| `backend/tests/test_ingest.py` | Retry policy and every connector, against recorded payload shapes, offline |
| `backend/tests/test_pipeline.py` | End to end on the real committed data |

## 4. Running everything

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt -r ml/requirements.txt

(cd backend && pytest && ruff check src tests && mypy src)            # 198 tests
(cd ml && PYTHONPATH=src:../backend/src pytest && ruff check src tests scripts)  # 42 tests
(cd frontend && npm install && npm run test -- --run && npm run typecheck && npm run build)  # 50 tests

python ml/scripts/build_notebooks.py   # regenerate and execute the three analysis notebooks
```

## 5. Extending

* **New World Bank indicator:** add a `SeriesSpec` in `ingest/catalog.py` and an
  `Indicator` in `etl/sources.py`, then add the id to `API_INDICATORS`. Run
  ingest and rebuild. `test_every_snapshot_series_feeds_an_indicator_or_the_benchmark`
  keeps the two catalogues in sync.
* **New forecasting model:** add a `ModelSpec` to `models.MODEL_SPECS`. It is
  backtested, scored, significance-tested and listed in the card automatically.
* **New forecast target:** write another task directory with the same
  artefact contract. `etl/artifacts.load_all` picks it up.
