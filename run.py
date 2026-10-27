"""Score every company in data/universe.csv and save the results.

Usage:
    python run.py              # uses cached data where available
    python run.py --refresh    # re-downloads statements and prices from Yahoo

Writes:
    outputs/<pillar>.csv       every metric and rank, one file per pillar
    outputs/overall.csv        ranks and pillar scores for every company
    outputs/shortlist.csv      quality businesses at sensible prices
    outputs/scorecard.json     everything above plus flags, for the dashboard
"""

import json
import sys

import numpy as np
import pandas as pd

from scorecard.data import fetch_universe, load_universe
from scorecard.engine import score_universe
from scorecard.flags import all_flags, shortlist
from scorecard.prices import load_prices

PILLAR_FILES = {
    "profitability_score": "profitability",
    "balance_sheet_score": "balance_sheet",
    "earnings_quality_score": "earnings_quality",
    "valuation_score": "valuation",
}


def _clean(x):
    """Make numbers JSON-safe: infinities become strings, NaN becomes null."""
    if isinstance(x, (float, np.floating)):
        if np.isnan(x):
            return None
        if np.isinf(x):
            return "inf" if x > 0 else "-inf"
        return round(float(x), 4)
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


def build_json(results, info, flags, short, as_of) -> dict:
    companies = []
    for name, row in results["overall"].iterrows():
        entry = {
            "name": name, "ticker": row["ticker"], "sector": row["sector"],
            "industry": info.loc[name].get("industry"), "rank": int(row["rank"]),
            "reporting_currency": info.loc[name].get("financialCurrency"),
            "scores": {k: _clean(row[k]) for k in
                       ["profitability_score", "balance_sheet_score", "earnings_quality_score",
                        "valuation_score", "quality_score", "overall_score"]},
            "metrics": {},
            "flags": flags[name],
            "shortlisted": name in short.index,
        }
        for key in PILLAR_FILES:
            r = results[key].loc[name]
            entry["metrics"].update({k: _clean(v) for k, v in r.items() if k != "peer_group" and not k.endswith("_rank") and not k.endswith("_score")})
        entry["peer_group"] = results["profitability_score"].loc[name, "peer_group"]
        companies.append(entry)
    return {"as_of": as_of.strftime("%Y-%m-%d"), "count": len(companies), "shortlist": list(short.index), "companies": companies}


def main(refresh: bool = False) -> None:
    print("Loading company data...")
    statements, info = fetch_universe(load_universe(), refresh=refresh)
    prices = load_prices(list(info["ticker"]), refresh=refresh)
    as_of = pd.Timestamp.today().normalize()

    results = score_universe(statements, info, prices, as_of)
    flags = all_flags(results, info)
    overall = results["overall"]
    short = shortlist(overall, flags)

    for key, fname in PILLAR_FILES.items():
        results[key].to_csv(f"outputs/{fname}.csv")
    overall.to_csv("outputs/overall.csv")
    short.to_csv("outputs/shortlist.csv")
    with open("outputs/scorecard.json", "w") as f:
        json.dump(build_json(results, info, flags, short, as_of), f, indent=1)

    view = overall.rename(columns={
        "profitability_score": "Profit", "balance_sheet_score": "Balance",
        "earnings_quality_score": "Earnings", "valuation_score": "Value",
        "quality_score": "Quality", "overall_score": "Overall",
    }).drop(columns=["ticker"])
    pd.set_option("display.width", 200)
    print(f"\nTop 15 of {len(view)}\n")
    print(view.head(15).to_string())

    print("\nShortlist: quality >= 60, value >= 40, at most one red flag\n")
    for name in short.index:
        f = flags[name]
        print(f"{name}  (overall {overall.loc[name, 'overall_score']}, quality {overall.loc[name, 'quality_score']}, value {overall.loc[name, 'valuation_score']})")
        for s in f["strengths"]:
            print(f"   + {s}")
        for s in f["red_flags"]:
            print(f"   ! {s}")
        for s in f["notes"]:
            print(f"   ? {s}")
    print("\nThis is a screen, not advice. Check the latest annual report and news before acting.")
    print("Full results saved to outputs/")


if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv)
