"""ETL pipeline: raw vendor CSVs -> normalised SQLite warehouse.

The pipeline is deliberately implemented with the Python standard library only
(``csv`` + ``sqlite3``). The dataset is ~4k rows of wide-format CSV, so pandas
would add ~50 MB of image weight and a multi-second import cost for no benefit,
and keeping it dependency-free means the whole data layer is unit-testable
anywhere Python runs.
"""

from realgrowth.etl.pipeline import run_etl
from realgrowth.etl.registry import Country, CountryRegistry, UnknownCountryError

__all__ = ["Country", "CountryRegistry", "UnknownCountryError", "run_etl"]
