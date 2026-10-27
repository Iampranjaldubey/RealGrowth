"""Feature engineering: transforms, alignment, and the no-look-ahead guarantee."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from realgrowth_ml.data import Panel, panel_from_frames
from realgrowth_ml.features import FEATURE_NAMES, build_feature_frame, inv_slog, slog


class TestSlog:
    @pytest.mark.parametrize("x", [-50.0, -1.0, 0.0, 0.5, 3.0, 120.0, 65_000.0])
    def test_round_trips(self, x: float) -> None:
        assert inv_slog(slog(x)) == pytest.approx(x)

    def test_is_odd_and_monotone(self) -> None:
        xs = np.linspace(-100, 100, 201)
        ys = np.asarray(slog(xs))
        assert np.all(np.diff(ys) > 0)
        assert np.allclose(ys, -np.asarray(slog(-xs)))


class TestAlignment:
    def test_lags_and_targets_line_up(self) -> None:
        obs = pd.DataFrame(
            [("inflation_rate", "AAA", y, float(y - 2000)) for y in range(1990, 2011)],
            columns=["indicator_id", "iso3", "year", "value"],
        )
        frame = build_feature_frame(panel_from_frames(obs), [1, 2], first_year=1990)
        row = frame[frame["year"] == 2005].iloc[0]
        assert row["infl_raw"] == 5.0
        assert row["infl_lag0"] == pytest.approx(slog(5.0))
        assert row["infl_lag1"] == pytest.approx(slog(4.0))
        assert row["infl_lag2"] == pytest.approx(slog(3.0))
        assert row["actual_h1"] == 6.0
        assert row["actual_h2"] == 7.0
        assert row["target_h1"] == pytest.approx(slog(6.0))
        last = frame[frame["year"] == 2010].iloc[0]
        assert np.isnan(last["target_h1"])  # the future is unknown, not zero

    def test_missing_year_breaks_lags_instead_of_skipping(self) -> None:
        """A 2003 gap must leave lag1 of 2004 empty, not reuse 2002."""
        obs = pd.DataFrame(
            [("inflation_rate", "AAA", y, 2.0) for y in range(1995, 2011) if y != 2003],
            columns=["indicator_id", "iso3", "year", "value"],
        )
        frame = build_feature_frame(panel_from_frames(obs), [1], first_year=1995)
        row = frame[frame["year"] == 2004].iloc[0]
        assert np.isnan(row["infl_lag1"])
        assert row["infl_lag2"] == pytest.approx(slog(2.0))


class TestNoLookAhead:
    def test_future_values_cannot_change_past_features(self, panel: Panel) -> None:
        """The core leakage guarantee, tested by intervention.

        Scramble every observation after 2010 in every indicator; every
        feature of every row with origin <= 2010 must be bit-identical.
        """
        base = build_feature_frame(panel, [1, 2])
        obs = panel.observations.copy()
        future = obs["year"] > 2010
        rng = np.random.default_rng(1)
        obs.loc[future, "value"] = rng.normal(500.0, 300.0, int(future.sum()))
        perturbed = build_feature_frame(Panel(obs, panel.countries), [1, 2])

        cols = list(FEATURE_NAMES)
        a = base[base["year"] <= 2010].set_index(["iso3", "year"])[cols]
        b = perturbed[perturbed["year"] <= 2010].set_index(["iso3", "year"])[cols]
        pd.testing.assert_frame_equal(a, b)

    def test_targets_do_change_so_the_test_has_teeth(self, panel: Panel) -> None:
        base = build_feature_frame(panel, [1])
        obs = panel.observations.copy()
        obs.loc[obs["year"] == 2011, "value"] += 100.0
        perturbed = build_feature_frame(Panel(obs, panel.countries), [1])
        row_a = base[base["year"] == 2010]["target_h1"].to_numpy()
        row_b = perturbed[perturbed["year"] == 2010]["target_h1"].to_numpy()
        assert not np.allclose(row_a, row_b)

    def test_aggregates_are_excluded(self) -> None:
        obs = pd.DataFrame(
            [("inflation_rate", c, y, 3.0) for c in ("AAA", "WLD") for y in range(1990, 2000)],
            columns=["indicator_id", "iso3", "year", "value"],
        )
        countries = pd.DataFrame(
            {
                "iso3": ["AAA", "WLD"],
                "name": ["A", "World"],
                "region": ["R", None],
                "is_aggregate": [False, True],
            }
        ).set_index("iso3")
        frame = build_feature_frame(panel_from_frames(obs, countries), [1], first_year=1990)
        assert set(frame["iso3"]) == {"AAA"}
