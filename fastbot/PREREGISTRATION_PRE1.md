# PREREGISTRATION PRE1: can you be positioned BEFORE the 15:50 imbalance is published?

Frozen 2026-10-08, before any of the statistics below has been computed. Harness: `singlestock/pre1_run.py`. Data already on disk (IMB1 `days.csv`, BOUNCE1 `spy_path.csv`); nothing new is pulled.

I am not a financial adviser. This is a measurement, not a recommendation.

## Idea (from the literature, not from our data)
Part of the closing imbalance is predictable hours earlier. Leveraged and inverse ETFs must rebalance at the close in the **direction of the day's move**, mechanically (Cheng & Madhavan 2009; Barbon, Beckmeyer, Buraschi & Moerke on leveraged-ETF and option-hedging flows), and options dealers' hedging can do the same (our v42). If the day's move so far predicts the imbalance, a trader could be in **before** 15:50 instead of racing the professionals after it (Nasdaq reports ~80% of the close move is priced within 300 ms of publication).

## Definitions
- **Day move D_t** = SPY midpoint 15:50:00 ÷ SPY midpoint 09:30:30 − 1 (both known before publication).
- **Imbalance S_t** and **z_t** exactly as IMB1.
- **Target R_t** = SPY midpoint 16:00:01 ÷ midpoint 15:50:00 − 1 (bp): positioned at 15:50:00, before publication, held into the close.

## Gates (days with z_t, 2019-05 → 2026-09)
- **G1 (mechanism):** corr(D_t, S_t) > 0 with t ≥ 2.0 (HC regression of S_t on D_t).
- **G2:** OLS of R_t on D_t (in %): slope > 0, HC t ≥ 2.0.
- **G3 (tradeable):** on days with |D_t| ≥ 1%, take sign(D_t) × R_t − 1.0 bp: mean > 0, t ≥ 2.0.
- **G4:** G3 mean positive in each of 2019–20, 2021–23, 2024–26.
- PASS needs G2, G3, G4 (G1 is the mechanism check, reported either way).

## Reported
Same with entry at 15:50:00 and exit at 15:50:15 and 15:51; days with |D_t| ≥ 2% (the Rodier et al. 2012 rule, which earned 0.6% a trade gross in 2006–11, mostly late 2008).

## Prediction
G1 PASS (the mechanism is well documented). G3 FAIL: the flow is known to everyone, so the price likely adjusts before 15:50.

## One run.
