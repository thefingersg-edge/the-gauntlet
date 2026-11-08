# PREREGISTRATION v38 — the noise-band rule on five markets it has never seen

Frozen 2026-09-26. The budget read spreads and squared returns only; no signed return has been read.
Script: scripts/noise_v38.py v1.0.

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. Question
v36 rule N (Zarattini et al. noise-band momentum) had a real gross edge on the US indices: +3.42 bp per instrument-day, t 3.2, in 2013–26. Is that a property of intraday index momentum in general, or of the US in that sample?

## 2. Data
- OANDA 5m bid/ask, pulled 2026-09-26 into data/v38 by run_v38_pull.sh.
- Checked independently: no duplicates, never ask < bid.
- Instruments and cash sessions (local time):
  - UK100: 08:00–16:30 London
  - DE30: 09:00–17:30 Frankfurt
  - EU50: 09:00–17:30 Frankfurt
  - JP225: 09:00–15:00 Tokyo
  - AU200: 10:00–16:00 Sydney
- A session needs at least 90% of its 5m bars.
- The gated period runs from 2013-01-01, or from the first real (bid ≠ ask) spread (AU200: 2014-02-26), to 2026-09-25.
- None of these instruments has been used for rule N, the timeline or the v37/v39 models. DE30 appeared only in the v24–v28 release-morning tests.

## 3. Rule — v36 N, unchanged apart from session times
- Checkpoints: the bars closing every 30 minutes from open + 30 to close − 30.
- sigma_k = mean over the prior 14 sessions of |close_k / open − 1|.
- Bands from max/min(open, prior session close). The stop is the session TWAP versus the band.
- Flat at the last bar's close. Fills at the next bar's open, paying the quoted spread.
- **Gate 0:** the generalised code, run on SPX500 with the US session, reproduces momentum_v36.noise_rows() day by day. Passed in self-test: 3,319 days, maximum difference 0.

## 4. Gates (pooled; unit = instrument-day; SEs clustered by date)
- **G1 GROSS replication (the scientific question):**
  - mean > 0 with t ≥ 2.0;
  - > 0 in each of 2013–17, 2018–21 and 2022–26;
  - excluding 2020–21: > 0 with t ≥ 1.64.
- **G2 NET of spread (the trading question):** the same conditions on net.
- Per-instrument figures are reported. Nothing is chosen from them.

## 5. Budget — read before any signed number
- 10,590 instrument-days on 3,378 dates; RMS 53.6 bp; 1.86 trades a day; MDE about 2.6 bp/day.
- **Cost is 5.46 bp/day pooled:** UK100 3.23, DE30 2.36, EU50 9.28, JP225 7.97, AU200 4.73.
- The US gross edge (3.4 bp/day) is below that cost. **G2 is expected to fail by arithmetic** unless these markets carry a much larger gross effect. G1 is the informative gate.

## 6. Reported, gating nothing
- **B.** v36 rule on SPX/NAS/US30 from 2013, split by whether the VIX futures curve was inverted (VX1 > VX2) at the prior close. The VX session dates are corrected as in tl_build 1.1. These years have already been seen.
- **C.** Volatility-scaled size on A (the median 20-day sigma ÷ each day's, capped at 3×): Sharpe and maximum drawdown compared with equal size.

## 7. One run.
