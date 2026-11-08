# ARM G-mem improvement search: plan, fixed before any variant was run

Written 2026-11-07 ~11:40, after spec 2 was gated (4 of 7) and diagnosed, before
any variant below was run. Spec 2 is a memory-open side test, not an arm.

## What was already seen (contamination, declared)
- Spec 2 full-sample gates, per-era, per-asset-class, per-|z| bucket, per year.
- Gate 5 rows for spec 2: K=2.5 gave +0.43%, L=5 gave +0.22%, both pooled over all eras.
- Spec 1's results (RESULT_ARM_G.md).
So E3 is NOT a clean holdout. The only clean data is after 2026-08-31.

## Variants: the complete list, eight, no additions
| id | change from spec 2 | why |
|---|---|---|
| G0 | none | baseline |
| G1 | K = 2.5 | |z| buckets rise monotonically 2.0 to 3.0+ |
| G2 | K = 3.0 | same, further |
| G3 | no trend filter, K = 2.0 | is the trend filter a hidden trend factor? |
| G4 | no trend filter, K = 2.5 | same at the higher threshold |
| G5 | trend read at t-L, K = 2.5 | spec 1's rule, so the shock cannot flip its own filter |
| G6 | K = 2.5, M = 99 (no stop) | 38 stops lost 5.7% each |
| G7 | K = 2.5, H = 3 | shorter hold, less financing |

## Selection rule, using E1 + E2 only (2005-01 to 2019-06)
Eligible: E1 net > 0 and E2 net > 0, and at least 14 of 21 markets positive on E1+E2.
Pick: the eligible variant with the highest E1+E2 net per trade. None eligible means
the search found nothing.
Then, for the pick only: full-sample seven gates, E3 net, and the unseen data after
2026-08-31, reported whatever they show.

## Verdict rule
"Improved" means: the pick clears all seven gates on the full sample AND is positive in
E3 AND positive on unseen data. Anything less is reported as not improved. Gate 7 is
scored against a stated drawdown claim of 25%, not vacuously.
