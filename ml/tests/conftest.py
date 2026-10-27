"""Synthetic panels with known structure, so ML tests are exact and fast."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from realgrowth_ml.data import Panel, panel_from_frames

YEARS = list(range(1975, 2026))


def synthetic_panel(n_countries: int = 30, seed: int = 0) -> Panel:
    """AR(1) inflation around country-specific means, plus correlated macro series."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_countries):
        iso3 = f"C{i:02d}"
        mean = rng.uniform(1.0, 15.0)
        x = mean
        money = mean + 3.0
        fx = 1.0
        for year in YEARS:
            money = 0.5 * money + 0.5 * (mean + 3.0) + rng.normal(0, 2.0)
            x = 0.3 * x + 0.7 * mean + 0.4 * (money - mean - 3.0) + rng.normal(0, 1.0)
            fx *= 1.0 + max(-0.5, rng.normal(x / 200.0, 0.05))
            for indicator_id, value in (
                ("inflation_rate", x),
                ("broad_money_growth", money),
                ("exchange_rate", fx),
                ("gdp_growth", rng.normal(3.0, 2.0)),
                ("gdp_per_capita_ppp", 5_000.0 * (1 + i)),
                ("trade_openness", 60.0),
            ):
                rows.append((indicator_id, iso3, year, float(value)))
    obs = pd.DataFrame(rows, columns=["indicator_id", "iso3", "year", "value"])
    countries = pd.DataFrame(
        {
            "iso3": [f"C{i:02d}" for i in range(n_countries)],
            "name": [f"Country {i}" for i in range(n_countries)],
            "region": ["A" if i % 2 else "B" for i in range(n_countries)],
            "is_aggregate": False,
        }
    ).set_index("iso3")
    return panel_from_frames(obs, countries)


@pytest.fixture(scope="session")
def panel() -> Panel:
    return synthetic_panel()
