# PREREGISTRATION OILGOLD batch: TSMOM2, OILCARRY1, EIA1, GOLDRY1, GLDFLOW1

Frozen 2026-10-08, before any oil, real-yield or GLD data exists on disk. Each harness is written to this spec and frozen by sha **before** its data is first read for a result. Data comes from `scripts/pull_oilgold.sh` (Dave's Mac).

I am not a financial adviser. This is a measurement, not a recommendation.

---
## TSMOM2 — trend following on oil, and the five-market portfolio
- Exactly TSMOM1's frozen harness (`scripts/tsmom1_run.py`, same sha) with `--markets WTICO_USD,BCO_USD --tag tsmom2a` (oil alone) and `--markets XAU_USD,SPX500_USD,NAS100_USD,WTICO_USD,BCO_USD --tag tsmom2b` (all five).
- Gates as TSMOM1 (net Sharpe t ≥ 2.0; positive in each era). Judged separately; Bonferroni not applied (two related runs, both reported).
- OANDA financing for oil CFDs is not measured; the index rule (policy rate ± 2.5%) is used and stated as an assumption.

## OILCARRY1 — does the shape of the oil futures curve predict returns?
- **Data:** EIA daily NYMEX WTI futures, contracts 1–4 (series PET.RCLC1–4.D), 1986 → 2026.
- **Signal:** at each month end, carry = F1 / F2 − 1 (positive = backwardation, the curve slopes down).
- **Position:** long front-month when carry > 0, short when < 0; 10% volatility target (60-day EWMA), cap ±3.
- **Return:** front-month futures excess return, rolled when contract 1 changes (the return on a roll day uses the new contract's prior price), minus 2 bp per unit traded.
- **Gates:** G1 net Sharpe × √years ≥ 2.0 over 1987–2026; G2 positive in 1987–2004, 2005–2014, 2015–2026. Reported: carry as a continuous weight; F1/F4 slope.
- Background: Koijen, Moskowitz, Pedersen & Vrugt ("Carry", 2018); Gorton & Rouwenhorst on commodity futures.

## EIA1 — do weekly crude inventory surprises move oil after the release?
- **Data:** EIA weekly US crude stocks excluding SPR (PET.WCESTUS1.W); OANDA WTICO_USD 15m bid/ask.
- **Release time:** Wednesday 10:30 ET after the reference week (Friday); if a US federal holiday falls Monday–Wednesday of that week, Thursday 11:00 ET. Stated as an approximation.
- **Surprise:** weekly change in stocks minus the average change for the same week of the year over the previous five years (no consensus history is used).
- **Trade:** −sign(surprise) (a bigger-than-normal draw is bullish), entry at the open of the 15-minute bar 15 minutes after the release, exit at the close of the 14:15 bar (the 14:30 settlement), paying the quoted spread.
- **Gates (2006 → 2026):** G1 mean net > 0, t ≥ 2.0; G2 positive in 2006–12, 2013–19, 2020–26.
- **Reported:** the first 15 minutes (release → +15 min) regressed on the surprise — shows whether the market reacts at all.

## GOLDRY1 — does gold snap back when it drifts away from real yields?
- **Data:** FRED DFII10 (10-year TIPS real yield, daily, 2003 →), OANDA XAUUSD daily 16:00 NY.
- **Weekly (Fridays):** regress gold's 4-week log return on the 4-week change in DFII10 over the previous 104 weeks; residual = this week's actual minus fitted.
- **Gates:** next 4-week gold return regressed on the residual: slope < 0 (mean reversion), Newey-West (4 lags) t ≤ −2.0; negative in 2005–12, 2013–19, 2020–26.

## GLDFLOW1 — do gold ETF flows predict gold?
- **Data:** SPDR GLD daily holdings in tonnes (sponsor archive, 2004-11 →), OANDA XAUUSD daily.
- **Signal:** % change in GLD tonnes over the week to Friday. **Target:** gold return over the following week (Friday 16:00 → Friday 16:00).
- **Gates:** slope > 0 (flows persist), Newey-West (1 lag) t ≥ 2.0; positive in 2005–12, 2013–19, 2020–26.

---
**Predictions:** TSMOM2 oil — borderline; OILCARRY1 — the best prior (a documented premium); EIA1 — FAIL (released information is priced within minutes); GOLDRY1 — FAIL; GLDFLOW1 — FAIL.
