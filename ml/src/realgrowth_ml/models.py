"""Forecasting models, all predicting slog inflation ``h`` years ahead.

Every model implements ``fit(frame, target) -> self`` and ``predict(frame)``
on the same feature frame, so the backtest treats them identically. The
baselines matter as much as the champion: a model is only worth serving if it
beats "inflation next year equals inflation this year" out of sample.

* ``naive``        — random walk: next value equals the last value.
* ``mean3``        — mean of the last three years.
* ``pooled_ar``    — ridge regression on three lags + the global median,
                     pooled across countries (a linear panel AR(3)).
* ``lgbm_infl_only``— gradient boosting on inflation-history features only
                     (ablation: what do the macro features add?).
* ``lgbm_global``  — gradient boosting on all features, one model for all
                     countries ("global" model, as in the M4/M5 literature).
* ``ensemble``     — equal-weight average of ``pooled_ar`` and ``lgbm_global``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from realgrowth_ml.config import SEED
from realgrowth_ml.features import CATEGORICAL, FEATURE_NAMES, INFLATION_ONLY


class Forecaster(Protocol):
    def fit(self, frame: pd.DataFrame, target: pd.Series) -> Forecaster: ...

    def predict(self, frame: pd.DataFrame) -> np.ndarray: ...


class Naive:
    def fit(self, frame: pd.DataFrame, target: pd.Series) -> Naive:
        return self

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        return frame["infl_lag0"].to_numpy(dtype=float)


class Mean3:
    def fit(self, frame: pd.DataFrame, target: pd.Series) -> Mean3:
        return self

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        lags = frame[["infl_lag0", "infl_lag1", "infl_lag2"]].to_numpy(dtype=float)
        return np.nanmean(lags, axis=1)  # lag0 is never NaN, so never all-NaN


@dataclass
class PooledAR:
    """Ridge on lags; falls back to the naive forecast where a lag is missing."""

    alpha: float = 1.0
    columns: tuple[str, ...] = ("infl_lag0", "infl_lag1", "infl_lag2", "global_infl_median")
    _model: Ridge | None = None
    _means: np.ndarray | None = None

    def fit(self, frame: pd.DataFrame, target: pd.Series) -> PooledAR:
        x = frame[list(self.columns)]
        ok = x.notna().all(axis=1) & target.notna()
        self._means = x[ok].to_numpy().mean(axis=0)
        self._model = Ridge(alpha=self.alpha).fit(x[ok].to_numpy(), target[ok].to_numpy())
        return self

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        assert self._model is not None, "fit() first"
        x = frame[list(self.columns)]
        ok = x.notna().all(axis=1).to_numpy()
        out = frame["infl_lag0"].to_numpy(dtype=float).copy()
        if ok.any():
            out[ok] = self._model.predict(x[ok].to_numpy())
        return out

    def contributions(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Exact SHAP values for a linear model: ``coef * (x - E[x])``.

        ``bias`` is the prediction at the training mean. Rows that fall back to
        the naive forecast attribute everything to ``infl_lag0``.
        """
        assert self._model is not None and self._means is not None, "fit() first"
        x = frame[list(self.columns)].to_numpy(dtype=float)
        coef = np.asarray(self._model.coef_)
        values = coef * (x - self._means)
        bias = float(self._model.intercept_ + coef @ self._means)
        out = pd.DataFrame(values, columns=list(self.columns), index=frame.index)
        out["bias"] = bias
        fallback = ~np.isfinite(x).all(axis=1)
        if fallback.any():
            out.loc[fallback, :] = 0.0
            out.loc[fallback, "infl_lag0"] = frame.loc[fallback, "infl_lag0"].to_numpy()
        return out

    @property
    def coefficients(self) -> dict[str, float]:
        assert self._model is not None
        coefs = dict(zip(self.columns, map(float, self._model.coef_), strict=True))
        return coefs | {"intercept": float(self._model.intercept_)}


DEFAULT_LGBM_PARAMS: dict[str, Any] = {
    "objective": "regression",
    "learning_rate": 0.03,
    "n_estimators": 400,
    "num_leaves": 15,
    "min_child_samples": 40,
    "subsample": 0.8,
    "subsample_freq": 1,
    "colsample_bytree": 0.8,
    "reg_lambda": 1.0,
    "random_state": SEED,
    "deterministic": True,
    "force_row_wise": True,
    "n_jobs": 4,
    "verbose": -1,
}

#: Grid searched on the validation window only (see config.VALIDATION_ORIGINS).
LGBM_GRID: tuple[dict[str, Any], ...] = tuple(
    {"num_leaves": leaves, "min_child_samples": child, "n_estimators": trees}
    for leaves in (7, 15, 31)
    for child in (20, 60)
    for trees in (300, 600)
)


