# Imputation forensics: finding invented data

Code: `ml/src/realgrowth_ml/anomaly.py` · Analysis:
`notebooks/analysis/03_imputation_forensics.ipynb` · Served: `/api/v1/anomalies`,
the Models & Methodology page, and used by the ETL.

## The problem

The original project's `cleaning.ipynb` filled missing cells in wages,
inflation, debt and diet cost with:

```python
world_avg = df[year_cols].mean()                 # cross-country mean per year
mean_ratio = (row[available] / world_avg[available]).mean()
row[missing_year] = world_avg[missing_year] * mean_ratio
```

It kept no record of which cells were filled, so invented values looked like
data. The ETL's hand-written rule (reject a >40% wage move that inflation does
not explain) catches some of them, but nobody knew how many it missed.

Inflation, debt and diet cost are now re-sourced from the publishers' APIs, so
only the wage panel still carries imputed values.

## Recovering exact labels

The formula leaves an algebraic fingerprint. Every filled cell of country *c*
in year *y* equals `r_c · w_y`. So for any two filled years *a*, *b* of the same
country, `v_b / v_a = w_b / w_a`, **the same ratio for every country**. In the
real panel, 42 countries share the 2021→2022 wage growth ratio 1.789205 to six
decimal places.

`reconstruct_labels`:

1. For every pair of years, finds a growth ratio shared by ≥3 countries to
   1e-6 and marks the cells involved. Pairs, not only consecutive years, so
   isolated filled cells are caught too.
2. Solves for `log w` by least squares over all pairwise links, anchored at the
   first year. A weak prior from genuine-cell means covers years no link
   reaches.
3. Computes each country's `r_c` from its genuine cells and marks every cell on
   `r_c · w_y` to 1e-6. Steps 2-3 repeat until the labels stop changing (2
   iterations here).

The ETL multiplies USD wages back by the exchange rate first, which removes
the currency conversion the notebook applied after imputing.

**Validation.** `ml/tests/test_anomaly.py` re-implements the notebook's
function, applies it to simulated wage panels, and checks that reconstruction
recovers exactly the filled cells (0 false positives, 0 false negatives) and
the world index. It also confirms that a clean panel gets no labels.

**Result.** 514 of 2,032 wage cells (25.3%) are imputed, in 111 of 121
countries. By year it rises from about 20% to **89% in 2022** (104 of 117). The
latest year, where data is scarcest, is where the original project's headline
chart came from.

## Detectors

The labels turn an unsupervised problem into a supervised one with exact
ground truth. That makes it possible to measure how well detectors that **do
not know the formula** would find invented cells, which is what matters for
other datasets with undocumented imputation.

Features per cell (none use the fingerprint): log growth in and out,
inflation-adjusted excess growth, per-country robust z-scores, deviation from
the year's cross-country median growth, deviation from a centred rolling
median level, inflation, and edge and neighbour indicators.

Supervised scores are **out-of-fold with GroupKFold(5) by country**, so a
country is never scored by a model trained on it.

| Detector | PR-AUC | Precision* | Recall* | Precision @0.5 | Recall @0.5 |
|---|---|---|---|---|---|
| ETL rule (>40% unexplained move) | — | 0.60 | 0.32 | — | — |
| Robust z-score | 0.41 | 0.58 | 0.31 | — | — |
| Isolation Forest | 0.52 | 0.65 | 0.35 | — | — |
| LightGBM, own-country features only | 0.94 | 0.99 | 0.53 | 0.87 | 0.84 |
| **LightGBM, all features** | **0.97** | **1.00** | **0.54** | **0.93** | **0.88** |

\* Each detector flags as many cells as the rule does (277). Base rate is 0.25.

Judged at the level it operates on (transitions, not cells), the rule is
precise but blind. 94% of the transitions it rejects are contaminated, but it
rejects only 24% of the 558 contaminated transitions. Most imputed cells
produce small, plausible-looking moves.

## Findings

1. **Outlier detection is the wrong tool for imputation detection.** Imputed
   values are smooth and plausible, not extreme. Unsupervised methods do only
   modestly better than the base rate.
2. **The signal is cross-sectional.** Imputed cells move with the cross-country
   mean, which genuine wages rarely do. Removing those features costs 0.03
   PR-AUC; the model still finds them from own-country dynamics.
3. **Reverse-engineering how bad data was made beats guessing.** It produced
   exact labels, a validated detector, and a pipeline fix.

## What the pipeline does with it

* `etl/artifacts.load_imputation_labels` reads the exact labels, and
  `derive_nominal_wage_growth` refuses to compute a growth rate with an imputed
  endpoint (558 `imputed_input` issues). The affected 111 series are flagged in
  the API and UI.
* The plausibility rule remains as a fallback when labels are unavailable, and
  catches 9 further transitions where both endpoints are genuine but the move
  is still implausible.
* The detector's out-of-fold probabilities are served at `/api/v1/anomalies`.
