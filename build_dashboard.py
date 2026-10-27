"""Build the dashboard page from the latest results.

Usage:
    python run.py && python backtest.py && python build_dashboard.py

Reads outputs/scorecard.json and outputs/backtest.json, embeds them in
dashboard/template.html and writes outputs/dashboard.html, a single
self-contained page.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    data = {
        "scorecard": json.loads((ROOT / "outputs/scorecard.json").read_text()),
        "backtest": json.loads((ROOT / "outputs/backtest.json").read_text())
        if (ROOT / "outputs/backtest.json").exists() else None,
    }
    # "</" inside a <script> block would end it early, so escape it
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    template = (ROOT / "dashboard/template.html").read_text()
    out = ROOT / "outputs/dashboard.html"
    out.write_text(template.replace("__DATA__", payload))
    print(f"Wrote {out.relative_to(ROOT)} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