@dataclass
class LightGBMForecaster:
    columns: Sequence[str] = FEATURE_NAMES
    params: dict[str, Any] = field(default_factory=dict)
    _model: lgb.LGBMRegressor | None = None

    def _x(self, frame: pd.DataFrame) -> pd.DataFrame:
        x = frame[list(self.columns)].astype(float)
        for column in CATEGORICAL:
            if column in x:
                x[column] = x[column].astype("category")
        return x

    def fit(self, frame: pd.DataFrame, target: pd.Series) -> LightGBMForecaster:
        ok = target.notna().to_numpy()
        self._model = lgb.LGBMRegressor(**(DEFAULT_LGBM_PARAMS | self.params))
        self._model.fit(self._x(frame[ok]), target[ok].to_numpy())
        return self

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        assert self._model is not None, "fit() first"
        return np.asarray(self._model.predict(self._x(frame)), dtype=float)

    def contributions(self, frame: pd.DataFrame) -> pd.DataFrame:
        """TreeSHAP attributions on the slog scale; columns = features + bias.

        LightGBM computes exact TreeSHAP natively (``pred_contrib=True``); each
        row's contributions sum to its prediction.
        """
        assert self._model is not None, "fit() first"
        values = self._model.predict(self._x(frame), pred_contrib=True)
        return pd.DataFrame(np.asarray(values), columns=[*self.columns, "bias"], index=frame.index)


@dataclass
class Ensemble:
    """Equal-weight average of the pooled AR and the global LightGBM model.

    Equal weights rather than fitted ones on purpose: estimated combination
    weights are noisy and routinely lose to the simple average out of sample
    (the "forecast combination puzzle", Stock & Watson 2004). Because SHAP
    values are linear in the model, the ensemble's attributions are the average
    of its members'.
    """

    params: dict[str, Any] = field(default_factory=dict)
    _members: list[PooledAR | LightGBMForecaster] = field(default_factory=list)

    def fit(self, frame: pd.DataFrame, target: pd.Series) -> Ensemble:
        self._members = [
            PooledAR().fit(frame, target),
            LightGBMForecaster(columns=FEATURE_NAMES, params=self.params).fit(frame, target),
        ]
        return self

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        assert self._members, "fit() first"
        return np.mean([m.predict(frame) for m in self._members], axis=0)

    def contributions(self, frame: pd.DataFrame) -> pd.DataFrame:
        parts = [m.contributions(frame) for m in self._members]
        columns = [*FEATURE_NAMES, "bias"]
        aligned = [p.reindex(columns=columns, fill_value=0.0) for p in parts]
        return sum(aligned[1:], aligned[0]) / len(aligned)


@dataclass(frozen=True)
class ModelSpec:
    id: str
    name: str
    kind: str  # "ml" | "baseline"
    description: str
    factory: Callable[[dict[str, Any]], Forecaster]
    tunable: bool = False
    #: Reuse another model's tuned hyperparameters instead of searching again.
    params_from: str | None = None


MODEL_SPECS: tuple[ModelSpec, ...] = (
    ModelSpec(
        "naive",
        "Naive (random walk)",
        "baseline",
        "Inflation h years ahead equals inflation in the latest year.",
        lambda _: Naive(),
    ),
    ModelSpec(
        "mean3",
        "Three-year mean",
        "baseline",
        "Mean of (signed-log) inflation over the latest three years.",
        lambda _: Mean3(),
    ),
    ModelSpec(
        "pooled_ar",
        "Pooled AR(3) ridge",
        "baseline",
        "Linear regression on three inflation lags and the global median, pooled across "
        "countries; the classical econometric benchmark.",
        lambda _: PooledAR(),
    ),
    ModelSpec(
        "lgbm_infl_only",
        "LightGBM (inflation history only)",
        "ml",
        "Gradient-boosted trees on inflation-history and global features only. An "
        "ablation that isolates the value of the macro-financial features.",
        lambda params: LightGBMForecaster(columns=INFLATION_ONLY, params=params),
        tunable=True,
    ),
    ModelSpec(
        "lgbm_global",
        "LightGBM global panel model",
        "ml",
        "One gradient-boosted tree model for all countries on inflation history, money "
        "growth, exchange-rate depreciation, output, labour, fiscal and structural features.",
        lambda params: LightGBMForecaster(columns=FEATURE_NAMES, params=params),
        tunable=True,
    ),
    ModelSpec(
        "ensemble",
        "Ensemble (pooled AR + LightGBM)",
        "ml",
        "Equal-weight average of the pooled AR(3) and the global LightGBM model, "
        "combining a stable linear forecast with a non-linear one that uses macro drivers.",
        lambda params: Ensemble(params=params),
        params_from="lgbm_global",
    ),
)


def spec(model_id: str) -> ModelSpec:
    for candidate in MODEL_SPECS:
        if candidate.id == model_id:
            return candidate
    raise KeyError(model_id)
