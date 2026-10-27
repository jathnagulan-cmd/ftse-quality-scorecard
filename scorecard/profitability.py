"""Pillar 1: Profitability.

The question this pillar answers: does the business earn good returns on the
money tied up in it, and is that getting better or worse?

Metrics (all calculated from annual reports):

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

# Yahoo labels the same line item differently across companies and over time,
# so for each item we try a list of names in order of preference.
ROW_NAMES = {
    "revenue": ["Total Revenue", "Operating Revenue"],
    "gross_profit": ["Gross Profit"],
    "ebit": ["EBIT", "Operating Income"],
    "total_assets": ["Total Assets"],
    "current_liabilities": ["Current Liabilities", "Total Current Liabilities"],
}


def get_row(statement: pd.DataFrame, item: str) -> pd.Series:
    """Pull one line item from a statement, oldest year first. NaN if missing."""
    for name in ROW_NAMES[item]:
        if name in statement.index:
            row = pd.to_numeric(statement.loc[name], errors="coerce")
            return row.sort_index()
    return pd.Series(np.nan, index=sorted(statement.columns))


def safe_divide(a: pd.Series, b: pd.Series) -> pd.Series:
    """Divide, but return NaN where the denominator is zero or negative.

    A negative capital base or negative revenue makes the ratio meaningless,
    so we'd rather have a gap than a misleading number.
    """
    b = b.where(b > 0)
    return a / b


def margin_trend(margins: pd.Series) -> float:
    """Average yearly change in operating margin (percentage points per year)."""
    m = margins.dropna()
    if len(m) < 2:
        return np.nan
    return (m.iloc[-1] - m.iloc[0]) / (len(m) - 1)


def company_metrics(income: pd.DataFrame, balance: pd.DataFrame) -> dict[str, float]:
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


def score(metrics: pd.DataFrame) -> pd.DataFrame:
    """Turn raw metrics into percentile ranks and a pillar score out of 100.

    `metrics` has one row per company and one column per metric.
    Higher is better for every profitability metric, so no flipping needed.
    A company missing a metric is scored on the ones it has.
    """
    ranks = metrics.rank(pct=True, method="average") * 100
    ranks.columns = [f"{c}_rank" for c in ranks.columns]
    result = metrics.join(ranks)
    result["profitability_score"] = ranks.mean(axis=1, skipna=True).round(1)
    return result.sort_values("profitability_score", ascending=False)
