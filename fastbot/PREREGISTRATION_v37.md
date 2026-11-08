# PREREGISTRATION v37 — the event timeline: can what happened before predict the trades we would have wanted?

Frozen 2026-09-26, before any model was fitted.
- **Build:** scripts/tl_build.py v1.0, which writes data/timeline_v37/.
- **Test:** scripts/timeline_v37.py v1.0.

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. The idea (Dave's)
- Mark, with hindsight, every point where a trade would have made money.
- Lay everything we have tested (plus standard indicators we have not tested) on one timeline of events, each stamped with the moment it was known.
- Ask whether any combination, or any "A then B" string of events in the minutes, hours or days before, predicts those points.

## 2. Symbol, decisions, labels
- **Data:** SPX500 (OANDA 5m bid/ask), 09:30–15:55 ET, 2005-01 → 2026-08-14 (the end of the 5m data).
- **Decision points:** 17 a day, at the bars closing 09:45, 10:00 … 13:45. Entry is at the next bar's open.
- **Label (triple barrier, on mid prices):**
  - target = stop = 1 × sigma(2h), where sigma(2h) = the RMS of 5m returns over the prior 20 sessions × √24;
  - horizon 24 bars (2h);
  - LONG wanted = the upper barrier is touched first; SHORT wanted = the lower barrier first;
  - a bar that touches both counts as a loss for both sides.
- **Base rates:** long-wanted 0.21 / 0.20 / 0.19; short-wanted 0.24 / 0.23 / 0.23 (train / validation / sealed).
- **Trade P&L:** barrier or timeout on mid, minus the entry bar's quoted spread (bid = ask before 2012, so train-era costs are zero; this does not matter, because nothing trains on P&L).

## 3. The timeline (125 features; every event stamped when it was known)
- **5m events (28):**
  - SMA20/50 cross, price crossing SMA20;
  - RSI crossing 70, 30 or 50; MACD signal cross; Bollinger 2σ breach;
  - 3σ shock (v35); new session high/low; opening-range breakout; sweep of the high/low;
  - v36 noise-band breach; v34 Rule-of-16 band touch;
  - engulfing bar, inside bar, NR7 bar.
- **Daily events (16), stamped 16:00 (gaps at 09:30):**
  - SMA50/200 cross, cross of SMA50;
  - NR7, inside day, engulfing;
  - 20-day high/low; 3-day streaks; ±2σ days; open gaps.
- **Calendar (5):** CPI, NFP and claims at release time; FOMC; FOMC press conference.
- **Macro and sentiment (21), each stamped at its publication time:**
  - VIX jump/drop and crossings of 20 and 30; VIX curve inversion/normalisation (VX1 vs VX2); SKEW crossing 140;
  - AAII bull−bear beyond ±20 (the next day); put/call crossing 1.0 (to 2019);
  - CFTC leveraged-fund net z beyond ±1.5 (report date + 3 days, 15:30);
  - 2-year yield 5-day change beyond ±20 bp; dollar 5-day change beyond ±1%; petrol week-on-week change beyond ±3%.
- **Encoding:**
  - for each event type: log(minutes since it last happened), plus counts in the last 60 min for 5m events;
  - 27 state values: time of day, day of week, return since the open, SMA distances, RSI, MACD, %B, gap, prior-day and 5-day returns, realised-vol ratio, VIX, VIX 5-day change, VX1/VX2, SKEW, AAII, COT z, yield and dollar changes, minutes to the next CPI/NFP/FOMC/claims (the schedules are public in advance), noise-band position, Rule-of-16 position, sigma.

## 4. Split (Dave's choice)
- Fit 2005–2012; early stopping on 2013–14; validation 2015–19.
- **Sealed 2020-01-01 → 2026-09-17, opened once.** The FIT stage never loads a sealed row.
- The whole pipeline runs in two stages. FIT writes a LOCK (models, thresholds, patterns) and prints its sha256. That sha is recorded in PREREGISTRATION_v37_LOCK.md before TEST runs, and TEST refuses any other LOCK.

## 5. Models, fixed now
- **LightGBM, one per side:** learning rate 0.03, 15 leaves, min 200 per leaf, feature/bagging fraction 0.7, L2 10, early stopping 60 rounds on 2013–14.
- **Readable patterns:**
  - every single event and ordered pair "A then B" within 60 min, 1 day or 5 days;
  - support ≥ 300 on 2005–14; ranked by binomial z;
  - the top 40 go to validation, where they must show z ≥ 2 in the same direction;
  - up to 5 are frozen.
- **Trading rule (thresholds from validation predictions):**
  - long when p_long ≥ the 90th percentile of validation p_long and p_long > p_short; short mirrored;
  - one trade at a time (2h block). Patterns trade in their direction, with conflicting patterns netted.

## 6. Gates
- **G1 information (per side):** validation AUC above ALL 20 permutation nulls. In each null, the training labels are shifted by a random whole number of days and the whole fit is repeated. The shift keeps time-of-day and day-of-week structure, so the model must beat "knowing the clock".
- **Leak void:** a validation AUC of 0.65 or more is presumed leakage and voids the run.
- **G2 model trades and G3 pattern trades (Bonferroni t ≥ 2.24), on the sealed data, net of spread:**
  - mean > 0 and t ≥ 2.24, clustered by date;
  - mean > 0 in each of 2020–21, 2022–23 and 2024–26;
  - mean above the 95th percentile of 200 random-entry nulls (same trade rate, random side, same blocking).

## 7. Power and blind spots
- **Sealed sample:** 1,647 days, 27,998 decision points. Median barrier 38 bp, median spread 0.77 bp; break-even win rate at the barrier is about 0.51.
- At about one trade a day, the MDE is ≈ 2.9 bp per trade, i.e. a win rate of about 0.54 or better.
- **What this cannot see or do:**
  - A modest real improvement in accuracy (0.51 → 0.53) is invisible.
  - The model is frozen from 2005–14 and never retrained, so a pattern that only exists after 2015 is missed. That is deliberate: it tests robustness to regime change.
  - We have already looked at most of these features on 2013–26 (v1–v36), so the sealed years are not perfectly blind to the researcher, only to the model.
  - No order-book, options-flow or news-text data is included (paid or unavailable).

## 8. One FIT, one TEST. No change of features, labels, parameters or thresholds between them.
