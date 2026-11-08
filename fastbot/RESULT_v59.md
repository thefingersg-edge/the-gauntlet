# RESULT — v59: slow macro adds nothing to the event timeline, and the timeline's own small signal replicates on a third unseen market

```
SPEC:     PREREGISTRATION_v59.md  sha d1339ab1…  (frozen before any v59 data was pulled)
METHOD:   tl_build4.py 4.0, v59_build.py, macro_v59.py (mechanical copies of the v54 pipeline; shas in PROVENANCE)
DATA:     FRED DBAA, DAAA, T10Y3M, DFF, DCOILWTICO, NFCI, ICSA (pulled 2026-10-10); OANDA US2000_USD 5m bid/ask 2005 → 2026-10
RUN:      2026-10-11       LOG: data/v59/run_v59_test.log
GATE 0:   SPX rebuilt by tl_build4 matches the v37 matrix exactly (91,116 of 91,116 rows; 125 base features and labels identical): PASS
VERDICT:  G1 FAIL (lower bound −0.0039)   G2 FAIL (2018–21 negative)   -> FAIL, as predicted
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## Numbers (AUC on hit points, 2013-01-01 → 2026-08-14; trained on SPX only, yearly walk-forward)
```
US2000 (never used before)   n 24,869   BASE 0.5353   AUG 0.5363   diff +0.0009   95% CI [-0.0039, +0.0057]
eras (AUG - BASE)            2013-17 +0.0020   2018-21 -0.0021   2022-26 +0.0029
SPX (training market)        BASE 0.5503   AUG 0.5507   diff +0.0004   (descriptive)
```

## Read it plainly
- **Credit spreads, the yield curve, Fed moves, the oil trend, financial conditions and jobless claims add nothing** to two-hour direction calls. The difference is +0.0009, inside the noise, and negative in 2018–21.
- **The model *uses* the slow states:** the curve ranks 14th of 145 features and NFCI 15th. But using them does not improve prediction. Slow states mostly let the model tell eras apart, not tell up from down tomorrow afternoon.
- **The slow-macro family is closed for the timeline.** tl_build4 stays a library.
- **Reported, the useful by-product:** BASE (the v40 model, trained only on SPX) scores **AUC 0.535 on US2000, 95% lower bound 0.521**. That is a **third out-of-market replication** of the timeline's small direction signal: 0.512 on five non-US indices (v40), 0.540 on US30+NAS100 (v54), and now 0.535 on the Russell 2000.
  - The signal is real and keeps transferring.
  - It is still too small to trade on its own (+1.5 bp a trade at best, t 1.4, from v40).

## Housekeeping
- **Spec typo:** the summary line says "9 states, 21 features". Its table defines 8 states, so 20 features were built. The table governed, and this was logged in PROVENANCE before the build.
- **Data:** US2000 is now on disk and has been used once (v59). It is no longer "unseen" for future timeline tests.
