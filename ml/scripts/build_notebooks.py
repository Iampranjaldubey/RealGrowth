"""Build the analysis notebooks from cell sources, then execute them in place.

Kept as a script so notebook source is reviewable as plain Python and the
executed .ipynb files are reproducible: `python ml/scripts/build_notebooks.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notebooks" / "analysis"

SETUP = r'''
import sys, json, sqlite3
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from IPython.display import Image, display

ROOT = next(p for p in Path.cwd().resolve().parents if (p / "ml" / "src").is_dir())
sys.path.insert(0, str(ROOT / "ml" / "src"))
DB = ROOT / "data" / "realgrowth.db"
MODELS = ROOT / "data" / "models"
FIG = ROOT / "docs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.3, "font.size": 10})
pd.set_option("display.precision", 3)
pd.set_option("display.width", 120)

def save(fig, name):
    path = FIG / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", dpi=130)
    plt.close(fig)
    display(Image(filename=str(path)))
'''


def md(text: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_markdown_cell(text.strip())


def code(text: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_code_cell(text.strip())


# --------------------------------------------------------------------- 01 EDA

EDA = [
    md("""
# 01 · Exploratory data analysis

**Question.** What does the data actually cover, how does inflation behave across
countries and time, and what does that imply for modelling?

**Data.** The SQLite warehouse built by `python -m realgrowth.etl` from the
committed API snapshot (`data/raw/api/`, World Bank WDI, IMF WEO, Our World in
Data) plus the legacy ILOSTAT wage extract. Nothing in this notebook re-reads
raw files; it analyses exactly what the API serves.
"""),
    code(SETUP),
    code("""
from realgrowth_ml.data import load_panel
panel = load_panel(DB)
obs = panel.observations
countries = panel.countries
print(f"{len(obs):,} observations · {obs.indicator_id.nunique()} indicators · "
      f"{(~countries.is_aggregate).sum()} countries · built {panel.built_at}")
"""),
    md("""
## 1. Coverage

Density is the share of the 217 countries with a value in each year. Two things
stand out: macro series are dense from the 1990s on, and inequality/poverty
surveys are sparse by nature (they are run every few years). The wage panel is
the thinnest series and stops in 2022.
"""),
    code("""
real = obs[obs.iso3.isin(countries.index[~countries.is_aggregate])]
n_countries = (~countries.is_aggregate).sum()
order = ["inflation_rate", "gdp_growth", "gdp_per_capita_ppp", "exchange_rate", "broad_money_growth",
         "unemployment_rate", "debt_to_gdp", "current_account", "real_interest_rate",
         "healthy_diet_cost", "gini_index", "poverty_rate", "avg_wage", "real_wage_growth"]
cov = (real[real.indicator_id.isin(order)].groupby(["indicator_id", "year"]).iso3.nunique()
       .unstack().reindex(order) / n_countries)
cov = cov.loc[:, 1970:]
fig, ax = plt.subplots(figsize=(11, 4.8))
im = ax.imshow(cov.fillna(0).to_numpy(), aspect="auto", cmap="viridis", vmin=0, vmax=1)
ax.set_yticks(range(len(cov)), cov.index)
ticks = list(range(0, cov.shape[1], 5))
ax.set_xticks(ticks, [cov.columns[i] for i in ticks])
ax.grid(False)
fig.colorbar(im, ax=ax, label="share of countries with data")
ax.set_title("Coverage by indicator and year")
save(fig, "eda_coverage")
"""),
    md("""
## 2. The distribution of inflation is extremely heavy-tailed

Annual CPI inflation ranges from deflation to tens of thousands of percent. A
model trained on raw percentages would spend its capacity on a handful of
hyperinflations. The signed-log transform `slog(x) = sign(x)·log(1+|x|)` is
near-linear for ordinary inflation, compresses the tail, and makes errors close
to *relative* errors. All forecasting models are trained and selected on this
scale.
"""),
    code("""
