"""ETL orchestration: read sources, derive, validate, load."""

from __future__ import annotations

import logging
from pathlib import Path

from realgrowth.etl import derive, warehouse
from realgrowth.etl.quality import QualityReport, build_report
from realgrowth.etl.registry import CountryRegistry
from realgrowth.etl.sources import SOURCES, indicator
from realgrowth.etl.transform import Issue, Observation, group_series, load_source

__all__ = ["StrictModeError", "run_etl"]

logger = logging.getLogger(__name__)


class StrictModeError(RuntimeError):
    """Raised in strict mode when the run produced a *fatal* data-quality issue."""


#: Issue kinds that indicate a genuine defect (a raw label the registry cannot
#: resolve, or two rows silently colliding on the same country-year). These
#: fail a strict build because they mean data is being dropped or shadowed
#: without anyone deciding that on purpose.
#:
#: ``out_of_range`` and ``implausible_growth`` are deliberately excluded: they
#: are the plausibility filters in realgrowth.etl.derive and
#: realgrowth.etl.transform doing their job on data that is known to contain
#: upstream imputation artefacts (see the ETL package docstring). Those are
#: expected, counted, and published via the quality report and series flags,
#: not defects to fail a build over.
FATAL_ISSUE_KINDS = frozenset({"unresolved_entity", "duplicate_entity"})


def run_etl(
    raw_dir: str | Path,
    reference_csv: str | Path,
    db_path: str | Path,
    *,
    strict: bool = False,
) -> QualityReport:
    """Build the warehouse from scratch and return the quality report.

    The database is always rebuilt rather than migrated: it is a derived
    artefact, so a clean rebuild is both simpler and guaranteed reproducible.
    """
    raw = Path(raw_dir)
    target = Path(db_path)
    registry = CountryRegistry.from_csv(reference_csv)
    logger.info(
        "registry loaded: %d countries, %d aggregates",
        len(registry.countries),
        len(registry.aggregates),
    )

    observations: list[Observation] = []
    issues: list[Issue] = []

    for spec in SOURCES:
        meta = indicator(spec.indicator_id)
        rows, source_issues = load_source(raw, spec, registry, meta)
        observations.extend(rows)
        issues.extend(source_issues)
        logger.info(
            "%-21s %6d observations from %s (%d issues)",
            spec.indicator_id,
            len(rows),
            spec.filename,
            len(source_issues),
        )

    series = group_series(observations)
    derived, derived_issues, flags = derive.derive_all(series)
    observations.extend(derived)
    issues.extend(derived_issues)
    logger.info(
        "derived %d observations (%d issues, %d series flags)",
        len(derived),
        len(derived_issues),
        len(flags),
    )

    report = build_report(observations, issues, registry, flags)

    if strict:
        fatal_counts = {
            kind: count for kind, count in report.issue_counts.items() if kind in FATAL_ISSUE_KINDS
        }
        if fatal_counts:
            raise StrictModeError(
                "fatal data-quality issue(s), "
                + ", ".join(f"{kind}={count}" for kind, count in fatal_counts.items())
            )

    if target.exists():
        target.unlink()
    for suffix in ("-wal", "-shm"):
        stale = target.with_name(target.name + suffix)
        if stale.exists():
            stale.unlink()

    connection = warehouse.connect(target)
    try:
        with connection:
            warehouse.create_schema(connection)
            warehouse.insert_countries(connection, registry)
            warehouse.insert_indicators(connection)
            warehouse.insert_observations(connection, observations)
            warehouse.insert_series_flags(connection, flags)
            warehouse.create_indexes(connection)
            warehouse.refresh_indicator_ranges(connection)
            warehouse.set_metadata(
                connection,
                [
                    ("schema_version", str(warehouse.SCHEMA_VERSION)),
                    ("built_at", warehouse.utc_now_iso()),
                    ("observation_count", str(len(observations))),
                    ("quality_report", report.to_json()),
                ],
            )
        connection.execute("VACUUM")
        connection.execute("ANALYZE")
    finally:
        connection.close()

    logger.info("wrote %s (%d observations)", target, len(observations))
    return report
