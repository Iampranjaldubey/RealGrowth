"""SQLite connection lifecycle for the API process.

One read-only connection per worker process, opened at startup and closed at
shutdown, handed to each request via FastAPI's dependency injection. This
replaces the previous ``DataLoader`` singleton, which parsed every CSV into a
mutable, unsynchronised, process-global cache and had at least one endpoint
(``population.py``) mutate it in place per request.

SQLite connections are not safe to share across threads by default; opening
read-only with ``check_same_thread=False`` is safe here because the connection
never writes, so there is no interleaved-write hazard to guard against.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

from realgrowth.etl import warehouse


class DatabaseUnavailableError(RuntimeError):
    """Raised when the warehouse file is missing or unreadable."""


def open_connection(database_path: str | Path) -> sqlite3.Connection:
    path = Path(database_path)
    if not path.is_file():
        raise DatabaseUnavailableError(
            f"warehouse not found at {path}; build it with `python -m realgrowth.etl`"
        )
    return warehouse.connect(path, read_only=True)


class ConnectionPool:
    """Holds the single long-lived connection used by request handlers."""

    def __init__(self) -> None:
        self._connection: sqlite3.Connection | None = None

    def open(self, database_path: str | Path) -> None:
        self._connection = open_connection(database_path)

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def get(self) -> sqlite3.Connection:
        if self._connection is None:
            raise DatabaseUnavailableError("database connection is not open")
        return self._connection


pool = ConnectionPool()


def get_connection() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency yielding the shared connection."""
    yield pool.get()
