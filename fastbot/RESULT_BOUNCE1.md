# RESULT — BOUNCE1: no reliable overnight bounce after closing imbalances (FAIL). Part B: the imbalance move happens in the first 15 seconds after publication.

```
SPEC:     PREREGISTRATION_BOUNCE1.md + BOUNCE1.1 (financing at the measured OANDA rate); shas in PROVENANCE
DATA:     IMB1 signal (data/imb1/days.csv) + Databento SPY bbo-1s path (data/imb1/spy_path.csv, 2,098 days, complete)
METHOD:   singlestock/bounce1_run.py; log data/run_bounce1.log
RUN:      2026-10-08
VERDICT:  G1 FAIL  G2 FAIL  G3 PASS  -> FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## Part A — overnight bounce (gated)
```
1,846 days; overnight SPY return (16:00:01 -> 09:30:30) SD 77 bp
G1 slope -2.68 bp per z (t -1.49): right direction (reversal), not significant          FAIL
G2 |z| >= 1, fade the imbalance overnight: 485 trades, gross +4.18 bp, financing +0.95 bp, net +2.23 bp (t 0.67)   FAIL
G3 net by period 2019-20 +1.2 | 2021-23 +1.6 | 2024-26 +3.8 bp                         PASS
reported: with the original flat 3 bp cost, net +1.18 bp (t 0.35)
```
Positive in every period but buried in overnight noise (SD 77 bp a night): far too weak to separate from zero.

## Part B — how long does the imbalance effect take? (DESCRIPTIVE)
```
SPY return from 15:50:00 to ...   slope (bp per z)   t
15:50:15                           +3.40            14.6
15:50:30                           +3.64            14.3
15:51:00                           +3.98            13.5
15:52:00                           +4.16            12.5
15:55:00                           +4.03             9.3
15:58:00                           +4.65             9.1
15:59:59                           +4.68             8.4
16:00:01                           +4.38             7.8
16:05 / 16:15 / 16:30 / 16:50      +3.59 / +3.16 / +3.35 / +3.69   (after-hours, thin)
```
- **About 75% of the whole move (+3.4 of +4.7 bp per z) happens in the first 15 seconds** after the imbalances are published; by 15:51 it is 85% done. Only about +0.7 bp per z is left after 15:51 — exactly what IMB1 found, and smaller than the cost.
- After the close about 1.5 bp per z gives back by 16:15, then holds; overnight a further, insignificant reversal (Part A).
- So our 9-minute window started too late to catch the effect, but the effect is a **seconds-scale** reaction — the domain of automated market makers, not something reachable through a retail CFD.
- Caveat: the first message for each stock arrives within 20 s of 15:50:00, so the 15:50:00 → 15:50:15 move is simultaneous with publication; part of it may be the same order flow showing up in prices and in the imbalance at once.
