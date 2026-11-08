# PREREGISTRATION v56: does weak S&P breadth predict the S&P's next month? A measurement, not a backtest

Written 2026-10-01, frozen 2026-10-02 at its first commit, before any S&P return has been joined to any breadth value. The harness is scripts/breadth_v56.py v1.0. It pins this file's sha256 and data/tv/MANIFEST.json's. Breadth comes from the TradingView connector (tv_series.py). The only things read so far are each series' history length and range.

I am not a financial adviser. This is a measurement, not a recommendation.

## Question
- Practitioners read **washed-out breadth** (few S&P stocks above their 50-day average) as a sign of a bottom, and a **breadth thrust** (Zweig 1986) as the start of a rally.
- Rule 4 (measure before you backtest): instead of trading a rule, measure whether the S&P's forward return depends on breadth at all.
- Prior: the six published timing effects in this programme replicated in their paper's era and decayed afterwards (PROGRAMME.md section 11). Breadth signals are published and widely watched.

## Data
- **S5FI:** % of S&P 500 members above their 50-day average, 2006-12-29 onward. **S5TH:** above their 200-day. **ADV / DECL:** NYSE advancing and declining issues. All from the frozen snapshot data/tv_20261001/ (MANIFEST.json sha256 b287eb00651b4cd9d43ffb4d567f681a1156dd20eecb674fa9890636d86bc9b3), available 18:00 ET on their date.
- **SPX500_USD 15m bid/ask:** fastbot/data/v24, which is OANDA, the vehicle. Mid prices; the 09:30 bar's open and the 15:45 bar's close, both ET.
- **Sample:** signal dates t from 2007-01-02, with the exit on or before **2026-09-25**.

## Definitions
- **Forward return:** r_h(t) = mid open of the 09:30 bar on the next session (t+1), to mid close of the 15:45 bar on session t+h, in bp.
  - The entry is the morning after the 18:00 stamp, so nothing is used before it is known.
  - **h = 20 is primary**; h = 5 is reported.
- **x(t)** = S5FI on date t, in units of 10 percentage points.
- **SEs:** Newey–West (Bartlett) with lag h, because 20-day returns overlap.
- **Eras:** 2007–12, 2013–19, 2020–26.

## Gates (the washout hypothesis: low breadth → higher forward return). PASS needs all three.
- **G1:** in the OLS of r_20 on x, the slope is < 0 with NW t ≤ −2.0.
- **G2:** the slope is < 0 in each era separately.
- **G3, economic:** in the OLS of r_20 on the dummy (S5FI < 20):
  - the coefficient (mean on low-breadth days minus mean on the rest) is > 0 with NW t ≥ 2.0;
  - **and** the low-breadth mean, minus the median entry spread, is > 0.

## Reported (not gated)
- h = 5.
- S5TH in place of S5FI.
- The ADD z-score (vs the prior 252 days).
- **Every Zweig breadth thrust,** listed with its r_20 and r_60. A thrust is the 10-day EMA of ADV/(ADV+DECL) rising above 0.615, having been below 0.40 within the previous 10 sessions.
- **Every first washout,** listed with r_20: S5FI below 10, re-armed only after it has been back above 30.
- Thrusts and first washouts are a handful each, so they get no gate.

## Budget (no outcomes; from the series' lengths)
- About 4,900 signal days, but 20-day returns overlap: **about 245 independent 20-day periods.**
- S5FI is below 20 on roughly one day in ten, clustered in 2008–09, 2011, 2015–16, 2018, 2020 and 2022. That is perhaps **25–40 independent episodes**.
- With a 20-day SD of about 450 bp, the G3 minimum detectable difference is about 140–180 bp. **Only a large effect could pass.**
- **Prediction, written now:**
  - G1: the sign is negative (as the literature says), but t is short of −2.
  - G2: fails, because one era is driven by a single crash.
  - Verdict FAIL.

## Blind spots
- S5FI is TradingView's construction. Its history before 2006-12 is not available, so 2005–06 is not tested.
- These are the signals as practitioners compute them, not an index-level reconstruction from members.

## One run.
