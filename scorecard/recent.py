"""What has happened since the last annual report: news, newer results and
management changes.

The scores read annual reports only. This module adds the context the scores
cannot see, shown on the dashboard next to them but deliberately NOT scored
(like the price trend): headlines are noisy and Yahoo's interim figures are
patchy, so mixing them into the scores would make them less trustworthy, and
the backtest could not test them anyway.

Three things are checked for each company:

  results   Yahoo's trailing-twelve-month operating margin (which includes
            any half-year or quarterly results published since the annual
            report) against the margin in the last annual report, the latest
            period's sales and earnings growth, and the last / next results
            dates.
  news      headlines from the last 60 days that Yahoo tags with the
            company's ticker, with roundup articles dropped. Headlines that
            look like a profit warning, a management change, a deal or a
            legal/regulatory problem are flagged.
  officers  the current chief executive and finance director, compared with
            data/officers.json. A new name is flagged for a year.

Everything is fetched once a day and cached in data/cache/recent.json.
"""

from __future__ import annotations

import json
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from scorecard.data import CACHE_DIR, ROOT

RECENT_FILE = CACHE_DIR / "recent.json"
OFFICERS_FILE = ROOT / "data" / "officers.json"

NEWS_DAYS = 60          # how far back headlines are kept
ALERT_DAYS = 30         # how recent a flagged headline must be to raise a warning
MAX_HEADLINES = 6
OFFICER_FLAG_DAYS = 365
RESULTS_SOON_DAYS = 21

# Margin moves smaller than this are noise in trailing figures
MARGIN_MOVE_POINTS = 0.02
MARGIN_MOVE_RELATIVE = 0.15
SALES_DROP = -0.05
EARNINGS_DROP = -0.30

TAGS = {
    "Profit warning": r"profit warning|warns on (profit|earnings)|cuts? (its |full[- ]year )?(guidance|forecast|outlook)"
                      r"|lowers? (its )?(guidance|forecast|outlook)|downgrades? (its )?(guidance|outlook)|shares? (plunge|slump|tumble|crash)",
    "Management change": r"\b(ceo|chief executive|cfo|finance director|chief financial officer|chair(man|woman)?)\b.*"
                         r"\b(steps? down|step down|resign|quits?|depart|leave|to leave|exit|ousted|replace|succeed|successor|appoint|named|retire)"
                         r"|\b(appoints?|names?|hires?)\b.*\b(ceo|chief executive|cfo|chair(man|woman)?)\b",
    "Deal": r"takeover|\bbid\b|merger|\bacquir|\bacquisition|offer for|buyout|approach for|\bspin[- ]?off|demerg",
    "Legal / regulatory": r"investigat|\bprobe\b|\bfined?\b|lawsuit|\bsued?\b|class action|\bcma\b|\bfca\b|\bsfo\b|regulator|antitrust|settlement",
    "Results": r"\bresults\b|trading update|half[- ]year|\binterim\b|first[- ]half|\bh1\b|\bq[1-4]\b|quarter|earnings call|full[- ]year",
}
# Headlines tagged with this are warnings rather than routine news
ALERT_TAGS = {"Profit warning": "bad", "Management change": "note", "Deal": "note", "Legal / regulatory": "note"}

ROUNDUP = re.compile(r"stocks to (watch|own|buy|consider)|\b\d+ (british|uk|ftse|european|dividend|undervalued|top)\b"
                     r"|\band \d+ (other|more)\b|plus \d+|(depositary receipts|adrs?) (rise|fall)|stocks? (lagging|leading)", re.I)


# ---------- pure functions (tested without a connection) ----------

def tag_headline(title: str) -> list[str]:
    return [tag for tag, pattern in TAGS.items() if re.search(pattern, title, re.I)]


def is_relevant(item: dict, ticker: str, name: str) -> bool:
    """Keep headlines Yahoo links to this company, dropping multi-stock roundups."""
    title = item.get("title") or ""
    if ROUNDUP.search(title):
        return False
    related = set(item.get("relatedTickers") or [])
    if ticker in related:
        return True
    # Dual-listed companies (Shell, BP...) are often tagged with the US symbol only
    base = ticker.split(".")[0]
    first_word = name.split()[0]
    return base in related and first_word.lower() in title.lower()


