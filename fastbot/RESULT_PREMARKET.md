# RESULT — does volatility whose cause is KNOWN carry a sign?

```
RUN:      2026-09-12
SPEC:     PREREGISTRATION_v22, frozen before any forward return touched
          a pre-market bar
CODE:     premarket_event.py 1.0
SAMPLE:   SPX500_USD M15, the 08:30 ET bar, 3,523 days 2013-2026
          981 scheduled releases, 2,449 controls, 733 placebos
VERDICT:  Yes -- and the sign is the opposite of the one registered.
          Releases REVERT. The reversion is real, survives execution
          prices, and is worth 1.68 bp against a 1.77 bp spread.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The one number

Fade the release-bar move at 08:45 ET, close at 09:45, 981 times over
thirteen years, paying the spread you would actually be given — sell the
bid, buy back the ask:

```
                n    gross bp     t      NET of spread      t
  release     981      +1.68   +1.76          -0.10      -0.10
  control   2,449      -0.75   -1.40          -2.51      -4.71

  cost actually paid   1.77 bp per round trip
```

**Gross edge 1.68 bp. Cost 1.77 bp. Net −0.10 bp, t = −0.10.**

> **CORRECTION, 2026-09-13.** The short leg divided its P&L by the exit
> price rather than the entry price — `Pe/Px − 1` where `(Pe − Px)/Pe`
> was meant. Caught by a planted test in `premarket_instruments.py`:
> with bid equal to ask the cost must be exactly zero, and the wrong
> form leaves a residue. Corrected, this row reads **net −0.15 bp and
> cost 1.83 bp**. The conclusion is unchanged and the error ran
> **against** the strategy, not for it — every `1.77` elsewhere in the
> project understates cost by about 0.06 bp, so every net figure quoted
> is that much too kind. v24 measures cost per instrument with the
> corrected formula.

That is not "close to zero" in the sense of being noisy. On 981
observations it is zero to within a tenth of a basis point, and the
reason it is zero is visible in the same line: **the edge and the spread
are the same number.**

## 2. The event table is now validated against a price

Gate A was the positive control and it carried a second job: **1,003
release timestamps built from ALFRED and federalreserve.gov, never once
checked against market data.**

```
                |move|      range      median volume
  release     15.47 bp    29.10 bp          923
  control      7.06 bp    13.42 bp          313
  diff        +8.41 bp                   t = 10.0     [PASS]
```

Release bars move **2.2× further** and carry **3× the activity** of the
same minute on a non-release day. If the times had been wrong — the
wrong rid, the wrong hour, minutes drifting — this is where it would
have shown. **It didn't.** `events_v2.csv` is an instrument, not a list.

That is worth more than this run's hypothesis, and it is reusable.

## 3. The gates

```
[PASS] Gate A  release |move| +8.41 bp, t = 10.0       positive control
[FAIL] Gate B  release bars -1.68 bp, t = -1.76        continuation?
[FAIL] Gate C  release minus control -2.43 bp, t = -2.22   <- HYPOTHESIS
[PASS] Gate D  placebo (day before) +0.22 bp, t = 0.20
[FAIL] Gate E  2.43 bp vs 2x the 1.76 bp spread = 3.51
[FAIL] Gate F  eras -0.82  -1.27  -5.17
[FAIL] Gate G  H=4 minus H=1, paired -1.83 bp, t = -2.15   <- MECHANISM
```

**Gate C fails by being significant in the wrong direction.** v22 §4
defined it as continuation at t ≥ +2.0; the measurement is t = −2.22.
The hypothesis is not merely unsupported, it is inverted.

**Gate D passing is what makes the rest readable.** The same slot on the
day before a release shows +0.22 bp at t = 0.20 — nothing. So this is
not a property of 08:30 in general. It is tied to the release.

**Gate F "fails" in an interesting way.** It asks for a positive effect
in all three eras. All three are negative, consistently, and growing:
−0.82, −1.27, −5.17. That is a stable phenomenon pointing the other way,
not an unstable one.

## 4. Where the reversion actually lives

The three pre-specified horizons localise it exactly:

```
  H= 1   08:45 -> 09:00 ET, still pre-market   diff  +0.04 bp   t +0.09
  H= 4   08:45 -> 09:45 ET, crossing the open  diff  -2.43 bp   t -2.22
  H=12   08:45 -> 11:45 ET, well into RTH      diff  -1.71 bp   t -0.79
