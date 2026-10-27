"""Declarative catalogue of indicators and where each one comes from.

Three kinds of indicator live here:

1. **API series** — fetched by :mod:`realgrowth.ingest` from the World Bank, the
   IMF or Our World in Data into ``data/raw/api/<id>.csv``. Their ids match
   the ingest catalogue's series ids one-to-one.
2. **Legacy CSV series** — only ``avg_wage``, which comes from an ILOSTAT
   extract converted to USD in the original project's notebooks; there is no
   keyless API for it. It is read from a wide CSV by header label, never by
   column position (two of the original files had an unnamed pandas index
   column that once shifted every value by one).
3. **Derived series** — computed in :mod:`realgrowth.etl.derive` from the above.

The headline indicator, real wage growth, used to be computed from wages in
*US dollars* minus *domestic* inflation, which mixes exchange-rate swings into a
"real" wage. The upstream notebook built the USD wage as ``local wage /
exchange rate``, so multiplying by the World Bank exchange rate recovers the
local-currency wage, and real wage growth is now computed entirely in local
currency — the definition the ILO and OECD use.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

YEAR_HEADER = re.compile(r"^(19|20)\d{2}$")

# ----------------------------------------------------------- indicator ids
# Wages and prices
REAL_WAGE_GROWTH = "real_wage_growth"
NOMINAL_WAGE_GROWTH = "nominal_wage_growth"
AVG_WAGE = "avg_wage"
AVG_WAGE_LCU = "avg_wage_lcu"
INFLATION_RATE = "inflation_rate"
CPI_INDEX = "cpi_index"
GDP_DEFLATOR_INFLATION = "gdp_deflator_inflation"
HEALTHY_DIET_COST = "healthy_diet_cost"
# Output
GDP_PER_CAPITA = "gdp_per_capita"
GDP_PER_CAPITA_PPP = "gdp_per_capita_ppp"
GDP_GROWTH = "gdp_growth"
# Labour
UNEMPLOYMENT_RATE = "unemployment_rate"
# Money and external
BROAD_MONEY_GROWTH = "broad_money_growth"
EXCHANGE_RATE = "exchange_rate"
CURRENT_ACCOUNT = "current_account"
TRADE_OPENNESS = "trade_openness"
REAL_INTEREST_RATE = "real_interest_rate"
# Public finance
DEBT_TO_GDP = "debt_to_gdp"
# Population and living standards
POPULATION = "population"
URBAN_POPULATION = "urban_population"
RURAL_POPULATION = "rural_population"
URBANISATION_RATE = "urbanisation_rate"
GINI_INDEX = "gini_index"
POVERTY_RATE = "poverty_rate"

# --------------------------------------------------------------- categories
WAGES_PRICES = "Wages & prices"
OUTPUT = "Output & growth"
LABOUR = "Labour"
MONEY_EXTERNAL = "Money & external"
PUBLIC_FINANCE = "Public finance"
PEOPLE = "Population & living standards"

CATEGORIES: tuple[str, ...] = (WAGES_PRICES, OUTPUT, LABOUR, MONEY_EXTERNAL, PUBLIC_FINANCE, PEOPLE)


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
    category: str = WAGES_PRICES
    is_derived: bool = False
    #: Ids this indicator is computed from (derived indicators only).
    depends_on: tuple[str, ...] = ()


_WB = "World Bank World Development Indicators"
_IMF = "IMF World Economic Outlook"
_OWID = "Our World in Data (FAO / World Bank Food Prices for Nutrition)"
_ILO = "ILOSTAT mean monthly earnings (legacy extract, converted to USD)"
_ILO_URL = "https://ilostat.ilo.org/topics/wages/"


def _wb(code: str) -> str:
    return f"https://data.worldbank.org/indicator/{code}"


def _imf(code: str) -> str:
    return f"https://www.imf.org/external/datamapper/{code}"


_PCT = "% per year"

INDICATORS: dict[str, Indicator] = {
    ind.id: ind
    for ind in (
        # ------------------------------------------------- wages & prices
        Indicator(
            id=REAL_WAGE_GROWTH,
            name="Real wage growth",
            unit=_PCT,
            unit_symbol="%",
            description=(
                "Year-on-year change in the average wage in local currency, minus "
                "consumer price inflation. Positive means pay outpaced prices; "
                "negative means workers lost purchasing power. Computed in local "
                "currency so exchange-rate swings do not masquerade as wage changes."
            ),
            source="Derived: nominal wage growth (local currency) minus CPI inflation",
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
            unit=_PCT,
            unit_symbol="%",
            description=(
                "Year-on-year change in the average monthly wage in local currency, "
                "before adjusting for inflation. Transitions too large to be explained "
                "by inflation are rejected as imputation artefacts."
            ),
            source="Derived: year-on-year change in the local-currency average wage",
            source_url=_ILO_URL,
            direction=1,
            decimals=2,
            valid_range=(-100.0, 100_000.0),
            is_derived=True,
            depends_on=(AVG_WAGE_LCU,),
        ),
        Indicator(
            id=AVG_WAGE_LCU,
            name="Average wage (local currency)",
            unit="local currency per month",
            unit_symbol="",
            description=(
                "Average monthly earnings in local currency units, recovered as the "
                "USD wage multiplied by the World Bank official exchange rate."
            ),
            source="Derived: average wage (USD) x official exchange rate",
            source_url=_ILO_URL,
            direction=1,
            decimals=0,
            valid_range=(0.0, 1e13),
            is_derived=True,
            depends_on=(AVG_WAGE, EXCHANGE_RATE),
        ),
        Indicator(
            id=AVG_WAGE,
            name="Average wage (USD)",
            unit="USD per month",
            unit_symbol="$",
            description=(
                "Average monthly earnings of employees in current US dollars. Some "
                "cells were imputed upstream; see the data-quality page."
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
            unit=_PCT,
            unit_symbol="%",
            description="Annual change in the consumer price index (FP.CPI.TOTL.ZG).",
            source=_WB,
            source_url=_wb("FP.CPI.TOTL.ZG"),
            direction=-1,
            decimals=2,
            valid_range=(-100.0, 1_000_000.0),
        ),
        Indicator(
            id=CPI_INDEX,
            name="Consumer price index",
            unit="index, 2010 = 100",
            unit_symbol="",
            description=(
                "Consumer price level relative to 2010. Ratios between two years "
                "give the cumulative price change, which the purchasing-power "
                "calculator uses."
            ),
            source=_WB,
            source_url=_wb("FP.CPI.TOTL"),
            direction=0,
            decimals=2,
            valid_range=(0.0, 1e18),
        ),
        Indicator(
            id=GDP_DEFLATOR_INFLATION,
            name="GDP deflator inflation",
            unit=_PCT,
            unit_symbol="%",
            description=(
                "Annual change in the GDP implicit deflator: price growth across the "
                "whole economy rather than the consumer basket."
            ),
            source=_WB,
            source_url=_wb("NY.GDP.DEFL.KD.ZG"),
            direction=-1,
            decimals=2,
            valid_range=(-100.0, 1_000_000.0),
        ),
        Indicator(
            id=HEALTHY_DIET_COST,
            name="Cost of a healthy diet",
            unit="PPP $ per person per day",
            unit_symbol="$",
            description=(
                "Least-cost daily diet meeting dietary guidelines, in "
                "purchasing-power-parity dollars per person per day."
            ),
            source=_OWID,
            source_url="https://ourworldindata.org/grapher/cost-healthy-diet",
            direction=-1,
            decimals=2,
            valid_range=(0.0, 100.0),
        ),
        # --------------------------------------------------------- output
        Indicator(
            id=GDP_PER_CAPITA,
            name="GDP per capita",
            unit="current USD",
            unit_symbol="$",
            description="Gross domestic product divided by population, in current US dollars.",
            source=_WB,
            source_url=_wb("NY.GDP.PCAP.CD"),
            direction=1,
            decimals=0,
            valid_range=(0.0, 500_000.0),
            category=OUTPUT,
        ),
        Indicator(
            id=GDP_PER_CAPITA_PPP,
            name="GDP per capita (PPP)",
            unit="current international $",
            unit_symbol="$",
            description=(
                "GDP per person at purchasing-power parity, which corrects for price "
                "level differences and is the better cross-country welfare comparison."
            ),
            source=_WB,
            source_url=_wb("NY.GDP.PCAP.PP.CD"),
            direction=1,
            decimals=0,
            valid_range=(0.0, 500_000.0),
            category=OUTPUT,
        ),
        Indicator(
            id=GDP_GROWTH,
            name="Real GDP growth",
            unit=_PCT,
            unit_symbol="%",
            description="Annual growth of GDP at constant prices.",
            source=_WB,
            source_url=_wb("NY.GDP.MKTP.KD.ZG"),
            direction=1,
            decimals=2,
            valid_range=(-100.0, 300.0),
            category=OUTPUT,
        ),
        # --------------------------------------------------------- labour
        Indicator(
            id=UNEMPLOYMENT_RATE,
            name="Unemployment rate",
            unit="% of labour force",
            unit_symbol="%",
            description="Unemployment as a share of the labour force (ILO modelled estimate).",
            source=_WB,
            source_url=_wb("SL.UEM.TOTL.ZS"),
            direction=-1,
            decimals=2,
            valid_range=(0.0, 100.0),
            category=LABOUR,
        ),
        # ----------------------------------------------- money & external
        Indicator(
            id=BROAD_MONEY_GROWTH,
            name="Broad money growth",
            unit=_PCT,
            unit_symbol="%",
            description=(
                "Annual growth of broad money (M2/M3), a classic leading indicator of inflation."
            ),
            source=_WB,
            source_url=_wb("FM.LBL.BMNY.ZG"),
            direction=0,
            decimals=2,
            valid_range=(-100.0, 1_000_000.0),
            category=MONEY_EXTERNAL,
        ),
        Indicator(
            id=EXCHANGE_RATE,
            name="Exchange rate",
            unit="local currency per USD",
            unit_symbol="",
            description=(
                "Official exchange rate, period average, local currency units per US dollar."
            ),
            source=_WB,
            source_url=_wb("PA.NUS.FCRF"),
            direction=0,
            decimals=4,
            valid_range=(0.0, 1e15),
            category=MONEY_EXTERNAL,
        ),
        Indicator(
            id=CURRENT_ACCOUNT,
            name="Current account balance",
            unit="% of GDP",
            unit_symbol="%",
            description="Current account balance as a share of GDP.",
            source=_WB,
            source_url=_wb("BN.CAB.XOKA.GD.ZS"),
            direction=0,
            decimals=2,
            valid_range=(-500.0, 500.0),
            category=MONEY_EXTERNAL,
        ),
        Indicator(
            id=TRADE_OPENNESS,
            name="Trade openness",
            unit="% of GDP",
            unit_symbol="%",
            description="Exports plus imports of goods and services as a share of GDP.",
            source=_WB,
            source_url=_wb("NE.TRD.GNFS.ZS"),
            direction=0,
            decimals=1,
            valid_range=(0.0, 2_000.0),
            category=MONEY_EXTERNAL,
        ),
        Indicator(
            id=REAL_INTEREST_RATE,
            name="Real interest rate",
            unit="%",
            unit_symbol="%",
            description="Lending interest rate adjusted for inflation by the GDP deflator.",
            source=_WB,
            source_url=_wb("FR.INR.RINR"),
            direction=0,
            decimals=2,
            valid_range=(-1_000.0, 1_000.0),
            category=MONEY_EXTERNAL,
        ),
        # ------------------------------------------------ public finance
        Indicator(
            id=DEBT_TO_GDP,
            name="Government debt to GDP",
            unit="% of GDP",
            unit_symbol="%",
            description="General government gross debt as a share of GDP (IMF WEO, history only).",
            source=_IMF,
            source_url=_imf("GGXWDG_NGDP"),
            direction=-1,
            decimals=2,
            valid_range=(0.0, 1_000.0),
            category=PUBLIC_FINANCE,
        ),
        # ------------------------------------ population & living standards
        Indicator(
            id=POPULATION,
            name="Total population",
            unit="people",
            unit_symbol="",
            description="Total resident population, mid-year estimate.",
            source=_WB,
            source_url=_wb("SP.POP.TOTL"),
            direction=0,
            decimals=0,
            valid_range=(0.0, 10_000_000_000.0),
            category=PEOPLE,
        ),
        Indicator(
            id=URBAN_POPULATION,
            name="Urban population",
            unit="people",
            unit_symbol="",
            description="Number of people living in urban areas.",
            source=_WB,
            source_url=_wb("SP.URB.TOTL"),
            direction=0,
            decimals=0,
            valid_range=(0.0, 10_000_000_000.0),
            category=PEOPLE,
        ),
        Indicator(
            id=RURAL_POPULATION,
            name="Rural population",
            unit="people",
            unit_symbol="",
            description="Number of people living in rural areas.",
            source=_WB,
            source_url=_wb("SP.RUR.TOTL"),
            direction=0,
            decimals=0,
            valid_range=(0.0, 10_000_000_000.0),
            category=PEOPLE,
        ),
        Indicator(
            id=URBANISATION_RATE,
            name="Urbanisation rate",
            unit="% of population",
            unit_symbol="%",
            description="Share of the population living in urban areas.",
            source=_WB,
            source_url=_wb("SP.URB.TOTL.IN.ZS"),
            direction=0,
            decimals=2,
            valid_range=(0.0, 100.0),
            category=PEOPLE,
        ),
        Indicator(
            id=GINI_INDEX,
            name="Gini index",
            unit="0-100",
            unit_symbol="",
            description=(
                "Income or consumption inequality; 0 is perfect equality, 100 perfect inequality."
            ),
            source=_WB,
            source_url=_wb("SI.POV.GINI"),
            direction=-1,
            decimals=1,
            valid_range=(0.0, 100.0),
            category=PEOPLE,
        ),
        Indicator(
            id=POVERTY_RATE,
            name="Extreme poverty rate",
            unit="% of population",
            unit_symbol="%",
            description="Share of people living below the international poverty line (2021 PPP).",
            source=_WB,
            source_url=_wb("SI.POV.DDAY"),
            direction=-1,
            decimals=1,
            valid_range=(0.0, 100.0),
            category=PEOPLE,
        ),
    )
}


@dataclass(frozen=True, slots=True)
class SourceSpec:
    """How to read one wide-format vendor CSV (legacy sources only)."""

    indicator_id: str
    filename: str
    #: Header label of the column holding the entity name.
    name_column: str
    #: Header label of an ISO3 column, when the source provides one.
    code_column: str | None = None
    #: Header labels that look like years but must be ignored.
    ignore_columns: frozenset[str] = field(default_factory=frozenset)


#: Wide CSVs in ``data/raw/``. Everything else now arrives through the API
#: snapshot; the files this tuple used to list live in ``data/legacy/`` for
#: provenance and for the imputation-detection study.
SOURCES: tuple[SourceSpec, ...] = (
    SourceSpec(AVG_WAGE, "avg_wage.csv", name_column="Country name"),
)

#: Indicators loaded from ``data/raw/api/<id>.csv`` (long format, ISO3-keyed).
API_INDICATORS: tuple[str, ...] = (
    INFLATION_RATE,
    CPI_INDEX,
    GDP_DEFLATOR_INFLATION,
    HEALTHY_DIET_COST,
    GDP_PER_CAPITA,
    GDP_PER_CAPITA_PPP,
    GDP_GROWTH,
    UNEMPLOYMENT_RATE,
    BROAD_MONEY_GROWTH,
    EXCHANGE_RATE,
    CURRENT_ACCOUNT,
    TRADE_OPENNESS,
    REAL_INTEREST_RATE,
    DEBT_TO_GDP,
    POPULATION,
    URBAN_POPULATION,
    RURAL_POPULATION,
    URBANISATION_RATE,
    GINI_INDEX,
    POVERTY_RATE,
)

#: API series that are not indicators: the IMF's own inflation projections,
#: stored in the ``forecasts`` table as the external benchmark.
IMF_FORECAST_SERIES = "imf_inflation_forecast"


def indicator(indicator_id: str) -> Indicator:
    """Look up indicator metadata, raising a clear error for typos."""
    try:
        return INDICATORS[indicator_id]
    except KeyError as exc:
        known = ", ".join(sorted(INDICATORS))
        raise KeyError(f"unknown indicator {indicator_id!r}; known ids: {known}") from exc
