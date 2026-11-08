# PREREGISTRATION TF1: candle patterns and market structure on 1-minute, 30-minute, 1-hour and 4-hour charts

Frozen 2026-10-07, before any 1-minute data has been pulled and before any pattern or structure has been computed on 30m/1h/4h bars. The harness (`scripts/tf1_run.py`) will be written to this spec and frozen by sha **before** it is run; it may only re-use the frozen definitions below.

I am not a financial adviser. This is a measurement, not a recommendation.

## What is being re-asked
- v2 (5-minute NAS100): 20 candle patterns × long/short = 40 tests, **all 40 negative**, and no better than random entries executed the same way.
- v51 (5- and 15-minute, four markets): break of structure (BOS) and change of character (CHoCH), **all fail** at every swing width.
- Question: is the answer the same on faster (1m) and slower (30m, 1h, 4h) charts?

## Fixed definitions (re-used, not re-written)
- **Patterns:** `scripts/patterns.py` 1.0 `detect()` — the 20 v2 patterns, thresholds frozen in PREREGISTRATION_v2 §3. Entry: stop at the pattern bar's high (long) / low (short), next bar only, gap fills at the open. Exit: open of the bar **6 bars later**. Non-overlapping per pattern, at most 4 round trips per day.
- **Structure:** `scripts/struct15.py` (pinned) `structure_events()` — BOS and CHoCH, swing widths k = 2, 3, 4, 5. Entry: open of the bar after the break, in the break's direction. Exit: close of the bar **16 bars later**.
- **Prices:** OANDA bid/ask; signals on the mid; fills at the actual bid/ask (each trade pays the quoted spread it met).
- **Financing:** any trade held across 17:00 New York pays the measured OANDA rate (BOUNCE1.1 rule: long r + 2.5%, short r − 2.5% a year, Friday ×3).

## Data, markets and windows (decided now)
| Timeframe | Built from | Hours | Primary window |
|---|---|---|---|
| 1m | **new OANDA M1 bid/ask pull** (`pull_m1.py`) | US cash session only (09:30–16:00 NY) | **2022-01-03 → 2026-09-25** (the low-spread regime; ~4.7 years) |
| 30m, 1h | 15m bid/ask in `data/v24` (resampled: first open, max high, min low, last close, open-bar spread) | US cash session only | 2005 → 2026-09-25, eras 2005–12 / 2013–19 / 2020–26 |
| 4h | same 15m files | 24-hour CFD session, bars on 00/04/08/12/16/20 UTC | 2005 → 2026-09-25, same eras |
Markets: **NAS100_USD and SPX500_USD**, pooled (standard errors clustered by entry date).

## Tests and gates
- Per timeframe: 40 pattern tests + BOS + CHoCH (each structure test pooled over k = 2..5, with every k required to have the same sign) = **42 tests; 4 timeframes = 168 tests.**
- A test **PASSES** only if all of:
  1. mean net return per trade > 0 with date-clustered t ≥ **3.4** (one-sided 5% after Bonferroni for 168 tests);
  2. it beats **random entries** executed identically (same bar count, same side, same session, 20 random draws matched on time of day and year) by t ≥ 2.0;
  3. positive in every era (30m/1h/4h) or in each of 2022–23 / 2024–26 (1m);
  4. at least 200 trades.
- **Recent-regime route (POLICY_RECENT_REGIME):** a 30m/1h/4h test that fails gate 3 only because 2005–12 is negative, but passes 1, 2 and 4 on 2013–2026, goes to a forward record, never to money.

## Prediction
All 168 fail. Expected false passes by chance: about 0.05.

## Data pull (Dave's Mac, only needed for 1m)
`python3 scripts/pull_m1.py --pull --instruments NAS100_USD,SPX500_USD --granularity M1 --sides B,A --start 2022-01-01 --data-dir ../data/m1_tf1`

## One run.
