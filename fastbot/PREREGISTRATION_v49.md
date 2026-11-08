# PREREGISTRATION v49 — does the FTSE open under-react to overnight US and European moves?

Frozen 2026-09-27, before any first-hour UK100 return has been joined to a predictor. The harness (scripts/ukopen_v49.py) must pin this sha256.

I am not a financial adviser. This is a measurement, not a recommendation.

## Question
- The FTSE 100 is heavy in miners, energy and global earners.
- Between the London close (16:30) and the next open (08:00), US markets trade for 4.5 more hours and European futures move from 07:00.
- The UK100 CFD trades overnight too, so most of this is priced in. The question is whether the cash open finishes the job or leaves a predictable first-hour move.

## Data (all OANDA, cash-session anchored)
- UK100 5m (data/v38) and DE30 5m (data/v38), 2013 → 2026-09-25.
- SPX500 15m (data/v24), converted to London time.

## Definitions (all inputs known by 07:55 London)
- **UK_on:** UK100 from the prior 16:25 bar close to the 07:55 bar close.
- **US_on:** SPX500 from the 16:30 London mark (the nearest 15m bar close at or before) to the last bar closing at or before 07:55 London.
- **EU_pre:** DE30 from 07:00 to 07:55 London.
- **Residual:** R = US_on − β·UK_on, where β is estimated on the prior 250 days only.
- **Target:** the UK100 first hour, from the 08:00 bar open to the 08:55 bar close.

## Gates (SEs clustered by date; two tests, t ≥ 2.24)
- **G1:** in First hour = a + b1·R + b2·EU_pre, b1 > 0 with t ≥ 2.24 (under-reaction to the US).
- **G2 tradeable:** when |R| is in the top fifth of its trailing 250 days, trade the first hour in the sign of R. The net after the quoted spread is > 0 with t ≥ 2.24, and > 0 in each of 2013–17, 2018–21 and 2022–26.
- **Reported:** b2 (the European pre-open) and the reverse sign (over-reaction).

## Budget
- 3,441 days. The first-hour RMS is 36.1 bp; a top-fifth trade gives about 688 days, so **the MDE is about 4.2 bp.**
- The UK100 spread is about 1.5–2 bp.

## Blind spots
- The CFD overnight quote may already carry everything, in which case b1 ≈ 0. That would be the expected answer.

## One run.
