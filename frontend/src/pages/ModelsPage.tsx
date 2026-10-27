import { useState } from "react";
import { useAnomalyModelCard, useInflationModelCard } from "@/api/queries";
import { featureLabel, leaderboard } from "@/lib/forecast";
import type { AnomalyModelCard, InflationModelCard } from "@/types/api";

const pct = (value: number | null | undefined, digits = 1) =>
  value === null || value === undefined ? "—" : `${(value * 100).toFixed(digits)}%`;
const num = (value: number | null | undefined, digits = 2) =>
  value === null || value === undefined ? "—" : value.toFixed(digits);

/**
 * The model card, rendered: how the forecasts were made, how they were
 * evaluated, where they are weak, and the imputation-detection study.
 * Everything on this page is read from the model cards written by the
 * training run, so it cannot drift from the models actually served.
 */
export function ModelsPage() {
  const inflation = useInflationModelCard();
  const anomaly = useAnomalyModelCard();

  return (
    <div>
      <div className="page-header">
        <h1>Models & methodology</h1>
        <p>
          How the inflation forecasts and the data-quality detector were built and tested. Numbers
          on this page come straight from the model cards produced by the training pipeline.
        </p>
      </div>

      {inflation.isLoading && <p>Loading model card…</p>}
      {inflation.isError && <p role="alert">Could not load the forecasting model card.</p>}
      {inflation.data && <InflationSection card={inflation.data} />}

      {anomaly.data && <AnomalySection card={anomaly.data} />}
    </div>
  );
}

