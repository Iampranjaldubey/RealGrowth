import { useState, type FormEvent } from "react";
import { ChartCard } from "@/components/ui/ChartCard";
import { CountrySelect } from "@/components/ui/CountrySelect";
import { TimeSeriesChart } from "@/components/charts/TimeSeriesChart";
import { usePurchasingPower } from "@/api/queries";
import { formatNumber, formatPercent } from "@/lib/formatters";
import { useUrlNumberState, useUrlState } from "@/lib/useUrlState";

const THIS_YEAR = new Date().getFullYear();

/**
 * "What is my money worth?" — a CPI-based calculator.
 *
 * Practical uses: checking whether a pay rise kept up with prices, adjusting
 * a rent, a contract value or a historical price for inflation. Years after
 * the latest CPI release are extended with the model's forecast and labelled
 * as projections, never presented as data.
 *
 * Form values are local until submitted; the submitted query lives in the
 * URL so a result can be shared as a link.
 */
export function PurchasingPowerPage() {
  const [country, setCountry] = useUrlState("country", "IND");
  const [amount, setAmount] = useUrlNumberState("amount", 50000);
  const [fromYear, setFromYear] = useUrlNumberState("from", 2015);
  const [toYear, setToYear] = useUrlNumberState("to", THIS_YEAR - 1);

  const [draft, setDraft] = useState({ amount, fromYear, toYear });
  const query = usePurchasingPower(country ? { country, amount, fromYear, toYear } : null);
  const result = query.data;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setAmount(draft.amount);
    setFromYear(draft.fromYear);
    setToYear(draft.toYear);
  };

  const projectedFrom = result?.path.find((p) => p.projected)?.year;

  return (
    <div>
      <div className="page-header">
        <h1>Purchasing-power calculator</h1>
        <p>
          How much money you would need in one year to buy what a given amount bought in another,
          based on each country's official consumer price index. Use it to check whether a salary
          kept up with prices, or to adjust a price or contract for inflation.
        </p>
      </div>

      <form className="controls-row glass-card" onSubmit={submit} aria-label="Purchasing power inputs">
        <CountrySelect id="pp-country" indicator="cpi_index" value={country} onChange={setCountry} />
        <div className="form-group">
          <label htmlFor="pp-amount">Amount (local currency)</label>
          <input
            id="pp-amount"
            type="number"
            min={1}
            step="any"
            required
            value={draft.amount}
            onChange={(e) => setDraft({ ...draft, amount: Number(e.target.value) })}
          />
        </div>
        <div className="form-group">
          <label htmlFor="pp-from">In year</label>
          <input
            id="pp-from"
            type="number"
            min={1960}
            max={THIS_YEAR + 2}
            required
            value={draft.fromYear}
            onChange={(e) => setDraft({ ...draft, fromYear: Number(e.target.value) })}
          />
        </div>
        <div className="form-group">
          <label htmlFor="pp-to">Is worth, in year</label>
          <input
            id="pp-to"
            type="number"
            min={1960}
            max={THIS_YEAR + 2}
            required
            value={draft.toYear}
            onChange={(e) => setDraft({ ...draft, toYear: Number(e.target.value) })}
          />
        </div>
        <button type="submit" className="btn btn-primary">
          Calculate
        </button>
      </form>

      {query.isError && (
        <div className="glass-card" role="alert">
          <p>{(query.error as { detail?: string }).detail ?? query.error.message}</p>
        </div>
      )}

      {result && (
        <>
          <div className="glass-card result-hero" aria-live="polite">
            <p>
              {formatNumber(result.amount, 0)} in {result.from_year} in {result.country.name} has the
              same purchasing power as
            </p>
            <p className="result-hero__value">
              {formatNumber(result.equivalent, 0)} <span>in {result.to_year}</span>
            </p>
            <p>
              Prices changed by {formatPercent(result.cumulative_inflation_pct, 1)} in total, or{" "}
              {formatPercent(result.annualised_inflation_pct, 2)} a year on average.
            </p>
            {result.uses_projection && (
              <p className="quality-banner" style={{ marginTop: 12, marginBottom: 0 }}>
                <span className="quality-banner__icon" aria-hidden="true">
                  🔮
                </span>
                Official price data ends in {result.last_observed_year}; {projectedFrom} onwards uses
                this site's inflation forecast and is an estimate, not data.
              </p>
            )}
          </div>

          <ChartCard title="Equivalent amount over time" subtitle="Local currency, at each year's prices">
            <TimeSeriesChart
              series={[
                {
                  iso3: result.country.iso3,
                  country: result.country.name,
                  region: result.country.region,
                  flag: null,
                  points: result.path.map((p) => ({ year: p.year, value: p.value })),
                },
              ]}
              valueFormatter={(v) => formatNumber(v, 0)}
              showLegend={false}
            />
          </ChartCard>
        </>
      )}

      {query.isLoading && <ChartCard loading />}
    </div>
  );
}
