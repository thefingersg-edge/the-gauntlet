# RESULT — v54: market internals add nothing the timeline did not already know. FAIL, as predicted. The original timeline signal replicates on two more unseen markets.

```
SPEC:     PREREGISTRATION_v54.md  sha fb8718bb…  (frozen in commit f4a4c25)
METHOD:   tl_build3.py 3.0, v54_build.py, internals_v54.py 1.0 (sha 53cccaa4…); data/tv_20261001 (MANIFEST b287eb00…)
LOGS:     data/v54/build_spx_gate0.log, build_us30.log, build_nas100.log, predict.log, test_run.log
RUN:      2026-10-02
VERDICT:  G1 FAIL (lower bound -0.0035)   G2 FAIL (US30 negative; two eras negative)
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## Gate 0 — passed
tl_build3 rebuilt SPX500 with all 91,116 v37 rows matched. The 125 original features, labels, barriers and spreads are identical, so the new family was added without touching the old timeline.

## The test (FOREST trained on SPX hit points before each year; scored on hit points 2013-01-01 → 2026-08-14)
```
            n        BASE     AUG      AUG - BASE
US30      25,046    0.5323   0.5313   -0.0011
NAS100    24,681    0.5480   0.5508   +0.0029
pooled    49,727    0.5403   0.5412   +0.0009   day-bootstrap 95% CI [-0.0035, +0.0050]
eras      2013-17 -0.0032   2018-21 -0.0023   2022-26 +0.0049
SPX (training market, walk-forward, descriptive)   0.5503 -> 0.5528, +0.0025
```
- **G1 FAIL.** The pooled improvement is +0.0009, with a confidence interval centred on zero.
- **G2 FAIL.** The difference is negative on US30 and in two of three eras.
- The prediction (G1 fails) was right.

## What the forest did with the new inputs (reported)
- The **state** features rank high:
  - adr10 (10-day A/D ratio EMA) is 5th of 145;
  - put/call level is 10th, its z-score 16th;
  - ADD z is 17th.
- Together they take 14.8% of total importance, about their equal share (13.8%).
- The **event** features (breadth crossings, thrusts, washouts, VIX3M inversion) rank 48–118: near useless.
- **Reading:** the forest uses the internals in place of features it already had, not in addition to them. That is the definition of redundant information, and it is what the prior said: breadth and A/D restate the index's own trend, and put/call restates the VIX.

## The useful by-product: the v37 timeline signal replicates again
- BASE, which is v40's model, on two markets no timeline model has seen: **pooled AUC 0.5403, day-bootstrap 95% lower bound 0.5284.**
- v40 found 0.512 on five non-US markets. On US markets, whose own VIX, releases and positioning the features describe, the signal is much stronger, close to SPX's own 0.550.
- This is not a gate. It is still the cleanest out-of-market check the timeline has had, and it supports the live v41 record on NAS100.

## What follows (as registered)
- The internals family is closed for the timeline. tl_build3 stays as a library; the default timeline is unchanged.
- The series stay available: v56 (breadth vs next month) uses them directly.
- TIMELINE_LIVING.md is updated.