from realgrowth_ml.features import slog
infl = panel.wide("inflation_rate")
values = infl.stack().to_numpy()
print(pd.Series(values).describe(percentiles=[.01, .05, .5, .95, .99]).round(2).to_string())
fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
axes[0].hist(np.clip(values, -20, 100), bins=120, color="#06b6d4")
axes[0].set_title("Inflation, % (clipped to [-20, 100])")
axes[1].hist(slog(values), bins=120, color="#8b5cf6")
axes[1].set_title("Inflation on the signed-log scale")
save(fig, "eda_inflation_distribution")
"""),
    md("""
## 3. Inflation is persistent, but less than a random walk

The naive forecast "next year equals this year" is a famously hard benchmark.
The scatter of `slog(π_t)` against `slog(π_{t+1})` shows why: points hug the
diagonal. But the slope of a pooled regression is below 1, which says inflation
*mean-reverts*. That is the gap a learned model can exploit.
"""),
    code("""
s = slog(infl)
pairs = pd.DataFrame({"now": s.stack(), "next": s.shift(-1, axis=1).stack()}).dropna()
pairs = pairs[pairs.index.get_level_values(1) >= 1990]
slope, intercept = np.polyfit(pairs["now"], pairs["next"], 1)
r = np.corrcoef(pairs["now"], pairs["next"])[0, 1]
print(f"n={len(pairs):,}  slope={slope:.3f}  intercept={intercept:.3f}  r={r:.3f}")
fig, ax = plt.subplots(figsize=(5.5, 5))
ax.scatter(pairs["now"], pairs["next"], s=3, alpha=0.25, color="#06b6d4")
lim = np.array([-2, 8])
ax.plot(lim, lim, "k--", lw=1, label="random walk (slope 1)")
ax.plot(lim, intercept + slope * lim, color="#ef4444", lw=2, label=f"pooled fit (slope {slope:.2f})")
ax.set_xlabel("slog inflation, year t"); ax.set_ylabel("slog inflation, year t+1")
ax.legend(); ax.set_title("Persistence and mean reversion, 1990-")
save(fig, "eda_persistence")
"""),
    md("""
## 4. Inflation has a strong common global component

The cross-country median moves together: the 1970s oil shocks, the long
disinflation, and the 2021-23 surge are visible in almost every country at once.
This motivates the `global_infl_median` features and the *global* (pooled
across countries) model design, and it is also why forecast errors are
correlated within a year, which the significance tests account for.
"""),
    code("""
q = s.loc[:, 1970:].quantile([0.1, 0.5, 0.9]).T
from realgrowth_ml.features import inv_slog
qp = inv_slog(q)
fig, ax = plt.subplots(figsize=(10, 3.8))
ax.fill_between(qp.index, qp[0.1], qp[0.9], alpha=0.25, color="#8b5cf6", label="10th-90th percentile")
ax.plot(qp.index, qp[0.5], color="#8b5cf6", lw=2, label="median country")
ax.set_yscale("symlog", linthresh=10); ax.set_ylabel("inflation, % (symlog)")
ax.legend(loc="upper right"); ax.set_title("Cross-country distribution of inflation over time")
save(fig, "eda_global_inflation")
print("median country inflation by year (last 8):")
print(qp[0.5].tail(8).round(2).to_string())
"""),
    md("""
## 5. Which macro variables move with next year's inflation?

Spearman rank correlations with *next year's* slog inflation, pooled over
1990 onwards. Money growth, currency depreciation and the GDP deflator carry
signal beyond current inflation, which is what the full LightGBM model uses and
the inflation-only ablation does not.
"""),
    code("""
from realgrowth_ml.features import build_feature_frame, FEATURE_NAMES
frame = build_feature_frame(panel, [1])
frame = frame[frame.year >= 1990]
corr = (frame[list(FEATURE_NAMES)].corrwith(frame["target_h1"], method="spearman")
        .drop("region_code").sort_values())
coverage = frame[list(FEATURE_NAMES)].notna().mean().reindex(corr.index)
display(pd.DataFrame({"spearman_with_next_year": corr, "non_missing_share": coverage}).round(3))
fig, ax = plt.subplots(figsize=(7, 5))
ax.barh(corr.index, corr.values, color=["#ef4444" if v > 0 else "#10b981" for v in corr.values])
ax.set_title("Rank correlation with next year's inflation (slog)")
save(fig, "eda_feature_correlations")
"""),
    md("""
