"""Backtest splits, models, conformal intervals and evaluation metrics."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from realgrowth_ml.backtest import run_backtest, training_mask
from realgrowth_ml.conformal import add_intervals, conformal_quantile, regime
from realgrowth_ml.data import Panel
from realgrowth_ml.features import build_feature_frame, slog
from realgrowth_ml.metrics import coverage, diebold_mariano, point_metrics, skill
from realgrowth_ml.models import MODEL_SPECS, Ensemble, LightGBMForecaster, PooledAR, spec


@pytest.fixture(scope="module")
def frame(panel: Panel) -> pd.DataFrame:
    return build_feature_frame(panel, [1, 2])


# --------------------------------------------------------------- backtest


class TestTrainingMask:
    @pytest.mark.parametrize("horizon", [1, 2])
    def test_no_training_target_is_after_the_origin(
        self, frame: pd.DataFrame, horizon: int
    ) -> None:
        for origin in (1995, 2005, 2015):
            rows = frame[training_mask(frame, origin, horizon)]
            assert (rows["year"] + horizon).max() <= origin

    def test_two_step_horizon_excludes_the_previous_origin(self, frame: pd.DataFrame) -> None:
        """Origin o-1 with h=2 targets o+1: still the future at origin o."""
        rows = frame[training_mask(frame, 2010, 2)]
        assert rows["year"].max() == 2008


class _Spy:
    """A forecaster that records the rows it was trained on."""

    seen: list[int] = []

    def fit(self, f: pd.DataFrame, target: pd.Series) -> _Spy:
        _Spy.seen.append(int(f["year"].max()))
        return self

    def predict(self, f: pd.DataFrame) -> np.ndarray:
        return f["infl_lag0"].to_numpy()


class TestRunBacktest:
    def test_each_origin_trains_only_on_its_past(self, frame: pd.DataFrame) -> None:
        _Spy.seen = []
        bt = run_backtest(frame, "spy", lambda _: _Spy(), horizon=2, origins=range(2000, 2005))
        assert _Spy.seen == [1998, 1999, 2000, 2001, 2002]
        assert set(bt["target_year"] - bt["origin_year"]) == {2}

    def test_actuals_are_the_observed_future(self, frame: pd.DataFrame) -> None:
        bt = run_backtest(frame, "naive", spec("naive").factory, horizon=1, origins=[2010])
        merged = bt.merge(
            frame[["iso3", "year", "infl_raw"]],
            left_on=["iso3", "target_year"],
            right_on=["iso3", "year"],
        )
        np.testing.assert_allclose(merged["actual"], merged["infl_raw"])


# ----------------------------------------------------------------- models


class TestModels:
    def test_naive_returns_last_value(self, frame: pd.DataFrame) -> None:
        model = spec("naive").factory({})
        np.testing.assert_allclose(model.predict(frame), frame["infl_lag0"])

    def test_learned_models_beat_naive_on_mean_reverting_data(self, frame: pd.DataFrame) -> None:
        """The synthetic panel is AR(1) around a country mean, so pooled
        regression on lags must beat the random walk out of sample."""
        scores = {}
        for model_id in ("naive", "pooled_ar", "lgbm_global"):
            bt = run_backtest(
                frame, model_id, spec(model_id).factory, horizon=1, origins=range(2010, 2024)
            )
            scores[model_id] = point_metrics(bt["actual"], bt["point"]).mae_log
        assert scores["pooled_ar"] < scores["naive"]
        assert scores["lgbm_global"] < scores["naive"]

    def test_pooled_ar_falls_back_to_naive_when_lags_missing(self, frame: pd.DataFrame) -> None:
        model = PooledAR().fit(frame, frame["target_h1"])
        row = frame.iloc[[0]].copy()
        row["infl_lag2"] = np.nan
        assert model.predict(row)[0] == pytest.approx(row["infl_lag0"].iloc[0])

    @pytest.mark.parametrize("factory", [PooledAR, LightGBMForecaster, Ensemble])
    def test_contributions_sum_to_prediction(self, frame: pd.DataFrame, factory: type) -> None:
        """SHAP's local-accuracy property, for every explainable model."""
        train = frame[frame["target_h1"].notna()]
        model = factory().fit(train, train["target_h1"])
        sample = train.dropna(subset=["infl_lag1", "infl_lag2"]).tail(25)
        total = model.contributions(sample).sum(axis=1).to_numpy()
        np.testing.assert_allclose(total, model.predict(sample), atol=1e-6)

    def test_lightgbm_is_deterministic(self, frame: pd.DataFrame) -> None:
        train = frame[frame["target_h1"].notna()]
        a = LightGBMForecaster().fit(train, train["target_h1"]).predict(train.tail(50))
        b = LightGBMForecaster().fit(train, train["target_h1"]).predict(train.tail(50))
        np.testing.assert_array_equal(a, b)

    def test_model_ids_are_unique(self) -> None:
        ids = [m.id for m in MODEL_SPECS]
        assert len(ids) == len(set(ids))
        assert {"naive", "pooled_ar", "lgbm_global", "ensemble"} <= set(ids)


