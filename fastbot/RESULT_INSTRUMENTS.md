# RESULT — does the 30-minute signal bar survive new instruments?

```
RUN:      2026-09-18
SPEC:     PREREGISTRATION_v24, amended by v24.1 (Gate A only)
CODE:     premarket_instruments.py 1.1
DATA:     5 instruments, M15 bid and ask, 2005/2006 - 2026, pulled fresh
          2,626 CPI and payrolls events, verified clean by verify_pull.py
VERDICT:  No. C - A is -0.09 bp at t = -0.12 on 2,626 events. The
          30-minute signal bar was one standard error on the sample that
          chose it, and there is nothing left of it.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The answer

```
[PASS] Gate A (v24.1)  all five instruments, t = 10.5 to 15.6
[FAIL] Gate B  C - A pooled over all  -0.09 bp, t = -0.12   n = 2,626
[FAIL] Gate C  C - A near-clones      +0.52 bp, t = +0.40   n = 1,054
```

**Registered prediction, v24 §6: "pooled C − A between −1 and +1.5 bp at
t < 2.0."** Measured −0.09 bp at t = −0.12. Dead centre.

Per instrument:

```
                 n   A gross      t   C gross      t     C-A      t    cost
NAS100_USD     525    +6.97  +4.02     +7.97  +3.42   +1.00  +0.49    1.21
US30_USD       529    +1.17  +0.87     +1.20  +0.73   +0.04  +0.02    0.78
EUR_USD        540    +1.54  +1.60     +1.36  +1.51   -0.19  -0.18    1.50
XAU_USD        501    +4.29  +1.99     +2.44  +1.20   -1.86  -1.04    3.77
DE30_EUR       531    +2.52  +1.61     +2.98  +1.61   +0.47  +0.24    0.92
```

**Not one instrument shows the improvement at even t = 0.5.** On
SPX500_USD it was +2.69 bp; here the largest is +1.00 and two are
negative.

## 2. Gate F is the shape of the thing

```
NAS100_USD   2005-2015  +5.36    2015-2026  -3.34    FLIPS
US30_USD     2005-2015  -0.55    2015-2026  +0.62    FLIPS
EUR_USD      2005-2015  +0.44    2015-2026  -0.81    FLIPS
XAU_USD      2006-2016  -0.84    2016-2026  -2.87
DE30_EUR     2005-2015  +2.09    2015-2026  -1.15    FLIPS
```

**Four of five flip sign between halves**, and NAS100 — the only one with
a visible C − A — swings from +5.36 to −3.34. That is not a weak effect.
It is a quantity with no sign, sampled twice.

## 3. The amendment never had to fire

v24.1 §3 restricted the amendment to licensing a **null only**, and put
the restriction in the code: a Gate B or Gate C pass would print THE VOID
STANDS and exit 4.

**Both failed.** The amendment permitted exactly what it was allowed to
permit, and the safeguard was never load-bearing. That is the outcome it
was designed for, and it is worth saying plainly that had Gate C passed,
this document would not exist — there would be a void and a request for
more data.

The amended Gate A, meanwhile, did the job the original could not:

```
                release |move|   control   ratio       t
NAS100_USD           32.25        9.71    3.32x     12.2
US30_USD             25.12        7.80    3.22x     12.9
EUR_USD              20.85        6.70    3.11x     15.6
XAU_USD              36.22       13.45    2.69x     13.8
DE30_EUR             26.33       11.59    2.27x     10.5
```

**The event table lands on bars that move, on five instruments never
tested against it.** The original Gate A is reported beside it: US30 at
t = 0.87 still does not clear the old t ≥ 2.0 bar. It never should have
been asked to.

## 4. What did NOT die — reported, and not gated

The per-instrument table shows variant A, the base release fade,
**positive on all five**, and on four of them by more than its own cost:

```
SPX500_USD  +3.93 (t 2.77)    the origin
NAS100_USD  +6.97 (t 4.02)
XAU_USD     +4.29 (t 1.99)
DE30_EUR    +2.52 (t 1.61)
EUR_USD     +1.54 (t 1.60)
US30_USD    +1.17 (t 0.87)
```

Six instruments, six positive. **This is reported output, not a gate.**
v24 gated the *difference*, and no threshold was set for this in advance,
so it cannot be claimed as a confirmation of anything.

And it is much weaker evidence than six numbers suggest. **All six react
to the same ~550 US releases on the same mornings.** They are six
readings of one market's response to one calendar, not six experiments.
The effective number of independent observations is closer to one
instrument's worth.

## 5. The mechanism test contradicts RESULT_PREMARKET §4

v24 §3 registered EUR_USD and XAU_USD as a discriminator: they have no
09:30 equity open, so a base effect there favours **information
absorption**, and its absence favours **the open doing the correcting.**

```
EUR_USD   +1.54 bp  t +1.60        no equity open
XAU_USD   +4.29 bp  t +1.99        no equity open
```

**Both positive, gold at t = 1.99.** That points at absorption, and it
sits badly with RESULT_PREMARKET §4, which localised the SPX reversion to
the crossing of the 09:30 open — nothing at H=1, −2.43 bp at H=4.

Not decisive: the NYSE open moves FX and gold too, through the dollar and
the US session, so these are not clean controls. But the registered
prediction in v24 §6 was "present but weaker in FX and gold," and gold
came in **stronger** than SPX500. Half right, and the wrong half is the
one that mattered.

**Third mechanism story to fail in this line**: overshoot-and-correct
(v22, killed by the quintile test), noise-plus-selection (v23, killed by
held-out data), and now the equity-open localisation. The effect keeps
surviving; every explanation for it does not.

## 6. Gate E passed and should be ignored

```
[PASS] Gate E  variant C net on the near-clones +3.58 bp
```

It tests variant C's level — and variant C just failed to beat variant A,
so its level is not a finding about anything this run asked. Worse,
`verify_pull.py` found **bid equal to ask for all of 2005-2011 on
NAS100_USD, US30_USD and DE30_EUR** — seven years with no spread at all,
which makes every cost figure for those instruments understated and
Gate E's margin softer than it looks.

v24.1 §5 named this and deliberately did **not** trim the sample to
2012+, because that would be changing the spec after seeing the data.

## 7. Where this leaves the line

**Settled:** the 30-minute signal bar is dead. It was +0.20 Sharpe
against a ±0.21 standard error, it came from picking the best of four
variants, and on 2,626 fresh events it is worth −0.09 bp.

**Not settled, and now harder to dismiss:** the base release fade is
positive on six instruments and 23 years. But it is the same calendar
every time, its best net was +2.02 bp at t = 1.53, its Sharpe was 0.32,
and no surviving explanation says why it happens.

**The honest next step is not another variant.** Every refinement tried
so far — longer hold, longer signal, per-release selection — has been
worth about one standard error and has died on contact with new data.
What has never been done is a **forward test**: register the plain rule
now, take it as it comes, ~24 events a year, no looking. That is slow and
it is the only sample left that nobody has seen.

---

**Investigation forty.** The first run in this project voided by a gate I
set badly rather than by the market, and the first where the correction
had to be written with a restriction that made a positive result
worthless in advance.
