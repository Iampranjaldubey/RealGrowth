"""Derived indicators, computed from ingested series.

The previous version of this project shipped ``real_growth.csv`` as an opaque
vendored artefact. Reverse-engineering it showed that, for all 1,530 populated
cells, it equals ``wage_percentage_change - inflation_rate`` exactly — it is real
wage growth.

It also showed the artefact was partly fabricated. Where the wage series had no
observation, the upstream notebook emitted a nominal growth of ``0.0`` rather
than a null, so ``real growth`` silently became ``-inflation``. Afghanistan, for
instance, was published as -5.13% in 2021 and -13.71% in 2022 purely because
those are the negated inflation rates; there is no Afghan wage data for either
year.

Recomputing here fixes that by construction: a growth rate requires the wage
level in both years, so a missing level yields no observation instead of an
invented one.
"""

from __future__ import annotations

from realgrowth.etl.sources import (
    AVG_WAGE,
    INFLATION_RATE,
    NOMINAL_WAGE_GROWTH,
    POPULATION,
    REAL_WAGE_GROWTH,
    RURAL_POPULATION,
    URBAN_POPULATION,
    URBANISATION_RATE,
    Indicator,
    indicator,
)
from realgrowth.etl.transform import Issue, Observation, SeriesFlag

Series = dict[tuple[str, str], dict[int, float]]

# ---------------------------------------------------------------------------
# Plausibility thresholds for the wage chain.
#
# The upstream notebook imputed missing wage cells by scaling the world average
# by each country's average ratio to it. That fills gaps but introduces step
# changes that are not wage movements: Spain is recorded as +147% in 2022 against
# 8.4% inflation, the Netherlands +125%, Singapore +125%. 8% of all transitions
# are affected, clustered in 2022.
#
# A large move is only credible when prices moved too. Zimbabwe's -162% real wage
# growth in 2022 is real — inflation there exceeded 100%. So a transition is
# rejected only when it is both extreme *and* unexplained by inflation.
# ---------------------------------------------------------------------------

#: A year-on-year wage move beyond this magnitude needs a price-level explanation.
IMPLAUSIBLE_GROWTH_PCT = 40.0

#: Inflation at or above this magnitude explains an extreme wage move.
INFLATION_EXPLAINS_PCT = 25.0

#: Countries with at least this many rejected transitions get a series-level flag.
VOLATILE_SERIES_MIN_REJECTS = 1


def is_implausible_growth(growth: float, inflation: float | None) -> bool:
    """Whether a year-on-year wage move is too large to be believed.

    ``growth`` and ``inflation`` are percentages. A move is implausible when it
    exceeds :data:`IMPLAUSIBLE_GROWTH_PCT` and inflation does not corroborate it.
    """
    if abs(growth) <= IMPLAUSIBLE_GROWTH_PCT:
        return False
    return inflation is None or abs(inflation) < INFLATION_EXPLAINS_PCT


def _emit(
    meta: Indicator, iso3: str, year: int, value: float
) -> tuple[Observation | None, Issue | None]:
    """Range-check a derived value before admitting it to the warehouse."""
    low, high = meta.valid_range
    if not low <= value <= high:
        return None, Issue(
            kind="out_of_range",
            indicator_id=meta.id,
            entity=iso3,
            year=year,
            detail=f"derived value {value!r} outside [{low}, {high}]; dropped",
        )
    return Observation(meta.id, iso3, year, value), None


def year_on_year_change(levels: dict[int, float]) -> dict[int, float]:
    """Percent change versus the previous year.

    Only consecutive year pairs count: a 2015 level followed by a 2019 level does
    not produce a 2019 "annual" growth rate. Years where the base is zero are
    skipped because the percent change is undefined.
    """
    out: dict[int, float] = {}
    for year, value in levels.items():
        previous = levels.get(year - 1)
        if previous is None or previous == 0:
            continue
        out[year] = (value - previous) / previous * 100.0
    return out


