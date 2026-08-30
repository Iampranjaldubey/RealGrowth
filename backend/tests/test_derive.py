"""Derived indicators: nominal/real wage growth and population aggregates.

These tests encode the two most important findings from reverse-engineering the
original dataset: real wage growth equals nominal wage growth minus inflation,
and the old artefact fabricated values by treating "no wage data" as "0% nominal
growth". Both regressions are pinned here.
"""

from __future__ import annotations

import pytest

from realgrowth.etl.derive import (
    derive_all,
    derive_nominal_wage_growth,
    derive_population,
    derive_real_wage_growth,
    is_implausible_growth,
    year_on_year_change,
)
from realgrowth.etl.sources import (
    AVG_WAGE,
    INFLATION_RATE,
    NOMINAL_WAGE_GROWTH,
    POPULATION,
    REAL_WAGE_GROWTH,
    RURAL_POPULATION,
    URBAN_POPULATION,
    URBANISATION_RATE,
)


class TestYearOnYearChange:
    def test_computes_percent_change(self) -> None:
        result = year_on_year_change({2020: 100.0, 2021: 110.0, 2022: 99.0})
        assert result[2021] == pytest.approx(10.0)
        assert result[2022] == pytest.approx(-10.0)
        assert 2020 not in result  # no prior year to compare against

    def test_skips_non_consecutive_years(self) -> None:
        """A 2015->2019 jump is not a single year's growth rate."""
        result = year_on_year_change({2015: 100.0, 2019: 200.0})
        assert result == {}

    def test_skips_zero_base(self) -> None:
        result = year_on_year_change({2020: 0.0, 2021: 50.0})
        assert 2021 not in result


class TestImplausibleGrowth:
    def test_moderate_growth_always_plausible(self) -> None:
        assert not is_implausible_growth(15.0, None)
        assert not is_implausible_growth(-15.0, 3.0)

    def test_large_unexplained_move_is_implausible(self) -> None:
        # Spain 2022: +147.5% wage move against 8.4% inflation.
        assert is_implausible_growth(147.5, 8.4)

    def test_large_move_explained_by_inflation_is_plausible(self) -> None:
        # Zimbabwe-like: triple-digit inflation legitimately drives large moves.
        assert not is_implausible_growth(-162.4, 120.0)

    def test_large_move_with_no_inflation_data_is_implausible(self) -> None:
        assert is_implausible_growth(80.0, None)


class TestDeriveNominalWageGrowth:
    def test_computes_growth_from_wage_levels(self) -> None:
        series = {
            (AVG_WAGE, "IND"): {2020: 100.0, 2021: 110.0, 2022: 121.0},
            (INFLATION_RATE, "IND"): {2020: 5.0, 2021: 5.0, 2022: 5.0},
        }
        obs, issues, flags = derive_nominal_wage_growth(series)
        by_year = {o.year: o.value for o in obs}
        assert by_year[2021] == pytest.approx(10.0)
        assert by_year[2022] == pytest.approx(10.0)
        assert flags == []

    def test_rejects_implausible_transition_and_flags_series(self) -> None:
        series = {
            # 2022 jumps +150% with only 8% inflation to explain it.
            (AVG_WAGE, "ESP"): {2020: 2000.0, 2021: 2100.0, 2022: 5250.0},
            (INFLATION_RATE, "ESP"): {2020: 1.0, 2021: 2.0, 2022: 8.4},
        }
        obs, issues, flags = derive_nominal_wage_growth(series)
        years = {o.year for o in obs}
        assert 2022 not in years
        assert 2021 in years  # the plausible transition survives
        assert any(i.kind == "implausible_growth" and i.year == 2022 for i in issues)
        assert {f.flag for f in flags} == {"volatile_levels", "partial_coverage"}
        assert {f.indicator_id for f in flags} == {
            AVG_WAGE,
            NOMINAL_WAGE_GROWTH,
            REAL_WAGE_GROWTH,
        }

    def test_missing_inflation_still_allows_plausible_growth(self) -> None:
        """A country with no inflation series shouldn't lose good wage data."""
        series = {(AVG_WAGE, "XYZ"): {2020: 100.0, 2021: 112.0}}
        obs, issues, flags = derive_nominal_wage_growth(series)
        assert obs[0].value == pytest.approx(12.0)
        assert flags == []


