"""Practical tools built on the warehouse."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query

from realgrowth.api.deps import RepositoryDep
from realgrowth.schemas import PurchasingPowerResponse

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


@router.get("/purchasing-power", response_model=PurchasingPowerResponse)
def purchasing_power(
    repo: RepositoryDep,
    country: Annotated[str, Query(description="ISO3 code, e.g. IND")],
    amount: Annotated[float, Query(gt=0, le=1e15)],
    from_year: Annotated[int, Query(ge=1960, le=2100)],
    to_year: Annotated[int, Query(ge=1960, le=2100)],
) -> dict[str, Any]:
    """What an amount of money in ``from_year`` is worth in ``to_year`` prices.

    For example: a salary of 50,000 in 2015 needs to be X in 2024 to buy the
    same basket. Years after the latest CPI release are extended with the
    champion forecast and marked ``projected``.
    """
    return repo.purchasing_power(country, amount, from_year, to_year)
