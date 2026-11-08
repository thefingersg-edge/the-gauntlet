# RESULT — FLOWS-14: valuation and macro predictors out of sample. DEAD.

```
SPEC:     PREREGISTRATION_MACRO.md (sha 554dcc85…)
METHOD:   macro.py   log data/macro_run.log   result data/macro_result.json
DATA:     Shiller ie_data.xls (sha 0df9392b…), FRED TB3MS/BAA/AAA
          DEVIATION (data, not method): Shiller's file now ends 2023-09, and its dividend
          series 2023-06. The out-of-sample run is 1965-01 .. 2023-06 (702 months), not to 2026-08.
RUN:      2026-10-01, once
VERDICT:  no predictor passes G1-G3  ->  DEAD
```

*Measurement, not a recommendation. Not financial advice.*

| predictor | R²_OOS 1965–2023 | Clark–West t | R²_OOS since 2000 | timing Sharpe vs buy-and-hold | gates |
|---|---|---|---|---|---|
| CAPE | −1.03% | 0.99 | +0.77% | 0.24 vs 0.40 | G1 ✗ G2 ✓ G3 ✗ |
| term spread | +0.14% | 1.34 | −0.83% | **0.43 vs 0.40** | G1 ✗ G2 ✗ G3 ✓ |
| credit spread | −0.03% | 0.14 | −0.15% | 0.34 vs 0.40 | ✗ ✗ ✗ |

This is Goyal and Welch's result, reproduced. Valuation and the macro
spreads do not beat the historical average at forecasting next month's
equity premium, and timing the market with CAPE cost about 40% of the
Sharpe ratio. The term spread's small timing gain is not backed by a
significant forecast. This is what the programme's "slow effects can't be
proved" floor predicted, now measured on 58 years of data.
