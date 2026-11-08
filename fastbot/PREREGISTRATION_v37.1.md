# PREREGISTRATION v37.1 — the timeline test, direction only

Frozen 2026-09-26. Amends v37 **before any sealed row was loaded**.
Script: scripts/timeline_v37_1.py v1.1.

I am not a financial adviser. This is a measurement, not a recommendation.

## Why an amendment
- **v37 was voided by its own rule.** The v37 FIT (timeline_v37.py 1.0.1) gave validation AUCs of 0.70 (long) and 0.69 (short), and v37 §6 says an AUC of 0.65 or more is presumed leakage and voids the run.
- **The diagnostic** (scripts/tl_diag_v37.py, validation rows only) found **not leakage but a label flaw**:
  - p_long and p_short correlate +0.74;
  - p_long predicts the SHORT label at AUC 0.66;
  - both predict "some barrier is hit" at AUC 0.75, and the realised-vol ratio alone gets 0.74.
- The v37 label rewarded knowing that a big move is coming (volatility is predictable: RESULT_VOLCAUSE, t 47) rather than which way it goes.
- Among points where a barrier was hit, the v37 models' direction AUC was only 0.557.
- The v37 LOCK (sha 1c93ecf5…) is **never tested**.

## What changes
1. **The target is direction only.** Among decision points where a barrier was hit, UP-FIRST = 1 and DOWN-FIRST = 0. Points where neither or both were hit are excluded from fitting and from AUC.
2. **One LightGBM model** (the v37 parameters) is fitted on 2005–12 hit points, with early stopping on 2013–14 hit points. AUC is measured on 2015–19 hit points.
3. **G1:** validation AUC above all 20 day-shift nulls (direction labels shifted by whole days within the training hit points), and below the 0.65 leak void.
4. **Trading rule:**
   - it acts at every decision point, because the model cannot know in advance whether a barrier will be hit;
   - long when p ≥ the 90th percentile of validation p over all points; short when p ≤ the 10th percentile;
   - one trade at a time, as in v37.
5. **Patterns:**
   - the v37 miner, scoring the up-first rate among hit points against the base rate;
   - the top 40 by |z| on 2005–14 must hold on 2015–19 with |z| ≥ 2 and the same sign;
   - up to 5 are frozen.

## What does not change
- Data, features, the timeline, the split, and the sealed period (2020-01-01 → 2026-09-17).
- G2 and G3: net > 0 and t ≥ 2.24; every sealed era > 0; above the 95th percentile of random entry.
- The LOCK-then-TEST protocol: one FIT, one TEST.

## Honest cost of the amendment
The 2015–19 validation fold has now been looked at once, by the voided run. What was learnt from it is that volatility features predict magnitude, which is already known and is not the question here. The sealed period is untouched.
