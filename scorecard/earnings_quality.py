"""Pillar 3: Earnings quality.

The question this pillar answers: is the profit real? Reported profit is full
of accounting judgements (when to recognise revenue, how fast to depreciate,
what to revalue). Cash is much harder to dress up. Companies whose profits
consistently run ahead of their cash are the ones that tend to disappoint.

Scored metrics:

  Cash conversion = Operating cash flow (pre-interest) / EBITDA,
                    summed over every year available  (higher is better)
        How much of the operating profit actually arrives as cash. Around
        80-100% is healthy; well below that means profit is getting stuck in
        stock, unpaid invoices or accounting adjustments. Summed over several
        years because any single year can be distorted by timing. Only
        calculated when EBITDA was positive every year; otherwise ranked last.

  Accrual ratio (Sloan) = (Net income - Operating cash flow) / Average total assets
                          (lower is better)
        The gap between accounting profit and cash, scaled by company size.
        Richard Sloan (1996) showed that companies with high accruals tend to
        see earnings fall back later. A negative number means cash is running
        AHEAD of profit, usually because of large non-cash charges.

  Receivables gap = Growth in receivables - Growth in revenue (latest year,
                    percentage points)  (lower is better)
        If money owed by customers grows much faster than sales, revenue may
        be being booked before it can be collected: a classic warning sign.

Disposals: profit on selling a business lands in net income, but the sale
proceeds are an investing cash flow, never an operating one. Left in, a big
disposal looks like profit with no cash behind it (Smiths Group's £1.7bn gain
in 2026 produced an accrual ratio of 40% of total assets). The cash flow
statement's own reconciling line for disposal gains is used to strip them out
of net income before the accrual ratio is calculated.

Consistency fix: IFRS lets companies classify interest paid as either an
operating or a financing cash flow. Rolls-Royce puts it in financing, the
others in operating. Left alone, that would make Rolls-Royce's operating cash
flow look better purely because of a presentation choice. So:
  - cash conversion uses OCF with interest added back (pre-interest), to match
    EBITDA, which is also before interest
  - the accrual ratio uses OCF with interest taken off (post-interest), to
    match net income, which is also after interest
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from scorecard.scoring import rank_and_score
from scorecard.statements import get_row

HIGHER_IS_BETTER = {
    "cash_conversion": True,
    "accrual_ratio": False,
    "receivables_gap": False,
}


def _row(df: pd.DataFrame, item: str) -> pd.Series:
    """A line item with missing interest-classification rows treated as zero."""
    s = get_row(df, item)
    return s.fillna(0) if item.startswith("interest_paid") or item == "disposal_adjustment" else s


def operating_cash_flows(cashflow: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Return (pre-interest OCF, post-interest OCF), oldest year first.

    Interest paid appears as a negative number, so subtracting it adds it back.
    """
    ocf = get_row(cashflow, "operating_cash_flow")
    pre_interest = ocf - _row(cashflow, "interest_paid_in_ocf")
    post_interest = ocf + _row(cashflow, "interest_paid_in_financing")
    return pre_interest, post_interest


def cash_conversion(ocf_pre_interest: pd.Series, ebitda: pd.Series) -> float:
    """Total pre-interest OCF / total EBITDA over the years where both exist.

    Only meaningful if EBITDA was positive in every year. If it dipped to zero
    or below, the total can be tiny and the ratio explodes (Ocado's four-year
    EBITDA of ~£0.2bn produced "488%" conversion). A business with no stable
    operating profit has no earnings whose quality can be vouched for, so it
    gets -inf and ranks last on this metric, rather than being rewarded.
    """
    both = pd.concat([ocf_pre_interest, ebitda], axis=1, join="inner").dropna()
    if both.empty:
        return np.nan
    if (both.iloc[:, 1] <= 0).any():
        return -np.inf
    return both.iloc[:, 0].sum() / both.iloc[:, 1].sum()


def accrual_ratio(net_income: pd.Series, ocf_post_interest: pd.Series, total_assets: pd.Series) -> float:
    df = pd.concat({"ni": net_income, "ocf": ocf_post_interest, "ta": total_assets}, axis=1).sort_index()
    df["avg_ta"] = df["ta"].rolling(2, min_periods=1).mean()
    df = df.dropna()
    if df.empty or df["avg_ta"].iloc[-1] <= 0:
        return np.nan
    last = df.iloc[-1]
    return (last["ni"] - last["ocf"]) / last["avg_ta"]


def growth(s: pd.Series) -> float:
    s = s.dropna()
    if len(s) < 2 or s.iloc[-2] <= 0:
        return np.nan
    return s.iloc[-1] / s.iloc[-2] - 1


def company_metrics(income: pd.DataFrame, balance: pd.DataFrame, cashflow: pd.DataFrame | None = None) -> dict[str, float]:
    if cashflow is None:
        raise ValueError("Earnings quality needs the cash flow statement")
    ebitda = get_row(income, "ebit") + get_row(income, "depreciation")
    pre, post = operating_cash_flows(cashflow)
    return {
        "cash_conversion": cash_conversion(pre, ebitda),
        "accrual_ratio": accrual_ratio(
            get_row(cashflow, "net_income_cf") + _row(cashflow, "disposal_adjustment"),
            post,
            get_row(balance, "total_assets"),
        ),
        "receivables_gap": growth(get_row(balance, "receivables")) - growth(get_row(income, "revenue")),
    }


def score(metrics: pd.DataFrame, peer_groups: pd.Series | None = None) -> pd.DataFrame:
    return rank_and_score(metrics, HIGHER_IS_BETTER, "earnings_quality_score")
