import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import { StatCard } from "@/components/ui/StatCard";
import { ChartCard } from "@/components/ui/ChartCard";
import { TimeSeriesChart } from "@/components/charts/TimeSeriesChart";
import { useSeries, useSnapshot } from "@/api/queries";
import { formatByUnit, formatPercent } from "@/lib/formatters";

const QUICK_LINKS = [
  { path: "/correlation", label: "Correlation Explorer", icon: "🔬", color: "secondary" as const },
  { path: "/indicators/real_wage_growth", label: "Real Wage Growth", icon: "🚀", color: "primary" as const },
  { path: "/indicators/inflation_rate", label: "Inflation Trends", icon: "📈", color: "warning" as const },
  { path: "/indicators/debt_to_gdp", label: "Debt Rankings", icon: "🏦", color: "danger" as const },
];

/**
 * The previous Home page displayed `globalInflation: 8.7` and
 * `globalGrowth: 3.2` as literal constants with comments admitting they were
 * "2022 estimates" — the first screen a visitor saw was not real data. Every
 * number here is a live snapshot/series query against the current warehouse.
 */
export function HomePage() {
  const gdpSnapshot = useSnapshot("gdp_per_capita", { order: "desc", limit: 10 });
  const realWageSnapshot = useSnapshot("real_wage_growth", { order: "desc", limit: 200 });
  const inflationSnapshot = useSnapshot("inflation_rate", { order: "desc", limit: 200 });
  const usSeries = useSeries("real_wage_growth", ["USA"]);

  const avgTop10Gdp = average(gdpSnapshot.data?.values.map((v) => v.value));
  const medianInflation = median(inflationSnapshot.data?.values.map((v) => v.value));
  const medianRealWageGrowth = median(realWageSnapshot.data?.values.map((v) => v.value));

  const loading = gdpSnapshot.isLoading || inflationSnapshot.isLoading || realWageSnapshot.isLoading;

  return (
    <div>
      <div className="page-header">
        <h1>Global Economic Overview</h1>
        <p>
          Real wage growth, inflation, GDP and more across {gdpSnapshot.data?.indicator.country_count ?? "218"}{" "}
          countries.
        </p>
      </div>

      <div className="stats-grid stagger-children">
        <StatCard
          title={`Avg. GDP Per Capita (Top 10, ${gdpSnapshot.data?.year ?? ""})`}
          value={formatByUnit(avgTop10Gdp, "$", 0)}
          icon="💰"
          color="primary"
          loading={loading}
        />
        <StatCard
          title={`Median Inflation (${inflationSnapshot.data?.year ?? ""})`}
          value={formatPercent(medianInflation)}
          icon="📈"
          color="warning"
          loading={loading}
        />
        <StatCard
          title={`Median Real Wage Growth (${realWageSnapshot.data?.year ?? ""})`}
          value={formatPercent(medianRealWageGrowth)}
          icon="🚀"
          color={medianRealWageGrowth !== undefined && medianRealWageGrowth < 0 ? "danger" : "tertiary"}
          loading={loading}
        />
      </div>

      <div className="two-col-grid">
        <ChartCard
          title="United States — Real Wage Growth"
          subtitle="Wage growth minus inflation, year over year"
          loading={usSeries.isLoading}
          error={usSeries.error?.message}
        >
          {usSeries.data && (
            <TimeSeriesChart series={usSeries.data.series} valueFormatter={(v) => formatPercent(v)} showLegend={false} />
          )}
        </ChartCard>

        <div className="glass-card">
          <h3 style={{ marginBottom: 16 }}>Quick navigation</h3>
          <div className="link-grid">
            {QUICK_LINKS.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                className="glass-card glass-card--interactive nav-tile"
                style={{ "--tile-color": `var(--accent-${link.color})` } as CSSProperties}
              >
                <span className="nav-tile__icon" aria-hidden="true">
                  {link.icon}
                </span>
                <span>{link.label}</span>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function average(values: number[] | undefined): number | undefined {
  if (!values || values.length === 0) return undefined;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

function median(values: number[] | undefined): number | undefined {
  if (!values || values.length === 0) return undefined;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  const lower = sorted[mid - 1];
  const upper = sorted[mid];
  if (sorted.length % 2 === 0 && lower !== undefined && upper !== undefined) {
    return (lower + upper) / 2;
  }
  return sorted[mid];
}
