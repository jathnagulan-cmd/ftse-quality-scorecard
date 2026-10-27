"""Fetching annual financial statements, with a local cache.

This is the only file that talks to the internet. Everything else works on
plain pandas DataFrames, which means the maths can be tested without a
connection, and the data source can be swapped later (e.g. for Companies
House filings) without touching the scoring logic.

Fetching 100 companies takes a few minutes and Yahoo rate-limits heavy use,
so each company's data is saved under data/cache/ the first time and read
from there afterwards. Delete the cache folder (or pass refresh=True) to
pull fresh numbers, e.g. after a new set of annual reports.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE_FILE = ROOT / "data" / "universe.csv"
CACHE_DIR = ROOT / "data" / "cache"
STATEMENTS = ("income", "balance", "cashflow")

# Banks, insurers, asset managers, investment trusts and property companies
# are excluded. Their accounts work differently (a bank's "debt" is its raw
# material, insurers have no gross margin, property companies are valued on
# net assets), so ROCE, margins and net debt/EBITDA mean little for them.
# They need their own scorecard with metrics like CET1 ratio or loan losses.
EXCLUDED_SECTORS = {"Financial Services", "Real Estate"}


def load_universe(path: Path = UNIVERSE_FILE) -> pd.DataFrame:
    """The list of companies to score.

    Columns: ticker, name, membership (which index), and optional
    sector / industry / financialCurrency / currency overrides (columns
    ending "_override") for when Yahoo's data is missing or wrong.
    "currency" is the quote currency (GBp = pence); "financialCurrency" is
    the currency the accounts are reported in.
    """
    return pd.read_csv(path, keep_default_na=False)


def _fetch_from_yahoo(ticker: str) -> tuple[dict[str, pd.DataFrame], dict]:
    import yfinance as yf  # imported here so tests don't need a connection

    t = yf.Ticker(ticker)
    statements = {"income": t.income_stmt, "balance": t.balance_sheet, "cashflow": t.cashflow}
    for name, df in statements.items():
        if df is None or df.empty:
            raise ValueError(f"no annual {name} statement returned")
    info = t.info or {}
    meta = {k: info.get(k) for k in ("sector", "industry", "financialCurrency", "currency")}
    return statements, meta


def _save(ticker: str, statements: dict[str, pd.DataFrame], meta: dict) -> None:
    folder = CACHE_DIR / ticker
    folder.mkdir(parents=True, exist_ok=True)
    for name, df in statements.items():
        df.to_csv(folder / f"{name}.csv")
    (folder / "meta.json").write_text(json.dumps(meta, indent=2))


def _load(ticker: str) -> tuple[dict[str, pd.DataFrame], dict] | None:
    folder = CACHE_DIR / ticker
    if not (folder / "meta.json").exists():
        return None
    statements = {}
    for name in STATEMENTS:
        df = pd.read_csv(folder / f"{name}.csv", index_col=0)
        df.columns = pd.to_datetime(df.columns)
        statements[name] = df
    return statements, json.loads((folder / "meta.json").read_text())


def fetch_company(ticker: str, refresh: bool = False) -> tuple[dict[str, pd.DataFrame], dict]:
    """Statements and sector info for one company, from cache if available."""
    if not refresh:
        cached = _load(ticker)
        if cached:
            return cached
    statements, meta = _fetch_from_yahoo(ticker)
    _save(ticker, statements, meta)
    time.sleep(0.5)  # be polite to Yahoo
    return statements, meta


def fetch_universe(universe: pd.DataFrame, refresh: bool = False) -> tuple[dict, pd.DataFrame]:
    """Fetch every company, drop excluded sectors, and report what was skipped.

    Returns (statements keyed by company name, info table indexed by name).
    """
    statements, info_rows, skipped = {}, [], []
    for row in universe.itertuples():
        try:
            s, meta = fetch_company(row.ticker, refresh)
        except Exception as e:  # one bad ticker shouldn't kill the run
            skipped.append(f"{row.name} ({row.ticker}): fetch failed: {e}")
            continue
        # Manual overrides in universe.csv fill gaps where Yahoo returns no sector
        for field in ("sector", "industry", "financialCurrency", "currency"):
            override = getattr(row, f"{field}_override", None)
            if isinstance(override, str) and override:
                meta[field] = override
        if meta.get("sector") in EXCLUDED_SECTORS:
            skipped.append(f"{row.name}: excluded sector ({meta['sector']})")
            continue
        statements[row.name] = s
        info_rows.append({"name": row.name, "ticker": row.ticker, "membership": row.membership, **meta})
    info = pd.DataFrame(info_rows).set_index("name")
    print(f"  {len(statements)} companies scored, {len(skipped)} skipped")
    for s in skipped:
        print(f"    - {s}")
    return statements, info
