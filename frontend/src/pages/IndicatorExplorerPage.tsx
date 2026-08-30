import { useParams } from "react-router-dom";
import { ChartCard } from "@/components/ui/ChartCard";
import { CountrySelect } from "@/components/ui/CountrySelect";
import { YearSlider } from "@/components/ui/YearSlider";
import { RankChart } from "@/components/charts/RankChart";
import { TimeSeriesChart } from "@/components/charts/TimeSeriesChart";
import { QualityBanner } from "@/components/ui/QualityBanner";
import { useIndicator, useSeries, useSnapshot } from "@/api/queries";
import { useUrlNumberState, useUrlState } from "@/lib/useUrlState";
import { formatByUnit } from "@/lib/formatters";

/**
 * One page, driven entirely by the indicator's own metadata, replacing seven
 * near-identical page components (GDP.jsx, Inflation.jsx, Wages.jsx, Debt.jsx,
 * Growth.jsx, Population.jsx, FoodPrices.jsx — each ~60-200 lines differing
 * only in which `api.*` method they called, their title, and a hardcoded
 * year range). Two tabs cover what those pages did between them: "Rankings"
 * (a snapshot for one year, sortable) and "Compare countries" (multi-country
 * time series) — both driven by /indicators/:id metadata, so the year slider
 * bounds and available countries always match what the data actually covers.
 *
 * Selections (tab, year, countries) live in the URL via useUrlState, so a
 * view is shareable/bookmarkable — the old app kept all of this in local
 * `useState`, so the back button did nothing and no view had a stable link.
 */
export function IndicatorExplorerPage() {
  const { indicatorId = "" } = useParams<{ indicatorId: string }>();
  const indicatorQuery = useIndicator(indicatorId);
  const indicator = indicatorQuery.data;

  const [tab, setTab] = useUrlState("tab", "rankings");
  const [year, setYear] = useUrlNumberState("year", indicator?.max_year ?? new Date().getFullYear());
  const [countryA, setCountryA] = useUrlState("a", "USA");
  const [countryB, setCountryB] = useUrlState("b", "CHN");

  const effectiveYear = clamp(year, indicator?.min_year, indicator?.max_year, indicator?.max_year ?? year);

  const snapshot = useSnapshot(tab === "rankings" ? indicatorId : undefined, {
    year: effectiveYear,
    order: (indicator?.direction ?? 1) >= 0 ? "desc" : "asc",
    limit: 15,
  });
  const compareSeries = useSeries(
    tab === "compare" ? indicatorId : undefined,
    [countryA, countryB].filter(Boolean),
  );

  if (indicatorQuery.isLoading) {
    return <p>Loading indicator…</p>;
  }
  if (indicatorQuery.isError || !indicator) {
    return <p>Could not load this indicator.</p>;
  }

  const formatter = (value: number) => formatByUnit(value, indicator.unit_symbol, indicator.decimals);
  const flaggedSeries = compareSeries.data?.series.filter((s) => s.flag) ?? [];

  return (
    <div>
      <div className="page-header">
        <h1>{indicator.name}</h1>
        <p>{indicator.description}</p>
      </div>

      <div className="tab-bar" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "rankings"}
          className={`tab-btn ${tab === "rankings" ? "active" : ""}`}
          onClick={() => setTab("rankings")}
        >
          Rankings
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "compare"}
          className={`tab-btn ${tab === "compare" ? "active" : ""}`}
          onClick={() => setTab("compare")}
        >
          Compare countries
        </button>
      </div>

      {tab === "rankings" && indicator.min_year !== null && indicator.max_year !== null && (
        <>
          <div className="controls-row glass-card">
            <YearSlider min={indicator.min_year} max={indicator.max_year} value={effectiveYear} onChange={setYear} />
          </div>
          <ChartCard
            title={`Top 15 — ${indicator.name} (${snapshot.data?.year ?? effectiveYear})`}
            subtitle={`${indicator.unit} · Source: ${indicator.source}`}
            loading={snapshot.isLoading}
            error={snapshot.error?.message}
          >
            {snapshot.data && (
              <RankChart values={snapshot.data.values} valueFormatter={formatter} limit={15} />
            )}
          </ChartCard>
        </>
      )}

      {tab === "compare" && (
        <>
          <div className="controls-row glass-card">
            <CountrySelect id="country-a" indicator={indicatorId} value={countryA} onChange={setCountryA} label="Country A" />
            <CountrySelect id="country-b" indicator={indicatorId} value={countryB} onChange={setCountryB} label="Country B" />
          </div>

          {flaggedSeries.map((series) => (
            <QualityBanner
              key={series.iso3}
              message={`${series.country}: ${series.flag}`}
            />
          ))}

          <ChartCard
            title={`${indicator.name} over time`}
            subtitle={indicator.unit}
            loading={compareSeries.isLoading}
            error={compareSeries.error?.message}
          >
            {compareSeries.data && (
              <TimeSeriesChart series={compareSeries.data.series} valueFormatter={formatter} />
            )}
          </ChartCard>
        </>
      )}
    </div>
  );
}

function clamp(value: number, min: number | null | undefined, max: number | null | undefined, fallback: number): number {
  if (min === null || min === undefined || max === null || max === undefined) return fallback;
  return Math.min(max, Math.max(min, value));
}
