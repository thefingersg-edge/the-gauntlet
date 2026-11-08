# PREREGISTRATION v50: a "fear and attention" table from free news-based indices. Does it forecast volatility beyond VIX?

Frozen 2026-09-28. No news or attention index has been fetched or looked at for this test. The power budget (scripts/budget_v50.py, log data/budget_v50.log) used only squared 5m returns and VIX. The harness (scripts/fear_v50.py) must pin this sha256.

I am not a financial adviser. This is a measurement, not a recommendation.

## Question
- Across v30–v32 and the v37 timeline, public sentiment and macro data did not predict *direction*. What has survived in this programme is volatility and risk premia.
- Newspaper-based uncertainty indices are free, have daily history back to 1985, and are rarely combined by small traders.
- **The question:** does a combined daily fear index add information about next-day realised volatility of SPX500 beyond VIX and the realised volatility of the previous day, week and month? If so, does that help the short-VIX carry trade avoid the drawdowns that sank it in RESULT_VIXDAILY?

## Data
**Fear sources.** All are free. The VM and cloud network cannot reach the sites, so Dave downloads them into `data/v50/raw/`:
1. US daily Economic Policy Uncertainty (EPU): policyuncertainty.com, `All_Daily_Policy_Data.csv`.
2. Daily Geopolitical Risk (GPRD): matteoiacoviello.com/gpr.htm, the daily file.
3. Daily Trade Policy Uncertainty (TPU), Caldara–Iacoviello: the daily file from the TPU page.
4. *(reported only)* Google Trends, weekly US web search for "stock market crash" and for "recession", 2004 onward.

**Snapshot rule.**
- Every raw file's sha256 is written to PROVENANCE.md before any of its values are read.
- `scripts/fear_build_v50.py` then builds `data/v50/fear_table.csv` from those raw files alone. The table's sha is recorded before any market data is joined, the same rule as the v48 table.
- These indices are rescaled and occasionally revised, so the historical snapshot may contain look-back revisions. The clean test is the forward record, below.

**Prices.**
- SPX500 and NAS100 OANDA 5m regular-hours bars (reactive.load), 2005 → 2026-08-14.
- VIX close from data/VIXCLS.csv.
- Short-VX carry P&L from vix_daily_risk.py (VX1!/VX2!, with the roll handled as in RESULT_VIXDAILY).

## Definitions (fixed now)
- **Target:** RV_t is the sum of squared 5m log returns in the regular session on day t. The primary target is log RV_t for SPX500.
- **Benchmark model (HAR + VIX):** log RV_t = c + h1·log RV_{t−1} + h5·mean log RV_{t−5..t−1} + h22·mean log RV_{t−22..t−1} + v·log VIX_{t−1}.
- **Timing (conservative):** for target day t, a fear index may use only values dated t−2 or earlier. That leaves one day for publication. A t−1 version is reported only.
- **Component abnormal level:** A_i(t) = log(mean of index i over the 7 days ending t−2) − log(mean over the 250 days ending t−2).
- **Component z-score:** z_i(t) = A_i(t) divided by the standard deviation of A_i over the prior 250 days.
- **Composite:** C(t) = the mean of z_EPU, z_GPR and z_TPU. It is fixed now and never reweighted.
- **Sample:** from the first day with 250 + 250 days of history for every component and 22 days of RV. Expected start is 2006–07.

## Gates (Bonferroni over three tests, so HAC t ≥ 2.39; Newey-West with 5 lags)
- **G1, in-sample increment.** In HAR + VIX + b·C, b > 0 with t ≥ 2.39, and b > 0 in each of 2005–12, 2013–19 and 2020–26 (estimated separately by era).
- **G2, out-of-sample forecast.**
  - Setup: an expanding window, refitted at each month start, with forecasts from 2009-01 onward.
  - Comparison: squared error of the log-RV forecast, HAR+VIX+C against HAR+VIX.
  - Pass: the Diebold–Mariano statistic favours +C with t ≥ 2.39, and the mean loss is lower in each era from 2009 onward.
- **G3, economic use (the volatility-carry overlay).**
  - **Base:** short one VX1 contract held continuously, daily P&L as in vix_daily_risk.py.
  - **Fear rule:** flat on day t when C(t) is in the top fifth of its prior 250 values.
  - **Price-only control:** flat on day t when log VIX_{t−1} is in the top fifth of its prior 250 values. This has the same idea and similar time out, but uses no news.
  - **Pass:** the fear rule's total P&L divided by its worst daily-marked drawdown beats both the base and the price-only control. Also, the fear rule's worst drawdown is smaller than the control's.
  - G3 is a point comparison on a few crisis episodes. It is reported with that caveat and has no t-statistic. A PASS on G3 without G1 and G2 is not a finding.
- **Overall:** "useful" requires G1, G2 and G3. G1 and G2 alone mean "real but not yet usable".

## Reported (not gated)
- Each component alone: EPU, GPR, TPU.
- NAS100 as the target.
- A 5-day RV horizon.
- t−1 timing.
- Google Trends at weekly frequency against next-week RV.
- Direction: C(t) against the next-day SPX500 regular-session return. This is expected to be about zero, as in v30–v32.
- The regression coefficient translated into a % change in RV per 1 SD of C.

## Budget (from budget_v50.py; no fear data used)
- SPX500: 5,363 days. HAR+VIX R² is 0.731, the residual SD is 0.568 log units, and the residual AR(1) is 0.00.
- **The MDE at t 2.39 with 80% power is about 0.025 log units, about a 2.5% change in next-day RV per 1 SD of C.** Per era it is 0.033–0.048.
- **Power is ample, so significance alone proves little.** An effect this small would be real but useless, which is why G2 (out-of-sample) and G3 (does it change a trading outcome) are required.
- For context, the literature on news-based uncertainty finds effects on volatility several times this size. The prediction written here is G1 PASS, G2 marginal, G3 uncertain.

## Blind spots
- VIX already prices much of the news. The whole test is whether the index adds anything *beyond* VIX, which is a hard bar.
- The indices are built from newspaper archives, and past values can be revised or rescaled. The snapshot may flatter history.
- G3 turns on a handful of episodes (2008, 2011, 2015, Feb 2018, 2020, 2022). It cannot be significant, and it says so.
- GDELT, SEC Form 4 insider buying, Fed-text tone and live headlines are **not** in v50. Each needs its own pre-registration once the downloads are known to be feasible (v51+).

## Forward record
From the first month after the run, each month's new raw files are snapshotted by sha and appended to `data/v50/forward_fear.csv`. The G2 comparison is recomputed on forward days only. First look at 250 forward days; verdict at 750.

## One run.