function InflationSection({ card }: { card: InflationModelCard }) {
  const [horizon, setHorizon] = useState(1);
  const names = Object.fromEntries(card.models.map((m) => [m.id, m.name]));
  const rows = leaderboard(card.metrics, horizon);
  const tests = card.significance.filter((s) => s.horizon === horizon);
  const regimes = card.regimes.filter((r) => r.horizon === horizon);

  return (
    <>
      <section className="glass-card" style={{ marginBottom: 24 }}>
        <h2 style={{ marginBottom: 8 }}>{card.title}</h2>
        <p style={{ marginBottom: 16 }}>{card.intended_use}</p>
        <dl className="definition-grid">
          <dt>Champion</dt>
          <dd>{names[card.champion] ?? card.champion}</dd>
          <dt>Training data</dt>
          <dd>
            {card.data.feature_rows.toLocaleString()} country-years, {card.data.countries} countries,{" "}
            {card.data.origin_years[0]}–{card.data.origin_years[1]}
          </dd>
          <dt>Evaluation</dt>
          <dd>{card.design.backtest}</dd>
          <dt>Model selection</dt>
          <dd>
            {card.design.selection_rule}, on forecasts made {card.design.validation_origins[0]}–
            {card.design.validation_origins[1]}. Forecasts from {card.design.first_test_origin} onwards
            are a held-out test set, reported once.
          </dd>
          <dt>Uncertainty</dt>
          <dd>{card.design.intervals}</dd>
          <dt>Target scale</dt>
          <dd>{card.design.target_transform}</dd>
        </dl>
      </section>

      <section className="glass-card" style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <h2>Held-out test results</h2>
          <div className="tab-bar" role="tablist" style={{ marginBottom: 0 }}>
            {card.design.horizons.map((h) => (
              <button
                key={h}
                type="button"
                role="tab"
                aria-selected={horizon === h}
                className={`tab-btn ${horizon === h ? "active" : ""}`}
                onClick={() => setHorizon(h)}
              >
                {h} year{h > 1 ? "s" : ""} ahead
              </button>
            ))}
          </div>
        </div>
        <div className="table-scroll">
          <table className="data-table">
            <caption className="sr-only">Test-window accuracy by model</caption>
            <thead>
              <tr>
                <th scope="col">Model</th>
                <th scope="col">MAE (pp)</th>
                <th scope="col">Median error (pp)</th>
                <th scope="col">Log-scale MAE</th>
                <th scope="col">Skill vs naive</th>
                <th scope="col">80% coverage</th>
                <th scope="col">95% coverage</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((m) => (
                <tr key={m.model_id} className={m.model_id === card.champion ? "is-highlighted" : ""}>
                  <th scope="row">{names[m.model_id] ?? m.model_id}</th>
                  <td>{num(m.mae)}</td>
                  <td>{num(m.median_ae)}</td>
                  <td>{num(m.mae_log, 3)}</td>
                  <td>{pct(m.skill_vs_naive)}</td>
                  <td>{pct(m.coverage_80)}</td>
                  <td>{pct(m.coverage_95)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p style={{ fontSize: "0.85rem", marginTop: 12 }}>
          n = {rows[0]?.n.toLocaleString()} forecasts. Skill is the reduction in log-scale error versus
          the naive "same as last year" forecast. Coverage is the share of actual outcomes that fell
          inside the stated interval; well-calibrated intervals sit near 80% and 95%.
        </p>
      </section>

      <div className="two-col-grid" style={{ marginBottom: 24 }}>
        <section className="glass-card">
          <h3 style={{ marginBottom: 8 }}>Is the champion really better?</h3>
          <p style={{ fontSize: "0.85rem", marginBottom: 12 }}>
            Diebold-Mariano tests on per-year mean loss (errors within a year are correlated, so
            years, not country-years, are the unit of evidence).
          </p>
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Versus</th>
                <th scope="col">DM statistic</th>
                <th scope="col">p-value</th>
              </tr>
            </thead>
            <tbody>
              {tests.map((t) => (
                <tr key={t.versus}>
                  <th scope="row">{names[t.versus] ?? t.versus}</th>
                  <td>{num(t.statistic)}</td>
                  <td className={t.p_value !== null && t.p_value < 0.05 ? "text-good" : ""}>{num(t.p_value, 3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="glass-card">
          <h3 style={{ marginBottom: 8 }}>Where the model is weaker</h3>
          <p style={{ fontSize: "0.85rem", marginBottom: 12 }}>
            Accuracy by inflation level at the time of the forecast.
          </p>
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Regime</th>
                <th scope="col">Model</th>
                <th scope="col">n</th>
                <th scope="col">Median error</th>
                <th scope="col">80% coverage</th>
              </tr>
            </thead>
            <tbody>
              {regimes.map((r) => (
                <tr key={`${r.regime}-${r.model_id}`}>
                  <th scope="row">{r.regime}</th>
                  <td>{names[r.model_id] ?? r.model_id}</td>
                  <td>{r.n}</td>
                  <td>{num(r.median_ae)} pp</td>
                  <td>{pct(r.coverage_80)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      <div className="two-col-grid" style={{ marginBottom: 24 }}>
        <section className="glass-card">
          <h3 style={{ marginBottom: 12 }}>Most influential features</h3>
          <ol className="plain-list">
            {card.global_importance.slice(0, 10).map((f) => (
              <li key={f.feature}>
                {featureLabel(f.feature)} <span className="muted">({f.mean_abs_shap.toFixed(3)})</span>
              </li>
            ))}
          </ol>
          <p style={{ fontSize: "0.8rem", marginTop: 8 }}>Mean |SHAP| across current forecasts.</p>
        </section>
        <section className="glass-card">
          <h3 style={{ marginBottom: 12 }}>Limitations</h3>
          <ul className="plain-list">
            {card.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <h4 style={{ margin: "12px 0 6px" }}>Not intended for</h4>
          <ul className="plain-list">
            {card.not_intended_for.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      </div>
    </>
  );
}

const DETECTOR_NAMES: Record<string, string> = {
  rule: "Hand-written rule (current ETL)",
  robust_z: "Robust z-score",
  isolation_forest: "Isolation Forest (unsupervised)",
  lgbm_local: "LightGBM, own-country features only",
  lgbm: "LightGBM, all features",
};

function AnomalySection({ card }: { card: AnomalyModelCard }) {
  const entries = Object.entries(card.detectors);
  return (
    <section className="glass-card" style={{ marginBottom: 24 }}>
      <h2 style={{ marginBottom: 8 }}>{card.title}</h2>
      <p style={{ marginBottom: 16 }}>
        The original wage dataset silently filled missing values with a formula. Reverse-engineering
        that formula recovered which cells were invented: {card.labels.imputed_cells.toLocaleString()} of{" "}
        {card.labels.observed_cells.toLocaleString()} ({pct(card.labels.imputed_share)}), affecting{" "}
        {card.labels.countries_with_imputation} of {card.labels.countries} countries. Those labels make
        it possible to measure how well different detectors would find them.
      </p>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Detector</th>
              <th scope="col">PR-AUC</th>
              <th scope="col">Precision*</th>
              <th scope="col">Recall*</th>
              <th scope="col">Precision @0.5</th>
              <th scope="col">Recall @0.5</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([id, d]) => (
              <tr key={id}>
                <th scope="row">{DETECTOR_NAMES[id] ?? id}</th>
                <td>{num(d.pr_auc, 3)}</td>
                <td>{pct(d.at_rule_budget.precision)}</td>
                <td>{pct(d.at_rule_budget.recall)}</td>
                <td>{pct(d.at_0_5?.precision)}</td>
                <td>{pct(d.at_0_5?.recall)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p style={{ fontSize: "0.85rem", marginTop: 12 }}>
        * When each detector flags the same number of cells as the rule does. Base rate{" "}
        {pct(card.base_rate)}. Supervised scores are out-of-fold, grouped by country, so the model
        never scores a country it was trained on.
      </p>
    </section>
  );
}
