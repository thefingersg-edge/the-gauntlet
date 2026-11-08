# PREREGISTRATION FORWARD_PEAD3: paper record of the earnings-drift signals from 2026-10-05

Frozen 2026-10-03. Recorder: `singlestock/pead_forward.py` (record / mark). Ledger: `data/pead3_forward.csv`, append-only. **Paper only; nothing is traded.**

I am not a financial adviser. This is a measurement, not a recommendation.

## Why forward
- PEAD3 passed every gate except 2005–12, and PEAD4 showed the recent years carry the strength. Every past window has now been looked at.
- **Only signals filed after 2026-10-05 can test it honestly.**

## What is recorded
Every PEAD1 long (top-decile EAR, M+S) whose first 10-Q/10-K is filed 0–60 days after the 8-K, with the filing on or after 2026-10-05. Each is tagged:
- **CONFIRMED** (SUE ≥ trailing 70th percentile): **the PEAD3 primary**;
- **not_confirmed**: the PEAD4 late-entry group;
- its band (M / S).

Entry at the open after the filing; hold 60 trading days; excess over the band; full EDGE cost plus commission.

## Data cadence
- Monthly: `sharadar_pull.py --refresh` (tables: tickers, stocks, actions, events, fundamentals; **the 5-year tier is enough**), then the pipeline stages, then `record` and `mark`.
- Signals are recorded **before** their outcome exists, and dated with the run.

## Verdict
- **Interim look:** 150 closed CONFIRMED trades.
- **Verdict:** 300 closed CONFIRMED trades, or 2028-03-31, whichever comes first.
- **PASS** = mean net > 0 with t ≥ 2.0 (clustered by entry month) **and** mean net > 0 in the S band.
- **Reported:** not_confirmed, M band, and the closing-auction cost variant.
- **Early stop:** only if t ≤ −3 at the interim.

## One verdict.
