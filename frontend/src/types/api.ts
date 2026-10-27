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
  /** Grouping for navigation, e.g. "Wages & prices". */
  category: string;
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

// ------------------------------------------------------------ forecasting

export type ModelKind = "ml" | "baseline" | "external";

export interface ForecastModel {
  id: string;
  indicator_id: string;
  name: string;
  kind: ModelKind;
  is_champion: boolean;
  description: string;
}

export interface ForecastPoint {
  origin_year: number;
  target_year: number;
  horizon: number;
  point: number;
  lower_80: number | null;
  upper_80: number | null;
  lower_95: number | null;
  upper_95: number | null;
}

export interface BacktestPoint {
  origin_year: number;
  target_year: number;
  horizon: number;
  actual: number;
  point: number;
  lower_80: number | null;
  upper_80: number | null;
}

export interface Contribution {
  feature: string;
  feature_value: number | null;
  /** TreeSHAP value on the signed-log scale; positive pushes the forecast up. */
  contribution: number;
}

export interface CountryForecastResponse {
  country: Country;
  indicator: Indicator;
  champion: ForecastModel;
  history: SeriesPoint[];
  forecasts: { model_id: string; points: ForecastPoint[] }[];
  backtest: { model_id: string; points: BacktestPoint[] }[];
  drivers: { target_year: number; contributions: Contribution[] }[];
}

export interface ForecastSnapshotValue {
  iso3: string;
  country: string;
  region: string | null;
  origin_year: number;
  target_year: number;
  point: number;
  lower_80: number | null;
  upper_80: number | null;
}

export interface ForecastSnapshotResponse {
  model: ForecastModel;
  horizon: number;
  values: ForecastSnapshotValue[];
}

/** One row of the model card's metrics table (model x horizon x window). */
export interface ModelMetric {
  model_id: string;
  horizon: number;
  window: "validation" | "test";
  n: number;
  mae: number;
  rmse: number;
  median_ae: number;
  mae_log: number;
  skill_vs_naive: number | null;
  coverage_80: number | null;
  coverage_95: number | null;
  median_width_80: number | null;
}

export interface SignificanceTest {
  horizon: number;
  versus: string;
  statistic: number | null;
  p_value: number | null;
  n_periods: number;
  mean_loss_diff: number | null;
}

export interface FeatureSpec {
  name: string;
  description: string;
  group: string;
}

/** The subset of model_card.json the UI reads; the full card has more. */
export interface InflationModelCard {
  task: "inflation";
  title: string;
  champion: string;
  trained_at: string;
  data: { countries: number; feature_rows: number; origin_years: [number, number] };
  design: {
    horizons: number[];
    backtest: string;
    validation_origins: [number, number];
    first_test_origin: number;
    selection_rule: string;
    intervals: string;
    target_transform: string;
  };
  features: FeatureSpec[];
  global_importance: { feature: string; mean_abs_shap: number }[];
  models: { id: string; name: string; kind: ModelKind; description: string }[];
  metrics: ModelMetric[];
  significance: SignificanceTest[];
  regimes: {
    model_id: string;
    horizon: number;
    regime: string;
    n: number;
    mae: number;
    median_ae: number;
    coverage_80: number | null;
  }[];
  yearly_errors: { model_id: string; horizon: number; target_year: number; median_ae: number }[];
  intended_use: string;
  limitations: string[];
  not_intended_for: string[];
}

export interface DetectorResult {
  description: string;
  pr_auc: number | null;
  roc_auc: number | null;
  at_rule_budget: { precision: number; recall: number; f1: number; flagged: number };
  at_0_5?: { precision: number; recall: number; f1: number; flagged: number } | null;
  transition_level?: { precision: number; recall: number; rejected: number; contaminated: number };
}

export interface AnomalyModelCard {
  task: "anomaly";
  title: string;
  labels: {
    observed_cells: number;
    imputed_cells: number;
    imputed_share: number;
    countries: number;
    countries_with_imputation: number;
    imputed_by_year: Record<string, number>;
  };
  base_rate: number;
  detectors: Record<string, DetectorResult>;
  feature_importance_gain: { feature: string; gain: number }[];
}

export interface AnomalyScore {
  iso3: string;
  country: string;
  year: number;
  score: number;
  is_flagged: boolean;
}

// ------------------------------------------------------------------ tools

export interface PurchasingPowerPoint {
  year: number;
  index: number;
  value: number;
  projected: boolean;
}

export interface PurchasingPowerResponse {
  country: Country;
  amount: number;
  from_year: number;
  to_year: number;
  equivalent: number;
  cumulative_inflation_pct: number;
  annualised_inflation_pct: number;
  uses_projection: boolean;
  last_observed_year: number;
  path: PurchasingPowerPoint[];
}
