"""Declarative catalogue of indicators and their raw sources.

Two ideas keep this layer honest:

1. **Columns are addressed by header label, never by position.** Two of the raw
   files carry an unnamed pandas index column, which is what made the previous
   implementation return ``"Country name"`` as a data year and crash the
   correlation endpoint with ``float('India')``. Year columns are discovered by
   matching a four-digit header, so an extra leading or trailing column simply
   cannot shift the data.
2. **Derived indicators are computed here, not vendored.** The repository used to
   ship ``real_growth.csv`` as an opaque artefact. It is in fact
   ``wage_growth - inflation``, so it is now recomputed from its inputs where
   both inputs genuinely exist (see :mod:`realgrowth.etl.derive`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

YEAR_HEADER = re.compile(r"^(19|20)\d{2}$")

# Indicator ids
GDP_PER_CAPITA = "gdp_per_capita"
INFLATION_RATE = "inflation_rate"
AVG_WAGE = "avg_wage"
DEBT_TO_GDP = "debt_to_gdp"
HEALTHY_DIET_COST = "healthy_diet_cost"
RURAL_POPULATION = "rural_population"
URBAN_POPULATION = "urban_population"
NOMINAL_WAGE_GROWTH = "nominal_wage_growth"
REAL_WAGE_GROWTH = "real_wage_growth"
POPULATION = "population"
URBANISATION_RATE = "urbanisation_rate"


@dataclass(frozen=True, slots=True)
class Indicator:
    """Presentation and provenance metadata for one measurable series."""

    id: str
    name: str
    unit: str
    unit_symbol: str
    description: str
    source: str
    source_url: str
    #: ``1`` if a higher value is better, ``-1`` if lower is better, ``0`` neutral.
    direction: int
    decimals: int
    #: Inclusive range of physically possible values; anything outside is a
    #: transcription error and is dropped rather than served.
    valid_range: tuple[float, float]
    is_derived: bool = False
    #: Ids this indicator is computed from (derived indicators only).
    depends_on: tuple[str, ...] = ()


_WORLD_BANK = "World Bank Open Data"
_WB_URL = "https://data.worldbank.org"
_MACROTRENDS = "Macrotrends"
_MT_URL = "https://www.macrotrends.net"
_OWID = "Our World in Data (FAO)"
_OWID_URL = "https://ourworldindata.org/grapher/cost-healthy-diet"
_ILO = "ILOSTAT, converted to USD with World Bank exchange rates"
_ILO_URL = "https://ilostat.ilo.org"

INDICATORS: dict[str, Indicator] = {
    ind.id: ind
    for ind in (
        Indicator(
            id=REAL_WAGE_GROWTH,
            name="Real wage growth",
            unit="% per year",
            unit_symbol="%",
            description=(
                "Year-on-year change in the average wage after subtracting consumer "
                "price inflation: positive means pay outpaced prices, negative means "
                "workers lost purchasing power. Important caveat: wages are "
                "denominated in US dollars while inflation is domestic CPI, so this "
                "blends wage movement with exchange-rate movement against the dollar. "
                "A country can show negative real growth largely because its currency "
                "weakened, which is why 2022 looks severe for Europe and Japan."
            ),
            source="Derived: nominal wage growth minus inflation",
            source_url=_ILO_URL,
            direction=1,
            decimals=2,
            valid_range=(-1_000.0, 1_000.0),
            is_derived=True,
            depends_on=(NOMINAL_WAGE_GROWTH, INFLATION_RATE),
        ),
        Indicator(
            id=NOMINAL_WAGE_GROWTH,
            name="Nominal wage growth",
            unit="% per year",
            unit_symbol="%",
            description=(
                "Year-on-year change in the average monthly wage in current US "
                "dollars, before adjusting for inflation."
            ),
            source="Derived: year-on-year change in average wage",
            source_url=_ILO_URL,
            direction=1,
            decimals=2,
            valid_range=(-100.0, 1_000.0),
            is_derived=True,
            depends_on=(AVG_WAGE,),
        ),
        Indicator(
            id=AVG_WAGE,
            name="Average wage",
            unit="USD per month",
            unit_symbol="$",
            description=(
                "Average monthly earnings of employees, converted to current US "
                "dollars using World Bank exchange rates."
            ),
            source=_ILO,
            source_url=_ILO_URL,
            direction=1,
            decimals=0,
            valid_range=(0.0, 100_000.0),
        ),
        Indicator(
            id=INFLATION_RATE,
            name="Inflation rate",
            unit="% per year",
            unit_symbol="%",
            description=(
                "Annual change in the consumer price index (World Bank series "
                "FP.CPI.TOTL.ZG)."
            ),
            source=_WORLD_BANK,
            source_url=f"{_WB_URL}/indicator/FP.CPI.TOTL.ZG",
            direction=-1,
            decimals=2,
            valid_range=(-100.0, 100_000.0),
        ),
        Indicator(
            id=GDP_PER_CAPITA,
            name="GDP per capita",
            unit="USD",
            unit_symbol="$",
            description="Gross domestic product divided by population, in current US dollars.",
            source=_WORLD_BANK,
            source_url=f"{_WB_URL}/indicator/NY.GDP.PCAP.CD",
            direction=1,
            decimals=0,
            valid_range=(0.0, 500_000.0),
        ),
        Indicator(
            id=DEBT_TO_GDP,
            name="Government debt to GDP",
            unit="% of GDP",
            unit_symbol="%",
            description="Gross general government debt expressed as a share of GDP.",
            source=_MACROTRENDS,
            source_url=f"{_MT_URL}/global-metrics/countries/ranking/debt-to-gdp-ratio",
            direction=-1,
            decimals=2,
            valid_range=(0.0, 1_000.0),
        ),
        Indicator(
            id=HEALTHY_DIET_COST,
            name="Cost of a healthy diet",
            unit="USD per person per day (PPP)",
            unit_symbol="$",
            description=(
                "Least-cost daily diet meeting dietary guidelines, in "
                "purchasing-power-parity dollars per person per day."
            ),
            source=_OWID,
            source_url=_OWID_URL,
            direction=-1,
            decimals=2,
            valid_range=(0.0, 100.0),
        ),
        Indicator(
            id=URBANISATION_RATE,
            name="Urbanisation rate",
            unit="% of population",
            unit_symbol="%",
            description="Share of the population living in urban areas.",
            source="Derived: urban / (urban + rural) population",
            source_url=_MT_URL,
            direction=0,
            decimals=2,
            valid_range=(0.0, 100.0),
            is_derived=True,
            depends_on=(URBAN_POPULATION, RURAL_POPULATION),
        ),
        Indicator(
            id=POPULATION,
            name="Total population",
            unit="people",
            unit_symbol="",
            description="Total population, computed as urban plus rural population.",
            source="Derived: urban + rural population",
            source_url=_MT_URL,
            direction=0,
            decimals=0,
            valid_range=(0.0, 3_000_000_000.0),
            is_derived=True,
            depends_on=(URBAN_POPULATION, RURAL_POPULATION),
        ),
        Indicator(
            id=URBAN_POPULATION,
            name="Urban population",
            unit="people",
            unit_symbol="",
            description="Number of people living in urban areas.",
            source=_MACROTRENDS,
            source_url=f"{_MT_URL}/global-metrics/countries/ranking/urban-population",
            direction=0,
            decimals=0,
            valid_range=(0.0, 3_000_000_000.0),
        ),
        Indicator(
            id=RURAL_POPULATION,
            name="Rural population",
            unit="people",
            unit_symbol="",
            description="Number of people living in rural areas.",
            source=_MACROTRENDS,
            source_url=f"{_MT_URL}/global-metrics/countries/ranking/rural-population",
            direction=0,
            decimals=0,
            valid_range=(0.0, 3_000_000_000.0),
        ),
    )
}


@dataclass(frozen=True, slots=True)
class SourceSpec:
    """How to read one wide-format vendor CSV."""

    indicator_id: str
    filename: str
    #: Header label of the column holding the entity name.
    name_column: str
    #: Header label of an ISO3 column, when the source provides one.
    code_column: str | None = None
    #: Header labels that look like years but must be ignored.
    ignore_columns: frozenset[str] = field(default_factory=frozenset)


SOURCES: tuple[SourceSpec, ...] = (
    SourceSpec(GDP_PER_CAPITA, "gdp_per_capita.csv", name_column="Country Name"),
    SourceSpec(INFLATION_RATE, "inflation_rate.csv", name_column="Country"),
    SourceSpec(AVG_WAGE, "avg_wage.csv", name_column="Country name"),
    SourceSpec(DEBT_TO_GDP, "debt_to_gdp.csv", name_column="Country Name"),
    SourceSpec(
        HEALTHY_DIET_COST,
        "healthy_diet_cost.csv",
        name_column="Entity",
        code_column="Code",
    ),
    SourceSpec(RURAL_POPULATION, "rural_population.csv", name_column="Country Name"),
    SourceSpec(URBAN_POPULATION, "urban_population.csv", name_column="Country Name"),
)


def indicator(indicator_id: str) -> Indicator:
    """Look up indicator metadata, raising a clear error for typos."""
    try:
        return INDICATORS[indicator_id]
    except KeyError as exc:
        known = ", ".join(sorted(INDICATORS))
        raise KeyError(f"unknown indicator {indicator_id!r}; known ids: {known}") from exc
