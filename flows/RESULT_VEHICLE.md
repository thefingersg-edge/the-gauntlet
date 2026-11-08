# RESULT — FLOWS-15: fastbot v36 noise-band momentum on index FUTURES. DEAD (K2) as registered: it lost in 2013–17. Since 2018 it pays after costs on both ES and NQ.

```
SPEC:     PREREGISTRATION_VEHICLE.md (sha 23d6dde4…)
METHOD:   vehicle.py 1.1 (1.1 only adds a session cache, keyed to the raw files' sha256s, so
          the run fits the device time limit; rule and costs are unchanged); v36 rule N
          imported from fastbot/scripts/momentum_v36.py 1.0
DATA:     Databento GLBX.MDP3 ohlcv-1m, ES.v.0 / NQ.v.0 / YM.v.0, 2012-12 .. 2026-08
          ($51.83; sha256 per file in data/futures.meta.json); 55 roll sessions dropped per contract
COSTS:    one tick per side on every fill + $2.50 per contract round trip
RUN:      2026-10-10, once    log data/vehicle_run.log   result data/vehicle_result.json
VERDICT:  G1 PASS  G2 FAIL  G3 PASS  G4 PASS  ->  DEAD (K2)
```

*Measurement, not a recommendation. Not financial advice.*

## The registered test (2013-01 → 2026-08, bp per instrument-day)

| | gross | net | gate |
|---|---|---|---|
| ES | +3.96 (t 3.55) | +0.77 (t 0.69) | |
| NQ | +7.28 (t 4.96) | **+5.76 (t 3.92)** | |
| **pooled ES+NQ** | | **+3.23, t 2.71** (n 3,980) | **G1 PASS** (t ≥ 2.24) |
| eras, pooled net | | **2013–17 −1.48** (t −1.0), 2018–21 +6.48 (t 2.6), 2022–26 +5.65 (t 2.5) | **G2 FAIL** |
| excluding 2020–21 | | +2.71, t 2.13 | G3 PASS |
| futures gross vs the CFD gross (ES 3.96 vs SPX 3.22; NQ 7.28 vs NAS 6.39) | | | G4 PASS: same signal |

YM (secondary): gross +0.96, net −0.80. The Dow carries almost none of the signal, as on CFDs.

## By era, each contract (descriptive)

```
       2013-17                    2018-21                    2022-26
ES  gross +1.01  net -3.73     gross +6.87  net +4.05     gross +4.81  net +3.01
NQ  gross +3.51  net +0.88     gross +10.05 net +8.90     gross +9.00  net +8.38
```

## Read it plainly

- **The registered verdict is DEAD.** It fails on one gate: the 2013–17 era
  loses money net. That gate exists to stop exactly the "it only works
  lately" result. The verdict stands.
- **The vehicle question is answered, and the answer is yes.** On futures,
  the same rule with the same signal (G4) keeps most of its gross: NQ
  +7.3 → +5.8 bp net, against a CFD spread that took the whole edge. This
confirms v36's own diagnosis: the problem was cost, not signal.
- **2013–17 failed for two reasons: the signal was weaker, and costs were
  higher in bp.** A one-tick ES spread was 1–1.5 bp per side at 2013–17
  prices, against about 0.4 bp now. ES gross was only +1.0 bp then.
- **Unlike every flow tested in this project, this one has grown rather
  than decayed.** NQ net is +8.9 and +8.4 bp in the two recent eras. That is
  noted, not used: picking "NQ since 2018" now would be choosing the window
  after seeing it.
- **Break-even cost:** NQ about 2.2 bp per side per trade, ES about 1.2 bp.
  Today's real NQ cost is about 0.2 bp a side plus commission.

## What it leaves

1. **This is the strongest lead in the programme. It is still a lead, not a
   result.** The only honest confirmation is forward data. fastbot
   FORWARD_v36 is already recording NAS100 noise-band trades on the CFD. A
   forward record of the same rule on **NQ futures prices** (paper, logged
   daily, no parameter change) would be the matching pre-registration.
2. Any live version would need a futures broker and NQ's contract size
   ($20 × the index, about $500k notional per contract; micro MNQ is $2 ×).
   Sizing and risk would be a separate design question. Nothing here
   recommends trading it.
