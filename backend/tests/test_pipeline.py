"""End-to-end ETL run against the real, committed raw data.

Where the other suites use small fabricated fixtures for exact assertions, this
suite runs the actual pipeline once per session (see ``real_warehouse`` in
conftest.py) and checks the properties that must hold no matter how the source
CSVs are refreshed: every declared indicator has data, the flagship derived
indicator behaves as documented, and nothing regresses to zero coverage
silently.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from realgrowth.etl import warehouse
from realgrowth.etl.sources import INDICATORS
from realgrowth.repository import Repository


class TestPipelineRunsCleanly:
    def test_produces_a_readable_warehouse(self, real_warehouse: Path) -> None:
        connection = warehouse.connect(real_warehouse, read_only=True)
        try:
            count = connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
            assert count > 20_000
        finally:
            connection.close()

    def test_every_declared_indicator_has_at_least_one_observation(
        self, real_repo: Repository
    ) -> None:
        for indicator in real_repo.list_indicators():
            assert indicator["min_year"] is not None, (
                f"{indicator['id']} has zero observations"
            )

    def test_registers_exactly_the_declared_indicator_set(self, real_repo: Repository) -> None:
        ids = {i["id"] for i in real_repo.list_indicators()}
        assert ids == set(INDICATORS)


class TestQualityReport:
    def test_reports_no_unresolved_entities(self, real_report: dict[str, Any]) -> None:
        """Every raw label must resolve; see test_registry's exhaustive check too."""
        assert real_report["unresolved_entities"] == []

    def test_flags_the_volatile_wage_series(self, real_report: dict[str, Any]) -> None:
        """The imputation artefact this rebuild is designed to surface, not hide."""
        assert real_report["flag_counts"].get("avg_wage:volatile_levels", 0) > 50

    def test_real_wage_growth_has_meaningful_coverage(self, real_report: dict[str, Any]) -> None:
        coverage = {c["indicator"]: c for c in real_report["coverage"]}
        real_growth = coverage["real_wage_growth"]
        assert real_growth["countries"] >= 100
        assert real_growth["min_year"] is not None and real_growth["max_year"] is not None


class TestRealWageGrowthEndToEnd:
    def test_matches_known_g7_pattern_for_2022(self, real_repo: Repository) -> None:
        """2022's cost-of-living crisis: G7 economies mostly show negative real
        wage growth once currency-adjusted USD wages are compared to domestic
        inflation. This is a smoke test against the true dataset, not a fixture.
        """
        snapshot = real_repo.get_snapshot("real_wage_growth", year=2022)
        by_country = {v["iso3"]: v["value"] for v in snapshot["values"]}
        for iso3 in ("GBR", "DEU", "ITA", "JPN"):
            assert iso3 in by_country
            assert by_country[iso3] < 0

    def test_zimbabwe_hyperinflation_survives_the_plausibility_filter(
        self, real_repo: Repository
    ) -> None:
        """A genuine crisis must not be discarded as an imputation artefact."""
        snapshot = real_repo.get_snapshot("real_wage_growth", year=2022)
        by_country = {v["iso3"]: v["value"] for v in snapshot["values"]}
        assert by_country.get("ZWE", 0) < -50
