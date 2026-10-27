"""Tests for the balance sheet pillar, using invented, hand-checkable numbers."""

import numpy as np
import pandas as pd
import pytest

from scorecard.balance_sheet import (
    altman_z_double_prime, company_metrics, interest_cover, net_debt_to_ebitda, score, z_zone,
)

YEAR = pd.to_datetime(["2025-12-31"])


def make_company(**items):
    income_items = {"Operating Income", "Reconciled Depreciation", "Interest Expense"}
    income = pd.DataFrame({YEAR[0]: {k: v for k, v in items.items() if k in income_items}})
    balance = pd.DataFrame({YEAR[0]: {k: v for k, v in items.items() if k not in income_items}})
    return income, balance


def test_metrics_by_hand():
    income, balance = make_company(**{
        "Operating Income": 150, "Reconciled Depreciation": 50, "Interest Expense": 30,
        "Total Debt": 500, "Cash Cash Equivalents And Short Term Investments": 100,
        "Total Assets": 1000, "Stockholders Equity": 400,
        "Current Assets": 300, "Current Liabilities": 200,
        "Total Liabilities Net Minority Interest": 600, "Retained Earnings": 250,
    })
    m = company_metrics(income, balance)
    assert m["net_debt_to_ebitda"] == pytest.approx(400 / 200)   # 2.0x
    assert m["interest_cover"] == pytest.approx(5.0)             # 150 / 30
    assert m["equity_ratio"] == pytest.approx(0.4)
    # Z'' = 6.56*0.1 + 3.26*0.25 + 6.72*0.15 + 1.05*(400/600)
    assert m["altman_z"] == pytest.approx(0.656 + 0.815 + 1.008 + 0.7)
    assert m["altman_zone"] == "safe"


def test_net_cash_gives_negative_leverage():
    assert net_debt_to_ebitda(-100, 200) == pytest.approx(-0.5)


def test_debt_with_no_ebitda_is_worst_possible():
    assert net_debt_to_ebitda(500, -10) == np.inf


def test_interest_sign_does_not_matter():
    assert interest_cover(100, -20) == interest_cover(100, 20) == pytest.approx(5.0)


def test_loss_making_company_has_negative_cover():
    assert interest_cover(-50, 25) == pytest.approx(-2.0)


def test_zones():
    assert z_zone(3.0) == "safe" and z_zone(2.0) == "grey" and z_zone(0.5) == "distress"


def test_low_debt_ranks_best():
    metrics = pd.DataFrame(
        {"net_debt_to_ebitda": [0.5, 2.0, np.inf], "interest_cover": [20, 5, -1], "equity_ratio": [0.5, 0.3, 0.1]},
        index=["Safe", "Average", "Stretched"],
    )
    result = score(metrics)
    assert list(result.index) == ["Safe", "Average", "Stretched"]
    assert result.loc["Safe", "balance_sheet_score"] == 100.0
