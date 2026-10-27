"""Share prices, exchange rates and market values.

Prices are cached in data/cache/prices.csv and refreshed when older than a
day. Two series are kept for every ticker:

  close     the actual traded price, used for valuation on a given date
  adjusted  the price adjusted for dividends and splits, used for measuring
            total returns in the backtest (a share that pays a 5% dividend
            and stays flat has still returned 5%)
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from scorecard.data import CACHE_DIR

PRICE_FILE = CACHE_DIR / "prices.csv"
FX_TICKERS = {"USD": "GBPUSD=X", "EUR": "GBPEUR=X"}  # units of currency per £1
HISTORY_START = "2020-01-01"


def load_prices(tickers: list[str], refresh: bool = False) -> dict[str, pd.DataFrame]:
    """Daily close and adjusted close for every ticker plus FX rates."""
    wanted = sorted(set(tickers) | set(FX_TICKERS.values()))
    if PRICE_FILE.exists() and not refresh:
        cached = pd.read_csv(PRICE_FILE, header=[0, 1], index_col=0, parse_dates=True)
        fresh = date.fromtimestamp(PRICE_FILE.stat().st_mtime) >= date.today()
        have = set(cached["close"].columns)
        if fresh and set(wanted) <= have:
            return {"close": cached["close"], "adjusted": cached["adjusted"]}

    import yfinance as yf

    raw = yf.download(wanted, start=HISTORY_START, auto_adjust=False, progress=False, threads=True)
    frames = {"close": raw["Close"], "adjusted": raw["Adj Close"]}
    PRICE_FILE.parent.mkdir(parents=True, exist_ok=True)
    pd.concat(frames, axis=1).to_csv(PRICE_FILE)
    return frames


def price_on(series: pd.Series, when: pd.Timestamp) -> float:
    """Last available price on or before a date (markets close at weekends)."""
    s = series.loc[:when].dropna()
    return float(s.iloc[-1]) if len(s) else np.nan


def to_gbp_factor(currency: str, fx: pd.DataFrame, when: pd.Timestamp) -> float:
    """Multiply an amount in `currency` by this to get pounds."""
    if currency == "GBP":
        return 1.0
    if currency == "GBp":  # pence
        return 0.01
    if currency in FX_TICKERS:
        return 1.0 / price_on(fx[FX_TICKERS[currency]], when)
    return np.nan


def market_cap(
    ticker: str,
    shares: float,
    quote_currency: str,
    reporting_currency: str,
    prices: dict[str, pd.DataFrame],
    when: pd.Timestamp,
) -> float:
    """Market value of the equity, in the currency the accounts are reported in.

    Price x shares gives the value in the quote currency (usually pence).
    That is converted to pounds, then into the reporting currency, so it can
    be compared directly with profits and debt from the accounts.
    """
    close = prices["close"]
    if ticker not in close or not shares > 0:
        return np.nan
    value_gbp = price_on(close[ticker], when) * shares * to_gbp_factor(quote_currency, close, when)
    return value_gbp / to_gbp_factor(reporting_currency, close, when)
