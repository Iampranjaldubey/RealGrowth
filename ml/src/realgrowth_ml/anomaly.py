"""Detecting imputation artefacts in the wage panel.

**The problem.** The original project's notebook filled missing wage cells
with ``r_c * w_y`` — the cross-country mean wage in year ``y`` times country
``c``'s average ratio to that mean — and kept no record of which cells were
filled. Filled cells look like data. The ETL's hand-written rule (reject a
>40% move that inflation does not explain) catches some of them; nobody knew
how many it missed.

**Ground truth by forensic reconstruction.** The imputation leaves an exact
algebraic fingerprint, which turns an unlabelled problem into a supervised one:

1. Two consecutive filled years of any country grow by exactly
   ``w_y / w_{y-1}``, so in every year the same growth ratio appears in many
   countries to machine precision. That recovers ``w`` up to a constant.
2. Given ``w``, every filled cell of country ``c`` equals ``r_c * w_y`` where
   ``r_c`` is the mean of ``value / w`` over that country's genuine years —
   which identifies isolated filled cells too. Iterate to a fixed point.

Caveat recorded in the labels' diagnostics: a country with only one genuine
year has every cell on the formula, so its one genuine cell is labelled filled.

**Detectors compared** (``evaluate``), none of which may use the fingerprint
itself — the point is to learn what a *general* detector can recover:

* ``rule``             the ETL's current plausibility rule;
* ``robust_z``         robust z-score of inflation-adjusted growth (MAD);
* ``isolation_forest`` unsupervised, on the same features as the classifier;
* ``lgbm``             supervised gradient boosting, evaluated out-of-fold
                       with GroupKFold by country so it cannot memorise one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import GroupKFold

from realgrowth_ml.config import FINGERPRINT_MIN_SHARED, LEVEL_RTOL, RATIO_DECIMALS, SEED
from realgrowth_ml.data import Panel

TASK = "anomaly"
WAGE_LCU = "avg_wage_lcu"
SCORED_INDICATOR = "avg_wage"

#: Mirrors realgrowth.etl.derive (kept in sync by ml/tests/test_anomaly.py).
RULE_GROWTH_PCT = 40.0
RULE_INFLATION_PCT = 25.0


# ------------------------------------------------------------------ labels


@dataclass
class Labels:
    imputed: pd.DataFrame  # bool, iso3 x year, False where no observation
    world_index: pd.Series  # recovered w_y, normalised to the first year
    diagnostics: dict[str, Any]


def reconstruct_labels(
    levels: pd.DataFrame,
    *,
    min_shared: int = FINGERPRINT_MIN_SHARED,
    decimals: int = RATIO_DECIMALS,
    rtol: float = LEVEL_RTOL,
    max_iter: int = 20,
) -> Labels:
    """Recover which cells of ``levels`` (iso3 x year) were imputed."""
    observed = levels.notna()
    years = list(levels.columns)
    v = levels

    # 1. Pairwise fingerprint: for any two years (a, b), two filled cells of the
    #    same country satisfy v_b / v_a = w_b / w_a, whatever lies between them.
    in_shared = pd.DataFrame(False, index=v.index, columns=years)
    links: list[tuple[int, int, float]] = []
    for i, a in enumerate(years):
        for b in years[i + 1 :]:
            ratio = (v[b] / v[a]).round(decimals)
            counts = ratio.value_counts()
            if not len(counts) or counts.iloc[0] < min_shared:
                continue
            shared = float(counts.index[0])
            hit = ((v[b] / v[a]) / shared - 1.0).abs() < 10.0 ** (-decimals)
            in_shared[a] |= hit
            in_shared[b] |= hit
            links.append((a, b, float(np.log(shared))))

    def world_index(imputed: pd.DataFrame) -> pd.Series:
        """Least-squares ``log w`` from all pairwise links, anchored at the
        first year. Years no link reaches use the ratio of genuine-cell means,
        which is how the notebook defined ``w``."""
        position = {y: k for k, y in enumerate(years)}
        genuine_mean = np.log(v.where(~imputed).mean(axis=0))
        rows, rhs = [], []
        for a, b, log_ratio in links:
            row = np.zeros(len(years))
            row[position[b]], row[position[a]] = 1.0, -1.0
            rows.append(row)
            rhs.append(log_ratio)
        reached = {y for a, b, _ in links for y in (a, b)}
        for prev, year in zip(years, years[1:], strict=False):
            if year in reached and prev in reached:
                continue
            row = np.zeros(len(years))
            row[position[year]], row[position[prev]] = 1.0, -1.0
            rows.append(row * 1e-3)  # weak prior: only binds where links are absent
            rhs.append((genuine_mean[year] - genuine_mean[prev]) * 1e-3)
        anchor = np.zeros(len(years))
        anchor[0] = 1.0
        solution, *_ = np.linalg.lstsq(
            np.vstack([anchor, *rows]), np.array([0.0, *rhs]), rcond=None
        )
        return pd.Series(np.exp(solution), index=years)

    # 2. Level check: with w known, every filled cell equals r_c * w_y where
    #    r_c averages value / w over the country's genuine cells. Iterate.
    imputed = in_shared & observed
    index = world_index(imputed)
    iterations = 0
    for _ in range(max_iter):
        iterations += 1
        index = world_index(imputed)
        ratio = (v / index).where(~imputed).mean(axis=1)
        predicted = pd.DataFrame(np.outer(ratio, index), index=v.index, columns=years)
        on_formula = ((v - predicted).abs() / predicted.abs()) < rtol
        updated = (on_formula | in_shared) & observed
        if updated.equals(imputed):
            break
        imputed = updated

    single_genuine = int(((~imputed & observed).sum(axis=1) == 1).sum())
    labels = imputed
    diagnostics = {
        "observed_cells": int(observed.sum().sum()),
        "imputed_cells": int(labels.sum().sum()),
        "imputed_share": float(labels.sum().sum() / max(1, observed.sum().sum())),
        "countries": int(observed.any(axis=1).sum()),
        "countries_with_imputation": int(labels.any(axis=1).sum()),
        "fingerprint_links": len(links),
        "iterations": iterations,
        "countries_with_single_genuine_year": single_genuine,
        "imputed_by_year": {int(k): int(v) for k, v in labels.sum().items()},
    }
    return Labels(labels, index, diagnostics)


# ---------------------------------------------------------------- features

DETECTOR_FEATURES: tuple[str, ...] = (
    "log_growth_in",
    "log_growth_out",
    "excess_in",
    "excess_out",
    "abs_excess_max",
    "robust_z_in",
    "robust_z_out",
    "xs_dev_in",
    "xs_dev_out",
    "level_dev",
    "inflation_slog",
    "is_first_year",
    "is_last_year",
    "neighbours_observed",
)

#: Features that compare a country with other countries in the same year. They
#: are the strongest signal (filled cells move with the cross-country mean) and
#: the ablation ``lgbm_local`` measures what is left without them.
CROSS_SECTIONAL: tuple[str, ...] = ("xs_dev_in", "xs_dev_out")


def rule_transition_metrics(
    levels: pd.DataFrame, inflation: pd.DataFrame, imputed: pd.DataFrame
) -> dict[str, float | int]:
    """The rule judged on its own terms: transitions, not cells.

    A transition ``(y-1 -> y)`` is *contaminated* if either endpoint was
    imputed. Precision is the share of rejected transitions that were
    contaminated; recall is the share of contaminated transitions rejected.
    """
    infl = inflation.reindex(index=levels.index, columns=levels.columns)
    growth_pct = (levels / levels.shift(1, axis=1) - 1.0) * 100.0
    exists = growth_pct.notna()
    rejected = (growth_pct.abs() > RULE_GROWTH_PCT) & (
        infl.isna() | (infl.abs() < RULE_INFLATION_PCT)
    )
    rejected &= exists
    contaminated = (imputed | imputed.shift(1, axis=1, fill_value=False)) & exists
    tp = int((rejected & contaminated).sum().sum())
    n_rejected = int(rejected.sum().sum())
    n_contaminated = int(contaminated.sum().sum())
    return {
        "transitions": int(exists.sum().sum()),
        "rejected": n_rejected,
        "contaminated": n_contaminated,
        "precision": tp / n_rejected if n_rejected else float("nan"),
        "recall": tp / n_contaminated if n_contaminated else float("nan"),
    }


def _robust_z(frame: pd.DataFrame) -> pd.DataFrame:
    median = frame.median(axis=1)
    mad = frame.sub(median, axis=0).abs().median(axis=1) * 1.4826
    mad = mad.where(mad > 1e-6, 1e-6)
    return frame.sub(median, axis=0).div(mad, axis=0)


def cell_features(levels: pd.DataFrame, inflation: pd.DataFrame) -> pd.DataFrame:
    """One row per observed (iso3, year) with detector features."""
    infl = inflation.reindex(index=levels.index, columns=levels.columns)
    log_v = np.log(levels.where(levels > 0))
    g_in = log_v - log_v.shift(1, axis=1)
    g_out = g_in.shift(-1, axis=1)
    price = np.log1p(infl.clip(lower=-99.0) / 100.0)
    excess_in = g_in - price
    excess_out = excess_in.shift(-1, axis=1)
    z = _robust_z(excess_in)
    xs_in = g_in.sub(g_in.median(axis=0), axis=1).abs()
    rolling_median = log_v.T.rolling(5, center=True, min_periods=2).median().T
    present = levels.notna()
    first = present & ~present.shift(1, axis=1, fill_value=False)
    last = present & ~present.shift(-1, axis=1, fill_value=False)
    neighbours = present.shift(1, axis=1, fill_value=False).astype(int) + present.shift(
        -1, axis=1, fill_value=False
    ).astype(int)

    frames = {
        "log_growth_in": g_in,
        "log_growth_out": g_out,
        "excess_in": excess_in,
        "excess_out": excess_out,
        "abs_excess_max": np.maximum(excess_in.abs(), excess_out.abs()),
        "robust_z_in": z,
        "robust_z_out": z.shift(-1, axis=1),
        "xs_dev_in": xs_in,
        "xs_dev_out": xs_in.shift(-1, axis=1),
        "level_dev": (log_v - rolling_median).abs(),
        "inflation_slog": np.sign(infl) * np.log1p(infl.abs()),
        "is_first_year": first.astype(float),
        "is_last_year": last.astype(float),
        "neighbours_observed": neighbours.astype(float),
    }
    stacked = []
    for name, frame in frames.items():
        s = frame.where(present).stack(future_stack=True)
        s.index = s.index.set_names(["iso3", "year"])
        stacked.append(s.rename(name))
    out = pd.concat(stacked, axis=1)
    mask = present.stack(future_stack=True)
    mask.index = mask.index.set_names(["iso3", "year"])
    return out[mask.reindex(out.index).fillna(False).to_numpy()]


def rule_flags(levels: pd.DataFrame, inflation: pd.DataFrame) -> pd.Series:
    """Cells adjacent to a transition the ETL's rule rejects."""
    infl = inflation.reindex(index=levels.index, columns=levels.columns)
    growth_pct = (levels / levels.shift(1, axis=1) - 1.0) * 100.0
    large = growth_pct.abs() > RULE_GROWTH_PCT
    unexplained = infl.isna() | (infl.abs() < RULE_INFLATION_PCT)
    bad = large & unexplained & growth_pct.notna()
    cell = bad | bad.shift(-1, axis=1, fill_value=False)
    s = cell.where(levels.notna()).stack(future_stack=True).dropna().astype(bool)
    s.index = s.index.set_names(["iso3", "year"])
    return s.rename("rule")


