"""Score every company in data/universe.csv and save the results.

Usage:
    python run.py              # uses cached data where available
    python run.py --refresh    # re-downloads everything from Yahoo
"""

import sys

import numpy as np
import pandas as pd

from scorecard import balance_sheet, earnings_quality, profitability
from scorecard.data import fetch_universe, load_universe
from scorecard.scoring import assign_peer_groups

PILLARS = {
    "profitability_score": profitability,
    "balance_sheet_score": balance_sheet,
    "earnings_quality_score": earnings_quality,
}

# The original five, shown in detail at the end so changes are easy to follow
WATCHLIST = ["Rolls-Royce", "Diageo", "Tesco", "Burberry", "Ocado"]


def fmt_pct(s: pd.Series) -> pd.Series:
    return s.map(lambda x: "n/a" if pd.isna(x) else ("n/m" if np.isinf(x) else f"{x * 100:.1f}"))


def main(refresh: bool = False) -> None:
    print("Loading company data...")
    statements, info = fetch_universe(load_universe(), refresh=refresh)
    peers = assign_peer_groups(info)

    results = {}
    for score_col, pillar in PILLARS.items():
        rows = {
            name: pillar.company_metrics(s["income"], s["balance"], s["cashflow"])
            for name, s in statements.items()
        }
        res = pillar.score(pd.DataFrame.from_dict(rows, orient="index"), peers)
        res.insert(0, "peer_group", peers)
        res.to_csv(f"outputs/{score_col.replace('_score', '')}.csv")
        results[score_col] = res

    overall = pd.DataFrame({col: res[col] for col, res in results.items()})
    overall["overall_score"] = overall.mean(axis=1).round(1)
    overall = info[["ticker", "sector"]].join(overall).sort_values("overall_score", ascending=False)
    overall.insert(0, "rank", range(1, len(overall) + 1))
    overall.to_csv("outputs/overall.csv")

    view = overall.rename(columns={
        "profitability_score": "Profit", "balance_sheet_score": "Balance",
        "earnings_quality_score": "Earnings", "overall_score": "Overall",
    }).drop(columns=["ticker"])
    pd.set_option("display.width", 200)
    print(f"\nTop 15 of {len(view)}\n")
    print(view.head(15).to_string())
    print("\nBottom 10\n")
    print(view.tail(10).to_string())

    p = results["profitability_score"].loc[WATCHLIST]
    print("\nWatchlist: profitability detail (margins ranked within peer group)\n")
    print(pd.DataFrame({
        "Peer group": p["peer_group"],
        "Gross margin %": fmt_pct(p["gross_margin"]), "Gross rank": p["gross_margin_rank"].round(0),
        "Op margin %": fmt_pct(p["operating_margin"]), "Op rank": p["operating_margin_rank"].round(0),
        "ROCE %": fmt_pct(p["roce"]), "ROCE rank": p["roce_rank"].round(0),
        "Profit score": p["profitability_score"],
    }).to_string())
    print("\nWatchlist: overall\n")
    print(view.loc[WATCHLIST].to_string())
    print("\nFull results saved to outputs/")


if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv)
