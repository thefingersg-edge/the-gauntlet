# RESULT — CYCLES1.1 and CYCLES2 Part S: bear-market dates fixed, and the "fingerprint" of a market top is mostly "it went up a lot"

```
SPEC:     DEFINITION_CYCLES1.1.md sha 652048d8…; PREREGISTRATION_CYCLES2.md sha 3770e133…  (frozen before computation)
METHOD:   cycles/cycles2_run.py (sha in PROVENANCE); Shiller monthly 1871-2026; daily cash closes 2005-2026
LOGS:     data/cycles/run_cycles11.log, run_cycles2_S.log; data/cycles/phases11_monthly.csv, phases11_daily.csv
RUN:      2026-10-09       Part F (FRED) waits for the Saturday pull
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## CYCLES1.1 — bear-market rallies merged (the Pagan–Sossounov fix)
- **Monthly S&P:** 23 bears become 21. 1929–32 becomes one −85% bear and 1937–42 one −57% bear.
- **Daily SPX:** 2007–09 becomes one bear of −57% over 517 days. It was confirmed on 7 July 2008, 272 days after the peak, when only **27%** of the fall had happened. A further −46% followed.

The headline answer does not change. Median lag from peak to confirmation is **10 months**. Median share of the fall already gone at confirmation is **70%**. Median further fall after confirmation is −9.5%. The tail matters, though: in the three biggest bears (1929, 1937, 2007) the label came early and most of the fall was still to come.

## CYCLES2 Part S — what did the 18 bear peaks with full data look like?
Each value is the percentile against all months since 1871. "Characteristic" means at least two-thirds of peaks fall on one side and the sign test gives p < 0.01.
```
feature                         median pct   same side   p       characteristic   12m before peak   flagged months -> bear within 12m   base   lift
S1 CAPE (valuation)             0.71         12/18       0.24    no               0.55              20.7%                               13.6%  1.5
S2 real earnings growth         0.59         11/18       0.48    no               0.42              15.1%                               11.9%  1.3
S3 long-rate change             0.66         12/18       0.24    no               0.46              10.9%                               11.9%  0.9
S4 inflation                    0.67         13/18       0.10    no               0.36               9.3%                               11.9%  0.8
S5 S&P 12-month gain            0.67         17/18       0.000   YES              0.77              23.9%                               11.6%  2.1
```
**Read it plainly:**
- **The only consistent feature of a bear-market peak is a strong rally into it.** 17 of 18 peaks came after an above-median 12-month gain. That is close to true by definition, since a peak is the top of a rise.
- **As a warning it is wrong 3 times out of 4.** Of the months in the top fifth for 12-month gains, only 24% were followed by a bear peak within a year. That is about double the base rate, but most strong rallies just keep going.
- **High valuation leans toward peaks but is not a fingerprint.** CAPE was above median at 12 of 18 peaks, but ranged from 7 (1919) to 43 (2000). Expensive months were followed by a peak within a year only 21% of the time.
- **Rising rates and high inflation were not characteristic of peaks** over 150 years, and both had a lift below 1. Twelve months before a peak, the median percentiles were unremarkable (0.36–0.55). A year out, nothing looked unusual.
- **The haystack:** even the best single "top signal" in 150 years flags about 370 months, of which about 90 were followed by a top. You would sit through roughly three false alarms for every real one, just as the moving-average detectors did in CYCLES1.

## Next
**Part F** covers credit spreads, the yield curve, fed policy, unemployment, industrial production, oil, sentiment and housing. It runs once the FRED pull is done on Saturday. It also checks the typed NBER recession table against USREC.