# --------------------------------------------------------------- evaluation


def _at_budget(y: np.ndarray, score: np.ndarray, budget: int) -> dict[str, float]:
    """Precision/recall when flagging the ``budget`` highest-scoring cells."""
    order = np.argsort(-score, kind="stable")
    flagged = np.zeros_like(y, dtype=bool)
    flagged[order[:budget]] = True
    p, r, f, _ = precision_recall_fscore_support(y, flagged, average="binary", zero_division=0)
    return {"precision": float(p), "recall": float(r), "f1": float(f), "flagged": int(budget)}


def _binary(y: np.ndarray, flagged: np.ndarray) -> dict[str, float]:
    p, r, f, _ = precision_recall_fscore_support(y, flagged, average="binary", zero_division=0)
    return {
        "precision": float(p),
        "recall": float(r),
        "f1": float(f),
        "flagged": int(flagged.sum()),
    }


def lgbm_classifier() -> lgb.LGBMClassifier:
    return lgb.LGBMClassifier(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=15,
        min_child_samples=20,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        random_state=SEED,
        deterministic=True,
        force_row_wise=True,
        n_jobs=4,
        verbose=-1,
    )


def out_of_fold_scores(features: pd.DataFrame, y: np.ndarray, n_splits: int = 5) -> np.ndarray:
    """Out-of-fold P(imputed), grouped by country."""
    groups = features.index.get_level_values("iso3")
    oof = np.zeros(len(features))
    for train, test in GroupKFold(n_splits=n_splits).split(features, y, groups):
        model = lgbm_classifier().fit(features.iloc[train], y[train])
        oof[test] = model.predict_proba(features.iloc[test])[:, 1]
    return oof


