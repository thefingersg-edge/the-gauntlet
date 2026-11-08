# PREREGISTRATION v45 — index rebalancing days: last-hour pressure and next-morning reversal

Frozen 2026-09-27, before any rebalance-day return has been computed. The harness (scripts/rebal_v45.py) must pin this sha256.

I am not a financial adviser. This is a measurement, not a recommendation.

## Question
S&P 500 and FTSE 100 quarterly reviews, and the Nasdaq-100's December reconstitution, take effect at the close of the third Friday of March, June, September and December. Index funds must trade in the closing auction, so price pressure into the close should partly reverse the next morning.

## Data
- SPX500, NAS100 (OANDA 5m, from 2005) and UK100 (5m, data/v38, from 2013).
- Rebalance days: quarterly third Fridays (Thursday when a holiday) that fall in the data.

## Definitions
- **Last hour (LH):** the return from close − 60 min to the close. US: 15:00 → 15:55 bar close. UK: 15:30 → 16:25 bar close.
- **Next morning (NM):** the next session's open → open + 60 min.
- **Controls:**
  - (a) the other monthly-expiry Fridays, which have witching but no rebalance;
  - (b) all other Fridays.

## Gate (one primary; SEs clustered by date)
- **Primary:** in NM = a + b·LH, estimated on rebalance days pooled across the three indices, b < 0 with t ≤ −2.0 (reversal), **and** b(rebalance) < b(control a) with the difference t ≤ −2.0.
- **Reported:** a trade that fades the LH direction over NM, net of spread; per-index results.

## Budget
- About 84 US quarterly days (2005–26) and about 55 UK days, but the indices move together. The last-hour RMS is 28 bp.
- **Low power:** only a reversal of at least about a third of the last-hour move is visible.

## Blind spots
- Index-level pressure is much smaller than constituent-level pressure: funds buy additions and sell deletions, and these largely cancel in the index.
- Rebalance days coincide with quad witching; control (a) separates the two.
- The special Nasdaq rebalance (July 2023) is not included.

## One run.
