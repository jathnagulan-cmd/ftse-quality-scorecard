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
| Earnings quality | Does reported profit actually turn into cash? | Built |
| Valuation | Is the market price reasonable for what you get? | Planned |

Scores are **relative**: each metric is ranked against other companies, so a
score says how a company compares with its peers, not whether it is good in
absolute terms.

### Universe

The FTSE 100 (constituent snapshot from December 2025, in `data/universe.csv`),
plus Burberry and Ocado from the original watchlist. **Banks, insurers, asset
managers, investment trusts and property companies are excluded.** Their
accounts work differently (a bank's debt is its raw material, insurers have
no gross margin), so these metrics would be meaningless for them. That leaves
72 scored companies.

### Peer-relative margins

Gross and operating margins are driven by the business model, so they are
ranked only against similar companies. A supermarket's 7% gross margin is
not worse than a luxury brand's 68%; they are different businesses. Each
company is compared within its industry (e.g. Grocery Stores) when at least
three FTSE companies share it, otherwise within its sector, otherwise against
everyone. ROCE, margin trend and the other pillars are ranked across the whole
universe because they mean the same in any business.

This changed Tesco's profitability score from 50 to 70: its margins are thin
for the FTSE, but the best among UK grocers.

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

### Pillar 3: Earnings quality

| Metric | Formula | Better when |
|---|---|---|
| Cash conversion | Σ Operating cash flow (pre-interest) ÷ Σ EBITDA, all years available | Higher |
| Accrual ratio (Sloan) | (Net income − Operating cash flow) ÷ Average total assets | Lower |
| Receivables gap | Receivables growth − Revenue growth, latest year | Lower |

Two adjustments keep the comparison fair:

- **Interest classification.** IFRS lets companies show interest paid as
  either an operating or a financing cash flow (Rolls-Royce uses financing;
  the others use operating). Operating cash flow is restated to the same basis
  for every company: pre-interest when compared with EBITDA, post-interest
  when compared with net income.
- **Disposals.** A profit on selling a business sits in net income, but the
  proceeds are an investing cash flow, so a big sale looks like profit with no
  cash behind it. Disposal gains and losses are stripped out of net income
  first (Smiths Group's £1.7bn disposal gain had produced an accrual ratio of
  40% of total assets; adjusted, 4.7%).
- **Unstable profits.** Cash conversion is only calculated when EBITDA was
  positive in every year. Otherwise the summed denominator can be tiny and the
  ratio explodes (Ocado's first run showed 488%). Such companies rank last on
  that metric instead of being rewarded for it.

### Overall score

For now, a simple equal-weighted average of the pillars built so far.

## Known limitations

Flagged deliberately, so they can be fixed or at least understood:

- **Sector-structural leverage.** Regulated utilities (e.g. Severn Trent)
  carry high debt by design, financed against stable regulated income. The
  balance sheet pillar ranks leverage across all sectors, so it treats this as
  weakness. Same problem as gross margins had, same likely fix.
- **Classification quirks.** Yahoo classifies Ocado as a grocer. Its 38% gross
  margin reflects a technology and logistics model, which gives it a flattering
  rank against Tesco and Sainsbury's.
- **Negative equity from buybacks.** Asset-light companies that return large
  amounts of capital (e.g. InterContinental Hotels) can show negative equity,
  which the equity ratio reads as fragility.
- **Write-downs flatter the accrual ratio.** Large non-cash impairments push
  profit below cash flow, which the Sloan ratio rewards (e.g. Burberry).
- **Funding by share issues.** A loss-making company that raises equity
  repeatedly can score well on equity ratio despite needing outside money.
- **Stale constituent list.** The universe is a snapshot; four companies
  (Ashtead, Hargreaves Lansdown, Phoenix, DS Smith) returned no data, two of
  them having since been taken over.

## Running it

Requires Python 3.10+.

```bash
pip install -r requirements.txt
python run.py             # fetches data (cached after the first run) and prints the scorecard
python run.py --refresh   # re-downloads everything
python -m pytest       # checks the calculations on hand-worked examples
```

Results are saved to `outputs/` (one CSV per pillar plus `overall.csv`, which
has every company's rank and pillar scores). The first run takes a few
minutes; data is cached in `data/cache/` afterwards.

## Data and limitations

Financial statements are pulled from Yahoo Finance via the `yfinance`
library, which typically provides four years of annual data. Line-item names
vary between companies, so the code checks several possible labels for each.
Free data has gaps and occasional errors; important figures should be checked
against the company's published annual report.

## Project structure

```
scorecard/data.py           fetching and caching statements, sector exclusions
data/universe.csv           companies to score (edit to change the universe)
scorecard/statements.py     reading line items, shared by every pillar
scorecard/scoring.py        peer groups and percentile ranking into scores /100
scorecard/profitability.py  pillar 1 metrics
scorecard/balance_sheet.py  pillar 2 metrics
scorecard/earnings_quality.py  pillar 3 metrics
run.py                      runs the scorecard end to end
tests/                      tests using invented, hand-checkable numbers
```
