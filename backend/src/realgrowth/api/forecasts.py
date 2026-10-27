"""Forecasts, model cards and imputation-artefact scores.

All predictions are precomputed offline (``python -m realgrowth_ml``) and
loaded into the warehouse by the ETL; these endpoints only read. That keeps the
API process free of the ML stack, makes every served number reproducible from
a model card plus a data snapshot, and keeps p99 latency at SQLite speed.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query

from realgrowth.api.deps import RepositoryDep
from realgrowth.schemas import (
    AnomalyScore,
    CountryForecastResponse,
    ForecastModel,
    ForecastSnapshotResponse,
)

router = APIRouter(prefix="/api/v1", tags=["models"])

DEFAULT_TARGET = "inflation_rate"


@router.get("/models", response_model=list[ForecastModel])
def list_models(repo: RepositoryDep, indicator: str | None = None) -> list[dict[str, Any]]:
    """Every forecasting model: the champion, baselines and the IMF benchmark."""
    return repo.list_models(indicator)


@router.get("/models/{task}/card")
def get_model_card(task: str, repo: RepositoryDep) -> dict[str, Any]:
    """The full model card for ``inflation`` or ``anomaly``: design, features,
    validation and test metrics, significance tests, limitations.

    Returned as written by the training run (it is versioned with the model),
    so its schema is documented in ``docs/MODEL_CARD.md`` rather than here.
    """
    return repo.get_model_card(task)


@router.get("/forecasts/{iso3}", response_model=CountryForecastResponse)
def get_country_forecast(
    iso3: str,
    repo: RepositoryDep,
    indicator: str = DEFAULT_TARGET,
    history_years: Annotated[int, Query(ge=1, le=70)] = 25,
) -> dict[str, Any]:
    """History, forecasts with 80%/95% intervals, the IMF benchmark, this
    country's out-of-sample backtest, and the drivers of each forecast."""
    return repo.get_country_forecast(iso3, indicator, history_years=history_years)


@router.get("/forecasts", response_model=ForecastSnapshotResponse)
def get_forecast_snapshot(
    repo: RepositoryDep,
    indicator: str = DEFAULT_TARGET,
    horizon: Annotated[int, Query(ge=1, le=2)] = 1,
) -> dict[str, Any]:
    """The champion's forecast for every country at one horizon, highest first."""
    return repo.get_forecast_snapshot(indicator, horizon)


@router.get("/anomalies", response_model=list[AnomalyScore])
def get_anomalies(
    repo: RepositoryDep,
    indicator: str = "avg_wage",
    country: str | None = None,
    flagged_only: bool = False,
) -> list[dict[str, Any]]:
    """Per-cell probability that a value is an imputation artefact."""
    return repo.get_anomaly_scores(indicator, country, flagged_only=flagged_only)
