# PREREGISTRATION FLOWS-14 — valuation and the macro predictors of the equity premium

```
WRITTEN:   2026-09-28, before any of these series has been fetched.
STATUS:    FROZEN at its first commit; macro.py pins this file's sha256.
SOURCE:    Campbell & Shiller (CAPE); Fama & French (1989), term and default
           spreads; Goyal & Welch (RFS 2008) and Goyal, Welch & Zafirov (2024),
           who find almost all such predictors fail out of sample
VEHICLE:   S&P 500 total return (a monthly allocation; an ETF, not a CFD)
```

*Measurement, not a recommendation. Not financial advice.*

## 0. The claim and the expectation

The oldest fundamentals in investing: expensive markets (high CAPE)
earn less, and a steep yield curve and wide credit spreads forecast higher
equity returns. **Registered expectation: fail out of sample, as in Goyal &
Welch.** It is run so the programme has tested valuation at all, and on
the only sample long enough to try: 1871–2026.

## 1. Data (Step 0, frozen before any statistic is computed)

- Shiller `ie_data.xls` (Yale): monthly S&P composite price, dividends, CPI,
  CAPE and GS10, 1871 →.
- FRED: TB3MS (1934 →), BAA and AAA (1919 →).
- **Target:** monthly log excess return = log((P_t + D_t/12) / P_t−1) − log(1 +
  TB3MS_t−1 / 1200).
- **Predictors, known at the end of month t−1** (one extra month of lag for
  publication): (1) log CAPE, (2) term spread GS10 − TB3MS, (3) credit spread
  BAA − AAA.

## 2. Method (Goyal–Welch out of sample)

- One-variable predictive regression, re-estimated each month on an
  expanding window from 1934-01. Out-of-sample forecasts run **1965-01 →
  2026-08**.
- Benchmark: the expanding historical mean.
- **R²_OOS = 1 − Σ(r − f)² / Σ(r − mean)²**, with Clark–West adjusted-MSPE t.

## 3. Gates (each predictor separately; BH q < 0.10 across the three)

| gate | test | pass |
|---|---|---|
| **G1** | R²_OOS over 1965–2026 | > 0 and Clark–West t ≥ 1.65 |
| **G2** | R²_OOS over 2000–2026 | > 0 |
| **G3** | timing portfolio w = clip(f / (3·σ²), 0, 1.5), σ² = 60-month variance | Sharpe > buy-and-hold Sharpe, 1965–2026 |

A predictor passes only if G1 ∧ G2 ∧ G3. **Kill:** none of the three pass.

## 4. Secondary

- Campbell–Thompson sign restriction (forecast floored at zero).
- CAPE against the next 10-year return, overlapping and descriptive only.

## 5. Power

About 740 out-of-sample months. The literature's in-sample R² is about 1%
a month. Out of sample, that is often negative.

## 6. Files

    flows/fetch_longrun.py  flows/macro.py  flows/RESULT_MACRO.md
