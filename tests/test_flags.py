"""Tests for red flags and the shortlist."""

import numpy as np
import pandas as pd

from scorecard.flags import company_flags, shortlist


def series(**kw):
    return pd.Series(kw, dtype=float)


P_OK = series(roce=0.15, margin_trend=0.0, margin_stability=0.02, years_of_data=4)
B_OK = series(net_debt_to_ebitda=1.5, interest_cover=10, equity_ratio=0.4)
E_OK = series(cash_conversion=0.9, accrual_ratio=0.0, receivables_gap=0.0)
V_OK = series(ev_to_ebit=15, pe_latest=18)


def test_clean_company_has_no_red_flags():
    assert company_flags(P_OK, B_OK, E_OK, V_OK, "Packaged Foods")["red_flags"] == []


def test_debt_flags_respect_regulated_utilities():
    b = series(net_debt_to_ebitda=5.0, interest_cover=4, equity_ratio=0.3)
    assert any("High debt" in f for f in company_flags(P_OK, b, E_OK, V_OK, "Apparel Retail")["red_flags"])
    assert not company_flags(P_OK, b, E_OK, V_OK, "Utilities - Regulated Water")["red_flags"]


def test_cyclical_industry_gets_a_caution_note():
    notes = company_flags(P_OK, B_OK, E_OK, V_OK, "Airlines")["notes"]
    assert any("Cyclical" in n for n in notes)


def test_no_profit_flags_are_raised():
    e = series(cash_conversion=-np.inf, accrual_ratio=0.0, receivables_gap=0.0)
    v = series(ev_to_ebit=np.inf, pe_latest=np.nan)
    red = company_flags(P_OK, B_OK, e, v, "Software")["red_flags"]
    assert len(red) == 2


def test_shortlist_rules():
    overall = pd.DataFrame(
        {"quality_score": [80, 80, 50, 80], "valuation_score": [60, 20, 90, 60]},
        index=["Good and fair", "Good but dear", "Cheap but weak", "Good but flagged"],
    )
    flags = {n: {"red_flags": [], "strengths": [], "notes": []} for n in overall.index}
    flags["Good but flagged"]["red_flags"] = ["a", "b"]
    assert list(shortlist(overall, flags).index) == ["Good and fair"]
