"""Data-quality reporting.

Four of the seven raw files were produced by an upstream notebook that imputed
missing values using an ad-hoc "scale the world average by this country's average
ratio" rule, and it did so without recording which cells were invented. That
cannot be undone downstream, so the honest response is to measure and publish
coverage rather than let a dense-looking chart imply complete data.

The report this module builds is stored in the warehouse and served at
``/api/v1/meta/quality`` so the limitation is visible in the product, not buried
in a README.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from realgrowth.etl.registry import CountryRegistry
from realgrowth.etl.sources import INDICATORS
from realgrowth.etl.transform import Issue, Observation, SeriesFlag


@dataclass(slots=True)
class IndicatorCoverage:
    """How complete one indicator actually is."""

    indicator_id: str
    observations: int
    countries: int
    min_year: int | None
    max_year: int | None
    #: Observations as a share of the countries x years grid, in percent.
    density: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "indicator": self.indicator_id,
            "observations": self.observations,
            "countries": self.countries,
            "min_year": self.min_year,
            "max_year": self.max_year,
            "density_pct": round(self.density, 1),
        }


@dataclass(slots=True)
class QualityReport:
    """Aggregate ETL outcome, suitable for JSON serialisation."""

    total_observations: int = 0
    total_countries: int = 0
    total_aggregates: int = 0
    coverage: list[IndicatorCoverage] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    flags: list[SeriesFlag] = field(default_factory=list)

    @property
    def issue_counts(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for issue in self.issues:
            counts[issue.kind] += 1
        return dict(sorted(counts.items()))

    @property
    def flag_counts(self) -> dict[str, int]:
        """Flagged series per indicator, keyed ``indicator:flag``."""
        counts: dict[str, int] = defaultdict(int)
        for flag in self.flags:
            counts[f"{flag.indicator_id}:{flag.flag}"] += 1
        return dict(sorted(counts.items()))

    @property
    def unresolved_entities(self) -> list[str]:
        return sorted(
            {i.entity for i in self.issues if i.kind == "unresolved_entity" and i.entity}
        )

    def as_dict(self, *, max_issues: int = 200) -> dict[str, Any]:
        return {
            "total_observations": self.total_observations,
            "total_countries": self.total_countries,
            "total_aggregates": self.total_aggregates,
            "issue_counts": self.issue_counts,
            "flag_counts": self.flag_counts,
            "unresolved_entities": self.unresolved_entities,
            "coverage": [c.as_dict() for c in self.coverage],
            "issues": [i.as_dict() for i in self.issues[:max_issues]],
            "issues_truncated": max(0, len(self.issues) - max_issues),
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2, sort_keys=False)

    def summary_lines(self) -> list[str]:
        """Human-readable summary for the CLI."""
        lines = [
            f"observations : {self.total_observations:,}",
            f"countries    : {self.total_countries:,} (+{self.total_aggregates} aggregates)",
        ]
        for coverage in self.coverage:
            span = (
                f"{coverage.min_year}-{coverage.max_year}"
                if coverage.min_year is not None
                else "no data"
            )
            lines.append(
                f"  {coverage.indicator_id:<21} {coverage.observations:>6,} obs  "
                f"{coverage.countries:>3} countries  {span:<11} "
                f"{coverage.density:>5.1f}% dense"
            )
        if self.issue_counts:
            lines.append("issues:")
            lines.extend(f"  {kind:<19} {count:,}" for kind, count in self.issue_counts.items())
        else:
            lines.append("issues       : none")
        if self.flag_counts:
            lines.append("flagged series:")
            lines.extend(f"  {key:<34} {count:,}" for key, count in self.flag_counts.items())
        return lines


def build_report(
    observations: list[Observation],
    issues: list[Issue],
    registry: CountryRegistry,
    flags: list[SeriesFlag] | None = None,
) -> QualityReport:
    """Summarise an ETL run."""
    by_indicator: dict[str, list[Observation]] = defaultdict(list)
    for obs in observations:
        by_indicator[obs.indicator_id].append(obs)

    coverage: list[IndicatorCoverage] = []
    for indicator_id in INDICATORS:
        rows = by_indicator.get(indicator_id, [])
        if not rows:
            coverage.append(
                IndicatorCoverage(indicator_id, 0, 0, None, None, 0.0)
            )
            continue
        years = {r.year for r in rows}
        countries = {r.iso3 for r in rows}
        grid = len(years) * len(countries)
        coverage.append(
            IndicatorCoverage(
                indicator_id=indicator_id,
                observations=len(rows),
                countries=len(countries),
                min_year=min(years),
                max_year=max(years),
                density=(len(rows) / grid * 100.0) if grid else 0.0,
            )
        )

    observed = {o.iso3 for o in observations}
    return QualityReport(
        total_observations=len(observations),
        total_countries=sum(1 for c in registry.countries if c.iso3 in observed),
        total_aggregates=sum(1 for c in registry.aggregates if c.iso3 in observed),
        coverage=coverage,
        issues=issues,
        flags=list(flags or []),
    )
