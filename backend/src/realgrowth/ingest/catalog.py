"""Catalogue of every series fetched from a public API.

Each entry names the warehouse indicator it feeds, the upstream source and the
upstream series code. Adding a World Bank indicator to the project is one line
here plus one :class:`~realgrowth.etl.sources.Indicator` entry for its
presentation metadata.

Source choice, in short (see ``docs/DATA.md`` for the long version):

* **World Bank WDI** is the backbone: one consistent API, ISO3 codes, 1960
  onwards, no key, and the series the original project scraped second-hand from
  Macrotrends (population, urbanisation) come from here anyway.
* **IMF World Economic Outlook** (DataMapper API) supplies general government
  debt, which the World Bank covers poorly, and the IMF's own inflation
  projections, which serve as the external benchmark for our forecasts.
* **Our World in Data** republishes the FAO cost-of-a-healthy-diet series in a
  tidy CSV with ISO3 codes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Source = Literal["worldbank", "imf", "owid"]


@dataclass(frozen=True, slots=True)
class SeriesSpec:
    """One upstream series and the snapshot file it is written to."""

    id: str
    source: Source
    code: str
    #: For IMF series: whether to keep historical years, projected years or both.
    #: The DataMapper API does not mark which years are projections, so the
    #: split uses the WEO convention: years up to the vintage year minus one are
    #: actuals or estimates, later years are projections.
    imf_part: Literal["history", "projection", "all"] = "all"

    @property
    def filename(self) -> str:
        return f"{self.id}.csv"


WORLD_BANK_SERIES: tuple[SeriesSpec, ...] = (
    SeriesSpec("inflation_rate", "worldbank", "FP.CPI.TOTL.ZG"),
    SeriesSpec("cpi_index", "worldbank", "FP.CPI.TOTL"),
    SeriesSpec("gdp_deflator_inflation", "worldbank", "NY.GDP.DEFL.KD.ZG"),
    SeriesSpec("gdp_per_capita", "worldbank", "NY.GDP.PCAP.CD"),
    SeriesSpec("gdp_per_capita_ppp", "worldbank", "NY.GDP.PCAP.PP.CD"),
    SeriesSpec("gdp_growth", "worldbank", "NY.GDP.MKTP.KD.ZG"),
    SeriesSpec("unemployment_rate", "worldbank", "SL.UEM.TOTL.ZS"),
    SeriesSpec("broad_money_growth", "worldbank", "FM.LBL.BMNY.ZG"),
    SeriesSpec("exchange_rate", "worldbank", "PA.NUS.FCRF"),
    SeriesSpec("current_account", "worldbank", "BN.CAB.XOKA.GD.ZS"),
    SeriesSpec("trade_openness", "worldbank", "NE.TRD.GNFS.ZS"),
    SeriesSpec("real_interest_rate", "worldbank", "FR.INR.RINR"),
    SeriesSpec("population", "worldbank", "SP.POP.TOTL"),
    SeriesSpec("urban_population", "worldbank", "SP.URB.TOTL"),
    SeriesSpec("rural_population", "worldbank", "SP.RUR.TOTL"),
    SeriesSpec("urbanisation_rate", "worldbank", "SP.URB.TOTL.IN.ZS"),
    SeriesSpec("gini_index", "worldbank", "SI.POV.GINI"),
    SeriesSpec("poverty_rate", "worldbank", "SI.POV.DDAY"),
)

IMF_SERIES: tuple[SeriesSpec, ...] = (
    SeriesSpec("debt_to_gdp", "imf", "GGXWDG_NGDP", imf_part="history"),
    SeriesSpec("imf_inflation_forecast", "imf", "PCPIPCH", imf_part="projection"),
)

OWID_SERIES: tuple[SeriesSpec, ...] = (
    SeriesSpec("healthy_diet_cost", "owid", "cost-healthy-diet"),
)

ALL_SERIES: tuple[SeriesSpec, ...] = WORLD_BANK_SERIES + IMF_SERIES + OWID_SERIES

#: IMF DataMapper codes that differ from the ISO3 codes the registry uses.
IMF_CODE_FIXES: dict[str, str] = {"UVK": "XKX", "WBG": "PSE", "WEOWORLD": "WLD"}


def series_by_id() -> dict[str, SeriesSpec]:
    return {spec.id: spec for spec in ALL_SERIES}
