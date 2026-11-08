# H4 test of the tuned rule: result (plan in H4_PLAN.md, script run_h4.py)

Run 2026-11-07 ~16:00 on engine.py as updated 15:52 the same day (v2 partial:
metals markup 1.19%; breadth also counted over priced instruments only).

## PLAN VERDICT: FAIL. The daily result is treated as fitted noise.
```
E1 0.000%   E2 -0.136%   E3 +0.087%      (needed: all three positive)
net -0.015% per trade, t -0.32, 1,618 trades   (needed: >= +0.10%)
gross +0.090%, cost 0.106%
Gates for reference: 2 of 6 (sample, matched control). Breadth 10 of 21
(7 of 15 priced). Gate 7 not computed (see plan).
```

## Detail
- Indices +0.12% net on 205 trades; the other 18 markets -0.035% on 1,413.
- Trades closed the same day: +0.095% net. Held over one or more nights: -0.074%.
- About 70 trades a year, so H4 would have given a fast forward test. It has nothing
  to test.

## Daily pick re-run on the updated engine (for comparison)
6 of 7 unchanged, net +0.432% per trade, E1 +0.611% E2 +0.510% E3 +0.251%,
breadth 15 of 21 (12 of 15 priced), Gate 5 worst K=2.25 at 12%.

## Reading
The same rule, at the same bar counts, on data the tuning never saw, has no edge in two
of three eras and none overall. What survives in every version tested today is the
equity-index effect ARM F found. The tuned daily strategy should not be forward-tested
as a strategy; if anything is recorded forward, it is the index dip-buy.
