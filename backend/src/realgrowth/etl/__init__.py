"""ETL pipeline: API snapshots + legacy CSV -> normalised SQLite warehouse.

Implemented with the Python standard library only (``csv`` + ``sqlite3``), so
the data layer runs on the deploy host and in CI without the data-science
stack, and is unit-testable anywhere Python runs. About 200k observations
build in a few seconds. Offline model outputs (``data/models/``) are loaded
by :mod:`realgrowth.etl.artifacts` through a plain-file contract.
"""

from realgrowth.etl.pipeline import run_etl
from realgrowth.etl.registry import Country, CountryRegistry, UnknownCountryError

__all__ = ["Country", "CountryRegistry", "UnknownCountryError", "run_etl"]
