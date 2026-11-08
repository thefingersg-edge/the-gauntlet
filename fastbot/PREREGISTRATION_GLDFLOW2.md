# PREREGISTRATION — GLDFLOW2: do gold-ETF flows predict gold, month by month?

Written and frozen 2026-10-16, after looking only at the file's layout (sheet names, headers, first/last dates). No change, return or correlation has been computed from it. Approved by Dave the same day ("Pre-register monthly").

I am not a financial adviser. This is a measurement, not a recommendation.

## Why a new test
GLDFLOW1 (PREREGISTRATION_OILGOLD_BATCH.md) asked the question weekly, using SPDR's daily holdings archive. That archive link now serves a PDF bar list, so GLDFLOW1 still cannot run and stays **pending** (not replaced). Dave downloaded the World Gold Council Goldhub ETF-flows workbook instead; it holds **month-end** holdings only. GLDFLOW2 is the monthly version of the same idea, registered as its own test.

## Data (frozen)
- **Holdings:** `data/gold/WGC_ETF_Flows_2026-09.xlsx` (sha256 54c8ae7aff679b681ea6d90ff01aa8da1b976d30887aeb1e2f670c50d5275ec4), sheet "Holdings by month", rows from the "Date" header row down.
  - **Primary series:** column headed "SPDR Gold Shares" with ticker "gld us equity" (tonnes, month end, 2004-11 → 2026-09).
  - **Reported series:** column "Tonnes" (all gold ETFs worldwide, tonnes).
  - The workbook's "Gold, US$/oz" column is a monthly AVERAGE and is **not used**.
- **Gold price:** OANDA XAUUSD 15m mid (struct15 cache, from 2006-03). Daily price = close of the last bar starting before 16:00 New York.

## Test
- x_m = % change in GLD tonnes from month-end m−1 to month-end m.
- **Timing (no look-ahead):** SPDR publishes each day's tonnes after the US close, and WGC's monthly file comes out in the first days of the next month. To be safe, the trade starts at the **2nd New York trading day of month m+1** (16:00 price) and ends at the 2nd trading day of month m+2.
- y_m = gold log return over that window.
- OLS y on x; Newey-West (1 lag) t. Sample: every month with both x and y, from 2006-04 onward.
- **G1:** slope > 0 and t ≥ 2.0 (flows persist).
- **G2:** slope > 0 in each era: 2006–12, 2013–19, 2020–26.
- **PASS** needs G1 and G2.

## Reported, fixed now (no gate)
- The same regression on global gold-ETF tonnes.
- The top-minus-bottom quintile gap in next-month gold return.
- Same-month correlation of x with gold's return over month m (expected strongly positive: flows follow price). Descriptive only.

## Prediction
**FAIL.** Flows are well known to chase price; persistence into the following month is weak in the published work, and 245-odd monthly points give little power (a true monthly correlation near 0.13 is needed for t ≈ 2).

## Harness
`scripts/gldflow2_run.py`, frozen (sha in PROVENANCE) before the run; self-test plants a flow effect and a null. Run once; log `data/gold/run_gldflow2.log`.
