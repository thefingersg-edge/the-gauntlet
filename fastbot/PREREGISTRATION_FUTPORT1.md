# PREREGISTRATION — FUTPORT1: trend + carry across 29 CME futures, the documented premia on the right vehicle

```
STATUS:   frozen before any FUTPORT1 data is pulled (sha in PROVENANCE.md). The harness is frozen separately before its one run.
WRITTEN:  2026-10-12 (Dave: "pre register all of them so we can start pulling data")
ORIGIN:   ANALYSIS_WHAT_CHANGED_2026-10-12.md, step 3. TSMOM1/TSMOM2 tested trend on 3-5 CFDs that pay financing (Sharpe 0.41, t 1.8).
          OILCARRY1 found carry on oil alone (Sharpe 0.47-0.54). The literature's version uses many futures:
          Moskowitz, Ooi & Pedersen 2012; Koijen, Moskowitz, Pedersen & Vrugt 2018; Hurst, Ooi & Pedersen 2017.
DATA:     Databento GLBX.MDP3 ohlcv-1d, continuous CALENDAR front and second (ROOT.c.0, ROOT.c.1), 2010-06-06 -> 2026-10-01.
          Pulled by scripts/fetch_futport1.py: it prints the cost first and downloads only with --confirm.
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## Markets (29, fixed; each enters when its data starts)
| group | roots | cost per side (bp of notional) |
|---|---|---|
| equity | ES, NQ, YM, RTY | 1.0 |
| rates | ZT, ZF, ZN, ZB | 1.0 |
| FX | 6E, 6J, 6B, 6A, 6C, 6S | 1.0 |
| metals | GC, SI, HG, PL | 2.0 |
| energy | CL, NG, HO, RB | 2.0 |
| grains / softs-oil | ZC, ZS, ZW, ZL, ZM | 3.0 |
| livestock | LE, HE | 3.0 |

## Construction (fixed)
- **Returns:** the roll-adjusted c.0 daily return. On a day when the c.0 instrument changes, the return is measured against the previous day's c.1 close (the OILCARRY1 method).
- **Volatility:** σ = EWMA(com 60) of the daily return, annualised, lagged one day.
- **Trend signal:** the average of sign(1-month), sign(3-month) and sign(12-month) roll-adjusted returns (21 / 63 / 252 days), so it lies in [−1, 1].
- **Carry signal:** sign(c.0 / c.1 − 1). Positive (backwardation) = long, recomputed daily.
- **Sizing:** each market's position = signal × 0.10 / σ, capped at ±4. Each sleeve (trend, carry) is the equal-weight average over the markets active that day.
- **Portfolio:**
  - the sleeves are rescaled to 10% annual volatility using their own trailing 252-day realised vol (lagged), capped at 3× leverage;
  - **the portfolio is 50% trend + 50% carry.**
- **Costs:**
  - turnover |Δposition| × the group's cost per side;
  - each roll, the position held pays 2 sides;
  - no financing (futures carry is in the price).

## Gates (all must pass)
- **G1:** portfolio net Sharpe × √years ≥ 2.0 (about 0.5 over 16 years).
- **G2:** positive net return in each era: 2010-06 → 2015, 2016 → 2020, 2021 → 2026-09.
- **G3:** a higher Sharpe than the equal-risk long-only portfolio of the same markets (each long at 0.10/σ, same costs).

## Reported (no gates)
- each sleeve alone, and the correlation between the sleeves;
- correlation with ES;
- each group's contribution;
- the 2022 and 2020 episodes;
- worst drawdown;
- **small-account implementability**: the smallest account that can hold one contract per active market (micro contracts where they exist: MES, MNQ, MYM, M2K, MGC, SIL, MCL, M6E…), and the tracking error from whole-contract rounding at $25k / $100k.

## Prediction
- **Trend:** Sharpe about 0.3–0.6. The 2010s were a known weak decade for trend; 2022 was strong.
- **Carry:** about 0.3–0.5. **Combined:** about 0.5. G1 borderline, G3 likely.
- **A PASS is a lead for a forward record and an implementability check, never money by itself.**
