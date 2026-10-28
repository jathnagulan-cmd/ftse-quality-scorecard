# FTSE Quality Scorecard

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jathnagulan-cmd/ftse-quality-scorecard/blob/main/scorecard_colab.ipynb)

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
| Valuation | Is the market price reasonable for what you get? | Built |

The three quality pillars and valuation are weighted equally in the overall
score, so quality carries 75% of the weight. On top of the scores, every
company gets plain-English **strengths, red flags and notes**, and a
**shortlist** picks out quality businesses at sensible prices (quality 60+,
valuation 40+, at most one red flag).

A second, **long-term shortlist** applies the same rules and also drops
cyclical industries and any company whose operating margin moved more than
3 points across the years available. It is meant for buying and holding
steady businesses for years. These extra rules come from that goal, not from
the backtest.

The dashboard also shows each company's **price trend** (1-month, 1-year and
5-year change, and distance from the 52-week high and low) with a note when a
share has risen more than 50% in a year or sits more than 30% below its
52-week high. These are shown for context and deliberately **not scored**:
price momentum works over months, not years, and rewarding it would push the
tool towards chasing whatever has recently gone up.

### Since the last annual report

The scores only see annual reports, so the dashboard also shows, for each
company, what has happened since (`scorecard/recent.py`, refreshed daily):

- **Newer results:** Yahoo's trailing-twelve-month operating margin, which
  includes any half-year or quarterly figures, compared with the margin in
  the last annual report (flagged when it moves 2+ points and 15%+), the
  latest period's sales and earnings growth, and the last and next results
  dates.
- **News:** headlines from the last 60 days that Yahoo links to the company,
  with multi-stock roundups dropped. Headlines that look like a profit
  warning, a management change, a deal or a legal or regulatory problem are
  flagged for 30 days.
- **Management changes:** the current chief executive and finance director
  are compared with `data/officers.json` and a new name is flagged for a
  year. The file is the baseline, so it's updated when the monthly refresh
  commits; changes only show up from the first commit onwards.

Companies with any of these warnings get a **Check first** tag. Like the
price trend, none of this is scored: headlines are noisy, Yahoo's interim
figures have gaps, and the backtest can't test them.

**This is a screen for deciding what to research, not a buy list.** The
scores read four years of accounts and nothing else, and the warnings above
are a prompt to read the latest results and announcements, not a substitute
for them.

## Backtest: has it worked?

`backtest.py` reruns the full scorecard at six past dates (May 2024 to August
2025) exactly as it would have looked then, using only accounts already
published (a four-month reporting lag) and that day's share price, then
measures each company's twelve-month total return including dividends.

| Signal | Top fifth beat bottom fifth | Typical gap (medians) |
|---|---|---|
| Quality (three pillars) | 5 of 6 periods | about +15 points a year |
| Valuation | 2 of 6 periods | slightly negative |
| Shortlist vs average company | 5 of 6 periods | about +4 points a year |

### Against a FTSE 100 tracker

The real alternative to picking shares is buying a FTSE 100 tracker fund and
doing nothing, so the backtest compares each list with one (iShares Core FTSE
100, dividends included).

| Over twelve months | Average return | Beat the tracker |
|---|---|---|
| FTSE 100 tracker | +15.7% | |
| Full shortlist | +20.1% | 4 of 6 periods |
| Long-term shortlist | −0.9% | 0 of 3 periods |

The long-term list needs three years of margins, so it only exists from 2025,
and in that year steady, defensive businesses badly lagged the market. Part of
the tracker's lead comes from banks, which the scorecard excludes: from May
2025 to May 2026 HSBC returned 65% and Barclays 47%. On this evidence, a
tracker would have beaten the long-term list, and that should be taken
seriously. Two-year returns are also reported, but only two dates have two
full years of history.

**Why the long-term list lagged.** Mostly style, partly two bad picks:

| Scored on | Long-term list | All non-cyclical companies scored | All companies scored | FTSE tracker |
|---|---|---|---|---|
| Feb 2025 (1 share) | +0.2% | +9.7% | +18.4% | +18.2% |
| May 2025 (7) | −8.3% | +10.3% | +17.9% | +21.9% |
| Aug 2025 (10) | +5.5% | +4.7% | +11.5% | +19.8% |

The list only holds steady, non-cyclical businesses, and in this window that
whole group trailed the market by 7 to 9 points while miners, airlines and
banks rallied. Inside the list, WPP (−54% from May 2025, −26% from August) and
Hikma (−30%, −18%) did most of the damage. The February list held a single
share, so it says almost nothing. The rules have not been changed in
response: three periods in one market can't separate a bad rule from an
unlucky year for defensive shares.

### Ideas tested and rejected

