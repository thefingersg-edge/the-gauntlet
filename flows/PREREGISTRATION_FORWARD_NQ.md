# PREREGISTRATION FORWARD_NQ — v36 noise-band rule on NQ futures, recorded forward

```
WRITTEN:   2026-10-10 (Saturday). Frozen at its first commit; forward_nq.py pins its sha256.
FROM:      RESULT_VEHICLE.md (FLOWS-15). NQ net +5.76 bp per trade-session, t 3.92, over
           2013-26; +8.4 bp in 2022-26. Choosing NQ, and reading the recent eras, came
           AFTER that result, so only sessions that had not happened on 2026-10-10 can
           confirm it.
STATUS:    RECORDS ONLY. Paper. No order is placed, and no broker account is touched.
```

*Measurement, not a recommendation. Not financial advice.*

## 1. What is recorded, all fixed now

- **Rule:** fastbot `momentum_v36.py` `noise_rows()`, imported unchanged:
  14-session lookback, checkpoints 10:00–15:30 ET, TWAP stop, flat at the
  15:55 bar close, fills at the next 5-minute bar's open.
- **Instrument:** CME Nasdaq-100 E-mini, Databento `GLBX.MDP3`, `NQ.v.0`
  (front month by volume), `ohlcv-1m`.
- **Bars:** 1-minute bars inside 09:30–15:59 ET grouped into 5-minute bars,
  labelled by their start time. Sessions with fewer than 70 bars are not
  evaluated. This is the construction of `vehicle.py` 1.1 `days_from()`.
  `forward_nq.py` must reproduce it exactly on historical data (§4).
- **Costs:** one tick (0.25 index points) against the trader on every fill,
  plus $2.50 per contract round trip, converted to bp at the session's
  09:30 price × $20. These are the FLOWS-15 costs.
- **Roll sessions:** the first session after the front-month instrument
  changes is written as *not evaluated* (reason "roll"), as in FLOWS-15.
- **First recorded session: Monday 2026-10-12.** Sessions from 2026-08-03 up
  to 2026-10-09 are warm-up only, for the lookback.
- **Every complete session gets one row**, written once after the session has
  ended and the data is available, and never rewritten: `date, trades,
  gross_bp, net_bp, instrument_id, status, recorded_utc`. A session with no
  trade is written with trades 0. A session that could not be evaluated has
  blank trades and gives its reason.
- **Unit:** net bp per *trade-session* (a session with at least one trade),
  as in v36 and FLOWS-15.

## 2. Evaluation, fixed now

- **One evaluation, at the 500th trade-session** (about 3.5 years at about
  143 a year). Until then the recorder prints **only the count of rows**, not
  a mean.
- **Interim kill, checked once, at the 250th trade-session:** stop if the mean
  net is ≤ −2 bp. Otherwise continue, and print nothing but "continue".

| gate at 500 | pass |
|---|---|
| **F1** | mean net > 0 and t ≥ 1.65 (one-sided, confirming a stated direction; SE clustered by date) |
| **F2** | mean net ≥ +2.0 bp |

**CONFIRMED** = F1 ∧ F2. Otherwise **NOT CONFIRMED**, and the lead is closed.

**Power, stated now.** The backtest SD is about 65 bp per trade-session, so
the standard error at 500 is about 2.9 bp. If the true effect is the
full-sample +5.8 bp, the expected t is 2.0 and the chance of passing is
about 62%. At the recent +8.4 bp it is about 90%. A NOT CONFIRMED verdict
does not prove the effect is zero, but it is binding.

## 3. Descriptive checks (gate nothing)

- **Cost check at 60 trade-sessions:** pull Databento `bbo-1m` for NQ at the
  minute of every recorded fill, and report the median half-spread in ticks
  against the assumed 1 tick per side.
- **Same-day comparison with fastbot FORWARD_v36** (NAS100 CFD): correlation
  of gross bp on the same sessions, reported at each 125 trade-sessions.

## 4. Before the first recorded session

`forward_nq.py --self-test` must show that its stdlib 5-minute builder
gives the same sessions as `vehicle.py` `days_from()` on the January–August
2026 NQ file. It must also show that its `noise_rows()` trades match
FLOWS-15's for those months. If either differs, the recorder does not start.

## 5. Nothing changes

No parameter, instrument, cost or rule change is allowed. A change means a
new document with a new start date.

## 6. Files

    flows/forward_nq.py                 recorder (pull from Databento + record), pins this file
    flows/data/forward_nq/NQ_1m.csv     forward 1-minute bars (appended, never edited)
    flows/data/forward_nq.csv           the ledger
    run: fastbot/scripts/forward_tick.sh step 7 (non-fatal), every 6 hours on the Mac
