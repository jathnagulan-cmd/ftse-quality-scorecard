"""Shared helpers for reading line items out of financial statements."""

from __future__ import annotations

import numpy as np
import pandas as pd

# Yahoo labels the same line item differently across companies and over time,
# so for each item we try a list of names in order of preference.
ROW_NAMES = {
    # Income statement
    "revenue": ["Total Revenue", "Operating Revenue"],
    "gross_profit": ["Gross Profit"],
    # Operating Income first: Yahoo's "EBIT" line is rebuilt from pre-tax profit
    # plus interest, so it can include non-operating items (e.g. hedge gains).
    "ebit": ["Operating Income", "EBIT"],
    "depreciation": ["Reconciled Depreciation", "Depreciation And Amortization"],
    "interest_expense": ["Interest Expense", "Interest Expense Non Operating"],
    # Balance sheet
    "total_assets": ["Total Assets"],
    "current_assets": ["Current Assets", "Total Current Assets"],
    "current_liabilities": ["Current Liabilities", "Total Current Liabilities"],
    "total_liabilities": ["Total Liabilities Net Minority Interest", "Total Liabilities"],
    "equity": ["Stockholders Equity", "Total Equity Gross Minority Interest"],
    "retained_earnings": ["Retained Earnings"],
    # Total Debt on Yahoo includes lease liabilities, which is what we want
    # under IFRS 16: a 20-year store lease is debt in all but name.
    "total_debt": ["Total Debt"],
    "cash": ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"],
}


def get_row(statement: pd.DataFrame, item: str) -> pd.Series:
    """Pull one line item from a statement, oldest year first. NaN if missing."""
    for name in ROW_NAMES[item]:
        if name in statement.index:
            row = pd.to_numeric(statement.loc[name], errors="coerce")
            return row.sort_index()
    return pd.Series(np.nan, index=sorted(statement.columns))


def latest_value(statement: pd.DataFrame, item: str) -> float:
    """Most recent non-missing value of a line item."""
    s = get_row(statement, item).dropna()
    return float(s.iloc[-1]) if len(s) else np.nan


def safe_divide(a: pd.Series, b: pd.Series) -> pd.Series:
    """Divide, but return NaN where the denominator is zero or negative.

    A negative capital base or negative revenue makes the ratio meaningless,
    so we'd rather have a gap than a misleading number.
    """
    b = b.where(b > 0)
    return a / b
