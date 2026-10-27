"""Source connectors: one function per upstream API, each returning tidy rows.

Every connector has the same contract::

    fetch_<source>(spec, client, allowed) -> FetchResult

``allowed`` is the set of ISO3 codes the country registry knows. Rows for any
other code (the IMF's ``ADVEC`` "advanced economies" group, the World Bank's
income-group aggregates, ...) are counted and dropped here, at the boundary,
so nothing downstream ever has to wonder whether a row is a country.

Connectors do no plausibility filtering. They faithfully record what the
publisher published; judging the values is the ETL's job, which keeps "what did
the source say?" and "what do we believe?" separable when debugging.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from realgrowth.ingest.catalog import IMF_CODE_FIXES, SeriesSpec
from realgrowth.ingest.http import FetchError, HttpClient

WORLD_BANK_BASE = "https://api.worldbank.org/v2"
IMF_BASE = "https://www.imf.org/external/datamapper/api/v1"
OWID_BASE = "https://ourworldindata.org/grapher"

#: First year requested from the World Bank (its data starts in 1960).
WB_START_YEAR = 1960


class Row(tuple[str, int, float]):
    """``(iso3, year, value)``. A tuple subclass only for a readable name."""

    __slots__ = ()

    def __new__(cls, iso3: str, year: int, value: float) -> Row:
        return super().__new__(cls, (iso3, year, value))

    @property
    def iso3(self) -> str:
        return self[0]

    @property
    def year(self) -> int:
        return self[1]

    @property
    def value(self) -> float:
        return self[2]


@dataclass
class FetchResult:
    """The rows fetched for one series, plus provenance for the manifest."""

    spec: SeriesSpec
    url: str
    rows: list[Row]
    fetched_at: str
    #: The publisher's own "last updated" stamp, when the API provides one.
    source_last_updated: str | None = None
    dropped_codes: set[str] = field(default_factory=set)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _resolve(code: str, allowed: set[str]) -> str | None:
    """Map an upstream entity code to a registry ISO3, or ``None`` to drop it."""
    code = IMF_CODE_FIXES.get(code, code).upper()
    if code in allowed:
        return code
    if f"AGG_{code}" in allowed:  # World Bank aggregates are stored as AGG_<code>
        return f"AGG_{code}"
    return None


def _dedupe(rows: Iterable[Row]) -> list[Row]:
    """Sort and keep the first value per (iso3, year)."""
    seen: dict[tuple[str, int], Row] = {}
    for row in rows:
        seen.setdefault((row.iso3, row.year), row)
    return sorted(seen.values())


# --------------------------------------------------------------- World Bank


def fetch_worldbank(
    spec: SeriesSpec,
    client: HttpClient,
    allowed: set[str],
    *,
    end_year: int | None = None,
    per_page: int = 20_000,
) -> FetchResult:
    """All countries, all years, for one WDI indicator (paginated)."""
    last = end_year or datetime.now(UTC).year
    base = (
        f"{WORLD_BANK_BASE}/country/all/indicator/{spec.code}"
        f"?format=json&per_page={per_page}&date={WB_START_YEAR}:{last}"
    )
    rows: list[Row] = []
    dropped: set[str] = set()
    last_updated: str | None = None
    page, pages = 1, 1
    while page <= pages:
        payload: Any = client.get_json(f"{base}&page={page}")
        if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
            message = payload[0].get("message") if isinstance(payload, list) and payload else None
            raise FetchError(f"World Bank {spec.code}: unexpected payload ({message or payload!r})")
        header, records = payload[0], payload[1]
        pages = int(header.get("pages", 1))
        last_updated = header.get("lastupdated") or last_updated
        for record in records:
            value = record.get("value")
            code = (record.get("countryiso3code") or "").strip()
            if value is None or not code:
                continue
            iso3 = _resolve(code, allowed)
            if iso3 is None:
                dropped.add(code)
                continue
            rows.append(Row(iso3, int(record["date"]), float(value)))
        page += 1
    return FetchResult(spec, base, _dedupe(rows), _now(), last_updated, dropped)


# ---------------------------------------------------------------------- IMF


def fetch_imf(
    spec: SeriesSpec,
    client: HttpClient,
    allowed: set[str],
    *,
    vintage_year: int | None = None,
) -> FetchResult:
    """One WEO series for every economy from the IMF DataMapper API.

    The API returns history and projections together without marking which is
    which. Following the WEO convention, years before ``vintage_year`` (the
    year of the fetch by default) are treated as history and the rest as
    projections; ``spec.imf_part`` selects which half is kept.
    """
    vintage = vintage_year or datetime.now(UTC).year
    url = f"{IMF_BASE}/{spec.code}"
    payload: Any = client.get_json(url)
    try:
        by_country: dict[str, dict[str, Any]] = payload["values"][spec.code]
    except (KeyError, TypeError) as exc:
        raise FetchError(f"IMF {spec.code}: unexpected payload shape") from exc

    rows: list[Row] = []
    dropped: set[str] = set()
    for code, by_year in by_country.items():
        iso3 = _resolve(code, allowed)
        if iso3 is None:
            dropped.add(code)
            continue
        for year_text, value in by_year.items():
            if value is None:
                continue
            year = int(year_text)
            is_projection = year >= vintage
            if spec.imf_part == "history" and is_projection:
                continue
            if spec.imf_part == "projection" and not is_projection:
                continue
            rows.append(Row(iso3, year, float(value)))
    return FetchResult(spec, url, _dedupe(rows), _now(), f"WEO vintage {vintage}", dropped)


# --------------------------------------------------------------------- OWID


def fetch_owid(spec: SeriesSpec, client: HttpClient, allowed: set[str]) -> FetchResult:
    """An Our World in Data grapher chart, via its CSV export."""
    url = f"{OWID_BASE}/{spec.code}.csv?v=1&csvType=full&useColumnShortNames=true"
    text = client.get_text(url)
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header or len(header) < 4 or header[1].lower() != "code":
        raise FetchError(f"OWID {spec.code}: unexpected header {header!r}")
    rows: list[Row] = []
    dropped: set[str] = set()
    for record in reader:
        if len(record) < 4 or not record[3].strip():
            continue
        code = record[1].strip()
        if code == "OWID_WRL":
            code = "WLD"
        iso3 = _resolve(code, allowed) if code else None
        if iso3 is None:
            dropped.add(code or record[0])
            continue
        rows.append(Row(iso3, int(record[2]), float(record[3])))
    return FetchResult(spec, url, _dedupe(rows), _now(), None, dropped)


def fetch(spec: SeriesSpec, client: HttpClient, allowed: set[str]) -> FetchResult:
    """Dispatch to the connector for ``spec.source``."""
    if spec.source == "worldbank":
        return fetch_worldbank(spec, client, allowed)
    if spec.source == "imf":
        return fetch_imf(spec, client, allowed)
    if spec.source == "owid":
        return fetch_owid(spec, client, allowed)
    raise ValueError(f"unknown source {spec.source!r}")  # pragma: no cover - Literal-guarded
