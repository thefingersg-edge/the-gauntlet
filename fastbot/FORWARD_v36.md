# FORWARD_v36 — NAS100 noise-band rule, recorded forward

Frozen 2026-09-25. Recorder: scripts/forward_noiseband.py v1.0, run by
forward_tick.sh (every 6 h, non-fatal step 5). **RECORDS ONLY. No orders.**

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. Why
v36 rule N failed its gate on three indices (net +1.09 bp/day, t 1.0), but it
had a real gross edge (+3.42 bp, t 3.2). NAS100 alone netted +4.35 bp/day (t 2.9).
Picking NAS100 was post-hoc, so only data that did not exist on 2026-09-25 can
confirm it.

## 2. What is recorded
- Rule: momentum_v36.py `noise_rows()`, imported unchanged (lookback 14,
  checkpoints 10:00–15:30, TWAP stop, flat at the 15:55 close).
- Data: OANDA NAS100_USD M5 bid/ask, pulled into data/v36fwd from 2026-08-01
  for warm-up.
- The first recorded session is **2026-09-28**. A session is written once,
  after it completes, and never rewritten.
- Output: data/forward_noiseband.csv (date, trades, gross_bp, net_bp).

## 3. What it can and cannot tell us (arithmetic, not hope)
From NAS100 2022–26: about 149 trade-days a year, SD 76 bp/day, cost 0.78 bp/day.
- **Confirming +4.35 bp/day net at 80% power (one-sided 5%) needs about 1,860
  trade-days, which is about 12 years.** A forward test alone will not confirm
  this in a useful time.
- What it CAN do in months:
  - **(a) validate execution:** is the live cost per day close to 0.78 bp?
    Checked at 60 trade-days.
  - **(b) catch a broken edge:** reported each quarter.
- There is no kill rule on performance before 250 trade-days. Earlier looks
  are descriptive only.

## 4. Nothing changes
No parameter, instrument or rule changes. Any change is a new document with a
new start date.
