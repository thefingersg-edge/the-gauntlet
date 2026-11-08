# PREREGISTRATION FORWARD_C1: the risk-control baseline, recorded forward

Frozen 2026-10-03. Recorder: `scripts/c1_forward.py`. Ledger: `data/c1_forward.csv`. **Paper only.**

I am not a financial adviser. This is a measurement, not a recommendation.

## Rule (from what survived: implied-vol sizing, IVSIZE / v52 G4; the 200-day filter, v52)
- **Exposure** to SPX500 and NAS100 each day = min(1.5, 15 / VIX of the previous close) × (1 if the previous close is above its 200-day average, else 0).
- **Comparison:** buy-and-hold, same instruments and days.
- **Costs:** the spread on each change of exposure, and OANDA financing on the exposure held.

## Why forward
v52's drawdown cut against random timing was found **after** its run (post-hoc). Here it is judged on days that do not exist yet.

## Verdict
- At 12 months: report max drawdown and Sharpe against buy-and-hold.
- At 36 months, verdict:
  - **useful** if the drawdown is ≤ 0.75 × buy-and-hold's **and** the Sharpe is no more than 0.1 below it.
- 12 months alone cannot settle it, and that is said now.

## One verdict.
