"""Data access: every query the API can run, expressed as SQL.

Deliberately free of any web-framework import so it can be unit-tested against a
temporary database without spinning up an app, and free of any ORM so the SQL
being executed is the SQL you read.

Filtering, ranking and aggregation happen in SQLite rather than in Python. The
previous implementation pulled whole DataFrames into memory and sorted them per
request; here the database does that work against an index.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from typing import Any, Literal

from realgrowth import stats

SortOrder = Literal["asc", "desc"]

#: Hard ceiling on rows any single endpoint will return.
MAX_LIMIT = 500


class NotFoundError(LookupError):
    """Raised when a requested entity does not exist."""


class RepositoryError(RuntimeError):
    """Raised when a query is well-formed but cannot be satisfied."""


def _rows_to_dicts(rows: Sequence[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


class Repository:
    """Read-only queries against the warehouse."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    # ------------------------------------------------------------- metadata

    def list_indicators(self) -> list[dict[str, Any]]:
        """Every indicator with its year span, coverage and provenance."""
        rows = self._connection.execute(
            """
            SELECT id, name, unit, unit_symbol, description, source, source_url, category,
                   direction, decimals, is_derived, depends_on,
                   min_year, max_year, country_count
            FROM indicators
            ORDER BY is_derived DESC, name
            """
        ).fetchall()
        out = []
        for row in _rows_to_dicts(rows):
            row["is_derived"] = bool(row["is_derived"])
            row["depends_on"] = [d for d in (row["depends_on"] or "").split(",") if d]
            out.append(row)
        return out

    def get_indicator(self, indicator_id: str) -> dict[str, Any]:
        for indicator in self.list_indicators():
            if indicator["id"] == indicator_id:
                return indicator
        raise NotFoundError(f"unknown indicator: {indicator_id}")

    def list_regions(self) -> list[str]:
        rows = self._connection.execute(
            """
            SELECT DISTINCT region FROM countries
            WHERE is_aggregate = 0 AND region IS NOT NULL AND region != ''
            ORDER BY region
            """
        ).fetchall()
        return [str(row["region"]) for row in rows]

    def list_countries(
        self,
        *,
        indicator_id: str | None = None,
        region: str | None = None,
        include_aggregates: bool = False,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        """Countries, optionally restricted to those having data for an indicator.

        The old UI populated dropdowns from a country list that was not filtered
        by indicator, so selecting a country often produced an empty chart. It
        also mixed World Bank aggregates such as "Africa Eastern and Southern"
        into a list of countries; aggregates are now opt-in.
        """
        clauses: list[str] = []
        params: list[Any] = []

        if not include_aggregates:
            clauses.append("c.is_aggregate = 0")
        if region:
            clauses.append("c.region = ?")
            params.append(region)
        if search:
            clauses.append("LOWER(c.name) LIKE ?")
            params.append(f"%{search.lower()}%")
        if indicator_id:
            self.get_indicator(indicator_id)  # validate, raising NotFoundError
            clauses.append(
                "EXISTS (SELECT 1 FROM observations o WHERE o.iso3 = c.iso3 AND o.indicator_id = ?)"
            )
            params.append(indicator_id)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._connection.execute(
            f"""
            SELECT c.iso3, c.name, c.region, c.is_aggregate
            FROM countries c
            {where}
            ORDER BY c.name
            """,
            params,
        ).fetchall()
        out = []
        for row in _rows_to_dicts(rows):
            row["is_aggregate"] = bool(row["is_aggregate"])
            out.append(row)
        return out

    def get_country(self, iso3: str) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT iso3, name, region, is_aggregate FROM countries WHERE iso3 = ?",
            (iso3.upper(),),
        ).fetchone()
        if row is None:
            raise NotFoundError(f"unknown country: {iso3}")
        country = dict(row)
        country["is_aggregate"] = bool(country["is_aggregate"])
        return country

    # ------------------------------------------------------------ series

    def get_flags(self, indicator_id: str, iso3s: Sequence[str] | None = None) -> dict[str, str]:
        """Series-level caveats, keyed by ISO3."""
        query = "SELECT iso3, flag, detail FROM series_flags WHERE indicator_id = ?"
        params: list[Any] = [indicator_id]
        if iso3s:
            placeholders = ",".join("?" * len(iso3s))
            query += f" AND iso3 IN ({placeholders})"
            params.extend(code.upper() for code in iso3s)
        return {
            str(row["iso3"]): str(row["detail"])
            for row in self._connection.execute(query, params).fetchall()
        }

    def get_series(
        self,
        indicator_id: str,
        iso3s: Sequence[str],
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[dict[str, Any]]:
        """One time series per requested country.

        Points are returned only where an observation exists, so the client can
        render a genuine gap instead of a zero. Encoding "no data" as ``0`` is
        what made the old dashboards show fictional collapses.
        """
        self.get_indicator(indicator_id)
        if not iso3s:
            return []
        codes = [code.upper() for code in iso3s]
        placeholders = ",".join("?" * len(codes))
        params: list[Any] = [indicator_id, *codes]
        year_clause = ""
        if start_year is not None:
            year_clause += " AND o.year >= ?"
            params.append(start_year)
        if end_year is not None:
            year_clause += " AND o.year <= ?"
            params.append(end_year)

        rows = self._connection.execute(
            f"""
            SELECT o.iso3, c.name, c.region, o.year, o.value
            FROM observations o
            JOIN countries c ON c.iso3 = o.iso3
            WHERE o.indicator_id = ? AND o.iso3 IN ({placeholders}){year_clause}
            ORDER BY c.name, o.year
            """,
            params,
        ).fetchall()

        flags = self.get_flags(indicator_id, codes)
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            iso3 = str(row["iso3"])
            series = grouped.setdefault(
                iso3,
                {
                    "iso3": iso3,
                    "country": row["name"],
                    "region": row["region"],
                    "flag": flags.get(iso3),
                    "points": [],
                },
            )
            series["points"].append({"year": row["year"], "value": row["value"]})

        # Preserve the caller's ordering, and report requested-but-empty series.
        ordered: list[dict[str, Any]] = []
        for code in codes:
            if code in grouped:
                ordered.append(grouped[code])
        return ordered

    def get_snapshot(
        self,
        indicator_id: str,
        *,
        year: int | None = None,
        region: str | None = None,
        min_population: int | None = None,
        include_aggregates: bool = False,
        order: SortOrder = "desc",
        limit: int | None = None,
    ) -> dict[str, Any]:
        """All countries' values for a single year, ranked.

        Backs both the choropleth and the ranking bar chart. ``year`` defaults to
        the indicator's most recent year rather than a hardcoded constant, so a
        page can never request a year the data does not cover.
        """
        indicator = self.get_indicator(indicator_id)
        if indicator["max_year"] is None:
            return {"indicator_id": indicator_id, "year": None, "values": []}

        target_year = indicator["max_year"] if year is None else year
        clauses = ["o.indicator_id = ?", "o.year = ?"]
        params: list[Any] = [indicator_id, target_year]

        if not include_aggregates:
            clauses.append("c.is_aggregate = 0")
        if region:
            clauses.append("c.region = ?")
            params.append(region)
        if min_population is not None:
            clauses.append(
                """
                EXISTS (
                    SELECT 1 FROM observations p
                    WHERE p.iso3 = o.iso3 AND p.indicator_id = 'population'
                      AND p.value >= ?
                      AND p.year = (SELECT MAX(year) FROM observations
                                    WHERE iso3 = o.iso3 AND indicator_id = 'population')
                )
                """
            )
            params.append(min_population)

        direction = "ASC" if order == "asc" else "DESC"
        effective_limit = MAX_LIMIT if limit is None else max(1, min(limit, MAX_LIMIT))
        params.append(effective_limit)

        rows = self._connection.execute(
            f"""
            SELECT o.iso3, c.name AS country, c.region, o.value
            FROM observations o
            JOIN countries c ON c.iso3 = o.iso3
            WHERE {" AND ".join(clauses)}
            ORDER BY o.value {direction}, c.name
            LIMIT ?
            """,
            params,
        ).fetchall()

        return {
            "indicator_id": indicator_id,
            "year": target_year,
            "values": _rows_to_dicts(rows),
        }

    def get_country_profile(self, iso3: str) -> dict[str, Any]:
        """Latest observation of every indicator for one country."""
        country = self.get_country(iso3)
        rows = self._connection.execute(
            """
            SELECT o.indicator_id, o.year, o.value
            FROM observations o
            WHERE o.iso3 = ?
              AND o.year = (
                  SELECT MAX(year) FROM observations
                  WHERE iso3 = o.iso3 AND indicator_id = o.indicator_id
              )
            ORDER BY o.indicator_id
            """,
            (country["iso3"],),
        ).fetchall()
        return {"country": country, "latest": _rows_to_dicts(rows)}

    # -------------------------------------------------------- correlation

    def correlate_over_time(
        self,
        iso3: str,
        indicator_x: str,
        indicator_y: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> dict[str, Any]:
        """Correlate two indicators across years, within one country."""
        country = self.get_country(iso3)
        self.get_indicator(indicator_x)
        self.get_indicator(indicator_y)

        # Parameter order follows the SQL text: the join predicate binds
        # indicator_y, then the WHERE clause binds indicator_x, the country and
        # any year bounds.
        year_clause = ""
        year_params: list[Any] = []
        if start_year is not None:
            year_clause += " AND x.year >= ?"
            year_params.append(start_year)
        if end_year is not None:
            year_clause += " AND x.year <= ?"
            year_params.append(end_year)

        rows = self._connection.execute(
            f"""
            SELECT x.year, x.value AS x_value, y.value AS y_value
            FROM observations x
            JOIN observations y
              ON y.iso3 = x.iso3 AND y.year = x.year AND y.indicator_id = ?
            WHERE x.indicator_id = ? AND x.iso3 = ?{year_clause}
            ORDER BY x.year
            """,
            [indicator_y, indicator_x, country["iso3"], *year_params],
        ).fetchall()

        points = [
            {
                "label": str(row["year"]),
                "year": row["year"],
                "x": row["x_value"],
                "y": row["y_value"],
            }
            for row in rows
        ]
        return self._summarise_correlation(
            mode="time",
            indicator_x=indicator_x,
            indicator_y=indicator_y,
            points=points,
            subject=country,
        )

    def correlate_across_countries(
        self,
        indicator_x: str,
        indicator_y: str,
        year: int,
        *,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Correlate two indicators across countries, within one year.

        The cross-sectional view the old app lacked: it could only correlate two
        series for a single country, which is the weaker of the two questions.
        """
        self.get_indicator(indicator_x)
        self.get_indicator(indicator_y)

        params: list[Any] = [indicator_y, indicator_x, year]
        region_clause = ""
        if region:
            region_clause = " AND c.region = ?"
            params.append(region)

        rows = self._connection.execute(
            f"""
            SELECT c.iso3, c.name, x.value AS x_value, y.value AS y_value
            FROM observations x
            JOIN observations y
              ON y.iso3 = x.iso3 AND y.year = x.year AND y.indicator_id = ?
            JOIN countries c ON c.iso3 = x.iso3
            WHERE x.indicator_id = ? AND x.year = ? AND c.is_aggregate = 0{region_clause}
            ORDER BY c.name
            """,
            params,
        ).fetchall()

        points = [
            {
                "label": str(row["name"]),
                "iso3": str(row["iso3"]),
                "x": row["x_value"],
                "y": row["y_value"],
            }
            for row in rows
        ]
        return self._summarise_correlation(
            mode="cross_section",
            indicator_x=indicator_x,
            indicator_y=indicator_y,
            points=points,
            year=year,
            region=region,
        )

    def _summarise_correlation(
        self,
        *,
        mode: str,
        indicator_x: str,
        indicator_y: str,
        points: list[dict[str, Any]],
        subject: dict[str, Any] | None = None,
        year: int | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "mode": mode,
            "indicator_x": indicator_x,
            "indicator_y": indicator_y,
            "country": subject,
            "year": year,
            "region": region,
            "points": points,
            "statistics": None,
            "note": None,
        }
        if len(points) < stats.MIN_PAIRS:
            result["note"] = (
                f"only {len(points)} overlapping observation(s); "
                f"at least {stats.MIN_PAIRS} are needed to correlate"
            )
            return result

        summary = stats.correlate([p["x"] for p in points], [p["y"] for p in points])
        result["statistics"] = {
            "n": summary.n,
            "r": summary.r,
            "r_squared": summary.r_squared,
            "slope": summary.slope,
            "intercept": summary.intercept,
            "p_value": summary.p_value,
            "ci_low": summary.ci_low,
            "ci_high": summary.ci_high,
            "is_significant": summary.is_significant,
            "strength": summary.strength,
        }
        result["note"] = "Correlation is not causation; both series may respond to a common driver."
        return result

    # ----------------------------------------------------------- quality

    def get_quality_report(self) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT value FROM etl_metadata WHERE key = 'quality_report'"
        ).fetchone()
        if row is None:
            raise RepositoryError("warehouse has no quality report; rebuild the database")
        report: dict[str, Any] = json.loads(str(row["value"]))
        return report

    def get_snapshot_manifest(self) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT value FROM etl_metadata WHERE key = 'snapshot_manifest'"
        ).fetchone()
        manifest: dict[str, Any] = json.loads(str(row["value"])) if row else {}
        return manifest

    def get_warehouse_info(self) -> dict[str, Any]:
        rows = self._connection.execute(
            "SELECT key, value FROM etl_metadata WHERE key IN ('schema_version', 'built_at')"
        ).fetchall()
        info = {str(row["key"]): str(row["value"]) for row in rows}
        counts = self._connection.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM observations) AS observations,
              (SELECT COUNT(*) FROM countries WHERE is_aggregate = 0) AS countries,
              (SELECT COUNT(*) FROM indicators) AS indicators
            """
        ).fetchone()
        return {
            "schema_version": int(info.get("schema_version", 0)),
            "built_at": info.get("built_at"),
            "observations": counts["observations"],
            "countries": counts["countries"],
            "indicators": counts["indicators"],
        }

    # ---------------------------------------------------------- forecasts

    def list_models(self, indicator_id: str | None = None) -> list[dict[str, Any]]:
        """Forecasting models (ours, baselines and the IMF benchmark)."""
        query = "SELECT id, indicator_id, name, kind, is_champion, description FROM models"
        params: list[Any] = []
        if indicator_id:
            query += " WHERE indicator_id = ?"
            params.append(indicator_id)
        query += " ORDER BY is_champion DESC, kind = 'external' DESC, kind, name"
        rows = _rows_to_dicts(self._connection.execute(query, params).fetchall())
        for row in rows:
            row["is_champion"] = bool(row["is_champion"])
        return rows

    def get_champion(self, indicator_id: str) -> dict[str, Any]:
        for model in self.list_models(indicator_id):
            if model["is_champion"]:
                return model
        raise NotFoundError(f"no forecasting model has been trained for {indicator_id}")

    def get_model_card(self, task: str) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT value FROM etl_metadata WHERE key = ?", (f"model_card:{task}",)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"no model card for {task!r}; train with `python -m realgrowth_ml`")
        card: dict[str, Any] = json.loads(str(row["value"]))
        return card

    def get_country_forecast(
        self, iso3: str, indicator_id: str, *, history_years: int = 25
    ) -> dict[str, Any]:
        """Everything the forecast page needs for one country.

        History, the champion's forward forecasts with intervals, the IMF
        benchmark, the champion's and naive baseline's out-of-sample backtest
        for this country, and the TreeSHAP drivers of each forecast.
        """
        country = self.get_country(iso3)
        indicator = self.get_indicator(indicator_id)
        champion = self.get_champion(indicator_id)
        code = country["iso3"]

        history = _rows_to_dicts(
            self._connection.execute(
                """
                SELECT year, value FROM observations
                WHERE indicator_id = ? AND iso3 = ? AND year >= (
                    SELECT MAX(year) FROM observations WHERE indicator_id = ? AND iso3 = ?
                ) - ?
                ORDER BY year
                """,
                (indicator_id, code, indicator_id, code, history_years),
            ).fetchall()
        )

        forecast_rows = _rows_to_dicts(
            self._connection.execute(
                """
                SELECT f.model_id, f.origin_year, f.target_year, f.horizon, f.point,
                       f.lower_80, f.upper_80, f.lower_95, f.upper_95
                FROM forecasts f JOIN models m ON m.id = f.model_id
                WHERE f.iso3 = ? AND m.indicator_id = ?
                ORDER BY f.model_id, f.target_year
                """,
                (code, indicator_id),
            ).fetchall()
        )
        by_model: dict[str, list[dict[str, Any]]] = {}
        for row in forecast_rows:
            by_model.setdefault(str(row.pop("model_id")), []).append(row)

        backtest_rows = _rows_to_dicts(
            self._connection.execute(
                """
                SELECT model_id, origin_year, target_year, horizon, actual, point,
                       lower_80, upper_80
                FROM backtest_predictions
                WHERE iso3 = ? AND model_id IN (?, 'naive') AND horizon = 1
                ORDER BY model_id, target_year
                """,
                (code, champion["id"]),
            ).fetchall()
        )
        backtest: dict[str, list[dict[str, Any]]] = {}
        for row in backtest_rows:
            backtest.setdefault(str(row.pop("model_id")), []).append(row)

        drivers_rows = _rows_to_dicts(
            self._connection.execute(
                """
                SELECT target_year, feature, feature_value, contribution
                FROM forecast_contributions
                WHERE model_id = ? AND iso3 = ?
                ORDER BY target_year, ABS(contribution) DESC
                """,
                (champion["id"], code),
            ).fetchall()
        )
        drivers: dict[int, list[dict[str, Any]]] = {}
        for row in drivers_rows:
            drivers.setdefault(int(row.pop("target_year")), []).append(row)

        return {
            "country": country,
            "indicator": indicator,
            "champion": champion,
            "history": history,
            "forecasts": [
                {"model_id": model_id, "points": points} for model_id, points in by_model.items()
            ],
            "backtest": [
                {"model_id": model_id, "points": points} for model_id, points in backtest.items()
            ],
            "drivers": [
                {"target_year": year, "contributions": rows[:8]}
                for year, rows in sorted(drivers.items())
            ],
        }

    def get_forecast_snapshot(self, indicator_id: str, horizon: int) -> dict[str, Any]:
        """The champion's forecast for every country at one horizon, ranked."""
        champion = self.get_champion(indicator_id)
        rows = _rows_to_dicts(
            self._connection.execute(
                """
                SELECT f.iso3, c.name AS country, c.region, f.origin_year, f.target_year,
                       f.point, f.lower_80, f.upper_80
                FROM forecasts f JOIN countries c ON c.iso3 = f.iso3
                WHERE f.model_id = ? AND f.horizon = ? AND c.is_aggregate = 0
                ORDER BY f.point DESC
                """,
                (champion["id"], horizon),
            ).fetchall()
        )
        return {"model": champion, "horizon": horizon, "values": rows}

    # ---------------------------------------------------------- anomalies

    def get_anomaly_scores(
        self, indicator_id: str, iso3: str | None = None, *, flagged_only: bool = False
    ) -> list[dict[str, Any]]:
        self.get_indicator(indicator_id)
        clauses = ["a.indicator_id = ?"]
        params: list[Any] = [indicator_id]
        if iso3:
            code = self.get_country(iso3)["iso3"]
            clauses.append("a.iso3 = ?")
            params.append(code)
        if flagged_only:
            clauses.append("a.is_flagged = 1")
        rows = self._connection.execute(
            f"""
            SELECT a.iso3, c.name AS country, a.year, a.score, a.is_flagged
            FROM anomaly_scores a JOIN countries c ON c.iso3 = a.iso3
            WHERE {" AND ".join(clauses)}
            ORDER BY c.name, a.year
            """,
            params,
        ).fetchall()
        out = _rows_to_dicts(rows)
        for row in out:
            row["is_flagged"] = bool(row["is_flagged"])
        return out

    # ------------------------------------------------------ purchasing power

    def purchasing_power(
        self, iso3: str, amount: float, from_year: int, to_year: int
    ) -> dict[str, Any]:
        """What ``amount`` in ``from_year`` is worth in ``to_year`` prices.

        Uses the consumer price index where it is observed. Years after the
        last observation are extended with the champion inflation forecast and
        marked ``projected``, so the calculator can answer "what will my salary
        need to be next year?" without pretending a forecast is data.
        """
        if amount <= 0:
            raise ValueError("amount must be positive")
        country = self.get_country(iso3)
        code = country["iso3"]
        cpi = {
            int(row["year"]): float(row["value"])
            for row in self._connection.execute(
                "SELECT year, value FROM observations "
                "WHERE indicator_id = 'cpi_index' AND iso3 = ?",
                (code,),
            ).fetchall()
        }
        if not cpi:
            raise NotFoundError(f"no consumer price index for {country['name']}")

        last_observed = max(cpi)
        projected_years: set[int] = set()
        forecast_rows = self._connection.execute(
            """
            SELECT f.target_year, f.point FROM forecasts f
            JOIN models m ON m.id = f.model_id
            WHERE f.iso3 = ? AND m.indicator_id = 'inflation_rate' AND m.is_champion = 1
            ORDER BY f.target_year
            """,
            (code,),
        ).fetchall()
        for row in forecast_rows:
            year = int(row["target_year"])
            if year == max(cpi) + 1:
                cpi[year] = cpi[year - 1] * (1 + float(row["point"]) / 100.0)
                projected_years.add(year)

        first_observed = min(cpi)
        last_available = max(cpi)
        for year in (from_year, to_year):
            if year not in cpi:
                raise ValueError(
                    f"{country['name']} has a price index for {first_observed}-{last_observed}"
                    + (
                        f" (projected to {last_available})"
                        if last_available > last_observed
                        else ""
                    )
                    + f"; {year} is not available"
                )

        factor = cpi[to_year] / cpi[from_year]
        low, high = min(from_year, to_year), max(from_year, to_year)
        path = [
            {
                "year": year,
                "index": cpi[year],
                "value": amount * cpi[year] / cpi[from_year],
                "projected": year in projected_years,
            }
            for year in range(low, high + 1)
            if year in cpi
        ]
        years = high - low
        # Geometric rate of change in the equivalent amount per year. It already
        # carries the right sign in both directions (factor < 1 going back in time
        # when prices rose), matching cumulative_inflation_pct.
        annualised = (factor ** (1 / years) - 1) * 100 if years and factor > 0 else 0.0
        return {
            "country": country,
            "amount": amount,
            "from_year": from_year,
            "to_year": to_year,
            "equivalent": amount * factor,
            "cumulative_inflation_pct": (factor - 1) * 100,
            "annualised_inflation_pct": annualised,
            "uses_projection": any(p["projected"] for p in path),
            "last_observed_year": last_observed,
            "path": path,
        }
