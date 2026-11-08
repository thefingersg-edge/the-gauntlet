# Pre-registration — reversal patterns

Written **before any result was looked at**, 2026-08-27. Held to `../GAUNTLET.md`.

## What Part B did and did not test

`b1_shapes.py` detects **converging trendlines** and classifies them three ways:
symmetrical triangle, rising wedge, falling wedge. That is the whole vocabulary.

**Not tested:** double tops and bottoms, head-and-shoulders and its inverse,
triple tops and bottoms. These are a different construction — a **level** test
(are two highs at the same price?) rather than a **slope** test (are two lines
converging?) — and the distinction matters for the gate Part B failed on.

Part B's wedges kept only 41–49% of detections when the swing-pivot window moved
by one bar, because a line fitted through three points is highly sensitive to
which points they are. A double top is defined by two prices being close to each
other, which is one number and plausibly more robust. **That is a real reason to
expect a different answer, and it is why this is worth running rather than
assumed.**

## Power, unlike the rest of this project

The closing measurement puts the portfolio-level noise floor at 0.165 Sharpe,
which swallowed every effect measured. Pattern tests are not in that regime:
each detection is an observation, Part B had 3,448 of them, and 21-day forward
returns have a standard deviation near 6%. At n ≈ 3,000 the standard error on a
conditional mean is about 0.11%, against an unconditional mean of +0.52%.

**This test can resolve a directional edge of roughly 0.2% or larger.** It is
one of the few well-powered questions left.

## Patterns and their textbook direction, fixed now

| pattern | construction | call |
|---|---|---|
| double top | two confirmed highs within `tol` of each other, an intervening low at least `depth` below, close breaks that low | **bearish** |
| double bottom | mirror | **bullish** |
| head and shoulders | three highs, middle highest, shoulders within `tol`, close breaks the neckline | **bearish** |
| inverse head and shoulders | mirror | **bullish** |

Detection is causal throughout: a pivot at bar *i* is only visible from *i + k*,
and confirmation is a close, never an intrabar touch.

## Gates

| # | criterion | threshold |
|---|---|---|
| 1 | **stability** — detections surviving pivot window 3 → 2 and 3 → 4, and the level tolerance ±50% | ≥ **80%** overlap, the same bar Part B failed |
| 2 | **sample** | ≥ 30 detections per era, pooled |
| 3 | **direction** — 21-day forward return signed by the textbook call | same sign in **all three eras** and in ≥ **14 of 21** markets |
| 4 | **against the unconditional** | the signed return must beat simply holding, +0.52% |
| 5 | **magnitude**, stated separately in advance — forward \|return\| ÷ prior vol, against a **volatility-matched** control | same sign in all three eras and ≥ 14 of 21 |

Gate 5 is written now for the reason Part B established: a failure on direction
must not be re-describable afterwards as a success on magnitude. Gate 4 exists
because Part B's wedges produced +0.02% against an unconditional +0.52% — beating
zero is not the bar, beating doing nothing is.

## Stated in advance

Part B found wedges mark quiet markets that stay quiet. Reversal patterns form at
extremes rather than in compressions, so the volatility-matched control is
expected to behave differently and is required rather than optional. If the
direction gate fails, the honest report is that a second family of chart patterns
carries no directional information — not that a magnitude result was found.
