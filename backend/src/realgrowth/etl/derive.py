"""Derived indicators, computed from ingested series.

The chain is::

    avg_wage (USD)  x  exchange_rate (LCU per USD)  ->  avg_wage_lcu
    avg_wage_lcu year-on-year change                ->  nominal_wage_growth
    nominal_wage_growth  -  inflation_rate          ->  real_wage_growth

Two historical defects shaped it.

**Opaque artefact.** The previous version shipped ``real_growth.csv`` as a
vendored file. Reverse-engineering showed it equals ``wage_percentage_change -
inflation_rate`` exactly, and that where the wage series had no observation the
notebook emitted a nominal growth of ``0.0`` rather than a null, so "real growth"
silently became ``-inflation`` (Afghanistan 2021-22). Recomputing here fixes
that by construction: a growth rate requires the wage level in both years.

**Currency mixing.** The notebook produced USD wages as ``local wage / exchange
rate`` and then subtracted *domestic* CPI inflation from *USD* wage growth, so a
currency depreciation looked like a real-wage collapse. Multiplying back by the
same World Bank exchange rate recovers the local-currency wage, and every growth
rate here is computed in local currency.
"""

from __future__ import annotations

from realgrowth.etl.sources import (
    AVG_WAGE,
    AVG_WAGE_LCU,
    EXCHANGE_RATE,
    INFLATION_RATE,
    NOMINAL_WAGE_GROWTH,
    REAL_WAGE_GROWTH,
    Indicator,
    indicator,
)
from realgrowth.etl.transform import Issue, Observation, SeriesFlag

Series = dict[tuple[str, str], dict[int, float]]
DerivationResult = tuple[list[Observation], list[Issue], list[SeriesFlag]]

# ---------------------------------------------------------------------------
# Plausibility thresholds for the wage chain.
#
# The upstream notebook imputed missing wage cells by scaling the cross-country
# average by each country's average ratio to it. That fills gaps but introduces
# step changes that are not wage movements. A large move is only credible when
# prices moved too: in local currency, nominal wages in a 100%-inflation economy
# genuinely double. So a transition is rejected only when it is both extreme
# *and* unexplained by inflation. ``docs/ANOMALY_DETECTION.md`` evaluates this
# rule against statistical and ML detectors on labelled data.
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


def derive_wage_lcu(series: Series) -> DerivationResult:
    """Local-currency wage: the USD wage times the LCU-per-USD exchange rate.

    A year without an exchange rate yields no observation rather than an
    assumed rate, so currency gaps surface as wage gaps.
    """
    meta = indicator(AVG_WAGE_LCU)
    observations: list[Observation] = []
    issues: list[Issue] = []
    for (indicator_id, iso3), usd_levels in sorted(series.items()):
        if indicator_id != AVG_WAGE:
            continue
        rates = series.get((EXCHANGE_RATE, iso3), {})
        for year, usd in sorted(usd_levels.items()):
            rate = rates.get(year)
            if rate is None or rate <= 0:
                continue
            obs, issue = _emit(meta, iso3, year, usd * rate)
            if obs:
                observations.append(obs)
            if issue:
                issues.append(issue)
    return observations, issues, []


