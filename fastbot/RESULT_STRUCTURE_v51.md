# RESULT — v51: break of structure and change of character. Both lose at every swing width, in every era and on every instrument. Following a structure break does slightly worse than entering at random.

```
SPEC:     PREREGISTRATION_v51.md  sha c57bd85d…
METHOD:   structure_v51.py 1.0; struct15.py sha a162ce2a… (causal swings/BOS/CHoCH); 15m mid bars SPX500, NAS100, XAUUSD (data/v24), UK100 (from data/v38 5m); to 2026-09-25; log data/run_v51.log
RUN:      2026-10-01
VERDICT:  CHoCH FAIL (G1-G4 all fail)   BOS FAIL (G1-G4 all fail)
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

Self-tests passed:
- **Causality:** events computed on truncated data are identical to the full-data events up to the cut point.
- **Gates:** a planted +5 bp passes, and a planted loss fails.

## Numbers (bp per 4h trade; SEs clustered by entry date; pooled over 4 instruments)
```
CHoCH   k=2  n 84,342  gross -0.48 (t -2.8)  net -2.65 (t -15.1)  excess -0.48
        k=3  n 64,851  gross -0.59 (t -2.7)  net -2.75 (t -12.6)  excess -0.59
        k=4  n 52,620  gross -0.77 (t -2.9)  net -2.90 (t -11.1)  excess -0.77
        k=5  n 44,466  gross -0.89 (t -3.1)  net -3.00 (t -10.3)  excess -0.89
        eras (k=3 net)  2005-12 -3.12   2013-19 -2.71   2020-26 -2.42
        instruments     SPX -2.01  NAS -2.01  UK100 -2.75  gold -4.27            ALL GATES FAIL
BOS     k=2  n 84,243  gross -0.84 (t -2.9)  net -3.02 (t -10.5)
        k=3  n 62,554  gross -0.43 (t -1.4)  net -2.62 (t -8.6)
        k=4  n 49,722  gross -0.27 (t -0.8)  net -2.46 (t -7.3)
        k=5  n 41,591  gross -0.22 (t -0.6)  net -2.40 (t -6.6)
        eras (k=3 net)  2005-12 -2.80   2013-19 -3.04   2020-26 -2.03
        instruments     SPX -2.33  NAS -1.57  UK100 -2.10  gold -4.36            ALL GATES FAIL
reported: longs/shorts both negative; "confirmed CHoCH" (first same-direction BOS) net -2.77 (t -7.8)
          1h bars, k=3: CHoCH -3.75, BOS -3.59
          random entry, same count and direction as CHoCH: net -1.89 (t -9.6)
```

## Read it plainly
- **No edge before costs, and a small negative one at that.**
  - After a change of character, price drifts slightly *against* the trade: −0.5 to −0.9 bp over 4 hours, significant at every width.
  - After a break of structure, the move is about zero.
  - The breaks don't lead anywhere. If anything, price leans back.
- **After the spread, every version loses 2–3 bp per trade.**
  - Entering at random bars with the same directions loses less (−1.9 bp).
  - Waiting for a "confirmed" change of character doesn't help, and nor do 1-hour bars.
- **This one is not killed by width fragility.** All four widths agree, and all of them are negative. The previous swing patterns failed because they were unstable; this one fails consistently.
- This fits what the programme found about intraday behaviour since about 2012. Short-term follow-through has gone (v35/v36), and a mild reversal dominates. A rule that buys breaks is on the wrong side of that.

## Caveats
- This is one mechanical, causal definition. Discretionary structure reading, multi-timeframe context and entries at order blocks or fair-value gaps are not covered.
- The 4h exit is fixed. Exit shapes are reported only, because exits do not rescue a zero-gross entry (result_v2).
