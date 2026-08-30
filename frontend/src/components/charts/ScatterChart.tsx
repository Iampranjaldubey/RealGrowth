import { Chart } from "react-chartjs-2";
import type { ChartData } from "chart.js";
import { paletteColor } from "@/lib/chartTheme"; // also registers Chart.js controllers/elements
import type { CorrelationPoint, CorrelationStatistics } from "@/types/api";

interface ScatterChartProps {
  points: CorrelationPoint[];
  statistics: CorrelationStatistics | null;
  xLabel: string;
  yLabel: string;
}

/** Scatter plot with an overlaid OLS regression line, for the Correlation Explorer. */
export function ScatterChart({ points, statistics, xLabel, yLabel }: ScatterChartProps) {
  const xs = points.map((p) => p.x);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);

  const data: ChartData<"scatter" | "line"> = {
    datasets: [
      {
        type: "scatter" as const,
        label: `${xs.length} observations`,
        data: points.map((p) => ({ x: p.x, y: p.y })),
        backgroundColor: paletteColor(0),
        pointRadius: 5,
        pointHoverRadius: 7,
      },
      ...(statistics
        ? [
            {
              type: "line" as const,
              label: `Fit: y = ${statistics.slope.toFixed(3)}x + ${statistics.intercept.toFixed(2)}`,
              data: [
                { x: minX, y: statistics.slope * minX + statistics.intercept },
                { x: maxX, y: statistics.slope * maxX + statistics.intercept },
              ],
              borderColor: paletteColor(1),
              borderWidth: 2,
              pointRadius: 0,
              fill: false,
            },
          ]
        : []),
    ],
  };

  return (
    <div className="chart-wrapper">
      <Chart
        type="scatter"
        data={data}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "top", labels: { usePointStyle: true } },
            tooltip: {
              callbacks: {
                label: (context) => {
                  if (context.datasetIndex !== 0) return context.dataset.label ?? "";
                  const point = points[context.dataIndex];
                  return point ? `${point.label}: (${point.x.toFixed(2)}, ${point.y.toFixed(2)})` : "";
                },
              },
            },
          },
          scales: {
            x: { title: { display: true, text: xLabel }, grid: { color: "rgba(255,255,255,0.05)" } },
            y: { title: { display: true, text: yLabel }, grid: { color: "rgba(255,255,255,0.05)" } },
          },
        }}
      />
    </div>
  );
}
