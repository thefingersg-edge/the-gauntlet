# PREREGISTRATION PEAD2: does the PEAD1 drift survive if bought and sold in the closing auction?

Frozen 2026-10-03. Harness: `singlestock/batch2_run.py pead2`, which pins this file. Same data, signal and bands as PEAD1 (frozen engine, cached signals).

I am not a financial adviser. This is a measurement, not a recommendation.

## What is already known (stated before the run)
- PEAD1 found +1.10% gross (t 3.9), and about zero after a full EDGE spread.
- A post-hoc check (open execution) showed that at 25% of the EDGE cost, net is +0.83% full sample (t 3.0) and **2018+ only t 1.8**. This test is therefore **not independent of what has been seen**. Its job is to fix the execution model for the forward test, and to see whether the cost case holds when execution is at the close.
- The "cheapest third" variant is **not** registered, because its outcome was already seen post-hoc (net +0.27%, t 1.0).

## Definition
- **Signal:** the PEAD1 long signal (top-decile EAR, M+S bands), known at the close of k+1.
- **Entry:** in the closing auction of k+2.
- **Exit:** in the closing auction 60 trading days later.
- **Return:** excess over the band benchmark over the same closes.
- **Cost:** **25% of the EDGE spread** plus 2 × $0.0035/price commission. A closing auction prints one price for buyers and sellers, so there is no half-spread to cross. 25% stands in for auction impact.
  - **This number is an assumption.** It is the one thing a forward record must measure.
  - Reported at 0%, 50% and 100%.

## Gates (single test, t ≥ 2.0, SEs clustered by quarter of entry)
- **G1:** M+S mean net excess > 0, t ≥ 2.0.
- **G2:** net > 0 in 2005–12, 2013–19 and 2020–26, **and** 2018–26 net > 0 with t ≥ 2.0.
- **G3:** net > 0 in M and in S separately.
- **G5:** calendar-time excess portfolio (equal weight of open positions, cost on the entry day), Sharpe ≥ 0.5 on 2018–26.

## Prediction
G1 PASS. G2 FAIL, on the 2018+ t-statistic. G3 FAIL in M (the mid band had almost no gross drift).

## One run.
