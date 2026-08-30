"""Shared fixtures.

The unit suite runs against a small purpose-built warehouse so assertions are
exact, plus a session-scoped build of the real one so the pipeline is exercised
end to end on genuine data.
"""

from __future__ import annotations

import sqlite3
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "backend" / "src"
if str(SRC) not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(SRC))

from realgrowth.etl import warehouse  # noqa: E402
from realgrowth.etl.pipeline import run_etl  # noqa: E402
from realgrowth.etl.registry import Country, CountryRegistry  # noqa: E402
from realgrowth.etl.transform import Observation  # noqa: E402
from realgrowth.repository import Repository  # noqa: E402

RAW_DIR = REPO_ROOT / "data" / "raw"
REFERENCE_CSV = REPO_ROOT / "data" / "reference" / "countries.csv"


@pytest.fixture(scope="session")
def reference_csv() -> Path:
    return REFERENCE_CSV


@pytest.fixture(scope="session")
def real_registry(reference_csv: Path) -> CountryRegistry:
    return CountryRegistry.from_csv(reference_csv)


@pytest.fixture
def tiny_registry() -> CountryRegistry:
    """A three-country registry with one aggregate and a couple of aliases."""
    return CountryRegistry(
        [
            Country("USA", "United States", "North America", False),
            Country("IND", "India", "South Asia", False),
            Country("KOR", "South Korea", "East Asia & Pacific", False),
            Country("WLD", "World", None, True),
        ],
        {"Korea, Rep.": "KOR", "United States of America": "USA", "OWID_WRL": "WLD"},
    )


def build_warehouse(path: Path, observations: list[Observation], registry: CountryRegistry) -> None:
    """Create a warehouse containing exactly ``observations``."""
    connection = warehouse.connect(path)
    try:
        with connection:
            warehouse.create_schema(connection)
            warehouse.insert_countries(connection, registry)
            warehouse.insert_indicators(connection)
            warehouse.insert_observations(connection, observations)
            warehouse.create_indexes(connection)
            warehouse.refresh_indicator_ranges(connection)
            warehouse.set_metadata(
                connection,
                [
                    ("schema_version", str(warehouse.SCHEMA_VERSION)),
                    ("built_at", warehouse.utc_now_iso()),
                    (
                        "quality_report",
                        f'{{"total_observations": {len(observations)}}}',
                    ),
                ],
            )
    finally:
        connection.close()


@pytest.fixture
def tiny_db(tmp_path: Path, tiny_registry: CountryRegistry) -> Iterator[sqlite3.Connection]:
    """A warehouse with hand-written values, so expected results are exact."""
    observations = [
        # gdp_per_capita: a clean rising series for two countries
        Observation("gdp_per_capita", "USA", 2020, 63_000.0),
        Observation("gdp_per_capita", "USA", 2021, 70_000.0),
        Observation("gdp_per_capita", "USA", 2022, 76_000.0),
        Observation("gdp_per_capita", "IND", 2020, 1_900.0),
        Observation("gdp_per_capita", "IND", 2021, 2_250.0),
        Observation("gdp_per_capita", "IND", 2022, 2_400.0),
        # inflation: USA has a gap in 2021 on purpose
        Observation("inflation_rate", "USA", 2020, 1.2),
        Observation("inflation_rate", "USA", 2022, 8.0),
        Observation("inflation_rate", "IND", 2020, 6.6),
        Observation("inflation_rate", "IND", 2021, 5.1),
        Observation("inflation_rate", "IND", 2022, 6.7),
        # population, used by the min_population filter
        Observation("population", "USA", 2022, 333_000_000.0),
        Observation("population", "IND", 2022, 1_400_000_000.0),
        Observation("population", "KOR", 2022, 51_000_000.0),
        # an aggregate, which must be excluded unless asked for
        Observation("gdp_per_capita", "WLD", 2022, 13_000.0),
    ]
    path = tmp_path / "tiny.db"
    build_warehouse(path, observations, tiny_registry)
    connection = warehouse.connect(path, read_only=True)
    yield connection
    connection.close()


@pytest.fixture
def tiny_repo(tiny_db: sqlite3.Connection) -> Repository:
    return Repository(tiny_db)


@pytest.fixture(scope="session")
def real_warehouse(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the warehouse from the committed raw CSVs once per session."""
    if not RAW_DIR.is_dir():  # pragma: no cover - guards a broken checkout
        pytest.skip(f"raw data not available at {RAW_DIR}")
    target = tmp_path_factory.mktemp("warehouse") / "realgrowth.db"
    run_etl(RAW_DIR, REFERENCE_CSV, target)
    return target


@pytest.fixture(scope="session")
def real_report(real_warehouse: Path) -> dict[str, Any]:
    connection = warehouse.connect(real_warehouse, read_only=True)
    try:
        return Repository(connection).get_quality_report()
    finally:
        connection.close()


@pytest.fixture
def real_repo(real_warehouse: Path) -> Iterator[Repository]:
    connection = warehouse.connect(real_warehouse, read_only=True)
    yield Repository(connection)
    connection.close()
