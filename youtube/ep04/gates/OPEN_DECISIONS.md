# Two unregistered implementation choices that decide verdicts

```
WRITTEN: 2026-11-02, after Arm F part A was run and BEFORE the other five
         arms are run. Both apply to all six arms, so they are settled once,
         here, rather than per arm.
```

Both of these are degrees of freedom I currently hold, and in both cases my
choice changes whether an arm passes. That is exactly the thing this
project exists to attack, so neither gets decided quietly.

## 1. Gate 5 — what is a "half-step"?

The preregistration says "at least 80% of the edge survives moving every
parameter by half a step in both directions". **It never defines the step.**
Arm B declared its own step table. Arm F did not. So I chose one, and the
choice decides the gate:

| Parameter | My step | Half-step tested | Result |
|---|---|---|---|
| time_limit (10 bars) | 10 | 5 and 15 | **5 bars -> 69% of base. FAILS.** |
| rsi_entry (20) | 10 | 15 and 25 | **25 -> 78% of base. FAILS (just).** |
| everything else | — | — | 80%-106%. Passes. |

Halving a 10-bar holding period to 5 is not obviously "half a step" -- it
is a structural change to the strategy. Under a uniform **+/-25% of value**
rule instead, time_limit would be tested at 8 and 13, and would very likely
pass.

So: my step table fails the arm, a proportional rule probably passes it.
Neither is more honest than the other, but picking after seeing that is
indefensible.

**Recommendation: a uniform rule, fixed now, applied to all six arms --
every parameter perturbed by +/-25% of its own value, rounded to the
nearest valid value.** It is mechanical, it cannot be tuned per arm, it
needs no judgement about what a parameter "means", and where an arm
declared its own steps (Arm B) we report both.

The alternative -- keep my hand-made table -- is acceptable only if it is
published in full with the admission that we wrote it.

## 2. Gate 6 — the matched control has knobs too

The preregistration says "matched on era, prior return and volatility". It
does not say over what window, into how many buckets, or against how many
control bars. I used, following the existing implementation in
`pineport/adaptive/o1_kalman.py`:

```
prior-return window    20 bars
volatility window      20 bars
buckets                10 x 10 deciles, within market
control bars sampled   up to 50 per trade, non-overlapping with any trade
horizon                same number of bars as the trade
costs                  identical to the trade
```

These are defensible and they are inherited rather than invented, which is
the best thing about them. But a shorter prior window, coarser buckets, or
allowing control bars that overlap trades would all move the number.

**Recommendation: keep exactly these, because they predate this study, and
publish them as part of the gate definition.** Then report one sensitivity
-- the same gate at a 60-bar prior window and 5x5 buckets -- so a viewer can
see the result is not an artefact of the bucketing.

## Why this is being raised now

Five arms are still unrun. If these are fixed after seeing their results,
every verdict in both episodes is worthless. Fixed now, they are simply
part of the method.
