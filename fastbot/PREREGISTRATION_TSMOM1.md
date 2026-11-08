# PREREGISTRATION TSMOM1: time-series momentum (trend following) on gold, S&P 500 and Nasdaq 100

Frozen 2026-10-08, before any trend statistic has been computed on these markets. Harness `scripts/tsmom1_run.py` (frozen by sha before it runs). Oil is added separately as TSMOM2 when its data exists.

I am not a financial adviser. This is a measurement, not a recommendation.

## Background
Moskowitz, Ooi & Pedersen (2012, "Time series momentum") and Hurst, Ooi & Pedersen (2017, "A century of evidence on trend-following investing"): a market's own past 12-month return predicts its next month, across asset classes, for over 100 years. A documented premium — the family that survives in this project — and never tested here.

## Rules (the published recipe, not tuned)
- **Markets:** OANDA XAUUSD, SPX500, NAS100 (mid prices), daily close = 16:00 New York (the 15:45 15-minute bar's close), 2005 → 2026-09-25.
- **Volatility:** σ_t = annualised exponentially weighted SD of daily returns (centre of mass 60 days), using data to day t only.
- **Signal:** at each month-end close, s = sign of the market's return over the previous 12 months.
- **Position:** w = s × 10% / σ (10% volatility target per market), capped at ±3× notional; portfolio = equal-weighted average of the three markets.
- **Execution:** the new position is taken at the **next** day's 16:00 close (one-day lag, so no look-ahead) and held until the next rebalance.
- **Costs:** half the quoted spread on every unit traded (the spread at that bar); daily CFD financing at the measured OANDA rule (long pays policy rate + 2.5%, short receives policy rate − 2.5%, per calendar day).

## Gates (performance from 2006-01, after the 12-month warm-up)
- **G1:** portfolio net annualised Sharpe × √years ≥ 2.0 (Sharpe ≥ about 0.43 over 20.7 years).
- **G2:** portfolio net return positive in each era 2006–12, 2013–19, 2020–26.
- PASS needs both.

## Reported (not gated)
1- and 3-month lookbacks; each market alone; without financing; equal-risk buy-and-hold on the same markets with the same costs (the benchmark a trend rule must justify itself against); worst drawdown.

## Budget / prediction
Published trend Sharpe is about 0.3–0.5 per market, and two of these three markets are highly correlated, so the portfolio Sharpe is likely 0.3–0.5: G1 is borderline. Prediction: G1 FAIL narrowly, G2 PASS.

## One run.
