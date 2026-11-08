# RESULT — FLOWS-2: the Friday before Treasury's borrowing estimates

```
RUN:      2026-09-26 20:11:58 UTC, once, on Dave's Mac (pineport/.venv)
SPEC:     PREREGISTRATION_REFUNDING.md sha256 1325073b...; event table 57be5dea...
          both checked at run time
CODE:     refunding.py as committed in 64fe651; common.py as in 8079914
EVIDENCE: data/refunding_run.log, data/refunding_result.json, data/refunding_trades.csv
VERDICT:  ALL GATES PASS, as registered -- the first in the programme.
          But the effect has decayed to nothing since 2019 (section 3).
```

*Measurement, not a recommendation. Not financial advice.*

## 1. The gates, as registered

| gate | result | |
|---|---|---|
| G1 replication, 2005-2023 | d +9.78 bp, t +2.14, n 4,882 days, q 0.064 | PASS |
| G2 eras | E1 +18.68 bp (t +2.22), E2 +5.94 (t +0.95), E3 +1.30 (t +0.21) | PASS (sign only) |
| G3 post-paper, 2024-Q1 on | mean +3.04 bp, n 11 | PASS (sign only) |
| G4 placebo, one week earlier | d +2.49 bp, t +0.65 | PASS |
| G5 trade, net | +8.81 bp a trade (t +2.24, n 87); +2.81 bp at +3 bp/side stress | PASS |
| G6 FOMC interaction | +15.58 bp with FOMC before, +6.50 without | sign as the paper |
| secondary USB30Y / DE10YB | +12.72 bp (t +1.76) / +5.13 bp (t +1.20) | descriptive |

No kill condition fired. The replication agrees with Wang & Zhao in size
(their 10-year: 12.6 bp) and in the FOMC interaction. The Friday control and
the placebo both did their jobs: this is not a generic Friday bond effect.

## 2. What the registered verdict does not show

The era gate asked only for a positive sign in each era. That was too weak a
test, and it is the lesson of this run. The coefficients fall
**18.7 → 5.9 → 1.3 bp**; only E1 is individually significant.

## 3. Post-hoc description — not a gate, not a test

Computed after the run from `refunding_trades.csv`, reported because the
registered numbers alone would overstate the result:

| period | net per trade | t | n | wins |
|---|---|---|---|---|
| E1 2005 – 2012-03 | +17.79 bp | +2.20 | 29 | 20 |
| E2 2012-04 – 2019-06 | +8.26 bp | +1.38 | 29 | 20 |
| E3 2019-07 – 2026-08 | **+0.39 bp** | +0.06 | 29 | 17 |
| post-paper, 2024 on | **+0.45 bp** | | 11 | 6 |

The five best events carry **54% of the total** profit: 2011-07-29, 2008-01-25,
2009-07-31, 2009-10-30, 2015-01-30. The first falls days before the August
2011 debt-ceiling deadline, consistent with the paper's finding that the gain
roughly triples under fiscal stress. That is a description of where the edge
came from, not a new hypothesis tested.

## 4. Why a forward test cannot rescue it

Net per event has a standard deviation of 36.7 bp. At four events a year:

- to confirm a 9 bp edge (the full-sample size) at t = 2 needs ~67 events, **about 17 years**
- to confirm a 3 bp edge (the post-paper size) needs ~600 events, **about 150 years**

## 5. What it means

Registered: pass. Honest reading: **a real effect that replicated on this
vehicle and has since decayed like the pre-FOMC drift did.** For the last seven
years the trade earned about zero after costs. Not tradeable on current
evidence, and not confirmable by waiting.

If anything survives it is conditional on fiscal stress, and that idea came
from looking at section 3. It could only be tested cleanly forward, on the next
debt-ceiling episode, under a new pre-registration written before it starts.

**For future pre-registrations:** era gates must require more than a sign —
at least a minimum effect size in the most recent era.
