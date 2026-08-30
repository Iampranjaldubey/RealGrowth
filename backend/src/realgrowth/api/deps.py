"""Shared FastAPI dependencies."""

from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import Depends

from realgrowth.db import get_connection
from realgrowth.repository import Repository


def get_repository(
    connection: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> Repository:
    return Repository(connection)


RepositoryDep = Annotated[Repository, Depends(get_repository)]