## 6. Real wages: why local currency matters

The original project computed real wage growth as **USD** wage growth minus
**domestic** inflation. That conflates a currency move with a pay cut. Below,
the same 2022 numbers computed both ways. In 2022 the dollar strengthened
sharply, so the USD-based method reported European and Japanese real wage
"collapses" that were mostly exchange-rate movements. The ETL now uses the
local-currency definition (the ILO/OECD convention).
"""),
    code("""
usd = panel.wide("avg_wage"); lcu = panel.wide("avg_wage_lcu")
real_lcu = panel.wide("real_wage_growth")
g_usd = (usd / usd.shift(1, axis=1) - 1) * 100
real_usd = g_usd - infl.reindex(index=g_usd.index, columns=g_usd.columns)
g7 = ["USA", "GBR", "DEU", "ITA", "JPN", "CAN"]
cmp = pd.DataFrame({"USD-based (old)": real_usd.reindex(g7)[2022],
                    "local currency (new)": real_lcu.reindex(g7)[2022]}).round(1)
display(cmp)
fig, ax = plt.subplots(figsize=(8, 3.6))
cmp.plot.bar(ax=ax, color=["#94a3b8", "#06b6d4"]); ax.axhline(0, color="k", lw=0.8)
ax.set_ylabel("real wage growth 2022, %"); ax.set_title("Same wages, two definitions")
plt.xticks(rotation=0)
save(fig, "eda_real_wage_definitions")
"""),
    md("""
## Takeaways for modelling

1. Model on the signed-log scale; report errors in percentage points *and* on the log scale.
2. The naive forecast is strong; any model must be judged against it out of sample.
3. Inflation mean-reverts and shares a global cycle, so pooled models with global features are justified.
4. Errors will be correlated within years; significance tests must use years, not country-years, as the unit.
5. Macro features add signal but have gaps; tree models handle missing values natively.
"""),
]

# --------------------------------------------------------------- 02 forecasting

FORECAST = [
    md("""
# 02 · Forecasting national inflation

**Question.** Can a model forecast next year's (and the year after's) CPI
inflation for ~190 countries better than the naive benchmark, and can it say
how uncertain it is?

This notebook analyses the artefacts written by `python -m realgrowth_ml train`
(`data/models/inflation/`) rather than retraining, so every number here is the
number the website serves. See `docs/MODELING.md` for the design rationale.

**Protocol.** Rolling-origin backtest: for every origin year a fresh model is
trained only on rows whose *target* year was already observed. Hyperparameters
and the champion are chosen on forecasts made in 2001-2008 (validation); forecasts
made from 2009 onwards (test) are reported once and never used for selection.
"""),
    code(SETUP),
    code("""
card = json.loads((MODELS / "inflation" / "model_card.json").read_text())
backtest = pd.read_csv(MODELS / "inflation" / "backtest.csv")
forecasts = pd.read_csv(MODELS / "inflation" / "forecasts.csv")
names = {m["id"]: m["name"] for m in card["models"]}
print("champion:", names[card["champion"]])
print("design:", json.dumps({k: card["design"][k] for k in ["backtest", "selection_rule", "intervals"]}, indent=1))
print(f"{len(backtest):,} out-of-sample forecasts; tuned params: {card['models'][4]['card']['params']}")
"""),
    md("""
## 1. Leaderboard on the held-out test window

Scored on a common sample (every model forecast every cell). `skill` is the
reduction in log-scale MAE versus naive. Two baselines matter: naive (random
walk) and the pooled AR(3), the classical econometric benchmark.
"""),
    code("""
m = pd.DataFrame(card["metrics"])
cols = ["n", "mae", "median_ae", "rmse", "mae_log", "skill_vs_naive", "coverage_80", "coverage_95", "median_width_80"]
for h in card["design"]["horizons"]:
    t = m[(m.window == "test") & (m.horizon == h)].set_index("model_id")[cols].sort_values("mae_log")
    t.index = [names.get(i, i) for i in t.index]
    print(f"\\n=== {h} year(s) ahead, test window ===")
    display(t.round(3))
