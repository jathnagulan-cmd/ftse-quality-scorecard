"""Tests for valuation, currency handling and point-in-time data."""

import numpy as np
import pandas as pd
import pytest

from scorecard.engine import as_published
from scorecard.prices import market_cap
from scorecard.valuation import company_metrics, score

YEARS = pd.to_datetime(["2024-12-31", "2025-12-31"])


def frame(rows: dict) -> pd.DataFrame:
    return pd.DataFrame(rows, index=YEARS).T[YEARS[::-1]]


def make(ebit=(80, 120), ocf=(100, 140), capex=(-20, -20), debt=300, cash=100, ni=(50, 70)):
    income = frame({"Operating Income": list(ebit), "Net Income": list(ni)})
    balance = frame({"Total Debt": [debt, debt], "Cash Cash Equivalents And Short Term Investments": [cash, cash]})
    cashflow = frame({"Operating Cash Flow": list(ocf), "Capital Expenditure": list(capex)})
    return income, balance, cashflow


def test_metrics_by_hand():
    m = company_metrics(*make(), market_cap=1800)
    # EV = 1800 + (300 - 100) = 2000; average EBIT = 100; average FCF = (80 + 120) / 2 = 100
    assert m["enterprise_value"] == pytest.approx(2000)
    assert m["ev_to_ebit"] == pytest.approx(20.0)
    assert m["fcf_yield"] == pytest.approx(0.05)
    assert m["pe_latest"] == pytest.approx(1800 / 70)


def test_no_average_profit_is_most_expensive():
    assert company_metrics(*make(ebit=(-50, 10)), market_cap=1000)["ev_to_ebit"] == np.inf


def test_cheaper_company_scores_higher():
    metrics = pd.DataFrame({"ev_to_ebit": [8.0, 20.0], "fcf_yield": [0.08, 0.03]}, index=["Cheap", "Dear"])
    assert score(metrics).index[0] == "Cheap"


def test_market_cap_converts_pence_and_currencies():
    dates = pd.to_datetime(["2026-01-02"])
    close = pd.DataFrame({"XYZ.L": [250.0], "GBPUSD=X": [1.25], "GBPEUR=X": [1.20]}, index=dates)
    prices = {"close": close}
    when = pd.Timestamp("2026-01-05")  # a weekend-ish later date uses the last price
    # 250p x 1,000 shares = £2,500
    assert market_cap("XYZ.L", 1000, "GBp", "GBP", prices, when) == pytest.approx(2500)
    # ...which is $3,125 for a company reporting in dollars
    assert market_cap("XYZ.L", 1000, "GBp", "USD", prices, when) == pytest.approx(3125)


def test_point_in_time_hides_unpublished_results():
    s = {"income": frame({"Operating Income": [1, 2]})}
    # 2025 results (year end 31 Dec) aren't public until about end of April 2026
    assert list(as_published(s, pd.Timestamp("2026-03-01"))["income"].columns) == [YEARS[0]]
    assert len(as_published(s, pd.Timestamp("2026-06-01"))["income"].columns) == 2
