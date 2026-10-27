import { Line } from "react-chartjs-2";
import { baseOptions } from "@/lib/chartTheme";
import type { ForecastChartData } from "@/lib/forecast";

interface ForecastChartProps {
  data: ForecastChartData;
  valueFormatter: (value: number) => string;
  benchmarkLabel?: string;
}

/**
 * History, point forecast, 80% and 95% conformal bands, and the IMF benchmark.
 *
 * Bands are drawn with Chart.js's dataset-relative fill: each "upper" dataset
 * fills down to the "lower" dataset immediately before it, so the shading is
 * exactly the interval and nothing else.
 */
export function ForecastChart({ data, valueFormatter, benchmarkLabel = "IMF WEO" }: ForecastChartProps) {
  const band = (label: string, values: (number | null)[], fill: false | string, alpha: string) => ({
    label,
    data: values,
    borderColor: "transparent",
    backgroundColor: `rgba(139, 92, 246, ${alpha})`,
    pointRadius: 0,
    fill,
    spanGaps: false,
    tension: 0,
  });

  const datasets = [
    band("95% lower", data.lower95, false, "0"),
    band("95% interval", data.upper95, "-1", "0.12"),
    band("80% lower", data.lower80, false, "0"),
    band("80% interval", data.upper80, "-1", "0.25"),
    {
      label: "Observed",
      data: data.history,
      borderColor: "#06b6d4",
      backgroundColor: "#06b6d4",
      borderWidth: 3,
      pointRadius: 0,
      pointHoverRadius: 5,
      tension: 0.25,
      spanGaps: false,
      fill: false,
    },
    {
      label: "Forecast",
      data: data.forecast,
      borderColor: "#8b5cf6",
      backgroundColor: "#8b5cf6",
      borderWidth: 3,
      borderDash: [6, 4],
      pointRadius: 4,
      tension: 0,
      spanGaps: false,
      fill: false,
    },
    {
      label: benchmarkLabel,
      data: data.benchmark,
      borderColor: "#f59e0b",
      backgroundColor: "#f59e0b",
      showLine: false,
      pointRadius: 6,
      pointStyle: "rectRot" as const,
      fill: false,
    },
  ];

  const options = baseOptions<"line">({ valueFormatter });
  // In high-inflation countries the 95% upper bound can be 10x the history,
  // flattening everything else. Cap the axis just above the 80% band; the 95%
  // band is then clipped at the top, which the legend still explains.
  const visible = [...data.history, ...data.upper80, ...data.benchmark].filter(
    (v): v is number => v !== null,
  );
  const highest95 = Math.max(...data.upper95.filter((v): v is number => v !== null), -Infinity);
  const cap = visible.length ? Math.max(...visible) * 1.25 : undefined;
  if (cap !== undefined && highest95 > cap) {
    const scales = (options.scales ?? {}) as Record<string, Record<string, unknown>>;
    scales.y = { ...(scales.y ?? {}), max: Math.ceil(cap) };
    options.scales = scales as typeof options.scales;
  }
  const plugins = (options.plugins ?? {}) as Record<string, unknown>;
  plugins.legend = {
    display: true,
    position: "top",
    labels: {
      usePointStyle: true,
      padding: 16,
      // Hide the invisible lower-bound helper datasets from the legend.
      filter: (item: { text: string }) => !item.text.endsWith("lower"),
    },
  };

  return (
    <div className="chart-wrapper" role="img" aria-label="Inflation history and forecast with prediction intervals">
      <Line data={{ labels: data.years, datasets }} options={{ ...options, plugins }} />
    </div>
  );
}