class TestDeriveRealWageGrowth:
    def test_is_nominal_minus_inflation(self) -> None:
        series = {
            (NOMINAL_WAGE_GROWTH, "USA"): {2022: 5.0},
            (INFLATION_RATE, "USA"): {2022: 8.0},
        }
        obs, issues, _ = derive_real_wage_growth(series)
        assert obs == [pytest.approx(("real_wage_growth", "USA", 2022, -3.0))]

    def test_reproduces_original_artefact_for_populated_cells(self) -> None:
        """Pinning the exact relationship recovered from the vendored CSV.

        real_growth.csv matched wage_growth - inflation on all 1,530 non-empty
        cells checked; this test is the executable version of that check.
        """
        series = {
            (NOMINAL_WAGE_GROWTH, "ALB"): {2015: -17.91},
            (INFLATION_RATE, "ALB"): {2015: 1.93},
        }
        obs, _, _ = derive_real_wage_growth(series)
        assert obs[0].value == pytest.approx(-17.91 - 1.93)

    def test_no_observation_without_both_inputs(self) -> None:
        series = {(NOMINAL_WAGE_GROWTH, "USA"): {2022: 5.0}}  # no inflation series
        obs, _, _ = derive_real_wage_growth(series)
        assert obs == []

    def test_does_not_fabricate_afghanistan_2021_2022(self) -> None:
        """The specific fabrication this rebuild fixes.

        The old artefact reported -5.13% (2021) and -13.71% (2022) for
        Afghanistan purely because nominal growth was zero-filled; with no wage
        observation for those years, no growth rate should exist at all.
        """
        series = {
            (AVG_WAGE, "AFG"): {2020: 171.87},  # last real observation
            (INFLATION_RATE, "AFG"): {2020: 5.6, 2021: 5.1, 2022: 13.7},
        }
        nominal, _, _ = derive_nominal_wage_growth(series)
        assert nominal == []  # no 2021/2022 wage level -> no growth rate at all

        full_series = dict(series)
        full_series[(NOMINAL_WAGE_GROWTH, "AFG")] = {}
        real, _, _ = derive_real_wage_growth(full_series)
        assert real == []


class TestDerivePopulation:
    def test_total_and_urbanisation_rate(self) -> None:
        series = {
            (URBAN_POPULATION, "IND"): {2022: 600.0},
            (RURAL_POPULATION, "IND"): {2022: 400.0},
        }
        obs, issues, _ = derive_population(series)
        by_indicator = {o.indicator_id: o.value for o in obs}
        assert by_indicator[POPULATION] == pytest.approx(1000.0)
        assert by_indicator[URBANISATION_RATE] == pytest.approx(60.0)

    def test_requires_both_urban_and_rural(self) -> None:
        series = {(URBAN_POPULATION, "SGP"): {2022: 5_000_000.0}}  # city-state, no rural row
        obs, _, _ = derive_population(series)
        assert obs == []


class TestDeriveAll:
    def test_real_growth_uses_freshly_derived_nominal_growth(self) -> None:
        """derive_all must feed nominal growth back in before computing real growth."""
        series = {
            (AVG_WAGE, "IND"): {2020: 100.0, 2021: 112.0},
            (INFLATION_RATE, "IND"): {2021: 5.0},
        }
        produced, issues, flags = derive_all(series)
        real = [o for o in produced if o.indicator_id == REAL_WAGE_GROWTH]
        assert real and real[0].value == pytest.approx(12.0 - 5.0)
