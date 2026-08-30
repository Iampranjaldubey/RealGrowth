"""Parsing and reshaping: wide vendor CSV -> tidy observations."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from realgrowth.etl.registry import CountryRegistry
from realgrowth.etl.sources import YEAR_HEADER, Indicator, SourceSpec

#: Tokens vendors use to mean "no observation".
NULL_TOKENS = frozenset({"", "..", "...", "-", "–", "n/a", "na", "nan", "null", "none"})


class Observation(NamedTuple):
    """One measurement: a single (indicator, country, year) cell."""

    indicator_id: str
    iso3: str
    year: int
    value: float


@dataclass(frozen=True, slots=True)
class SeriesFlag:
    """A durable caveat attached to one country's series for one indicator.

    Unlike an :class:`Issue` (a note about a single ETL run), a flag is stored in
    the warehouse and served with the data so the UI can warn the reader that a
    particular line is not trustworthy.
    """

    indicator_id: str
    iso3: str
    flag: str
    detail: str


@dataclass(frozen=True, slots=True)
class Issue:
    """A data-quality finding, surfaced in the ETL report instead of a stack trace."""

    kind: str
    indicator_id: str
    detail: str
    entity: str | None = None
    year: int | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "indicator": self.indicator_id,
            "entity": self.entity,
            "year": self.year,
            "detail": self.detail,
        }


def parse_number(raw: str | None) -> float | None:
    """Parse a vendor numeric cell, returning ``None`` for missing values.

    Handles the three encodings present in the raw data: plain floats, thousands
    separators from scraped HTML tables (``"909,121,500"``), and percent signs.
    """
    if raw is None:
        return None
    text = raw.strip()
    if text.casefold() in NULL_TOKENS:
        return None
    text = text.replace(",", "").replace("%", "").replace("$", "").strip()
    if text.startswith("(") and text.endswith(")"):  # accounting negatives
        text = "-" + text[1:-1]
    if not text or text.casefold() in NULL_TOKENS:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    # Reject non-finite values outright; they poison aggregations downstream.
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return value


@dataclass(frozen=True, slots=True)
class WideTable:
    """A parsed wide CSV: header labels plus the rows we care about."""

    name_column: str
    code_column: str | None
    year_columns: tuple[str, ...]
    rows: tuple[dict[str, str], ...]

    @property
    def years(self) -> tuple[int, ...]:
        return tuple(sorted(int(y) for y in self.year_columns))


def read_wide_csv(path: str | Path, spec: SourceSpec) -> WideTable:
    """Read a wide CSV, locating columns by header label rather than position."""
    file_path = Path(path)
    with file_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or ())
        if spec.name_column not in headers:
            raise ValueError(
                f"{file_path.name}: expected a {spec.name_column!r} column, "
                f"found {headers[:6]}"
            )
        if spec.code_column is not None and spec.code_column not in headers:
            raise ValueError(
                f"{file_path.name}: expected a {spec.code_column!r} column, found {headers[:6]}"
            )
        year_columns = tuple(
            h
            for h in headers
            if h and YEAR_HEADER.match(h.strip()) and h not in spec.ignore_columns
        )
        if not year_columns:
            raise ValueError(f"{file_path.name}: no four-digit year columns in {headers[:8]}")
        rows = tuple(dict(row) for row in reader)
    return WideTable(
        name_column=spec.name_column,
        code_column=spec.code_column,
        year_columns=year_columns,
        rows=rows,
    )


def extract(
    table: WideTable,
    spec: SourceSpec,
    registry: CountryRegistry,
    meta: Indicator,
) -> tuple[list[Observation], list[Issue]]:
    """Reshape a wide table into observations, validating as we go.

    Rules applied, each of which the previous implementation got wrong somewhere:

    * an entity we cannot resolve to an ISO code is reported, not silently kept
      under its raw string;
    * two raw rows resolving to the same country is a conflict, reported rather
      than last-write-wins;
    * values outside the indicator's physically possible range are dropped;
    * missing cells produce no row at all, so ``NULL`` never has to be encoded
      as ``0.0``.
    """
    observations: list[Observation] = []
    issues: list[Issue] = []
    seen: dict[tuple[str, int], float] = {}

    for row in table.rows:
        raw_name = (row.get(table.name_column) or "").strip()
        if not raw_name:
            continue

        iso3: str | None = None
        if table.code_column:
            code = (row.get(table.code_column) or "").strip().upper()
            if code and code in registry:
                iso3 = code
        if iso3 is None:
            iso3 = registry.resolve(raw_name)
        if iso3 is None:
            issues.append(
                Issue(
                    kind="unresolved_entity",
                    indicator_id=meta.id,
                    entity=raw_name,
                    detail=(
                        f"{raw_name!r} is not in data/reference/countries.csv; "
                        "add it as a country or an alias"
                    ),
                )
            )
            continue

        for column in table.year_columns:
            value = parse_number(row.get(column))
            if value is None:
                continue
            year = int(column)
            low, high = meta.valid_range
            if not low <= value <= high:
                issues.append(
                    Issue(
                        kind="out_of_range",
                        indicator_id=meta.id,
                        entity=iso3,
                        year=year,
                        detail=f"{value!r} outside valid range [{low}, {high}]; dropped",
                    )
                )
                continue

            key = (iso3, year)
            previous = seen.get(key)
            if previous is not None:
                if previous != value:
                    issues.append(
                        Issue(
                            kind="duplicate_entity",
                            indicator_id=meta.id,
                            entity=iso3,
                            year=year,
                            detail=(
                                f"{raw_name!r} resolves to {iso3}, which already has "
                                f"{previous!r} for {year}; kept the first value"
                            ),
                        )
                    )
                continue
            seen[key] = value
            observations.append(Observation(meta.id, iso3, year, value))

    return observations, issues


def load_source(
    raw_dir: str | Path,
    spec: SourceSpec,
    registry: CountryRegistry,
    meta: Indicator,
) -> tuple[list[Observation], list[Issue]]:
    """Read and reshape a single source file."""
    table = read_wide_csv(Path(raw_dir) / spec.filename, spec)
    return extract(table, spec, registry, meta)


def group_series(observations: Iterator[Observation] | list[Observation]) -> dict[
    tuple[str, str], dict[int, float]
]:
    """Index observations as ``(indicator_id, iso3) -> {year: value}``."""
    series: dict[tuple[str, str], dict[int, float]] = {}
    for obs in observations:
        series.setdefault((obs.indicator_id, obs.iso3), {})[obs.year] = obs.value
    return series
