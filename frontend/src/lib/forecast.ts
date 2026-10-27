/**
 * Pure helpers for the forecasting views, kept out of components so they
 * can be unit-tested without rendering a chart.
 */

import type { BacktestPoint, Contribution, ForecastPoint, ModelMetric, SeriesPoint } from "@/types/api";

/** Plain-language names for model features (the model card has the long form). */
export const FEATURE_LABELS: Record<string, string> = {
  infl_lag0: "Inflation this year",
  infl_lag1: "Inflation last year",
  infl_lag2: "Inflation two years ago",
  infl_mean5: "5-year average inflation",
  infl_std5: "5-year inflation volatility",
  infl_change: "Change in inflation",
  deflator_lag0: "GDP deflator inflation",
  money_growth_lag0: "Money supply growth",
  money_growth_lag1: "Money supply growth (last year)",
  fx_change_lag0: "Currency depreciation vs USD",
  gdp_growth_lag0: "Real GDP growth",
  unemployment_lag0: "Unemployment rate",
  real_interest_lag0: "Real interest rate",
  current_account_lag0: "Current account balance",
  debt_lag0: "Government debt",
  log_trade_openness: "Trade openness",
  log_gdp_pc_ppp: "Income level (GDP per capita, PPP)",
  global_infl_median: "Global inflation (median country)",
  global_infl_change: "Change in global inflation",
  region_code: "Region",
};

export function featureLabel(feature: string): string {
  return FEATURE_LABELS[feature] ?? feature;
}

/** Signed-log, the scale the model works on. Mirrors realgrowth_ml.features.slog. */
export function slog(x: number): number {
  return Math.sign(x) * Math.log1p(Math.abs(x));
}

/**
 * Datasets for the history + forecast chart, aligned on one year axis.
 *
 * The forecast line starts at the last observed point so it visibly continues
 * the history rather than floating free; interval bands start there too, with
 * zero width, which reads correctly as "certainty decreases with horizon".
 */
export interface ForecastChartData {
  years: number[];
  history: (number | null)[];
  forecast: (number | null)[];
  lower80: (number | null)[];
  upper80: (number | null)[];
  lower95: (number | null)[];
  upper95: (number | null)[];
  benchmark: (number | null)[];
}

export function buildForecastChartData(
  history: SeriesPoint[],
  forecast: ForecastPoint[],
  benchmark: ForecastPoint[] = [],
): ForecastChartData {
  const last = history.at(-1);
  const years = Array.from(
    new Set([
      ...history.map((p) => p.year),
      ...forecast.map((p) => p.target_year),
      ...benchmark.map((p) => p.target_year),
    ]),
  ).sort((a, b) => a - b);

  const byYear = <T>(points: T[], key: (p: T) => number, value: (p: T) => number | null) => {
    const map = new Map<number, number | null>(points.map((p) => [key(p), value(p)]));
    return years.map((year) => (map.has(year) ? (map.get(year) ?? null) : null));
  };

  const anchored = (value: (p: ForecastPoint) => number | null) => {
    const series = byYear(forecast, (p) => p.target_year, value);
    if (last && forecast.length > 0) {
      const index = years.indexOf(last.year);
      if (index >= 0) series[index] = last.value;
    }
    return series;
  };

  return {
    years,
    history: byYear(history, (p) => p.year, (p) => p.value),
    forecast: anchored((p) => p.point),
    lower80: anchored((p) => p.lower_80),
    upper80: anchored((p) => p.upper_80),
    lower95: anchored((p) => p.lower_95),
    upper95: anchored((p) => p.upper_95),
    benchmark: byYear(benchmark, (p) => p.target_year, (p) => p.point),
  };
}

/** Per-country backtest accuracy: champion vs naive on this country's history. */
export function backtestSummary(champion: BacktestPoint[], naive: BacktestPoint[]) {
  const mae = (points: BacktestPoint[]) =>
    points.length === 0
      ? null
      : points.reduce((sum, p) => sum + Math.abs(p.actual - p.point), 0) / points.length;
  const withInterval = champion.filter((p) => p.lower_80 !== null && p.upper_80 !== null);
  const covered = withInterval.filter(
    (p) => p.actual >= (p.lower_80 as number) && p.actual <= (p.upper_80 as number),
  ).length;
  return {
    n: champion.length,
    championMae: mae(champion),
    naiveMae: mae(naive),
    coverage80: withInterval.length ? covered / withInterval.length : null,
  };
}

/** Sort a forecast's attributions by absolute size and keep the top `n`. */
export function topDrivers(contributions: Contribution[], n = 6): Contribution[] {
  return [...contributions]
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
    .slice(0, n);
}

/** Test-window leaderboard for one horizon, best first. */
export function leaderboard(metrics: ModelMetric[], horizon: number): ModelMetric[] {
  return metrics
    .filter((m) => m.window === "test" && m.horizon === horizon)
    .sort((a, b) => a.mae_log - b.mae_log);
}