Three metrics from [valinvest](https://github.com/astro30/valinvest) (MIT
licence) were tried as extra parts of the quality score, rebuilt on Yahoo data:
cash ROCE (free cash flow ÷ capital employed), the share of years with ROCE
of 10% or more, and the yearly change in share count. Each one made the
backtest **worse**. The quality score's typical top-vs-bottom gap (medians) fell
from +15.2% a year to between +9.5% and +11.8%, and none had a signal on its
own. So none is scored. Cash ROCE and share count change are shown on the
dashboard as context, and a share count rising more than 2% a year is noted.

The quality signal looks real; valuation showed nothing in this window. The
weights have **not** been changed to fit this result: six overlapping periods
in one market are far too few to tune on, and doing so would make the
backtest look better while making the model less trustworthy. Limitations:
short history, overlapping periods, today's FTSE 100 as the universe
(survivorship bias), and no trading costs. One outlier shows why medians are
reported too: in February 2025 the model ranked Fresnillo near the bottom,
then silver prices exploded and it returned 432%.

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

### Peer-relative metrics

Some metrics are driven by the business model rather than business quality,
so they are ranked only against similar companies:

- **Gross and operating margin.** A supermarket's 7% gross margin is not worse
  than a luxury brand's 68%; they are different businesses.
- **Net debt / EBITDA and interest cover.** A regulated water company with
  government-set, inflation-linked revenue can safely carry far more debt
  than a fashion retailer.

Each company is compared within its industry (e.g. Grocery Stores) when at
least two FTSE companies share it, otherwise within its sector, otherwise
against everyone. ROCE, margin trend, stability and earnings quality are
ranked across the whole universe because they mean the same in any business.

### Handling cyclical companies

A score built on the latest year flatters companies at the top of their cycle.
With record silver prices, Fresnillo ranked 1st of 72. Two changes address it:

- **Multi-year averages.** ROCE and margins are averaged over every year
  available rather than taken from the latest year alone.
- **Margin stability.** A new metric scores how much operating margin swings
  from year to year. Quality businesses earn steady margins whatever the
  economy does. It is ranked universe-wide on purpose: within a sector, the
  least volatile miner would still score well.

Fresnillo moved from 1st to 20th and Antofagasta (copper) from 31st to 61st.
Note the related trap for valuation: cyclicals look cheapest on P/E at the
peak, exactly when profits are about to fall.

### Pillar 1: Profitability

| Metric | Formula | Why it matters |
|---|---|---|
| ROCE | EBIT ÷ (Total assets − Current liabilities) | Profit generated per pound of long-term capital invested |
| Operating margin | EBIT ÷ Revenue | Share of sales left after operating costs |
| Gross margin | Gross profit ÷ Revenue | Pricing power |
| Margin trend | Average yearly change in operating margin | Direction of travel, not just level |
| Margin stability | Standard deviation of operating margin across years (lower is better) | Resilience through the cycle |

ROCE and both margins are averages over every year available (usually four).

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
| Accrual ratio (Sloan) | (Net income − Operating cash flow) ÷ Average total assets, floored at −5% | Lower |
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
- **Write-downs.** Large non-cash impairments push profit below cash flow,
  which the raw accrual ratio rewards (Burberry: −13%). Values below −5% are
  treated as −5%, so a write-down earns no extra credit.
