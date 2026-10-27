"""Run the scorecard on the default companies and save the results.

Usage:
    python run.py
"""

import pandas as pd

from scorecard.data import DEFAULT_TICKERS, fetch_all
from scorecard.profitability import company_metrics, score


def main() -> None:
    print("Fetching annual reports...")
    statements = fetch_all(DEFAULT_TICKERS)

    rows = {}
    for ticker, s in statements.items():
        rows[DEFAULT_TICKERS[ticker]] = company_metrics(s["income"], s["balance"])
    metrics = pd.DataFrame.from_dict(rows, orient="index")

    results = score(metrics)
    results.to_csv("outputs/profitability.csv")

    # Friendly view: ratios as percentages
    view = results[["roce", "operating_margin", "gross_margin", "margin_trend", "profitability_score"]].copy()
    for col in ["roce", "operating_margin", "gross_margin", "margin_trend"]:
        view[col] = (view[col] * 100).round(1)
    view.columns = ["ROCE %", "Op margin %", "Gross margin %", "Margin trend (pp/yr)", "Score /100"]
    print("\nProfitability pillar\n")
    print(view.to_string())
    print("\nSaved to outputs/profitability.csv")


if __name__ == "__main__":
    main()
