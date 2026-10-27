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

import pytest

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
            assert indicator["min_year"] is not None, f"{indicator['id']} has zero observations"

    def test_registers_exactly_the_declared_indicator_set(self, real_repo: Repository) -> None:
        ids = {i["id"] for i in real_repo.list_indicators()}
        assert ids == set(INDICATORS)


class TestQualityReport:
    def test_reports_no_unresolved_entities(self, real_report: dict[str, Any]) -> None:
        """Every raw label must resolve; see test_registry's exhaustive check too."""
        assert real_report["unresolved_entities"] == []

    def test_flags_the_affected_wage_series(self, real_report: dict[str, Any]) -> None:
        """The imputation artefact this rebuild is designed to surface, not hide.

        With forensic labels most series are flagged ``imputed_levels``; the
        plausibility rule (``volatile_levels``) catches the remainder, or
        everything when no labels are available.
        """
        flags = real_report["flag_counts"]
        flagged = flags.get("avg_wage:volatile_levels", 0) + flags.get("avg_wage:imputed_levels", 0)
        assert flagged > 50

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

    def test_hyperinflation_survives_the_plausibility_filter(self, real_repo: Repository) -> None:
        """A genuine crisis must not be discarded as an imputation artefact.

        Argentina's 2022 local-currency wage move exceeds the 40% rule, but
        ~72% inflation explains it and the wage level is genuine, so it stays.
        """
        snapshot = real_repo.get_snapshot("real_wage_growth", year=2022)
        by_country = {v["iso3"]: v["value"] for v in snapshot["values"]}
        nominal = real_repo.get_snapshot("nominal_wage_growth", year=2022)
        assert {v["iso3"]: v["value"] for v in nominal["values"]}["ARG"] > 40
        assert by_country["ARG"] < -10

    def test_imputed_wage_cells_never_produce_growth_rates(
        self, real_repo: Repository, real_report: dict[str, Any]
    ) -> None:
        """With forensic labels available, no growth rate may touch an imputed
        wage level. France's 2020-22 and Zimbabwe's 2020-22 wages were filled
        upstream, so neither has a 2022 real wage growth figure."""
        if real_report["issue_counts"].get("imputed_input", 0) == 0:
            pytest.skip("no imputation labels in data/models/anomaly")
        snapshot = real_repo.get_snapshot("real_wage_growth", year=2022)
        iso3s = {v["iso3"] for v in snapshot["values"]}
        assert "FRA" not in iso3s
        assert "ZWE" not in iso3s
        assert real_report["flag_counts"]["real_wage_growth:imputed_inputs"] > 50

    def test_local_currency_growth_matches_published_magnitudes(
        self, real_repo: Repository
    ) -> None:
        """In local currency, G7 real wage losses in 2022 were single digits
        (ILO Global Wage Report 2022-23). The old USD-based chain produced
        double-digit "losses" driven by dollar strength instead.
        """
        snapshot = real_repo.get_snapshot("real_wage_growth", year=2022)
        by_country = {v["iso3"]: v["value"] for v in snapshot["values"]}
        for iso3 in ("GBR", "DEU", "ITA", "JPN", "USA"):
            assert -10 < by_country[iso3] < 0, iso3


class TestApiSnapshot:
    def test_inflation_reaches_recent_years(self, real_repo: Repository) -> None:
        """The point of live ingestion: the data is no longer frozen at 2022."""
        inflation = real_repo.get_indicator("inflation_rate")
        assert inflation["max_year"] >= 2024
        assert inflation["min_year"] == 1960

    def test_imf_benchmark_is_loaded_as_external_model(self, real_warehouse: Path) -> None:
        connection = warehouse.connect(real_warehouse, read_only=True)
        try:
            row = connection.execute(
                "SELECT kind, (SELECT COUNT(*) FROM forecasts WHERE model_id = 'imf_weo') "
                "FROM models WHERE id = 'imf_weo'"
            ).fetchone()
        finally:
            connection.close()
        assert row is not None
        assert row[0] == "external"
        assert row[1] > 500
