"""Repository queries against a small, hand-built warehouse (see conftest.tiny_db)."""

from __future__ import annotations

import pytest

from realgrowth.repository import NotFoundError, Repository


class TestListIndicators:
    def test_includes_year_span_and_country_count(self, tiny_repo: Repository) -> None:
        indicators = {i["id"]: i for i in tiny_repo.list_indicators()}
        gdp = indicators["gdp_per_capita"]
        assert gdp["min_year"] == 2020
        assert gdp["max_year"] == 2022
        # Two real countries have gdp_per_capita in the fixture; WLD is an aggregate.
        assert gdp["country_count"] == 3  # USA, IND, and WLD all have a row


class TestGetIndicator:
    def test_returns_metadata(self, tiny_repo: Repository) -> None:
        assert tiny_repo.get_indicator("inflation_rate")["id"] == "inflation_rate"

    def test_unknown_raises_not_found(self, tiny_repo: Repository) -> None:
        with pytest.raises(NotFoundError):
            tiny_repo.get_indicator("does_not_exist")


class TestListCountries:
    def test_excludes_aggregates_by_default(self, tiny_repo: Repository) -> None:
        names = {c["name"] for c in tiny_repo.list_countries()}
        assert "World" not in names
        assert names == {"United States", "India", "South Korea"}

    def test_can_include_aggregates(self, tiny_repo: Repository) -> None:
        names = {c["name"] for c in tiny_repo.list_countries(include_aggregates=True)}
        assert "World" in names

    def test_filters_by_indicator_availability(self, tiny_repo: Repository) -> None:
        """South Korea has no gdp_per_capita in the fixture and must be excluded."""
        names = {c["name"] for c in tiny_repo.list_countries(indicator_id="gdp_per_capita")}
        assert names == {"United States", "India"}

    def test_filters_by_region(self, tiny_repo: Repository) -> None:
        names = {c["name"] for c in tiny_repo.list_countries(region="South Asia")}
        assert names == {"India"}

    def test_search_is_case_insensitive_substring(self, tiny_repo: Repository) -> None:
        names = {c["name"] for c in tiny_repo.list_countries(search="united")}
        assert names == {"United States"}

    def test_unknown_indicator_raises(self, tiny_repo: Repository) -> None:
        with pytest.raises(NotFoundError):
            tiny_repo.list_countries(indicator_id="not_real")


class TestGetSeries:
    def test_only_returns_years_with_data(self, tiny_repo: Repository) -> None:
        """USA has no 2021 inflation observation; it must be absent, not zero."""
        series = tiny_repo.get_series("inflation_rate", ["USA"])
        years = {p["year"] for p in series[0]["points"]}
        assert years == {2020, 2022}
        assert 2021 not in years

    def test_multiple_countries_each_get_their_own_series(self, tiny_repo: Repository) -> None:
        series = tiny_repo.get_series("gdp_per_capita", ["USA", "IND"])
        by_country = {s["iso3"]: s for s in series}
        assert len(by_country["USA"]["points"]) == 3
        assert len(by_country["IND"]["points"]) == 3

    def test_year_bounds_are_applied(self, tiny_repo: Repository) -> None:
        series = tiny_repo.get_series("gdp_per_capita", ["USA"], start_year=2021, end_year=2021)
        assert [p["year"] for p in series[0]["points"]] == [2021]

    def test_empty_country_list_returns_empty(self, tiny_repo: Repository) -> None:
        assert tiny_repo.get_series("gdp_per_capita", []) == []

    def test_requesting_country_with_no_data_omits_it(self, tiny_repo: Repository) -> None:
        series = tiny_repo.get_series("gdp_per_capita", ["USA", "KOR"])
        assert {s["iso3"] for s in series} == {"USA"}

    def test_unknown_indicator_raises(self, tiny_repo: Repository) -> None:
        with pytest.raises(NotFoundError):
            tiny_repo.get_series("not_real", ["USA"])


