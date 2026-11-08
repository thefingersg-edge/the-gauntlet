# PREREGISTRATION v47 — the London gold fix

Frozen 2026-09-27, before any fix-window return has been computed. The harness (scripts/goldfix_v47.py) must pin this sha256.

I am not a financial adviser. This is a measurement, not a recommendation.

## Question
- The London PM gold fix (15:00 London) is a benchmark auction that funds, miners and jewellers must trade at.
- Studies of the pre-2015 fixing (Abrantes-Metz & Metz 2014; Caminschi & Heaney 2014) reported unusual, often downward, price moves around the PM fix.
- In March 2015 the fix was replaced by the ICE-run LBMA Gold Price auction.

Does the pattern exist on this data, and did it survive the reform?

## Data
XAU/USD, OANDA 15m bid/ask (data/v24), 2006-03 → 2026-09-25, in London time.

## Definitions
- **PM window:** 14:45 → 15:15 London, from the 14:45 bar open to the 15:00 bar close.
- **AM window:** 10:15 → 10:45 London (reported only).
- **Eras:** pre-reform (to 2015-03-19) and post-reform (from 2015-03-20).

## Gates
- **G1 replication (pre-reform):** mean PM-window return < 0 with t ≤ −2.0.
- **G2 tradeable (post-reform):** mean PM-window return < 0 with t ≤ −2.24, **and** a short over the window is net positive after the quoted spread. Post-reform bid/ask is real.
- **Reported:** the AM window; the reversal 15:15 → 16:15; by year.

## Budget
- 2,323 pre-reform and 2,973 post-reform days. The window RMS is 28.7 bp, so **the post-reform MDE is about 1.4 bp.**
- The gold spread is about 1.5 bp. A tradeable edge would need to be above about 2–3 bp.

## Blind spots
- 15m bars blur the exact 15:00 auction. OANDA gold is a spot CFD, not the auction itself.
- The prior is that the reform removed whatever existed.

## One run.
