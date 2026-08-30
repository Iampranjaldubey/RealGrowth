"""HTTP-level tests against the FastAPI app.

Requires fastapi/httpx, which are not present in every environment this repo is
edited in; CI installs them from requirements-dev.txt. Uses the same
session-built warehouse as test_pipeline.py so this suite exercises the real
data end to end, not a mock.
"""

from __future__ import annotations

from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from realgrowth.db import pool  # noqa: E402
from realgrowth.main import create_app  # noqa: E402


@pytest.fixture
def client(real_warehouse: Path) -> TestClient:
    pool.open(real_warehouse)
    app = create_app()
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        pool.close()


class TestHealth:
    def test_health_reports_ok(self, client: TestClient) -> None:
        response = client.get("/api/v1/meta/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["name"] == "RealGrowth API"


class TestIndicators:
    def test_lists_all_eleven_indicators(self, client: TestClient) -> None:
        response = client.get("/api/v1/indicators")
        assert response.status_code == 200
        ids = {i["id"] for i in response.json()}
        assert "real_wage_growth" in ids
        assert len(ids) == 11

    def test_unknown_indicator_is_404_with_the_standard_error_shape(
        self, client: TestClient
    ) -> None:
        response = client.get("/api/v1/indicators/not_real")
        assert response.status_code == 404
        body = response.json()
        assert set(body) == {"error", "detail", "status"}
        assert body["status"] == 404

    def test_series_returns_only_years_with_data(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/indicators/gdp_per_capita/series", params={"countries": "USA,IND"}
        )
        assert response.status_code == 200
        series = {s["iso3"]: s for s in response.json()["series"]}
        assert series["USA"]["points"]
        assert series["IND"]["points"]

    def test_series_missing_countries_param_is_422(self, client: TestClient) -> None:
        response = client.get("/api/v1/indicators/gdp_per_capita/series")
        assert response.status_code == 422

    def test_snapshot_defaults_to_latest_year_with_no_hardcoded_bounds(
        self, client: TestClient
    ) -> None:
        """The bug class this fixes: the old Debt page offered years 1950-2022
        for data covering only 2018-2022. The snapshot must self-report its year.
        """
        response = client.get("/api/v1/indicators/debt_to_gdp/snapshot")
        assert response.status_code == 200
        body = response.json()
        assert body["year"] == body["indicator"]["max_year"]

    def test_snapshot_excludes_aggregates_by_default(self, client: TestClient) -> None:
        response = client.get("/api/v1/indicators/gdp_per_capita/snapshot")
        countries = {v["country"] for v in response.json()["values"]}
        assert "World" not in countries

    def test_growth_indicator_never_returns_a_country_name_as_a_value(
        self, client: TestClient
    ) -> None:
        """Regression test for the original growth.py off-by-one bug, where
        `/api/growth/<country>` returned the country's own name as a data point.
        """
        response = client.get(
            "/api/v1/indicators/real_wage_growth/series", params={"countries": "IND"}
        )
        assert response.status_code == 200
        for point in response.json()["series"][0]["points"]:
            assert isinstance(point["value"], (int, float))


class TestCountries:
    def test_lists_countries_excluding_aggregates(self, client: TestClient) -> None:
        response = client.get("/api/v1/countries")
        assert response.status_code == 200
        names = {c["name"] for c in response.json()}
        assert "World" not in names
        assert "United States" in names

    def test_filters_by_indicator_so_dropdowns_cannot_offer_empty_choices(
        self, client: TestClient
    ) -> None:
        response = client.get("/api/v1/countries", params={"indicator": "debt_to_gdp"})
        assert response.status_code == 200
        assert len(response.json()) < 218  # strictly fewer than the full roster

    def test_country_profile_returns_latest_observation_per_indicator(
        self, client: TestClient
    ) -> None:
        response = client.get("/api/v1/countries/USA")
        assert response.status_code == 200
        body = response.json()
        assert body["country"]["iso3"] == "USA"
        assert body["latest"]

    def test_unknown_country_is_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/countries/ZZZ")
        assert response.status_code == 404


class TestCorrelation:
    def test_time_series_mode_does_not_crash_on_growth_indicator(
        self, client: TestClient
    ) -> None:
        """The exact request that 500'd in the old API: float('India') from the
        unnamed leading column in real_growth.csv.
        """
        response = client.get(
            "/api/v1/correlation/time-series",
            params={"country": "IND", "x": "real_wage_growth", "y": "inflation_rate"},
        )
        assert response.status_code == 200

    def test_cross_section_mode(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/correlation/cross-section",
            params={"x": "gdp_per_capita", "y": "healthy_diet_cost", "year": 2020},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["mode"] == "cross_section"
        if body["statistics"]:
            assert -1.0 <= body["statistics"]["r"] <= 1.0

    def test_unknown_indicator_id_is_404_not_500(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/correlation/time-series",
            params={"country": "USA", "x": "not_real", "y": "inflation_rate"},
        )
        assert response.status_code == 404


class TestMeta:
    def test_quality_report_is_served(self, client: TestClient) -> None:
        response = client.get("/api/v1/meta/quality")
        assert response.status_code == 200
        body = response.json()
        assert body["total_observations"] > 20_000
        assert "avg_wage:volatile_levels" in body["flag_counts"]

    def test_openapi_schema_is_generated(self, client: TestClient) -> None:
        """A smoke test that every response_model is well-formed enough to
        produce a schema — the auto-generated docs the old API never had.
        """
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert response.json()["info"]["title"] == "RealGrowth API"


class TestErrorContract:
    """Every failure mode must return the same {error, detail, status} shape."""

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/indicators/not_real",
            "/api/v1/countries/ZZZ",
        ],
    )
    def test_error_shape_is_consistent(self, client: TestClient, path: str) -> None:
        response = client.get(path)
        assert response.status_code >= 400
        body = response.json()
        assert set(body) == {"error", "detail", "status"}
