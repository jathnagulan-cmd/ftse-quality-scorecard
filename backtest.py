"""Backtest: did high-scoring companies actually go on to beat low-scoring ones?

Usage:
    python backtest.py

Method
------
At each past formation date the full scorecard is rerun as it would have
looked that day: only accounts published by then (see engine.py's four-month
rule) and the share price on that date. Companies are split into five equal
groups (quintiles) by score, and each group's average total return over the
following twelve months is measured, dividends included.

What would count as evidence the scores work: the top quintile beating the
bottom quintile consistently, and a positive rank correlation between score
and subsequent return.

Limitations, stated up front
----------------------------
- Short history. Free data covers about four years of accounts, so the first
  usable date is mid-2024 and there are only a handful of overlapping
  twelve-month periods, all in one market environment. Even a strong result
  could be luck.
- Fewer years per score. Early dates have only two years of accounts, so
  averages are shorter and the stability metric is mostly missing.
- Survivorship bias. The universe is today's FTSE 100, which by construction
  includes companies that did well enough to be in it. Companies that fell out
  of the index are missing. This inflates every group's returns; the gap
  between groups is less affected, but not immune.
- No costs. Trading costs and stamp duty (0.5% on UK shares) are ignored.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from scorecard.data import fetch_universe, load_universe
from scorecard.engine import score_universe
from scorecard.flags import all_flags, long_term_shortlist, shortlist
from scorecard.prices import load_prices, price_on

FORMATION_DATES = pd.to_datetime(["2024-05-01", "2024-08-01", "2024-11-01", "2025-02-01", "2025-05-01", "2025-08-01", "2025-11-01"])
HORIZON = pd.DateOffset(months=12)
LONG_HORIZON = pd.DateOffset(months=24)
# The realistic alternative to picking shares: a FTSE 100 tracker fund.
# iShares Core FTSE 100 ETF; its dividend-adjusted price gives total return.
BENCHMARK = "ISF.L"
SCORES = ["overall_score", "quality_score", "valuation_score"]
GROUPS = 5


def forward_returns(tickers: pd.Series, adjusted: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    out = {}
    for name, t in tickers.items():
        if t in adjusted:
            p0, p1 = price_on(adjusted[t], start), price_on(adjusted[t], end)
            out[name] = p1 / p0 - 1 if p0 > 0 and p1 > 0 else np.nan
    return pd.Series(out)


def evaluate(date, results, info, prices, horizon=HORIZON) -> dict:
    overall = results["overall"]
    rets = forward_returns(overall["ticker"], prices["adjusted"], date, date + horizon)
    df = overall.join(rets.rename("ret")).dropna(subset=["ret"])
    row = {"date": date.strftime("%Y-%m-%d"), "companies": len(df), "universe_return": df["ret"].mean(),
           "universe_median": df["ret"].median()}
    for sc in SCORES:
        groups = pd.qcut(df[sc].rank(method="first"), GROUPS, labels=False)
        by_group = df.groupby(groups)["ret"].mean()
        med = df.groupby(groups)["ret"].median()
        key = sc.replace("_score", "")
        row[f"{key}_top"] = by_group.iloc[-1]
        row[f"{key}_bottom"] = by_group.iloc[0]
        row[f"{key}_spread"] = by_group.iloc[-1] - by_group.iloc[0]
        # Medians: one share going up 400% can't swing these
        row[f"{key}_median_spread"] = med.iloc[-1] - med.iloc[0]
        row[f"{key}_rank_corr"] = df[sc].corr(df["ret"], method="spearman")
    flags = all_flags(results, info)
    short = shortlist(overall, flags)
    short_rets = df.loc[df.index.intersection(short.index), "ret"]
    row["shortlist_size"] = len(short_rets)
    row["shortlist_return"] = short_rets.mean() if len(short_rets) else np.nan
    row["shortlist_median"] = short_rets.median() if len(short_rets) else np.nan
    # Long-term shortlist, held as an equal-weighted portfolio (so the mean is what you'd earn)
    lt = long_term_shortlist(overall, flags, results["profitability_score"], info)
    lt_rets = df.loc[df.index.intersection(lt.index), "ret"]
    row["long_term_size"] = len(lt_rets)
    row["long_term_return"] = lt_rets.mean() if len(lt_rets) else np.nan
    row["benchmark_return"] = forward_returns(pd.Series({"FTSE 100 tracker": BENCHMARK}), prices["adjusted"], date, date + horizon).iloc[0]
    return row


def main() -> None:
    statements, info = fetch_universe(load_universe())
    prices = load_prices(list(info["ticker"]) + [BENCHMARK])
    last_price_date = prices["adjusted"].dropna(how="all").index.max()

    rows, long_rows = [], []
    for date in FORMATION_DATES:
        if date + HORIZON > last_price_date:
            print(f"  {date:%Y-%m-%d}: skipped, twelve months haven't passed yet")
            continue
        results = score_universe(statements, info, prices, as_of=date)
        rows.append(evaluate(date, results, info, prices))
        if date + LONG_HORIZON <= last_price_date:
            long_rows.append(evaluate(date, results, info, prices, LONG_HORIZON))
        print(f"  {date:%Y-%m-%d}: scored {rows[-1]['companies']} companies")

    res = pd.DataFrame(rows).set_index("date")
    res.to_csv("outputs/backtest.csv")

    pct = lambda x: "n/a" if x is None or pd.isna(x) else f"{x * 100:+.1f}%"  # noqa: E731
    print("\nTwelve-month total returns after each formation date\n")
    table = pd.DataFrame({
        "Companies": res["companies"],
        "All": res["universe_return"].map(pct),
        "Top 20% overall": res["overall_top"].map(pct),
        "Bottom 20% overall": res["overall_bottom"].map(pct),
        "Spread": res["overall_spread"].map(pct),
        "Median spread": res["overall_median_spread"].map(pct),
        "Rank corr": res["overall_rank_corr"].round(2),
        "Shortlist": res["shortlist_return"].map(lambda x: "n/a" if pd.isna(x) else pct(x)),
        "Shortlist n": res["shortlist_size"],
        "Long-term": res["long_term_return"].map(lambda x: "n/a" if pd.isna(x) else pct(x)),
        "Long-term n": res["long_term_size"],
        "FTSE tracker": res["benchmark_return"].map(pct),
    })
    print(table.to_string())

    summary = {"periods": len(res), "note": "Overlapping 12-month periods; see backtest.py for limitations."}
    for key in ["overall", "quality", "valuation"]:
        summary[key] = {
            "avg_top": res[f"{key}_top"].mean(), "avg_bottom": res[f"{key}_bottom"].mean(),
            "avg_spread": res[f"{key}_spread"].mean(),
            "avg_median_spread": res[f"{key}_median_spread"].mean(),
            "periods_top_beat_bottom_median": int((res[f"{key}_median_spread"] > 0).sum()),
            "periods_top_beat_bottom": int((res[f"{key}_spread"] > 0).sum()),
            "avg_rank_corr": res[f"{key}_rank_corr"].mean(),
        }
    summary["universe_avg"] = res["universe_return"].mean()
    summary["shortlist_avg"] = res["shortlist_return"].mean()
    summary["shortlist_beat_universe"] = int((res["shortlist_return"] > res["universe_return"]).sum())
    summary["shortlist_median_avg"] = res["shortlist_median"].mean()
    summary["universe_median_avg"] = res["universe_median"].mean()
    summary["shortlist_beat_universe_median"] = int((res["shortlist_median"] > res["universe_median"]).sum())
    summary["benchmark_avg"] = res["benchmark_return"].mean()
    summary["shortlist_beat_benchmark"] = int((res["shortlist_return"] > res["benchmark_return"]).sum())
    summary["long_term_avg"] = res["long_term_return"].mean()
    summary["long_term_beat_benchmark"] = int((res["long_term_return"] > res["benchmark_return"]).sum())
    # The long-term list needs three years of margins, so early dates have none
    summary["long_term_periods"] = int(res["long_term_return"].notna().sum())
    summary["by_period"] = json.loads(res.reset_index().to_json(orient="records"))
    if long_rows:
        lr = pd.DataFrame(long_rows)
        summary["two_year"] = json.loads(lr[[
            "date", "companies", "universe_median", "quality_median_spread", "shortlist_return",
            "long_term_return", "long_term_size", "benchmark_return",
        ]].to_json(orient="records"))
        lr.to_csv("outputs/backtest_two_year.csv", index=False)

    print("\nAverages across periods\n")
    for key in ["overall", "quality", "valuation"]:
        s = summary[key]
        print(f"  {key:9s}  top {pct(s['avg_top'])}  bottom {pct(s['avg_bottom'])}  spread {pct(s['avg_spread'])}"
              f"  top beat bottom in {s['periods_top_beat_bottom']}/{len(res)}  rank corr {s['avg_rank_corr']:+.2f}"
              f"  | median spread {pct(s['avg_median_spread'])}, positive in {s['periods_top_beat_bottom_median']}/{len(res)}")
    print(f"  shortlist  {pct(summary['shortlist_avg'])} vs universe {pct(summary['universe_avg'])},"
          f" beat it in {summary['shortlist_beat_universe']}/{len(res)} periods")
    print(f"  shortlist median {pct(summary['shortlist_median_avg'])} vs universe median {pct(summary['universe_median_avg'])},"
          f" beat it in {summary['shortlist_beat_universe_median']}/{len(res)} periods")
    print(f"\n  Against a FTSE 100 tracker ({pct(summary['benchmark_avg'])} average):")
    print(f"    shortlist  {pct(summary['shortlist_avg'])}, beat the tracker in {summary['shortlist_beat_benchmark']}/{len(res)} periods")
    print(f"    long-term  {pct(summary['long_term_avg'])}, beat the tracker in {summary['long_term_beat_benchmark']}/{summary['long_term_periods']} periods with a list")
    if long_rows:
        print("\nTwo-year returns (only dates with two full years of history)\n")
        for r in summary["two_year"]:
            print(f"  {r['date']}: shortlist {pct(r['shortlist_return'])}, long-term {pct(r['long_term_return'])}"
                  f" ({r['long_term_size']} shares), FTSE tracker {pct(r['benchmark_return'])}")

    with open("outputs/backtest.json", "w") as f:
        json.dump(summary, f, indent=1, default=float)
    print("\nPeriods overlap and share one market environment: treat this as weak evidence either way.")


if __name__ == "__main__":
    main()
