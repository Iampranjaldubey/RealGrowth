"""Strict mode: which issue kinds are allowed to ship vs. must fail the build."""

from __future__ import annotations

from pathlib import Path

import pytest

from realgrowth.etl.pipeline import StrictModeError, run_etl
from realgrowth.etl.sources import API_INDICATORS


def _write_csv(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "raw"
    (directory / "api").mkdir(parents=True)
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


def _write_all_sources(raw_dir: Path, *, skip: str | None = None) -> None:
    """A minimal but complete snapshot: every API series plus the wage CSV."""
    for indicator_id in API_INDICATORS:
        if indicator_id == skip:
            continue
        _write_csv(
            raw_dir / "api" / f"{indicator_id}.csv",
            "iso3,year,value\nUSA,2020,1.5\nUSA,2021,2.5\nIND,2020,5.0\nIND,2021,6.0\n",
        )
    _write_csv(
        raw_dir / "avg_wage.csv",
        ",Country name,2020,2021\n0,United States,4000,4200\n1,India,150,160\n",
    )


class TestStrictMode:
    def test_clean_data_passes_strict_mode(
        self, raw_dir: Path, reference_csv: Path, tmp_path: Path
    ) -> None:
        _write_all_sources(raw_dir)
        report = run_etl(raw_dir, reference_csv, tmp_path / "out.db", strict=True)
        assert report.total_observations > 0

    def test_unknown_code_in_snapshot_fails_strict_mode(
        self, raw_dir: Path, reference_csv: Path, tmp_path: Path
    ) -> None:
        _write_all_sources(raw_dir)
        _write_csv(raw_dir / "api" / "gdp_per_capita.csv", "iso3,year,value\nATL,2020,1000\n")
        with pytest.raises(StrictModeError, match="unresolved_entity"):
            run_etl(raw_dir, reference_csv, tmp_path / "out.db", strict=True)

    def test_unresolved_wage_label_fails_strict_mode(
        self, raw_dir: Path, reference_csv: Path, tmp_path: Path
    ) -> None:
        _write_all_sources(raw_dir)
        _write_csv(raw_dir / "avg_wage.csv", ",Country name,2020\n0,Atlantis,100\n")
        with pytest.raises(StrictModeError, match="unresolved_entity"):
            run_etl(raw_dir, reference_csv, tmp_path / "out.db", strict=True)

    def test_unresolved_entity_does_not_fail_non_strict_mode(
        self, raw_dir: Path, reference_csv: Path, tmp_path: Path
    ) -> None:
        _write_all_sources(raw_dir)
        _write_csv(raw_dir / "avg_wage.csv", ",Country name,2020\n0,Atlantis,100\n")
        report = run_etl(raw_dir, reference_csv, tmp_path / "out.db", strict=False)
        assert "Atlantis" in report.unresolved_entities

    def test_missing_snapshot_file_fails_strict_mode(
        self, raw_dir: Path, reference_csv: Path, tmp_path: Path
    ) -> None:
        """A series silently vanishing from the snapshot is a defect, not a gap."""
        _write_all_sources(raw_dir, skip="inflation_rate")
        with pytest.raises(StrictModeError, match="missing_source"):
            run_etl(raw_dir, reference_csv, tmp_path / "out.db", strict=True)

    def test_out_of_range_value_does_not_fail_strict_mode(
        self, raw_dir: Path, reference_csv: Path, tmp_path: Path
    ) -> None:
        """out_of_range is an expected plausibility-filter finding, not a defect
        that should block a build — see FATAL_ISSUE_KINDS."""
        _write_all_sources(raw_dir)
        _write_csv(
            raw_dir / "api" / "gdp_per_capita.csv",
            "iso3,year,value\nUSA,2020,63000\nIND,2021,-999999\n",
        )
        report = run_etl(raw_dir, reference_csv, tmp_path / "out.db", strict=True)
        assert report.issue_counts.get("out_of_range", 0) >= 1
