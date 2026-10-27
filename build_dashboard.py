"""Build the dashboard page from the latest results.

Usage:
    python run.py && python backtest.py && python build_dashboard.py

Reads outputs/scorecard.json and outputs/backtest.json, downloads price
history for the charts (1D to 5Y), embeds it all in dashboard/template.html
and writes outputs/dashboard.html, a single self-contained page.

    python build_dashboard.py --refresh   # also re-downloads daily prices
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scorecard.charts import price_history

ROOT = Path(__file__).resolve().parent


def main() -> None:
    data = {
        "scorecard": json.loads((ROOT / "outputs/scorecard.json").read_text()),
        "backtest": json.loads((ROOT / "outputs/backtest.json").read_text())
        if (ROOT / "outputs/backtest.json").exists() else None,
    }
    tickers = [c["ticker"] for c in data["scorecard"]["companies"]]
    data["prices"] = price_history(tickers, refresh="--refresh" in sys.argv)
    data["prices_built"] = datetime.now(timezone.utc).isoformat(timespec="minutes")
    # "</" inside a <script> block would end it early, so escape it
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    template = (ROOT / "dashboard/template.html").read_text()
    out = ROOT / "outputs/dashboard.html"
    out.write_text(template.replace("__DATA__", payload))
    print(f"Wrote {out.relative_to(ROOT)} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
