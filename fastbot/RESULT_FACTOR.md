# RESULT — which part of the release move comes back? Neither.

```
RUN:      2026-09-25
SPEC:     PREREGISTRATION_v28, amended by v28.1, both frozen before the
          run and checked by sha256 at run time
CODE:     premarket_factor.py 1.0
SAMPLES:  equity indices only (SPX500, NAS100, US30, DE30)
          S1 CPI+payrolls 1,868   S2 claims 3,052   S3 control 13,456
VERDICT:  G1 FAILS (-0.023, t -0.21). G2 FAILS. The split explains
          nothing, my registered prediction was wrong, and absorption
          joins the other three dead explanations.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. Gate 0 — the file reads the bars the way v27 did

27,486 trades matched against `horizon_v27_trades.csv`, largest
disagreement **5e-07 bp**. Reported beside it, with no threshold: the
four-equity mean fade at 09:45 is **+4.27 bp** against v27's
six-instrument +3.61.

## 2. The regression

Fade at 09:45, in sigma units, on the pack's share of the move (C) and
the instrument's own (E):

```
sample                    n       bC      t       bE      t    bE-bC      t
S1 CPI + payrolls      1868   +0.103  +0.87   +0.080  +1.02   -0.023  -0.21  FAIL
S2 claims              3052   +0.401  +1.38   +0.270  +1.38   -0.131  -1.03  FAIL
S3 control            13456   -0.070  -0.53   -0.150  -1.12   -0.080  -1.48
```

**Neither component predicts the reversion**, and they do not differ.
G1 and G2 both fail, and G3 reads *nowhere*: the decomposition does not
describe the release fade on release mornings, on claims, or on ordinary
mornings.

**My registered prediction was that bE > 0 and bC ~ 0.** It is wrong.
I said it out loud to Dave before running it, which is the only reason
it costs nothing: it was written down first.

## 3. What the failure tells us anyway

The reversion does not scale with the move **at all**:

```
raw, S1:   fade = +2.59 bp  +  0.057 x |move|      t on the slope +1.14
           mean |move| 29.5 bp, mean fade +4.27 bp
```

Most of the fade is the constant. This is the second independent
confirmation of the v22 quintile result, by a different method on a
different window. **The release fade is a roughly fixed-size bounce, not
a proportional retracement** — how far the price went tells you almost
nothing about how much comes back.

That is an awkward fact for every story anyone has told about it,
including mine. An overshoot corrects in proportion. An absorption cost
scales with what had to be absorbed. A constant does neither.

## 4. The descriptive table points the other way, and it is not evidence

Registered as reported-only, the thirds by idiosyncratic share:

```
                       low third   middle   high third   high - low
S1 CPI + payrolls          +6.06    +5.65        +1.10        -4.96
S2 claims                  +0.91    +1.11        +0.55        -0.36
S3 control                 -0.11    -0.45        +0.48        +0.60
```

Read naively, moves that the pack **shared** reverted +6.06 bp and moves
an instrument made **alone** reverted +1.10 — the opposite of my
prediction, and pointing at the market misreading the data rather than
at absorption.

Post-hoc arithmetic on that gap, because a number without an error bar
invites over-reading: **-4.96 bp +/- 2.61, t = -1.90** on the sample
that is already spent, and **-0.36 +/- 2.10, t = -0.17** on the
independent one. That is the exact shape this project has been fooled by
twice: a suggestive gap on the discovery sample and nothing where it
would have to replicate. **It is not evidence, and no rule follows from
it.**

## 5. How strong a null this is

The contrast's standard error is 0.111 sigma units, so the smallest
mechanism G1 could have caught is about **0.25 sigma — roughly 10 bp of
extra reversion for a component one sigma larger**, on a mean sigma of
40.4 bp against a mean fade of +4.27 bp. That is more than twice the
whole effect. This is "a strong version of absorption is not there", not
"nothing subtle is there".

> **CORRECTION, 2026-09-25.** This section first said 4.9 bp. The check
> script that produced it reused the CONTROL sample's standard error
> (0.054) instead of S1's (0.111). The corrected figure is 10 bp, which
> makes the null weaker than first written, not stronger. The regression,
> the gates and every other number in this document are unaffected.

## 6. Where the mechanism hunt now stands

```
overshoot-and-correct      dead   no scaling with move size (v22, again here)
noise-plus-selection       dead   held-out decade reproduced it (v23)
the 09:30 open corrects    dead   gold and EUR_USD show it too (v24)
risk premium               dead   it stops overnight (v27)
absorption vs information  dead   this run
```

What survives is a description, not an explanation: **a scheduled
release moves six markets; over the next hour a roughly constant amount
comes back, on release mornings only, with no dependence on how far the
price moved; it is finished by the close and gone by the next day.**

## 7. What is left to feed it

Every test so far has used price and a calendar. Two inputs have never
been used at all, and they are the only ones that can speak to
direction:

1. **Participation.** The tick-volume column in the same files, never
   analysed. A fixed-size bounce that does not scale with the move might
   scale with how many participants showed up. Free, on disk, and a
   sharp prediction either way. (The spread split was already run once,
   in RESULT_PREMARKET section 5, and pointed AGAINST the crude
   liquidity story: the effect was slightly stronger where spreads were
   tightest.)
2. **The release's content.** Headline against internals, and a surprise
   measure. Actuals and revisions are free from BLS and ALFRED, which
   `event_table.py` already talks to; a real consensus costs money; a
   rate instrument's 08:30 move is a free market-based stand-in for the
   surprise.

Both are registrations of their own. Neither changes rule A, and v25
keeps running it.

---

**Investigation forty-four.** Four explanations tried, four dead, and
the effect still there.

---

**Inputs as run, and the standing caveats: PROVENANCE.md**
