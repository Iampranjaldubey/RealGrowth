"""Wide-CSV parsing and reshaping."""

from __future__ import annotations

from pathlib import Path

import pytest

from realgrowth.etl.registry import Country, CountryRegistry
from realgrowth.etl.sources import GDP_PER_CAPITA, HEALTHY_DIET_COST, indicator
from realgrowth.etl.transform import (
    Observation,
    SourceSpec,
    extract,
    group_series,
    parse_number,
    read_wide_csv,
)


class TestParseNumber:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("42", 42.0),
            ("42.5", 42.5),
            ("-3.14", -3.14),
            ("909,121,500", 909_121_500.0),
            ("12.5%", 12.5),
            ("$1,234.50", 1234.50),
            ("(5.2)", -5.2),
        ],
    )
    def test_parses_valid_numbers(self, raw: str, expected: float) -> None:
        assert parse_number(raw) == pytest.approx(expected)

    @pytest.mark.parametrize("raw", ["", "  ", "..", "-", "N/A", "n/a", "NaN", None])
    def test_missing_tokens_become_none(self, raw: str | None) -> None:
        assert parse_number(raw) is None

    def test_non_numeric_text_becomes_none(self) -> None:
        assert parse_number("Country name") is None

    def test_rejects_infinity_and_nan_strings(self) -> None:
        assert parse_number("inf") is None
        assert parse_number("-inf") is None
        assert parse_number("nan") is None


@pytest.fixture
def registry() -> CountryRegistry:
    return CountryRegistry(
        [
            Country("USA", "United States", "North America", False),
            Country("IND", "India", "South Asia", False),
            Country("ALB", "Albania", "Europe & Central Asia", False),
        ],
        {},
    )


