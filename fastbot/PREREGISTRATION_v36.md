# PREREGISTRATION v36 — noise-band momentum and gamma-proxy momentum

Frozen 2026-09-25 before any signed return was read. Script: scripts/momentum_v36.py v1.0.

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. Why
v35 found that the classic intraday momentum effect (first half-hour → last
half-hour) was real in 2005–12 and gone from 2013. The literature offers two
survivors:
1. Zarattini, Aziz & Barbon (2024): noise-band breakout momentum on SPY.
2. Baltussen, Da, Lammers & Martens (JFE 2021): momentum lives on days when
   dealers are short gamma.

## 2. Data
OANDA 5m bid/ask SPX500, NAS100, US30, 09:30–15:55 ET, sessions ≥ 70 bars.
Discovery 2005–12 is gross only. **Gated 2013-01-01 → 2026-09-17, NET of the
quoted spread.** Fills are at the next bar's open.

## 3. N — noise-band momentum (their rules, unlevered, no volatility sizing)
- Checkpoints: the bars closing at 10:00, 10:30 … 15:30.
- For each checkpoint k, sigma_k = mean over the prior 14 sessions of
  |close_k / 09:30 open − 1|.
- Upper = max(open, prior 15:55 close) × (1 + sigma_k).
  Lower = min(open, prior close) × (1 − sigma_k).
- Entries: a close above upper → long; a close below lower → short.
- Stops: a long exits when a checkpoint closes below max(upper, session
  average price); a short mirrors this. A re-entry is allowed at the same
  checkpoint.
- Any open trade is closed at the 15:55 bar's close.
- **Departures from the paper, fixed now:**
  - The session average is time-weighted (TWAP) instead of volume-weighted,
    because OANDA tick counts are not exchange volume.
  - No leverage or volatility targeting, since these scale returns but do
    not create them (RESULT_VOLTARGET).
  - The instruments are CFDs, not SPY.
- Unit: the net P&L summed per instrument-day, over days with at least one trade.

## 4. G — gamma-proxy momentum
- A day is "hot" when the prior-day VIX close is at or above the 2/3
  quantile of the 252 closes before it. This is a free stand-in for dealers
  being short gamma.
- On hot days, the sign of the rest-of-day return (prior 15:55 close → 15:30
  open) sets the direction of a trade from the 15:30 open to the 15:55 close.
- Reported, not gated: the same rule on the other (non-hot) days, as the
  mechanism contrast.

## 5. Gates (two tests, Bonferroni t ≥ 2.24, SEs clustered by date)
PASS requires all three:
1. holdout net > 0 with t ≥ 2.24;
2. net > 0 in each of 2013–17, 2018–21 and 2022–26;
3. excluding 2020–21: net > 0 with t ≥ 1.64.

## 6. Power budget (holdout, RMS and cost only)
| test | n | dates | RMS | cost | MDE (80%) |
|---|---|---|---|---|---|
| N | 6,103 instrument-days (1.7 trades each) | 2,683 | 56 bp | 2.32 bp/day | ≈ 3.4 bp/day |
| G | 3,238 | 1,080 | 46 bp | 1.28 bp | ≈ 4.3 bp |

**What the budget cannot see.**
- An N edge below about 3.4 bp per day is invisible. The paper's claimed
  return is achieved with leverage of up to 4×, so its unlevered daily edge
  may sit near this line.
- G can see only about 4 bp or more.
- The VIX stand-in is not true dealer gamma: a FAIL on G does not refute
  Baltussen et al. It only rejects this free proxy.
- The paper's sample (2007–2024) overlaps our holdout, so this is a test of
  the idea on our instruments and costs, not an independent out-of-sample test.

## 7. One run. No change of lookback, checkpoints, quantile or stops after it.