"""),
    md("""
**Reading the table.** The mean error in percentage points is dominated by a few
high-inflation country-years (RMSE ≫ MAE); the median error is the typical miss.
The ensemble has the lowest MAE, median error and log-scale MAE at both
horizons. RMSE, which is driven almost entirely by hyperinflation episodes, is
effectively tied across the stronger models (naive is marginally lowest at h=1).
The advantage over naive grows with the horizon, as expected: persistence decays
and mean reversion matters more two years out.
"""),
    md("""
## 2. Is the improvement real? Diebold-Mariano tests

Errors are strongly correlated within a year (2022 surprised everyone), so the
loss differential is averaged per target year before testing; the unit of
evidence is ~15 years, not ~3,000 country-years. Newey-West variance with
`h-1` lags and the Harvey-Leybourne-Newbold small-sample correction.
"""),
    code("""
dm = pd.DataFrame(card["significance"])
dm["versus"] = dm["versus"].map(names)
display(dm.round(3))
"""),
    md("""
The champion beats the naive forecast significantly at both horizons
(p ≈ 0.02), the three-year mean at one year (p = 0.001), and the inflation-only
LightGBM at two years (p = 0.03). Against the pooled AR and the full LightGBM
model the gains are consistent in sign but not significant with only ~15 test
years. That is an honest result worth stating: the ensemble's main value over
its members is robustness, not a large accuracy jump.
"""),
    md("""
## 3. Error over time

Median absolute error by target year. The 2021-23 inflation surge is a regime
change; every model (and, as widely documented, every central bank) under-predicted
it. The model recovers faster than naive once the surge is in the data.
"""),
    code("""
ye = pd.DataFrame(card["yearly_errors"])
fig, axes = plt.subplots(1, 2, figsize=(12, 3.8), sharey=True)
for ax, h in zip(axes, [1, 2]):
    for mid, color in [(card["champion"], "#8b5cf6"), ("naive", "#94a3b8"), ("pooled_ar", "#10b981")]:
        d = ye[(ye.model_id == mid) & (ye.horizon == h) & (ye.target_year >= 2000)]
        ax.plot(d.target_year, d.median_ae, marker="o", ms=3, color=color, label=names[mid])
    ax.axvline(card["design"]["first_test_origin"] + h - 0.5, color="k", ls=":", lw=1)
    ax.set_title(f"{h} year(s) ahead"); ax.set_xlabel("target year")
axes[0].set_ylabel("median |error|, pp"); axes[0].legend()
fig.suptitle("Out-of-sample error by year (dotted line: start of test window)")
save(fig, "forecast_error_by_year")
"""),
    md("""
## 4. Are the prediction intervals honest?

Intervals come from Mondrian split-conformal prediction: absolute log-scale
errors from the previous 10 observed years, calibrated separately by inflation
regime. A well-calibrated 80% interval should contain the outcome ~80% of the
time. Coverage by target year shows how the rolling window adapts after 2021.
"""),
    code("""
champ = backtest[(backtest.model_id == card["champion"]) & backtest.lower_80.notna()].copy()
champ["inside"] = (champ.actual >= champ.lower_80) & (champ.actual <= champ.upper_80)
test = champ[champ.origin_year >= card["design"]["first_test_origin"]]
by_year = test.groupby(["horizon", "target_year"]).inside.mean().unstack(0)
print("overall test coverage (80% nominal):", test.groupby("horizon").inside.mean().round(3).to_dict())
fig, ax = plt.subplots(figsize=(10, 3.4))
for h, color in [(1, "#8b5cf6"), (2, "#06b6d4")]:
    ax.plot(by_year.index, by_year[h], marker="o", ms=3, color=color, label=f"h={h}")
