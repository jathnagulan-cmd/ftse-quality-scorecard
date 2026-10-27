"""Fetching annual financial statements.

This is the only file that talks to the internet. Everything else works on
plain pandas DataFrames, which means the maths can be tested without a
connection, and the data source can be swapped later (e.g. for Companies
House filings) without touching the scoring logic.
"""

from __future__ import annotations

import pandas as pd

# The five starter companies. ".L" means listed on the London Stock Exchange.
DEFAULT_TICKERS = {
    "DGE.L": "Diageo",
    "RR.L": "Rolls-Royce",
    "TSCO.L": "Tesco",
    "BRBY.L": "Burberry",
    "OCDO.L": "Ocado",
}


def fetch_statements(ticker: str) -> dict[str, pd.DataFrame]:
    """Return the annual income statement, balance sheet and cash flow for one company.

    Yahoo Finance returns each statement as a table where rows are line items
    (e.g. "Total Revenue") and columns are financial year-end dates.
    """
    import yfinance as yf  # imported here so tests don't need a connection

    t = yf.Ticker(ticker)
    income = t.income_stmt
    balance = t.balance_sheet
    cashflow = t.cashflow
    for name, df in [("income", income), ("balance", balance), ("cash flow", cashflow)]:
        if df is None or df.empty:
            raise ValueError(f"No annual {name} statement returned for {ticker}")
    return {"income": income, "balance": balance, "cashflow": cashflow}


def fetch_all(tickers: dict[str, str] | None = None) -> dict[str, dict[str, pd.DataFrame]]:
    """Fetch statements for every ticker, skipping (and reporting) any that fail."""
    tickers = tickers or DEFAULT_TICKERS
    out = {}
    for ticker, name in tickers.items():
        try:
            out[ticker] = fetch_statements(ticker)
            print(f"  fetched {name} ({ticker})")
        except Exception as e:  # one bad ticker shouldn't kill the run
            print(f"  skipped {name} ({ticker}): {e}")
    return out
