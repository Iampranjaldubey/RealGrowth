import { Link } from "react-router-dom";
import { ChartCard } from "@/components/ui/ChartCard";
import { CountrySelect } from "@/components/ui/CountrySelect";
import { DriversList } from "@/components/ui/DriversList";
import { StatCard } from "@/components/ui/StatCard";
import { ForecastChart } from "@/components/charts/ForecastChart";
import { useCountryForecast, useInflationModelCard } from "@/api/queries";
import { backtestSummary, buildForecastChartData } from "@/lib/forecast";
import { formatPercent } from "@/lib/formatters";
import { useUrlState } from "@/lib/useUrlState";

const IMF_MODEL = "imf_weo";

/**
 * Inflation outlook for one country: history, our 1- and 2-year-ahead
 * forecasts with conformal intervals, the IMF's published projection for
 * comparison, what drove the forecast, and how the model would have done for
 * this country in the past (its out-of-sample backtest).
 */
export function ForecastPage() {
  const [iso3, setIso3] = useUrlState("country", "IND");
  const forecast = useCountryForecast(iso3 || undefined);
  const card = useInflationModelCard();
  const data = forecast.data;

  const championId = data?.champion.id;
  const champion = data?.forecasts.find((f) => f.model_id === championId)?.points ?? [];
  const imf = data?.forecasts.find((f) => f.model_id === IMF_MODEL)?.points ?? [];
  const next = champion.find((p) => p.horizon === 1);
  const after = champion.find((p) => p.horizon === 2);
  const imfNext = next ? imf.find((p) => p.target_year === next.target_year) : undefined;
  const drivers = data?.drivers.find((d) => d.target_year === next?.target_year);

  const backtest = backtestSummary(
    data?.backtest.find((b) => b.model_id === championId)?.points ?? [],
    data?.backtest.find((b) => b.model_id === "naive")?.points ?? [],
  );
  const testH1 = card.data?.metrics.find(
    (m) => m.model_id === card.data?.champion && m.horizon === 1 && m.window === "test",
  );

  const pct = (value: number | null | undefined) => formatPercent(value ?? null, 1);

  return (
    <div>
      <div className="page-header">
        <h1>Inflation outlook</h1>
        <p>
          Forecasts of consumer price inflation one and two years ahead, with honest uncertainty
          ranges. The shaded bands contain the true value 80% and 95% of the time in out-of-sample
          testing.{" "}
          <Link to="/models">How the model works and how well it performs →</Link>
        </p>
      </div>

      <div className="controls-row glass-card">
        <CountrySelect id="forecast-country" indicator="inflation_rate" value={iso3} onChange={setIso3} />
      </div>

      {forecast.isError && (
        <div className="glass-card" role="alert">
          <p>No forecast is available for this country. {forecast.error.message}</p>
        </div>
      )}

      {data && (
        <>
          <div className="stats-grid stagger-children">
            <StatCard
              title={`Forecast for ${next?.target_year ?? "next year"}`}
              value={pct(next?.point)}
              icon="🔮"
              color="secondary"
            />
            <StatCard
              title="80% range"
              value={next ? `${pct(next.lower_80)} to ${pct(next.upper_80)}` : "N/A"}
              icon="↕️"
              color="primary"
            />
            <StatCard
              title={`IMF projection (${next?.target_year ?? ""})`}
              value={pct(imfNext?.point)}
              icon="🏛️"
              color="warning"
            />
            <StatCard
              title={`Forecast for ${after?.target_year ?? "year after"}`}
              value={pct(after?.point)}
              icon="📅"
              color="tertiary"
            />
          </div>

          <ChartCard
            title={`${data.country.name}: inflation, observed and forecast`}
            subtitle={`${data.indicator.unit} · model: ${data.champion.name} · data: ${data.indicator.source}`}
          >
            <ForecastChart
              data={buildForecastChartData(data.history, champion, imf)}
              valueFormatter={(v) => formatPercent(v, 1)}
            />
          </ChartCard>

          <div className="two-col-grid" style={{ marginTop: 24 }}>
            <div className="glass-card">
              <h3 style={{ marginBottom: 4 }}>What is driving the {next?.target_year} forecast</h3>
              <p style={{ fontSize: "0.85rem", marginBottom: 16 }}>
                Each bar is a feature's contribution relative to the average forecast (TreeSHAP, on
                the model's log scale). Longer bars matter more.
              </p>
              <DriversList contributions={drivers?.contributions ?? []} />
            </div>

            <div className="glass-card">
              <h3 style={{ marginBottom: 4 }}>Track record for {data.country.name}</h3>
              <p style={{ fontSize: "0.85rem", marginBottom: 16 }}>
                One-year-ahead forecasts the model would have made in past years, using only data
                available at the time.
              </p>
              <table className="data-table">
                <tbody>
                  <tr>
                    <th scope="row">Past forecasts evaluated</th>
                    <td>{backtest.n}</td>
                  </tr>
                  <tr>
                    <th scope="row">Average error, this model</th>
                    <td>{backtest.championMae === null ? "N/A" : `${backtest.championMae.toFixed(2)} pp`}</td>
                  </tr>
                  <tr>
                    <th scope="row">Average error, "same as last year"</th>
                    <td>{backtest.naiveMae === null ? "N/A" : `${backtest.naiveMae.toFixed(2)} pp`}</td>
                  </tr>
                  <tr>
                    <th scope="row">Actual inside 80% range</th>
                    <td>{backtest.coverage80 === null ? "N/A" : formatPercent(backtest.coverage80 * 100, 0).replace("+", "")}</td>
                  </tr>
                  {testH1 && (
                    <tr>
                      <th scope="row">All countries, 2010 onwards</th>
                      <td>
                        {testH1.median_ae.toFixed(2)} pp median error ·{" "}
                        {((testH1.skill_vs_naive ?? 0) * 100).toFixed(0)}% better than naive
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {forecast.isLoading && <ChartCard loading />}
    </div>
  );
}
