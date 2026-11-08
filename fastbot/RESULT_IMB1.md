# RESULT — IMB1: the 15:50 closing-auction imbalance points the right way for the last minutes, but too weakly to trade. FAIL.

```
SPEC:     PREREGISTRATION_IMB1.md  sha 30687efc…
DATA:     Databento imbalance (XNAS.ITCH, XNYS.PILLAR) + SPY bbo-1s, 2018-05 .. 2026-09; 2,197 days, all pulled (2,098 trading days); median 484 members reporting
METHOD:   singlestock/imb1_run.py; log data/run_imb1.log
RUN:      2026-10-07
VERDICT:  G1 FAIL  G2 FAIL  G3 FAIL  -> FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
1,848 days with a signal (2019-05 .. 2026-09); SPY 15:51 -> 16:00 return SD 19.1 bp
G1 slope +0.70 bp per z (t +1.62)                                           FAIL
G2 |z| >= 1: 486 trades, gross +0.53 bp, net -0.47 bp after 1 bp (t -0.60)    FAIL
G3 2019-20 +1.93 | 2021-23 -1.65 | 2024-26 -0.85 bp net                      FAIL
reported: |z| >= 2 (92 days) +2.52 bp net (t 1.54); Nasdaq-only +0.43 (t 1.1); NYSE-only +0.70 (t 1.5)
          slope by period 2019-20 +1.58 | 2021-23 +0.19 | 2024-26 +0.72
```
## Read it plainly
- **The sign is right** (buy imbalances are followed by slightly higher prices into the close), in every period and on both exchanges, but the effect is about half a basis point — smaller than the cost of trading it, even at OANDA's tight closing spread.
- The largest imbalances (|z| ≥ 2) look better (+2.5 bp) but on only 92 days and at t 1.5; that is a slice chosen after seeing it, not a result.
- Conclusion: closing-auction flow is mostly absorbed before 15:51. No forward record (it does not meet the recent-regime rule: 2021–23 is negative).
