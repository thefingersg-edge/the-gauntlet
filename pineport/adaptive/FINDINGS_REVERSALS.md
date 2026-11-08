# Reversal patterns — none of them holds

> ## CORRECTION — the control in the first version of this file was broken
>
> Each detection was compared against non-detection days in the same cell, with
> a **±21-bar window** around every detection excluded from the control pool.
> With a pattern firing hundreds of times per market that window removes most of
> the series, and the cell means are then computed on a handful of survivors.
> The same construction in `b3_pattern_zoo.py` reported a **+4.67% baseline
> against a +0.76% unconditional** on gold, which is how it was caught.
>
> With the pool corrected to exclude only the detection bars themselves:
>
> | claim in the first version | corrected |
> |---|---|
> | all four patterns above control, pooled +0.0044, t +2.47 | **two above, two below** — the "one state" reading does not survive |
> | head and shoulders significantly bullish, excess +0.0080, t **+2.55** | +0.0043, t **+1.47** — not significant |
> | double bottom excess +0.0085, t +1.97 | +0.0098, t +2.33 |
>
> **The verdict is unchanged — the patterns still fail — but the mechanism story
> was wrong and is removed below.** Every number that follows is post-correction.

Run 2026-08-27 against `PREREGISTRATION_REVERSALS.md`, written first. 21 markets,
2005–2026. Reproduce with `python3 b2_reversals.py`.

Part B tested converging trendlines only. This adds the level constructions —
double tops and bottoms, head-and-shoulders and its inverse. **1,774 detections**,
543–681 per era, so unlike most of this project the test is well powered.

## Verdict: fails, and my stated reason for expecting otherwise was wrong

| gate | threshold | observed | |
|---|---|---|---|
| 1 · stability under perturbation | ≥ 80% | **43% / 66% / 63% / 40%** on four of six | ✗ |
| 2 · sample size | ≥ 30 per era | 543–681 | ✓ |
| 3 · direction, same sign in 3 eras and ≥14/21 | | **+0.0015 / −0.0022 / +0.0075**, 13/21 | ✗ |
| 4 · beats the unconditional (+0.43%) | | +0.22%, better in **9 of 21** | ✗ |
| 5 · magnitude vs vol-matched control | | ratio 1.042 | see below |

The pre-registration argued a double top might survive the pivot gate the wedges
failed, because a level is one number where a fitted line is three points. **It
does not.** Moving the swing-pivot window from 3 to 2 keeps **43%** of
detections, against the wedges' 41%. The construction was not the problem;
pivots are.

## The per-pattern table, which is where it gets interesting

Signed by each pattern's textbook call:

| pattern | n | mean | t |
|---|---|---|---|
| double bottom | 410 | **+0.0163** | **+3.87** |
| inverse head and shoulders | 520 | +0.0057 | +1.95 |
| double top | 377 | −0.0031 | −0.76 |
| **head and shoulders** | 467 | **−0.0099** | **−3.36** |

The two **bullish** patterns work and the two **bearish** ones fail, head and
shoulders significantly so — it is wrong against its own call at t = −3.36. That
shape is the signature of a long bias rather than a pattern effect, so it was
tested directly.

## The control that settles it

Each detection compared against non-detection days in the **same market, same
era, and same prior-21-day-return decile** — so drift and post-decline
mean-reversion are matched out.

| pattern | raw | matched control | **excess** | t |
|---|---|---|---|---|
| double bottom | +0.0163 | +0.0065 | **+0.0098** | **+2.33** |
| head and shoulders | +0.0099 | +0.0055 | +0.0043 | +1.47 |
| inverse head and shoulders | +0.0057 | +0.0058 | −0.0001 | −0.03 |
| double top | +0.0031 | +0.0078 | −0.0048 | −1.21 |

Two thirds of double bottom's raw +1.63% was drift and post-decline
mean-reversion; what is left is +0.98% at t = +2.33. Head and shoulders still
runs the wrong way against its own bearish call, but at t = +1.47 that is not a
claim worth making. **Nothing here is significant once the number of patterns
tested is counted** — see `FINDINGS_ZOO.md`, where 25 more constructions were run
and double bottom's closest relative, triple bottom, returned +0.16% across 7 of
21 markets.

Signed by the textbook call, after the control:

| | n | mean | t |
|---|---|---|---|
| 2005–12 | 681 | −0.0002 | −0.06 |
| 2012–19 | 550 | −0.0000 | −0.01 |
| 2019–26 | 543 | +0.0072 | +2.21 |
| **all** | **1,774** | **+0.0021** | **+1.22** |

**Zero in two eras out of three, and 13 of 21 markets.** The textbook direction
is worth nothing.

## What is left

Double bottom, at +0.98% over 21 days with t = +2.33 on 410 detections, is the
only construction in this family with any life in it. Against roughly 90 tests
run across the pattern programme, one t of 2.3 is what chance delivers, and its
nearest relative in `FINDINGS_ZOO.md` — triple bottom, n = 13,585 — returns
+0.16% and holds its sign in 7 of 21 markets.

The magnitude result (1.042 against a vol-matched control) is consistent across
eras, but it is a 4% effect and was pre-registered as a secondary precisely so
that a direction failure could not be reported as a magnitude success.

## Together with Part B

Two families of chart pattern, seven constructions, 5,222 detections:

- **Converging trendlines** mark quiet markets that stay quiet — vol expansion
  *below* a vol-matched control in 11 of 11 markets.
- **Reversal patterns** mark pulled-back markets that drift up — +0.44% above a
  drawdown-matched control, on all four regardless of direction.

Both carry information about **state**. Neither carries information about
**direction**. And both fail the pivot-stability gate at 40–49%, which means even
the state reading depends on where you decide the swings are.
