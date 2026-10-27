"""ETL orchestration: read snapshots, derive, validate, load, attach models."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from realgrowth.etl import artifacts, derive, warehouse
from realgrowth.etl.quality import QualityReport, build_report
from realgrowth.etl.registry import CountryRegistry
from realgrowth.etl.sources import API_INDICATORS, SOURCES, indicator
from realgrowth.etl.transform import (
    Issue,
    Observation,
    group_series,
    load_api_source,
    load_source,
)

__all__ = ["StrictModeError", "run_etl"]

logger = logging.getLogger(__name__)

#: Sub-directory of ``raw_dir`` holding the API snapshot.
API_SUBDIR = "api"


class StrictModeError(RuntimeError):
    """Raised in strict mode when the run produced a *fatal* data-quality issue."""


#: Issue kinds that indicate a genuine defect: a label or code the registry
#: cannot resolve, two rows silently colliding on the same country-year, or a
#: snapshot file that is missing altogether. These fail a strict build because
#: they mean data is being dropped or shadowed without anyone deciding so.
#:
#: ``out_of_range`` and ``implausible_growth`` are deliberately excluded: they
#: are the plausibility filters doing their job on data known to contain
#: upstream imputation artefacts. Those are expected, counted, and published via
#: the quality report and series flags, not defects to fail a build over.
FATAL_ISSUE_KINDS = frozenset({"unresolved_entity", "duplicate_entity", "missing_source"})


def run_etl(
    raw_dir: str | Path,
    reference_csv: str | Path,
    db_path: str | Path,
    *,
    strict: bool = False,
    models_dir: str | Path | None = None,
) -> QualityReport:
    """Build the warehouse from scratch and return the quality report.

    ``raw_dir`` holds the legacy wide CSVs and an ``api/`` sub-directory with
    the ingest snapshot. ``models_dir`` (optional) holds offline model
    artefacts; without it the warehouse simply has no forecasts.

    The database is always rebuilt rather than migrated: it is a derived
    artefact, so a clean rebuild is both simpler and guaranteed reproducible.
    """
    raw = Path(raw_dir)
    api_dir = raw / API_SUBDIR
    target = Path(db_path)
    registry = CountryRegistry.from_csv(reference_csv)
    logger.info(
        "registry loaded: %d countries, %d aggregates",
        len(registry.countries),
        len(registry.aggregates),
    )

    observations: list[Observation] = []
    issues: list[Issue] = []

    for indicator_id in API_INDICATORS:
        rows, source_issues = load_api_source(api_dir, registry, indicator(indicator_id))
        observations.extend(rows)
        issues.extend(source_issues)
        logger.info(
            "%-24s %6d observations from api/ (%d issues)",
            indicator_id,
            len(rows),
            len(source_issues),
        )

    for spec in SOURCES:
        meta = indicator(spec.indicator_id)
        rows, source_issues = load_source(raw, spec, registry, meta)
        observations.extend(rows)
        issues.extend(source_issues)
        logger.info(
            "%-24s %6d observations from %s (%d issues)",
            spec.indicator_id,
            len(rows),
            spec.filename,
            len(source_issues),
        )

    series = group_series(observations)
    imputed_cells = artifacts.load_imputation_labels(
        Path(models_dir) if models_dir is not None else None
    )
    derived, derived_issues, flags = derive.derive_all(series, imputed_cells)
    observations.extend(derived)
    issues.extend(derived_issues)
    logger.info(
        "derived %d observations (%d issues, %d series flags, %d imputed wage cells excluded)",
        len(derived),
        len(derived_issues),
        len(flags),
        len(imputed_cells),
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

    manifest_path = api_dir / "manifest.json"
    snapshot_manifest = (
        manifest_path.read_text(encoding="utf-8") if manifest_path.is_file() else "{}"
    )

    connection = warehouse.connect(target)
    try:
        with connection:
            warehouse.create_schema(connection)
            warehouse.insert_countries(connection, registry)
            warehouse.insert_indicators(connection)
            warehouse.insert_observations(connection, observations)
            warehouse.insert_series_flags(connection, flags)
            model_summary = artifacts.load_all(
                connection,
                api_dir=api_dir,
                models_dir=Path(models_dir) if models_dir is not None else None,
            )
            warehouse.create_indexes(connection)
            warehouse.refresh_indicator_ranges(connection)
            warehouse.set_metadata(
                connection,
                [
                    ("schema_version", str(warehouse.SCHEMA_VERSION)),
                    ("built_at", warehouse.utc_now_iso()),
                    ("observation_count", str(len(observations))),
                    ("quality_report", report.to_json()),
                    ("snapshot_manifest", snapshot_manifest),
                    ("model_artifacts", json.dumps(model_summary.as_dict())),
                ],
            )
        connection.execute("VACUUM")
        connection.execute("ANALYZE")
    finally:
        connection.close()

    logger.info("wrote %s (%d observations)", target, len(observations))
    return report
