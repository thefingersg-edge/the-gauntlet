# PREREGISTRATION — VIXIMP1: can a small account actually hold the VIX carry, with a crash rule?

```
STATUS:   frozen before any VIXIMP1 number is computed (sha in PROVENANCE.md)
WRITTEN:  2026-10-10 (Saturday VIX-carry review, option 2 of REVIEW_2026-10-04)
BUILDS ON: RESULT_VIXCURVE (premium ~0.40 Sharpe, all eras), RESULT_VIXCARRY (min size 0.63 mini contracts),
           RESULT_VIXDAILY (daily worst drawdown -68.2 vol pts; at a 30% budget the carry returns 3.4-4.0% vs a risk-matched index at 5.1% (2% cash) -> REJECTED)
DATA:     data/CBOE_DLY_VX1!, 1D_1f2b8.csv and CBOE_DLY_VX2!, 1D_7782c.csv (TradingView daily, 2004->2026-08), data/VIXCLS.csv (FRED spot VIX)
COSTS:    researched 2026-10-10:
            Cboe Mini VIX (VXM): $100 per vol point, tick 0.05 = $5
            IBKR exchange-fee recovery $0.20 per VXM contract; all-in $1.50 per fill assumed (as RESULT_VIXCARRY)
            Cboe customer maintenance margin, VXM front month: $572 ($629 heightened risk), Jul-2024 schedule
          ETP route: SVIX (-1x short-VIX futures ETF, expense ratio 1.47%) is US-domiciled with no PRIIPs KID,
          so it is not available to UK retail clients -> reported only, not gated.
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## Question
RESULT_VIXDAILY rejected always-short VIX carry because one bad stretch (−68 vol points, 2007–08) forces a $10k account to hold too little to beat simply owning the index.

Does one simple crash rule cut that drawdown enough to allow **one** mini contract in a $10,000 account while still beating the index?

## Construction (fixed)
- **Base P&L:** short the front-month VX, marked close-to-close. The roll correction is exactly as in vix_daily_risk.py 1.2: on roll days the P&L is −(VX1_t − VX2_{t−1}); the roll offset is identified by its own scan and the run refuses if that scan fails.
- **Roll cost:** 2 ticks + 2 × $1.50 commission per contract per roll.

## Rules
| | rule | detail |
|---|---|---|
| R0 | always short | baseline; reproduces RESULT_VIXDAILY |
| R1 | contango filter | short over day t only if VX2 > VX1 at close t−1; otherwise flat |
| R2 | spot-VIX stop | short over day t only if VIXCLS at close t−1 ≤ 25; otherwise flat |

- Signals are taken at close t−1 and traded at that close.
- Each position change costs 1 tick + $1.50.
- Flat days earn 0. Cash interest on margin is ignored, the same for every rule and the benchmark.

## Gates for R1 and R2 (all four must pass; R0 is reported only)
- **G1:** net mean daily P&L > 0 with Newey–West (5 lags) t ≥ 2.24.
- **G2:** net P&L positive in each era (2004–12, 2013–19, 2020–26).
- **G3:** worst daily-close drawdown of one VXM ≤ $3,000 (30 vol points), so 1 contract fits a $10,000 account at a 30% drawdown budget.
- **G4:** annual return on a $10,000 account holding the largest whole number of VXM within the 30% budget (at least 1) is greater than **5.1%**, the risk-matched index figure in RESULT_VIXDAILY at 2% cash.

## Reported, no gates
- worst single day and worst 5 days;
- the 2008, Feb-2018 and Mar-2020 episodes;
- time in market;
- number of switches per year;
- days on which a $10k account would have fallen below the $629 heightened margin per contract;
- outcomes for $10k, $25k and $50k accounts;
- the ETP route as a −1x daily-rebalanced version (expense 1.47%), for context only.

## Caveats written in advance
- **Close-to-close only.** Intraday moves (5 Feb 2018 after hours) were worse than any close shows, so G3 is a lower bound on the real risk.
- **Signals in the same close.** Signals and fills both use closes. Spot VIX's close (16:15 ET) and futures settlements differ slightly, so the stop is mildly optimistic.
- **A PASS means a paper forward record first,** never money straight away.
