# RESULT — BREADTH2: v56's breadth effect does not survive. Zero in the unseen years (1998–2006), and below the bar without survivorship bias.

```
SPEC:     PREREGISTRATION_BREADTH2.md  sha 6d3f6896…
METHOD:   singlestock/breadth2_run.py; Sharadar S&P 500 quarter-end snapshots + adds/removes, point-in-time; log data/run_breadth2.log; series data/breadth2_series.npz
RUN:      2026-10-04
VERDICT:  G1 sign negative, not confirmed   G2 FAIL   G3 FAIL   -> FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
point-in-time breadth: 7,151 days 1998-03-31 .. 2026-09-02, member coverage 99.6%; corr with TradingView S5FI 0.998
G1 1998-05 .. 2006-12   slope  -4.22 bp per 10pp (NW t -0.21)        sign right, effect ~zero
G2 2007 .. 2026-08      slope -23.65 bp per 10pp (NW t -1.69)        FAIL (bar -2.0)
G3 breadth < 20 minus rest  +207.8 bp (NW t +1.82, 438 low days)    FAIL (bar +2.0)
reported: eras 1998-06 -4.8 (t -0.2) | 2007-12 -2.9 (t -0.1) | 2013-19 -40.5 (t -2.6) | 2020-26 -39.8 (t -1.9)
          OANDA SPX500 target 2007+: -22.7 (t -1.97); h = 5: -4.5 (t -1.1)
```
## Read it plainly
- **Survivorship was not the problem:** the point-in-time series is almost identical to TradingView's S5FI (correlation 0.998).
- **The problem is that the effect only exists after 2013.** On the nine years v56 never saw, it is zero, and 2007–12 is zero too. With the target and the whole period counted, it falls below every bar.
- v56 is therefore a post-2013 pattern of uncertain life, not a stable timing rule. No forward record is added.
