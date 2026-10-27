"""Pillar 1: Profitability.

The question this pillar answers: does the business earn good returns on the
money tied up in it, and is that getting better or worse?

Metrics (all calculated from annual reports):

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
        better sign than a decaying 15% one.

Scoring: each metric is converted to a percentile rank within the group of
companies being compared (100 = best; with five companies the worst gets
20), then the four ranks are
averaged into a pillar score out of 100. This is a *relative* score: it says
how a company compares with its peers, not whether it is good in absolute
terms. With only five companies the ranks are coarse; they get more
meaningful as the universe grows.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from scorecard.scoring import rank_and_score
from scorecard.statements import get_row, safe_divide


def margin_trend(margins: pd.Series) -> float:
    """Average yearly change in operating margin (percentage points per year)."""
    m = margins.dropna()
    if len(m) < 2:
        return np.nan
    return (m.iloc[-1] - m.iloc[0]) / (len(m) - 1)


def company_metrics(income: pd.DataFrame, balance: pd.DataFrame, cashflow: pd.DataFrame | None = None) -> dict[str, float]:
    """Calculate the four profitability metrics for one company.

    Level metrics use the most recent year; the trend uses every year available.
    """
    revenue = get_row(income, "revenue")
    gross_profit = get_row(income, "gross_profit")
    ebit = get_row(income, "ebit")
    capital_employed = get_row(balance, "total_assets") - get_row(balance, "current_liabilities")

    roce = safe_divide(ebit, capital_employed)
    op_margin = safe_divide(ebit, revenue)
    gross_margin = safe_divide(gross_profit, revenue)

    def latest(s: pd.Series) -> float:
        s = s.dropna()
        return float(s.iloc[-1]) if len(s) else np.nan

    return {
        "roce": latest(roce),
        "operating_margin": latest(op_margin),
        "gross_margin": latest(gross_margin),
        "margin_trend": margin_trend(op_margin),
    }


HIGHER_IS_BETTER = {
    "roce": True,
    "operating_margin": True,
    "gross_margin": True,
    "margin_trend": True,
}


def score(metrics: pd.DataFrame) -> pd.DataFrame:
    """Percentile-rank the metrics and average them into a pillar score /100."""
    return rank_and_score(metrics, HIGHER_IS_BETTER, "profitability_score")
