"""FastAPI application factory and ASGI entry point.

Run with: ``uvicorn realgrowth.main:app`` (see backend/Dockerfile).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from realgrowth import __version__
from realgrowth.api import correlation, countries, indicators, meta, regions
from realgrowth.api.errors import register_error_handlers
from realgrowth.config import get_settings
from realgrowth.db import pool

logger = logging.getLogger(__name__)

#: slowapi's bundled handler is typed for RateLimitExceeded specifically, which
#: is narrower than the Exception-handler signature FastAPI expects; casting
#: here is what slowapi's own documented usage does.
ExceptionHandler = Callable[[Request, Exception], Response | Awaitable[Response]]


def create_limiter() -> Limiter:
    settings = get_settings()
    return Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.rate_limit_per_minute}/minute"],
        storage_uri="memory://",
    )


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        pool.open(settings.database_path)
        logger.info("opened warehouse at %s", settings.database_path)
        try:
            yield
        finally:
            pool.close()

    app = FastAPI(
        title="RealGrowth API",
        description=(
            "Macroeconomic indicators for 218 countries: GDP, inflation, wages, "
            "real wage growth, debt-to-GDP, diet cost and population, with a "
            "correlation explorer and a published data-quality report."
        ),
        version=__version__,
        lifespan=lifespan,
    )

    limiter = create_limiter()
    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded, cast(ExceptionHandler, _rate_limit_exceeded_handler)
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    app.include_router(meta.router)
    app.include_router(indicators.router)
    app.include_router(countries.router)
    app.include_router(regions.router)
    app.include_router(correlation.router)

    return app


app = create_app()