def clean_news(items: list[dict], ticker: str, name: str, today: date) -> list[dict]:
    out, seen = [], set()
    cutoff = today - timedelta(days=NEWS_DAYS)
    for it in sorted(items, key=lambda x: x.get("providerPublishTime") or 0, reverse=True):
        ts = it.get("providerPublishTime")
        title = (it.get("title") or "").strip()
        if not ts or not title or title.lower() in seen or not is_relevant(it, ticker, name):
            continue
        published = datetime.fromtimestamp(ts, tz=timezone.utc).date()
        if published < cutoff:
            continue
        seen.add(title.lower())
        out.append({"date": published.isoformat(), "title": title, "publisher": it.get("publisher") or "",
                    "link": it.get("link") or "", "tags": tag_headline(title)})
    return out[:MAX_HEADLINES]


def _iso(ts) -> str | None:
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat() if isinstance(ts, (int, float)) and ts > 0 else None


def _num(x) -> float | None:
    return float(x) if isinstance(x, (int, float)) and x == x and abs(x) != float("inf") else None


def results_summary(info: dict, annual_margin: float | None, today: date) -> dict:
    """Newer figures from Yahoo compared with the last annual report."""
    ttm = _num(info.get("operatingMargins"))
    stamps = [info.get(k) for k in ("earningsTimestamp", "earningsTimestampStart", "earningsTimestampEnd")]
    dates = sorted({d for d in (_iso(s) for s in stamps) if d})
    last = max((d for d in dates if d < today.isoformat()), default=None)
    upcoming = min((d for d in dates if d >= today.isoformat()), default=None)
    fy_end, latest_period = _iso(info.get("lastFiscalYearEnd")), _iso(info.get("mostRecentQuarter"))
    if last and latest_period and last < latest_period:
        last = None  # Yahoo's results date is stale: newer figures have come out since
    return {
        "annual_year_end": fy_end,
        "latest_period_end": latest_period,
        "newer_than_annual": bool(fy_end and latest_period and latest_period > fy_end),
        "last_results": last,
        "next_results": upcoming,
        "operating_margin_ttm": ttm,
        "operating_margin_annual": _num(annual_margin),
        "sales_growth": _num(info.get("revenueGrowth")),
        "earnings_growth": _num(info.get("earningsGrowth")),
    }


def officers_from_info(info: dict) -> dict:
    """Current chief executive and finance director, by title."""
    found = {}
    for o in info.get("companyOfficers") or []:
        title, name = (o.get("title") or ""), " ".join((o.get("name") or "").split())
        if not name:
            continue
        if "ceo" not in found and re.search(r"\bCEO\b|chief executive", title, re.I) and not re.search(r"deputy|division|regional|\bof\b", title, re.I):
            found["ceo"] = name
        if "cfo" not in found and re.search(r"\bCFO\b|chief financial|finance director", title, re.I) and not re.search(r"deputy|division|regional", title, re.I):
            found["cfo"] = name
    return found


def update_officers(current: dict, saved: dict, today: date) -> dict:
    """Merge today's names into the saved record, noting when a name changed.

    `since` is None for names already there when tracking began.
    """
    record = dict(saved)
    for role, name in current.items():
        old = record.get(role)
        if not old:
            record[role] = {"name": name, "since": None}
        elif old["name"] != name:
            record[role] = {"name": name, "since": today.isoformat(), "previous": old["name"]}
    return record


ROLE = {"ceo": "chief executive", "cfo": "finance director"}


