"""Warehouse metadata and the data-quality report.

Publishing the quality report as an endpoint, rather than leaving it in a build
log, is a deliberate choice: several source series contain imputed values (see
``realgrowth.etl.derive``), and the honest thing to do is make that
machine-readable and visible in the product rather than only in a README.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from realgrowth import __version__
from realgrowth.api.deps import RepositoryDep
from realgrowth.config import get_settings
from realgrowth.schemas import HealthResponse, QualityReport, WarehouseInfo

router = APIRouter(prefix="/api/v1/meta", tags=["meta"])


@router.get("/health", response_model=HealthResponse)
def health() -> dict[str, Any]:
    settings = get_settings()
    return {
        "status": "ok",
        "name": "RealGrowth API",
        "version": __version__,
        "environment": settings.environment,
    }


@router.get("/quality", response_model=QualityReport)
def quality(repo: RepositoryDep) -> dict[str, Any]:
    """The ETL's data-quality findings: coverage, rejected values, caveats."""
    return repo.get_quality_report()


@router.get("/warehouse", response_model=WarehouseInfo)
def warehouse_info(repo: RepositoryDep) -> dict[str, Any]:
    return repo.get_warehouse_info()
