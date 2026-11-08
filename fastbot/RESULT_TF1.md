# RESULT — TF1: candle patterns and market structure on 1-minute, 30-minute, 1-hour and 4-hour charts. 0 of 168 pass.

```
SPEC:     PREREGISTRATION_TF1.md + TF1.1 (shas in PROVENANCE); harness scripts/tf1_run.py (frozen before any run; later change mechanical only)
DATA:     OANDA NAS100 + SPX500 15m bid/ask 2005 -> 2026-09-25, resampled (24-hour CFD session); overnight financing charged at the measured rate
LOGS:     data/run_tf1_verdict.log; per-chunk results data/tf1/*.json
RUN:      2026-10-07
VERDICT:  1m 0/42, 30m 0/42, 1h 0/42, 4h 0/42 PASS  (Bonferroni t >= 3.4; must also beat matched random entries and be positive in every era)
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
                   pattern tests: mean > 0    beat random entries    best single test
1m (2022-26)       0 of 40                    16 of 40               exhaustion long -0.5 bp (t -1.8); median test -0.7 bp
30m                2 of 40                    20 of 40 (chance)      opening range long +1.4 bp, t 1.5
1h                 10 of 40                   14 of 40               key reversal long +5.4 bp, t 2.1 (275 trades)
4h                 16 of 36*                  14 of 36               inside bar long +7.4 bp, t 2.9
structure          BOS / CHoCH negative on every timeframe:
  1m  BOS -0.7 bp (t -5.1)   CHoCH -0.9 (t -9.2)
  30m BOS -1.4 bp (t -1.9)   CHoCH -2.8 (t -5.2)
  1h  BOS -4.0 (t -2.7)      CHoCH -0.5 (t -0.5)
  4h  BOS -8.8 (t -2.2)      CHoCH -9.6 (t -2.4)
* 4h: 'exhaustion' (needs a price gap between 24-hour bars) and 'opening range' (no 4h bar starts at 09:00 New York) never fire.
```
## Read it plainly
- **Same answer as 5-minute and 15-minute:** candle patterns do no better than random entries made the same way (about half beat random, as chance predicts), and following breaks of structure loses money on every timeframe — worst on the slowest.
- The longer bars look a little better per trade only because a longer hold collects more of the index's upward drift (more longs than shorts look "positive"); none survives the comparison with random entries plus the multiple-test bar.
- Two tests were flagged by the code as recent-regime candidates (1h hammer long, 4h doji long), but neither meets the policy (they must pass the significance and random-entry gates on 2013–26; neither comes close: t 0.2 and random-entry t −0.7). **No forward record.**
- **1-minute (added 2026-10-08, OANDA M1 2022-26):** every one of the 40 pattern tests loses money after the spread, exactly as on 5-minute (v2); structure breaks lose too. Faster charts make it worse, not better.
