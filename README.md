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
| Balance sheet strength | Could it survive a bad few years? | Planned |
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

Ratios with a zero or negative denominator are left blank rather than
reported as misleading numbers.

## Running it

Requires Python 3.10+.

```bash
pip install -r requirements.txt
python run.py          # fetches data and prints the scorecard
python -m pytest       # checks the calculations on hand-worked examples
```

Results are saved to `outputs/profitability.csv`.

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
scorecard/profitability.py  pillar 1 metrics and scoring
run.py                      runs the scorecard end to end
tests/                      tests using invented, hand-checkable numbers
```
