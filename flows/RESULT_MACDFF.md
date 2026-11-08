# RESULT — FLOWS-16: the MACD "fake filter" on NQ futures. DEAD (K1, K2, K3).

```
SPEC:     PREREGISTRATION_MACDFF.md (sha 53b51890…)
METHOD:   macdff.py (self-tests pass: Pine EMA/RMA conventions, wave averages, crosses, costs,
          no look-ahead, entry/exit timing)   log data/macdff_run.log   result data/macdff_result.json
          trades data/macdff_trades.csv
DATA:     Databento NQ.v.0, 15-minute RTH bars from the FLOWS-15 1-minute files, 3,365 sessions
          (2012-12 warm-up, trades 2013-01 .. 2026-08), roll sessions dropped
RUN:      2026-10-19, once
VERDICT:  G1 FAIL  G2 FAIL  G3 FAIL  G4 FAIL  G5 PASS  ->  DEAD
```

*Measurement, not a recommendation. Not financial advice.*

## The registered test (net bp per trade: one tick per fill + $2.50 round trip)

| | result | gate |
|---|---|---|
| FF exhaustion crosses, 1,410 trades (628 long, 782 short) | **+0.09 bp**, t 0.06 (gross +1.01) | G1 FAIL |
| by era | 2013–17 +2.01, 2018–21 +0.38, **2022–26 −2.47** | G2 FAIL |
| FF minus plain MACD crosses | −1.44 bp (t −0.75) | G3 FAIL: the filter makes it worse |
| FF minus 20 random same-time, same-side, same-length trades | +0.87 bp (t 0.54) | G4 FAIL |
| size | 1,410 trades | G5 PASS |

## Read it plainly

- **The filter does not find better crosses.** Stretched crosses made
  nothing after costs (profit factor 1.005). Plain MACD crosses did slightly
  better (+1.5 bp, PF 1.08), but that was not gated and is not significant.
  Random trades at the same times did about as well.
- **It has got worse recently,** −2.5 bp a trade since 2022. That is the
  opposite of the noise-band rule, which has grown.
- **A stricter threshold made it worse** (1.5× average wave: −2.6 bp, PF
  0.88). So did 5-minute bars (−1.9 bp, t −2.5, PF 0.89) and ES (−0.8 bp).
  More filtering just meant fewer, worse trades.
- **The exhaustion idea doesn't hold intraday here.** 80% of the filtered
  trades were still open at 16:00: after a stretched move, the opposite cross
  that would close the trade rarely came the same day. The move did not
  snap back.
- **Why it looks good on a chart:** the dots land on visible turning points,
  but just as many land in the middle of moves that keep going. Measured
  over 1,410 trades, the hits and the misses cancel.

## What this closes

The MACD "fake filter" family on NQ and ES futures, intraday, at futures
costs. Under rule 2 it is not re-tested with other MACD lengths, wave
counts or thresholds. The corrected Pine indicator stays in `pine/` as a
visual aid only.
