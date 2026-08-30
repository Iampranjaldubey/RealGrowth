/**
 * Types mirroring backend/src/realgrowth/schemas.py.
 *
 * Kept hand-written rather than generated: the API surface is small and
 * stable enough that a generator (openapi-typescript) would be one more
 * moving part for little benefit here, but the field names and shapes below
 * must be kept in sync with the Pydantic models they mirror.
 */

export interface Indicator {
  id: string;
  name: string;
  unit: string;
  unit_symbol: string;
  description: string;
  source: string;
  source_url: string;
  /** 1 = higher is better, -1 = lower is better, 0 = neutral */
  direction: -1 | 0 | 1;
  decimals: number;
  is_derived: boolean;
  depends_on: string[];
  min_year: number | null;
  max_year: number | null;
  country_count: number;
}

export interface Country {
  iso3: string;
  name: string;
  region: string | null;
  is_aggregate: boolean;
}

export interface SeriesPoint {
  year: number;
  value: number;
}

export interface CountrySeries {
  iso3: string;
  country: string;
  region: string | null;
  /** A data-quality caveat for this series, if any. */
  flag: string | null;
  points: SeriesPoint[];
}

export interface SeriesResponse {
  indicator: Indicator;
  series: CountrySeries[];
}

export interface SnapshotValue {
  iso3: string;
  country: string;
  region: string | null;
  value: number;
}

export interface SnapshotResponse {
  indicator: Indicator;
  year: number | null;
  values: SnapshotValue[];
}

export interface IndicatorObservation {
  indicator_id: string;
  year: number;
  value: number;
}

export interface CountryProfileResponse {
  country: Country;
  latest: IndicatorObservation[];
}

export interface CorrelationStatistics {
  n: number;
  r: number;
  r_squared: number;
  slope: number;
  intercept: number;
  p_value: number | null;
  ci_low: number | null;
  ci_high: number | null;
  is_significant: boolean;
  strength: string;
}

export interface CorrelationPoint {
  label: string;
  x: number;
  y: number;
  year: number | null;
  iso3: string | null;
}

export interface CorrelationResponse {
  mode: "time" | "cross_section";
  indicator_x: Indicator;
  indicator_y: Indicator;
  country: Country | null;
  year: number | null;
  region: string | null;
  points: CorrelationPoint[];
  statistics: CorrelationStatistics | null;
  note: string | null;
}

export interface QualityCoverage {
  indicator: string;
  observations: number;
  countries: number;
  min_year: number | null;
  max_year: number | null;
  density_pct: number;
}

export interface QualityIssue {
  kind: string;
  indicator: string;
  entity: string | null;
  year: number | null;
  detail: string;
}

export interface QualityReport {
  total_observations: number;
  total_countries: number;
  total_aggregates: number;
  issue_counts: Record<string, number>;
  flag_counts: Record<string, number>;
  unresolved_entities: string[];
  coverage: QualityCoverage[];
  issues: QualityIssue[];
  issues_truncated: number;
}

export interface ApiErrorPayload {
  error: string;
  detail: string | null;
  status: number;
}