def derive_nominal_wage_growth(
    series: Series, imputed_cells: frozenset[tuple[str, int]] = frozenset()
) -> DerivationResult:
    """Year-on-year change in the local-currency wage.

    Two filters, in order:

    1. **Known imputed cells.** ``imputed_cells`` holds ``(iso3, year)`` wage
       cells proven to be imputed by the forensic reconstruction in
       ``realgrowth_ml.anomaly`` (exact labels, not model guesses). A growth
       rate with an invented endpoint is not a measurement, so it is dropped.
    2. **Plausibility rule.** A remaining move too large for inflation to
       explain is rejected — the fallback when no labels are available, and a
       guard against artefacts the labels cannot see.
    """
    meta = indicator(NOMINAL_WAGE_GROWTH)
    observations: list[Observation] = []
    issues: list[Issue] = []
    flags: list[SeriesFlag] = []

    for (indicator_id, iso3), levels in sorted(series.items()):
        if indicator_id != AVG_WAGE_LCU:
            continue
        inflation = series.get((INFLATION_RATE, iso3), {})
        rejected: list[int] = []
        imputed: list[int] = []

        for year, value in sorted(year_on_year_change(levels).items()):
            if (iso3, year) in imputed_cells or (iso3, year - 1) in imputed_cells:
                imputed.append(year)
                issues.append(
                    Issue(
                        kind="imputed_input",
                        indicator_id=meta.id,
                        entity=iso3,
                        year=year,
                        detail=(
                            f"wage level for {year - 1} or {year} was imputed upstream "
                            "(forensic label); growth rate not computed"
                        ),
                    )
                )
                continue
            price_change = inflation.get(year)
            if is_implausible_growth(value, price_change):
                rejected.append(year)
                against = "no" if price_change is None else f"{price_change:+.1f}%"
                issues.append(
                    Issue(
                        kind="implausible_growth",
                        indicator_id=meta.id,
                        entity=iso3,
                        year=year,
                        detail=(
                            f"{value:+.1f}% wage move against {against} inflation; "
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
            flags.append(SeriesFlag(AVG_WAGE_LCU, iso3, "volatile_levels", detail))
            flags.append(SeriesFlag(meta.id, iso3, "partial_coverage", detail))
            flags.append(SeriesFlag(REAL_WAGE_GROWTH, iso3, "partial_coverage", detail))

        if imputed:
            detail = (
                f"{len(imputed)} growth rate(s) ({_year_span(imputed)}) omitted because the "
                "underlying wage level was imputed by the original data provider"
            )
            flags.append(SeriesFlag(AVG_WAGE, iso3, "imputed_levels", detail))
            flags.append(SeriesFlag(AVG_WAGE_LCU, iso3, "imputed_levels", detail))
            flags.append(SeriesFlag(meta.id, iso3, "imputed_inputs", detail))
            flags.append(SeriesFlag(REAL_WAGE_GROWTH, iso3, "imputed_inputs", detail))

    return observations, issues, flags


def _year_span(years: list[int]) -> str:
    """Compact year list: [2006, 2007, 2008, 2012] -> '2006-2008, 2012'."""
    runs: list[list[int]] = []
    for year in sorted(years):
        if runs and year == runs[-1][-1] + 1:
            runs[-1].append(year)
        else:
            runs.append([year])
    return ", ".join(str(r[0]) if len(r) == 1 else f"{r[0]}-{r[-1]}" for r in runs)


def derive_real_wage_growth(series: Series) -> DerivationResult:
    """Nominal wage growth minus inflation — the project's headline indicator.

    Because implausible transitions were already rejected upstream, a real wage
    growth figure only exists where the wage move itself was credible.
    """
    meta = indicator(REAL_WAGE_GROWTH)
    observations: list[Observation] = []
    issues: list[Issue] = []
    for (indicator_id, iso3), nominal in sorted(series.items()):
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


#: Ordered: each step consumes the previous step's output.
DERIVATIONS = (
    derive_wage_lcu,
    derive_nominal_wage_growth,
    derive_real_wage_growth,
)


def derive_all(
    series: Series, imputed_cells: frozenset[tuple[str, int]] = frozenset()
) -> DerivationResult:
    """Run every derivation, feeding each result back so later steps can use it."""
    produced: list[Observation] = []
    issues: list[Issue] = []
    flags: list[SeriesFlag] = []
    for step in DERIVATIONS:
        if step is derive_nominal_wage_growth:
            observations, step_issues, step_flags = derive_nominal_wage_growth(
                series, imputed_cells
            )
        else:
            observations, step_issues, step_flags = step(series)
        produced.extend(observations)
        issues.extend(step_issues)
        flags.extend(step_flags)
        for obs in observations:
            series.setdefault((obs.indicator_id, obs.iso3), {})[obs.year] = obs.value
    return produced, issues, flags
