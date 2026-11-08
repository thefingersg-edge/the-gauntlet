# PREREGISTRATION BOUNCE1: does the close that the auction imbalance pushed bounce back overnight? (+ a descriptive check of how long the imbalance effect takes)

Frozen 2026-10-07, before any of the SPY data below has been requested. Uses IMB1's frozen signal (z_t from `data/imb1/days.csv`, sha in PROVENANCE; `singlestock/imb1_run.zser`, unchanged).

I am not a financial adviser. This is a measurement, not a recommendation.

## Data (Databento, `scripts/databento_imb2.py` on Dave's Mac)
SPY quotes (`bbo-1s`, XNAS.ITCH, which includes after-hours) for every IMB1 trading day: 09:30:00–09:31:00 and 15:49:55–16:51:00 ET. Midpoints are taken as the last valid quote at or before each checkpoint (first at or after for 09:30:30 and 16:00:01).

## Part A — BOUNCE1 (gated)
- **Question:** after a large buy (sell) imbalance, does SPY fall (rise) from just after the close to the next morning, as forced closing flow unwinds?
- **Target:** b_t = SPY mid at 09:30:30 on the next trading day ÷ SPY mid at 16:00:01 − 1, in bp.
- **Cost:** 3.0 bp per trade = 1.0 bp spread (close + open) + 2.0 bp for one night's CFD financing (OANDA charges roughly the policy rate + 2.5% a year on index CFDs; our fills audit showed financing is material).
- **G1:** OLS of b_t on z_t: slope < 0 with HC t ≤ −2.0.
- **G2:** on |z_t| ≥ 1 days, trade −sign(z_t) from 16:00:01 to 09:30:30: mean of −sign(z)·b − 3.0 > 0 with t ≥ 2.0.
- **G3:** G2's mean net positive in each of 2019–20, 2021–23, 2024–26.
- PASS needs all three. Prediction: FAIL (IMB1 showed the close is barely pushed, so there is little to bounce).

## Part B — how long does the imbalance effect take? (DESCRIPTIVE, no gate)
- For each checkpoint h in {15:50:15, 15:50:30, 15:51, 15:52, 15:55, 15:58, 15:59:59, 16:00:01, 16:05, 16:15, 16:30, 16:50}: slope (HC t) of the SPY return from the 15:50:00 midpoint to h on z_t.
- Shows whether the effect builds after 15:51 (our window was too short), is all in the first minute (too fast for us), or simply isn't there. After 16:00 SPY trades thinly after-hours, so those checkpoints are reported with that caveat. **No trading conclusion may be drawn from Part B**; any idea it suggests needs its own pre-registration.

## One run of each.
