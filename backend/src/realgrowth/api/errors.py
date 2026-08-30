"""Central exception -> HTTP response mapping.

One error contract, ``{"error": ..., "detail": ..., "status": ...}``, for every
failure mode. The previous API produced 400 JSON for some invalid input, an
empty array for other invalid input, and an uncaught 500 traceback for the rest
(``population.py`` indexed a DataFrame column before validating the year existed,
turning a bad request into a server error).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from realgrowth.db import DatabaseUnavailableError
from realgrowth.etl.registry import UnknownCountryError
from realgrowth.repository import NotFoundError, RepositoryError

logger = logging.getLogger(__name__)


def _error(status: int, error: str, detail: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"error": error, "detail": detail, "status": status}
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    @app.exception_handler(UnknownCountryError)
    async def not_found(_: Request, exc: Exception) -> JSONResponse:
        return _error(404, "Not found", str(exc))

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _error(422, "Invalid request", str(exc.errors()))

    @app.exception_handler(ValueError)
    async def bad_value(_: Request, exc: ValueError) -> JSONResponse:
        return _error(400, "Bad request", str(exc))

    @app.exception_handler(RepositoryError)
    async def repository_error(_: Request, exc: RepositoryError) -> JSONResponse:
        return _error(503, "Data unavailable", str(exc))

    @app.exception_handler(DatabaseUnavailableError)
    async def database_unavailable(_: Request, exc: DatabaseUnavailableError) -> JSONResponse:
        logger.error("database unavailable: %s", exc)
        return _error(503, "Data unavailable", str(exc))

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return _error(500, "Internal server error", None)
