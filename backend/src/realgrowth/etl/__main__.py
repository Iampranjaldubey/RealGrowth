"""Command-line entry point: ``python -m realgrowth.etl``."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from realgrowth.etl.pipeline import StrictModeError, run_etl

#: repo_root/backend/src/realgrowth/etl/__main__.py -> repo_root
REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_RAW = REPO_ROOT / "data" / "raw"
DEFAULT_REFERENCE = REPO_ROOT / "data" / "reference" / "countries.csv"
DEFAULT_DB = REPO_ROOT / "data" / "realgrowth.db"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m realgrowth.etl",
        description="Build the RealGrowth SQLite warehouse from the raw CSV sources.",
    )
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW, help="raw CSV directory")
    parser.add_argument(
        "--reference", type=Path, default=DEFAULT_REFERENCE, help="country registry CSV"
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_DB, help="SQLite file to write")
    parser.add_argument(
        "--report", type=Path, default=None, help="also write the quality report as JSON"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero if any data-quality issue is found (used in CI)",
    )
    parser.add_argument("--quiet", action="store_true", help="only print the summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)-7s %(message)s",
        stream=sys.stderr,
    )

    if not args.raw_dir.is_dir():
        print(f"error: raw directory not found: {args.raw_dir}", file=sys.stderr)
        return 2
    if not args.reference.is_file():
        print(f"error: reference CSV not found: {args.reference}", file=sys.stderr)
        return 2

    try:
        report = run_etl(args.raw_dir, args.reference, args.output, strict=args.strict)
    except StrictModeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("\n".join(report.summary_lines()))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report.to_json() + "\n", encoding="utf-8")
        print(f"\nreport written to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
