# PREREGISTRATION BUYBACK1: does the S&P 500 do worse when most companies are in their buyback blackout?

Frozen 2026-10-08, before any blackout statistic has been computed. Harness `singlestock/buyback1_run.py`. Data in hand (Sharadar S&P 500 membership and 8-K earnings dates; OANDA SPX500).

I am not a financial adviser. This is a measurement, not a recommendation.

## Idea
US companies are the largest buyers of their own shares, but most stop buying from a few weeks before the quarter ends until just after they report earnings (the "blackout"). Market commentary often says the index lacks support when most of the S&P 500 is in blackout. The blackout calendar is knowable in advance.

## Definitions (fixed)
- **Members:** point-in-time S&P 500 (Sharadar quarter-end snapshots ± additions/removals, as BREADTH2).
- **Blackout for a member:** from 14 calendar days before each calendar quarter end (Mar/Jun/Sep/Dec) until 2 trading days after its first 8-K Item 2.02 (earnings release) filed within 75 days after that quarter end. A member with no such filing that quarter is left out of that quarter.
- **B_t** = share of included members in blackout on day t (known in advance).
- **Target:** OANDA SPX500 return from the 16:00 close of day t to the 16:00 close of day t+5 (bp).

## Gates (2005-04 → 2026-09)
- **G1:** OLS of the 5-day return on B_t (per 10 percentage points): slope < 0, Newey-West (5 lags) t ≤ −2.0.
- **G2:** slope negative in each era 2005–12, 2013–19, 2020–26.
- PASS needs both.

## Reported
Days with B_t ≥ 60% minus days with B_t ≤ 20%; 20-day horizon; the share of members dropped for missing earnings dates.

## Caveats stated now
B_t is strongly seasonal (it peaks every quarter around early earnings season), so it also stands in for anything else that happens at that time of the quarter. Equal-weighted (not by company size), although the largest buybacks come from the largest companies.

## Prediction
FAIL (blackout talk is popular; evidence for an index effect is thin).

## One run.
