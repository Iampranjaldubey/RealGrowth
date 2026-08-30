"""Strict mode: which issue kinds are allowed to ship vs. must fail the build."""

from __future__ import annotations

from pathlib import Path

import pytest

from realgrowth.etl.pipeline import StrictModeError, run_etl


def _write_csv(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "raw"
    directory.mkdir()
    return directory


@pytest.fixture
def reference_csv(tmp_path: Path) -> Path:
    path = tmp_path / "countries.csv"
    path.write_text(
        "iso3,name,region,is_aggregate,aliases\n"
        "USA,United States,North America,0,\n"
        "IND,India,South Asia,0,\n",
        encoding="utf-8",
    )
    return path


def _write_all_sources(raw_dir: Path, *, gdp_extra_row: str = "") -> None:
    _write_csv(
        raw_dir / "gdp_per_capita.csv",
        "Country Name,2020,2021\nUnited States,63000,70000\nIndia,1900,2100\n" + gdp_extra_row,
    )
    _write_csv(
        raw_dir / "inflation_rate.csv", "Country,2020,2021\nUnited States,1.2,4.7\nIndia,6.6,5.1\n"
    )
    _write_csv(
        raw_dir / "avg_wage.csv",
        ",Country name,2020,2021\n0,United States,4000,4200\n1,India,150,160\n",
    )
    _write_csv(raw_dir / "debt_to_gdp.csv", "Country Name,2021,2020\nUnited States,120,110\n")
    _write_csv(
        raw_dir / "healthy_diet_cost.csv", "Unnamed: 0,Entity,Code,2020\n0,United States,USA,3.5\n"
    )
    _write_csv(raw_dir / "rural_population.csv", "Country Name,2021\nUnited States,60000000\n")
    _write_csv(raw_dir / "urban_population.csv", "Country Name,2021\nUnited States,270000000\n")


class TestStrictMode:
    def test_clean_data_passes_strict_mode(
        self, raw_dir: Path, reference_csv: Path, tmp_path: Path
    ) -> None:
        _write_all_sources(raw_dir)
        report = run_etl(raw_dir, reference_csv, tmp_path / "out.db", strict=True)
        assert report.total_observations > 0

    def test_unresolved_entity_fails_strict_mode(
        self, raw_dir: Path, reference_csv: Path, tmp_path: Path
    ) -> None:
        _write_all_sources(raw_dir, gdp_extra_row="Atlantis,1000,1000\n")
        with pytest.raises(StrictModeError, match="unresolved_entity"):
            run_etl(raw_dir, reference_csv, tmp_path / "out.db", strict=True)

    def test_unresolved_entity_does_not_fail_non_strict_mode(
        self, raw_dir: Path, reference_csv: Path, tmp_path: Path
    ) -> None:
        _write_all_sources(raw_dir, gdp_extra_row="Atlantis,1000,1000\n")
        report = run_etl(raw_dir, reference_csv, tmp_path / "out.db", strict=False)
        assert "Atlantis" in report.unresolved_entities

    def test_out_of_range_value_does_not_fail_strict_mode(
        self, raw_dir: Path, reference_csv: Path, tmp_path: Path
    ) -> None:
        """out_of_range is an expected plausibility-filter finding, not a defect
        that should block a build — see FATAL_ISSUE_KINDS."""
        _write_all_sources(raw_dir)
        _write_csv(
            raw_dir / "gdp_per_capita.csv",
            "Country Name,2020,2021\nUnited States,63000,70000\nIndia,1900,-999999\n",
        )
        report = run_etl(raw_dir, reference_csv, tmp_path / "out.db", strict=True)
        assert report.issue_counts.get("out_of_range", 0) >= 1
