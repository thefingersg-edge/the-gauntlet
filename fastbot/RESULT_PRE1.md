# RESULT — PRE1: the predictable part of the closing imbalance is already in the price before 15:50. FAIL.

```
SPEC:     PREREGISTRATION_PRE1.md (sha in PROVENANCE); singlestock/pre1_run.py; log data/run_pre1.log
DATA:     IMB1 imbalances + SPY path (already on disk), 1,847 days 2019-05 -> 2026-09
RUN:      2026-10-08
VERDICT:  G1 PASS (mechanism)   G2 FAIL  G3 FAIL  G4 FAIL  -> FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
G1 the day's move (09:30 -> 15:50) predicts the imbalance: corr +0.17, t +6.7          PASS (mechanism is real)
G2 the day's move predicts 15:50:00 -> close: -0.13 bp per 1% (t -0.1)                FAIL
G3 position before publication on |day move| >= 1% days: 315 days, gross -0.02 bp, net -1.02 bp   FAIL
G4 2019-20 +5.1 | 2021-23 -2.6 | 2024-26 -4.7 bp                                       FAIL
reported: 15:50:00 -> 15:50:15 +0.4 bp per 1% (t 0.8); |day move| >= 2% (52 days) +1.9 bp net (t 0.3)
```
## Read it plainly
- **Leveraged-ETF style flows do show up in the imbalance** (big up days → buy imbalances, as the literature says) — but only explain a small part of it (correlation 0.17).
- **Being positioned before 15:50 earns nothing**: the predictable part is already priced in by 15:50. The 15-second jump comes from the *unpredictable* part of the imbalance — the part nobody could know in advance.
- The old "front-run leveraged ETFs" rule (|move| ≥ 2%) earned 0.6% a trade in 2006–11, mostly in late 2008 (Rodier et al. 2012, via CXO Advisory); here, 2019–26, it is +1.9 bp and noise. Another published edge competed away.