ax.axhline(0.8, color="k", ls="--", lw=1, label="nominal 80%")
ax.set_ylim(0.2, 1.0); ax.set_ylabel("empirical coverage"); ax.legend()
ax.set_title("80% interval coverage by target year (test window)")
save(fig, "forecast_coverage_by_year")
display(pd.DataFrame(card["regimes"]).round(3))
"""),
    md("""
Coverage is close to nominal over the whole test window (79% and 78% for the
80% interval) and within a few points of it in each inflation regime, which is
what Mondrian calibration is for: one pooled interval would be too wide for
Switzerland and too narrow for Argentina.

Year by year it is a different story, and the chart is the honest view.
Conformal prediction guarantees *average* coverage under exchangeability, not
coverage in every year. When the world changes faster than a 10-year
calibration window, coverage drops: in 2015 (oil-price collapse and deflation)
and above all in 2022, when only 43% (h=1) and 28% (h=2) of outcomes fell inside
the 80% interval. It then recovers to ~90% by 2024-25 as the surge enters the
calibration set. This is the expected failure mode of any method that assumes
the near future resembles the recent past, and it is listed in the model card.
"""),
    md("""
## 5. What drives the forecasts?

Mean absolute TreeSHAP value per feature across current forecasts (the
ensemble's attributions are the average of its members': exact SHAP for the
linear model, TreeSHAP for LightGBM).
"""),
    code("""
imp = pd.DataFrame(card["global_importance"]).set_index("feature")["mean_abs_shap"].head(12)[::-1]
fig, ax = plt.subplots(figsize=(7, 4.5))
ax.barh(imp.index, imp.values, color="#8b5cf6"); ax.set_xlabel("mean |SHAP| (slog scale)")
ax.set_title("Global feature importance, current forecasts")
save(fig, "forecast_feature_importance")
"""),
    md("""
Current inflation dominates, as the EDA predicted; history (5-year mean, lags),
the global cycle and then money growth, depreciation and the deflator follow.
The inflation-only ablation in the leaderboard quantifies what the macro
features add on top.
"""),
    md("""
## 6. Current forecasts against the IMF

The IMF's World Economic Outlook is produced by country economists with far
richer information (monthly data, policy plans). Historical WEO vintages are not
scriptably downloadable, so this is a side-by-side comparison of *current*
forecasts, not a backtest.
"""),
    code("""
imf = pd.read_csv(ROOT / "data" / "raw" / "api" / "imf_inflation_forecast.csv")
ours = forecasts[forecasts.horizon == 1][["iso3", "target_year", "point", "lower_80", "upper_80"]]
both = ours.merge(imf, left_on=["iso3", "target_year"], right_on=["iso3", "year"])
both = both[both.point.abs() < 60]
inside = ((both.value >= both.lower_80) & (both.value <= both.upper_80)).mean()
print(f"{len(both)} countries · rank corr {both.point.corr(both.value, method='spearman'):.2f} · "
      f"median |ours - IMF| {np.median(np.abs(both.point - both.value)):.2f}pp · "
      f"IMF inside our 80% interval: {inside:.0%}")
fig, ax = plt.subplots(figsize=(5.5, 5))
ax.scatter(both.value, both.point, s=12, alpha=0.7, color="#8b5cf6")
lim = [min(both.value.min(), both.point.min()) - 1, max(both.value.max(), both.point.max()) + 1]
ax.plot(lim, lim, "k--", lw=1); ax.set_xlabel("IMF WEO projection, %"); ax.set_ylabel("our forecast, %")
ax.set_title(f"Next-year inflation: ours vs IMF ({int(both.target_year.mode()[0])})")
save(fig, "forecast_vs_imf")
"""),
    md("""
## 7. Example: fan charts

History plus forecast with 80% and 95% intervals and the IMF projection.
"""),
    code("""
infl = pd.read_sql("SELECT iso3, year, value FROM observations WHERE indicator_id='inflation_rate'",
                   sqlite3.connect(DB)).pivot(index="iso3", columns="year", values="value")
