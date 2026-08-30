/**
 * Shared Chart.js registration and option builders.
 *
 * The previous frontend had three chart components (Line/Bar/Pie), each
 * re-declaring an almost identical ~50-line options object with its own
 * title/legend/tooltip/scales blocks. This module centralises that into one
 * `baseOptions()` builder so a Line and a Bar chart share one source of
 * truth for typography, tooltip styling and grid colour.
 */

import {
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  ScatterController,
  Title,
  Tooltip,
  type ChartOptions,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  LineController,
  BarController,
  ScatterController,
  Title,
  Tooltip,
  Legend,
  Filler,
);

ChartJS.defaults.color = "#94a3b8";
ChartJS.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";

export const chartPalette = ["#06b6d4", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", "#ec4899", "#3b82f6"];

export function paletteColor(index: number): string {
  return chartPalette[index % chartPalette.length] ?? "#06b6d4";
}

interface BaseOptionsArgs {
  valueFormatter?: (value: number) => string;
  showLegend?: boolean;
  indexAxis?: "x" | "y";
}

/**
 * Generic over the chart type because Chart.js's `ChartOptions<T>` is not
 * structurally assignable between different `T`s (a known upstream
 * limitation — the callback signatures embed the type parameter). Callers
 * pass their own type, e.g. `baseOptions<"bar">(...)`, so the returned shape
 * lines up with what `<Bar>`/`<Line>` expect without an `as` cast at every
 * call site.
 */
export function baseOptions<TType extends "line" | "bar" = "line" | "bar">({
  valueFormatter,
  showLegend = true,
  indexAxis = "x",
}: BaseOptionsArgs = {}): ChartOptions<TType> {
  return {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: {
        display: showLegend,
        position: "top",
        labels: { usePointStyle: true, padding: 16, font: { size: 12 } },
      },
      tooltip: {
        backgroundColor: "rgba(15, 23, 42, 0.92)",
        titleColor: "#f1f5f9",
        bodyColor: "#cbd5e1",
        borderColor: "rgba(255, 255, 255, 0.1)",
        borderWidth: 1,
        padding: 10,
        cornerRadius: 8,
        callbacks: valueFormatter
          ? {
              label: (context) => {
                const label = context.dataset.label ? `${context.dataset.label}: ` : "";
                const raw = indexAxis === "y" ? context.parsed.x : context.parsed.y;
                return `${label}${valueFormatter(raw ?? 0)}`;
              },
            }
          : undefined,
      },
    },
    scales: {
      x: {
        grid: { color: "rgba(255, 255, 255, 0.05)" },
        ticks: {
          font: { size: 11 },
          callback:
            indexAxis === "y" && valueFormatter
              ? (value) => valueFormatter(Number(value))
              : undefined,
        },
      },
      y: {
        grid: { color: "rgba(255, 255, 255, 0.05)" },
        ticks: {
          font: { size: 11 },
          callback:
            indexAxis === "x" && valueFormatter
              ? (value) => valueFormatter(Number(value))
              : undefined,
        },
      },
    },
  };
}
