import { useQualityReport } from "@/api/queries";
import { formatNumber } from "@/lib/formatters";

/**
 * Surfaces the ETL's quality report (backend/src/realgrowth/etl/quality.py)
 * in the product itself. Several upstream sources contain imputed values —
 * missing wage/inflation/debt/diet-cost cells were filled by scaling the
 * world average — and the honest thing to do with that limitation is publish
 * it, not bury it in a README nobody reads before trusting a chart.
 */
export function DataQualityPage() {
  const { data: report, isLoading, isError } = useQualityReport();

  if (isLoading) return <p>Loading data-quality report…</p>;
  if (isError || !report) return <p>Could not load the data-quality report.</p>;

  return (
    <div>
      <div className="page-header">
        <h1>Data Quality</h1>
        <p>
          What the ETL pipeline found when it built this warehouse: coverage per indicator, values
          rejected as implausible, and series flagged for the reader's caution.
        </p>
      </div>

      <div className="stats-grid">
        <SummaryCard label="Observations" value={formatNumber(report.total_observations)} />
        <SummaryCard label="Countries" value={formatNumber(report.total_countries)} />
        <SummaryCard label="Aggregates tracked" value={formatNumber(report.total_aggregates)} />
      </div>

      <div className="glass-card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 16 }}>Coverage by indicator</h3>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
          <thead>
            <tr style={{ textAlign: "left", color: "var(--text-tertiary)" }}>
              <th style={{ padding: "8px 4px" }}>Indicator</th>
              <th style={{ padding: "8px 4px" }}>Observations</th>
              <th style={{ padding: "8px 4px" }}>Countries</th>
              <th style={{ padding: "8px 4px" }}>Years</th>
              <th style={{ padding: "8px 4px" }}>Density</th>
            </tr>
          </thead>
          <tbody>
            {report.coverage.map((row) => (
              <tr key={row.indicator} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                <td style={{ padding: "8px 4px" }}>{row.indicator}</td>
                <td style={{ padding: "8px 4px" }}>{formatNumber(row.observations)}</td>
                <td style={{ padding: "8px 4px" }}>{row.countries}</td>
                <td style={{ padding: "8px 4px" }}>
                  {row.min_year && row.max_year ? `${row.min_year}–${row.max_year}` : "—"}
                </td>
                <td style={{ padding: "8px 4px" }}>{row.density_pct.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="two-col-grid">
        <div className="glass-card">
          <h3 style={{ marginBottom: 16 }}>Issues found during the ETL run</h3>
          {Object.keys(report.issue_counts).length === 0 ? (
            <p>No issues found.</p>
          ) : (
            <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
              {Object.entries(report.issue_counts).map(([kind, count]) => (
                <li key={kind} style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>{describeIssueKind(kind)}</span>
                  <strong>{formatNumber(count)}</strong>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="glass-card">
          <h3 style={{ marginBottom: 16 }}>Series flagged for caution</h3>
          {Object.keys(report.flag_counts).length === 0 ? (
            <p>No series were flagged.</p>
          ) : (
            <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
              {Object.entries(report.flag_counts).map(([key, count]) => (
                <li key={key} style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>{key.replace(":", " — ")}</span>
                  <strong>{formatNumber(count)}</strong>
                </li>
              ))}
            </ul>
          )}
          <p style={{ marginTop: 12, fontSize: "0.85rem" }}>
            Most flags are on <code>avg_wage</code>: the upstream source imputed missing months by
            scaling the world average, which occasionally produces a wage jump with no matching
            inflation to explain it. Those transitions are excluded from wage-growth figures rather
            than plotted as real movement.
          </p>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="glass-card">
      <div className="stat-card__title">{label}</div>
      <div className="stat-card__value">{value}</div>
    </div>
  );
}

function describeIssueKind(kind: string): string {
  const labels: Record<string, string> = {
    unresolved_entity: "Unresolved country labels",
    duplicate_entity: "Duplicate country conflicts",
    out_of_range: "Values outside a plausible range",
    implausible_growth: "Wage-growth transitions rejected as imputation artefacts",
  };
  return labels[kind] ?? kind;
}