fig, axes = plt.subplots(1, 3, figsize=(14, 3.6))
for ax, iso3 in zip(axes, ["USA", "IND", "TUR"]):
    h = infl.loc[iso3].dropna().loc[2005:]
    f = forecasts[forecasts.iso3 == iso3].sort_values("target_year")
    x = [h.index[-1], *f.target_year]
    ax.plot(h.index, h.values, color="#06b6d4", lw=2, label="observed")
    ax.fill_between(x, [h.iloc[-1], *f.lower_95], [h.iloc[-1], *f.upper_95], color="#8b5cf6", alpha=0.12, label="95%")
    ax.fill_between(x, [h.iloc[-1], *f.lower_80], [h.iloc[-1], *f.upper_80], color="#8b5cf6", alpha=0.3, label="80%")
    ax.plot(x, [h.iloc[-1], *f.point], color="#8b5cf6", ls="--", marker="o", ms=3, label="forecast")
    i = imf[imf.iso3 == iso3]
    ax.scatter(i.year, i.value, marker="D", color="#f59e0b", zorder=3, label="IMF")
    ax.set_title(iso3); ax.set_xlim(2005, x[-1] + 1)
    # Cap the axis at the 80% band so a wide 95% band does not flatten the history.
    ax.set_ylim(top=max(h.max(), f.upper_80.max(), i.value.max() if len(i) else 0) * 1.25)
axes[0].legend(fontsize=8)
save(fig, "forecast_fan_charts")
"""),
    md("""
## 8. Error analysis: the biggest misses

Where does the champion fail worst (test window, 1 year ahead)?
"""),
    code("""
c = backtest[(backtest.model_id == card["champion"]) & (backtest.horizon == 1) &
             (backtest.origin_year >= card["design"]["first_test_origin"])].copy()
c["error"] = c.actual - c.point
display(c.reindex(c.error.abs().sort_values(ascending=False).index).head(12)
        [["iso3", "origin_year", "target_year", "point", "actual", "error"]].round(1))
print("share of test forecasts that under-predicted:", round((c.error > 0).mean(), 3))
"""),
    md("""
The largest misses are currency crises and hyperinflation onsets (Zimbabwe,
South Sudan, Sudan, Venezuela, Lebanon, Argentina): events driven by policy and
balance-of-payments shocks that annual macro aggregates do not anticipate. The
model card lists this as the main limitation; the high-inflation regime is also
where its intervals are widest by design.

## Conclusions

* A pooled ensemble of a linear AR model and a global LightGBM model beats the
  naive benchmark by ~11% (1 year) and ~17% (2 years) on log-scale MAE out of
  sample, significant at 5% by Diebold-Mariano on per-year losses.
* Mondrian conformal intervals achieve near-nominal coverage on average and per
  inflation regime, but not in every year: coverage collapsed during the 2022
  surge before recovering.
* Forecasts rank countries similarly to the IMF (Spearman ≈ 0.78), and the IMF
  projection falls inside our 80% interval for most countries.
* The main failure mode is crisis onset, which no annual-data model can foresee.
"""),
]

# ---------------------------------------------------------------- 03 anomaly

ANOMALY = [
    md("""
# 03 · Imputation forensics: finding invented data

**Question.** The wage dataset this project inherited was gap-filled by an
undocumented heuristic. Which cells are real, which are invented, and how well
can a detector find invented cells without being told the formula?

**Why it matters.** Real wage growth is the project's headline indicator. A
growth rate with an invented endpoint is fiction presented as a measurement.
"""),
    code(SETUP),
    md("""
## 1. The imputation formula

From `notebooks/cleaning.ipynb` (the original project), applied to wages, inflation,
debt and diet cost:

```python
world_avg = df[year_cols].mean()                       # cross-country mean per year
def fill_missing_with_ratio(row):
    ratios = row[available] / world_avg[available]
    mean_ratio = ratios.mean()
    row[year] = world_avg[year] * mean_ratio            # for every missing year
```

So every filled cell of country *c* in year *y* equals `r_c · w_y`. That leaves an
algebraic fingerprint: for any two filled years *a*, *b* of the same country,
`v_b / v_a = w_b / w_a`, **the same ratio for every country**. Wages were then
converted to USD; multiplying back by the same exchange rate (as the ETL does)
recovers the fingerprint exactly.
"""),
    code("""
