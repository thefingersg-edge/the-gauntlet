# RESULT — does the payrolls reversion reproduce out of sample?

```
RUN:      2026-09-12
SPEC:     PREREGISTRATION_v23, frozen before any pre-2013 pre-market bar
CODE:     premarket_confirm.py 1.0
SAMPLE:   SPX500_USD, the 08:30 ET bar, 2003-2012
          117 payrolls, 113 CPI, 1,846 controls -- never previously used
VERDICT:  Gate B fails on significance, not on sign. And my registered
          prediction was wrong, which matters more than the gate.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The gates

```
[PASS] Gate A  payrolls |move| 41.01 bp vs control 10.38, t = 9.6
[FAIL] Gate B  +3.23 bp vs the +2.0 bp bar, t = 0.95      <- THE CONFIRMATION
[PASS] Gate C  2003-2007 +3.99 (n=57)   2008-2012 +2.50 (n=60)
```

**Gate A also cleared the data's own viability.** The pre-2012 series is
mid-only and back-filled, and the worry was that it might not respond to
news at all. It responds at four times the control, t = 9.6.

**Gate B fails on the t-statistic while clearing the effect size.**
+3.23 bp against a +2.0 bp bar, but t = 0.95 on 117 events. The point
estimate is 0.71× the modern one; the sample cannot tell it from zero.

## 2. I predicted this wrong

v23 §5, registered before the run: *"I expect the payrolls gross figure
to land between −2 and +2 bp with an unstable sign across the two
halves."*

It landed at **+3.23 bp with the same sign in both halves.** Wrong on
the range and wrong on the stability. The reasoning behind that
prediction — the selection-signature argument in STRATEGY §3 — does not
survive contact with the held-out data, and §4 below explains why the
argument was flawed to begin with.

## 3. Everything measured, in one grid

```
  gross bp from fading, H=4, mid prices

              2003-2007        2008-2012        2013-2026
  NFP       +3.99 t+1.49     +2.50 t+0.41     +4.55 t+1.77
  CPI       -1.34 t-0.43    +12.11 t+2.74     +2.18 t+1.08
  CLAIMS            --       +4.53 t+1.85     +0.59 t+0.53
```

**Seven of eight populated cells are positive. Payrolls is positive in
all three periods**, spanning 23 years and two entirely different
volatility regimes. Not one cell individually reaches t = 2 except CPI
in the crisis window, which is also where 08:30 bars moved a median
50 bp and is the cell least worth trusting.

**Post-registration synthesis** — pooling the discovery sample with its
confirmation, and pooling the two major releases. Not a registered
statistic, and reported as arithmetic rather than as a result:

```
  CPI + payrolls, 561 events, 24/yr over 23.4 years
    gross                              +3.79 bp    t = +2.88
    net of the 1.77 bp round trip      +2.02 bp    t = +1.53
                                       = +48 bp per year
    Sharpe  +0.32 +/- 0.21        years to 2 SE: 39
```

**The gross effect is significant over 23 years. What survives the
spread is not.** Those two sentences are the whole result.

## 4. Correction — the selection argument in STRATEGY §3 was wrong

STRATEGY §3 argued the payrolls line was the maximum of four noise
draws, on this evidence:

```
  NFP     Sharpe +0.29  =  +1.07 SE        expected |max| of 4 draws: 1.03
  CLAIMS  Sharpe -0.29  =  -1.07 SE
```

**Those Sharpes are net of cost, and that is what manufactured the
symmetry.** Subtracting a fixed 1.77 bp from strata with different gross
edges pushes the small one below zero and leaves the large one above it.
The grid above shows what is actually there:

```
  gross edge   CLAIMS +0.59    CPI +2.18    NFP +4.55     none negative
```

**Claims was never negative.** It has a small gross edge that the spread
eats. That is not a null cut four ways — it is one effect of varying
size with a constant cost subtracted, and I read the cost as the signal.

Second walk-back in two documents: RESULT_PREMARKET §8's overshoot
mechanism was disconfirmed by its own quintile test, and now STRATEGY
§3's selection argument is disconfirmed by held-out data. **Both were
arguments I found persuasive when I wrote them.**

## 5. What this does and does not establish

**Establishes:** a bar containing a major scheduled release partly
reverses over the following hour, on SPX500_USD, across 23 years, 561
events and three disjoint periods, gross of costs, at t = 2.88. It is
not a quote artifact (RESULT_PREMARKET §5), not a property of the 08:30
slot (Gate D there), and the effect arrives with the RTH open rather
than before it.

**Does not establish:** that it can be collected. Net of the spread
actually paid it is +2.02 bp per trade at t = 1.53 — the direction this
project has seen six times and now sees a seventh, except that this
time something is left over rather than nothing.

**Does not establish a mechanism.** Two candidate explanations have now
failed: overshoot-and-correct (no scaling with move size) and
noise-plus-selection (reproduced out of sample). I do not know why this
happens.

## 6. Why Sharpe 0.32 is the end of it, and leverage does not help

48 bp a year is not the objection — the objection is 0.32 ± 0.21.

**Leverage multiplies return and risk together and leaves the Sharpe
exactly where it was.** A 0.32 Sharpe run at whatever size makes the
return interesting produces drawdowns several times the annual return,
and the error bar admits a true value of 0.11 as readily as 0.53.

The two things that could raise it are both bounded:

- **Lower cost.** Break-even is 3.79 bp; SPX500_USD costs 1.77. A
  venue at half that lifts net to roughly +2.9 bp and the Sharpe to
  about 0.45.
- **More events.** The same rule on other index instruments adds
  observations, but they are all equity indices reacting to the same US
  release, so the diversification is far less than independent — call
  it 0.45 as a ceiling too.

**Neither route reaches a Sharpe worth trading, and both are knowable in
advance**, which is why the honest thing is to stop here rather than
fetch more data to arrive at 0.45.

---

**Investigation thirty-nine.** The project's first confirmation run, the
first candidate whose gross edge exceeds its cost, and the first time
held-out data has told me my own null argument was wrong.
