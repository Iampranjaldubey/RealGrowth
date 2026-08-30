"""Country dimension: lists, search, and per-country profiles."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from realgrowth.api.deps import RepositoryDep
from realgrowth.schemas import Country, CountryProfileResponse

router = APIRouter(prefix="/api/v1/countries", tags=["countries"])


@router.get("", response_model=list[Country])
def list_countries(
    repo: RepositoryDep,
    indicator: str | None = None,
    region: str | None = None,
    search: str | None = None,
    include_aggregates: bool = False,
) -> list[dict[str, Any]]:
    """Countries, optionally restricted to those with data for ``indicator``.

    Filtering by indicator is what the old country dropdowns lacked: selecting a
    country with no debt data, for example, silently rendered an empty chart.
    """
    return repo.list_countries(
        indicator_id=indicator,
        region=region,
        search=search,
        include_aggregates=include_aggregates,
    )


@router.get("/{iso3}", response_model=CountryProfileResponse)
def get_country_profile(iso3: str, repo: RepositoryDep) -> dict[str, Any]:
    """The most recent observation of every indicator for one country."""
    return repo.get_country_profile(iso3)
