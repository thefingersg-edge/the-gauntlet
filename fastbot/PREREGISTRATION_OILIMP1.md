# PREREGISTRATION — OILIMP1: can a small account actually hold the oil carry, and what does it look like going forward?

```
STATUS:   frozen before any OILIMP1 number is computed (sha in PROVENANCE.md). One run of the backtest; the forward record appends only.
WRITTEN:  2026-10-11 (Dave: "lets do all 4", option 1 after RESULT_OILGOLD_BATCH)
BUILDS ON: OILCARRY1 PASS (Sharpe 0.47 registered; 0.54 with the logged roll fix, offset -1). Its signal, vol target and roll fix are reused unchanged.
DATA:     data/oil/wti_f1.csv, wti_f2.csv, wti_f3.csv (EIA RCLC1-3, 1986 -> 2024-04-05)
          data/v51/wticousd_15m.npz (OANDA WTICO_USD bid/ask; spreads only)
          NEW (pulled by scripts/forward_oilcarry.py --seed on the Mac, Databento GLBX.MDP3 ohlcv-1d, CL.c.0 and CL.c.1, 2010-06 -> today)
COSTS:    researched 2026-10-11:
            CME Micro WTI (MCL): 100 barrels (1/10 of CL); tick $0.01 = $1.00; launched 2021. Initial margin about $1,372 in March 2025 (Schwab), about 20% of notional.
            Commission + fees: $1.50 per contract per side assumed (as VIXIMP1's IBKR all-in figure).
            OANDA commodity CFDs are priced off the futures plus a basis; daily financing offsets the basis and adds an admin fee (OANDA help: "commodity financing cost variation").
              So CFD P&L ~ futures excess return - admin fee - spread. The admin fee is not published per instrument: 2.5%/yr is assumed (the index markup), with 1.5% and 3.5% as sensitivity.
            ETC route: WisdomTree WTI Crude Oil (CRUD, LSE), 0.49% management fee + 0.45% swap rate = 0.94%/yr. It tracks a multi-tenor index, is long-only for retail, and can't be shorted.
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## Question
OILCARRY1 found a real carry premium on paper: long WTI in backwardation, short in contango. Can an account of **$10,000** hold it through a broker Dave can actually use, after integer contracts, roll costs, margin and fees, and still pay?

## Fixed construction (all routes)
- **Signal:** OILCARRY1 with the roll fix, exactly as scripts/oilcarry1_rollfix.py:
  - at each month end, the sign of F1/F2 − 1;
  - weight w = sign × 0.10 / σ, capped at ±3, where σ is the EWMA(com 60) annualised vol of the roll-adjusted F1 daily return;
  - the new weight applies from the first trading day after month end.
- **Account:** a fixed capital of $10,000 (primary), with $25,000 and $50,000 reported. P&L is in dollars on fixed capital, not compounded.
- **Return series:** the roll-adjusted F1 daily price change. The roll is on the CL last trading day (offset −1).
- **Period:** 1987-01-01 → 2024-04-05 (EIA). Eras: 1987–2004, 2005–2014, 2015–2024.

## Routes
| | route | sizing | costs |
|---|---|---|---|
| **M** | Micro WTI futures (MCL) | n = round(w × capital / (100 × F1)) whole contracts, reset at each month end | each contract change: $1.00 tick + $1.50 per side; every month the held contracts roll: 2 × ($1.00 + $1.50) per contract. Before 2021, MCL is synthetic (CL / 10, same underlying), disclosed |
| **C** | OANDA WTI CFD | units = w × capital / F1 barrels (fractional) | half the OANDA quoted spread on each change, taken from the first 15m bar at or after 10:00 New York on the rebalance day; days before OANDA spreads exist (pre-2013 zero in the source) use the 2013–2024 median. Admin fee 2.5%/yr on the notional held each night (Friday 3) |
| E | CRUD ETC, long or flat (reported only) | long w⁺ capped at 1 (no leverage) when carry > 0; else flat | 0.94%/yr while held; 10 bp per switch. The F2 roll-adjusted return stands in for the multi-tenor index |

## Gates (each of M and C judged alone; Bonferroni over 2 routes)
- **G1:** net Sharpe × √years ≥ 2.24 for the $10k account.
- **G2:** net P&L > 0 in each era.
- **G3:** worst peak-to-trough drawdown ≤ $3,000 (30% of the account), on daily marks.
- **G4 (holdability):**
  - **M:** the $10k integer-contract P&L correlates ≥ 0.80 with the fractional ideal, AND at every month end the margin (20% of notional) is ≤ 50% of capital.
  - **C:** G1 still holds with the admin fee at 3.5%/yr.
- A route PASSES only if G1–G4 all pass.

## Reported (no gates)
- **Account sizes:** for $25k and $50k, the share of months with 0 contracts, and the average |n|.
- **Admin-fee sensitivity:** 1.5% / 2.5% / 3.5%.
- **Episodes:** worst month, worst day, and the April 2020 negative-price days.
- **Route E** vs M and C.
- **Databento check:**
  - over the overlap 2010-06 → 2024-04, the correlation of daily CL.c.0 changes with EIA F1, and agreement of the month-end carry sign;
  - an **out-of-sample stub 2024-04-08 → 2026-09-30** on Databento CL.c.0/CL.c.1 for routes M and C. It is about 2.5 years, too short to judge, and is reported only.

## Forward record (paper, appends only; scripts/forward_oilcarry.py)
- **Start:** the month end of 2026-10-30.
- **Monthly entry:** at each month end, the Mac tick pulls Databento CL.c.0/CL.c.1 daily bars (it refuses any pull over $1) and records:
  - the carry sign, σ and w;
  - the MCL contracts for $10k, $25k and $50k;
  - the CFD units.
- **Daily mark:** the paper P&L is marked from the CL.c.0 daily close, roll-adjusted on contract changes. Ohlcv-1d closes are last trades, not settlements; this is disclosed.
- **Rows are never recomputed.** Each row carries the code version.
- **Review at 24 months (2028-10):**
  - **KEEP** if the forward Sharpe is above the 5th percentile of 24-month blocks bootstrapped from the 1987–2024 backtest of the same route;
  - otherwise **DROP**.
  - A KEEP is permission to write a funding pre-registration, never money by itself.

## Prediction
- **M at $10k: FAIL on G4.** One MCL is about $6–8k of oil, and the 10% vol target at oil's ~35% vol wants about $2.9k, so the account holds 0 or 1 contract and tracks poorly.
- **C: borderline on G1.** The registered Sharpe × √years was 2.89 before costs.
