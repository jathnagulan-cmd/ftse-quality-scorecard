"""The scoring engine: one function that scores every company as of a date.

Both the live scorecard (run.py) and the backtest (backtest.py) call this,
so the backtest tests exactly the model you actually use.

Point-in-time rule: when scoring as of a date, only accounts that would have
been PUBLISHED by then are used. UK-listed companies must publish annual
results within four months of their year end, so a year is usable from four
months after its year-end date. Without this, a backtest quietly uses
information nobody had at the time (look-ahead bias) and looks far better
than reality.
"""

from __future__ import annotations

import pandas as pd

from scorecard import balance_sheet, earnings_quality, profitability, valuation
from scorecard.prices import market_cap
from scorecard.scoring import assign_peer_groups
from scorecard.statements import get_row, latest_value

REPORTING_LAG = pd.DateOffset(months=4)

QUALITY_PILLARS = {
    "profitability_score": profitability,
    "balance_sheet_score": balance_sheet,
    "earnings_quality_score": earnings_quality,
}


def as_published(statements: dict[str, pd.DataFrame], as_of: pd.Timestamp) -> dict[str, pd.DataFrame]:
    """Keep only financial years whose results were public by `as_of`."""
    cutoff = as_of - REPORTING_LAG
    out = {}
    for name, df in statements.items():
        cols = [c for c in df.columns if pd.Timestamp(c) <= cutoff]
        out[name] = df[cols]
    return out


def score_universe(
    statements: dict[str, dict[str, pd.DataFrame]],
    info: pd.DataFrame,
    prices: dict[str, pd.DataFrame],
    as_of: pd.Timestamp | None = None,
    min_years: int = 2,
) -> dict[str, pd.DataFrame]:
    """Score every company. Returns one table per pillar plus 'overall'.

    Companies with fewer than `min_years` of published accounts are skipped.
    """
    as_of = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.today().normalize()

    usable = {}
    for name, s in statements.items():
        s = as_published(s, as_of)
        if s["income"].shape[1] and get_years(s) >= min_years:
            usable[name] = s
    info = info.loc[list(usable)]
    peers = assign_peer_groups(info)

    results = {}
    for col, pillar in QUALITY_PILLARS.items():
        rows = {n: pillar.company_metrics(s["income"], s["balance"], s["cashflow"]) for n, s in usable.items()}
        res = pillar.score(pd.DataFrame.from_dict(rows, orient="index"), peers)
        res.insert(0, "peer_group", peers)
        results[col] = res

    rows = {}
    for n, s in usable.items():
        meta = info.loc[n]
        mcap = market_cap(
            meta["ticker"], latest_value(s["balance"], "shares"),
            meta.get("currency") or "GBp", meta.get("financialCurrency") or "GBP", prices, as_of,
        )
        rows[n] = valuation.company_metrics(s["income"], s["balance"], s["cashflow"], mcap)
    res = valuation.score(pd.DataFrame.from_dict(rows, orient="index"))
    res.insert(0, "peer_group", peers)
    results["valuation_score"] = res

    overall = pd.DataFrame({col: r[col] for col, r in results.items()})
    overall["quality_score"] = overall[list(QUALITY_PILLARS)].mean(axis=1).round(1)
    # Overall: the three quality pillars and valuation, equally weighted,
    # so quality carries 75% of the weight and price 25%.
    overall["overall_score"] = overall[list(QUALITY_PILLARS) + ["valuation_score"]].mean(axis=1).round(1)
    overall = info[["ticker", "sector"]].join(overall).sort_values("overall_score", ascending=False)
    overall.insert(0, "rank", range(1, len(overall) + 1))
    results["overall"] = overall
    return results


def get_years(s: dict[str, pd.DataFrame]) -> int:
    """Number of years with a reported revenue figure."""
    return int(get_row(s["income"], "revenue").notna().sum())
