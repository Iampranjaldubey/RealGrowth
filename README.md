# RealGrowth

**Is pay actually keeping up with prices?** RealGrowth tracks real wage growth — nominal wage
growth minus inflation — alongside GDP, debt, population and the cost of a healthy diet, across
218 countries. It's a from-scratch rebuild of an earlier prototype, replacing a pandas-in-memory
Flask API and a plain-JS frontend with a tested SQLite warehouse, a typed FastAPI service, and a
TypeScript/React client.

Run it locally with a Python process for the API and Vite for the frontend (see
[Getting started](#getting-started)) — API docs are served at `/docs` and the data-quality report
at `/data-quality` once it's running.

## The finding that shaped this rebuild

The original dataset shipped a file called `real_growth.csv` with no explanation of how it was
computed. Reverse-engineering it showed it is exactly `nominal_wage_growth − inflation`: real wage
growth. That's a genuinely interesting question — it just needed the data behind it to be
trustworthy. It wasn't, quite: an upstream notebook filled missing values by scaling the world
average, which invented wage swings with no matching price movement (Spain: +147% in 2022 against
8.4% inflation; the Netherlands, Singapore, and roughly 80% of countries have at least one such
artefact). The ETL now **rejects those specific transitions** rather than plotting them, and
**publishes what it rejected** at `/api/v1/meta/quality` and the `/data-quality` page — see
[Data quality](#data-quality) below.

## Architecture

```
data/raw/*.csv  +  data/reference/countries.csv
        │
        ▼
backend/src/realgrowth/etl/   (stdlib only: csv + sqlite3)
  registry.py   → resolve 283 raw country labels to ISO-3166 alpha-3
  transform.py  → wide CSV → tidy observations, columns addressed by header label
  derive.py     → nominal/real wage growth, population, urbanisation rate
  quality.py    → coverage + rejected-value report
  warehouse.py  → SQLite schema + bulk load
        │
        ▼
data/realgrowth.db   (~2.4 MB, 26k+ observations, rebuilt by `python -m realgrowth.etl`)
        │
        ▼
backend/src/realgrowth/   (FastAPI + Pydantic, thin routers over a tested repository)
  repository.py → every query as SQL
  stats.py      → Pearson r, OLS regression, p-value, 95% CI (stdlib, no numpy)
  api/          → /api/v1/{indicators,countries,regions,correlation,meta}
        │
        ▼
frontend/src/   (React 19 + TypeScript + TanStack Query)
  api/          → typed client + query hooks
  pages/        → HomePage, IndicatorExplorerPage, CorrelationPage, DataQualityPage
```

Design choices worth calling out:

- **No pandas.** The dataset is ~4k rows of wide CSV; a stdlib `csv`/`sqlite3` pipeline is fully
  unit-testable anywhere Python runs and adds no dependency weight. `backend/tests/` has 130+ tests
  that need nothing beyond the standard library, plus an `httpx`-based suite for the HTTP layer.
- **Countries are ISO3, not strings.** The seven raw sources disagree on country names ("Korea,
  Rep." vs "South Korea", "Turkiye" vs "Turkey", one leading-unnamed-index-column CSV that used to
  make `/api/growth/<country>` return the country's own name as a data point). Every join now goes
  through `data/reference/countries.csv`, a curated registry mapping all 283 raw labels to ISO3.
- **Missing data is absent, not zero.** No endpoint encodes "no observation" as `0` — a pattern
  that used to make Afghanistan's real wage growth for 2021–22 equal the negated inflation rate,
  because nominal wage growth had been zero-filled for years with no wage data at all.
- **The correlation explorer reports a full statistical picture** — n, r, R², a regression line, a
  two-sided p-value and a 95% CI via Fisher's z-transform — not a bare coefficient, which invites
  reading noise (r = 0.9 on four points) as signal.

## Data quality

Four of the seven sources (`avg_wage`, `inflation_rate`, `debt_to_gdp`, `healthy_diet_cost`) were
originally filled at missing cells by an ILOSTAT/World-Bank-derived notebook using a "scale the
world average by this country's average ratio" heuristic — a reasonable-sounding fallback that
occasionally invents values indistinguishable from real ones. This rebuild can't undo that
imputation, but it does three things instead of pretending the data is clean:

1. **Rejects implausible wage-growth transitions.** A year-on-year wage move greater than ±40%
   with no matching inflation is treated as an imputation artefact and dropped — see
   `is_implausible_growth` in `backend/src/realgrowth/etl/derive.py`. Genuine crises (Zimbabwe,
   Lebanon) survive because inflation there corroborates the move.
2. **Flags the series it had to prune.** Every affected country/indicator pair gets a
   `series_flags` row served alongside its data (`CountrySeries.flag` in the API), so the frontend
   can show the caveat next to the chart it applies to, not in a README nobody reads first.
3. **Publishes the full report.** `python -m realgrowth.etl --report` and
   `GET /api/v1/meta/quality` expose coverage per indicator, every rejected value, and unresolved
   entities (currently zero — see `backend/tests/test_registry.py`'s exhaustive check against the
   live raw files).

## Data sources

| Indicator | Source |
|---|---|
| GDP per capita | [World Bank Open Data](https://data.worldbank.org/indicator/NY.GDP.PCAP.CD) |
| Inflation rate | [World Bank Open Data](https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG) |
| Average wage | ILOSTAT, converted to USD via World Bank exchange rates |
| Debt-to-GDP, urban/rural population | [Macrotrends](https://www.macrotrends.net/global-metrics/countries) |
| Cost of a healthy diet | [Our World in Data / FAO](https://ourworldindata.org/grapher/cost-healthy-diet) |

`real_wage_growth`, `nominal_wage_growth`, `population` and `urbanisation_rate` are derived from
the above (see the table above's four rows) rather than sourced directly — the derivations live in
`backend/src/realgrowth/etl/derive.py`. `notebooks/` contains the original scraping/cleaning
notebooks that produced the raw CSVs, kept for provenance with their outputs stripped.

## Stack

| Layer | Technology |
|---|---|
| Data warehouse | SQLite, built by a stdlib Python ETL |
| API | FastAPI, Pydantic v2, slowapi (rate limiting), uvicorn |
| Frontend | React 19, TypeScript (strict), TanStack Query, React Router 7, Chart.js |
| Testing | pytest + httpx (backend, 130+ tests), Vitest + React Testing Library (frontend) |
| CI | GitHub Actions — lint, type-check and test every push ([workflow](.github/workflows/ci.yml)) |
| Deploy | Render Blueprint (`render.yaml`) — a Python web service + a static site, free tier, no containers |

## Getting started

### Native (recommended for local dev)

```bash
# 1. Build the warehouse (stdlib only, no venv needed for this step)
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt
PYTHONPATH=backend/src python -m realgrowth.etl   # writes data/realgrowth.db

# 2. Run the API
PYTHONPATH=backend/src REALGROWTH_DATABASE_PATH=data/realgrowth.db \
  uvicorn realgrowth.main:app --reload

# 3. Run the frontend (separate terminal)
cd frontend
npm install
VITE_API_URL=http://localhost:8000/api npm run dev
```

### Tests

```bash
# Backend — 130+ tests, most need nothing beyond the standard library
cd backend && pip install -r requirements-dev.txt
pytest                       # full suite
ruff check src tests         # lint
mypy src                     # type-check

# Frontend
cd frontend && npm install
npm run test
npm run typecheck
```

## Deployment

No Docker required. The repo ships a [Render](https://render.com) Blueprint
(`render.yaml`) that stands up both services on the free tier:

1. Push this repo to GitHub.
2. In Render: **New > Blueprint**, select the repo, and apply `render.yaml`.
3. Render prompts for the two cross-service URLs it can't know until the
   services exist. Set them and redeploy:
   - `realgrowth-api` → `REALGROWTH_CORS_ORIGINS` = the web URL, e.g.
     `https://realgrowth-web.onrender.com`
   - `realgrowth-web` → `VITE_API_URL` = the API URL + `/api`, e.g.
     `https://realgrowth-api.onrender.com/api`

The API builds its SQLite warehouse from the committed CSVs at deploy time
(`python -m realgrowth.etl --strict`), so there's no database to provision or
migrate; the frontend is a static build served over a CDN.

The same two moving parts deploy on any host: a Python web process
(`uvicorn realgrowth.main:app --host 0.0.0.0 --port $PORT`, with the ETL run
once at build time) and a static `frontend/dist` folder. Point the frontend at
the API with `VITE_API_URL`, and restrict the API's CORS to the frontend origin
with `REALGROWTH_CORS_ORIGINS`.

## API overview

Full interactive documentation (OpenAPI/Swagger) is served at `/docs` by the running API. Routes,
summarised:

| Route | Purpose |
|---|---|
| `GET /api/v1/indicators` | Every indicator, with its real min/max year and country count |
| `GET /api/v1/indicators/{id}/series?countries=USA,IND` | Time series for one or more countries |
| `GET /api/v1/indicators/{id}/snapshot?year=&region=&min_population=` | Ranked cross-country snapshot for one year |
| `GET /api/v1/countries?indicator=` | Countries, optionally restricted to those with data for `indicator` |
| `GET /api/v1/countries/{iso3}` | Latest value of every indicator for one country |
| `GET /api/v1/correlation/time-series?country=&x=&y=` | Correlate two indicators over years, within one country |
| `GET /api/v1/correlation/cross-section?x=&y=&year=` | Correlate two indicators across countries, within one year |
| `GET /api/v1/meta/quality` | The ETL's data-quality report |

Every error response has the same shape: `{"error": str, "detail": str | null, "status": int}`.

## Project structure

```
RealGrowth/
├── data/
│   ├── raw/                    source CSVs (World Bank, Macrotrends, OWID, ILOSTAT)
│   └── reference/countries.csv curated ISO3 registry (283 raw labels → 218 countries + aggregates)
├── backend/
│   ├── src/realgrowth/
│   │   ├── etl/                registry, transform, derive, quality, warehouse, pipeline
│   │   ├── api/                FastAPI routers (indicators, countries, regions, correlation, meta)
│   │   ├── repository.py       every query, as SQL
│   │   ├── stats.py            Pearson r / OLS / significance, stdlib only
│   │   ├── main.py, config.py, db.py, schemas.py
│   └── tests/                  130+ tests: ETL, repository, stats, API
├── frontend/
│   ├── src/
│   │   ├── api/                 typed client (client.ts) + TanStack Query hooks (queries.ts)
│   │   ├── components/          charts/, layout/, ui/
│   │   ├── pages/                HomePage, IndicatorExplorerPage, CorrelationPage, DataQualityPage
│   │   └── lib/                  formatters, chart theme, URL-driven state
│   └── .env.example             VITE_API_URL template (copy to .env for local dev)
├── notebooks/                    original scraping/cleaning notebooks (outputs stripped)
├── .github/workflows/ci.yml      lint + type-check + test, every push
└── render.yaml                   Render Blueprint: Python API + static site (no Docker)
```

## What changed from the previous version

This is a ground-up rebuild, not an incremental update. In short: the data layer moved from
pandas-in-memory to a tested SQLite warehouse; the API moved from Flask to typed FastAPI with a
consistent error contract; the frontend moved from plain JS to TypeScript with nine near-duplicate
pages collapsed into one metadata-driven page; and CI and a real test suite exist for the first
time. Commit history has the full detail per layer.

## License

Code is licensed under the [MIT License](LICENSE). The underlying economic data belongs to its
original publishers (World Bank, Macrotrends, Our World in Data / FAO, ILOSTAT) — see
[Data sources](#data-sources) — and is used here for non-commercial, educational purposes; refer to
each publisher's own terms before reuse.
