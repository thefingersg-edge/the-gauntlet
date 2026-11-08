# Pre-registration — grid agreement as a sizing input

Written **before running anything**, 2026-08-27, following the discipline of
`PREREGISTRATION_ADAPTIVE.md`. Same data, same execution model, same eras.

## The statistic

Over the 26 fixed `(fast, slow)` SMA crossover pairs already defined in
`core.PAIRS`:

```
A_t = mean over pairs of sign( SMA_fast(t) - SMA_slow(t) )      in [-1, +1]
```

`A` is **not fitted to anything**. It has no free parameter beyond the grid,
which was fixed before the previous study. |A| = 1 means every lookback from
8 to 256 days agrees on direction; |A| = 0 means the grid is split.

## The claim, and the reason it might work that does not reference a backtest

Directional forecasts have failed fourteen times in this project; sizing rules
(the stop-loss plateau, volatility targeting) have not. `A` is proposed as a
**confidence measure, not a forecast**: when short and long lookbacks disagree,
the price is inside a range that different observers read differently, and
exposure should be smaller — not because agreement predicts return, but
because disagreement marks the states where any single lookback's signal is
least reliable. That is a claim about *dispersion of the estimator*, and it is
falsifiable independently of whether trend itself pays.

## Why the previous study does NOT already answer this

`never_gridmean` in A4 averaged the 26 strategies' **returns**, which is
arithmetically the same position as `A_t` — but it charged each pair its own
turnover separately. Trading the aggregate nets those trades against each
other, so the real rule pays materially less cost. Cost netting is part of what
is being tested.

## Controls, and what each one rules out

| control | rules out |
|---|---|
| `sign(A)` at full size | that the gain is direction, not sizing |
| best single fixed pair, and the fixed-lookback curve | that the grid adds nothing over one good lookback |
| **shuffled magnitude**: `sign(A_t) x \|A\|` drawn from a far-lagged copy | that the gain is the *distribution* of exposures rather than their *timing* |
| volatility targeting alone, on a single fixed rule | that the gain is vol targeting wearing a new hat |
| matched average exposure and matched turnover | that the gain is simply being less invested |

## Pre-registered pass criteria

All seven, or the candidate is rejected.

| # | criterion | threshold |
|---|---|---|
| 1 | pooled 11-market Sharpe | beats the best single fixed pair **and** the best fixed lookback |
| 2 | per market | beats the fixed centre pair in ≥ **7 of 11** |
| 3 | per era | positive in **all three** |
| 4 | vs the shuffled-magnitude null | beats it, pooled and in ≥ **7 of 11** markets |
| 5 | vs `sign(A)` at full size | beats it — otherwise this is a direction result, not a sizing one |
| 6 | shape | **PLATEAU** across the sizing exponent γ in `sign(A)·\|A\|^γ`, not a spike |
| 7 | costs | survives **5bp** per unit turnover |

An eighth, stated as a separate question rather than a gate: does agreement add
anything **on top of** volatility targeting, which is the one effect this
project has already established? Tested as `A x vol_target` against
`sign(fixed) x vol_target`.

## What a failure looks like

If `sign(A)` at full size matches or beats `A`, the agreement magnitude carries
no information and the whole idea reduces to "average your lookbacks", which is
already known. If the shuffled-magnitude null matches it, the exposure profile
is doing the work and the timing is irrelevant. Either outcome is a rejection.