from realgrowth_ml.data import load_panel
from realgrowth_ml import anomaly
panel = load_panel(DB)
levels = panel.wide("avg_wage_lcu")
ratio = (levels[2022] / levels[2021]).round(6)
counts = ratio.value_counts()
print("Most common 2021->2022 wage growth ratios across countries:")
display(counts.head(5).rename("countries").to_frame())
print(f"{counts.iloc[0]} countries share the ratio {counts.index[0]} to 6 decimal places.")
print("Genuine wage data would essentially never do that.")
"""),
    md("""
## 2. Reconstructing the labels

`anomaly.reconstruct_labels` (1) finds every pair of years where ≥3 countries
share a growth ratio to 1e-6, (2) solves for the world index `w` by least squares
over all those pairwise links, then (3) marks every cell that sits on `r_c · w_y`
to 1e-6, iterating until stable. The method is validated on a simulation of the
notebook's exact algorithm, where it recovers the filled cells with zero errors
(`ml/tests/test_anomaly.py`).
"""),
    code("""
labels = anomaly.reconstruct_labels(levels)
d = labels.diagnostics
print(f"{d['imputed_cells']} of {d['observed_cells']} wage cells imputed ({d['imputed_share']:.1%}); "
      f"{d['countries_with_imputation']} of {d['countries']} countries affected; "
      f"{d['fingerprint_links']} pairwise links; converged in {d['iterations']} iterations")
by_year = pd.Series(d["imputed_by_year"]); total = levels.notna().sum()
fig, ax = plt.subplots(figsize=(10, 3.4))
ax.bar(by_year.index.astype(int), (by_year.values / total.values) * 100, color="#ef4444")
ax.set_ylabel("% of cells imputed"); ax.set_title("Share of wage observations that were invented, by year")
save(fig, "anomaly_imputed_by_year")
"""),
    md("""
**89% of 2022 wage values were invented.** The original project's headline chart
— real wage growth in the 2022 cost-of-living crisis — was mostly computed from
imputed numbers. The latest year is where data is scarcest, and where a
`world average × ratio` fill is most tempting.
"""),
    code("""
mat = labels.imputed.loc[levels.notna().any(axis=1)]
mat = mat.loc[mat.sum(axis=1).sort_values().index]
state = np.where(levels.loc[mat.index].isna(), 0, np.where(mat, 2, 1))
from matplotlib.colors import ListedColormap
fig, ax = plt.subplots(figsize=(10, 12))
ax.imshow(state, aspect="auto", cmap=ListedColormap(["#f1f5f9", "#06b6d4", "#ef4444"]), interpolation="none")
ax.set_yticks(range(len(mat)), mat.index, fontsize=5); ax.set_xticks(range(len(mat.columns)), mat.columns, rotation=90)
ax.grid(False); ax.set_title("Wage panel: genuine (blue), imputed (red), missing (grey)")
save(fig, "anomaly_panel_map")
"""),
    md("""
## 3. How good is the existing rule?

The ETL's rule rejects a wage move >40% that inflation ≥25% does not explain.
Judged at the level it operates (transitions), it is very **precise** but misses
most contaminated transitions, because most imputed cells produce small,
plausible-looking moves.
"""),
    code("""
inflation = panel.wide("inflation_rate")
t = anomaly.rule_transition_metrics(levels, inflation, labels.imputed)
print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in t.items()}, indent=1))
"""),
    md("""
## 4. Detectors compared

None of the detectors may use the fingerprint itself — the question is what a
*general-purpose* detector can recover, which matters for datasets where the
imputation formula is unknown. All supervised scores are **out-of-fold with
GroupKFold by country**, so a country is never scored by a model trained on it.

* **robust z-score** of inflation-adjusted growth (MAD-scaled, per country);
* **Isolation Forest**, unsupervised, on the detector features;
* **LightGBM, own-country features only** (ablation);
* **LightGBM, all features**, including cross-sectional deviation (how far a
  country's growth is from the year's cross-country median).
