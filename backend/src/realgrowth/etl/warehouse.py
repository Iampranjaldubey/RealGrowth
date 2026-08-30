"""SQLite warehouse: schema definition and bulk load.

Why SQLite rather than keeping DataFrames in memory (the previous design):

* the old loader parsed every CSV at import time and cached mutable DataFrames in
  a process-global singleton, which one endpoint then mutated per request —
  unsafe across gunicorn workers and impossible to reason about;
* filtering, ranking, joining and paging are what SQL is for, and pushing them
  into the database removed most of the hand-rolled Python in the API layer;
* a single ~2 MB file is trivially reproducible from the raw CSVs, so the build
  is deterministic and the artefact never needs committing.

The fact table is sparse — only observed values are stored — so ``value`` is
``NOT NULL`` and "no data" is the absence of a row rather than a sentinel.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from realgrowth.etl.registry import CountryRegistry
from realgrowth.etl.sources import INDICATORS
from realgrowth.etl.transform import Observation, SeriesFlag

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE countries (
    iso3         TEXT PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    region       TEXT,
    is_aggregate INTEGER NOT NULL DEFAULT 0 CHECK (is_aggregate IN (0, 1))
);

CREATE TABLE indicators (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    unit        TEXT NOT NULL,
    unit_symbol TEXT NOT NULL,
    description TEXT NOT NULL,
    source      TEXT NOT NULL,
    source_url  TEXT NOT NULL,
    direction   INTEGER NOT NULL CHECK (direction IN (-1, 0, 1)),
    decimals    INTEGER NOT NULL,
    is_derived  INTEGER NOT NULL DEFAULT 0 CHECK (is_derived IN (0, 1)),
    depends_on  TEXT NOT NULL DEFAULT '',
    min_year    INTEGER,
    max_year    INTEGER,
    country_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE observations (
    indicator_id TEXT NOT NULL REFERENCES indicators(id) ON DELETE CASCADE,
    iso3         TEXT NOT NULL REFERENCES countries(iso3) ON DELETE CASCADE,
    year         INTEGER NOT NULL,
    value        REAL NOT NULL,
    PRIMARY KEY (indicator_id, iso3, year)
) WITHOUT ROWID;

CREATE TABLE series_flags (
    indicator_id TEXT NOT NULL REFERENCES indicators(id) ON DELETE CASCADE,
    iso3         TEXT NOT NULL REFERENCES countries(iso3) ON DELETE CASCADE,
    flag         TEXT NOT NULL,
    detail       TEXT NOT NULL,
    PRIMARY KEY (indicator_id, iso3, flag)
) WITHOUT ROWID;

CREATE TABLE etl_metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

INDEXES = """
CREATE INDEX idx_obs_indicator_year ON observations (indicator_id, year);
CREATE INDEX idx_obs_iso3           ON observations (iso3);
CREATE INDEX idx_countries_region   ON countries (region) WHERE is_aggregate = 0;
"""


def connect(path: str | Path, *, read_only: bool = False) -> sqlite3.Connection:
    """Open a warehouse connection with foreign keys and row access by name."""
    target = Path(path)
    if read_only:
        connection = sqlite3.connect(f"file:{target}?mode=ro", uri=True, check_same_thread=False)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(target, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    if not read_only:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    """Create tables in an empty database."""
    connection.executescript(SCHEMA)


def create_indexes(connection: sqlite3.Connection) -> None:
    """Create indexes after bulk insert, which is faster than maintaining them."""
    connection.executescript(INDEXES)


def insert_countries(connection: sqlite3.Connection, registry: CountryRegistry) -> int:
    """Populate the country dimension."""
    rows = [(c.iso3, c.name, c.region, int(c.is_aggregate)) for c in registry]
    connection.executemany(
        "INSERT INTO countries (iso3, name, region, is_aggregate) VALUES (?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def insert_indicators(connection: sqlite3.Connection) -> int:
    """Populate the indicator dimension from the code-defined catalogue."""
    rows = [
        (
            ind.id,
            ind.name,
            ind.unit,
            ind.unit_symbol,
            ind.description,
            ind.source,
            ind.source_url,
            ind.direction,
            ind.decimals,
            int(ind.is_derived),
            ",".join(ind.depends_on),
        )
        for ind in INDICATORS.values()
    ]
    connection.executemany(
        """
        INSERT INTO indicators (
            id, name, unit, unit_symbol, description, source, source_url,
            direction, decimals, is_derived, depends_on
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def insert_observations(connection: sqlite3.Connection, observations: Iterable[Observation]) -> int:
    """Bulk-insert the fact table."""
    cursor = connection.executemany(
        "INSERT INTO observations (indicator_id, iso3, year, value) VALUES (?, ?, ?, ?)",
        (tuple(o) for o in observations),
    )
    return cursor.rowcount if cursor.rowcount != -1 else 0


def insert_series_flags(connection: sqlite3.Connection, flags: Iterable[SeriesFlag]) -> int:
    """Record per-series caveats so the API can serve them alongside the data."""
    rows = [(f.indicator_id, f.iso3, f.flag, f.detail) for f in flags]
    connection.executemany(
        """
        INSERT INTO series_flags (indicator_id, iso3, flag, detail)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (indicator_id, iso3, flag) DO UPDATE SET detail = excluded.detail
        """,
        rows,
    )
    return len(rows)


def refresh_indicator_ranges(connection: sqlite3.Connection) -> None:
    """Denormalise each indicator's year span and country count.

    The UI needs these to build sliders and dropdowns. Storing them means a page
    never offers a year that has no data — the old Debt page let users pick any
    year from 1950 to 2022 for a dataset covering five years, so 93% of choices
    rendered an empty map.
    """
    connection.execute(
        """
        UPDATE indicators SET
            min_year = (
                SELECT MIN(year) FROM observations o WHERE o.indicator_id = indicators.id
            ),
            max_year = (
                SELECT MAX(year) FROM observations o WHERE o.indicator_id = indicators.id
            ),
            country_count = (
                SELECT COUNT(DISTINCT iso3) FROM observations o
                WHERE o.indicator_id = indicators.id
            )
        """
    )


def set_metadata(connection: sqlite3.Connection, entries: Sequence[tuple[str, str]]) -> None:
    """Upsert warehouse metadata."""
    connection.executemany(
        """
        INSERT INTO etl_metadata (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        entries,
    )


def get_metadata(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute("SELECT value FROM etl_metadata WHERE key = ?", (key,)).fetchone()
    return None if row is None else str(row["value"])


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
