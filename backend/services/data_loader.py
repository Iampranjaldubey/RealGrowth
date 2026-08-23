"""
Centralized data loading service with lazy loading and caching.
All CSV datasets are loaded once and cached for the lifetime of the application.
"""
import os
import pandas as pd
from config import Config


class DataLoader:
    """Singleton-style data loader for all economic datasets."""

    _instance = None
    _loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not DataLoader._loaded:
            self._data_dir = Config.DATA_DIR
            self._cache = {}
            self._load_all()
            DataLoader._loaded = True

    def _csv_path(self, filename):
        return os.path.join(self._data_dir, filename)

    def _load_all(self):
        """Load and prepare all datasets."""
        self._load_gdp()
        self._load_inflation()
        self._load_food()
        self._load_population()
        self._load_wages()
        self._load_debt()
        self._load_growth()

    # ── GDP ──────────────────────────────────────────────
    def _load_gdp(self):
        df = pd.read_csv(self._csv_path('GDP_per_capita.csv'), on_bad_lines='skip')
        df['Population'] = pd.to_numeric(df['Population'], errors='coerce')
        year_columns = [col for col in df.columns if col.isdigit()]
        for col in year_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        self._cache['gdp'] = df
        self._cache['gdp_year_columns'] = year_columns

    @property
    def gdp(self):
        return self._cache['gdp']

    @property
    def gdp_year_columns(self):
        return self._cache['gdp_year_columns']

    # ── Inflation ────────────────────────────────────────
    def _load_inflation(self):
        df = pd.read_csv(self._csv_path('filled_Inflation_Rate.csv'))
        countries = df['Country'].tolist()
        inflation_data = {}
        for country in countries:
            inflation_data[country] = (
                df.loc[df['Country'] == country]
                .drop('Country', axis=1)
                .values.flatten()
                .tolist()[0:15]
            )
        self._cache['inflation'] = df
        self._cache['inflation_countries'] = countries
        self._cache['inflation_data'] = inflation_data

    @property
    def inflation(self):
        return self._cache['inflation']

    @property
    def inflation_countries(self):
        return self._cache['inflation_countries']

    @property
    def inflation_data(self):
        return self._cache['inflation_data']

    # ── Food ─────────────────────────────────────────────
    def _load_food(self):
        df = pd.read_csv(self._csv_path('filled_healthy_diet_cost.csv'))
        self._cache['food'] = df

    @property
    def food(self):
        return self._cache['food']

    # ── Population ───────────────────────────────────────
    def _load_population(self):
        df_rural = pd.read_csv(self._csv_path('rural_population.csv'))
        df_urban = pd.read_csv(self._csv_path('urban_population.csv'))
        df_rural_pct = pd.read_csv(self._csv_path('rural_pop_percent_change.csv'))
        df_urban_pct = pd.read_csv(self._csv_path('urban_pop_percent_change.csv'))

        for df in [df_rural, df_urban, df_rural_pct, df_urban_pct]:
            df['Country Name'] = df['Country Name'].str.strip()
            df.columns = df.columns.str.strip()

        self._cache['rural_pop'] = df_rural
        self._cache['urban_pop'] = df_urban
        self._cache['rural_pct_change'] = df_rural_pct
        self._cache['urban_pct_change'] = df_urban_pct

    @property
    def rural_pop(self):
        return self._cache['rural_pop']

    @property
    def urban_pop(self):
        return self._cache['urban_pop']

    @property
    def rural_pct_change(self):
        return self._cache['rural_pct_change']

    @property
    def urban_pct_change(self):
        return self._cache['urban_pct_change']

    # ── Wages ────────────────────────────────────────────
    def _load_wages(self):
        df = pd.read_csv(self._csv_path('avg_wage.csv'))
        self._cache['wages'] = df

    @property
    def wages(self):
        return self._cache['wages']

    # ── Debt ─────────────────────────────────────────────
    def _load_debt(self):
        df = pd.read_csv(self._csv_path('filled_debt_to_gdp_ratio.csv'))
        df.columns = df.columns.str.strip()
        self._cache['debt'] = df

    @property
    def debt(self):
        return self._cache['debt']

    # ── Real Growth ──────────────────────────────────────
    def _load_growth(self):
        df = pd.read_csv(self._csv_path('real_growth.csv'))
        df.columns = df.columns.str.strip()
        self._cache['growth'] = df

    @property
    def growth(self):
        return self._cache['growth']


# Module-level singleton instance
data = DataLoader()
