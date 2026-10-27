"""Pydantic response models.

Every route declares a ``response_model``, so the response shape is enforced,
self-documenting in ``/docs``, and typed end to end when the frontend generates
a client from the OpenAPI schema. The previous API had no schemas at all: some
endpoints returned bare arrays, others wrapped the same shape in ``{"countries":
[...]}`` for no discernible reason, and invalid input variously produced a 400,
an empty array, or an uncaught 500.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """Base for all response models: immutable, and rejects unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ErrorResponse(ApiModel):
    """The single error shape returned by every endpoint in this API."""

    error: str
    detail: str | None = None
    status: int


class Country(ApiModel):
    iso3: str
    name: str
    region: str | None
    is_aggregate: bool


class Indicator(ApiModel):
    id: str
    name: str
    unit: str
    unit_symbol: str
    description: str
    source: str
    source_url: str
    category: str
    direction: int = Field(description="1 = higher is better, -1 = lower is better, 0 = neutral")
    decimals: int
    is_derived: bool
    depends_on: list[str]
    min_year: int | None
    max_year: int | None
    country_count: int


class SeriesPoint(ApiModel):
    year: int
    value: float


class CountrySeries(ApiModel):
    iso3: str
    country: str
    region: str | None
    flag: str | None = Field(
        default=None,
        description="Data-quality caveat for this series, if any; null means none.",
    )
    points: list[SeriesPoint]


class SeriesResponse(ApiModel):
    indicator: Indicator
    series: list[CountrySeries]


class SnapshotValue(ApiModel):
    iso3: str
    country: str
    region: str | None
    value: float


class SnapshotResponse(ApiModel):
    indicator: Indicator
    year: int | None
    values: list[SnapshotValue]


class IndicatorObservation(ApiModel):
    indicator_id: str
    year: int
    value: float


class CountryProfileResponse(ApiModel):
    country: Country
    latest: list[IndicatorObservation]


class CorrelationStatistics(ApiModel):
    n: int
    r: float
    r_squared: float
    slope: float
    intercept: float
    p_value: float | None
    ci_low: float | None
    ci_high: float | None
    is_significant: bool
    strength: str


class CorrelationPoint(ApiModel):
    label: str
    x: float
    y: float
    year: int | None = None
    iso3: str | None = None


class CorrelationResponse(ApiModel):
    mode: str = Field(description="'time' (one country over years) or 'cross_section'")
    indicator_x: Indicator
    indicator_y: Indicator
    country: Country | None
    year: int | None
    region: str | None
    points: list[CorrelationPoint]
    statistics: CorrelationStatistics | None
    note: str | None


class IndicatorCoverage(ApiModel):
    indicator: str
    observations: int
    countries: int
    min_year: int | None
    max_year: int | None
    density_pct: float


class QualityIssue(ApiModel):
    kind: str
    indicator: str
    entity: str | None
    year: int | None
    detail: str


class QualityReport(ApiModel):
    total_observations: int
    total_countries: int
    total_aggregates: int
    issue_counts: dict[str, int]
    flag_counts: dict[str, int]
    unresolved_entities: list[str]
    coverage: list[IndicatorCoverage]
    issues: list[QualityIssue]
    issues_truncated: int


class WarehouseInfo(ApiModel):
    schema_version: int
    built_at: str | None
    observations: int
    countries: int
    indicators: int


class HealthResponse(ApiModel):
    status: str
    name: str
    version: str
    environment: str


# ------------------------------------------------------------- forecasting


class ForecastModel(ApiModel):
    id: str
    indicator_id: str
    name: str
    kind: str = Field(description="'ml', 'baseline' or 'external' (the IMF benchmark)")
    is_champion: bool
    description: str


class HistoryPoint(ApiModel):
    year: int
    value: float


class ForecastPoint(ApiModel):
    origin_year: int
    target_year: int
    horizon: int
    point: float
    lower_80: float | None
    upper_80: float | None
    lower_95: float | None
    upper_95: float | None


class ModelForecasts(ApiModel):
    model_id: str
    points: list[ForecastPoint]


class BacktestPoint(ApiModel):
    origin_year: int
    target_year: int
    horizon: int
    actual: float
    point: float
    lower_80: float | None
    upper_80: float | None


class ModelBacktest(ApiModel):
    model_id: str
    points: list[BacktestPoint]


class Contribution(ApiModel):
    feature: str
    feature_value: float | None
    contribution: float = Field(description="TreeSHAP value on the signed-log scale")


class ForecastDrivers(ApiModel):
    target_year: int
    contributions: list[Contribution]


class CountryForecastResponse(ApiModel):
    country: Country
    indicator: Indicator
    champion: ForecastModel
    history: list[HistoryPoint]
    forecasts: list[ModelForecasts]
    backtest: list[ModelBacktest]
    drivers: list[ForecastDrivers]


class ForecastSnapshotValue(ApiModel):
    iso3: str
    country: str
    region: str | None
    origin_year: int
    target_year: int
    point: float
    lower_80: float | None
    upper_80: float | None


class ForecastSnapshotResponse(ApiModel):
    model: ForecastModel
    horizon: int
    values: list[ForecastSnapshotValue]


class AnomalyScore(ApiModel):
    iso3: str
    country: str
    year: int
    score: float = Field(description="Out-of-fold P(cell is an imputation artefact)")
    is_flagged: bool


# ------------------------------------------------------------------ tools


class PurchasingPowerPoint(ApiModel):
    year: int
    index: float
    value: float
    projected: bool


class PurchasingPowerResponse(ApiModel):
    country: Country
    amount: float
    from_year: int
    to_year: int
    equivalent: float
    cumulative_inflation_pct: float
    annualised_inflation_pct: float
    uses_projection: bool
    last_observed_year: int
    path: list[PurchasingPowerPoint]
