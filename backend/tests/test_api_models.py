"""HTTP tests for forecasts, model cards, anomaly scores and tools.

These run against the session-built real warehouse, which includes the
committed model artefacts in ``data/models/``. If a checkout has no artefacts
the forecasting tests are skipped rather than failed: the warehouse is still
valid without them (see ``realgrowth.etl.artifacts``).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from realgrowth.config import get_settings  # noqa: E402
from realgrowth.main import create_app  # noqa: E402
from tests.conftest import MODELS_DIR  # noqa: E402

needs_models = pytest.mark.skipif(
    not (MODELS_DIR / "inflation" / "model_card.json").is_file(),
    reason="no trained model artefacts in data/models",
)


@pytest.fixture
def client(real_warehouse: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("REALGROWTH_DATABASE_PATH", str(real_warehouse))
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as test_client:
            yield test_client
    finally:
        get_settings.cache_clear()


@needs_models
class TestModels:
    def test_exactly_one_champion_plus_imf_benchmark(self, client: TestClient) -> None:
        models = client.get("/api/v1/models", params={"indicator": "inflation_rate"}).json()
        assert sum(m["is_champion"] for m in models) == 1
        kinds = {m["id"]: m["kind"] for m in models}
        assert kinds["imf_weo"] == "external"
        assert kinds["naive"] == "baseline"

    def test_model_card_reports_held_out_metrics(self, client: TestClient) -> None:
        card = client.get("/api/v1/models/inflation/card").json()
        assert card["champion"] in {m["id"] for m in card["models"]}
        windows = {m["window"] for m in card["metrics"]}
        assert windows == {"validation", "test"}
        h1 = card["champion_test"]["h1"]
        assert h1["n"] > 1_000
        assert 0.7 <= h1["coverage_80"] <= 0.9  # conformal intervals near nominal

    def test_anomaly_card(self, client: TestClient) -> None:
        card = client.get("/api/v1/models/anomaly/card").json()
        assert card["labels"]["imputed_cells"] > 0
        assert card["detectors"]["lgbm"]["pr_auc"] > card["detectors"]["robust_z"]["pr_auc"]

    def test_unknown_card_is_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/models/nope/card")
        assert response.status_code == 404
        assert set(response.json()) == {"error", "detail", "status"}


@needs_models
class TestCountryForecast:
    def test_forecast_payload(self, client: TestClient) -> None:
        response = client.get("/api/v1/forecasts/IND")
        assert response.status_code == 200
        body = response.json()
        assert body["country"]["iso3"] == "IND"
        assert body["history"]
        models = {f["model_id"]: f["points"] for f in body["forecasts"]}
        champion = body["champion"]["id"]
        assert champion in models and "imf_weo" in models
        last_history = body["history"][-1]["year"]
        for point in models[champion]:
            assert point["target_year"] > point["origin_year"]
            assert point["origin_year"] <= last_history
            assert point["lower_80"] <= point["point"] <= point["upper_80"]
            assert point["lower_95"] <= point["lower_80"]
            assert point["upper_80"] <= point["upper_95"]

    def test_backtest_and_drivers(self, client: TestClient) -> None:
        body = client.get("/api/v1/forecasts/USA").json()
        backtest = {b["model_id"] for b in body["backtest"]}
        assert {body["champion"]["id"], "naive"} <= backtest
        assert body["drivers"]
        assert len(body["drivers"][0]["contributions"]) <= 8

    def test_unknown_country_is_404(self, client: TestClient) -> None:
        assert client.get("/api/v1/forecasts/ZZZ").status_code == 404

    def test_snapshot_is_sorted_and_excludes_aggregates(self, client: TestClient) -> None:
        body = client.get("/api/v1/forecasts", params={"horizon": 1}).json()
        points = [v["point"] for v in body["values"]]
        assert points == sorted(points, reverse=True)
        assert len(points) > 150
        assert "WLD" not in {v["iso3"] for v in body["values"]}

    def test_horizon_is_validated(self, client: TestClient) -> None:
        assert client.get("/api/v1/forecasts", params={"horizon": 5}).status_code == 422


@needs_models
class TestAnomalies:
    def test_scores_are_probabilities(self, client: TestClient) -> None:
        rows = client.get("/api/v1/anomalies", params={"country": "ESP"}).json()
        assert rows
        assert all(0.0 <= r["score"] <= 1.0 for r in rows)
        assert all(r["iso3"] == "ESP" for r in rows)

    def test_flagged_only(self, client: TestClient) -> None:
        rows = client.get("/api/v1/anomalies", params={"flagged_only": True}).json()
        assert rows and all(r["is_flagged"] for r in rows)


class TestPurchasingPower:
    def test_matches_the_cpi_ratio(self, client: TestClient) -> None:
        body = client.get(
            "/api/v1/tools/purchasing-power",
            params={"country": "USA", "amount": 100, "from_year": 2010, "to_year": 2020},
        ).json()
        path = {p["year"]: p["index"] for p in body["path"]}
        assert body["equivalent"] == pytest.approx(100 * path[2020] / path[2010])
        assert body["uses_projection"] is False
        assert 15 < body["cumulative_inflation_pct"] < 25  # US CPI rose ~19% in 2010-20

    def test_works_backwards_in_time(self, client: TestClient) -> None:
        body = client.get(
            "/api/v1/tools/purchasing-power",
            params={"country": "USA", "amount": 100, "from_year": 2020, "to_year": 2010},
        ).json()
        assert body["equivalent"] < 100
        # Regression: the annualised rate must have the same sign as the
        # cumulative change, in both directions.
        assert body["cumulative_inflation_pct"] < 0
        assert body["annualised_inflation_pct"] < 0
        forward = client.get(
            "/api/v1/tools/purchasing-power",
            params={"country": "USA", "amount": 100, "from_year": 2010, "to_year": 2020},
        ).json()
        assert forward["annualised_inflation_pct"] > 0

    @needs_models
    def test_extends_with_forecast_and_marks_it(self, client: TestClient) -> None:
        body = client.get(
            "/api/v1/tools/purchasing-power",
            params={"country": "IND", "amount": 1000, "from_year": 2020, "to_year": 2026},
        ).json()
        assert body["uses_projection"] is True
        projected = [p["year"] for p in body["path"] if p["projected"]]
        assert projected and min(projected) > body["last_observed_year"]

    def test_year_without_data_is_400(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/tools/purchasing-power",
            params={"country": "USA", "amount": 100, "from_year": 2010, "to_year": 2099},
        )
        assert response.status_code == 400
        assert "not available" in response.json()["detail"]

    def test_amount_must_be_positive(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/tools/purchasing-power",
            params={"country": "USA", "amount": -5, "from_year": 2010, "to_year": 2020},
        )
        assert response.status_code == 422


class TestSources:
    def test_manifest_lists_every_series_with_checksum(self, client: TestClient) -> None:
        body = client.get("/api/v1/meta/sources").json()
        series = body["series"]
        assert "inflation_rate" in series
        assert all(len(entry["sha256"]) == 64 for entry in series.values())
