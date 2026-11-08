# The v37 timeline — kept active

Dave, 2026-09-26: this stays live, and it gets retested whenever something new is found.

## How to add something new
1. Add the event or state to tl_build.py (INTRADAY / DAILY / CALENDAR / MACRO / STATES).
   Stamp it with the moment it was known. Add a self-test that fails if it is stamped early. The VX bug is the reason for this rule.
2. Bump the tl_build version and rebuild matrix.npz. Record the new sha.
3. Write a new pre-registration naming the new features and the test data.

## The rule for retests
- Everything up to 2026-08-14 has now been looked at (v37.2 sealed test, v37.3 eras).
- A retest that claims evidence must be scored on data after the last look: forward data, or instruments never used (e.g. v38's new indices).
- Retests on old data are allowed, but they are descriptive only.

## Defaults learnt so far
- Label: direction only (up-first among barrier hits). The magnitude label predicts volatility, not direction (v37 void).
- Train on all history with an expanding window, not a short recent window (v37.3 Part B).
- Direction AUC so far is 0.52–0.58, with +1.5 bp a trade at best, t 1.4. Not tradeable yet.

## Record of retests
- **v54 (2026-10-02), market internals** (put/call USI:PCC, VIX/VIX3M, S5FI/S5TH breadth, NYSE ADD/ADV/DECL, Zweig thrust); 20 features via tl_build3.py, data/tv_20261001.
  - Scored on US30 + NAS100, never used by any timeline model.
  - **FAIL:** AUG − BASE = +0.0009, 95% CI [−0.0035, +0.0050]. The internals are redundant with what the timeline already has. Family closed.
  - By-product: BASE (the v40 model) scores **AUC 0.540 (lower bound 0.528) on US30 + NAS100**, a second out-of-market replication.
  - tl_build3.py stays as a library. The default timeline is unchanged (tl_build 1.1 / tl_build2).

## Inputs now come from the TradingView connector (2026-10-02)
- VIX, VX1/VX2 and SKEW for the live v41 record are appended from data/tv/ (tv_series.py 1.1, which refuses a pull that rewrites a stored value).
- The original files are never edited (PREREGISTRATION_v41.1).
- AAII, COT and FRED inputs come from data/v41/refresh/, which only the Mac's forward_tick.sh step 6 can fill.

## Record of retests (pending)
- **v59 (2026-10-11), slow macro: FAIL.** Credit spread, 10y-3m curve, fed funds, WTI, NFCI and jobless claims add nothing on US2000 (AUG−BASE +0.0009, CI [−0.0039, +0.0057]; 2018–21 negative). The slow-macro family is closed for the timeline, and tl_build4 is kept as a library. By-product: BASE scored AUC 0.535 on US2000 (lower bound 0.521), a third out-of-market replication. US2000 is now used. See RESULT_v59.md.