# -------------------------------------------------------------- conformal


class TestConformal:
    def test_quantile_uses_finite_sample_rank(self) -> None:
        scores = np.arange(1.0, 11.0)  # 1..10
        # ceil(11 * 0.8) = 9 -> 9th smallest
        assert conformal_quantile(scores, 0.8) == 9.0
        # ceil(11 * 0.95) = 11 > n -> no finite interval
        assert math.isinf(conformal_quantile(scores, 0.95))

    def test_regime_bins(self) -> None:
        np.testing.assert_array_equal(regime(np.array([1.0, -5.0, 4.0, 12.0])), [0, 1, 1, 2])

    def test_marginal_coverage_on_exchangeable_errors(self) -> None:
        """With i.i.d. errors, split-conformal intervals must cover at the
        nominal rate (within sampling error)."""
        rng = np.random.default_rng(7)
        rows = []
        for year in range(1990, 2030):
            for i in range(60):
                truth = rng.normal(2.0, 0.3)
                rows.append(
                    {
                        "model_id": "m",
                        "iso3": f"C{i}",
                        "horizon": 1,
                        "origin_year": year,
                        "target_year": year + 1,
                        "infl_origin": 2.0,
                        "target_log": truth,
                        "point_log": truth + rng.normal(0, 0.2),
                        "actual": float(np.expm1(truth)),
                    }
                )
        out = add_intervals(pd.DataFrame(rows), window=10)
        evaluated = out[out["lower_80"].notna()]
        cov80, n = coverage(evaluated["actual"], evaluated["lower_80"], evaluated["upper_80"])
        cov95, _ = coverage(evaluated["actual"], evaluated["lower_95"], evaluated["upper_95"])
        assert n > 1_500
        assert 0.77 <= cov80 <= 0.83
        assert 0.93 <= cov95 <= 0.97

    def test_calibration_never_uses_unobserved_targets(self) -> None:
        """An origin's interval may only use errors whose target year has
        already been observed — never its own (future) error."""
        rows = [
            {
                "model_id": "m",
                "iso3": f"C{i}",
                "horizon": 1,
                "origin_year": y,
                "target_year": y + 1,
                "infl_origin": 2.0,
                "target_log": 1.0,
                "point_log": 1.0 + (5.0 if y == 2001 else 0.1),
                "actual": 1.7,
            }
            for y in range(2000, 2004)
            for i in range(20)
        ]
        out = add_intervals(pd.DataFrame(rows)).groupby("origin_year").first()
        assert np.isnan(out.loc[2000, "lower_80"])  # nothing observed yet
        # Origin 2001's own +5 errors (target 2002) are not visible at 2001...
        width_2001 = out.loc[2001, "upper_80"] - out.loc[2001, "lower_80"]
        # ...but are by 2003, so the interval widens.
        width_2003 = out.loc[2003, "upper_80"] - out.loc[2003, "lower_80"]
        assert width_2001 < width_2003


# ---------------------------------------------------------------- metrics


class TestMetrics:
    def test_point_metrics(self) -> None:
        m = point_metrics(np.array([1.0, 2.0, 3.0, np.nan]), np.array([1.0, 3.0, 5.0, 9.0]))
        assert m.n == 3
        assert m.mae == pytest.approx(1.0)
        assert m.rmse == pytest.approx(math.sqrt(5 / 3))
        assert m.median_ae == pytest.approx(1.0)
        expected_log = np.mean(
            np.abs(slog(np.array([1.0, 2.0, 3.0])) - slog(np.array([1.0, 3.0, 5.0])))
        )
        assert m.mae_log == pytest.approx(expected_log)

    def test_skill(self) -> None:
        assert skill(0.9, 1.0) == pytest.approx(0.1)
        assert math.isnan(skill(1.0, 0.0))

    def test_diebold_mariano_detects_a_real_difference(self) -> None:
        rng = np.random.default_rng(3)
        years = np.repeat(np.arange(2000, 2030), 50)
        frame = pd.DataFrame({"target_year": years, "a": rng.gamma(2, 0.5, years.size)})
        frame["b"] = frame["a"] + 0.2 + rng.normal(0, 0.05, years.size)
        result = diebold_mariano(frame, "a", "b")
        assert result.statistic < 0 and result.p_value < 0.01
        assert result.n_periods == 30

    def test_diebold_mariano_is_not_fooled_by_noise(self) -> None:
        rng = np.random.default_rng(4)
        years = np.repeat(np.arange(2000, 2030), 50)
        frame = pd.DataFrame(
            {
                "target_year": years,
                "a": rng.gamma(2, 0.5, years.size),
                "b": rng.gamma(2, 0.5, years.size),
            }
        )
        assert diebold_mariano(frame, "a", "b").p_value > 0.05