@dataclass
class AnomalyResult:
    card: dict[str, Any]
    cells: pd.DataFrame  # iso3, year, label, rule, robust_z, isolation_forest, lgbm


def evaluate(panel: Panel) -> AnomalyResult:
    levels = panel.wide(WAGE_LCU)
    inflation = panel.wide("inflation_rate")
    labels = reconstruct_labels(levels)

    features = cell_features(levels, inflation)
    y_series = labels.imputed.stack(future_stack=True)
    y_series.index = y_series.index.set_names(["iso3", "year"])
    y = y_series.reindex(features.index).fillna(False).to_numpy(dtype=bool)

    rule = rule_flags(levels, inflation).reindex(features.index).fillna(False).to_numpy(bool)
    z_score = features[["robust_z_in", "robust_z_out"]].abs().max(axis=1).fillna(0.0).to_numpy()
    filled = features.fillna(features.median())
    forest = IsolationForest(n_estimators=300, random_state=SEED).fit(filled)
    forest_score = -forest.score_samples(filled)
    lgbm_score = out_of_fold_scores(features, y.astype(int))
    local_features = features.drop(columns=list(CROSS_SECTIONAL))
    lgbm_local_score = out_of_fold_scores(local_features, y.astype(int))

    budget = int(rule.sum())
    detectors: dict[str, dict[str, Any]] = {
        "rule": {
            "description": "ETL rule: >40% move not explained by >=25% inflation",
            "pr_auc": None,
            "roc_auc": None,
            "at_rule_budget": _binary(y, rule),
            "transition_level": rule_transition_metrics(levels, inflation, labels.imputed),
        }
    }
    for name, score, description in (
        ("robust_z", z_score, "max |robust z| of inflation-adjusted growth in/out"),
        ("isolation_forest", forest_score, "Isolation Forest on detector features"),
        (
            "lgbm_local",
            lgbm_local_score,
            "LightGBM, own-country features only (ablation: no cross-sectional features)",
        ),
        ("lgbm", lgbm_score, "LightGBM classifier, out-of-fold (GroupKFold by country)"),
    ):
        detectors[name] = {
            "description": description,
            "pr_auc": float(average_precision_score(y, score)),
            "roc_auc": float(roc_auc_score(y, score)),
            "at_rule_budget": _at_budget(y, score, budget),
            "at_0_5": _binary(y, score >= 0.5) if name.startswith("lgbm") else None,
        }

    # Fit on all cells only to *report* feature importances. Every metric above
    # and every served score comes from the out-of-fold models, not this one.
    final = lgbm_classifier().fit(features, y.astype(int))
    importance = sorted(
        zip(DETECTOR_FEATURES, map(int, final.booster_.feature_importance("gain")), strict=True),
        key=lambda kv: -kv[1],
    )

    cells = features.reset_index()[["iso3", "year"]].copy()
    cells["label"] = y
    cells["rule"] = rule
    cells["robust_z"] = z_score
    cells["isolation_forest"] = forest_score
    cells["lgbm"] = lgbm_score

    card = {
        "task": TASK,
        "indicator_id": SCORED_INDICATOR,
        "title": "Imputation-artefact detection in the average-wage panel",
        "trained_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "labels": labels.diagnostics,
        "base_rate": float(y.mean()),
        "cells": int(len(y)),
        "detectors": detectors,
        "served_detector": "lgbm",
        "served_threshold": 0.5,
        "feature_importance_gain": [{"feature": f, "gain": g} for f, g in importance],
        "features": list(DETECTOR_FEATURES),
        "world_index": {int(k): float(v) for k, v in labels.world_index.items()},
    }
    return AnomalyResult(card, cells)


def write_artifacts(result: AnomalyResult, models_dir: Path) -> Path:
    out = models_dir / TASK
    out.mkdir(parents=True, exist_ok=True)
    scores = pd.DataFrame(
        {
            "indicator_id": SCORED_INDICATOR,
            "iso3": result.cells["iso3"],
            "year": result.cells["year"],
            "score": result.cells["lgbm"].round(4),
            "is_flagged": (result.cells["lgbm"] >= 0.5).astype(int),
        }
    )
    scores.to_csv(out / "scores.csv", index=False)
    labelled = result.cells.copy()
    for column in ("robust_z", "isolation_forest", "lgbm"):
        labelled[column] = labelled[column].round(4)
    labelled.to_csv(out / "labelled_cells.csv", index=False)
    (out / "model_card.json").write_text(
        json.dumps(result.card, indent=2, default=float) + "\n", encoding="utf-8"
    )
    return out
