# ARM G — the informed run. Result.

```
GATED:   2026-11-07, on the same engine, same measured costs, same gates
         as the six blind arms. No special-casing.
VERDICT: cleared 3 of 7, and fires FIVE of its own six abandon conditions.
```

## All three registered predictions resolved

| | registered 2026-11-06 | outcome |
|---|---|---|
| 1 Avoidance | proposes nothing from the closed list | **PASSED** |
| 2 Holding period | holds days not weeks, cites financing | **PASSED** |
| 3 Gates | does NOT clear all seven | **CONFIRMED — 3 of 7** |

It put its own odds of clearing all seven at 8-10%. It cleared three.

## The scoreboard entry

| | |
|---|---|
| trades | 1,589 across 21 markets, 917 long / 672 short |
| **gross per trade** | **−0.0012%** |
| cost per trade | 0.155% |
| net per trade | −0.156% |
| median hold | 5 nights |
| sized at 0.25%/σ | 10,000 → 8,318, CAGR −0.9%, daily max DD 24.5% |

```
  [FAIL] 1 sign consistency   E1 +0.011%  E2 −0.329%  E3 −0.125%
  [FAIL] 2 breadth            7 of 21
  [FAIL] 3 effect size        −0.156% against +0.2%
  [PASS] 4 sample             1,589
  [FAIL] 5 robustness         not applicable, base edge not positive
  [PASS] 6 matched control    +0.123%, 97% coverage
  [PASS] 7 daily risk         24.5% measured vs 20% designed for
```

## The headline: the best-informed arm found no edge at all

Every one of the six blind arms found a **positive gross edge** and lost it
to costs. ARM G, given 184 pre-registrations, 162 results and our own gate
output, produced a strategy with **essentially zero gross edge before a
single basis point of cost** — −0.0012% per trade.

Accumulated negative knowledge steered it away from every trap that sank
the others. It did not steer it toward an edge. That is the answer to the
question the run was built to ask, and ARM G gave it before the run:

> "Mostly better informed, and only slightly better... Ruling out places to
> look doesn't create an edge in what's left."

## The subtle part — gate 6 passes while the strategy loses money

ARM G **cleared the matched control at +0.123%** with 97% coverage. The
gate that killed most of episodes 1 to 3, and which only ARM F had
previously passed.

And its net is −0.156%.

Both are true because they measure different things. The control is a
matched hold from a bar with the same era, prior return and volatility —
i.e. from a bar that has also just taken a 2σ shock against its trend.
**That state is unprofitable for everyone.** ARM G loses less than the
matched alternative while still losing.

So gate 6 answers "is this better than an equivalent hold", not "does this
make money". Gate 3 answers the second. **An arm can pass one and fail the
other, and this is the first to demonstrate it.** That is a point in favour
of the gate set, not against it.

## Its own kill conditions — five of six fired

It wrote these before the run and named no escape clause.

```
K1  any gate fails                FIRED   four of seven failed
K2  it is ARM F relabelled        FIRED   ex-index net −0.208%, needed
                                          > +0.10%; 5 of 18 markets
                                          positive, needed 11
K3  short side negative, 2+ eras  FIRED   E2 −0.393%, E3 −0.293%
K4  era 3 below a third of era 1  FIRED   E1 +0.011%, E3 −0.125%
K5  ex-crisis turns negative      FIRED   −0.144% on 1,486 trades
K6  first 150 forward trades <= 0  not yet testable
```

K2 is the most informative. ARM G's whole claim was that ARM F's index
dip-buy is a special case of a cross-asset liquidity premium. **Strip the
three indices and the remaining eighteen markets lose 0.21% per trade with
five of eighteen positive.** There is no cross-asset premium here. ARM F's
effect is an index effect, and ARM G's own test is what established that —
a genuinely useful negative result, and one no blind arm could have
produced because none of them knew to ask.

K5 matters too: removing the 2008 and 2020 crises leaves it at −0.144%, so
this is not an edge that merely needs tail events. It does not work in the
tails either.

## What the informed run was worth

It did not find a tradeable strategy. It did three other things:

1. **It proved the briefing changes behaviour.** Five of six blind arms
   proposed trend following; ARM G ruled it out by name, citing the arms
   that failed, and held for four days because it had read the financing
   finding.
2. **It closed a question about ARM F.** The index dip-buy does not
   generalise. We now know that, pre-registered, rather than assuming it.
3. **It found a defect in our own cost model** — the Brent roll — that six
   blind arms, three gate runs and I had all missed. See
   `ARM_G_SCORED.md`.

## Does inherited search count as search?

Partially, and the evidence here is against the strong form. If inherited
search behaved like own search, ARM G should have shown an inflated
in-sample result that decays forward, as ARM F's did across its three
rounds. Instead it showed **no in-sample edge at all** — which is what you
would expect if the prior work genuinely removed the overfitted places to
look rather than handing over a fitted answer.

One run is not an answer to that question. But the direction is the
opposite of the pessimistic prediction, and it is worth stating plainly:
the 185th look at this dataset produced the most honest result in the
study, not the most flattering one.
