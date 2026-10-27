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
    "receivables": ["Accounts Receivable", "Receivables"],
    # Cash flow statement
    "operating_cash_flow": ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"],
    # The profit figure the cash flow statement starts from, so the two match
    "net_income_cf": ["Net Income From Continuing Operations", "Net Income"],
    # Interest paid that the company chose to classify as operating. Some put
    # it under financing instead (IFRS allows both), so we add it back to put
    # every company's operating cash flow on the same pre-interest basis.
    "interest_paid_in_ocf": ["Interest Paid Cfo"],
    "interest_paid_in_financing": ["Interest Paid Cff"],
    # The cash flow statement's reconciling line that removes profit or loss
    # on selling a business (negative for a gain). Adding it to net income
    # strips the one-off out.
    "disposal_adjustment": ["Gain Loss On Sale Of Business"],
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
