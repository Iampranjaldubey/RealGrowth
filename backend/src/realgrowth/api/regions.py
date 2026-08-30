"""World Bank macro-region list, used to populate region filters."""

from __future__ import annotations

from fastapi import APIRouter

from realgrowth.api.deps import RepositoryDep

router = APIRouter(prefix="/api/v1/regions", tags=["regions"])


@router.get("", response_model=list[str])
def list_regions(repo: RepositoryDep) -> list[str]:
    return repo.list_regions()
