import { Line } from "react-chartjs-2";
import { baseOptions, paletteColor } from "@/lib/chartTheme";
import type { CountrySeries } from "@/types/api";

interface TimeSeriesChartProps {
  series: CountrySeries[];
  valueFormatter?: (value: number) => string;
  showLegend?: boolean;
}

/**
 * Renders one or more countries' series on a shared year axis.
 *
 * Builds a sparse dataset: each series may cover a different set of years
 * (a gap is `null`, not a zero-filled dip), so the axis is the union of every
 * year present in any series and each dataset is mapped onto it individually.
 */
export function TimeSeriesChart({ series, valueFormatter, showLegend = true }: TimeSeriesChartProps) {
  const years = Array.from(new Set(series.flatMap((s) => s.points.map((p) => p.year)))).sort(
    (a, b) => a - b,
  );

  const datasets = series.map((s, index) => {
    const byYear = new Map(s.points.map((p) => [p.year, p.value]));
    const color = paletteColor(index);
    return {
      label: s.country,
      data: years.map((year) => byYear.get(year) ?? null),
      borderColor: color,
      backgroundColor: `${color}33`,
      spanGaps: false,
      fill: series.length === 1,
      tension: 0.3,
      borderWidth: 3,
      pointRadius: 0,
      pointHoverRadius: 6,
    };
  });

  return (
    <div className="chart-wrapper">
      <Line
        data={{ labels: years, datasets }}
        options={baseOptions<"line">({ valueFormatter, showLegend })}
      />
    </div>
  );
}
