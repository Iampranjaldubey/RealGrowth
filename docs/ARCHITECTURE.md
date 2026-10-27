# Architecture

RealGrowth is four small programs connected by files, not by a running service
mesh. Each stage reads committed files and writes files, so every number the
website shows can be traced back to a data snapshot and a model card.

```
 ┌───────────────────────────────────────────────────────────────────────────┐
 │ 1. INGEST            backend/src/realgrowth/ingest/        (stdlib only)  │
 │    World Bank WDI API ─┐                                                  │
 │    IMF DataMapper API ─┼─► data/raw/api/<series>.csv + manifest.json       │
 │    Our World in Data  ─┘   (iso3,year,value; URL, fetch time, SHA-256)     │
 └───────────────────────────────────────────────────────────────────────────┘
                 │                         data/raw/avg_wage.csv (legacy ILOSTAT extract)
                 ▼                                         │
 ┌───────────────────────────────────────────────────────────────────────────┐
 │ 2. ETL               backend/src/realgrowth/etl/           (stdlib only)  │
 │    registry → transform → derive → quality → warehouse → artifacts         │
 │                                      ▲                         ▲          │
 │                     exact imputation │labels        model files│          │
 │                                      │                         │          │
 │                              ──► data/realgrowth.db (SQLite, ~23 MB)       │
 └───────────────────────────────────────────────────────────────────────────┘
                 │                                         ▲
                 ▼                                         │
 ┌───────────────────────────────────────────────────────────────────────────┐
 │ 3. ML (offline)      ml/src/realgrowth_ml/   (pandas, scikit-learn, LightGBM)│
 │    features → backtest → conformal → champion → forecasts + TreeSHAP       │
 │    anomaly: forensic labels → detectors → scores                           │
 │                              ──► data/models/{inflation,anomaly}/          │
 └───────────────────────────────────────────────────────────────────────────┘
                 │  (ETL is re-run so the warehouse contains the models)
                 ▼
 ┌───────────────────────────────────────────────────────────────────────────┐
 │ 4. SERVE   FastAPI (backend/src/realgrowth/)  ──►  React (frontend/src/)    │
 │    read-only SQL over the warehouse               typed client, TanStack   │
 └───────────────────────────────────────────────────────────────────────────┘
```

## Why it is shaped like this

**Fetching is separate from building.** Live APIs change: the World Bank revises
history, the IMF publishes a new vintage twice a year, and APIs go down. The
ingest step freezes what each API returned into a snapshot with checksums
(`python -m realgrowth.ingest --verify` checks them). The ETL only reads
snapshots. As a result builds are reproducible, deploys never depend on a third
party being up, and `git diff data/raw/api/` shows exactly what a publisher
revised between two refreshes.

**The data layer has no third-party dependencies.** Ingest and ETL use only
`urllib`, `csv` and `sqlite3`. They run on the deploy host and in CI with nothing
installed, and the whole data layer is unit-testable in milliseconds.