```

**Inside pre-market, nothing happens.** The reversion appears precisely
when the 09:30 open is crossed, and then partly fades again.

v22 §4 registered Gate G as the mechanism and predicted the opposite:
that a thin pre-market would reprice *incompletely* and the move would
**finish** at the open. It does not finish at the open. **It is partly
taken back at the open.**

> **CORRECTION, added 2026-09-12 after STRATEGY_PREMARKET_FADE §4.**
> This section originally went further and explained the reversion as a
> thin venue *overshooting*. That story predicts the reversion should
> grow with the size of the move, and it does not — split by release-bar
> move, the five quintiles run +1.16, +2.37, −0.45, +4.66, +0.66, with
> the largest moves showing nothing. The overshoot explanation is
> **disconfirmed on the data that produced it** and should not be
> carried forward. What is measured is the reversion and its timing;
> the reason for it is not established.

## 5. It is not a quote artifact

The obvious objection: a big move in a thin venue leaves the mid
mis-marked at the bar close, entry at the next mid open is a price
nobody could deal at, and reversion follows mechanically. If that were
it, the effect would live in the wide-spread bars.

```
  tight half   n=495   median spread 0.95 bp   gross +1.94 bp   t +1.40
  wide  half   n=486   median spread 2.42 bp   gross +1.41 bp   t +1.08
```

**It is slightly stronger where the spread is tightest.** The reversion
is a real feature of the price series. It is simply the size of the
spread.

*(§5 is a post-registration diagnostic, not in v22. It is reported
because it can only weaken the finding — Gate E had already failed — and
it decides whether the follow-up in §9 is worth writing.)*

## 6. The v21 cell replicates exactly

The FOMC 14:00 stratum is v21's original event cell, recomputed by a
different script:

```
  v21  n=108   cont +1.19 bp   t +0.20
  v22  n=107   cont +1.17 bp   t +0.20
```

Independent reimplementation, same answer to two decimal places. The
one-event discrepancy is a bar-availability filter. **This is the check
that says the machinery agrees with itself**, and it is the reason the
new numbers can be trusted.

## 7. My predictions, scored

| | registered | measured | |
|---|---|---|---|
| Gate A | pass overwhelmingly | t = 10.0 | **held** |
| Gate B | fail, −1 to +2 bp | −1.68 bp | **held, and inside the range** |
| Gate C | fail, \|diff\| < 2 bp | **−2.43 bp, t −2.22** | **missed — bigger, and significant the other way** |
| Gate D | pass | pass | **held** |
| Gate E | winnable if C passes | 69% of cost | **held** |
| Gate G | the live one, ~1 in 4 | **wrong sign**, t −2.15 | **missed, inverted** |
| CLAIMS | "the one to watch" | the deadest of the three | **missed** |

**The claims prior was wrong for a reason I should have seen before
registering it.** The argument was that nobody trades claims, so an
un-arbitraged effect would survive there. But the breakdown shows why
that cannot work:

```
  CLAIMS  n=696   |move| 10.87 bp   cont -0.59   vs control -1.34  t -1.08
  CPI     n=169   |move| 27.73 bp   cont -2.18   vs control -2.93  t -1.40
  NFP     n=162   |move| 25.99 bp   cont -4.55   vs control -5.31  t -2.02
```

**Claims barely moves the tape** — 10.87 bp against CPI's 27.73. Nobody
trades it because there is nothing in it. "Uncrowded" and "nothing there"
are the same observation from two sides, and I registered the flattering
reading. The effect scales with the size of the release, which is the
opposite of the crowding story.

Three held, three missed, two of them sign errors. **That is now the
project's most reproducible result: my directional priors are wrong at
roughly the rate of a coin flip** — v19's Gate B, v21's Gates B and C,
v22's C and G. The gates keep being worth more than the predictions.

## 8. What this settles

**The hypothesis, as asked, is answered and inverted.** Volatility whose
cause is known does carry a sign at 15 minutes on SPX500_USD. The sign
is reversion, not continuation, it arrives with the RTH open rather than
before it, and it is 1.68 bp gross against a 1.77 bp round trip.

**And the arithmetic is not a coincidence.** A predictable move that
could be harvested by crossing a spread of *s* gets competed down until
it is worth about *s* — that is where a dealer sets the spread, and the
residual is what pays for quoting it. So "the edge equals the spread" is
not this candidate being unlucky. It is what equilibrium looks like from
the outside.

This project's oldest finding, now with a number attached: **nothing
died of absence, everything died of access. Seven for seven.**

**It also weakens v21 retrospectively**, as v22 §2 registered in
advance. v21 read `corr(spread, range) = +0.001` as "the liquidity axis
is orthogonal to the volatility axis". The precondition check for this
run found OANDA's spread is **1.67 bp pre-market against 1.63 bp at
midday — flat across the whole 24-hour day**, while activity varies
4-fold. A spread that barely moves correlates with nothing by
construction. v21's null stands; the *reason* it gave for being able to
decompose was better than the instrument deserved.

## 9. What is left

**Not a tuned version of this.** Moving the horizon, the slot or the
stratum until something clears 1.77 bp is the definition of the thing
this project exists not to do.

The one genuinely open question is whether **1.77 bp is Dave's cost or
OANDA's choice.** The whole result rests on a retail CFD spread. The
same reversion measured against CME e-mini futures — where the round
trip is roughly a quarter of a tick plus commission — is a different
arithmetic problem with the same numerator. **That is a data-access
question, not a research question, and it is the honest next step.**

---

**Investigation thirty-eight.** The first to validate the event table
against a price, the first to replicate a prior cell exactly, and the
first where the gross edge and the cost of taking it agreed to within a
tenth of a basis point.
