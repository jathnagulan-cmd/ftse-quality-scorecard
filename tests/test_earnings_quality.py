"""Tests for the earnings quality pillar, using invented, hand-checkable numbers."""

import numpy as np
import pandas as pd
import pytest

from scorecard.earnings_quality import (
    accrual_ratio, cash_conversion, company_metrics, growth, operating_cash_flows, score,
)

YEARS = pd.to_datetime(["2024-12-31", "2025-12-31"])


def frame(rows: dict) -> pd.DataFrame:
    """Build a statement in Yahoo's layout: line items as rows, newest year first."""
    return pd.DataFrame(rows, index=YEARS).T[YEARS[::-1]]


def test_interest_classification_is_neutralised():
    # Same underlying business, interest presented differently
    in_operating = frame({"Operating Cash Flow": [80, 80], "Interest Paid Cfo": [-20, -20]})
    in_financing = frame({"Operating Cash Flow": [100, 100], "Interest Paid Cff": [-20, -20]})
    pre_a, post_a = operating_cash_flows(in_operating)
    pre_b, post_b = operating_cash_flows(in_financing)
    assert list(pre_a) == list(pre_b) == [100, 100]
    assert list(post_a) == list(post_b) == [80, 80]


def test_metrics_by_hand():
    income = frame({
        "Total Revenue": [1000, 1100], "Operating Income": [150, 160], "Reconciled Depreciation": [50, 40],
    })
    balance = frame({"Total Assets": [900, 1100], "Accounts Receivable": [100, 121]})
    cashflow = frame({
        "Operating Cash Flow": [150, 170], "Interest Paid Cfo": [-10, -10],
        "Net Income From Continuing Operations": [100, 120],
    })
    m = company_metrics(income, balance, cashflow)
    # Pre-interest OCF 160 + 180 = 340, EBITDA 200 + 200 = 400
    assert m["cash_conversion"] == pytest.approx(0.85)
    # (120 - 170) / average(900, 1100) = -50 / 1000
    assert m["accrual_ratio"] == pytest.approx(-0.05)
    # Receivables +21%, revenue +10%
    assert m["receivables_gap"] == pytest.approx(0.11)


def test_any_loss_making_year_ranks_last_not_first():
    # Tiny summed EBITDA would otherwise give a huge "conversion" figure
    ocf = pd.Series([60.0, 140.0, 320.0])
    ebitda = pd.Series([-180.0, 50.0, 160.0])
    assert cash_conversion(ocf, ebitda) == -np.inf


def test_growth_needs_positive_base():
    assert np.isnan(growth(pd.Series([0.0, 10.0])))


def test_cash_backed_profit_ranks_best():
    metrics = pd.DataFrame(
        {"cash_conversion": [1.0, 0.8, 0.4], "accrual_ratio": [-0.05, 0.0, 0.10], "receivables_gap": [-0.02, 0.0, 0.15]},
        index=["Cash-backed", "Average", "Paper profits"],
    )
    result = score(metrics)
    assert list(result.index) == ["Cash-backed", "Average", "Paper profits"]
