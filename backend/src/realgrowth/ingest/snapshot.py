"""Snapshots: the on-disk record of what each API returned, and when.

Fetching and building are deliberately separate steps. ``python -m
realgrowth.ingest`` writes one long-format CSV per series into
``data/raw/api/`` plus a ``manifest.json``; the ETL only ever reads those files.
That gives three properties a live-API pipeline would otherwise lack:

* **reproducibility** — the warehouse, the models and every number in the docs
  are a pure function of committed files, so a rebuild next year reproduces
  today's results even after upstream revisions;
* **auditability** — the manifest records the URL, fetch time, publisher's
  update stamp, row count and SHA-256 of every file, so a diff between two
  snapshots shows exactly what the publisher revised;
* **offline builds** — deploys and CI never depend on a third-party API being up.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from realgrowth.ingest.connectors import FetchResult, Row

MANIFEST_NAME = "manifest.json"
HEADER = ("iso3", "year", "value")


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    series_id: str
    source: str
    code: str
    url: str
    fetched_at: str
    source_last_updated: str | None
    rows: int
    countries: int
    min_year: int | None
    max_year: int | None
    sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "series_id": self.series_id,
            "source": self.source,
            "code": self.code,
            "url": self.url,
            "fetched_at": self.fetched_at,
            "source_last_updated": self.source_last_updated,
            "rows": self.rows,
            "countries": self.countries,
            "min_year": self.min_year,
            "max_year": self.max_year,
            "sha256": self.sha256,
        }


def _format_value(value: float) -> str:
    # repr round-trips a float exactly; strip a trailing ".0" for readability.
    text = repr(float(value))
    return text[:-2] if text.endswith(".0") else text


def write_series(directory: Path, result: FetchResult) -> ManifestEntry:
    """Write one series as ``iso3,year,value`` and describe it for the manifest."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / result.spec.filename
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(HEADER)
        for row in result.rows:
            writer.writerow((row.iso3, row.year, _format_value(row.value)))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    years = [row.year for row in result.rows]
    return ManifestEntry(
        series_id=result.spec.id,
        source=result.spec.source,
        code=result.spec.code,
        url=result.url,
        fetched_at=result.fetched_at,
        source_last_updated=result.source_last_updated,
        rows=len(result.rows),
        countries=len({row.iso3 for row in result.rows}),
        min_year=min(years) if years else None,
        max_year=max(years) if years else None,
        sha256=digest,
    )


def read_series(path: Path) -> list[Row]:
    """Read a snapshot file back into rows."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if tuple(header or ()) != HEADER:
            raise ValueError(f"{path.name}: expected header {HEADER}, found {header}")
        return [Row(iso3, int(year), float(value)) for iso3, year, value in reader]


def read_manifest(directory: Path) -> dict[str, dict[str, Any]]:
    path = directory / MANIFEST_NAME
    if not path.is_file():
        return {}
    data: dict[str, dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))["series"]
    return data


def write_manifest(directory: Path, entries: Iterable[ManifestEntry]) -> Path:
    """Merge ``entries`` into the manifest, keeping entries for other series."""
    existing = read_manifest(directory)
    for entry in entries:
        existing[entry.series_id] = entry.as_dict()
    path = directory / MANIFEST_NAME
    payload = {"schema": 1, "series": dict(sorted(existing.items()))}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def verify(directory: Path) -> list[str]:
    """Check every manifest entry against the file on disk; return problems."""
    problems: list[str] = []
    for series_id, entry in read_manifest(directory).items():
        path = directory / f"{series_id}.csv"
        if not path.is_file():
            problems.append(f"{series_id}: file missing")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            problems.append(f"{series_id}: sha256 mismatch (file edited after fetch?)")
    return problems
