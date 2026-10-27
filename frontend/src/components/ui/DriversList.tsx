import { featureLabel, topDrivers } from "@/lib/forecast";
import type { Contribution } from "@/types/api";

interface DriversListProps {
  contributions: Contribution[];
  limit?: number;
}

/**
 * The biggest contributors to one forecast, as diverging bars.
 *
 * Values are TreeSHAP attributions on the model's signed-log scale, so the
 * bars show relative push (up or down) rather than percentage points; the
 * caption says so instead of pretending they add up to the forecast in %.
 */
export function DriversList({ contributions, limit = 6 }: DriversListProps) {
  const rows = topDrivers(contributions, limit);
  const max = Math.max(...rows.map((r) => Math.abs(r.contribution)), 1e-9);

  if (rows.length === 0) {
    return <p>No attributions available for this forecast.</p>;
  }

  return (
    <ul className="drivers-list" aria-label="Forecast drivers">
      {rows.map((row) => {
        const width = `${(Math.abs(row.contribution) / max) * 50}%`;
        const up = row.contribution >= 0;
        return (
          <li key={row.feature} className="drivers-row">
            <span className="drivers-row__name">{featureLabel(row.feature)}</span>
            <span className="drivers-row__track" aria-hidden="true">
              <span
                className={`drivers-row__bar ${up ? "drivers-row__bar--up" : "drivers-row__bar--down"}`}
                style={{ width }}
              />
            </span>
            <span className="drivers-row__value">
              {up ? "▲ raises" : "▼ lowers"}
              <span className="sr-only"> the forecast by {Math.abs(row.contribution).toFixed(3)}</span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}