def recent_flags(results: dict | None, news: list[dict], officers: dict, today: date) -> dict[str, list[str]]:
    """Plain-English warnings about what has changed since the annual report."""
    bad, note, good = [], [], []
    if results:
        ttm, annual = results.get("operating_margin_ttm"), results.get("operating_margin_annual")
        if ttm is not None and annual is not None and annual > 0:
            move = ttm - annual
            if abs(move) >= MARGIN_MOVE_POINTS and abs(move) / annual >= MARGIN_MOVE_RELATIVE:
                text = (f"Operating margin over the last twelve months is {ttm * 100:.1f}%, "
                        f"{'down' if move < 0 else 'up'} from {annual * 100:.1f}% in the last annual report")
                (bad if move < 0 else good).append(text)
        sg, eg = results.get("sales_growth"), results.get("earnings_growth")
        if sg is not None and sg <= SALES_DROP:
            bad.append(f"Sales down {abs(sg) * 100:.0f}% on a year earlier in the latest reported period")
        if eg is not None and eg <= EARNINGS_DROP:
            note.append(f"Earnings down {abs(eg) * 100:.0f}% on a year earlier in the latest reported period")
        nxt = results.get("next_results")
        if nxt and date.fromisoformat(nxt) - today <= timedelta(days=RESULTS_SOON_DAYS):
            note.append(f"Results due {date.fromisoformat(nxt).strftime('%-d %B')}: the picture may change")
    for role, rec in officers.items():
        since = rec.get("since")
        if since and today - date.fromisoformat(since) <= timedelta(days=OFFICER_FLAG_DAYS):
            prev = f", replacing {rec['previous']}" if rec.get("previous") else ""
            note.append(f"New {ROLE.get(role, role)}: {rec['name']}{prev} (noticed {date.fromisoformat(since).strftime('%-d %B %Y')})")
    cutoff = (today - timedelta(days=ALERT_DAYS)).isoformat()
    seen = set()
    for h in news:
        if h["date"] < cutoff:
            continue
        for tag in h["tags"]:
            level = ALERT_TAGS.get(tag)
            if level and tag not in seen:
                seen.add(tag)
                (bad if level == "bad" else note).append(f"{tag} in the news ({h['date']}): “{h['title']}”")
    return {"strengths": good, "red_flags": bad, "notes": note}


# ---------- fetching ----------

def _retry(fn, tries: int = 3, wait: float = 4.0):
    for i in range(tries):
        try:
            out = fn()
            if out:
                return out
        except Exception:
            pass
        if i < tries - 1:
            time.sleep(wait * (i + 1))
    return None


def _fetch_one(ticker: str, name: str) -> tuple[dict | None, list[dict] | None]:
    import yfinance as yf

    def get_info():
        i = yf.Ticker(ticker).info or {}
        return i if i.get("currency") else None  # a rate-limited reply comes back nearly empty

    info = _retry(get_info)
    query = re.sub(r"\b(Group|plc|PLC|International|Holdings)\b", "", name).strip() or name
    raw = _retry(lambda: yf.Search(query, news_count=20, max_results=1).news, tries=2)
    return info, raw


def load_recent(companies: list[dict], refresh: bool = False, today: date | None = None) -> dict:
    """Recent results, news, officers and flags for every company, keyed by ticker.

    A company whose data couldn't be fetched gets {"unavailable": true} rather
    than failing the build.
    """
    today = today or date.today()
    # Reuse today's complete entries; refetch anything missing or rate-limited
    done = {}
    if RECENT_FILE.exists():
        cached = json.loads(RECENT_FILE.read_text())
        if cached.get("date") == today.isoformat():
            done = {t: v for t, v in cached["companies"].items() if v.get("results") is not None}
            if not refresh and {c["ticker"] for c in companies} <= set(cached["companies"]) and len(done) == len(cached["companies"]):
                return cached["companies"]

    saved_officers = json.loads(OFFICERS_FILE.read_text()) if OFFICERS_FILE.exists() else {}
    out = {}
    for c in companies:
        ticker, name = c["ticker"], c["name"]
        if ticker in done:
            out[ticker] = done[ticker]
            continue
        info, raw = _fetch_one(ticker, name)
        annual = (c.get("metrics") or {}).get("operating_margin_latest")
        results = results_summary(info, annual, today) if info else None
        news = clean_news(raw or [], ticker, name, today)
        officers = saved_officers.get(ticker, {})
        if info:
            officers = update_officers(officers_from_info(info), officers, today)
            if officers:
                saved_officers[ticker] = officers
        out[ticker] = {
            "unavailable": info is None and raw is None,
            "results": results,
            "news": news,
            "officers": officers,
            "flags": recent_flags(results, news, officers, today),
        }
        time.sleep(0.4)  # be polite to Yahoo

    OFFICERS_FILE.write_text(json.dumps(saved_officers, indent=1, sort_keys=True) + "\n")
    RECENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RECENT_FILE.write_text(json.dumps({"date": today.isoformat(), "companies": out}))
    return out
