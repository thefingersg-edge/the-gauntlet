# AUDIT — v54 and v56, independent review (2026-10-02)

```
WRITTEN:  2026-10-02, after RESULT_INTERNALS_v54 and RESULT_BREADTH_v56
SCRIPT:   scripts/audit_v56.py      LOG: data/v56_audit.log
STATUS:   descriptive. Neither frozen verdict changes.
```

I am not a financial adviser. This is a measurement, not a recommendation.

## v56 (breadth -> next month): code correct; evidence weaker than NW t says

| check | result | reading |
|---|---|---|
| reproduction | slope −23.87 bp, t −2.06; low-minus-rest +229.6 bp, t +2.13 | **exact** |
| S5FI on t vs S&P return on t−1 / t / t+1 | corr −0.03 / **+0.76** / −0.03 | dated correctly, **no look-ahead** |
| ADD, same test | +0.01 / **+0.81** / −0.04 | same |
| columns, bar stamps | OANDA rows = bar start; open col 1, close col 4 | correct |
| rotation null (2,000 offsets ≥ 1 y) | one-sided p **0.048** (slope), **0.057** (dummy) | borderline |
| null sd of the NW t | **1.17 / 1.15**, not 1.0 | NW(20) overstates t by ~15–17% on this design |
| NW lag 20 / 40 / 60 / 120 | slope t −2.06 / −1.95 / −1.99 / −2.06 | stable, just at the line |

- **No coding error.** The harness does what PREREGISTRATION_v56 says.
- **The inference is the weak point.** On a null that keeps both series'
  autocorrelation, the slope t of −2.06 corresponds to about −1.76 on the
  standard-normal scale. With Hansen–Hodrick in RESULT_BREADTH_v56, two of three
  independent methods put it short of the bar.
- **Open question, not tested here.** Is S5FI < 20 just high VIX under another
  name? If it is, v56 measured the variance premium again (fastbot, z = 10), and is
  not a new effect. That is PREREGISTRATION_v57.
- **Lesson for future gates.** For overlapping-horizon regressions on a persistent
  regressor, register a rotation (circular-shift) null alongside NW. NW t was
  overconfident by about a sixth here.

## v54 (internals in the timeline): no error found that could flip the FAIL
- The design is paired: same seed, same training rows, and BASE is exactly the first 125 columns (checked by self-test).
- The bootstrap clusters by **date** across US30 and NAS100, which is right because the two markets share each day's shock.
- The walk-forward is strict (`S["date"] < Y-01-01`).
- The 2 h label horizon can leak a few hours across the year boundary. That would favour AUG and BASE equally.
- Not re-run here: the Cowork VM lacks scikit-learn and has no network to install it.
