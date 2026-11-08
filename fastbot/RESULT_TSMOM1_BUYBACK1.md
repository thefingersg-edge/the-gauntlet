# RESULTS — TSMOM1 (trend following, gold/S&P/Nasdaq) and BUYBACK1 (buyback blackouts). Both FAIL.

**I am not a financial adviser. This is a measurement, not a recommendation.**

## TSMOM1 (PREREGISTRATION_TSMOM1; scripts/tsmom1_run.py; data/run_tsmom1.log; run 2026-10-08)
```
portfolio, 12-month trend, net of spread and CFD financing: Sharpe +0.38 (t +1.73, 20.3 yrs), +3.1%/yr, worst drawdown -20%   G1 FAIL
net by era 2006-12 +16.5% | 2013-19 +18.9% | 2020-26 +26.7%                                                          G2 PASS
reported: 3-month +0.26 (t 1.2) | 1-month -0.16
          gold +0.22 (no financing +0.43) | S&P +0.15 (+0.37) | Nasdaq +0.49 (+0.67, t 2.2)
          equal-risk BUY-AND-HOLD of the same three, same costs: Sharpe +0.61 (t 2.8), drawdown -16%
```
- Trend following is positive in every era — the textbook premium is here — but with only three markets (two of them almost the same) it falls just short of significance, as predicted.
- **CFD financing roughly halves it** (gold 0.43 → 0.22, S&P 0.37 → 0.15): trend following through CFDs pays interest on every long.
- Simply holding the three markets at equal risk did better (Sharpe 0.61). Trend following earns its keep by diversifying across many markets (oil next, TSMOM2), not on two equity indices and gold.

## BUYBACK1 (PREREGISTRATION_BUYBACK1; singlestock/buyback1_run.py; data/run_buyback1.log; run 2026-10-08)
```
blackout share (equal-weight S&P members) averages 50%, 0-100% through each quarter; 93% of members matched to earnings dates
G1 next-5-day S&P return on blackout share: +1.23 bp per 10pp (t +0.89) -- wrong sign      FAIL
G2 eras -2.4 (t -0.9) | -0.3 (t -0.2) | +6.8 (t +2.5)                                        FAIL
reported: blackout >= 60% days +26.5 bp over 5 days vs <= 20% days +14.0 bp
```
- The "no buyback support during blackout" story does not show up; if anything, the index did better in blackout weeks (which coincide with earnings season), especially since 2020.
