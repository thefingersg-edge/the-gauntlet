# PREREGISTRATION GRAN1: does the single-stock data hold information about SPX500 and NAS100?

Frozen 2026-10-03, before any GRAN1 series has been joined to an index return. Inputs: `singlestock/gran_build.py` → `data/sharadar/cache/gran_daily.csv` (sha 6377d9b2…), built from the Sharadar files only. Only first dates and the signals' own autocorrelation have been looked at. Harness: `singlestock/gran1_run.py`, which pins this file and the table.

I am not a financial adviser. This is a measurement, not a recommendation.

## Already covered elsewhere (not repeated)
v56/v57, from another session: S&P breadth (% above the 50-day) predicted the next month (t −2.06), but **not beyond VIX**. Breadth is therefore not re-tested here.

## New rule from today: a sealed hold-out
- **2023-07-01 → 2026-09-30 is sealed.**
- All gates below are computed on data **up to 2023-06-30**. Only a hypothesis that passes is run **once** on the sealed window.
- On the sealed window it must have the same sign with t ≥ 1.0. That is a deliberately low bar: about 3 years cannot do more, and this says so.

## Hypotheses (three, Bonferroni, so t ≥ 2.39; Newey-West SEs, 20 lags for 20-day horizons, 5 for daily)
- **H1, insiders as a group.**
  - *Literature:* Seyhun; Lakonishok & Lee; Jiang & Zaman. When company insiders across the market buy more relative to selling, the market tends to rise afterwards.
  - *Signal:* `ins_ratio30` = purchases / (purchases + sales) by officers and directors over the prior 30 days of filings, using data dated ≤ t−1. Standardised by its trailing 500-day mean and SD.
  - *Target:* the SPX500 log return from close t to close t+20 (OANDA daily, cash close).
  - *Pass:* slope > 0, t ≥ 2.39, slope > 0 in each era (2008–12, 2013–17, 2018–23H1).
  - *Sample:* 2008-01 → 2023-06 (the insider coverage).
- **H2, the earnings season as a whole.**
  - *Literature:* Kothari, Lewellen & Warner. Aggregate earnings news relates to market returns, but the direction is disputed.
  - *Signal:* `ear_L28` = the mean earnings-announcement reaction of the 500 largest stocks (by dollar volume) whose reaction became known in the prior 28 days (at least 20 announcements; data dated ≤ t−1). Standardised as in H1.
  - *Target:* the SPX500 20-day return, as in H1.
  - *Pass:* **two-sided**, |t| ≥ 2.39 with the same sign in each era (2005–12, 2013–17, 2018–23H1).
- **H3, dispersion forecasts volatility.**
  - *Signal:* `disp_L` = the cross-sectional SD of daily returns across the top-500 stocks. The 5-day mean of log `disp_L`, dated ≤ t−1.
  - *Target:* log realised variance of SPX500 on day t+1 (5m regular-session bars), in the v50 HAR + ln VIX model.
  - *Pass:* slope > 0, t ≥ 2.39, positive in each era (2005–12, 2013–17, 2018–23H1), **and** out-of-sample from 2010 (expanding window, monthly refit) beats HAR+VIX on squared error with DM t ≥ 2.0.

## Reported (not gated)
- NAS100 for all three.
- A simple timing rule for H1/H2: long SPX only when the signal is in its favourable half, against buy-and-hold.
- 60-day horizon for H1.

## Budget (data/gran budget printout, index returns used for RMS only)
- SPX500 2005–2023H1: 4,616 days, 20-day RMS 479 bp, about 230 independent 20-day periods.
- **MDE correlation about 0.21**, i.e. about 100 bp of 20-day return per 1 SD of the signal. H1 has fewer periods (from 2008), so its MDE correlation is about 0.23.
- **H1 and H2 are underpowered for realistic effects.** Predicted FAIL. H3 has daily power, similar to v50 (MDE about 2.5% of RV per SD). Predicted uncertain: dispersion is closer to the market's own state than newspaper fear was.

## One run (and at most one sealed run per passing hypothesis).
