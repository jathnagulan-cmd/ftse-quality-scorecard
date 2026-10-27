"""Share price series for the dashboard charts: 1D, 1W, 1M, 1Y and 5Y.

Each range is a list of [unix time in ms, price] pairs, small enough to embed
in the dashboard page:

  1D  five-minute prices for the latest trading session
  1W  thirty-minute prices for the last five sessions
  1M  daily closes for the last month
  1Y  daily closes for the last year
  5Y  weekly closes for the last five years

Prices are actual traded prices (not dividend-adjusted), in the quote
currency: pence for most London shares, dollars for a few. The page is a
snapshot from when it was last built, refreshed after each market close.
"""

from __future__ import annotations

import pandas as pd

from scorecard.prices import load_prices


def _pairs(s: pd.Series, decimals: int = 2) -> list[list]:
    s = s.dropna()
    return [[int(t.timestamp() * 1000), round(float(v), decimals)] for t, v in s.items()]


def price_history(tickers: list[str], refresh: bool = False) -> dict[str, dict[str, list]]:
    import yfinance as yf

    daily = load_prices(tickers, refresh=refresh)["close"]
    intraday = yf.download(tickers, period="5d", interval="5m", auto_adjust=False, progress=False, threads=True)["Close"]
    if isinstance(intraday, pd.Series):
        intraday = intraday.to_frame(tickers[0])

    out = {}
    for t in tickers:
        series = {}
        if t in intraday:
            s = intraday[t].dropna()
            if len(s):
                last_day = s.index[-1].date()
                series["1D"] = _pairs(s[[ts.date() == last_day for ts in s.index]])
                series["1W"] = _pairs(s.resample("30min").last().dropna())
        if t in daily:
            d = daily[t].dropna()
            if len(d):
                end = d.index[-1]
                series["1M"] = _pairs(d[d.index > end - pd.DateOffset(months=1)])
                series["1Y"] = _pairs(d[d.index > end - pd.DateOffset(years=1)])
                series["5Y"] = _pairs(d[d.index > end - pd.DateOffset(years=5)].resample("W-FRI").last())
        out[t] = series
    return out
