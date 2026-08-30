/**
 * Typed fetch client for the RealGrowth API.
 *
 * Replaces the previous axios wrapper (services/api.js). The important
 * differences:
 *
 * - Every path segment is `encodeURIComponent`-escaped; the old client
 *   interpolated country names directly into the URL path.
 * - Every call accepts an `AbortSignal`, which TanStack Query wires up
 *   automatically so an in-flight request is cancelled when its inputs
 *   change — the old `useApi` hook had no cancellation, so rapid year or
 *   country changes could let a stale response overwrite a newer one.
 * - Errors throw a typed `ApiError` carrying the backend's
 *   `{error, detail, status}` contract instead of a generic Error.
 */

import type {
  ApiErrorPayload,
  CorrelationResponse,
  Country,
  CountryProfileResponse,
  Indicator,
  QualityReport,
  SeriesResponse,
  SnapshotResponse,
} from "@/types/api";

const BASE_URL = import.meta.env.VITE_API_URL ?? "/api";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string | null;

  constructor(payload: ApiErrorPayload) {
    super(payload.error);
    this.name = "ApiError";
    this.status = payload.status;
    this.detail = payload.detail;
  }
}

function buildQuery(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, { signal });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as ApiErrorPayload | null;
    throw new ApiError(
      payload ?? { error: "Request failed", detail: response.statusText, status: response.status },
    );
  }
  return (await response.json()) as T;
}

/** Escape a path segment — country codes and indicator ids are safe, but
 * this guards against any value containing "/", "?" or "&". */
function segment(value: string): string {
  return encodeURIComponent(value);
}

export const api = {
  listIndicators: (signal?: AbortSignal) => request<Indicator[]>("/v1/indicators", signal),

  getIndicator: (indicatorId: string, signal?: AbortSignal) =>
    request<Indicator>(`/v1/indicators/${segment(indicatorId)}`, signal),

  getSeries: (
    indicatorId: string,
    countries: string[],
    options: { startYear?: number; endYear?: number } = {},
    signal?: AbortSignal,
  ) =>
    request<SeriesResponse>(
      `/v1/indicators/${segment(indicatorId)}/series${buildQuery({
        countries: countries.join(","),
        start_year: options.startYear,
        end_year: options.endYear,
      })}`,
      signal,
    ),

  getSnapshot: (
    indicatorId: string,
    options: {
      year?: number;
      region?: string;
      minPopulation?: number;
      includeAggregates?: boolean;
      order?: "asc" | "desc";
      limit?: number;
    } = {},
    signal?: AbortSignal,
  ) =>
    request<SnapshotResponse>(
      `/v1/indicators/${segment(indicatorId)}/snapshot${buildQuery({
        year: options.year,
        region: options.region,
        min_population: options.minPopulation,
        include_aggregates: options.includeAggregates,
        order: options.order,
        limit: options.limit,
      })}`,
      signal,
    ),

  listCountries: (
    options: {
      indicator?: string;
      region?: string;
      search?: string;
      includeAggregates?: boolean;
    } = {},
    signal?: AbortSignal,
  ) =>
    request<Country[]>(
      `/v1/countries${buildQuery({
        indicator: options.indicator,
        region: options.region,
        search: options.search,
        include_aggregates: options.includeAggregates,
      })}`,
      signal,
    ),

  getCountryProfile: (iso3: string, signal?: AbortSignal) =>
    request<CountryProfileResponse>(`/v1/countries/${segment(iso3)}`, signal),

  listRegions: (signal?: AbortSignal) => request<string[]>("/v1/regions", signal),

  correlateTimeSeries: (
    params: { country: string; x: string; y: string; startYear?: number; endYear?: number },
    signal?: AbortSignal,
  ) =>
    request<CorrelationResponse>(
      `/v1/correlation/time-series${buildQuery({
        country: params.country,
        x: params.x,
        y: params.y,
        start_year: params.startYear,
        end_year: params.endYear,
      })}`,
      signal,
    ),

  correlateCrossSection: (
    params: { x: string; y: string; year: number; region?: string },
    signal?: AbortSignal,
  ) =>
    request<CorrelationResponse>(
      `/v1/correlation/cross-section${buildQuery({
        x: params.x,
        y: params.y,
        year: params.year,
        region: params.region,
      })}`,
      signal,
    ),

  getQualityReport: (signal?: AbortSignal) => request<QualityReport>("/v1/meta/quality", signal),
};
