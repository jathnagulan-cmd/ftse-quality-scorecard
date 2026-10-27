"""Run the scorecard on the default companies and save the results.

Usage:
    python run.py
"""

import numpy as np
import pandas as pd

from scorecard import balance_sheet, profitability
from scorecard.data import DEFAULT_TICKERS, fetch_all

PILLARS = {
    "profitability_score": profitability,
    "balance_sheet_score": balance_sheet,
}


def pct(s: pd.Series) -> pd.Series:
    return (s * 100).round(1)


def fmt_multiple(s: pd.Series) -> pd.Series:
    return s.map(lambda x: "n/a" if pd.isna(x) else ("no profit" if np.isinf(x) else f"{x:.1f}x"))


def main() -> None:
    print("Fetching annual reports...")
    statements = fetch_all(DEFAULT_TICKERS)

    results = {}
    for score_col, pillar in PILLARS.items():
        rows = {DEFAULT_TICKERS[t]: pillar.company_metrics(s["income"], s["balance"]) for t, s in statements.items()}
        results[score_col] = pillar.score(pd.DataFrame.from_dict(rows, orient="index"))
        results[score_col].to_csv(f"outputs/{score_col.replace('_score', '')}.csv")

    # Pillar 1 view
    p = results["profitability_score"]
    view = pd.DataFrame({
        "ROCE %": pct(p["roce"]), "Op margin %": pct(p["operating_margin"]),
        "Gross margin %": pct(p["gross_margin"]), "Margin trend (pp/yr)": pct(p["margin_trend"]),
        "Score /100": p["profitability_score"],
    })
    print("\nPillar 1: Profitability\n")
    print(view.to_string())

    # Pillar 2 view
    b = results["balance_sheet_score"]
    view = pd.DataFrame({
        "Net debt/EBITDA": fmt_multiple(b["net_debt_to_ebitda"]),
        "Interest cover": fmt_multiple(b["interest_cover"]),
        "Equity ratio %": pct(b["equity_ratio"]),
        "Altman Z''": b["altman_z"].round(2), "Z'' zone": b["altman_zone"],
        "Score /100": b["balance_sheet_score"],
    })
    print("\nPillar 2: Balance sheet strength  (Altman Z'' shown for reference, not scored)\n")
    print(view.to_string())

    # Overall: simple average of the pillars built so far
    overall = pd.DataFrame({col: res[col] for col, res in results.items()})
    overall["overall_score"] = overall.mean(axis=1).round(1)
    overall = overall.sort_values("overall_score", ascending=False)
    overall.to_csv("outputs/overall.csv")
    overall.columns = ["Profitability", "Balance sheet", "Overall"]
    print("\nOverall (equal-weighted average of pillars built so far)\n")
    print(overall.to_string())
    print("\nResults saved to outputs/")


if __name__ == "__main__":
    main()
