# RealGrowth frontend

React 19 + TypeScript SPA for the RealGrowth API. See the [root README](../README.md) for the
full project overview, architecture and screenshots.

## Stack

- **React 19** + **TypeScript** (strict mode: `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`)
- **TanStack Query** for data fetching — caching, request de-duplication and cancellation
- **React Router 7** with URL-driven state (year/country/tab selections live in the query string,
  so every view is bookmarkable and the back button works)
- **Chart.js** via `react-chartjs-2` for line/bar/scatter charts
- **Vite** + **Vitest** + **React Testing Library**

## Commands

```bash
npm install
npm run dev         # local dev server, expects the API at VITE_API_URL (default /api)
npm run build        # tsc -b && vite build
npm run test          # vitest
npm run test:coverage
npm run lint
npm run typecheck
```

No `package-lock.json` is committed: this project was built in a sandbox with no npm registry
access, so the lockfile is generated fresh by CI (`npm install`) rather than hand-maintained out of
sync with what actually resolves. Run `npm install` locally once to generate your own.

## Structure

```
src/
  api/          typed fetch client (client.ts) + TanStack Query hooks (queries.ts)
  components/
    charts/     Chart.js wrappers: TimeSeriesChart, RankChart, ScatterChart
    layout/     Sidebar
    ui/         ChartCard, StatCard, CountrySelect, YearSlider, RankList, ...
  context/      ThemeContext (dark/light)
  lib/          formatters, chart theme, useUrlState
  pages/        HomePage, IndicatorExplorerPage, CorrelationPage, DataQualityPage
  types/        API response types, mirroring backend/src/realgrowth/schemas.py
```

`IndicatorExplorerPage` is a single generic page driven by `/api/v1/indicators/:id` metadata,
replacing seven near-identical page components from the previous version of this app (GDP,
Inflation, Wages, Debt, Growth, Population, Food Prices — each ~60–200 lines differing only in
which endpoint they called and a hardcoded year range).

## Notable decisions

- **No world map.** The previous map (`react-simple-maps`) doesn't declare React 19 support, loads
  its topology from an external CDN at runtime with no offline fallback, and joined country data by
  English display name against the map's own English names — which is why the United States never
  rendered a value. `RankList`/`RankChart` show the same "who's highest" information as a ranked bar
  list, with no map library, no CDN dependency, and a real ISO3 join. Re-adding a real map — an
  ISO3-keyed SVG shipped in the repo — is a natural next step, not a rejected idea.
- **Data-quality page.** Several upstream sources contain imputed values (see the root README).
  `/data-quality` renders the ETL's quality report directly rather than leaving that caveat only in
  documentation.
