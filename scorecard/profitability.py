"""Pillar 1: Profitability.

The question this pillar answers: does the business earn good returns on the
money tied up in it, reliably, through good years and bad?

Metrics (all calculated from annual reports). ROCE and the two margins are
AVERAGES over every year available (usually four), not just the latest year.
A single year flatters companies at the top of their cycle: a silver miner
with record silver prices looks like a wonderful business until prices fall.
Ideally the average would cover a full cycle (7-10 years); four years is what
the free data allows.

  EBIT here means reported operating profit (see statements.py for why).

  ROCE  (Return on Capital Employed) = EBIT / (Total assets - Current liabilities)
        The headline measure. How much operating profit the business makes for
        every pound of long-term capital invested in it. Above ~15% is strong;
        below the cost of capital (~8-10%) means it is destroying value.

  Operating margin = EBIT / Revenue
        How much of each pound of sales survives as operating profit.
        Low margins aren't automatically bad (supermarkets run on ~4%), which
        is why we never judge a company on margin alone.

  Gross margin = Gross profit / Revenue
        Pricing power. A high gross margin usually means customers pay for
        the brand or the product, not just the cost of making it.

  Margin trend = change in operating margin per year over the period available
        Direction matters as much as level. An improving 8% margin can be a
        better sign than a decaying 15% one. On its own this rewards cyclical
        booms (Fresnillo's margin rose ~13 points a year with the silver
        price), which is why it is paired with stability below.

  Margin stability = standard deviation of operating margin across years
                     (percentage points; lower is better)
        How much margins swing from year to year. Quality businesses earn
        steady margins whatever the economy does; commodity producers,
        airlines and housebuilders don't. Needs at least three years.

Shown but not scored:

  Cash ROCE = Free cash flow / (Total assets - Current liabilities), averaged
        ROCE using cash instead of accounting profit (free cash flow = operating
        cash flow after interest, minus capital expenditure). Borrowed from the
        "CROIC" test in valinvest. Not scored because adding it made the
        backtest worse (see README), but it is a useful cross-check on ROCE.

Scoring: each metric is converted to a percentile rank (100 = best), then
the five ranks are averaged into a pillar score out of 100. This is a *relative* score: it says
how a company compares with its peers, not whether it is good in absolute
terms. Gross and operating margin are ranked only against peers in the
same industry (see scoring.py), because a supermarket and a luxury brand
have structurally different margins.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from scorecard.scoring import rank_and_score
from scorecard.earnings_quality import operating_cash_flows
from scorecard.statements import get_row, safe_divide


def margin_trend(margins: pd.Series) -> float:
    """Average yearly change in operating margin (percentage points per year)."""
    m = margins.dropna()
    if len(m) < 2:
        return np.nan
    return (m.iloc[-1] - m.iloc[0]) / (len(m) - 1)


def margin_stability(margins: pd.Series) -> float:
    """Standard deviation of operating margin across years. NaN with under 3 years."""
    m = margins.dropna()
    if len(m) < 3:
        return np.nan
    return float(m.std(ddof=0))


def average(s: pd.Series) -> float:
    s = s.dropna()
    return float(s.mean()) if len(s) else np.nan


def company_metrics(income: pd.DataFrame, balance: pd.DataFrame, cashflow: pd.DataFrame | None = None) -> dict[str, float]:
    """Calculate the five profitability metrics for one company.

    Levels are averaged over every year available; latest-year figures are
    kept alongside for reference but not scored.
    """
    revenue = get_row(income, "revenue")
    gross_profit = get_row(income, "gross_profit")
    ebit = get_row(income, "ebit")
    capital_employed = get_row(balance, "total_assets") - get_row(balance, "current_liabilities")

    roce = safe_divide(ebit, capital_employed)
    op_margin = safe_divide(ebit, revenue)
    gross_margin = safe_divide(gross_profit, revenue)

    cash_roce = np.nan
    if cashflow is not None:
        _, ocf_post_interest = operating_cash_flows(cashflow)
        capex = get_row(cashflow, "capex")  # reported as a negative number
        cash_roce = average(safe_divide(ocf_post_interest + capex, capital_employed))

    def latest(s: pd.Series) -> float:
        s = s.dropna()
        return float(s.iloc[-1]) if len(s) else np.nan

    return {
        "roce": average(roce),
        "operating_margin": average(op_margin),
        "gross_margin": average(gross_margin),
        "margin_trend": margin_trend(op_margin),
        "margin_stability": margin_stability(op_margin),
        "roce_latest": latest(roce),
        "operating_margin_latest": latest(op_margin),
        "years_of_data": int(op_margin.notna().sum()),
        "cash_roce": cash_roce,  # shown, not scored
    }


HIGHER_IS_BETTER = {
    "roce": True,
    "operating_margin": True,
    "gross_margin": True,
    "margin_trend": True,
    "margin_stability": False,
}


# Margins depend on the business model, so they are compared within peer
# groups. ROCE, the trend and stability mean the same in any industry, so they
# are compared across everyone. (Ranking stability within sector would defeat
# the point: every miner is volatile, so the least volatile miner would still
# score well.)
PEER_RELATIVE = ("gross_margin", "operating_margin")


def score(metrics: pd.DataFrame, peer_groups: pd.Series | None = None) -> pd.DataFrame:
    """Percentile-rank the metrics and average them into a pillar score /100."""
    return rank_and_score(metrics, HIGHER_IS_BETTER, "profitability_score", peer_groups, PEER_RELATIVE)
