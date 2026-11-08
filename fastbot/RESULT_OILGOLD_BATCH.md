# RESULT — OILGOLD batch: oil's futures-curve carry passes, gold's real-yield snap-back passes narrowly but has faded, and the rest fail

```
SPEC:     PREREGISTRATION_OILGOLD_BATCH.md  sha 182b6e9f…  (frozen 2026-10-08, before any of this data existed)
METHOD:   TSMOM2 via scripts/tsmom1_run.py (TSMOM1's frozen sha 14c5b223…); OILCARRY1 / EIA1 / GOLDRY1 via scripts/oilgold_run.py (frozen before run)
DATA:     pulled 2026-10-10 (pull_oilgold.sh + EIA): OANDA WTI/Brent 15m; EIA WTI futures 1-4 and weekly crude stocks; FRED DFII10
LOGS:     data/run_tsmom2a.log, run_tsmom2b.log, run_oilcarry1.log (+ run_oilcarry1_rollfix.log), run_eia1.log, run_goldry1.log
RUN:      2026-10-11
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

| test | question | result | verdict |
|---|---|---|---|
| TSMOM2a | 12-month trend on oil alone | Sharpe +0.11 (t 0.5); 2006–12 −10% | **FAIL** |
| TSMOM2b | 12-month trend, 5 markets (gold, SPX, NAS, WTI, Brent) | Sharpe +0.41 (t 1.81), every era positive; equal-risk buy-and-hold Sharpe +0.41 | **FAIL** (G1) |
| **OILCARRY1** | oil futures curve: long when backwardated, short in contango | **Sharpe +0.47, ×√years 2.89 over 37 years; every era positive** | **PASS** |
| EIA1 | trade the weekly crude-stock surprise 15 min after release | −11.7 bp per release (t −2.4), negative in every era | **FAIL**, wrong sign |
| **GOLDRY1** | does gold snap back after drifting from real yields? | **slope −0.124 (t −2.09)**; eras −0.23 / −0.12 / **−0.00** | **PASS**, narrowly |
| GLDFLOW1 | do gold-ETF flows predict gold? | not run: the SPDR "archive CSV" link now returns a 120-page PDF | **NOT RUN** (data) |

## OILCARRY1 — the strongest result in the batch
- Over 1987 to 2024-04-05 (where the EIA futures series ends), a simple rule paid in every era:
  - long the front-month WTI future when the curve slopes down (backwardation);
  - short it when the curve slopes up (contango);
  - sized to 10% volatility.
- Net of costs it returned +5.6% a year, with a worst drawdown of −28%. Era sums: 1987–2004 +155%, 2005–14 +3%, 2015–24 +51%.
- This matches the published "carry" premium in commodities (Koijen, Moskowitz, Pedersen & Vrugt 2018). It is a **risk premium, not a prediction**, the same family as the VIX carry.
- **Roll-day fix (found after the run, logged as mechanical):**
  - The roll scan shows EIA's front-month series switches contract *on* the last trading day, one day earlier than the harness assumed (correlation 0.82 vs 0.63).
  - The error worked *against* the strategy. Corrected, the Sharpe rises to **+0.54** (×√years 3.29), and 2005–14 improves to +15%.
- **Reported:**
  - the F1/F4 slope gives Sharpe +0.51;
  - a continuous carry weight gives +0.27;
  - excluding the April 2020 negative-price days changes little (+0.51).
- **Caveats:**
  - These are futures returns, not CFD. OANDA's oil CFD would add financing.
  - It needs a futures account (or an ETF route) to hold.
  - The 2005–14 decade was flat.

## GOLDRY1 — real once, faded now
- **Gold falls when real yields rise:** about −8.8% per +1 percentage point over 4 weeks.
- **When gold drifts away from that relationship, it partly snaps back over the next month** (t −2.09).
- **The effect has disappeared since 2020** (slope −0.002). This is the familiar story of gold "decoupling" from real yields as central banks bought heavily. As registered it passes, but it would not survive the recent-regime test.

## EIA1 — the market reacts fast, then over-reacts
- **The first 15 minutes react hard and in the textbook direction:** a bigger-than-normal draw lifts oil about 15 bp per standard deviation (t −5.4).
- **Trading *with* the surprise from 15 minutes onward loses in every era** (−11.7 bp after spread). The initial move partly reverses by the 14:30 settlement.
- That reversal is a **post-hoc lead only**. Fading it would need its own pre-registration, and gross of the spread it is only about +7 bp.

## TSMOM2
- **Oil alone:** no trend premium after CFD costs.
- **Five markets:** positive in every era but t 1.8, the same as TSMOM1. It does no better than holding the same markets at equal risk (Sharpe 0.41 each).

## What follows
- **OILCARRY1 PASS:** a lead. Next is a pre-registered implementability check, like VIXIMP1: Micro WTI futures (MCL) or an ETF route, small-account sizing, roll costs, and a forward paper record. **No money.**
- **GOLDRY1 PASS:** forward record only. The recent era is zero.
- **GLDFLOW1:** find an alternative holdings source (e.g. the World Gold Council ETF data) and run it once that is pulled.
