# PREREGISTRATION BATCHB: four index ideas re-tested at single-stock level (B1–B4)

Frozen 2026-10-03. Built by `singlestock/batchB_build.py`, `batchB_select.py` and `batchB_engine.py`. Budget: `singlestock/budget_batchB.py`, log `data/budget_batchB.log`, which printed counts and RMS only. Outcomes for the main window are cached but **have not been looked at**. Harness: `singlestock/batchB_run.py`, which pins this file and the engine files.

I am not a financial adviser. This is a measurement, not a recommendation.

## Common rules
- **Universe:** M + S liquidity bands, US common stocks ≥ $5 (B1 also includes L).
- **Timing:** the signal is known at a close. Buy in the **closing auction of the next trading day**, and sell in the closing auction H trading days later.
- **Return:** the stock's total return minus its band's equal-weight return over the same closes.
- **Delistings:** as PEAD1.
- **Cost (primary):** 25% of the 60-day EDGE spread plus 2 × $0.0035/price (the closing-auction model from PEAD2). **G4 also requires a pass at 50% of EDGE**, so the result does not hang on the 25% assumption alone.
- **Main window:** entries from 2005-01-01, exits by **2023-06-30**. **Sealed: 2023-07-01 → 2026-09-30**, used once per survivor.
- **Bar:** four tests, Bonferroni, so **t ≥ 2.50**. SEs are clustered by the unit given below.

## The tests (direction fixed)
| | Signal | Hold H | Cluster | Long side |
|---|---|---|---|---|
| **B1** | Removed from the S&P 500 (Sharadar `removed`, effective date) | 60 | quarter | **deleted stocks** (rebound) |
| **B2** | Pre-earnings: 14 days before the predicted results date (same-quarter 8-K Item 2.02 date + 364 days) | 9 | week | all such stocks (run-up) |
| **B3** | Short-term reversal: bottom decile of the prior 5-day return each week | 5 | week | **last week's losers** |
| **B4** | Momentum: top decile of the 12-1 month return at each month end | 21 | month | **winners** |

## Gates (each test)
- **G1:** mean net > 0 (25% cost), clustered t ≥ 2.50.
- **G2:** net > 0 in 2005–12, 2013–17 and 2018–23H1.
- **G3:** net > 0 in M and in S separately. Not applied to B1, which has too few events.
- **G4:** mean net > 0 at 50% of EDGE.
- **Survivors only:** one sealed run, where net > 0 with t ≥ 1.0 confirms.

## Reported (not gated)
- B1 additions (expected to underperform).
- Costs at 0% and 100% of EDGE.
- L band for B2–B4.

## Budget (counts and squared returns only; main window)
```
B1  177 deletions, 65 quarters, 60d RMS 25.7%  -> MDE about 5-9%     (low power: literature rebound is a few %)
B2  186,583 events, 9d RMS 9.0%                -> MDE about 0.1% (event) to about 1% (week clusters)
B3  272,878 events, 964 weeks, 5d RMS 8.1%     -> MDE about 0.04-0.7%
B4  59,411 events, 217 months, 21d RMS 15.4%   -> MDE about 0.2-2.9%
median EDGE spread 72-99 bp, so the 25% cost is about 20-25 bp plus commission
```

## Predictions (written now)
- **B1:** FAIL (power).
- **B2:** G1 uncertain; this premium is small.
- **B3:** gross positive, net doubtful.
- **B4:** FAIL. Momentum in US stocks has been weak since 2009, with crashes.

## One run (plus at most one sealed run per survivor).
