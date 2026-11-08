# PREREGISTRATION v37.2 — v37.1 again, on a timeline without a look-ahead bug

Frozen 2026-09-26. The sealed period has still never been loaded.

I am not a financial adviser. This is a measurement, not a recommendation.

## What happened
- **The v37.1 FIT** (timeline_v37_1.py 1.1.1) passed G1:
  - direction AUC 0.558 against a null maximum of 0.527;
  - the dominant feature and every top pattern was "VIX curve inversion within 1 day", with down-first 74% of the time.
- **This was a bug, and it flattered the result.** tl_build.py 1.0 dated every TradingView VX1!/VX2! daily close one day EARLY:
  - TradingView stamps CBOE futures bars at the session open, 17:00 Chicago on the previous calendar day;
  - vix_curve_budget.py had documented this and handled it, but tl_build 1.0 did not;
  - so each decision point could see the NEXT day's VIX-curve close, a full day of look-ahead.
- **Proof:** the day-to-day change in the VX1 close correlated +0.83 with the next day's VIX change and +0.19 with the same day's. After the fix, the VX curve correlates +0.61 with the same day and −0.11 with the day before.
- **The v37.1 LOCK (sha 85be5ec7…) is VOID and will never be tested.**

## The fix
- tl_build.py v1.1 (sha c3ce293356a1d447d89bc337598f28d1d5b59ada3a5ef0cfdfe43c04cd7225ad) maps each VX bar to its session date (Chicago time; 16:00 or later → next day).
- A self-test now fails if the VX curve lines up with the day before's VIX.
- The matrix was rebuilt: data/timeline_v37/matrix.npz, sha 6fc354b289c94cbf28b018e5f233e22d949c1f23cc6aeff3bc88aced09ce2088.
- No other series uses TradingView timestamps. VIX, SKEW, put/call, AAII, COT and FRED carry plain dates with publication lags as in v37 §3.

## The test
- Identical to v37.1 in every respect (direction only, same model, nulls, patterns, thresholds, gates and one-FIT-one-TEST protocol), run by scripts/timeline_v37_2.py.
- It refuses to run unless the matrix sha matches the one above.

## Honest cost
- The 2015–19 validation fold has now been used by two voided runs.
- Nothing in either was tuned to it. Both voids were caught by pre-registered rules or by distrusting a pass.
- A G1 pass here is still weaker evidence than a first look would have been. The sealed period is the real test.
