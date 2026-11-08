# PREREGISTRATION — CYCLES2: what was going on before each bear market? (descriptive "fingerprint")

```
STATUS:   frozen before any CYCLES2 number is computed (sha in PROVENANCE.md)
WRITTEN:  2026-10-09
TYPE:     DESCRIPTIVE with a pre-set bar for calling a feature "characteristic". It is NOT a trading test.
EVENTS:   bear-market peaks from CYCLES1.1 on the monthly S&P (1871-2026). Only peaks with all feature data are used.
PART S:   Shiller variables (on disk). Run 2026-10-09.
PART F:   FRED variables (data/cycles/fred/, pulled by cycles/fred_cycles_pull.py). Run once the pull exists.
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## Question
Do bear-market peaks share a recognisable fingerprint, compared with ordinary months? Examples would be expensive valuations, rising rates, high inflation, falling earnings or a widening credit spread. If they do, how often does that same fingerprint appear *without* a bear following? That second number is the haystack.

## Features (value in month t uses only data published by month t)
**Part S (Shiller):**
| | feature | definition |
|---|---|---|
| S1 | valuation | CAPE, as an expanding percentile of its own history to date (needs ≥ 120 months) |
| S2 | earnings momentum | real earnings change over 12 months, lagged 3 months for the reporting delay |
| S3 | rates | long rate change over 12 months (percentage points) |
| S4 | inflation | CPI change over 12 months |
| S5 | price momentum | S&P change over the previous 12 months |

**Part F (FRED; monthly averages of daily or weekly series):**
| | feature | definition |
|---|---|---|
| F1 | credit spread | Baa − Aaa, change over 12 months |
| F2 | yield curve | 10-year (GS10) − 3-month (TB3MS) level |
| F3 | policy | fed funds change over 12 months |
| F4 | labour | unemployment rate minus its 12-month low (Sahm-style) |
| F5 | activity | industrial production change over 12 months |
| F6 | oil | real WTI change over 12 months (deflated by CPIAUCSL) |
| F7 | sentiment | Michigan sentiment change over 12 months |
| F8 | housing | building permits change over 12 months |

Recession (USREC) is reported, not used as a feature: it is dated after the event.

## Measurement
**At each bear peak month:** each feature's percentile within the distribution of *all* months in which that feature exists.

**A feature is "characteristic" if both hold:**
- at least two-thirds of peaks lie on the same side of the median;
- a two-sided sign test gives p < 0.05/k, where k = 5 for Part S and 8 for Part F.

**Haystack (reported for every feature):**
- Flag every month in which the feature is in the extreme quintile on the side the peaks favour.
- Report the share of flagged months followed by a bear peak within the next 12 months. This is the precision.
- Report the same share for all months. This is the base rate.
- Report the lift = precision ÷ base rate.

**Also reported:** the same percentiles 12 months *before* each peak, which shows whether the fingerprint was visible early.

## What it can and cannot say
- There are about 15–25 events, so this is history, not a forecasting model.
- A characteristic feature with a lift under about 2 means the signal appears far more often without a bear than with one.
- Any trading rule suggested by this needs its own pre-registration and a forward record.
