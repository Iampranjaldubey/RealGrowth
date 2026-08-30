/**
 * TanStack Query hooks: one per API call, each with a stable query key.
 *
 * This replaces two ad-hoc hooks from the previous frontend:
 *
 * - `useApi` returned a non-memoized `execute` function, so every page's
 *   `useEffect` had to suppress the exhaustive-deps lint rule to avoid an
 *   infinite loop, and nothing cancelled a stale in-flight request.
 * - `useCountries` cached country lists in a module-level mutable object
 *   that was never invalidated and invisible to React DevTools.
 *
 * TanStack Query subsumes both: caching, de-duplication of identical
 * in-flight requests, and automatic cancellation are the library's job, not
 * hand-rolled per hook.
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export const queryKeys = {
  indicators: ["indicators"] as const,
  indicator: (id: string) => ["indicators", id] as const,
  series: (id: string, countries: string[], startYear?: number, endYear?: number) =>
    ["indicators", id, "series", countries, startYear, endYear] as const,
  snapshot: (
    id: string,
    year?: number,
    region?: string,
    minPopulation?: number,
    order?: string,
  ) => ["indicators", id, "snapshot", year, region, minPopulation, order] as const,
  countries: (indicator?: string, region?: string, search?: string) =>
    ["countries", indicator, region, search] as const,
  countryProfile: (iso3: string) => ["countries", iso3, "profile"] as const,
  regions: ["regions"] as const,
  correlationTimeSeries: (country: string, x: string, y: string) =>
    ["correlation", "time-series", country, x, y] as const,
  correlationCrossSection: (x: string, y: string, year: number, region?: string) =>
    ["correlation", "cross-section", x, y, year, region] as const,
  quality: ["quality"] as const,
};

export function useIndicators() {
  return useQuery({
    queryKey: queryKeys.indicators,
    queryFn: ({ signal }) => api.listIndicators(signal),
    staleTime: Infinity, // The indicator catalogue changes only on an ETL rebuild.
  });
}

export function useIndicator(indicatorId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.indicator(indicatorId ?? ""),
    queryFn: ({ signal }) => api.getIndicator(indicatorId as string, signal),
    enabled: Boolean(indicatorId),
  });
}

export function useSeries(
  indicatorId: string | undefined,
  countries: string[],
  options: { startYear?: number; endYear?: number } = {},
) {
  return useQuery({
    queryKey: queryKeys.series(indicatorId ?? "", countries, options.startYear, options.endYear),
    queryFn: ({ signal }) => api.getSeries(indicatorId as string, countries, options, signal),
    enabled: Boolean(indicatorId) && countries.length > 0,
  });
}

export function useSnapshot(
  indicatorId: string | undefined,
  options: {
    year?: number;
    region?: string;
    minPopulation?: number;
    includeAggregates?: boolean;
    order?: "asc" | "desc";
    limit?: number;
  } = {},
) {
  return useQuery({
    queryKey: queryKeys.snapshot(
      indicatorId ?? "",
      options.year,
      options.region,
      options.minPopulation,
      options.order,
    ),
    queryFn: ({ signal }) => api.getSnapshot(indicatorId as string, options, signal),
    enabled: Boolean(indicatorId),
  });
}

export function useCountries(
  options: { indicator?: string; region?: string; search?: string; includeAggregates?: boolean } = {},
) {
  return useQuery({
    queryKey: queryKeys.countries(options.indicator, options.region, options.search),
    queryFn: ({ signal }) => api.listCountries(options, signal),
  });
}

export function useCountryProfile(iso3: string | undefined) {
  return useQuery({
    queryKey: queryKeys.countryProfile(iso3 ?? ""),
    queryFn: ({ signal }) => api.getCountryProfile(iso3 as string, signal),
    enabled: Boolean(iso3),
  });
}

export function useRegions() {
  return useQuery({
    queryKey: queryKeys.regions,
    queryFn: ({ signal }) => api.listRegions(signal),
    staleTime: Infinity,
  });
}

export function useCorrelationTimeSeries(
  country: string | undefined,
  x: string | undefined,
  y: string | undefined,
) {
  return useQuery({
    queryKey: queryKeys.correlationTimeSeries(country ?? "", x ?? "", y ?? ""),
    queryFn: ({ signal }) =>
      api.correlateTimeSeries({ country: country as string, x: x as string, y: y as string }, signal),
    enabled: Boolean(country && x && y),
  });
}

export function useCorrelationCrossSection(
  x: string | undefined,
  y: string | undefined,
  year: number | undefined,
  region?: string,
) {
  return useQuery({
    queryKey: queryKeys.correlationCrossSection(x ?? "", y ?? "", year ?? 0, region),
    queryFn: ({ signal }) =>
      api.correlateCrossSection({ x: x as string, y: y as string, year: year as number, region }, signal),
    enabled: Boolean(x && y && year),
  });
}

export function useQualityReport() {
  return useQuery({
    queryKey: queryKeys.quality,
    queryFn: ({ signal }) => api.getQualityReport(signal),
  });
}
