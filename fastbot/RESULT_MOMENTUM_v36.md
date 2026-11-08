# RESULT — v36: noise-band and gamma-proxy momentum. Both FAIL the gate, both are real before costs.

```
SPEC:     PREREGISTRATION_v36.md  sha aeffbae5…
METHOD:   scripts/momentum_v36.py 1.0   log data/momentum_v36_run.log
GATED:    2013 → 2026-09-17, NET of quoted spread, SPX500/NAS100/US30 5m
VERDICT:  N FAIL   G FAIL
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## Numbers
```
                               2005-12 gross    2013-26 gross    2013-26 NET     net by era
N noise band (bp/instr-day)    +6.22 (t 3.45)   +3.42 (t 3.17)   +1.09 (t 1.01)  -2.07  +2.98  +2.89
G last 30m, hot-VIX days       +9.64 (t 3.74)   +2.57 (t 1.93)   +1.28 (t 0.96)  +1.81  +4.16  -1.56
  G contrast, other days       -0.58 (t -1.04)  -0.21 (t -0.69)
```

## Read it plainly
- **These are the first strategies in this project with a real edge before
  costs in the holdout.** The noise-band rule makes +3.4 bp per instrument-day
  gross (t 3.2) in 2013–26. The CFD spread on its ~1.7 trades a day costs
  2.3 bp, which leaves +1.1 bp (t 1.0). The problem is cost, not signal.
- **The gamma mechanism shows up clearly, and it is fading.** In 2005–12,
  last-30-minute momentum was +9.6 bp on hot-VIX days and nothing on other
  days, which is exactly Baltussen et al.'s prediction. In 2013–26 hot days
  still show +2.6 bp gross (t 1.9), but 2022–26 net is negative. That fits
  the 0DTE literature (dealers mostly long gamma since 2022).
- **NAS100 noise-band net is +4.35 bp/day (t 2.9).** This was NOT gated per
  instrument, so it is post-hoc. There is an a-priori reason to expect
  NAS100 to be best: COST_BUDGET (2026-08-17, before any signal) found it
  the only index with cost/vol ≤ 0.15. But choosing it now, after seeing
  this, is selection. The only honest confirmation left is forward data.
- **The 2013–17 era is negative for N (−2.07 net).** Spreads were wider then
  (about 3 bp on SPX in 2013 against about 0.7 bp now), so the net edge is
  partly a story of falling costs.

## What would change the verdict (not tested, stated for the decision)
- **Cheaper execution.** Index futures (e.g. micro Nasdaq) typically cost a
  fraction of a CFD spread per round trip. At about 0.5 bp a day instead of
  2.3, N's +3.4 bp gross would clear costs. That needs a futures broker and
  futures data, and it would be a new pre-registration, not a re-read of this one.
- **A forward test.** NAS100 noise-band on OANDA, logged from 2026-09-26, with
  no parameter changes.

## Caveats
- TWAP was used in place of volume-VWAP, with no leverage or vol sizing and
  CFDs in place of SPY.
- The paper's sample overlaps the holdout.
- The VIX-based "hot" day is a proxy, not dealer gamma.

## Addendum 2026-09-25 — longs vs shorts (POST-HOC, descriptive, gates nothing)
Script scripts/sides_v36_posthoc.py, log data/sides_v36_posthoc.log. Per trade, 2013–26, three indices:
```
          gross          net            drift (just being long/short then)   gross minus drift
LONGS     +2.35 (t 3.0)  +0.99 (t 1.3)  +0.54                                +1.81 (t 2.4)
SHORTS    +1.67 (t 1.6)  +0.30 (t 0.3)  -0.49                                +2.16 (t 2.1)
```
Longs look better only because the market rose (2013–26 was a bull market).
With that drift removed, the signal is the same size on both sides. Dropping the
shorts would swap a signal for market exposure, which is the kind of
regime-dependence this project is trying to avoid.
