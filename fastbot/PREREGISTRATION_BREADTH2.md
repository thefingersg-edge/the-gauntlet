# PREREGISTRATION BREADTH2: does v56 survive without survivorship bias, and on years it never saw?

Frozen 2026-10-04, before any point-in-time breadth series has been built. Harness: `singlestock/breadth2_run.py`, which pins this file.

I am not a financial adviser. This is a measurement, not a recommendation.

## Why
v56 (PASS, narrowly: slope −23.9 bp per 10 pp of S5FI, NW t −2.06, 2007–2026) used TradingView's S5FI, built from the index's members, and was only tested from 2007. Two doubts: survivorship in the series, and no out-of-sample period. Sharadar's S&P 500 table has quarter-end membership snapshots from 1998-03-31 plus every addition and removal, so both can be fixed.

## Construction (fixed now)
- **Membership on day t:** the latest quarter-end snapshot on or before t, plus additions and minus removals dated after that snapshot and on or before t. Tickers matched to the Sharadar price store; a day counts only if ≥ 90% of members have a price.
- **Breadth B_t:** % of members whose dividend-adjusted close on t is above their own 50-day simple average (needs 50 prior closes).
- **Target:** the equal-weighted average return of day-t members from the **open of t+1 to the close of t+20** (h = 20), from Sharadar prices. Entry is after B_t is known (B_t uses closes up to t).
- **Statistics:** OLS of the 20-day return (bp) on B_t / 10, Newey-West with 20 lags, as v56.

## Gates
- **G1 (unseen years, 1998-05-01 to 2006-12-29):** slope < 0 with NW t ≤ −1.645 (one-sided; the direction was fixed by v56). Budget: 8.7 years against v56's 19.7; with v56's effect size the expected t is only about −1.4, so **G1 is likely underpowered**. Accepted.
- **G2 (replication without survivorship, 2007-01-02 to 2026-08-31):** slope < 0 with NW t ≤ −2.0.
- **G3 (whole period, 1998–2026):** days with B_t < 20 minus all other days, 20-day return > 0 with NW t ≥ 2.0.
- **PASS needs G2 and G3, plus G1's sign negative.** G1 reaching −1.645 is reported as "confirmed out of sample".

## Reported (not gated)
Correlation of B_t with TradingView S5FI (2007+); the same regressions on OANDA SPX500 (open t+1 → close t+20, 2007+); h = 5; era slopes 1998–2006 / 2007–12 / 2013–19 / 2020–26.

## If it passes
A forward record of the point-in-time low-breadth regime on SPX500 (recording only), pre-registered separately.

## One run.