def derive_nominal_wage_growth(
    series: Series,
) -> tuple[list[Observation], list[Issue], list[SeriesFlag]]:
    """Year-on-year change in the average wage, rejecting implausible transitions."""
    meta = indicator(NOMINAL_WAGE_GROWTH)
    observations: list[Observation] = []
    issues: list[Issue] = []
    flags: list[SeriesFlag] = []

    for (indicator_id, iso3), levels in sorted(series.items()):
        if indicator_id != AVG_WAGE:
            continue
        inflation = series.get((INFLATION_RATE, iso3), {})
        rejected: list[int] = []

        for year, value in sorted(year_on_year_change(levels).items()):
            price_change = inflation.get(year)
            if is_implausible_growth(value, price_change):
                rejected.append(year)
                issues.append(
                    Issue(
                        kind="implausible_growth",
                        indicator_id=meta.id,
                        entity=iso3,
                        year=year,
                        detail=(
                            f"{value:+.1f}% wage move against "
                            f"{'no' if price_change is None else format(price_change, '+.1f')}"
                            f"{'' if price_change is None else '%'} inflation; "
                            "rejected as an imputation artefact"
                        ),
                    )
                )
                continue
            obs, issue = _emit(meta, iso3, year, value)
            if obs:
                observations.append(obs)
            if issue:
                issues.append(issue)

        if len(rejected) >= VOLATILE_SERIES_MIN_REJECTS:
            detail = (
                f"{len(rejected)} year-on-year move(s) "
                f"({', '.join(str(y) for y in rejected)}) exceed "
                f"{IMPLAUSIBLE_GROWTH_PCT:.0f}% without matching inflation, indicating "
                "imputed wage levels; treat absolute values with caution"
            )
            flags.append(SeriesFlag(AVG_WAGE, iso3, "volatile_levels", detail))
            flags.append(SeriesFlag(meta.id, iso3, "partial_coverage", detail))
            flags.append(SeriesFlag(REAL_WAGE_GROWTH, iso3, "partial_coverage", detail))

    return observations, issues, flags


def derive_real_wage_growth(
    series: Series,
) -> tuple[list[Observation], list[Issue], list[SeriesFlag]]:
    """Nominal wage growth minus inflation — the project's headline indicator.

    Because implausible transitions were already rejected upstream, a real wage
    growth figure only exists where the wage move itself was credible.
    """
    meta = indicator(REAL_WAGE_GROWTH)
    observations: list[Observation] = []
    issues: list[Issue] = []
    for (indicator_id, iso3), nominal in series.items():
        if indicator_id != NOMINAL_WAGE_GROWTH:
            continue
        inflation = series.get((INFLATION_RATE, iso3))
        if not inflation:
            continue
        for year, growth in sorted(nominal.items()):
            price_change = inflation.get(year)
            if price_change is None:
                continue
            obs, issue = _emit(meta, iso3, year, growth - price_change)
            if obs:
                observations.append(obs)
            if issue:
                issues.append(issue)
    return observations, issues, []


def derive_population(
    series: Series,
) -> tuple[list[Observation], list[Issue], list[SeriesFlag]]:
    """Total population and urbanisation rate from the urban/rural split."""
    total_meta = indicator(POPULATION)
    rate_meta = indicator(URBANISATION_RATE)
    observations: list[Observation] = []
    issues: list[Issue] = []
    for (indicator_id, iso3), urban_levels in series.items():
        if indicator_id != URBAN_POPULATION:
            continue
        rural_levels = series.get((RURAL_POPULATION, iso3))
        if not rural_levels:
            continue
        for year, urban in sorted(urban_levels.items()):
            rural = rural_levels.get(year)
            if rural is None:
                continue
            total = urban + rural
            obs, issue = _emit(total_meta, iso3, year, total)
            if obs:
                observations.append(obs)
            if issue:
                issues.append(issue)
            if total > 0:
                obs, issue = _emit(rate_meta, iso3, year, urban / total * 100.0)
                if obs:
                    observations.append(obs)
                if issue:
                    issues.append(issue)
    return observations, issues, []


#: Ordered because ``real_wage_growth`` consumes ``nominal_wage_growth``.
DERIVATIONS = (
    derive_nominal_wage_growth,
    derive_real_wage_growth,
    derive_population,
)


def derive_all(
    series: Series,
) -> tuple[list[Observation], list[Issue], list[SeriesFlag]]:
    """Run every derivation, feeding each result back so later steps can use it."""
    produced: list[Observation] = []
    issues: list[Issue] = []
    flags: list[SeriesFlag] = []
    for step in DERIVATIONS:
        observations, step_issues, step_flags = step(series)
        produced.extend(observations)
        issues.extend(step_issues)
        flags.extend(step_flags)
        for obs in observations:
            series.setdefault((obs.indicator_id, obs.iso3), {})[obs.year] = obs.value
    return produced, issues, flags
