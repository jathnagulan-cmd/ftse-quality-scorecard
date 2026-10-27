"""Pillar 2: Balance sheet strength.

The question this pillar answers: could this company survive a bad few years
without its lenders or shareholders having to rescue it?

Scored metrics (latest annual report):

  Net debt / EBITDA  (lower is better)
        Net debt = Total debt (including leases) - Cash and short-term investments
        EBITDA   = Operating profit + Depreciation and amortisation
        Roughly: how many years of operating cash profit it would take to pay
        off the debt. Under ~2x is comfortable, above ~4x is stretched.
        A negative figure means the company holds more cash than debt.
        We build EBITDA ourselves because Yahoo's EBITDA line has the same
        non-operating distortions as its EBIT line.

  Interest cover = Operating profit / Interest expense  (higher is better)
        How many times over profits cover the interest bill. Below ~3x, a
        bad year starts to threaten the company's ability to pay its lenders.

  Equity ratio = Shareholders' equity / Total assets  (higher is better)
        How much of the business is funded by owners rather than creditors.
        A thicker cushion absorbs losses before lenders are at risk.

Reported but NOT scored:

  Altman Z''-score (the non-manufacturer version, which needs no share price):
        Z'' = 6.56*(Working capital / TA) + 3.26*(Retained earnings / TA)
            + 6.72*(EBIT / TA) + 1.05*(Equity / Total liabilities)
        Zones: above 2.6 safe, 1.1 to 2.6 grey, below 1.1 distress.
        It is shown as a cross-check, not scored, because it misreads some
        healthy business models. Supermarkets deliberately run negative
        working capital (customers pay at the till, suppliers are paid weeks
        later), which drags a perfectly solvent Tesco into the "distress" zone.
        It also punishes companies like Rolls-Royce for losses long since
        recovered, through retained earnings.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from scorecard.scoring import rank_and_score
from scorecard.statements import latest_value

HIGHER_IS_BETTER = {
    "net_debt_to_ebitda": False,
    "interest_cover": True,
    "equity_ratio": True,
}


def net_debt_to_ebitda(net_debt: float, ebitda: float) -> float:
    """Leverage multiple, with the awkward cases handled explicitly.

    If EBITDA is zero or negative, the ratio is meaningless: a company with
    debt and no operating cash profit is as bad as it gets (infinity), while
    one with net cash and no profit can't sensibly be ranked (NaN).
    """
    if np.isnan(net_debt) or np.isnan(ebitda):
        return np.nan
    if ebitda <= 0:
        return np.inf if net_debt > 0 else np.nan
    return net_debt / ebitda


def interest_cover(ebit: float, interest: float) -> float:
    """Operating profit / interest. No interest bill and positive profit = infinite cover."""
    if np.isnan(ebit) or np.isnan(interest):
        return np.nan
    interest = abs(interest)  # Yahoo reports it as positive for some companies, negative for others
    if interest == 0:
        return np.inf if ebit > 0 else np.nan
    return ebit / interest


def altman_z_double_prime(income: pd.DataFrame, balance: pd.DataFrame) -> float:
    ta = latest_value(balance, "total_assets")
    tl = latest_value(balance, "total_liabilities")
    if not ta > 0 or not tl > 0:
        return np.nan
    wc = latest_value(balance, "current_assets") - latest_value(balance, "current_liabilities")
    re = latest_value(balance, "retained_earnings")
    ebit = latest_value(income, "ebit")
    eq = latest_value(balance, "equity")
    return 6.56 * wc / ta + 3.26 * re / ta + 6.72 * ebit / ta + 1.05 * eq / tl


def z_zone(z: float) -> str:
    if np.isnan(z):
        return "n/a"
    return "safe" if z > 2.6 else "grey" if z >= 1.1 else "distress"


def company_metrics(income: pd.DataFrame, balance: pd.DataFrame, cashflow: pd.DataFrame | None = None) -> dict[str, float]:
    ebit = latest_value(income, "ebit")
    ebitda = ebit + latest_value(income, "depreciation")
    net_debt = latest_value(balance, "total_debt") - latest_value(balance, "cash")
    ta = latest_value(balance, "total_assets")
    z = altman_z_double_prime(income, balance)
    return {
        "net_debt_to_ebitda": net_debt_to_ebitda(net_debt, ebitda),
        "interest_cover": interest_cover(ebit, latest_value(income, "interest_expense")),
        "equity_ratio": latest_value(balance, "equity") / ta if ta > 0 else np.nan,
        "altman_z": z,
        "altman_zone": z_zone(z),
    }


def score(metrics: pd.DataFrame) -> pd.DataFrame:
    """Score on the three scored metrics; the Altman columns ride along unscored."""
    return rank_and_score(metrics, HIGHER_IS_BETTER, "balance_sheet_score")
