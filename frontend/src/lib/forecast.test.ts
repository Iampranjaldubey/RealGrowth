import { describe, expect, it } from "vitest";
import {
  backtestSummary,
  buildForecastChartData,
  featureLabel,
  leaderboard,
  slog,
  topDrivers,
} from "./forecast";
import type { BacktestPoint, ForecastPoint, ModelMetric } from "@/types/api";

const fp = (target_year: number, point: number, horizon = target_year - 2024): ForecastPoint => ({
  origin_year: 2024,
  target_year,
  horizon,
  point,
  lower_80: point - 1,
  upper_80: point + 1,
  lower_95: point - 2,
  upper_95: point + 2,
});

describe("buildForecastChartData", () => {
  const history = [
    { year: 2022, value: 6.0 },
    { year: 2023, value: 5.0 },
    { year: 2024, value: 4.0 },
  ];

  it("puts history, forecast and benchmark on one sorted year axis", () => {
    const data = buildForecastChartData(history, [fp(2025, 3.5), fp(2026, 3.2)], [fp(2025, 3.9)]);
    expect(data.years).toEqual([2022, 2023, 2024, 2025, 2026]);
    expect(data.history).toEqual([6, 5, 4, null, null]);
    expect(data.benchmark).toEqual([null, null, null, 3.9, null]);
  });

  it("anchors the forecast and its bands to the last observation", () => {
    const data = buildForecastChartData(history, [fp(2025, 3.5)]);
    expect(data.forecast).toEqual([null, null, 4, 3.5]);
    // zero-width band at the anchor: uncertainty starts at the last data point
    expect(data.lower80[2]).toBe(4);
    expect(data.upper80[2]).toBe(4);
    expect(data.upper95[3]).toBe(5.5);
  });

  it("does not anchor anything when there is no forecast", () => {
    const data = buildForecastChartData(history, []);
    expect(data.forecast.every((v) => v === null)).toBe(true);
  });
});

describe("backtestSummary", () => {
  const bt = (actual: number, point: number, lo: number | null = null, hi: number | null = null): BacktestPoint => ({
    origin_year: 2010,
    target_year: 2011,
    horizon: 1,
    actual,
    point,
    lower_80: lo,
    upper_80: hi,
  });

  it("computes MAE and coverage only over rows that have an interval", () => {
    const summary = backtestSummary(
      [bt(2, 1, 0, 3), bt(5, 4, 4.5, 6), bt(3, 3)],
      [bt(2, 4), bt(5, 1)],
    );
    expect(summary.n).toBe(3);
    expect(summary.championMae).toBeCloseTo(2 / 3);
    expect(summary.naiveMae).toBeCloseTo(3);
    expect(summary.coverage80).toBe(1);
  });

  it("returns nulls when there is nothing to evaluate", () => {
    expect(backtestSummary([], [])).toEqual({ n: 0, championMae: null, naiveMae: null, coverage80: null });
  });
});

describe("topDrivers", () => {
  it("ranks by absolute contribution", () => {
    const rows = topDrivers(
      [
        { feature: "a", feature_value: 1, contribution: 0.1 },
        { feature: "b", feature_value: 1, contribution: -0.5 },
        { feature: "c", feature_value: 1, contribution: 0.3 },
      ],
      2,
    );
    expect(rows.map((r) => r.feature)).toEqual(["b", "c"]);
  });
});

describe("leaderboard", () => {
  const m = (model_id: string, horizon: number, window: "test" | "validation", mae_log: number) =>
    ({ model_id, horizon, window, mae_log }) as ModelMetric;

  it("keeps only the test window for one horizon, best first", () => {
    const rows = leaderboard(
      [m("naive", 1, "test", 0.5), m("ens", 1, "test", 0.4), m("ens", 1, "validation", 0.1), m("ens", 2, "test", 0.3)],
      1,
    );
    expect(rows.map((r) => r.model_id)).toEqual(["ens", "naive"]);
  });
});

describe("helpers", () => {
  it("slog matches the Python definition", () => {
    expect(slog(0)).toBe(0);
    expect(slog(-3)).toBeCloseTo(-Math.log(4));
  });

  it("labels known features and passes unknown ones through", () => {
    expect(featureLabel("fx_change_lag0")).toBe("Currency depreciation vs USD");
    expect(featureLabel("mystery")).toBe("mystery");
  });
});
