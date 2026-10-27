"""Imputation forensics: label reconstruction and detector plumbing.

The key test simulates the original notebook's imputation on synthetic wages
and checks that reconstruction recovers exactly the cells it filled.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from realgrowth_ml import anomaly

YEARS = list(range(2006, 2023))


def notebook_imputation(raw: pd.DataFrame) -> pd.DataFrame:
    """A faithful copy of ``fill_missing_with_ratio`` from notebooks/cleaning.ipynb."""
    world_avg = raw.mean()

    def fill(row: pd.Series) -> pd.Series:
        available = row.notna()
        if available.sum() == 0:
            return row
        mean_ratio = (row[available] / world_avg[available]).mean()
        return row.fillna(world_avg * mean_ratio)

    return raw.apply(fill, axis=1)


@pytest.fixture(scope="module")
def simulated() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(11)
    n = 40
    base = rng.lognormal(mean=7.0, sigma=1.5, size=n)
    growth = rng.normal(0.05, 0.04, size=(n, len(YEARS)))
    levels = base[:, None] * np.exp(np.cumsum(growth, axis=1))
    raw = pd.DataFrame(levels, index=[f"C{i:02d}" for i in range(n)], columns=YEARS)
    mask = rng.random(raw.shape) < 0.25
    mask[:, -1] |= rng.random(n) < 0.6  # latest year is most often missing
    mask[0, :] = False  # keep a couple of fully genuine countries
    mask[1, :] = False
    for i in range(n):  # every country keeps at least two genuine years
        if (~mask[i]).sum() < 2:
            mask[i, :2] = False
    raw_missing = raw.mask(mask)
    filled = notebook_imputation(raw_missing)
    truth = pd.DataFrame(mask, index=raw.index, columns=YEARS)
    return filled, truth


class TestReconstruction:
    def test_recovers_exactly_the_filled_cells(
        self, simulated: tuple[pd.DataFrame, pd.DataFrame]
    ) -> None:
        filled, truth = simulated
        labels = anomaly.reconstruct_labels(filled)
        mismatch = labels.imputed != truth
        assert int(mismatch.sum().sum()) == 0
        assert labels.diagnostics["imputed_cells"] == int(truth.sum().sum())

    def test_recovers_the_world_index_up_to_scale(
        self, simulated: tuple[pd.DataFrame, pd.DataFrame]
    ) -> None:
        filled, truth = simulated
        labels = anomaly.reconstruct_labels(filled)
        world = filled.mask(truth).mean()
        np.testing.assert_allclose(labels.world_index, world / world.iloc[0], rtol=1e-6)

    def test_clean_panel_has_no_labels(self) -> None:
        rng = np.random.default_rng(2)
        clean = pd.DataFrame(
            rng.lognormal(5, 1, size=(20, len(YEARS))),
            index=[f"C{i}" for i in range(20)],
            columns=YEARS,
        )
        assert anomaly.reconstruct_labels(clean).imputed.sum().sum() == 0


class TestRule:
    def test_rule_constants_match_the_etl(self) -> None:
        derive = pytest.importorskip("realgrowth.etl.derive")
        assert anomaly.RULE_GROWTH_PCT == derive.IMPLAUSIBLE_GROWTH_PCT
        assert anomaly.RULE_INFLATION_PCT == derive.INFLATION_EXPLAINS_PCT

    def test_rule_flags_both_cells_of_an_unexplained_jump(self) -> None:
        levels = pd.DataFrame([[100.0, 105.0, 300.0, 310.0]], index=["A"], columns=[1, 2, 3, 4])
        inflation = pd.DataFrame([[2.0, 2.0, 2.0, 2.0]], index=["A"], columns=[1, 2, 3, 4])
        flags = anomaly.rule_flags(levels, inflation)
        assert flags.loc[("A", 2)] and flags.loc[("A", 3)]
        assert not flags.loc[("A", 1)] and not flags.loc[("A", 4)]

    def test_inflation_explains_the_jump(self) -> None:
        levels = pd.DataFrame([[100.0, 300.0]], index=["A"], columns=[1, 2])
        inflation = pd.DataFrame([[150.0, 180.0]], index=["A"], columns=[1, 2])
        assert not anomaly.rule_flags(levels, inflation).any()


class TestFeatures:
    def test_one_row_per_observed_cell(self, simulated: tuple[pd.DataFrame, pd.DataFrame]) -> None:
        filled, _ = simulated
        inflation = pd.DataFrame(3.0, index=filled.index, columns=filled.columns)
        features = anomaly.cell_features(filled, inflation)
        assert len(features) == int(filled.notna().sum().sum())
        assert list(features.columns) == list(anomaly.DETECTOR_FEATURES)

    def test_detector_beats_chance_out_of_fold(
        self, simulated: tuple[pd.DataFrame, pd.DataFrame]
    ) -> None:
        from sklearn.metrics import average_precision_score

        filled, truth = simulated
        inflation = pd.DataFrame(3.0, index=filled.index, columns=filled.columns)
        features = anomaly.cell_features(filled, inflation)
        y_series = truth.stack()
        y_series.index = y_series.index.set_names(["iso3", "year"])
        y = y_series.reindex(features.index).to_numpy(dtype=int)
        scores = anomaly.out_of_fold_scores(features, y, n_splits=4)
        assert average_precision_score(y, scores) > 2 * y.mean()
