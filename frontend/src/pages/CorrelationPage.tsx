import { ChartCard } from "@/components/ui/ChartCard";
import { CountrySelect } from "@/components/ui/CountrySelect";
import { ScatterChart } from "@/components/charts/ScatterChart";
import { useCorrelationTimeSeries, useIndicators } from "@/api/queries";
import { useUrlNumberState, useUrlState } from "@/lib/useUrlState";

/**
 * The previous Correlation page had a live bug: it called
 * `useApi(api.getCorrelationIndicators)` but never invoked `execute`, then
 * separately fired `api.getCorrelationIndicators().catch(console.error)` and
 * discarded the result — so `indicators` was always null and both dropdowns
 * rendered zero options. This version fetches the indicator list through the
 * same `useIndicators()` query that populates every other dropdown in the
 * app and actually uses the result.
 */
export function CorrelationPage() {
  const indicatorsQuery = useIndicators();
  const [country, setCountry] = useUrlState("country", "USA");
  const [x, setX] = useUrlState("x", "inflation_rate");
  const [y, setY] = useUrlState("y", "real_wage_growth");
  const [startYear, setStartYear] = useUrlNumberState("start", 2010);

  const correlation = useCorrelationTimeSeries(country, x, y);
  const indicators = indicatorsQuery.data ?? [];

  return (
    <div>
      <div className="page-header">
        <h1>Correlation Explorer</h1>
        <p>
          Test whether two indicators move together within a single country over time. A correlation
          is a statistical association, not evidence that one causes the other.
        </p>
      </div>

      <div className="controls-row glass-card">
        <CountrySelect id="corr-country" value={country} onChange={setCountry} label="Country" />

        <div className="form-group">
          <label htmlFor="corr-x">X axis</label>
          <select id="corr-x" value={x} onChange={(e) => setX(e.target.value)}>
            {indicators.map((ind) => (
              <option key={ind.id} value={ind.id}>
                {ind.name}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="corr-y">Y axis</label>
          <select id="corr-y" value={y} onChange={(e) => setY(e.target.value)}>
            {indicators.map((ind) => (
              <option key={ind.id} value={ind.id}>
                {ind.name}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group" style={{ minWidth: 140 }}>
          <label htmlFor="corr-start">From year</label>
          <input
            id="corr-start"
            type="number"
            value={startYear}
            onChange={(e) => setStartYear(Number(e.target.value))}
          />
        </div>
      </div>

      <ChartCard
        title={
          correlation.data
            ? `${correlation.data.indicator_x.name} vs. ${correlation.data.indicator_y.name} — ${correlation.data.country?.name ?? ""}`
            : undefined
        }
        loading={correlation.isLoading}
        error={correlation.error?.message}
      >
        {correlation.data && correlation.data.points.length > 0 ? (
          <>
            <ScatterChart
              points={correlation.data.points}
              statistics={correlation.data.statistics}
              xLabel={`${correlation.data.indicator_x.name} (${correlation.data.indicator_x.unit})`}
              yLabel={`${correlation.data.indicator_y.name} (${correlation.data.indicator_y.unit})`}
            />
            <StatisticsSummary
              statistics={correlation.data.statistics}
              note={correlation.data.note}
            />
          </>
        ) : (
          <p>{correlation.data?.note ?? "Not enough overlapping data for this combination."}</p>
        )}
      </ChartCard>
    </div>
  );
}

function StatisticsSummary({
  statistics,
  note,
}: {
  statistics: NonNullable<ReturnType<typeof useCorrelationTimeSeries>["data"]>["statistics"];
  note: string | null | undefined;
}) {
  if (!statistics) {
    return note ? <p style={{ marginTop: 12 }}>{note}</p> : null;
  }

  return (
    <div style={{ marginTop: 16, display: "flex", flexWrap: "wrap", gap: 20, fontSize: "0.9rem" }}>
      <Stat label="r" value={statistics.r.toFixed(3)} />
      <Stat label="R²" value={statistics.r_squared.toFixed(3)} />
      <Stat label="n" value={String(statistics.n)} />
      <Stat
        label="p-value"
        value={statistics.p_value !== null ? statistics.p_value.toFixed(4) : "n/a (n too small)"}
      />
      <Stat label="Strength" value={statistics.strength} />
      <Stat label="Significant (p < .05)" value={statistics.is_significant ? "Yes" : "No"} />
      {note && <p style={{ width: "100%", marginTop: 8 }}>{note}</p>}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ color: "var(--text-tertiary)", fontSize: "0.75rem", textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>{value}</div>
    </div>
  );
}
