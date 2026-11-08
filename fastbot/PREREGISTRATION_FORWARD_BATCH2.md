# PREREGISTRATION — FORWARD_BATCH2: paper forward records for the trend sleeve, its micro version, and GOLDRY1

```
STATUS:   frozen before any forward day (sha in PROVENANCE.md). Ledgers append only; history is never recomputed; every row carries a code version.
WRITTEN:  2026-10-12 (Dave: "pre register everything that we can take forward")
CODE:     scripts/forward_trend1.py (to be written and frozen before its first tick). It is a NON-FATAL step on the Mac's forward_tick.sh.
          The recorder's self-test must reproduce FUTPORT1's trend-sleeve daily series from data/futport1 exactly before it may record.
```
**I am not a financial adviser. This is a measurement, not a recommendation. Paper only; nothing here places an order.**

## 1. FORWARD_TREND1: the FUTPORT1 trend sleeve (29 markets, fractional, 10% vol)
- **Data:** Databento GLBX ohlcv-1d c.0/c.1 for the 29 roots, appended daily. Each pull is refused above $1.00.
- **Rule:** exactly scripts/futport1_run.py: trend signal, σ, sizing, costs and sleeve scaling. The 252-day histories continue from the backtest data.
- **Ledger:** data/forward_trend1.csv, one row per trading day with:
  - the sleeve return (net) and the gross return;
  - the scale factor and the number of markets;
  - each market's weight.
- **Start:** the first trading day after the recorder is frozen.
- **Review at 24 months:**
  - **KEEP** if the forward Sharpe is above the 5th percentile of 24-month block-bootstrap Sharpes (21-day blocks, seed 0) drawn from the 2012-05 → 2026-09 backtest of the same sleeve;
  - otherwise **DROP**.
  - **No running Sharpe is shown before 12 months;** counts and the date only.

## 2. FORWARD_MICRO1: the FUTMICRO1 $50k whole-contract version
- **What:** the same days and data, recorded alongside FORWARD_TREND1 in data/forward_micro1.csv (contracts per market, $ P&L net).
- **Status:** recorded whether or not FUTMICRO1 passes. If FUTMICRO1 FAILS, the record is descriptive only.
- **Review:** at 24 months, under the same KEEP / DROP rule as FORWARD_TREND1, using the FUTMICRO1 $50k backtest.

## 3. FORWARD_GOLDRY1: gold's snap-back after drifting from real yields (OILGOLD batch PASS, recent era ~0)
- **Status:** this is the forward record promised by policy_recent_regime and RESULT_OILGOLD_BATCH.
- **Weekly (Friday):** the GOLDRY1 residual, exactly as scripts/oilgold_run.py goldry, using:
  - FRED DFII10, refreshed by the Mac's existing FRED step;
  - the OANDA XAU daily 16:00 New York price, from the tick's 15m pull.
- **Paper position for the next week:** −sign(residual) × 0.10/σ_gold.
- **Ledger:** data/forward_goldry1.csv.
- **Review at 24 months:** KEEP if the forward slope of next-week return on the residual is < 0. That is a direction check only, not a significance test, which honours the recent-regime rule.

## What a KEEP means
A KEEP permits a funding pre-registration, never money by itself. FORWARD_TREND1 additionally needs FUTMICRO1 (or a larger account) to be holdable.
