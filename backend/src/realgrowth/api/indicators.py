"""Indicator catalogue, time series and cross-country snapshots."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query

from realgrowth.api.deps import RepositoryDep
from realgrowth.schemas import Indicator, SeriesResponse, SnapshotResponse

router = APIRouter(prefix="/api/v1/indicators", tags=["indicators"])


def _csv_param(value: str) -> list[str]:
    return [item.strip().upper() for item in value.split(",") if item.strip()]


@router.get("", response_model=list[Indicator])
def list_indicators(repo: RepositoryDep) -> list[dict[str, Any]]:
    """Every indicator, with its provenance and the year range it actually covers."""
    return repo.list_indicators()


@router.get("/{indicator_id}", response_model=Indicator)
def get_indicator(indicator_id: str, repo: RepositoryDep) -> dict[str, Any]:
    return repo.get_indicator(indicator_id)


@router.get("/{indicator_id}/series", response_model=SeriesResponse)
def get_series(
    indicator_id: str,
    repo: RepositoryDep,
    countries: Annotated[str, Query(description="Comma-separated ISO3 codes, e.g. USA,IND,DEU")],
    start_year: Annotated[int | None, Query(ge=1900, le=2100)] = None,
    end_year: Annotated[int | None, Query(ge=1900, le=2100)] = None,
) -> dict[str, Any]:
    """One time series per requested country.

    Only years with an actual observation are returned; there is no zero-filled
    gap to misread as a collapse.
    """
    indicator = repo.get_indicator(indicator_id)
    series = repo.get_series(
        indicator_id, _csv_param(countries), start_year=start_year, end_year=end_year
    )
    return {"indicator": indicator, "series": series}


@router.get("/{indicator_id}/snapshot", response_model=SnapshotResponse)
def get_snapshot(
    indicator_id: str,
    repo: RepositoryDep,
    year: Annotated[
        int | None,
        Query(ge=1900, le=2100, description="Defaults to the indicator's most recent year"),
    ] = None,
    region: str | None = None,
    min_population: Annotated[int | None, Query(ge=0)] = None,
    include_aggregates: bool = False,
    order: Literal["asc", "desc"] = "desc",
    limit: Annotated[int | None, Query(ge=1, le=500)] = None,
) -> dict[str, Any]:
    """All countries' values for one year, ranked — backs the map and rankings.

    ``year`` defaults to the indicator's latest year rather than a hardcoded
    constant, so a client can never request a year the data does not cover (the
    previous UI offered 1950-2022 for a debt series covering only 2018-2022).
    """
    indicator = repo.get_indicator(indicator_id)
    snapshot = repo.get_snapshot(
        indicator_id,
        year=year,
        region=region,
        min_population=min_population,
        include_aggregates=include_aggregates,
        order=order,
        limit=limit,
    )
    return {"indicator": indicator, "year": snapshot["year"], "values": snapshot["values"]}
