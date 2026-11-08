# ARM G-mem tuning: result (plan in TUNE_PLAN.md, grid in tune_grid.csv)

FITTED IN-SAMPLE. 2,160 combinations searched on 2005-2019. Never report this as an
untuned arm clearing gates.

## The pick
L=6, V=40, K=3.0, H=3, no stop, NO trend filter (so T does nothing).
In words: fade any 6-day move of 3 sigma or more, either direction, hold 3 days.
Tuning dropped the trend filter, the core of spec 2.

## Full-sample gates: 6 of 7
```
[PASS] 1 sign        E1 +0.609%  E2 +0.507%  E3 +0.248%
[PASS] 2 breadth     15 of 21
[PASS] 3 effect      +0.429% net (gross +0.577%, cost 0.148%)
[PASS] 4 sample      347
[FAIL] 5 robustness  K=2.25 keeps 12%, H=4 keeps 22%, L=4 keeps 27%, V=50 keeps 78%
[PASS] 6 control     +0.581%, 100% coverage
[PASS] 7 daily risk  8.0% measured vs a 25% claim
equity 10,000 -> 11,764 over 21 years, CAGR 0.8% (below cash)
```
Verdict under the plan: does NOT pass. E3 is positive (+0.248%, above the 0.10% bar),
but Gate 5 fails, and by far more than ARM F's 72-78%.

## Why the 6 of 7 is not evidence
- Knife edge: one step to the next grid value in K, H or L removes 73-88% of the edge.
- Train rank does not predict test. Among the 28 eligible combinations, the correlation
  of training net with E3 net is -0.03. The top 20 average -0.02% in E3; 10 of 20 are
  negative. The pick's E3 is luck of the draw among them.
- It is still mostly indices: 49 index trades net +2.53%; the other 298 net +0.08%.
  Breadth 15 is reached on markets averaging a few basis points.
- Long +0.86%, short -0.08%: the long side carries it, as with ARM F.
- 2026 so far: 13 trades, -1.35%. Unseen after 2026-08-31: 1 trade.

## Conclusion
Tuning can make this family clear six gates in-sample. It cannot make it robust, and
the selection carries no measurable information about the next seven years.
