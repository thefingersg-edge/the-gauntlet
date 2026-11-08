# PREREGISTRATION PEAD5: the EAR drift held for 120 trading days

Frozen 2026-10-03, straight after PEAD4 suggested the drift lasts beyond 60 days. Harness: `singlestock/pead5_run.py`, which pins this file. **Not independent of PEAD1–4**, which used the same events; the forward record is the real test. Main window: entries from 2005-01, exits by 2023-06-30.

I am not a financial adviser. This is a measurement, not a recommendation.

## Definition
- **Events:** PEAD1 long signals (top-decile EAR, M+S).
- **Trade:** enter at the open of k+2 (as PEAD1), hold **120 trading days**.
- **Return:** excess over the band. **Cost: the full EDGE spread plus commission (one round trip).**

## Gates (single test, t ≥ 2.0, clustered by quarter)
- **G1:** M+S net > 0, t ≥ 2.0.
- **G2:** net > 0 in 2005–12, 2013–17 and 2018–23H1.
- **G3:** net > 0 in M and in S.

## Reported
- 90 and 180 days.
- SUE-confirmed subset.
- Entries after 2023-06 (not clean).

## Prediction
G1 PASS, G2 uncertain (2005–12), G3 FAIL in M.

## One run.