**Training is offline, serving is batch.** Models are trained by the `ml/`
package, which needs the scientific Python stack. The API never imports it. The
two meet at a plain-file contract in `data/models/` (see
[MODEL_CARD.md](MODEL_CARD.md#artefact-contract)), which the stdlib ETL loads into
the warehouse. This is the *batch prediction* pattern: forecasts are precomputed
and versioned with the data that produced them. For annual data that changes a
few times a year it is simpler, cheaper and more auditable than an online model
server, and API latency stays at SQLite speed (a few milliseconds per request locally).

**One warehouse, rebuilt from scratch.** `data/realgrowth.db` is a derived
artefact and is never migrated. Every build deletes it and recreates it, which
removes a whole class of state bugs.

## Data flow in one refresh

```bash
python -m realgrowth.ingest          # 1. snapshot every API series      (~1 min)
python -m realgrowth.etl             # 2. build the warehouse            (~5 s)
python -m realgrowth_ml all          # 3. labels, detectors, forecasting (~3.5 min)
python -m realgrowth.etl --strict    # 4. rebuild including model outputs
```

Step 3 reads the warehouse from step 2, and step 4 reads both the snapshot and
the model outputs. The imputation labels written in step 3 depend only on wage
levels and exchange rates, never on anything they filter, so steps 2-4 are
deterministic rather than circular. On a fresh clone the committed
`data/models/` already exists, so steps 2 and 4 give the same result.

`.github/workflows/refresh-data.yml` runs these four steps weekly and opens a pull
request with the diff, so a human reviews every data and model change before it
ships.

## Warehouse schema (v2)

| Table | Grain | Written by |
|---|---|---|
| `countries` | ISO3 | registry (`data/reference/countries.csv`) |
| `indicators` | indicator id | `etl/sources.py` catalogue, plus year span and country count |
| `observations` | indicator × country × year | ETL (sparse: no row means no data) |
| `series_flags` | indicator × country × flag | `etl/derive.py` (caveats served with the data) |
| `models` | model id | `etl/artifacts.py` from `model_card.json`, plus the IMF benchmark |
| `forecasts` | model × country × target year | `forecasts.csv` and the IMF snapshot |
| `backtest_predictions` | model × country × horizon × target year | `backtest.csv` |
| `forecast_contributions` | model × country × target year × feature | `contributions.csv` (TreeSHAP) |
| `anomaly_scores` | indicator × country × year | `anomaly/scores.csv` |
| `etl_metadata` | key | quality report, snapshot manifest, model cards, build time |

"Missing" is always the absence of a row, never `0` or `NULL` in a value column.
The original project showed fictional collapses because it encoded gaps as zero.

## API surface

| Route | Purpose |
|---|---|
| `GET /api/v1/indicators[/{id}]` | Catalogue with provenance and real year coverage |
| `GET /api/v1/indicators/{id}/series?countries=` | Time series, with any data-quality flag |
| `GET /api/v1/indicators/{id}/snapshot?year=` | Ranked cross-section for one year |
| `GET /api/v1/countries[/{iso3}]` | Countries; latest value of every indicator |
| `GET /api/v1/correlation/{time-series,cross-section}` | r, R², OLS, p-value, Fisher-z CI |
| `GET /api/v1/forecasts/{iso3}` | History, forecasts with 80/95% intervals, IMF, backtest, drivers |
| `GET /api/v1/forecasts?horizon=` | Champion forecast for every country |
| `GET /api/v1/models`, `/models/{task}/card` | Model list and full model cards |
| `GET /api/v1/anomalies?country=` | Per-cell probability of being an imputation artefact |
| `GET /api/v1/tools/purchasing-power` | CPI-based "what is this amount worth in year X" |
| `GET /api/v1/meta/{health,quality,warehouse,sources}` | Health, quality report, build info, snapshot provenance |

Every error has the shape `{"error", "detail", "status"}`. Interactive docs are
served at `/docs`. The API is read-only and unauthenticated by design (public
open data), rate-limited per IP by slowapi, and CORS is restricted to the
frontend origin via `REALGROWTH_CORS_ORIGINS` in production.

## Frontend

React 19 + TypeScript (strict) + TanStack Query. Pages:

* **Dashboard**: live headline numbers.
* **Inflation outlook** (`/forecasts`): fan chart, IMF comparison, SHAP drivers,
  and the country's own backtest.
* **Purchasing power** (`/purchasing-power`): the calculator. Projected years
  are labelled as projections.
* **Indicator explorer** (`/indicators/:id`): rankings and multi-country
  comparison for all 24 indicators.
* **Correlation explorer**: with significance and confidence intervals.
* **Models & methodology** (`/models`): the model cards, rendered.
* **Data quality**: the ETL's quality report.

All view state lives in the URL, so every view is a shareable link.
