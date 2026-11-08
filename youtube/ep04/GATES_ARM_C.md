# Arm C gate set

```
WRITTEN: 2026-10-31, before any strategy was generated.
DECIDED: remove the two gates that cannot be applied to an intraday
         strategy. Report those two quantities as numbers instead of
         gating on them. Add three gates intraday needs and daily does
         not. Publish the comparison frame.
```

## The principle

> **A gate that cannot be satisfied at a given timeframe is removed, not
> rewritten. The quantity it measured is then reported as a number rather
> than as a pass or a fail, so nothing is hidden and no threshold has been
> invented to suit the result.**

Rewriting a threshold invites the accusation that we tuned it. Removing it
and showing the raw number instead cannot be tuned, because there is no
number of ours in it.

## The two that are removed, and why

Two different reasons. The distinction matters and should be said out loud.

**BREADTH — removed because of a data limit.** The gate asks for the same
sign in 14 of 21 markets. We hold 15-minute bars for only 12 of the 21.
If the generator produces a 15-minute strategy, 14 is unreachable at any
quality. This is not a statement about intraday trading; it is a statement
about our data cupboard.

*Reported instead:* how many markets agreed in sign, out of however many
had bars at that timeframe. Raw counts, both numbers shown.

**EFFECT SIZE — removed because the quantity is not comparable.** The gate
asks 0.2% per trade after costs. That is a daily-holding-period number: on
EURUSD a round trip costs roughly 2bp, so 0.2% is about ten times cost, and
a trade held for days can clear it. A 15-minute bar's entire typical range
is 5-10bp. Applying the gate unchanged is a category error, and any
replacement threshold would be a number we chose, which is the thing we are
trying to avoid.

*Reported instead:* net edge per trade after costs, annualised net return,
and the modelled round-trip cost it was measured against. Three numbers,
stated plainly, with the caveat that per-trade edge is not comparable
across holding periods.

## The Arm C gate set

Five shared with the daily arms, three that only Arm C faces.

```
SHARED

C1  SIGN CONSISTENCY   same sign of edge in all three eras
                       Identical to the daily gate.

C2  SAMPLE             at least 200 trades, spread over at least 250
                       distinct trading days
                       The 200 floor is the daily gate unchanged. The
                       distinct-days requirement is additional and applies
                       only to Arm C: intraday generates thousands of
                       trades, so 200 stops binding, and the characteristic
                       intraday failure is a result carried by a handful of
                       extraordinary sessions.

C3  ROBUSTNESS         at least 80% of the edge survives moving every
                       parameter by half a step in both directions, with
                       time-of-day parameters included
                       The daily gate perturbs lookbacks and thresholds.
                       Session and clock parameters -- "enter after 09:45",
                       "flat by 15:30" -- are the ones most likely to have
                       been fitted, so they are perturbed too.

C4  MATCHED CONTROL    matched on era, prior return, volatility AND
                       time-of-day bucket
                       Intraday returns have strong time-of-day structure.
                       A control blind to the London/New York overlap would
                       flatter any strategy that happens to trade at a
                       particular hour.

C5  RISK RESOLUTION    drawdown at the strategy's own bar resolution, plus
                       maximum adverse excursion within each trade
                       The daily gate exists to stop a strategy reporting
                       risk at a resolution that hides it. A strategy flat
                       at every close hides everything at daily resolution,
                       so the same principle points at a finer resolution
                       here, not a coarser one.

ARM C ONLY

C6  EXECUTION REALISM  cost model fixed and published before generation:
                       per-instrument spread, fills at the NEXT bar's open,
                       no assumed limit fills, stated slippage
                       Intraday results live or die on fill assumptions. If
                       costs are chosen after seeing the strategy, we can
                       kill or save anything we like and the result means
                       nothing. Numbers on paper before the prompt is sent.

C7  NO INTRA-BAR       signals computed from closed bars only. Any rule
    LOOK-AHEAD         needing the current bar's high or low before it
                       closes is executed at the next bar, and the
                       substitution is reported on screen.
                       The commonest way an intraday backtest lies.

C8  SESSION INTEGRITY  session boundaries in an explicit IANA timezone, DST
                       handled, verified against a known calendar before
                       any result is computed
                       From our own scar tissue: we have already been bitten
                       by session-open timestamping, where a daily bar was
                       stamped 17:00 America/Chicago on the previous
                       calendar day and the error moved with DST. Intraday
                       multiplies that exposure.
```

**Pass is all eight.** Clearing six of eight is reported as six of eight.

## The comparison frame — one grid, on screen

