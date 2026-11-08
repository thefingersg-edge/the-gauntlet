# PREREGISTRATION v52: the 200-day moving average as a risk overlay

Frozen 2026-10-01, before any overlay return has been computed. The budget used daily closes for counts and volatility only. The harness (scripts/ma_overlay_v52.py) must pin this file and scripts/daily_close.py (sha 617eadd2fc60ae99a736e0fa8b7455e12f0c3918069f3587f4176e5b0044c88c).

I am not a financial adviser. This is a measurement, not a recommendation.

## Question
- The only tools that have survived this programme are **risk overlays on long exposure**: vol targeting, implied-vol sizing, and a VIX exit for carry.
- The classic overlay, holding the market only above its 200-day average, has never been tested here on its own.
- **The question:** does it cut drawdowns without giving up return-to-risk, and is its timing better than chance?

## Data
- Daily closes from daily_close.py (struct15 15m caches) for SPX500, NAS100, UK100 and XAUUSD. The close is the 15m bar ending at each market's cash close (New York 16:00; London 16:30; gold at the 17:00 New York roll).
- **Sample:** 2005 (2006-03 for gold) through **2026-09-25**. The first 200 days of each series are warm-up.
- Financing uses DGS3MO from fastbot/data/DGS3MO.csv.

## Definitions
- **Flag:** F_t = 1 if close_t > the mean of the last 200 closes up to and including t; otherwise 0.
- **Position:** the position over close t → close t+1 is F_{t−1}. That is a one-day delay, so no trade is executed at the same close that decided it.
- **Costs:**
  - One full quoted spread (at that day's close bar) on each switch.
  - Financing while long: (DGS3MO + 2.5%)/360 per calendar night, so Friday → Monday is three nights.
  - Flat earns 0.
  - Buy-and-hold (B&H) pays the same financing.
- **Portfolio:** the equal-weighted mean of the four instruments' daily returns.
- **Eras:** 2005–12, 2013–19, 2020–26.

## Gates (verdict "useful risk overlay" requires G1, G2 and G3)
- **G1, drawdown:** the portfolio overlay's max drawdown is ≤ 0.75 × B&H's. In each era, the overlay's max drawdown is ≤ B&H's.
- **G2, timing is real:**
  - **Null:** for each of 500 draws, circularly shift each instrument's flag series by an independent random offset of at least 250 days. This keeps the time in market and the run lengths but breaks the timing.
  - **Pass:** the overlay portfolio's Sharpe exceeds the null's 95th percentile.
- **G3, return-to-risk:** overlay Sharpe ≥ B&H Sharpe − 0.05, **and** overlay Calmar (annual return / |max drawdown|) > B&H Calmar.
- **G4, adds to the stack** (separate label: "adds to vol sizing"):
  - **Base:** for SPX500 and NAS100, an implied-vol-sized long with exposure = min(1.5, 15 / VIX_{t−1}). VIX is used for both, since VXN is not held.
  - **Pass:** applying the flag on top raises the 2-instrument Calmar, and lowers its Sharpe by no more than 0.05, compared with the vol-sized base alone.

## Reported (not gated)
- A 100-day MA.
- Same-day execution (no delay).
- Per instrument.
- Time in market and number of switches.
- Comparison with the v50 VIX rule (flat when VIX_{t−1} is in the top fifth of its prior 250 values).

## Budget
- Each series has about 21.7 years (gold 20.5). Daily volatility is 19.0% (SPX), 21.9% (NAS), 17.4% (UK) and 18.3% (gold) a year. A Sharpe ratio's SE is about 0.21 per instrument.
- **A difference in Sharpe between an overlay and its own base is not resolvable in 21 years.** That is why the gates are about drawdown, beating a timing-destroyed null, and not giving up return-to-risk, rather than claiming a higher Sharpe.
- **Prediction, written now:** G1 PASS (equities). G2 marginal. G3 likely PASS on Calmar. Gold is the likely weak spot.

## Blind spots
- 2008 and 2022 dominate any drawdown comparison, so G1 effectively turns on two or three bear markets.
- A CFD account earns nothing when flat. Real cash would add a little to the overlay.
- The overlay saves financing while flat. That is real for a CFD, but it flatters the overlay compared with futures.

## One run.