def _write_csv(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


class TestReadWideCsv:
    def test_finds_columns_by_label_not_position(self, tmp_path: Path) -> None:
        """The exact bug class that broke the old growth endpoint.

        A leading unnamed index column must not shift which column is read as
        which year.
        """
        path = _write_csv(
            tmp_path / "wide.csv",
            ",Country name,2010,2011\n0,Afghanistan,49.2,4.1\n",
        )
        spec = SourceSpec("x", "wide.csv", name_column="Country name")
        table = read_wide_csv(path, spec)
        assert table.years == (2010, 2011)
        assert table.rows[0]["Country name"] == "Afghanistan"
        assert table.rows[0]["2010"] == "49.2"

    def test_missing_name_column_raises(self, tmp_path: Path) -> None:
        path = _write_csv(tmp_path / "bad.csv", "Nope,2010\nFoo,1\n")
        spec = SourceSpec("x", "bad.csv", name_column="Country")
        with pytest.raises(ValueError, match="Country"):
            read_wide_csv(path, spec)

    def test_no_year_columns_raises(self, tmp_path: Path) -> None:
        path = _write_csv(tmp_path / "bad.csv", "Country,Notes\nFoo,bar\n")
        spec = SourceSpec("x", "bad.csv", name_column="Country")
        with pytest.raises(ValueError, match="no four-digit year columns"):
            read_wide_csv(path, spec)


class TestExtract:
    def test_reshapes_wide_to_long(self, tmp_path: Path, registry: CountryRegistry) -> None:
        path = _write_csv(
            tmp_path / "gdp.csv",
            "Country Name,2020,2021\nUnited States,63000,70000\nIndia,1900,2100\n",
        )
        spec = SourceSpec(GDP_PER_CAPITA, "gdp.csv", name_column="Country Name")
        table = read_wide_csv(path, spec)
        obs, issues = extract(table, spec, registry, indicator(GDP_PER_CAPITA))
        assert issues == []
        assert set(obs) == {
            Observation(GDP_PER_CAPITA, "USA", 2020, 63000.0),
            Observation(GDP_PER_CAPITA, "USA", 2021, 70000.0),
            Observation(GDP_PER_CAPITA, "IND", 2020, 1900.0),
            Observation(GDP_PER_CAPITA, "IND", 2021, 2100.0),
        }

    def test_missing_cells_produce_no_observation(
        self, tmp_path: Path, registry: CountryRegistry
    ) -> None:
        path = _write_csv(
            tmp_path / "gdp.csv", "Country Name,2020,2021\nIndia,1900,\n"
        )
        spec = SourceSpec(GDP_PER_CAPITA, "gdp.csv", name_column="Country Name")
        table = read_wide_csv(path, spec)
        obs, _ = extract(table, spec, registry, indicator(GDP_PER_CAPITA))
        assert obs == [Observation(GDP_PER_CAPITA, "IND", 2020, 1900.0)]

    def test_unresolved_entity_is_reported_not_dropped_silently(
        self, tmp_path: Path, registry: CountryRegistry
    ) -> None:
        path = _write_csv(
            tmp_path / "gdp.csv", "Country Name,2020\nAtlantis,1000\n"
        )
        spec = SourceSpec(GDP_PER_CAPITA, "gdp.csv", name_column="Country Name")
        table = read_wide_csv(path, spec)
        obs, issues = extract(table, spec, registry, indicator(GDP_PER_CAPITA))
        assert obs == []
        assert len(issues) == 1
        assert issues[0].kind == "unresolved_entity"
        assert issues[0].entity == "Atlantis"

    def test_out_of_range_value_is_dropped_and_reported(
        self, tmp_path: Path, registry: CountryRegistry
    ) -> None:
        path = _write_csv(
            tmp_path / "gdp.csv", "Country Name,2020\nIndia,-999999\n"
        )
        spec = SourceSpec(GDP_PER_CAPITA, "gdp.csv", name_column="Country Name")
        table = read_wide_csv(path, spec)
        obs, issues = extract(table, spec, registry, indicator(GDP_PER_CAPITA))
        assert obs == []
        assert issues[0].kind == "out_of_range"

    def test_prefers_code_column_when_present(
        self, tmp_path: Path, registry: CountryRegistry
    ) -> None:
        """The one source with ISO codes should be trusted over name matching."""
        path = _write_csv(
            tmp_path / "diet.csv",
            "Entity,Code,2020\nAlbania,ALB,3.5\n",
        )
        spec = SourceSpec(
            HEALTHY_DIET_COST, "diet.csv", name_column="Entity", code_column="Code"
        )
        table = read_wide_csv(path, spec)
        obs, issues = extract(table, spec, registry, indicator(HEALTHY_DIET_COST))
        assert issues == []
        assert obs == [Observation(HEALTHY_DIET_COST, "ALB", 2020, 3.5)]

    def test_two_rows_resolving_to_same_country_conflict_reported(
        self, tmp_path: Path, registry: CountryRegistry
    ) -> None:
        path = _write_csv(
            tmp_path / "gdp.csv",
            "Country Name,2020\nUnited States,63000\nUnited States,64000\n",
        )
        spec = SourceSpec(GDP_PER_CAPITA, "gdp.csv", name_column="Country Name")
        table = read_wide_csv(path, spec)
        obs, issues = extract(table, spec, registry, indicator(GDP_PER_CAPITA))
        assert obs == [Observation(GDP_PER_CAPITA, "USA", 2020, 63000.0)]
        assert any(i.kind == "duplicate_entity" for i in issues)


class TestGroupSeries:
    def test_indexes_by_indicator_and_country(self) -> None:
        observations = [
            Observation("gdp_per_capita", "USA", 2020, 63000.0),
            Observation("gdp_per_capita", "USA", 2021, 70000.0),
            Observation("gdp_per_capita", "IND", 2020, 1900.0),
        ]
        series = group_series(observations)
        assert series[("gdp_per_capita", "USA")] == {2020: 63000.0, 2021: 70000.0}
        assert series[("gdp_per_capita", "IND")] == {2020: 1900.0}
