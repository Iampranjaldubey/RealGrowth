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

/** The tooltip callback fields common to every chart type this app uses. */
interface TooltipContext {
  dataset: { label?: string };
  parsed: unknown;
}

/**
 * Chart.js's `ChartOptions<T>` embeds `T` throughout its callback signatures
 * (tooltip callbacks, scale tick callbacks, etc.), so a single object literal
 * cannot be structurally typed as both `ChartOptions<"bar">` and
 * `ChartOptions<"line">` — TypeScript has no way to prove a `context.parsed.y`
 * access is safe across every chart type at once. The options built here only
 * use the handful of fields common to bar and line charts (never a
 * per-type-specific callback shape), so the `as` is a type-system workaround
 * for a real Chart.js limitation, not a hidden unsafe cast — passing bad
 * shapes into a chart component still fails visibly in the browser console.
 */
export function baseOptions<TType extends "line" | "bar" = "line" | "bar">({
  valueFormatter,
  showLegend = true,
  indexAxis = "x",
}: BaseOptionsArgs = {}): ChartOptions<TType> {
  const options: Record<string, unknown> = {
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
              label: (context: TooltipContext) => {
                const label = context.dataset.label ? `${context.dataset.label}: ` : "";
                const parsed = context.parsed as { x?: number; y?: number };
                const raw = indexAxis === "y" ? parsed.x : parsed.y;
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
              ? (value: string | number) => valueFormatter(Number(value))
              : undefined,
        },
      },
      y: {
        grid: { color: "rgba(255, 255, 255, 0.05)" },
        ticks: {
          font: { size: 11 },
          callback:
            indexAxis === "x" && valueFormatter
              ? (value: string | number) => valueFormatter(Number(value))
              : undefined,
        },
      },
    },
  };
  return options as ChartOptions<TType>;
}
