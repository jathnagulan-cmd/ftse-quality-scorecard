"""Plain-English strengths and red flags for each company, and the shortlist.

Scores say how a company ranks. Flags say WHAT to look at. The aim is to
turn hours of due diligence into a focused twenty minutes: the flags tell you
which questions to take to the latest annual report.

Every rule is a simple threshold on a metric that already exists, so each
flag can be traced back to a number. Thresholds are rules of thumb, not laws.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Industries where high, stable debt is normal because revenue is regulated
REGULATED = ("Utilities - Regulated",)

# Industries whose profits swing with the economy or commodity prices. Four
# years of data (roughly 2022-2025) contains no full downturn for most of
# these, so their averages may still flatter them.
CYCLICAL_KEYWORDS = (
    "Airlines", "Mining", "Metals", "Gold", "Copper", "Oil & Gas", "Residential Construction",
    "Chemicals", "Steel", "Building Materials", "Auto", "Lodging", "Travel",
)

# Long-term shortlist: as the main shortlist, but only businesses whose
# profits have held steady. Excludes cyclical industries and any company
# whose operating margin swung by more than this across the years available.
LONG_TERM_MAX_MARGIN_SWING = 0.03

SHORTLIST_MIN_QUALITY = 60
SHORTLIST_MIN_VALUATION = 40
SHORTLIST_MAX_RED_FLAGS = 1
SHORTLIST_SIZE = 10


def _ok(x) -> bool:
    return x is not None and not (isinstance(x, float) and np.isnan(x))


def is_cyclical(industry) -> bool:
    return isinstance(industry, str) and any(k in industry for k in CYCLICAL_KEYWORDS)


def company_flags(p: pd.Series, b: pd.Series, e: pd.Series, v: pd.Series, industry: str) -> dict[str, list[str]]:
    """Return {'strengths': [...], 'red_flags': [...], 'notes': [...]} for one company."""
    good, bad, notes = [], [], []
    regulated = isinstance(industry, str) and industry.startswith(REGULATED)

    # Profitability
    if _ok(p.roce) and p.roce > 1.0:
        good.append("Exceptional return on capital: ROCE averaged over 100% (very little capital tied up)")
    elif _ok(p.roce) and p.roce > 0.20:
        good.append(f"High return on capital: ROCE averaged {p.roce:.0%}")
    if _ok(p.roce) and p.roce < 0.08:
        bad.append(f"Low return on capital: ROCE averaged {p.roce:.0%}, below a typical cost of capital")
    if _ok(p.margin_trend) and p.margin_trend < -0.02:
        bad.append(f"Operating margin falling about {-p.margin_trend * 100:.1f} points a year")
    if _ok(p.margin_stability) and p.margin_stability < 0.01:
        good.append(f"Very steady margins: operating margin moved less than 1 point across {int(p.years_of_data)} years")
    if _ok(p.margin_stability) and p.margin_stability > 0.05:
        bad.append(f"Volatile margins (swing of {p.margin_stability * 100:.0f} points): cyclical or erratic profits")
    if is_cyclical(industry):
        notes.append(f"Cyclical industry ({industry}): the data may not include a full downturn, so treat strong scores with caution")
    if _ok(p.years_of_data) and p.years_of_data < 3:
        notes.append(f"Only {int(p.years_of_data)} years of data: averages and stability are less reliable")

    # Balance sheet
    nd = b.net_debt_to_ebitda
    if _ok(nd) and np.isinf(nd):
        bad.append("Has debt but no operating cash profit (EBITDA) to service it")
    elif _ok(nd) and nd < 0:
        good.append("Net cash: holds more cash than debt")
    elif _ok(nd) and nd > 3.5 and not regulated:
        bad.append(f"High debt: net debt is {nd:.1f}x EBITDA (including leases)")
    elif _ok(nd) and nd > 6 and regulated:
        bad.append(f"High debt even for a regulated utility: {nd:.1f}x EBITDA")
    ic = b.interest_cover
    if _ok(ic) and not np.isinf(ic) and ic < 3:
        bad.append(f"Thin interest cover: operating profit covers interest only {ic:.1f}x")
    if _ok(b.equity_ratio) and b.equity_ratio < 0:
        notes.append("Negative shareholders' equity, often from large buybacks; check it isn't from losses")

    # Earnings quality
    cc = e.cash_conversion
    if _ok(cc) and np.isinf(cc):
        bad.append("EBITDA has been negative in at least one year: no stable profit to judge")
    elif _ok(cc) and cc < 0.70:
        bad.append(f"Weak cash conversion: only {cc:.0%} of EBITDA arrived as operating cash")
    elif _ok(cc) and cc > 0.95:
        good.append(f"Profits backed by cash: {cc:.0%} cash conversion")
    if _ok(e.accrual_ratio) and e.accrual_ratio > 0.05:
        bad.append(f"Profit running well ahead of cash (accrual ratio {e.accrual_ratio:.0%} of assets)")
    if _ok(e.receivables_gap) and e.receivables_gap > 0.10:
        bad.append(f"Money owed by customers grew {e.receivables_gap * 100:.0f} points faster than sales")

    # Valuation
    if _ok(v.ev_to_ebit):
        if np.isinf(v.ev_to_ebit):
            bad.append("No average operating profit, so it can't be valued on earnings")
        elif v.ev_to_ebit > 30:
            bad.append(f"Expensive: {v.ev_to_ebit:.0f}x average operating profit, priced for strong growth")
        elif 0 < v.ev_to_ebit < 10:
            good.append(f"Cheap on normalised profits: {v.ev_to_ebit:.1f}x average operating profit")
    if _ok(v.pe_latest) and v.pe_latest < 10 and _ok(p.margin_stability) and p.margin_stability > 0.04:
        notes.append("Low P/E on volatile profits: may look cheap because profits are at a peak")
    if _ok(v.pe_latest) and v.pe_latest > 60:
        notes.append(f"Headline P/E of {v.pe_latest:.0f} reflects unusually low latest-year profit, not price alone")

    return {"strengths": good, "red_flags": bad, "notes": notes}


def all_flags(results: dict[str, pd.DataFrame], info: pd.DataFrame) -> dict[str, dict[str, list[str]]]:
    p, b, e, v = (results[k] for k in ("profitability_score", "balance_sheet_score", "earnings_quality_score", "valuation_score"))
    return {
        name: company_flags(p.loc[name], b.loc[name], e.loc[name], v.loc[name], info.loc[name].get("industry"))
        for name in results["overall"].index
    }


def _base_rules(overall: pd.DataFrame, flags: dict, tradeable: pd.Series | None) -> pd.Series:
    red = pd.Series({n: len(f["red_flags"]) for n, f in flags.items()}).reindex(overall.index)
    ok = (
        (overall["quality_score"] >= SHORTLIST_MIN_QUALITY)
        & (overall["valuation_score"] >= SHORTLIST_MIN_VALUATION)
        & (red <= SHORTLIST_MAX_RED_FLAGS)
    )
    if tradeable is not None:
        # Only rule out companies CONFIRMED as unavailable; unchecked ones stay
        ok &= tradeable.reindex(overall.index).fillna("unchecked") != "no"
    return ok


def shortlist(overall: pd.DataFrame, flags: dict, tradeable: pd.Series | None = None) -> pd.DataFrame:
    """Good businesses at sensible prices with few red flags, best first."""
    return overall[_base_rules(overall, flags, tradeable)].head(SHORTLIST_SIZE)


def long_term_shortlist(
    overall: pd.DataFrame, flags: dict, profitability: pd.DataFrame, info: pd.DataFrame,
    tradeable: pd.Series | None = None,
) -> pd.DataFrame:
    """The shortlist restricted to steady businesses, for buying and holding for years.

    Drops cyclical industries and companies whose margins swung more than
    LONG_TERM_MAX_MARGIN_SWING. These rules come from the goal (long-term
    holding), not from the backtest.
    """
    swing = profitability["margin_stability"].reindex(overall.index)
    cyclical = info["industry"].reindex(overall.index).map(is_cyclical)
    ok = _base_rules(overall, flags, tradeable) & (swing <= LONG_TERM_MAX_MARGIN_SWING) & ~cyclical
    return overall[ok].head(SHORTLIST_SIZE)
