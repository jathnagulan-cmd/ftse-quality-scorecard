"""Which companies can actually be bought on Trading 212.

Trading 212 publishes its full instrument list only through its API, which
needs an API key from your own account. check_trading212.py fetches the list
once and saves the result to data/trading212.csv (company tickers and a
yes/no, nothing secret). Everything else reads that file.

If the file doesn't exist, every company is "unchecked" and nothing is
excluded: the tool never guesses availability.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
AVAILABILITY_FILE = ROOT / "data" / "trading212.csv"
LONDON_CURRENCIES = {"GBX", "GBP", "USD", "EUR"}  # a few FTSE shares trade in USD/EUR on the LSE


def symbol_variants(yahoo_ticker: str) -> set[str]:
    """Possible spellings of a London ticker: 'BT-A.L' -> {'BT-A', 'BT.A', 'BTA', 'BT/A'}."""
    base = yahoo_ticker.removesuffix(".L").upper()
    return {base, base.replace("-", "."), base.replace("-", ""), base.replace("-", "/")}


def match_instruments(universe: pd.DataFrame, instruments: list[dict]) -> pd.DataFrame:
    """Match each company to a Trading 212 stock instrument.

    Trading 212 tickers look like "TSCOl_EQ" for London listings (the
    lowercase "l" marks the London exchange); shortName holds the plain symbol.
    A company matches if a STOCK instrument has its symbol as shortName, or a
    ticker of the form <SYMBOL>l_EQ, in a currency used on the LSE.
    """
    by_short, by_ticker = {}, {}
    for ins in instruments:
        if ins.get("type") != "STOCK":
            continue
        t = str(ins.get("ticker", ""))
        if t.endswith("l_EQ"):
            by_ticker[t[: -len("l_EQ")].upper()] = ins
        if str(ins.get("currencyCode", "")).upper() in LONDON_CURRENCIES and t.endswith("l_EQ"):
            by_short[str(ins.get("shortName", "")).upper()] = ins

    rows = []
    for row in universe.itertuples():
        hit = None
        for sym in symbol_variants(row.ticker):
            hit = by_ticker.get(sym) or by_short.get(sym)
            if hit:
                break
        rows.append({
            "ticker": row.ticker, "name": row.name,
            "available": "yes" if hit else "no",
            "t212_ticker": hit.get("ticker") if hit else "",
            "t212_name": hit.get("name") if hit else "",
        })
    return pd.DataFrame(rows)


def load_availability() -> pd.Series | None:
    """yes/no by company name, or None if the check has never been run."""
    if not AVAILABILITY_FILE.exists():
        return None
    df = pd.read_csv(AVAILABILITY_FILE, keep_default_na=False)
    return df.set_index("name")["available"]