- **Unstable profits.** Cash conversion is only calculated when EBITDA was
  positive in every year. Otherwise the summed denominator can be tiny and the
  ratio explodes (Ocado's first run showed 488%). Such companies rank last on
  that metric instead of being rewarded for it.

### Pillar 4: Valuation

| Metric | Formula | Better when |
|---|---|---|
| EV / EBIT | (Market cap + Net debt incl. leases) ÷ Average operating profit | Lower |
| Free cash flow yield | Average (Operating cash flow before interest − Capex) ÷ EV | Higher |

Both use **average** profit and cash flow, because cyclicals look cheapest on
a single year's figures exactly at their peak. Market cap is converted from
the quote currency (pence, or dollars for IHG and Compass) into each
company's reporting currency. The latest-year P/E is shown but not scored:
Burberry's is 178 because its profits are temporarily tiny, while on
normalised figures it is cheap. Ranked across all companies, since cheap
means cheap in any sector.

## Known limitations

Flagged deliberately, so they can be fixed or at least understood:

- **Turnarounds are under-rewarded.** Averaging over four years drags in the
  bad early years of a genuine recovery, and the recovery itself shows up as
  margin instability. Rolls-Royce fell from 8th to 22nd when averages were
  introduced. The model can't yet tell a cyclical boom from a structural
  improvement.
- **Airlines and miners can still top the list.** Four years of data starts
  after the pandemic, so it contains no downturn for most cyclicals. They now
  carry a caution note, but their scores may still flatter them.
- **Four years is not a full cycle.** Commodity and economic cycles run 7-10
  years; the free data only covers about four.
- **Peer groups of two are coarse.** Beating your only rival earns full marks
  and losing earns half, so near-identical businesses can end up far apart
  (Severn Trent and United Utilities). Shrinking small-group ranks towards the
  middle would soften this.
- **Negative equity from buybacks.** Asset-light companies that return large
  amounts of capital (e.g. InterContinental Hotels) can show negative equity,
  which the equity ratio reads as fragility.
- **Funding by share issues.** A loss-making company that raises equity
  repeatedly can score well on equity ratio despite needing outside money.
- **Stale constituent list.** The universe is a snapshot; four companies
  (Ashtead, Hargreaves Lansdown, Phoenix, DS Smith) returned no data, two of
  them having since been taken over.

### Fixed so far

| Problem | Fix |
|---|---|
| Yahoo's EBIT included non-operating gains (Rolls-Royce +£2.8bn) | Use reported operating profit |
| Altman Z'' put Tesco in "distress" | Reported, not scored |
| Interest classified differently under IFRS | Restate all operating cash flow to one basis |
| Near-zero EBITDA gave Ocado 488% cash conversion | Require positive EBITDA every year |
| Supermarket margins penalised against luxury brands | Rank margins within industry |
| Disposal gain gave Smiths Group a 40% accrual ratio | Strip disposal gains from net income |
| Peak-cycle miners ranked top | Multi-year averages plus margin stability |
| Utilities penalised for normal regulated debt | Rank leverage within industry |
| Write-downs rewarded by the accrual ratio | Floor at −5% |
| Ocado classified as a grocer | Override in `data/universe.csv` |
| Cyclicals look cheap at the peak | Valuation on average profits, not latest |
| Quote and reporting currencies differ | Convert market cap via FX on the day |
| Backtest could use unpublished results | Four-month reporting lag in engine.py |
| One outlier skewed backtest averages | Report medians alongside means |

## Running it

The quickest way is the Colab notebook: click **Open in Colab** at the top of this page and run the cells. Nothing to install. To run it on your own computer instead:

Requires Python 3.10+.

```bash
pip install -r requirements.txt
python run.py             # scores everything and prints the shortlist with its flags
python run.py --refresh   # re-downloads statements and prices
python backtest.py        # tests the scores against past returns
python build_dashboard.py # builds outputs/dashboard.html from the latest results
python check_trading212.py  # optional: which companies are on Trading 212 (needs your API key)
python -m pytest       # checks the calculations on hand-worked examples
```

Results are saved to `outputs/`: one CSV per pillar, `overall.csv` (every
company's rank and scores), `shortlist.csv`, `backtest.csv`, and
`dashboard.html`, a single phone-friendly page with the shortlist, red flags
and a breakdown for every company. The first run takes a few
minutes; data is cached in `data/cache/` afterwards.

## Website

The dashboard is published with GitHub Pages at
**https://jathnagulan-cmd.github.io/ftse-quality-scorecard/**.
`.github/workflows/site.yml` rebuilds it every weekday after the London close
(and when the code changes): it scores everything with today's prices, fetches
news and newer results, runs `check_dashboard.py`, wraps the page with
`build_site.py` and deploys it. If Yahoo is unreachable or the check fails,
nothing is deployed and the site keeps its last good version. Run it by hand
from the **Actions** tab (Update website > Run workflow).

```bash
python check_dashboard.py   # opens the page in a headless browser; exit 1 = don't publish
python build_site.py        # wraps outputs/dashboard.html into _site/index.html
```

Trading 212 availability is left off the public page because it comes from
the owner's own account; it's still in `outputs/`.

## Trading 212 availability

Trading 212 publishes its instrument list only through its API.
`check_trading212.py` fetches it once with your own API key (create one in the
app with the **metadata** permission only, never trading access) and saves
`data/trading212.csv`, which holds only tickers and yes/no. Companies confirmed
as unavailable are left out of both shortlists; until the check has been run,
every company shows as "not checked" and nothing is excluded. The key is read
from your terminal environment and is never written to a file.

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
scorecard/valuation.py      pillar 4 metrics
scorecard/prices.py         share prices, exchange rates, market values
scorecard/engine.py         scores every company as of any date (point-in-time)
scorecard/flags.py          strengths, red flags, notes and the shortlist
backtest.py                 point-in-time backtest, with a FTSE 100 tracker benchmark
check_trading212.py         records which companies are tradeable on Trading 212
scorecard/trading212.py     matching companies to Trading 212 instruments
build_dashboard.py          builds the dashboard page
dashboard/template.html     dashboard page template
run.py                      runs the scorecard end to end
tests/                      tests using invented, hand-checkable numbers
```
