"""Country resolution — the join key everything else depends on."""

from __future__ import annotations

import csv

import pytest

from realgrowth.etl.registry import (
    Country,
    CountryRegistry,
    UnknownCountryError,
    normalise_name,
)
from realgrowth.etl.sources import SOURCES


class TestNormaliseName:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("United States", "united states"),
            ("  United   States  ", "united states"),
            ("UNITED STATES", "united states"),
            ("Côte d'Ivoire", "côte d'ivoire"),
            ("Korea,\tRep.", "korea, rep."),
        ],
    )
    def test_folds_case_and_whitespace(self, raw: str, expected: str) -> None:
        assert normalise_name(raw) == expected

    def test_does_not_strip_punctuation(self) -> None:
        """Congo and DR Congo differ only by words, so nothing may be discarded."""
        assert normalise_name("Congo") != normalise_name("Democratic Republic of Congo")


class TestResolution:
    def test_resolves_canonical_name(self, tiny_registry: CountryRegistry) -> None:
        assert tiny_registry.resolve("United States") == "USA"

    def test_resolves_alias(self, tiny_registry: CountryRegistry) -> None:
        assert tiny_registry.resolve("Korea, Rep.") == "KOR"

    def test_resolves_iso_code_as_its_own_label(self, tiny_registry: CountryRegistry) -> None:
        assert tiny_registry.resolve("ind") == "IND"

    def test_is_case_and_space_insensitive(self, tiny_registry: CountryRegistry) -> None:
        assert tiny_registry.resolve("  united states of america ") == "USA"

    def test_unknown_returns_none(self, tiny_registry: CountryRegistry) -> None:
        assert tiny_registry.resolve("Atlantis") is None

    def test_require_raises_for_unknown(self, tiny_registry: CountryRegistry) -> None:
        with pytest.raises(UnknownCountryError):
            tiny_registry.require("Atlantis")

    def test_no_fuzzy_matching(self, tiny_registry: CountryRegistry) -> None:
        """A near-miss must fail loudly rather than land on the wrong country."""
        assert tiny_registry.resolve("United State") is None
        assert tiny_registry.resolve("Kore") is None


class TestConstructionValidation:
    def test_rejects_duplicate_iso3(self) -> None:
        with pytest.raises(ValueError, match="duplicate iso3"):
            CountryRegistry(
                [
                    Country("USA", "United States", "North America", False),
                    Country("USA", "America", "North America", False),
                ],
                {},
            )

    def test_rejects_alias_pointing_at_unknown_country(self) -> None:
        with pytest.raises(ValueError, match="unknown iso3"):
            CountryRegistry([Country("USA", "United States", None, False)], {"Burgundy": "BGD"})

    def test_rejects_ambiguous_alias(self) -> None:
        with pytest.raises(ValueError, match="ambiguous"):
            CountryRegistry(
                [
                    Country("COG", "Congo", None, False),
                    Country("COD", "DR Congo", None, False),
                ],
                {"Congo": "COD"},
            )

    def test_rejects_empty_name(self) -> None:
        with pytest.raises(ValueError, match="name must not be empty"):
            Country("USA", "", None, False)


class TestPartitioning:
    def test_separates_countries_from_aggregates(self, tiny_registry: CountryRegistry) -> None:
        assert [c.iso3 for c in tiny_registry.aggregates] == ["WLD"]
        assert "WLD" not in {c.iso3 for c in tiny_registry.countries}

    def test_regions_are_sorted_and_deduplicated(self, tiny_registry: CountryRegistry) -> None:
        assert tiny_registry.regions == (
            "East Asia & Pacific",
            "North America",
            "South Asia",
        )


class TestRealRegistry:
    """Guards the curated reference file against regressions."""

    def test_every_country_has_a_region(self, real_registry: CountryRegistry) -> None:
        missing = [c.iso3 for c in real_registry.countries if not c.region]
        assert missing == [], f"countries without a region: {missing}"

    def test_aggregates_are_flagged_not_treated_as_countries(
        self, real_registry: CountryRegistry
    ) -> None:
        """World Bank groupings must never appear in a list of countries."""
        for label in ("World", "European Union", "OECD members", "IDA only"):
            iso3 = real_registry.resolve(label)
            assert iso3 is not None, label
            assert real_registry[iso3].is_aggregate, label

    def test_known_naming_variants_converge(self, real_registry: CountryRegistry) -> None:
        """The specific collisions that broke the old world map."""
        groups = [
            ("United States", "USA"),
            ("Korea, Rep.", "South Korea"),
            ("Turkiye", "Turkey"),
            ("Viet Nam", "Vietnam"),
            ("Russian Federation", "Russia"),
            ("Congo, Dem. Rep.", "Democratic Republic Of Congo"),
            ("Egypt, Arab Rep.", "Egypt"),
            ("Hong Kong SAR, China", "Hong Kong (China)"),
            ("Yemen, Rep.", "Yemen"),
            ("St. Kitts And Nevis", "Saint Kitts and Nevis"),
        ]
        for left, right in groups:
            assert real_registry.resolve(left) == real_registry.resolve(right) is not None, (
                f"{left!r} and {right!r} must resolve to the same country"
            )

    def test_congos_stay_distinct(self, real_registry: CountryRegistry) -> None:
        assert real_registry.resolve("Congo") != real_registry.resolve(
            "Democratic Republic Of Congo"
        )

    def test_resolves_every_label_in_every_raw_source(self, real_registry: CountryRegistry) -> None:
        """The regression guard: no raw entity may be silently dropped.

        If a vendor renames a country in a refreshed CSV this test fails with the
        exact label to add, rather than the country quietly vanishing from the UI.
        """
        from tests.conftest import RAW_DIR

        unresolved: dict[str, list[str]] = {}
        for spec in SOURCES:
            path = RAW_DIR / spec.filename
            with path.open(newline="", encoding="utf-8-sig") as handle:
                for row in csv.DictReader(handle):
                    raw = (row.get(spec.name_column) or "").strip()
                    if raw and real_registry.resolve(raw) is None:
                        unresolved.setdefault(spec.filename, []).append(raw)
        assert unresolved == {}, f"unresolved country labels: {unresolved}"
