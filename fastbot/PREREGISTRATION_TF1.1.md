# PREREGISTRATION TF1.1: amendment — session and holding rules for 30m / 1h / 4h

Frozen 2026-10-07, before any pattern or structure has been computed at these timeframes (no harness has run).

I am not a financial adviser. This is a measurement, not a recommendation.

- **Problem found while writing the harness:** v2's engine requires a trade to open and close inside the US cash session on the same day. A 6-bar hold is 6 hours on 1h bars, which cannot fit in a 6.5-hour session, so 1h (and most 30m) tests would produce almost no trades by construction.
- **Change:** 30m, 1h and 4h all use the **24-hour CFD session** (bars aligned to UTC: 30m/1h on the clock; 4h on 00/04/08/12/16/20). The same-day rule is replaced by: drop any trade whose entry-to-exit calendar span exceeds 2 × (hold bars × bar length), which removes weekend and holiday gaps. Overnight financing is charged as in TF1 (BOUNCE1.1 rule). The cap of 4 trades per day per pattern stays (New York date).
- **1m is unchanged:** v2's engine as it is (US session, same-day exits); structure trades on 1m must also enter and exit within 09:00–16:00 New York on the same day.
- **Random-entry benchmark (all timeframes), made exact:** for each test, 20 random draws of entry bars with the test's own firing rate in each (New York hour × year) cell and the same side(s), run through the identical execution. Gate 2 = Welch t of (test mean − pooled random mean) ≥ 2.0.
- **Running order:** the harness runs one timeframe at a time (`tf1_run.py 30m|1h|4h|1m`), each once; the verdict table is compiled after all four. Bonferroni stays at 168 tests (t ≥ 3.4).
