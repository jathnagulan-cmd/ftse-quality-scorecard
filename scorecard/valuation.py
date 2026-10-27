"""Pillar 4: Valuation.

The question this pillar answers: is the price reasonable for what you get?
A great business bought at a silly price is still a bad investment.

Enterprise value (EV) = Market capitalisation + Net debt (including leases)
    What it would cost to buy the whole business, debts and all. Using EV
    rather than share price alone means a company isn't made to look cheap
    just because it is loaded with debt.

Scored metrics (universe-wide, because cheap means cheap in any sector):

  EV / EBIT  (lower is better)
        Years of operating profit it would take to pay back the full price.
        Joel Greenblatt's "Magic Formula" pairs this with return on capital.
        EBIT is AVERAGED over every year available, not the latest year.
        This matters most for cyclicals, which look cheapest exactly at the
        peak, when profits are about to fall. A company with no average
        operating profit is ranked as the most expensive.

  Free cash flow yield = Average free cash flow / EV  (higher is better)
        Free cash flow = Operating cash flow (before interest) - Capital
        expenditure. The cash return the business generates on its full
        price each year, before paying lenders. Before interest because EV
        includes debt, so the cash must be what's available to lenders and
        shareholders together.

Shown for reference, NOT scored:

  P/E (latest year) = Market cap / Latest net income
        The number most people quote, kept so you can see how misleading it
        can be next to the normalised figures above.

Market cap uses today's price (or the price on the backtest date) and the
latest reported share count, converted into the reporting currency.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from scorecard.earnings_quality import operating_cash_flows
from scorecard.scoring import rank_and_score
from scorecard.statements import get_row, latest_value

HIGHER_IS_BETTER = {
    "ev_to_ebit": False,
    "fcf_yield": True,
}


def _avg(s: pd.Series) -> float:
    s = s.dropna()
    return float(s.mean()) if len(s) else np.nan


def company_metrics(
    income: pd.DataFrame, balance: pd.DataFrame, cashflow: pd.DataFrame, market_cap: float
) -> dict[str, float]:
    net_debt = latest_value(balance, "total_debt") - latest_value(balance, "cash")
    ev = market_cap + net_debt
    avg_ebit = _avg(get_row(income, "ebit"))

    pre_interest_ocf, _ = operating_cash_flows(cashflow)
    capex = get_row(cashflow, "capex").fillna(0)  # reported as a negative number
    avg_fcf = _avg(pre_interest_ocf + capex)

    if np.isnan(ev) or np.isnan(avg_ebit):
        ev_to_ebit = np.nan
    elif avg_ebit <= 0:
        ev_to_ebit = np.inf
    else:
        ev_to_ebit = ev / avg_ebit

    latest_ni = latest_value(income, "net_income")
    return {
        "ev_to_ebit": ev_to_ebit,
        "fcf_yield": avg_fcf / ev if ev > 0 else np.nan,
        "pe_latest": market_cap / latest_ni if latest_ni > 0 else np.nan,
        "market_cap": market_cap,
        "enterprise_value": ev,
    }


def score(metrics: pd.DataFrame, peer_groups: pd.Series | None = None) -> pd.DataFrame:
    return rank_and_score(metrics, HIGHER_IS_BETTER, "valuation_score")