class TestGetSnapshot:
    def test_defaults_to_latest_year(self, tiny_repo: Repository) -> None:
        """No hardcoded year: the previous UI offered years the data didn't have."""
        snapshot = tiny_repo.get_snapshot("gdp_per_capita")
        assert snapshot["year"] == 2022

    def test_excludes_aggregates_by_default(self, tiny_repo: Repository) -> None:
        snapshot = tiny_repo.get_snapshot("gdp_per_capita", year=2022)
        assert "World" not in {v["country"] for v in snapshot["values"]}

    def test_can_include_aggregates(self, tiny_repo: Repository) -> None:
        snapshot = tiny_repo.get_snapshot("gdp_per_capita", year=2022, include_aggregates=True)
        assert "World" in {v["country"] for v in snapshot["values"]}

    def test_orders_descending_by_default(self, tiny_repo: Repository) -> None:
        snapshot = tiny_repo.get_snapshot("gdp_per_capita", year=2022)
        values = [v["value"] for v in snapshot["values"]]
        assert values == sorted(values, reverse=True)

    def test_ascending_order(self, tiny_repo: Repository) -> None:
        snapshot = tiny_repo.get_snapshot("gdp_per_capita", year=2022, order="asc")
        values = [v["value"] for v in snapshot["values"]]
        assert values == sorted(values)

    def test_min_population_filters_out_smaller_countries(self, tiny_repo: Repository) -> None:
        """South Korea (51M, has no gdp_per_capita) shouldn't leak; test on population itself."""
        snapshot = tiny_repo.get_snapshot("population", year=2022, min_population=100_000_000)
        countries = {v["country"] for v in snapshot["values"]}
        assert countries == {"United States", "India"}

    def test_year_with_no_data_returns_empty_values(self, tiny_repo: Repository) -> None:
        snapshot = tiny_repo.get_snapshot("gdp_per_capita", year=1999)
        assert snapshot["values"] == []

    def test_limit_is_respected(self, tiny_repo: Repository) -> None:
        snapshot = tiny_repo.get_snapshot("gdp_per_capita", year=2022, limit=1)
        assert len(snapshot["values"]) == 1

    def test_indicator_with_no_observations_returns_no_year(self, tiny_repo: Repository) -> None:
        snapshot = tiny_repo.get_snapshot("debt_to_gdp")
        assert snapshot == {"indicator_id": "debt_to_gdp", "year": None, "values": []}


class TestGetCountryProfile:
    def test_returns_latest_value_per_indicator(self, tiny_repo: Repository) -> None:
        profile = tiny_repo.get_country_profile("USA")
        by_indicator = {row["indicator_id"]: row for row in profile["latest"]}
        assert by_indicator["gdp_per_capita"]["year"] == 2022
        assert by_indicator["gdp_per_capita"]["value"] == pytest.approx(76_000.0)
        # inflation_rate's latest year for USA is 2022 (2021 was a deliberate gap)
        assert by_indicator["inflation_rate"]["year"] == 2022

    def test_unknown_country_raises(self, tiny_repo: Repository) -> None:
        with pytest.raises(NotFoundError):
            tiny_repo.get_country_profile("ZZZ")


class TestCorrelateOverTime:
    def test_correlates_two_indicators_within_a_country(self, tiny_repo: Repository) -> None:
        result = tiny_repo.correlate_over_time("USA", "gdp_per_capita", "inflation_rate")
        assert result["mode"] == "time"
        assert result["country"]["iso3"] == "USA"
        # Only 2020 and 2022 have both series (2021 inflation is missing for USA).
        assert len(result["points"]) == 2

    def test_too_few_points_yields_note_not_statistics(self, tiny_repo: Repository) -> None:
        result = tiny_repo.correlate_over_time("USA", "gdp_per_capita", "inflation_rate")
        assert result["statistics"] is None
        assert "overlapping observation" in result["note"]

    def test_unknown_country_raises(self, tiny_repo: Repository) -> None:
        with pytest.raises(NotFoundError):
            tiny_repo.correlate_over_time("ZZZ", "gdp_per_capita", "inflation_rate")


class TestCorrelateAcrossCountries:
    def test_correlates_across_countries_within_a_year(self, tiny_repo: Repository) -> None:
        result = tiny_repo.correlate_across_countries("gdp_per_capita", "inflation_rate", 2020)
        assert result["mode"] == "cross_section"
        assert result["year"] == 2020
        assert {p["label"] for p in result["points"]} == {"United States", "India"}

    def test_excludes_aggregates(self, tiny_repo: Repository) -> None:
        result = tiny_repo.correlate_across_countries("gdp_per_capita", "inflation_rate", 2020)
        assert "World" not in {p["label"] for p in result["points"]}


class TestQualityAndWarehouseInfo:
    def test_quality_report_round_trips(self, tiny_repo: Repository) -> None:
        report = tiny_repo.get_quality_report()
        assert report["total_observations"] == 15

    def test_warehouse_info_reports_counts(self, tiny_repo: Repository) -> None:
        info = tiny_repo.get_warehouse_info()
        assert info["observations"] == 15
        assert info["countries"] == 3  # excludes the World aggregate