"""),
    code("""
acard = json.loads((MODELS / "anomaly" / "model_card.json").read_text())
rows = []
for name, det in acard["detectors"].items():
    rows.append({"detector": name, "PR-AUC": det["pr_auc"], "ROC-AUC": det["roc_auc"],
                 "precision@rule budget": det["at_rule_budget"]["precision"],
                 "recall@rule budget": det["at_rule_budget"]["recall"],
                 "precision@0.5": (det.get("at_0_5") or {}).get("precision"),
                 "recall@0.5": (det.get("at_0_5") or {}).get("recall")})
display(pd.DataFrame(rows).set_index("detector").round(3))
print(f"base rate (share of cells imputed): {acard['base_rate']:.3f}")
"""),
    code("""
from sklearn.metrics import precision_recall_curve
cells = pd.read_csv(MODELS / "anomaly" / "labelled_cells.csv")
fig, ax = plt.subplots(figsize=(6, 5))
for col, color, label in [("robust_z", "#94a3b8", "robust z"), ("isolation_forest", "#10b981", "Isolation Forest"),
                          ("lgbm", "#8b5cf6", "LightGBM (out-of-fold)")]:
    p, r, _ = precision_recall_curve(cells.label, cells[col])
    ax.plot(r, p, color=color, lw=2, label=label)
rule = acard["detectors"]["rule"]["at_rule_budget"]
ax.scatter([rule["recall"]], [rule["precision"]], color="#ef4444", zorder=3, s=60, label="ETL rule")
ax.axhline(acard["base_rate"], color="k", ls=":", lw=1, label="chance")
ax.set_xlabel("recall"); ax.set_ylabel("precision"); ax.legend(loc="lower left")
ax.set_title("Detecting imputed wage cells")
save(fig, "anomaly_pr_curves")
display(pd.DataFrame(acard["feature_importance_gain"]).head(8))
"""),
    md("""
**Findings.**

* Unsupervised methods do only modestly better than the 0.25 base rate
  (PR-AUC 0.41 and 0.52): imputed cells are not *outliers*, they are smooth,
  plausible values. Outlier detection is the wrong tool for imputation detection.
* A supervised detector finds them with PR-AUC ≈ 0.97, mostly through
  cross-sectional features: imputed cells move *with the cross-country mean*,
  which genuine wages rarely do. Without those features (ablation) it still
  reaches ≈ 0.94.
* The labels made supervision possible. This is the general lesson: when you
  can reverse-engineer how bad data was produced, you can turn an unsupervised
  problem into a supervised one with exact labels.

## 5. What the pipeline does with this

The ETL now loads the exact labels and **refuses to compute a growth rate with an
imputed endpoint** (`imputed_input` issues), and flags every affected series in
the API and UI. The plausibility rule remains as a fallback for anything the
labels cannot see. The ML detector's scores are served at `/api/v1/anomalies`
for transparency and as a tool for other datasets with the same problem.
"""),
    code("""
q = json.loads(sqlite3.connect(DB).execute("SELECT value FROM etl_metadata WHERE key='quality_report'").fetchone()[0])
cov = {c["indicator"]: c for c in q["coverage"]}
print("issue counts:", q["issue_counts"])
print("real wage growth now:", {k: cov["real_wage_growth"][k] for k in ["observations", "countries", "min_year", "max_year"]})
"""),
]


def build(name: str, cells: list[nbformat.NotebookNode]) -> Path:
    nb = nbformat.v4.new_notebook()
    nb.cells = cells
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    ExecutePreprocessor(timeout=600, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(OUT)}})
    nbformat.write(nb, path)
    return path


if __name__ == "__main__":
    targets = {
        "01_exploratory_analysis.ipynb": EDA,
        "02_inflation_forecasting.ipynb": FORECAST,
        "03_imputation_forensics.ipynb": ANOMALY,
    }
    wanted = set(sys.argv[1:]) or set(targets)
    for filename, cells in targets.items():
        if any(w in filename for w in wanted):
            print("built", build(filename, cells))
