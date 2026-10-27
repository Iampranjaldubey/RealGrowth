"""Read the warehouse into pandas.

The ML package never parses raw files: it reads the same SQLite warehouse the
API serves, so a model is trained on exactly the cleaned, ISO3-keyed,
range-checked data a user sees.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class Panel:
    """Country-year observations plus the country dimension."""

    observations: pd.DataFrame  # indicator_id, iso3, year, value
    countries: pd.DataFrame  # iso3 (index), name, region, is_aggregate
    built_at: str | None = None

    def wide(self, indicator_id: str, *, countries_only: bool = True) -> pd.DataFrame:
        """``iso3 x year`` matrix for one indicator, with contiguous year columns."""
        rows = self.observations[self.observations["indicator_id"] == indicator_id]
        if countries_only:
            keep = self.countries.index[~self.countries["is_aggregate"]]
            rows = rows[rows["iso3"].isin(keep)]
        matrix = rows.pivot(index="iso3", columns="year", values="value")
        if matrix.empty:
            return matrix
        years = range(int(matrix.columns.min()), int(matrix.columns.max()) + 1)
        return matrix.reindex(columns=list(years)).sort_index()

    @property
    def country_ids(self) -> list[str]:
        return sorted(self.countries.index[~self.countries["is_aggregate"]])


def load_panel(db_path: str | Path) -> Panel:
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found; build it with `python -m realgrowth.etl`")
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
        observations = pd.read_sql_query(
            "SELECT indicator_id, iso3, year, value FROM observations", connection
        )
        countries = pd.read_sql_query(
            "SELECT iso3, name, region, is_aggregate FROM countries", connection
        ).set_index("iso3")
        built = connection.execute(
            "SELECT value FROM etl_metadata WHERE key = 'built_at'"
        ).fetchone()
    countries["is_aggregate"] = countries["is_aggregate"].astype(bool)
    observations["year"] = observations["year"].astype(int)
    return Panel(observations, countries, built[0] if built else None)


def panel_from_frames(observations: pd.DataFrame, countries: pd.DataFrame | None = None) -> Panel:
    """Build a panel in memory (tests and notebooks)."""
    obs = observations.copy()
    obs["year"] = obs["year"].astype(int)
    if countries is None:
        countries = pd.DataFrame(
            {
                "iso3": sorted(obs["iso3"].unique()),
                "name": sorted(obs["iso3"].unique()),
                "region": "Test",
                "is_aggregate": False,
            }
        ).set_index("iso3")
    return Panel(obs, countries)
