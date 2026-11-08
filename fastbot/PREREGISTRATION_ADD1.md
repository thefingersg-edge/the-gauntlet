# PREREGISTRATION ADD1: do new S&P 500 members lag after joining? One confirmation run on the sealed window

Frozen 2026-10-04. Harness: `singlestock/add1_run.py`, which pins this file.

I am not a financial adviser. This is a measurement, not a recommendation.

## Origin
BATCHB reported (not gated) that stocks added to the S&P 500 lag their size benchmark by −2.71% over 60 trading days after inclusion (t −3.43, n 367), on entries to 2023-06-30. The sealed window 2023-07-01 to 2026-09-30 has never been looked at for this.

## Definition (identical to the BATCHB report)
- Events: Sharadar `sp500` rows with action `added`; the date is the effective date.
- Entry: closing auction of the first trading day after the effective date (`batchB_engine.run`, unchanged); hold 60 trading days; return = excess over the stock's liquidity-band benchmark.
- Window: entries on or after 2023-07-01 with the exit on or before the last price in the store.
- The trade being tested is a **short**: success = negative excess.

## Look-ahead check (done before the run)
Additions are announced days before the effective date, and entry is the day after it, so the event is public before entry.

## Gates
- **G1:** mean excess < 0 with t ≤ −1.645 (one-sided; direction fixed by the earlier report), SEs clustered by entry month.
- **G2:** mean excess still < 0 after a short's costs: 0.25 × EDGE + commission + 0.10% borrow for 60 days.
- PASS needs both.

## Budget
About 15–19 additions a year, so roughly 45–50 events. With a 60-day excess SD of about 12%, the standard error is about 1.7%: a true −2.7% gives an expected t of about −1.6. **The test is close to a coin flip even if the effect is real.** Accepted; a FAIL here is weak evidence, a PASS is strong.

## One run.
