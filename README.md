# FTSE Quality Scorecard

A Python tool that scores UK-listed companies on the fundamental strength of
the underlying business, using numbers from their annual reports.

It does not try to predict share prices. It answers a narrower, more honest
question: **is this a strong business, and what is driving that view?** Every
score can be traced back to the metrics behind it.

## How it works

Companies are scored on four pillars, each out of 100, and combined into an
overall quality score.

| Pillar | Question it answers | Status |
|---|---|---|
| Profitability | Does it earn good returns on its capital, and is that improving? | Built |
| Balance sheet strength | Could it survive a bad few years? | Built |
| Earnings quality | Does reported profit actually turn into cash? | Planned |
| Valuation | Is the market price reasonable for what you get? | Planned |

Scores are **relative**: each metric is ranked against the other companies in
the group, so a score says how a company compares with its peers.

### Pillar 1: Profitability

| Metric | Formula | Why it matters |
|---|---|---|
| ROCE | EBIT ÷ (Total assets − Current liabilities) | Profit generated per pound of long-term capital invested |
| Operating margin | EBIT ÷ Revenue | Share of sales left after operating costs |
| Gross margin | Gross profit ÷ Revenue | Pricing power |
| Margin trend | Average yearly change in operating margin | Direction of travel, not just level |

EBIT means reported operating profit. Yahoo's own "EBIT" line is only used
as a fallback, because it is rebuilt from pre-tax profit and can include
non-operating gains (for Rolls-Royce in 2025 it overstated operating profit
by around £2.8bn).

Ratios with a zero or negative denominator are left blank rather than
reported as misleading numbers.

### Pillar 2: Balance sheet strength

| Metric | Formula | Better when |
|---|---|---|
| Net debt / EBITDA | (Total debt incl. leases − Cash) ÷ (Operating profit + D&A) | Lower |
| Interest cover | Operating profit ÷ Interest expense | Higher |
| Equity ratio | Shareholders' equity ÷ Total assets | Higher |

EBITDA is built from reported operating profit rather than taken from Yahoo's
EBITDA line, for the same reason as above. A company with debt and no
operating cash profit is ranked worst on leverage.

The **Altman Z''-score** (the non-manufacturer version) is reported alongside
as a cross-check but deliberately not scored. It misreads some healthy
business models: supermarkets run negative working capital by design
(customers pay at the till, suppliers are paid weeks later), which puts a
solvent Tesco in the "distress" zone.

### Overall score

For now, a simple equal-weighted average of the pillars built so far.

## Running it

Requires Python 3.10+.

```bash
pip install -r requirements.txt
python run.py          # fetches data and prints the scorecard
python -m pytest       # checks the calculations on hand-worked examples
```

Results are saved to `outputs/` (one CSV per pillar plus `overall.csv`).

Starter companies: Diageo, Rolls-Royce, Tesco, Burberry, Ocado.

## Data and limitations

Financial statements are pulled from Yahoo Finance via the `yfinance`
library, which typically provides four years of annual data. Line-item names
vary between companies, so the code checks several possible labels for each.
Free data has gaps and occasional errors; important figures should be checked
against the company's published annual report.

## Project structure

```
scorecard/data.py           fetching statements (the only part that uses the internet)
scorecard/statements.py     reading line items, shared by every pillar
scorecard/scoring.py        percentile ranking into scores /100
scorecard/profitability.py  pillar 1 metrics
scorecard/balance_sheet.py  pillar 2 metrics
run.py                      runs the scorecard end to end
tests/                      tests using invented, hand-checkable numbers
```
