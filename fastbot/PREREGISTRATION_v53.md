# PREREGISTRATION v53: credit spreads and the stock–bond correlation as risk overlays. Do they add anything beyond VIX?

Frozen 2026-10-01, before any credit-spread or correlation value has been fetched or joined. Dave fetches the FRED series with scripts/fred_fetch_v53.py (key stays on his Mac). Each raw file's sha256 goes into PROVENANCE.md before it is read. The harness (scripts/credit_v53.py) must pin this file and scripts/daily_close.py (sha 617eadd2fc60ae99a736e0fa8b7455e12f0c3918069f3587f4176e5b0044c88c).

I am not a financial adviser. This is a measurement, not a recommendation.

## Question
- **Credit:** credit markets are said to price trouble before equities.
- **Stock–bond correlation:** when stocks and bonds fall together (a positive correlation, as in an inflation regime), bonds stop hedging and equity risk is said to be higher.
- v50 showed that VIX already contains the news. **So each signal must add something beyond a VIX rule, not just beat buy-and-hold.**

## Data
- **BAA10Y:** Moody's Baa corporate yield minus the 10y Treasury, daily from 1986. This is the primary credit series.
- **DGS10:** the 10y Treasury yield, from FRED via fred_fetch_v53.py.
- **BAMLH0A0HYM2 (HY OAS):** reported only, and only if FRED returns history from 2005.
- **Publication lag:** a value dated d is usable from the close of d+1.
- **Equities:** SPX500 and NAS100 daily closes from daily_close.py, 2005 → **2026-09-25**. VIX from fastbot/data/VIXCLS.csv.

## Definitions
- **Credit signal C:**
  - D20(d) = BAA10Y(d) − BAA10Y 20 observations earlier.
  - Risk-off for the position over close t → close t+1 if the latest D20 dated ≤ t−1 is above the 80th percentile of the 250 D20 values before it.
- **Correlation signal R:**
  - ρ_t = the 63-day correlation of SPX500 daily log returns with bond returns (−ΔDGS10), using data dated ≤ t−1.
  - Risk-off when ρ_t > 0.
- **VIX rule V (control, from v50):** risk-off when VIX_{t−1} is above the 80th percentile of its prior 250 values.
- **Exposure:** 0 when risk-off, otherwise 1.
- **Costs and portfolio:** exactly as in v52 (spread per switch, financing while long, flat earns 0), with the portfolio the equal weight of SPX500 and NAS100.
- **Eras:** 2005–12, 2013–19, 2020–26.

## Gates (two signals, so the null percentile is 97.5). Each signal is "useful" only if G1, G2 and G3 all hold.
- **G1, drawdown:** the portfolio max drawdown is ≤ 0.75 × B&H's, and ≤ B&H's in each era.
- **G2, timing is real:** Sharpe exceeds the 97.5th percentile of 500 circular-shift nulls (offset ≥ 250 days), as in v52.
- **G3, adds beyond VIX:** "flat when the signal OR V fires" has a higher Calmar than V alone, and a Sharpe no more than 0.05 below V alone.

## Reported (not gated)
- Each signal against V alone.
- HY OAS in place of BAA10Y, if history allows.
- A level version of credit (BAA10Y z-score against its trailing 250).
- ρ computed with the 2y yield (data/v31/DGS2.csv).
- Per instrument; UK100 against US credit; time in market; switches.

## Budget
- The same daily sample as v52: about 21.7 years, Sharpe SE about 0.21. **Sharpe differences are not resolvable.** The gates are drawdown, a timing null, and beating VIX on Calmar.
- **Prediction, written now:**
  - **Credit:** G1 likely PASS, G3 likely FAIL (VIX already has it).
  - **Correlation:** FAIL. ρ was mostly negative in 2005–21 and positive from 2022, so R is close to an era switch. The circular-shift null should catch that.

## Blind spots
- R is close to a single regime change in 2022. With one switch, no 21-year test can tell a good regime call from luck. That is stated now.
- BAA10Y is not high yield. It is the long free series. HY OAS, if available, is reported alongside.

## One run.
