# AMENDMENT A1 to FORWARD_NQ — a progress report every 50 trade-sessions

```
WRITTEN:   2026-10-11, before the first recorded session (2026-10-12). Base unchanged
           (sha de80d50c…). Frozen at its first commit; forward_nq.py pins it.
```

*Measurement, not a recommendation. Not financial advice.*

## The change

The base (§2) showed only counts until the 500th trade-session. Dave asked
for something to read along the way. From now on, **every 50 trade-sessions**
(50, 100, 150, …) the recorder writes `data/forward_nq_reports/report_NNN.md`
with:

- the running mean net and gross bp per trade-session, its t-statistic, and a
  95% interval;
- **the range a true +5.8 bp edge would produce at this sample size** (5.8 ±
  1.96 × 65/√n), so each report says whether the forward record is still
  consistent with the backtest. The same range is given for a true 0 bp;
- trades per session, the share of long trades, and the worst and best
  sessions;
- the same-day comparison with fastbot FORWARD_v36 (NAS100 CFD), and at
  report 100 onward the bbo-1m cost check from §3.

## What does NOT change

- **The reports are descriptive. They gate nothing and stop nothing.** The
  only stop before 500 is still the single interim check at 250 (mean net
  ≤ −2 bp). The verdict is still taken once, at 500, by F1 ∧ F2.
- **No report may lead to a change of rule, instrument, cost or start date.**
  Any change would be a new document and a new test.
- Looking at the running mean is a temptation, and that is why the expected
  range is printed beside it. At 50 trade-sessions the standard error is
  about 9 bp, so a mean anywhere from about −12 to +24 bp is consistent with
  the backtest. No single early report means much.
