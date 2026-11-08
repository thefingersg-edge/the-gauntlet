# Scoping: moving from indices to individual companies (2026-10-02)

Not a test, and nothing is pre-registered yet. This scopes the next phase so Dave can decide on data and a broker.

I am not a financial adviser. This is research direction, not a recommendation.

## Why switch
- **Index tests can't find what single stocks carry.** About 50 tests on indices, gold and FX found no direction edge after costs. Index effects average out: v45 showed rebalance pressure cancelling at index level.
- **The real-fills audit settled the cost question.** The cost model is right. Dave's profit was market drift (gold), minus financing.
- **Single stocks offer two things indices can't:**
  - *Breadth:* thousands of separate earnings and insider events a year.
  - *Room for a small trader:* small and mid caps are too small for funds to trade in size.

## Candidate effects, ranked
1. **Drift after an earnings surprise, in small and mid caps.**
   - The best documented. A Columbia study of 1974–2020 finds the long-good-news, short-bad-news return fell from about 5% a quarter in the 1980s–90s to 3% or less in the late 2010s, and was indistinguishable from zero across all stocks after 2017. It disappeared earlier for large firms than for microcaps.
   - A Caltech replication finds it unstable from quarter to quarter: 16% of quarters negative for the good-news side.
   - **Prior: weak in large caps, plausible in small and mid caps, and must be shown after 2017.**
2. **Earnings-day gap, continue or fade.** Needs intraday data. Second stage.
3. **Insider buying clusters** (Form 4, several insiders buying within a few days). Free from EDGAR, timestamped.
4. **Short-term reversal** (last week's losers against winners). Real but cost-heavy; low priority.

Published effects lose roughly half their strength after publication (McLean–Pontiff and later replications). Each test has to show the effect after 2015 and after costs, not just in full history.

## Data
| Need | Option | Cost (checked 2026-10-02) | Notes |
|---|---|---|---|
| Daily prices incl. delisted companies | **Sharadar Bundle, personal use** | **$29/month or $299/year** | Prices from 1998, fundamentals from 1990, 8-K events from 1993, insiders from 2005, S&P 500 constituents from 1957; about 20,000 companies including delisted ones |
| Same, with index-membership history | Norgate Platinum | $630/year | Delisted companies and historical constituents from 1990. Mainly an end-of-day package for trading platforms |
| Announcement *time* (before open or after close) | SEC EDGAR 8-K Item 2.02 acceptance timestamps | Free | Point-in-time and includes dead companies. Needed to place the trade on the right side of the announcement |
| Intraday bars (for the gap test) | Polygon, Databento and similar | To be priced at stage 2 | Not needed for the first test |
| Bid/ask history for small caps | Not in end-of-day data | — | Estimate the spread from daily high/low (Corwin–Schultz / Abdi–Ranaldo), and validate on a sample of real quotes |

Free price data (Yahoo, and the TradingView feed) drops dead companies, which flatters every backtest. **Not usable for this.**

## Vehicle and costs
- **Interactive Brokers UK, US shares:** USD 0.0035 per share commission, plus exchange and clearing fees, plus 0.03% currency conversion if not holding USD.
  - Example: 100 shares worth £5,000 costs about £1.77 in total.
  - A cash position has no financing charge, unlike the CFD overnight charge that cancelled Dave's profit.
- **Small-cap spreads are the real cost:** often 10–50 bp. A test must charge an estimated spread for each stock, not a flat figure.
- **Shorting small caps** adds borrow cost and availability problems. **The first test should be long-only** (buy good-news surprises), judged against a size-matched benchmark.
- **OANDA's single-stock range** is limited, and CFD financing would apply. Not the right vehicle for multi-week holds.

## Proposed first test (to pre-register after the data is in hand): PEAD1, post-earnings drift by size band
- **Universe:** all US common stocks priced above $5, in liquidity bands. Daily data, 2005–2026, including delisted companies.
- **Surprise:** standardised unexpected earnings (from Sharadar fundamentals) plus the announcement-day return (EAR), both known by the close of the day after the announcement.
- **Trade:** long the top decile, entered at the next open (after the EDGAR timestamp), held 20 and 60 trading days. Net of commission and an estimated spread.
- **Gates:**
  - positive net excess return over a size-matched benchmark;
  - every era, and **separately on 2018–2026**;
  - robust to the size band;
  - beats a random-entry null.
- **Power:** about 2,000 or more small and mid caps × 4 announcements a year × 20 years is over 100,000 events. Power is not the problem; costs and decay are.

## Decisions for Dave
1. Sharadar Bundle (one month, $29, to start) is the cheapest clean route. This is his purchase; I don't buy anything.
2. IBKR (or another share broker) only becomes relevant if PEAD1 passes.
