# RESULT — CYCLES2 Part F: the economy gives no reliable warning before a bear market peak

```
SPEC:     PREREGISTRATION_CYCLES2.md sha 3770e133…   HARNESS: cycles/cycles2_run.py (frozen 9 Oct)
DATA:     FRED, pulled 2026-10-10 by cycles/fred_cycles_pull.py (16 series, data/cycles/fred/, shas in PROVENANCE)
RUN:      2026-10-10       LOG: data/cycles/run_cycles2_F.log
CHECK:    the NBER recession table typed into cycles1_run.py matches FRED USREC exactly
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

Each feature is measured at the S&P bear-market peaks (CYCLES1.1 dates). The number of peaks depends on when each series starts.
```
feature                          peaks   median pct   same side   characteristic?   12m before   flagged -> bear within 12m   base    lift
F1 credit spread (Baa-Aaa) chg   12      0.31         9/12        no                0.60         15.1%                       11.2%   1.34
F2 yield curve (10y - 3m)         7      0.41         4/7         no                0.47         10.7%                        9.5%   1.12
F3 fed funds 12m change           7      0.65         5/7         no                0.24          7.0%                        9.8%   0.71
F4 unemployment vs 12m low        7      0.19         5/7         no                0.19         13.6%                        9.1%   1.49
F5 industrial production chg     12      0.66         8/12        no                0.41         15.6%                       11.2%   1.39
F6 real oil price 12m chg         7      0.86         5/7         no                0.36         14.3%                        8.9%   1.60
F7 consumer sentiment chg         4      0.32         3/4         no                0.55          4.5%                        9.1%   0.50
F8 building permits chg           7      0.45         4/7         no                0.65         12.0%                       10.5%   1.14
```
**0 of 8 are characteristic** at the pre-registered bar.

## Read it plainly
- **At market tops the economy usually looks fine.** Unemployment was near its 12-month low, industrial production was growing, and credit spreads were not widening. The trouble shows up *after* the peak, which is why recessions get dated in hindsight too.
- **The textbook warnings are weak here.**
  - **Yield-curve inversion:** only 4 of 7 peaks had a below-median curve, and the lift is 1.1.
  - **Fed hiking:** fed funds had risen before 5 of 7 peaks, but the "hiking" flag preceded a peak *less* often than an average month (lift 0.7).
  - **Oil spike:** the strongest lean is rising real oil before 5 of 7 peaks (lift 1.6), but 86% of the months it flags are not followed by a peak within a year.
- **Combined with Part S:** across 13 economic and valuation measures, nothing reliably marks a bear-market top. The only consistent feature is a strong rally into it (Part S).
- **Small samples:** 7–12 peaks per measure. This is history, not a forecasting model.
