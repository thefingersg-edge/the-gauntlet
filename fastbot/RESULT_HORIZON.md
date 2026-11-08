# RESULT — 1 day and 2 days: do the bars keep going?

```
RUN:      2026-09-25
SPEC:     PREREGISTRATION_v27, frozen before any overnight mark existed
          and checked by sha256 at run time
CODE:     premarket_horizon.py 1.0
SAMPLES:  S1 CPI+payrolls 3,125 trades (DESCRIPTIVE ONLY, spent by v26.1)
          S2 claims only  4,964 trades, 2009-2026   GATED
          S3 control mornings 23,521 trades, 2005-2026   GATED
VERDICT:  G1 FAILS. The bars do not keep going. The afternoon drift is
          handed back overnight, the direction is a coin flip at one day,
          and financing finishes it.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

**Inputs, and the caveats that apply to every number here: PROVENANCE.md**
-- in particular that financing is charged at today's measured rate
applied to twenty years, and that cost before 2012 is understated
because bid equalled ask on four of the six instruments.

---

## 1. What Dave asked

> *"with the hold time can you review it at longer periods, 1 day,
> 2 days, to see if the bars went in the right direction."*

The CPI/payrolls sample was already spent for horizon questions by
v26.1, so it is reported here and **decides nothing**. The gates read
two samples that had never been used for this: weekly claims, and every
ordinary morning.

## 2. CPI and payrolls — descriptive, and it answers the question anyway

```
horizon      n   gross  positive     SD     net   net+fin   +fin x2   vs 09:45    t
09:45     3125   +3.61       54%   35.7   +2.19    +2.19     +2.19
15:45     3125   +8.11       52%   87.8   +6.39    +6.39     +6.39     +4.50  +1.83
+1 day    3125   +1.84       49%  153.8   +0.18    -1.08     -2.34     -1.77  -0.39
+2 days   3125   +2.53       50%  173.0   +0.97    -0.96     -2.90     -1.08  -0.22
```

**The afternoon drift is given back overnight.** +8.11 bp at 15:45
becomes +1.84 bp at the next day's close. It does not slow down, it
reverses: the increment over rule A's exit goes from +4.50 bp to
**-1.77 bp**.

**The direction stops being right.** 54% of trades are in the predicted
direction at 09:45, 52% at 15:45, and **49% at one day** — a coin flip.
Dave's question, answered in its own terms: the bars went the right way
for an hour, less so by the close, and not at all by the next day.

**The swings quadruple.** SD 35.7 bp at 09:45, 153.8 at one day, 173.0
at two. And the overnight horizons pay financing, which turns what is
left negative: **-1.08 bp at one day, -0.96 at two.**

Nothing here is explained by market drift: these trades are long on 44%
of mornings, the market moved +0.28 bp over the +1 day window, and drift
times that imbalance is -0.03 bp of the +1.84.

## 3. G1 — claims, the independent sample. FAIL.

```
horizon      n   gross  positive     SD     net   net+fin   vs 09:45     t
09:45     4964   +0.86       51%   32.3   -0.61    -0.61
15:45     4964   +0.92       51%   79.6   -0.56    -0.56      +0.06  +0.04
+1 day    4963   +0.80       51%  130.1   -0.90    -1.68      -0.06  -0.02
+2 days   4962   +1.63       50%  174.3   +0.03    -2.79      +0.76  +0.19
```

```
[FAIL] G1   -0.06 bp at t = -0.02, halves -1.96 / +1.83 (sign flips),
            net of financing -1.68 bp.  Every condition missed.
```

**Holding an extra day adds nothing on 4,963 independent trades.** The
halves disagree, which is what a quantity with no sign looks like
sampled twice.

The pre-specified 15:45 line matters too: **+0.06 bp at t = 0.04.** The
afternoon drift that v26.1 measured at +4.50 bp on CPI and payrolls does
not appear here at all. Claims' own release effect is four times smaller
(+0.86 against +3.61 at 09:45), so this excludes a drift the size of
S1's, not a proportionally smaller one.

## 4. G2 — the control, and a bonus the control was not asked for

```
horizon       n   gross  positive     SD     net   net+fin   vs 09:45     t
09:45     23521   +0.19       51%   30.0   -1.21    -1.21
15:45     23521   +0.09       50%   83.9   -1.43    -1.43      -0.10  -0.12
+1 day    23515   +0.59       50%  137.2   -0.96    -1.95      +0.40  +0.30
+2 days   23504   +0.02       50%  174.9   -1.57    -3.37      -0.17  -0.10
```

**G2: flat.** +0.40 bp at t = 0.30. There is no general morning drift to
borrow, so the afternoon drift on release days, whatever it is, is
release-linked rather than a market-wide pattern.

**The bonus is the first line of that table.** On 23,521 ordinary
mornings the same fade is worth **+0.19 bp**, against **+3.61 bp** on
release mornings — nineteen times smaller, on the largest control this
line has ever run. The release is doing the work. That is the cleanest
placebo the project has produced for the base effect, and it was
registered as a control rather than found afterwards.

## 5. Predictions, scored

```
G1 fails, within 3 bp of zero, t < 2        -0.06 at t -0.02      RIGHT
S1 positive to +1 day but smaller per day   +1.84 gross, but the
                                            increment REVERSED     WRONG
G2 control positive and under 3 bp          +0.40 at t +0.30      RIGHT
share positive stays 50-55% everywhere      54, 52, 49, 50        JUST WRONG
```

Two right, one wrong, one wrong at the edge. The one I got wrong is the
shape of the failure: I expected the drift to fade slowly overnight and
it does not — it hands back more than it made after 09:45.

## 6. What this settles

- **1 day and 2 days are finished.** Not by opinion: by a gate set
  beforehand on an independent sample, with the same answer showing in
  the spent sample and in the control.
- **The one-hour time exit stands.** Rule A and PREREGISTRATION_v25 are
  unchanged, and claims stays out of the strategy — it was a sample
  here, not a trade.
- **The base fade is release-specific**, +3.61 against +0.19 on 23,521
  control mornings.
- **Still open, and now narrower:** the same-day drift from 09:45 to
  15:45 on CPI and payrolls. It failed its own gate in v26.1 at t =
  1.76, its sample is spent, claims cannot resolve it, and the control
  says it is not a market-wide effect. The only clean way left to answer
  it is forward: recording the 15:45 mark alongside the 09:45 exit
  changes no rule and decides no gate, and in a few years it would
  answer the question with data nobody has seen.

---

**Investigation forty-three.** The first one in this line where a
control was run at scale, and the base effect passed it.
