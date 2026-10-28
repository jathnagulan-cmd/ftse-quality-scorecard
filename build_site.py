"""Turn the dashboard into a standalone website for GitHub Pages.

Usage:
    python build_dashboard.py && python build_site.py

outputs/dashboard.html is written as a page fragment (head tags and body
markup together, the format Claude artifacts expect). This wraps it in a full
HTML document and writes _site/index.html, which the GitHub Actions workflow
(.github/workflows/site.yml) publishes to GitHub Pages.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "outputs" / "dashboard.html"
SITE = ROOT / "_site"
BODY_START = '<div class="wrap">'

DESCRIPTION = ("FTSE 100 companies ranked on profitability, balance sheet strength, cash quality and "
               "valuation from their annual reports, with news and results since. A research screen, not advice.")


def main() -> None:
    page = SOURCE.read_text()
    if BODY_START not in page:
        raise SystemExit(f"{SOURCE.name} doesn't look like the dashboard (no {BODY_START!r})")
    head, body = page.split(BODY_START, 1)
    head = head.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
    html = f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="{DESCRIPTION}">
<meta property="og:title" content="FTSE Quality Scorecard">
<meta property="og:description" content="{DESCRIPTION}">
<meta property="og:type" content="website">
<style>body {{ margin: 0; }}</style>
{head.strip()}
</head>
<body>
{BODY_START}{body}
</body>
</html>
"""
    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(html)
    (SITE / ".nojekyll").write_text("")  # serve files as-is, no Jekyll processing
    print(f"Wrote {SITE.name}/index.html ({len(html) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
