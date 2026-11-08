# PREREGISTRATION v44 — options-expiry week and the week after, with dealer gamma

Frozen 2026-09-27, before any expiry-week return has been computed. The harness (scripts/opex_v44.py) will be written to this text and must pin its sha256.

I am not a financial adviser. This is a measurement, not a recommendation.

## Question
Monthly index-option expiry (the third Friday; Thursday when Friday is a holiday) removes a large block of dealer hedging at once. The common claim is that markets are pinned and calm into expiry, then freer and weaker the week after. v42 showed that dealer gamma (GEX) does shape intraday momentum. Does expiry change the next week's direction or volatility?

## Data
- SPX500 and NAS100, OANDA 5m bid/ask, cash sessions.
- SqueezeMetrics GEX (data/gex/DIX.csv, sha b64bccce…).
- Period: 2011-05 → 2026-08-14.

## Definitions
- **Expiry week (IN):** the five sessions ending with the expiry-day close.
- **Week after (OUT):** from the first session after expiry to the fifth, close to close.
- **Reference:** all other five-session windows starting on a Monday, non-overlapping.
- **Realised volatility:** the square root of the sum of squared 5m mid returns inside cash sessions, per window.

## Gates (two, Bonferroni t ≥ 2.24; SEs by expiry cycle)
- **H1 direction:** the mean OUT return is below the reference mean, with t ≤ −2.24. Net of one round-trip spread.
- **H2 volatility:** the mean of log(RV_OUT / RV_IN) per cycle is > 0 with t ≥ 2.24, and > 0 in each of 2011–16, 2017–21 and 2022–26.
- **Reported:** H2 split by the GEX tercile on expiry day (prior-day value); SPX and NAS separately.

## Budget (squared returns only)
- 167 post-expiry weeks out of 756. The weekly RMS is 233 bp, so **H1's MDE is about 56 bp a week**: only a large directional effect is visible.
- H2 is a within-cycle ratio and far better powered.
- **H2 is a volatility (sizing) result. It cannot make money on its own with CFDs.**

## Blind spots
- Quarterly expiries coincide with index rebalancing (v45 separates them).
- Weekly and 0DTE expiries since about 2016–2022 dilute the monthly event.

## One run.