This is the artefact that makes the whole thing legible. Arms across the
top, the union of gates down the side, four cell states.

```
                        ARM A   ARM B   ARM C   ARM D
  SIGN CONSISTENCY        o       o       o       o
  BREADTH                 o       o      [n]      o
  EFFECT SIZE             o       o      [n]      o
  SAMPLE                  o       o       o+      o
  ROBUSTNESS              o       o       o+      o
  MATCHED CONTROL         o       o       o+      o
  RISK RESOLUTION         o       o       o+      o
  EXECUTION REALISM       -       -       o       -
  NO INTRA-BAR LOOK-AHEAD -       -       o       -
  SESSION INTEGRITY       -       -       o       -
                        -----   -----   -----   -----
  GATES FACED             7       7       8       7

  o   gate applied
  o+  gate applied, with an intraday-specific addition
  [n] not applied -- number reported instead
  -   not applicable to a daily strategy
```

The line that goes with it, and it is the honest one:

> Arm C faces eight gates. Three of them the other three arms never face.
> Two it is excused from, and we show you those numbers anyway.

That sentence is the whole defence, and it is true. Arm C is not getting an
easier test. It is getting a different one, with more gates than the others
and two quantities reported rather than judged.

## Also run Arm C through the daily set, and publish it

The eight-gate result is the finding. The seven-gate daily result is
reported alongside it, labelled as the comparison we consider unfair, with
the two unsatisfiable gates marked.

This costs one extra table and removes the "you built a softer test for
your own strategy" attack entirely, because we will have run the harder
test ourselves and shown it losing. The gap between the two is also the
most interesting number in the segment.

## What this costs us, stated

Removing EFFECT SIZE leaves Arm C with no economic-significance gate. A
strategy could clear all eight with an edge of a fraction of a basis point
-- consistent, robust, honestly costed, and worthless.

We are not pretending otherwise. The per-trade edge, the annualised return
and the cost it was measured against all go on screen as numbers, so a
viewer can see a worthless edge for themselves. But it will not be marked
as a failed gate, and if Arm C passes eight of eight on a trivial edge, we
say in the narration that it passed every gate we could fairly apply and
that the edge is nonetheless too small to trade. The gates are not the
whole verdict and this is the arm where that shows.

## Unchanged from the preregistration

If Arm C's output cannot be implemented with the OHLC bars we hold -- if it
needs tick data or order-book depth -- that is reported as the result. No
substitute strategy, no widening of the data. Restating it because intraday
is where that temptation will be strongest.

---

## Amendment, 2026-11-01 — robustness versus the hypothesis

Decided after ARM C's output was received but **before any gate was run**,
and applying to all five arms, not only Arm C.

### The problem

C3 as written perturbs every parameter by half a step, time-of-day
parameters included. Arm C's strategy is "first hour of the US session
predicts the last hour". Its 15:00-16:00 entry window is not a tuned value;
it is the claim. Perturbing it does not test robustness, it tests a
different hypothesis, and it fails by construction.

Deciding per strategy, after seeing results, which parameters are sacred is
the exact move this project criticises. So the rule has to be general,
fixed now, and not ours to apply by taste.

### The rule

> **A parameter is hypothesis-defining if the generator's own stated
> economic rationale makes that specific value load-bearing. Everything
> else is a free parameter.**

The generator's rationale was written before anyone saw a result, so this
test cannot be gamed by us after the fact. It is read off the output, not
decided by us.

Worked through, on the arms in hand:

- **ARM C** — the rationale names the last hour of the US session. The
  09:00-10:00 reference window and the 15:00-16:00 entry window are
  hypothesis-defining. The 0.20 ATR threshold, the 0.30 ATR stop and the
  14-period ATR are free.
- **ARM B** — the rationale is path continuity, not a particular horizon.
  "60-day" is a window choice, not the mechanism, and the output itself
  submits L to perturbation at 50 and 70 in its own parameters table. All
  of L, W, theta, H and k are free.

### What gets run and published

Both, every time, for every arm:

```
PRIMARY     C3 exactly as preregistered -- every parameter perturbed,
            hypothesis-defining ones included
SECONDARY   C3 with hypothesis-defining parameters held fixed, free
            parameters perturbed as normal
```

Both numbers go on screen with both labels. If an arm passes one and fails
the other, that gap is reported as the result rather than resolved in
favour of whichever we prefer. No goalpost moves because nothing was
removed -- the preregistered test still runs and still counts.

This is the same pattern already committed to for Arm C's dual gate set:
when a test is arguably unfair, run it anyway and run the fair one beside
it.
