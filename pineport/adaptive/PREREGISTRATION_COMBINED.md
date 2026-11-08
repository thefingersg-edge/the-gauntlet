# Pre-registration — the passes, combined

Written **before any combined result was looked at**, 2026-08-27. Held to
`../GAUNTLET.md`.

## What actually passed, and what kind of thing each one is

| from | what passed | what kind |
|---|---|---|
| C2 | inverse trailing-vol sizing beats constant sizing (+0.059, t +2.59, 9/11) | **size** |
| F/G | implied vol is the better sizing input where one exists (6/6 gates, replicated) | **size** |
| C1 | `sign(A)` — averaging 26 lookbacks — beats any single fixed pair (+0.267 vs +0.228) | **direction** |
| D3 | Δ real yield predicts equity/growth returns at a quarter (ρ ≈ −0.16, era-consistent, grid-stable) | **untested as a component** |

**Three of the four are sizing results.** That is not incidental — it is the
finding of the whole project, and it constrains what a combination can be.

## The honest prior, written before the run

Every sizing component is worth roughly +0.05 Sharpe. The direction component
loses to buy-and-hold by **0.46** (best rule +0.164 against the 21-market
basket's +0.624, Part H). Adding sizing improvements to a rule that far behind
cannot close the gap; that is arithmetic, not pessimism.

So the expected outcome is stated now: **the combination that survives will be a
risk overlay on long exposure, not a trading strategy.** If that is what the run
shows, it was predicted. If the directional stack unexpectedly beats
buy-and-hold, that is the surprise and gets treated as one.

## Design — one component at a time, so contributions are attributable

Each rung adds exactly one thing to the rung above. 21 markets, equal weight,
daily, 1bp and 5bp.

| # | rung |
|---|---|
| 0 | **buy and hold the basket** — the benchmark that has beaten everything so far |
| 1 | + inverse trailing-vol sizing |
| 2 | + implied-vol sizing on the six markets that have an index |
| 3 | + `sign(A)` direction (long/short rather than always long) |
| 4 | + real-yield overlay on the discount-rate markets |

Rung 4 is the only genuinely new test here and is scored separately: the other
three have already passed on their own and this is a composition, not a
re-litigation of them.

## Gates

| # | criterion | threshold |
|---|---|---|
| 1 | the full stack beats **its own best single rung** | otherwise stacking added nothing |
| 2 | in **all three eras** | 3 of 3 |
| 3 | beats buy-and-hold on Sharpe, **or** the risk case is stated with the drawdown number | one or the other, in writing |
| 4 | survives **5bp** | yes |
| 5 | the real-yield overlay beats a **destroyed-timing null** (750-day lag) | yes, or rung 4 is dropped |
| 6 | no rung's gain depends on one market (GAUNTLET 4.2) | top 3 under ~40% of positive contribution |

Gate 1 is the one that matters. This project has already established that four
correlated trend indicators stacked together are one effect measured four times,
not four discoveries. Three sizing rules stacked may be the same mistake in a
different coat, and the test for it is whether the stack beats the best rung
alone.
