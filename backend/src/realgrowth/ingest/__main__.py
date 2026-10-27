"""Command-line entry point: ``python -m realgrowth.ingest``.

Fetches every catalogued series (or a subset with ``--only``) from its public
API and writes a snapshot to ``data/raw/api/``. Run it, review the diff of the
CSVs and ``manifest.json``, commit, and rebuild the warehouse. The scheduled
GitHub Actions workflow (``.github/workflows/refresh-data.yml``) does exactly
that every week.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

from realgrowth.ingest.catalog import ALL_SERIES
from realgrowth.ingest.connectors import fetch
from realgrowth.ingest.http import FetchError, HttpClient
from realgrowth.ingest.snapshot import verify, write_manifest, write_series

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUT = REPO_ROOT / "data" / "raw" / "api"
DEFAULT_REFERENCE = REPO_ROOT / "data" / "reference" / "countries.csv"

logger = logging.getLogger("realgrowth.ingest")


def allowed_codes(reference_csv: Path) -> set[str]:
    with reference_csv.open(newline="", encoding="utf-8") as handle:
        return {row["iso3"].strip().upper() for row in csv.DictReader(handle)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m realgrowth.ingest",
        description="Fetch public-API series into data/raw/api/ snapshots.",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--only", nargs="*", default=None, help="series ids to fetch")
    parser.add_argument("--verify", action="store_true", help="only verify checksums")
    parser.add_argument("--list", action="store_true", help="list catalogued series")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s", stream=sys.stderr)

    if args.list:
        for spec in ALL_SERIES:
            print(f"{spec.id:<26} {spec.source:<10} {spec.code}")
        return 0

    if args.verify:
        problems = verify(args.out)
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        print("snapshot ok" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0

    wanted = set(args.only) if args.only else None
    specs = [s for s in ALL_SERIES if wanted is None or s.id in wanted]
    if wanted and len(specs) != len(wanted):
        unknown = wanted - {s.id for s in specs}
        print(f"error: unknown series: {', '.join(sorted(unknown))}", file=sys.stderr)
        return 2

    allowed = allowed_codes(args.reference)
    client = HttpClient()
    entries = []
    failures = 0
    for spec in specs:
        try:
            result = fetch(spec, client, allowed)
        except FetchError as exc:
            # One unavailable source must not block refreshing the others; the
            # previous snapshot for this series is simply kept.
            failures += 1
            logger.error("%s: %s (keeping previous snapshot)", spec.id, exc)
            continue
        entry = write_series(args.out, result)
        entries.append(entry)
        logger.info(
            "%-26s %6d rows  %3d countries  %s-%s",
            spec.id,
            entry.rows,
            entry.countries,
            entry.min_year,
            entry.max_year,
        )
    write_manifest(args.out, entries)
    print(f"fetched {len(entries)} series, {failures} failure(s) -> {args.out}")
    return 1 if failures and not entries else 0


if __name__ == "__main__":
    raise SystemExit(main())
