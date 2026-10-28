"""Check outputs/dashboard.html before it is published.

Usage:
    python check_dashboard.py              # exit code 0 = safe to publish, 1 = don't
    python check_dashboard.py other.html   # check a different file

Opens the page in a headless browser (the way a reader would see it) and
fails if any of these are true:

  - the page throws a JavaScript error or shows no companies (a blank page)
  - any company is missing its sector (Yahoo rate-limiting can cause this,
    and it lets banks slip past the exclusion)
  - the number of companies moved by more than MAX_COUNT_CHANGE from the
    last committed scorecard (a sign something was wrongly included or dropped)
  - fewer than MIN_1D_SHARE of companies have prices for the 1D chart

Needs Playwright with Chromium (`pip install playwright && playwright install
chromium`). It isn't in requirements.txt because only the publishing step
needs it.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "outputs" / "dashboard.html"
MIN_COMPANIES = 60
MAX_COUNT_CHANGE = 5
MIN_1D_SHARE = 0.8


def committed_count() -> int | None:
    """Company count in the last committed scorecard, if there is one."""
    try:
        raw = subprocess.run(["git", "show", "HEAD:outputs/scorecard.json"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
        return json.loads(raw)["count"]
    except Exception:
        return None


def main() -> int:
    from playwright.sync_api import sync_playwright

    problems = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto((Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else PAGE).as_uri())
        page.wait_for_timeout(1500)
        rows = page.locator("#rows .row").count()
        data = page.evaluate("JSON.parse(document.getElementById('data').textContent)") if not errors else None
        browser.close()

    if errors:
        problems.append(f"page error: {errors[0][:200]}")
    if rows < MIN_COMPANIES:
        problems.append(f"only {rows} companies shown (need {MIN_COMPANIES}+)")
    if data:
        companies = data["scorecard"]["companies"]
        missing = [c["name"] for c in companies if not c.get("sector")]
        if missing:
            problems.append(f"{len(missing)} companies have no sector: {', '.join(missing[:5])}")
        before = committed_count()
        if before is not None and abs(len(companies) - before) > MAX_COUNT_CHANGE:
            problems.append(f"{len(companies)} companies vs {before} in the last committed scorecard")
        prices = data.get("prices") or {}
        with_1d = sum(1 for c in companies if (prices.get(c["ticker"]) or {}).get("1D"))
        if with_1d < MIN_1D_SHARE * len(companies):
            problems.append(f"only {with_1d} of {len(companies)} companies have 1D prices")
        print(f"{rows} companies shown, {with_1d} with 1D prices, as of {data['scorecard']['as_of']}")

    for prob in problems:
        print("FAIL:", prob)
    print("OK to publish" if not problems else "Do not publish")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
