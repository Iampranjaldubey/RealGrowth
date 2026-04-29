"""
Data Service — the single data access layer for the application.

Loads all CSV datasets once at initialization, stores them as immutable
DataFrames, and exposes clean query methods for each economic indicator.
No global state is mutated. Routes call these methods via current_app.
"""

import os
import logging

import pandas as pd

logger = logging.getLogger(__name__)


class DataService:
    """
    Encapsulates all CSV data loading and querying logic.
    Instantiated once during app creation and stored on app.config.
    """

    def __init__(self, data_dir):
        """
        Load and prepare all CSV datasets from the given directory.

        Args:
            data_dir: Absolute path to the directory containing CSV files.
        """
        logger.info(f"Loading datasets from: {data_dir}")

        # --- GDP Per Capita ---
        self._df_gdp = pd.read_csv(
            os.path.join(data_dir, "GDP_per_capita.csv"),
            on_bad_lines="skip"
        )
        self._df_gdp["Population"] = pd.to_numeric(
            self._df_gdp["Population"], errors="coerce"
        )
        self._gdp_year_columns = [
            col for col in self._df_gdp.columns if col.isdigit()
        ]
        for col in self._gdp_year_columns:
            self._df_gdp[col] = pd.to_numeric(
                self._df_gdp[col], errors="coerce"
            )

        # --- Inflation ---
        self._df_inflation = pd.read_csv(
            os.path.join(data_dir, "filled_Inflation_Rate.csv")
        )
        self._inflation_countries = self._df_inflation["Country"].tolist()
        # Pre-compute inflation data dict for fast lookups
        self._inflation_data = {}
        for country in self._inflation_countries:
            row = self._df_inflation.loc[
                self._df_inflation["Country"] == country
            ]
            values = row.drop("Country", axis=1).values.flatten().tolist()[:15]
            self._inflation_data[country] = values

        # --- Food (Healthy Diet Cost) ---
        self._df_food = pd.read_csv(
            os.path.join(data_dir, "filled_healthy_diet_cost.csv")
        )
        self._food_year_columns = [
            col for col in self._df_food.columns if col.isdigit()
        ]

        # --- Population (Rural & Urban) ---
        self._df_rural_pop = pd.read_csv(
            os.path.join(data_dir, "rural_population.csv")
        )
        self._df_urban_pop = pd.read_csv(
            os.path.join(data_dir, "urban_population.csv")
        )
        # Clean column names and country names
        for df in [self._df_rural_pop, self._df_urban_pop]:
            df["Country Name"] = df["Country Name"].str.strip()
            df.columns = df.columns.str.strip()

        # Pre-clean population numeric values (commas in strings)
        pop_year_cols = [
            c for c in self._df_rural_pop.columns if c != "Country Name"
        ]
        for col in pop_year_cols:
            self._df_rural_pop[col] = (
                self._df_rural_pop[col]
                .astype(str)
                .str.replace(",", "", regex=False)
            )
            self._df_rural_pop[col] = pd.to_numeric(
                self._df_rural_pop[col], errors="coerce"
            )
        for col in pop_year_cols:
            if col in self._df_urban_pop.columns:
                self._df_urban_pop[col] = (
                    self._df_urban_pop[col]
                    .astype(str)
                    .str.replace(",", "", regex=False)
                )
                self._df_urban_pop[col] = pd.to_numeric(
                    self._df_urban_pop[col], errors="coerce"
                )

        # --- Wages ---
        self._df_wage = pd.read_csv(
            os.path.join(data_dir, "avg_wage.csv")
        )

        # --- Debt to GDP ---
        self._df_debt = pd.read_csv(
            os.path.join(data_dir, "filled_debt_to_gdp_ratio.csv")
        )
        self._df_debt.columns = self._df_debt.columns.str.strip()

        # --- Real Growth ---
        self._df_real_growth = pd.read_csv(
            os.path.join(data_dir, "real_growth.csv")
        )
        self._df_real_growth.columns = self._df_real_growth.columns.str.strip()

        logger.info("All datasets loaded successfully")

    # ------------------------------------------------------------------ #
    #                          GDP METHODS                                 #
    # ------------------------------------------------------------------ #

    def get_gdp_years(self):
        """Return list of available GDP year columns."""
        return self._gdp_year_columns

    def get_gdp_countries(self):
        """Return sorted list of unique GDP country names."""
        return sorted(
            self._df_gdp["Country Name"].dropna().unique().tolist()
        )

    def get_gdp_top10(self, year, min_population=0):
        """
        Get the top 10 countries by GDP per capita for a given year.

        Args:
            year: Year column string (e.g., "2023").
            min_population: Minimum population filter (default 0).

        Returns:
            dict with 'labels' and 'values' lists.
        """
        if year not in self._gdp_year_columns:
            return {"labels": [], "values": []}

        filtered = self._df_gdp[
            self._df_gdp["Population"] >= min_population
        ].copy()
        filtered["gdp_per_capita"] = filtered[year]
        filtered = filtered.dropna(subset=["gdp_per_capita"])
        top10 = filtered.sort_values(
            by="gdp_per_capita", ascending=False
        ).head(10)

        return {
            "labels": top10["Country Name"].tolist(),
            "values": [round(v, 2) for v in top10["gdp_per_capita"].tolist()],
        }

    def get_gdp_compare(self, country1, country2):
        """
        Compare GDP per capita of two countries across all years.

        Returns:
            dict with 'years', 'country1', and 'country2' data.
        """
        c1_data = self._df_gdp[self._df_gdp["Country Name"] == country1]
        c2_data = self._df_gdp[self._df_gdp["Country Name"] == country2]

        if c1_data.empty or c2_data.empty:
            return None

        def extract_values(df_row):
            values = []
            for year in self._gdp_year_columns:
                val = df_row[year].iloc[0]
                if pd.notna(val):
                    values.append(round(float(val), 2))
                else:
                    values.append(None)
            return values

        return {
            "years": self._gdp_year_columns,
            "country1": {"name": country1, "data": extract_values(c1_data)},
            "country2": {"name": country2, "data": extract_values(c2_data)},
        }

    # ------------------------------------------------------------------ #
    #                       INFLATION METHODS                              #
    # ------------------------------------------------------------------ #

    def get_inflation_countries(self):
        """Return list of countries with inflation data."""
        return self._inflation_countries

    def get_inflation(self, country):
        """
        Get inflation rate data for a specific country.

        Returns:
            dict with 'country' and 'values' list, or None if not found.
        """
        if country not in self._inflation_data:
            return None
        return {"country": country, "values": self._inflation_data[country]}

    # ------------------------------------------------------------------ #
    #                     FOOD PRICE METHODS                               #
    # ------------------------------------------------------------------ #

    def get_food_countries(self):
        """Return list of countries with food price data."""
        return sorted(self._df_food["Entity"].dropna().unique().tolist())

    def get_food_compare(self, country1, country2):
        """
        Compare healthy diet costs between two countries.

        Returns:
            list of dicts with 'year', country1 value, country2 value.
        """
        selected = self._df_food[
            self._df_food["Entity"].isin([country1, country2])
        ]
        recent_years = self._food_year_columns[-5:]

        result = []
        for year in recent_years:
            row = {"year": year}
            for _, r in selected.iterrows():
                val = r[year]
                row[r["Entity"]] = (
                    round(float(val), 2) if pd.notna(val) else None
                )
            result.append(row)
        return result

    # ------------------------------------------------------------------ #
    #                      POPULATION METHODS                              #
    # ------------------------------------------------------------------ #

    def get_population_metadata(self):
        """Return available countries and years for population data."""
        countries = self._df_rural_pop["Country Name"].dropna().unique().tolist()
        years = [
            col for col in self._df_rural_pop.columns if col != "Country Name"
        ]
        return {"countries": sorted(countries), "years": years}

    def get_population_distribution(self, country, year):
        """
        Get urban vs rural population for a country in a given year.

        Returns:
            dict with 'rural' and 'urban' values, or None if not found.
        """
        if country not in self._df_rural_pop["Country Name"].values:
            return None
        if year not in self._df_rural_pop.columns:
            return None

        rural = self._df_rural_pop.loc[
            self._df_rural_pop["Country Name"] == country, year
        ].values[0]
        urban = self._df_urban_pop.loc[
            self._df_urban_pop["Country Name"] == country, year
        ].values[0]

        return {
            "rural": float(rural) if pd.notna(rural) else None,
            "urban": float(urban) if pd.notna(urban) else None,
        }

    def get_population_trend(self, country):
        """
        Get population trend over all years for a country.

        Returns:
            dict with 'rural' and 'urban' year->value dicts.
        """
        if country not in self._df_rural_pop["Country Name"].values:
            return None

        rural_row = (
            self._df_rural_pop.loc[
                self._df_rural_pop["Country Name"] == country
            ]
            .drop(columns=["Country Name"])
            .iloc[0]
        )
        urban_row = (
            self._df_urban_pop.loc[
                self._df_urban_pop["Country Name"] == country
            ]
            .drop(columns=["Country Name"])
            .iloc[0]
        )

        rural = {
            yr: float(val)
            for yr, val in rural_row.items()
            if pd.notna(val)
        }
        urban = {
            yr: float(val)
            for yr, val in urban_row.items()
            if pd.notna(val)
        }
        return {"rural": rural, "urban": urban}

    # ------------------------------------------------------------------ #
    #                        WAGES METHODS                                 #
    # ------------------------------------------------------------------ #

    def get_wage_countries(self):
        """Return list of countries with wage data."""
        return sorted(
            self._df_wage["Country name"].dropna().unique().tolist()
        )

    def get_wages(self, country):
        """
        Get average wage data for a country across years.

        Returns:
            dict of year -> wage value, or None if not found.
        """
        row = self._df_wage[self._df_wage["Country name"] == country]
        if row.empty:
            return None

        wage_year_cols = [
            col for col in self._df_wage.columns if col.isdigit()
        ]
        wages = row[wage_year_cols].iloc[0].to_dict()
        return {
            year: round(float(val), 2)
            for year, val in wages.items()
            if pd.notna(val)
        }

    # ------------------------------------------------------------------ #
    #                         DEBT METHODS                                 #
    # ------------------------------------------------------------------ #

    def get_debt_data(self, year="2022"):
        """
        Get debt-to-GDP ratio data for all countries for a given year.

        Returns:
            list of dicts with 'country' and 'value'.
        """
        if year not in self._df_debt.columns:
            return []

        result = []
        for _, row in self._df_debt.iterrows():
            val = row[year]
            if pd.notna(val):
                result.append({
                    "country": row["Country Name"],
                    "value": round(float(val), 2),
                })
        return result

    # ------------------------------------------------------------------ #
    #                    REAL GROWTH METHODS                                #
    # ------------------------------------------------------------------ #

    def get_growth_countries(self):
        """Return list of countries with real growth data."""
        return sorted(
            self._df_real_growth["Country name"].dropna().unique().tolist()
        )

    def get_growth(self, country):
        """
        Get real economic growth data for a country.

        Returns:
            dict with 'years' and 'values' lists, or None if not found.
        """
        row = self._df_real_growth[
            self._df_real_growth["Country name"] == country
        ]
        if row.empty:
            return None

        data = row.iloc[0, 1:]  # Skip index and 'Country name'
        # Filter out the unnamed index column if present
        data = data[data.index.str.isdigit() | data.index.str.match(r"^\d{4}$")]

        return {
            "years": data.index.tolist(),
            "values": [
                round(float(v), 4) if pd.notna(v) else None
                for v in data.values.tolist()
            ],
        }
