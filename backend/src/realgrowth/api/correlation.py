"""Correlation Explorer: relate two indicators, over time or across countries.

The previous implementation supported only the time-series mode, and crashed on
one indicator combination outright (``float('India')`` from the ``growth`` column
bug). It also reported a bare coefficient with no sample size or significance,
which invites reading noise as signal. This version adds the cross-sectional
mode and returns the full :class:`~realgrowth.stats.CorrelationResult`.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query

from realgrowth.api.deps import RepositoryDep
from realgrowth.schemas import CorrelationResponse

router = APIRouter(prefix="/api/v1/correlation", tags=["correlation"])


@router.get("/time-series", response_model=CorrelationResponse)
def correlate_time_series(
    repo: RepositoryDep,
    country: Annotated[str, Query(description="ISO3 code, e.g. USA")],
    x: Annotated[str, Query(description="Indicator id for the X axis")],
    y: Annotated[str, Query(description="Indicator id for the Y axis")],
    start_year: Annotated[int | None, Query(ge=1900, le=2100)] = None,
    end_year: Annotated[int | None, Query(ge=1900, le=2100)] = None,
) -> dict[str, Any]:
    """Do two indicators move together over time, within one country?"""
    result = repo.correlate_over_time(country, x, y, start_year=start_year, end_year=end_year)
    return {
        **result,
        "indicator_x": repo.get_indicator(x),
        "indicator_y": repo.get_indicator(y),
    }


@router.get("/cross-section", response_model=CorrelationResponse)
def correlate_cross_section(
    repo: RepositoryDep,
    x: Annotated[str, Query(description="Indicator id for the X axis")],
    y: Annotated[str, Query(description="Indicator id for the Y axis")],
    year: Annotated[int, Query(ge=1900, le=2100)],
    region: str | None = None,
) -> dict[str, Any]:
    """Do two indicators move together across countries, within one year?"""
    result = repo.correlate_across_countries(x, y, year, region=region)
    return {
        **result,
        "indicator_x": repo.get_indicator(x),
        "indicator_y": repo.get_indicator(y),
    }
