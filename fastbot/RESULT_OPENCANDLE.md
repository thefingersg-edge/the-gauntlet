# RESULT — the opening "liquidity candle"

```
RUN:      2026-09-11
SPEC:     PREREGISTRATION_v17, frozen before any forward return
CODE:     liquidity_candle.py 1.0
SAMPLE:   SPX500_USD M15, 5,842 RTH sessions, 139,562 bar-observations,
          2003-03-21 to 2026-08-28
VERDICT:  FAIL on all five gates. The rule's own trigger produces a
          mean reversal of -0.00 bp.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The rule as stated, measured directly

```
fires on 54.8% of openings   (3,118 of 5,687)
fired      -0.00 bp reversal
did not    -0.57 bp
difference +0.57 bp          t = 0.53
```

**The candles that trigger the rule average exactly zero.** Not a small
edge, not an edge eaten by costs — zero, on 3,118 triggers across 23
years.

## 2. Why the threshold was never selecting anything

Found before any return was computed, from frequency alone:

```
ET       median range/ATR14    fires at >=25%
09:30         0.260                54.0%
10:30         0.199                29.4%
12:00         0.136                12.4%
15:45         0.201                31.3%
```

**The 09:30 bar's median range is 0.260 of ATR14 and the rule's cut is
0.25.** The threshold sits on the median of the thing it selects, so it
passes more than half of all openings. A filter that admits the typical
case is not identifying a liquidity event.

And because opening bars are roughly twice the size of midday bars, a
fixed threshold across the day mostly just selects **the open**. "A big
candle at the open" and "the open" are nearly the same statement, which
is why v17 tested them apart.

## 3. The grid

Bars bucketed by time of day, and within each slot by size quartile
computed among bars at that same slot. Reversal measured from the **mid
open of the next bar** to the mid close four bars later — the signal
bar's own close is never the entry price.

```
slot       Q1 small       Q2       Q3    Q4 big    Q4-Q1      t
09:30        -0.40     -0.57     -0.89     +0.82    +1.22    0.78
10:00        -0.52     -0.36     +1.35     -0.11    +0.41    0.30
midday       +0.15     -0.21     +0.50     -0.17    -0.32   -0.97
15:45        -0.44     +0.30     -0.78     -2.92    -2.48   -2.86
```

```
[FAIL] Gate A  09:30 Q4 mean +0.82 bp, t = 0.66  (n=1422)
[FAIL] Gate B  open minus midday +0.99 bp, t = 0.77
[FAIL] Gate C  big minus small at 09:30 +1.22 bp, t = 0.78
[FAIL] Gate D  eras +0.81  -3.10  +5.52
[FAIL] Gate E  +1.22 bp against a 1.8 bp cost bar

    FAIL
```

Gate D is the most telling of the five: split into three disjoint eras
the difference goes **+0.81, −3.10, +5.52**. It changes sign. That is
what noise looks like.

## 4. Two numbers that would become a strategy if I let them

**The 15:45 cell reads −2.92 bp with t = −2.86.** It is the only
notable cell in the table — and it is *continuation*, the opposite of
the claim, at the close rather than the open. It also does not survive
its own multiplicity: sixteen cells were examined, t = 2.86 is p ≈
0.0042, and Bonferroni over sixteen requires 0.0031. **It fails.**
Reporting it as a finding would be exactly the error v17 §5 was written
to prevent, so it is reported as what it is: the largest of sixteen
draws.

**H = 1 bar reads +1.85 bp with t = 2.14.** Tempting, and wrong on three
counts. It is one of two pre-specified robustness horizons, not the
primary. It is below the 1.8 bp round-trip cost. And the decay is the
giveaway:

```
H =  1 bar    +1.85   t 2.14
H =  4 bars   +1.22   t 0.78     <- the pre-registered primary
H = 12 bars   +0.60   t 0.27
```

**An effect that shrinks monotonically toward zero as the horizon
lengthens is microstructure, not information.** A real reversal would
persist for at least as long as it takes to trade it.

## 5. Dave's fourth question, and why the answer is "not yet"

*Where the pattern was correct, did prior trends differ from where it
failed?*

v17 §5 gated that search on Gate A passing, and Gate A failed, so **it
did not run.** That was not caution after the fact — the gate was
written before any return existed, precisely because this is the most
reliable way to manufacture a signal. Ten features at α = 0.05 yield one
false positive by chance; splitting a sample **by its own outcome** and
then hunting for what separates the halves will always find something.

But the honest version of the objection deserves saying: **a zero
unconditional mean can hide +X in half the sample and −X in the other**,
and conditioning could in principle find that. That is a real question
and it is not answered here. What it needs is its own pre-registration
with the structure v17 §5 already specifies — ten enumerated features,
Holm correction, **discovery on 2003-2014 and confirmation on
2015-2026**, with only the holdout reported. That can genuinely fail,
which is what makes it worth running.

What cannot be done is to run it now, having seen Gate A fail, and treat
whatever emerges as a discovery.

## 6. On wedges

Not tested here, and worth being straight about why it is a harder
problem rather than a similar one.

**A wedge detector carries six to eight free parameters** — lookback,
number of touches, convergence ratio, tolerance, minimum duration,
breakout definition — and there is no canonical definition to appeal to.
That has two consequences. A null result is always deniable ("that was
not a proper wedge"), and a positive result is very likely a fit to
whichever parameter set was tried last.

It is testable, but only if the definition is frozen in code **with no
tunable parameter left** before any outcome is measured, and the answer
accepted whatever it is. That is a separate pre-registration, and the
same two-part structure applies: does the pattern predict, and does
prior context change that.

## 7. What this does and does not settle

**It settles the premise.** A large opening 15m candle does not predict
reversal on the S&P 500, on 5,687 openings over 23 years, at any of
three horizons, in any era, at any size quartile. The rule built on that
premise cannot work for the reason given, whatever its P&L on a
hand-picked chart.

**It does not test the full published rule** — confirmation patterns,
stops and targets are not modelled. But a rule whose stated mechanism
measures zero is not saved by its exit logic.

**The source could not be read.** Both video fetches returned HTTP 429
throughout, so the rule is as Dave described it. v17 §2 records the
three assumptions made (09:30-09:45 ET, prior 14 RTH daily ranges,
direction against the candle's own close-vs-open). **If the video
defines any of them differently, this run is void and gets
re-specified** — not adjusted.

---

**Investigation thirty-three.** The first pattern claim tested in this
project, and the category is now 0 for 16.
