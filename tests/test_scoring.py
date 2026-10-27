"""Tests for peer groups and peer-relative ranking."""

import pandas as pd
import pytest

from scorecard.profitability import score as profitability_score
from scorecard.scoring import assign_peer_groups


def test_peer_groups_fall_back_from_industry_to_sector_to_all():
    info = pd.DataFrame(
        {
            "industry": ["Grocery", "Grocery", "Grocery", "Tobacco", "Tobacco", "Airlines"],
            "sector": ["Staples", "Staples", "Staples", "Staples", "Staples", "Transport"],
        },
        index=["G1", "G2", "G3", "T1", "T2", "A1"],
    )
    groups = assign_peer_groups(info, min_peers=3)
    assert groups["G1"] == "Industry: Grocery"
    assert groups["T1"] == "Sector: Staples"  # only 2 tobacco firms, so use the sector
    assert groups["A1"] == "All companies"   # alone in its sector too


def test_supermarket_not_penalised_for_supermarket_margins():
    # Grocer A is the best grocer but has margins far below every brand.
    metrics = pd.DataFrame(
        {
            "roce": [0.15, 0.10, 0.05, 0.12, 0.08, 0.06],
            "operating_margin": [0.05, 0.03, 0.01, 0.20, 0.15, 0.10],
            "gross_margin": [0.08, 0.06, 0.04, 0.70, 0.60, 0.50],
            "margin_trend": [0.0] * 6,
            "margin_stability": [0.01] * 6,
        },
        index=["Grocer A", "Grocer B", "Grocer C", "Brand A", "Brand B", "Brand C"],
    )
    groups = pd.Series(["Grocery"] * 3 + ["Luxury"] * 3, index=metrics.index)

    universe_wide = profitability_score(metrics)
    peer_relative = profitability_score(metrics, groups)

    # Universe-wide, the best grocer is dragged down by margins it can never match
    assert universe_wide.loc["Grocer A", "gross_margin_rank"] == pytest.approx(50.0)
    # Against other grocers, it tops both margin rankings
    assert peer_relative.loc["Grocer A", "gross_margin_rank"] == pytest.approx(100.0)
    assert peer_relative.loc["Grocer A", "operating_margin_rank"] == pytest.approx(100.0)
    # ROCE is still ranked against everyone
    assert peer_relative.loc["Grocer A", "roce_rank"] == pytest.approx(100.0)
    assert peer_relative.loc["Grocer A", "profitability_score"] > universe_wide.loc["Grocer A", "profitability_score"]
