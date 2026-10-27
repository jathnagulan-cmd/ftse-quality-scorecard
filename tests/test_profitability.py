"""Tests for the profitability pillar, using small invented statements.

The numbers here are made up so the expected answers can be worked out by hand.
They are not real company data.
"""

import numpy as np
import pandas as pd
import pytest

from scorecard.profitability import company_metrics, margin_trend, score

YEARS = pd.to_datetime(["2023-12-31", "2024-12-31", "2025-12-31"])


def make_company(revenue, gross, ebit, assets, cur_liab, ebit_label="EBIT"):
    # Yahoo returns newest year first, so we do the same here
    cols = YEARS[::-1]
    income = pd.DataFrame(
        {c: [r, g, e] for c, r, g, e in zip(cols, revenue[::-1], gross[::-1], ebit[::-1])},
        index=["Total Revenue", "Gross Profit", ebit_label],
    )
    balance = pd.DataFrame(
        {c: [a, l] for c, a, l in zip(cols, assets[::-1], cur_liab[::-1])},
        index=["Total Assets", "Current Liabilities"],
    )
    return income, balance


def test_metrics_by_hand():
    # Latest year: revenue 1000, gross 400, EBIT 150, capital employed 1200 - 200 = 1000
    income, balance = make_company(
        revenue=[800, 900, 1000], gross=[300, 350, 400], ebit=[80, 117, 150],
        assets=[1000, 1100, 1200], cur_liab=[200, 200, 200],
    )
    m = company_metrics(income, balance)
    assert m["roce"] == pytest.approx(0.15)
    assert m["operating_margin"] == pytest.approx(0.15)
    assert m["gross_margin"] == pytest.approx(0.40)
    # Margins 10% -> 13% -> 15%: up 5pp over 2 years = 2.5pp a year
    assert m["margin_trend"] == pytest.approx(0.025)


def test_falls_back_to_operating_income_label():
    income, balance = make_company(
        revenue=[100, 100, 100], gross=[50, 50, 50], ebit=[10, 10, 10],
        assets=[200, 200, 200], cur_liab=[100, 100, 100], ebit_label="Operating Income",
    )
    assert company_metrics(income, balance)["roce"] == pytest.approx(0.10)


def test_negative_capital_employed_gives_nan_not_nonsense():
    income, balance = make_company(
        revenue=[100, 100, 100], gross=[50, 50, 50], ebit=[10, 10, 10],
        assets=[100, 100, 100], cur_liab=[150, 150, 150],
    )
    assert np.isnan(company_metrics(income, balance)["roce"])


def test_margin_trend_needs_two_years():
    assert np.isnan(margin_trend(pd.Series([0.1])))


def test_best_company_ranks_first():
    metrics = pd.DataFrame(
        {
            "roce": [0.25, 0.10, 0.02],
            "operating_margin": [0.20, 0.08, 0.01],
            "gross_margin": [0.60, 0.30, 0.10],
            "margin_trend": [0.01, 0.00, -0.02],
        },
        index=["Strong", "Middling", "Weak"],
    )
    result = score(metrics)
    assert list(result.index) == ["Strong", "Middling", "Weak"]
    assert result.loc["Strong", "profitability_score"] == 100.0
