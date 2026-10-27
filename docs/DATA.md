# Data

## Sources

All series except wages come from public, keyless APIs and are refreshed by
`python -m realgrowth.ingest`. The table reflects the committed snapshot (fetched
2026-10-26; the World Bank reported its last update as 2026-10-08).

| Indicator id | Source | Upstream code | Countries | Years |
|---|---|---|---|---|
| `inflation_rate` | World Bank WDI | FP.CPI.TOTL.ZG | 213 | 1960-2025 |
| `cpi_index` | World Bank WDI | FP.CPI.TOTL | 192 | 1960-2025 |
| `gdp_deflator_inflation` | World Bank WDI | NY.GDP.DEFL.KD.ZG | 233 | 1961-2025 |
| `gdp_per_capita` | World Bank WDI | NY.GDP.PCAP.CD | 234 | 1960-2025 |
| `gdp_per_capita_ppp` | World Bank WDI | NY.GDP.PCAP.PP.CD | 223 | 1990-2025 |
| `gdp_growth` | World Bank WDI | NY.GDP.MKTP.KD.ZG | 234 | 1961-2025 |
| `unemployment_rate` | World Bank WDI (ILO modelled) | SL.UEM.TOTL.ZS | 207 | 1991-2025 |
| `broad_money_growth` | World Bank WDI | FM.LBL.BMNY.ZG | 166 | 1961-2025 |
| `exchange_rate` | World Bank WDI | PA.NUS.FCRF | 214 | 1960-2025 |
| `current_account` | World Bank WDI | BN.CAB.XOKA.GD.ZS | 200 | 1960-2025 |
| `trade_openness` | World Bank WDI | NE.TRD.GNFS.ZS | 214 | 1960-2025 |
| `real_interest_rate` | World Bank WDI | FR.INR.RINR | 148 | 1961-2025 |
| `population`, `urban_population`, `rural_population`, `urbanisation_rate` | World Bank WDI | SP.POP.TOTL, SP.URB.TOTL, SP.RUR.TOTL, SP.URB.TOTL.IN.ZS | 237 | 1960-2025 |
| `gini_index` | World Bank WDI | SI.POV.GINI | 171 | 1963-2025 |
| `poverty_rate` | World Bank WDI | SI.POV.DDAY | 177 | 1963-2025 |
| `debt_to_gdp` | IMF World Economic Outlook | GGXWDG_NGDP (history only) | 195 | 1980-2025 |
| *IMF inflation projections* | IMF World Economic Outlook | PCPIPCH (projections only) | 192 | 2026-2031 |
| `healthy_diet_cost` | Our World in Data (FAO / World Bank) | cost-healthy-diet | 176 | 2017-2024 |
| `avg_wage` | ILOSTAT extract from the original project, in USD | — | 121 | 2006-2022 |

The country counts include World Bank aggregates (World, regions, income
groups) where the registry knows them. Aggregates are stored but excluded from
country lists, rankings and models unless explicitly requested.

**Derived indicators** (`backend/src/realgrowth/etl/derive.py`):

```
avg_wage_lcu        = avg_wage (USD) × exchange_rate (LCU per USD)
nominal_wage_growth = year-on-year % change of avg_wage_lcu
real_wage_growth    = nominal_wage_growth − inflation_rate
```

### Why APIs and not scrapers

The original project scraped Macrotrends and Wikipedia HTML. Macrotrends
republishes World Bank and IMF data, so scraping it means taking a copy of a
source you can query directly, with extra transcription risk and less clear
terms of use. Every series that used to be scraped now comes from its primary
publisher's documented API. That makes it more accurate, more recent (1960-2025
instead of 2018-2022 for some series), and stable against page-layout changes.

### Why wages are still a legacy file

ILOSTAT's earnings data has no keyless API that worked during this rebuild
(the SDMX dataflow ids returned 404, and the R-plumber endpoint reports the
indicator id as deprecated). The wage panel therefore comes from the original
project's extract. Its quality problems are the subject of
[ANOMALY_DETECTION.md](ANOMALY_DETECTION.md). Replacing it with a live ILOSTAT
connector is the first item in the roadmap.

## Country registry

The raw sources name countries inconsistently ("Korea, Rep." vs "South Korea",
"Turkiye" vs "Turkey", "Congo" vs "Congo, Dem. Rep."). `data/reference/countries.csv`
maps every known label to an ISO-3166 alpha-3 code: 218 countries and 24 named
aggregates. Matching is exact after case and whitespace folding, never fuzzy,
because a fuzzy matcher would merge the two Congos. API connectors map
publisher codes at the boundary (`UVK` → `XKX` Kosovo, `WBG` → `PSE`,
`WEOWORLD` → `WLD`). Any unknown code fails a `--strict` build.

## Quality controls

Applied in the ETL and published at `/api/v1/meta/quality` and on the Data
Quality page:

| Check | Outcome | Fails `--strict`? |
|---|---|---|
| Label/code not in registry | `unresolved_entity` issue, row dropped | yes |
| Two rows for one country-year | `duplicate_entity`, first kept | yes |
| Snapshot file missing | `missing_source` | yes |
| Value outside physical range | `out_of_range`, dropped | no |
| Wage growth with an imputed endpoint | `imputed_input`, not computed; series flagged | no |
| Wage move >40% not explained by ≥25% inflation | `implausible_growth`, dropped; series flagged | no |

Plausibility findings do not fail the build. They are known properties of the
upstream data, and they are counted and published rather than hidden.

## Two corrections to the original dataset

**1. Real wages are computed in local currency.** The original computed real
wage growth as *USD* wage growth minus *domestic* inflation. In 2022 the dollar
rose sharply, so that method reported Japan at −17.7% and Germany at −13.6%. In
local currency, the ILO/OECD definition, the figures are −0.9% and −2.2%. The
USD wage had been produced as `local wage / exchange rate`, so multiplying by the
same World Bank rate recovers the local-currency wage exactly. See
`notebooks/analysis/01_exploratory_analysis.ipynb` §6.

**2. Invented wage values are excluded.** 25% of wage cells (514 of 2,032), and
89% of 2022 cells, were filled by a formula and not measured. The ETL now
refuses to compute any growth rate with an imputed endpoint. Real wage growth
dropped from 1,736 to 1,318 observations. The ones that remain are
measurements.

## Licences

World Bank WDI and Our World in Data publish under CC BY 4.0. The IMF permits
reuse with attribution under its copyright and usage terms. ILOSTAT data is
reusable with attribution. Check each publisher's current terms before
commercial reuse. The code is MIT-licensed.
