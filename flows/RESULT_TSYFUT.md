# RESULT — FLOWS-17: the auction concession replicates on Treasury futures, and the futures spread still eats it. NOT TRADEABLE.

```
SPEC:     PREREGISTRATION_TSYFUT.md (sha 8846965a…, frozen 6d8f48b, label-only relabel 987998d, both before any data)
METHOD:   tsyfut.py 1.0 (sha 088fb6810a62…); log data/tsyfut_run.log; result data/tsyfut_result.json
DATA:     Databento GLBX.MDP3 bbo-1m, ZN.v.0 and ZB.v.0, 2010-06-07 -> 2026-08-31 (5.76M / 5.73M records, 66 contracts each; $15.41)
EVENTS:   auction_events.csv (d1bfd601…), 856 auction days in sample (the spec's "858" was a row count, not a day count)
RUN:      2026-10-31, once
VERDICT:  A FAIL (G4)   B FAIL (B1)   C FAIL (C1)   ->  NOT TRADEABLE ON FUTURES at retail cost
```

*Measurement, not a recommendation. Not financial advice.*

## The registered run

| part | statistic | value | gate |
|---|---|---|---|
| A | R = POST − PRE, ZN, 852 days | **+2.76 bp, t 4.11** | G1 PASS |
| A | eras E1 / E2 / E3 | +7.54 / +1.84 / **+2.51** (E3 = 91% of full) | G2 PASS |
| A | PRE / POST | −1.79 / +0.96 | G3 PASS |
| A | trade net (2 round trips) | **−0.46 bp**, t −0.68; E3 −0.80 | **G4 FAIL** |
| A | placebo, 3,214 non-auction weekdays | R −0.71, t −2.03 | G5 PASS |
| B | pre-auction short only, net | +0.19 bp, t 0.35; E3 +0.17 | **B1 FAIL**, B2 PASS |
| C | 10-year auctions, 5 sessions either side, 187 events | gross +5.25 (t 0.66), net +2.06 (t 0.26); E3 net +3.14 | **C1 FAIL**, C2 PASS |

The pre-registered predictions were G1 PASS / G4 FAIL, B FAIL, and C FAIL with a positive sign. **All three came true.**

## Reported (not gated)
- **Cost arithmetic, measured:** the median ZN spread is 1.00 tick = 1.25 bp, and commission is 0.16 bp a side. Two round trips cost about 3.2 bp against +2.76 bp gross.
- **ZB, 30-year auction days (195):** R +4.74 bp (t 1.48). Trade net −0.45. C-style legs: gross +13.3, net +8.1 (t 0.59).
- **Post-Robeco, 2025-04 → 2026-08 (84 days):** A R −0.38, A net −3.93, B net −2.64. Too few days to test, but there is **no sign of the effect since a large manager published that it trades it.**
- **C placebo** (legs anchored on the 10th session after each 10-year auction): gross +12.76 (t 1.71). That is larger than C itself (+5.25). **The 5-day "cycle" is not auction-specific;** it is the bond drift over the sample.
- **The A placebo is negative** (t −2.03; G5 passes as written, because the gate tests t < 2). On ordinary days the 10:00–16:00 shape goes the other way, which makes the auction-day contrast, if anything, slightly larger. It does not change the trade.
- **By tenor:** positive for most tenors. New 10-year issues alone are −3.13 (n 65), against +6.8 / +7.6 for the 10-year reopenings. Descriptive; small samples. (The log prints tenor years truncated to integers.)

## How to read it, plainly
- **The effect is real and has not decayed through 2019–26.** It replicates on a second vehicle at almost exactly FLOWS-11's size (+2.76 vs +2.91 bp) and passes every replication gate.
- **The vehicle was not the only problem.** Futures halve the cost compared with the CFD, but a one-tick spread crossed four times is still more than the edge. The CFD and futures failures are the same failure.
- **The one remaining route is passive execution** (resting limit orders, earning the spread rather than paying it). That is a different question: it needs order-book data to model fills, and it is exactly where professional market makers compete. With no sign of the effect since 2025-04, it is **not recommended.**
- **Closed under Rule 2.** FLOWS-11 and FLOWS-17 together close the Treasury auction concession for retail aggressive execution.
