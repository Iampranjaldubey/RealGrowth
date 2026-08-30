"""Canonical country registry.

The seven raw sources in this project disagree about how to name a country. The
same place appears as ``Korea, Rep.``, ``South Korea``, ``Congo, Dem. Rep.``,
``Democratic Republic Of Congo``, ``Turkiye``, ``Turkey``, ``Viet Nam`` and so
on, and only one source ships ISO codes. Joining those strings directly (which
the previous implementation did) silently loses countries: the world map failed
to colour the United States because the map's ``United States of America`` never
matched the data's ``United States``.

This module resolves every raw label to an ISO-3166-1 alpha-3 code using a
curated registry (``data/reference/countries.csv``), so every downstream join is
on a stable key. Resolution is intentionally strict: an unrecognised label is
reported rather than silently dropped or fuzzy-matched onto the wrong country.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

_WHITESPACE = re.compile(r"\s+")

#: Codes we mint ourselves for World Bank / OWID aggregates, which have no ISO code.
AGGREGATE_PREFIX = "AGG_"


def normalise_name(raw: str) -> str:
    """Fold a raw country label into a lookup key.

    Collapses runs of whitespace and case-folds. Deliberately conservative: no
    punctuation stripping or fuzzy matching, because ``Congo`` vs
    ``Democratic Republic of Congo`` are different countries and a loose matcher
    would merge them.
    """
    return _WHITESPACE.sub(" ", raw.strip()).casefold()


class UnknownCountryError(KeyError):
    """Raised when a raw label cannot be resolved to a registry entry."""


@dataclass(frozen=True, slots=True)
class Country:
    """A registry entry: either a real country or a named aggregate."""

    iso3: str
    name: str
    region: str | None
    is_aggregate: bool

    def __post_init__(self) -> None:
        if not self.iso3:
            raise ValueError("iso3 must not be empty")
        if not self.name:
            raise ValueError(f"{self.iso3}: name must not be empty")


class CountryRegistry:
    """Immutable name -> ISO3 resolver backed by the curated reference CSV."""

    def __init__(self, countries: Iterable[Country], aliases: Mapping[str, str]) -> None:
        self._by_iso3: dict[str, Country] = {}
        for country in countries:
            if country.iso3 in self._by_iso3:
                raise ValueError(f"duplicate iso3 in registry: {country.iso3}")
            self._by_iso3[country.iso3] = country

        self._lookup: dict[str, str] = {}
        for country in self._by_iso3.values():
            self._lookup[normalise_name(country.name)] = country.iso3
            # An ISO code is always an acceptable label for itself.
            self._lookup[normalise_name(country.iso3)] = country.iso3

        for alias, iso3 in aliases.items():
            if iso3 not in self._by_iso3:
                raise ValueError(f"alias {alias!r} points at unknown iso3 {iso3!r}")
            key = normalise_name(alias)
            existing = self._lookup.get(key)
            if existing is not None and existing != iso3:
                raise ValueError(
                    f"alias {alias!r} is ambiguous: maps to both {existing} and {iso3}"
                )
            self._lookup[key] = iso3

    # ------------------------------------------------------------------ loading

    @classmethod
    def from_csv(cls, path: str | Path) -> CountryRegistry:
        """Load the registry from ``data/reference/countries.csv``."""
        countries: list[Country] = []
        aliases: dict[str, str] = {}
        with Path(path).open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            required = {"iso3", "name", "region", "is_aggregate", "aliases"}
            missing = required - set(reader.fieldnames or ())
            if missing:
                raise ValueError(f"{path}: reference CSV missing columns {sorted(missing)}")
            for row in reader:
                iso3 = (row["iso3"] or "").strip()
                if not iso3:
                    continue
                region = (row["region"] or "").strip() or None
                countries.append(
                    Country(
                        iso3=iso3,
                        name=(row["name"] or "").strip(),
                        region=region,
                        is_aggregate=(row["is_aggregate"] or "0").strip() == "1",
                    )
                )
                for alias in (row["aliases"] or "").split("|"):
                    alias = alias.strip()
                    if alias:
                        aliases[alias] = iso3
        return cls(countries, aliases)

    # ------------------------------------------------------------- resolution

    def resolve(self, raw_name: str) -> str | None:
        """Return the ISO3 for ``raw_name``, or ``None`` if unrecognised."""
        return self._lookup.get(normalise_name(raw_name))

    def require(self, raw_name: str) -> str:
        """Like :meth:`resolve` but raises :class:`UnknownCountryError`."""
        iso3 = self.resolve(raw_name)
        if iso3 is None:
            raise UnknownCountryError(raw_name)
        return iso3

    # ---------------------------------------------------------------- access

    def __getitem__(self, iso3: str) -> Country:
        try:
            return self._by_iso3[iso3]
        except KeyError as exc:
            raise UnknownCountryError(iso3) from exc

    def __contains__(self, iso3: object) -> bool:
        return iso3 in self._by_iso3

    def __len__(self) -> int:
        return len(self._by_iso3)

    def __iter__(self) -> Iterator[Country]:
        return iter(sorted(self._by_iso3.values(), key=lambda c: c.name))

    @property
    def countries(self) -> tuple[Country, ...]:
        """Real countries only, excluding aggregates."""
        return tuple(c for c in self if not c.is_aggregate)

    @property
    def aggregates(self) -> tuple[Country, ...]:
        """Named aggregates (regions, income groups, lending groups, World)."""
        return tuple(c for c in self if c.is_aggregate)

    @property
    def regions(self) -> tuple[str, ...]:
        return tuple(sorted({c.region for c in self.countries if c.region}))
