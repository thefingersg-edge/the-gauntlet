# ARM G-mem tuning: plan, fixed 2026-11-07 ~14:10 before the grid ran

Requested by Dave after the eight-variant search found nothing. This is open, labelled
in-sample tuning. Its result is a FITTED strategy and is never reported as a gate pass
of an untuned arm.

## Grid (2,160 combinations, all run, all logged to tune_grid.csv)
L {2,3,4,5,6}  V {40,60,100}  T {100,200,300}  K {1.5,2.0,2.5,3.0}  H {3,5,8}
M {3.0, 99 = no stop}  trend filter {with, none}

## Train = E1 + E2 (entries 2005-01 to 2019-06). Tuning sees nothing later.
Eligible: train trades >= 200, E1 net > 0, E2 net > 0, >= 14 of 21 markets positive on train.
Pick: highest train net per trade among eligible.

## Test, for the pick, reported whatever it shows
- E3 (2019-07 to 2026-08). Seen before in aggregate for spec 2, so a weak test.
- Unseen, after 2026-08-31. Clean, but small.
- Full-sample seven gates, Gate 7 against a stated 25% drawdown claim.
Also reported: the E3 result of the top 20 train combos, to show how much train rank
predicts test.

## Pass rule
"Tuned and worth forward-testing" requires the pick to be positive in E3 with net >= 0.10%
per trade, and to clear all seven full-sample gates. Otherwise: tuning does not rescue it.
