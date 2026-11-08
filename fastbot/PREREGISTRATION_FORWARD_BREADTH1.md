# PREREGISTRATION FORWARD_BREADTH1: the post-2013 breadth effect, judged forward only

Frozen 2026-10-04, before the record's first day (2026-10-05). Part of the "recent-regime" track (POLICY_RECENT_REGIME.md).

I am not a financial adviser. This is a measurement, not a recommendation.

## Why forward only
BREADTH2 found the v56 effect (weak breadth → stronger S&P month) absent in 1998–2012 but consistent after 2013 (2013–19 slope −40 bp per 10 pp, t −2.6; 2020–26 −40, t −1.9). Picking "after 2013" after seeing the data is hindsight, so only new data can judge it.

## Definition (frozen)
- Breadth B_t and the 20-day target exactly as BREADTH2 (`singlestock/breadth2_run.build`, sha in PROVENANCE): point-in-time S&P 500 members, % above their 50-day average; target = equal-weighted member return from the open of t+1 to the close of t+20.
- Recorder: `singlestock/forward_breadth.py`, run monthly after the Sharadar refresh; ledger `data/breadth_forward.csv`.

## Verdict (once, at 2031-10-05: five years of new days)
- **G1:** OLS slope of r20 (bp) on B_t / 10 < 0 with Newey-West (20 lags) t ≤ −2.0.
- **G2:** days with B_t < 20 minus the rest > 0 (sign only; only about 15 such days a year are expected).
- PASS needs G1 and G2.

## Budget
At the 2013–26 strength (−40 bp per 10 pp), five years give an expected t of about −2.2; at the full-sample strength (−24) about −1.3. A PASS therefore needs the recent effect to be real and to persist.

## One verdict.
