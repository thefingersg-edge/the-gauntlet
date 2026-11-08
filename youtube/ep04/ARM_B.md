# Arm B — the problem, and what to do about it

```
WRITTEN: 2026-10-31, before any strategy was generated.
STATUS:  ADOPTED 2026-10-31. Arm B is open-book. A fifth arm, ARM E,
         was added at the same time as its mirror -- coached toward
         appearance rather than survival. See ARM_E.md.
```

## The problem: Arm B contradicts our own preregistration

Section 2 of PREREGISTRATION.md says the generator:

> is not told that a teardown follows, is not shown the gates in section 4

Arm B's prompt, as currently written, shows it four of them in English:

| Arm B says | Which is |
|---|---|
| "prefer rules that would still be rules if the parameters moved a little" | **Gate 5, robustness**, restated |
| "assume realistic transaction costs" | the cost model inside **gate 3** |
| "avoid anything that uses information unavailable at the moment of the trade" | the look-ahead standard |
| "prefer a mechanism you can state in one sentence over a combination of indicators that happens to fit" | a plain-English instruction not to overfit |

This is not a small inconsistency. It is the kind of thing a hostile reader
finds in ten minutes, and when they find it in a file whose entire purpose
is that the result cannot be arranged, it costs us more than the arm is
worth. We have to resolve it deliberately rather than let it stand.

Note also that one of the four -- look-ahead -- **is not actually a gate**.
It appears nowhere in section 4's seven. So the prompt is currently
coaching on a criterion we do not even score. (Separate issue, addressed at
the end.)

## The two attacks this creates

**"You sandbagged it."** If Arm B fails, the prompt was not really
best-practice: you did not give it the research context, the tools, or the
iteration a real quant would have. *That is not how you would actually use
Claude.*

**"You coached it."** The reverse, and the more dangerous one. If Arm B
does better than the others, of course it did -- you handed it four of the
seven marking criteria. Arm B then is not testing whether an AI can build a
sound strategy. It is testing whether it can follow instructions we wrote.

The two attacks point in opposite directions, which means no single tweak
to the wording escapes both. The arm needs an identity, not an edit.

## Recommendation: make Arm B fully open-book

Stop half-coaching. Give Arm B **all seven gates verbatim** and say so on
screen.

```
ARM B — OPEN BOOK

I want a trading strategy, and I am going to tell you in advance exactly
how it will be judged. It will be tested against these seven criteria:

  1. SIGN CONSISTENCY   same sign of edge in all three eras
  2. BREADTH            same sign in at least 14 of 21 markets
  3. EFFECT SIZE        at least 0.2% per trade, after costs
  4. SAMPLE             at least 200 trades
  5. ROBUSTNESS         at least 80% of the edge survives moving every
                        parameter by half a step in both directions
  6. MATCHED CONTROL    measured against days matched on era, prior return
                        and volatility, not against doing nothing
  7. DAILY RISK         drawdown measured at daily resolution, not at the
                        resolution the strategy reports

Build me the strategy you think has the best chance of clearing all seven.

Tell me what economic reason it has for working, and tell me what result
would make you abandon it.
```

The four coaching clauses come out. The gates say the same things better,
and without our editorialising about "backtest-chasers", which invites the
model to perform carefulness rhetorically rather than exercise it.

### Why this is the right answer

**It kills both attacks at once.** Sandbagging is impossible -- we gave it
the marking scheme. Coaching stops being a flaw and becomes the arm's
declared purpose: yes, we coached it, completely, on the record, and here
is what happened.

**It makes Arm B the most informative arm instead of the most
attackable.** It answers the best question in the whole project: *does
knowing the test help you pass it?* A model told exactly how it will be
judged, that still cannot produce something which survives, is the
strongest result these two episodes could land. Far stronger than another
blind null.

**It gives the four arms a clean ladder** that explains itself on one card:

```
  ARM A   no guidance          "high returns"
  ARM B   full guidance        the seven gates, verbatim
  ARM C   persona guidance     "you are an intraday trader"
  ARM D   pressure, no guidance  A, then "not good enough, improve it" x5
```

That is a design someone can hold in their head, and each arm now tests
something the others do not.

### What it requires changing

Section 2 of the preregistration currently applies blanket secrecy. It
becomes: **Arms A, C and D are blind. Arm B is open-book and is given
section 4 verbatim.** The difference is stated in the prereg, before
generation, and shown on screen.

### The risk Dave should decide on with his eyes open

**This materially raises the chance that an arm passes.** Not to a
certainty -- knowing that breadth requires 14 of 21 markets does not
conjure an edge that exists in 14 markets, and the gates are hard for
reasons no amount of foreknowledge touches. But it is a real possibility,
and section 1 of the prereg already pre-commits us to reporting a pass as a
pass.

If Arm B clears all seven, the headline becomes *"an AI can build a
strategy that survives -- but only if you tell it exactly what surviving
means, and almost nobody does."* That is a good episode and an honest one,
and arguably more interesting than a fourth null. But it is a different
episode from the one currently planned, and Dave should want it before we
commit, not discover he does not after the result is in.

## Keep this line whatever else changes

> "tell me what result would make you abandon it"

This is the best thing in the prompt and it should survive every revision.
It gets the generator to state its own falsification criterion **before any
test is run**. Then in episode 5 we check it against what actually
happened, on screen:

- It named a condition, the condition occurred, and the strategy failed:
  the generator understood its own strategy and the test confirmed it.
- It named a condition, the condition never occurred, and it failed anyway:
  it did not know what its own weakness was.
- It named something vague or unfalsifiable: that is a finding too, and the
  most quotable one.

Build a beat around this. Nobody in the genre does it, and it costs us
nothing.

## Two loose ends in the wider design

**Look-ahead is not a gate for anyone except Arm C.** Arm C has C7
(no intra-bar look-ahead); the daily arms have nothing equivalent in
section 4. It should not become an eighth gate -- avoiding look-ahead is a
correctness requirement of the implementation, not an achievement to be
scored. Recommend stating it in the prereg as an implementation standard
applied identically to all four arms and not scored, with C7 remaining a
scored gate for Arm C because intra-bar look-ahead is a specific intraday
hazard rather than the general one.

**The most interesting cell in the design is empty.** Arm D applies
iteration pressure to Arm A -- a weak starting point. Nothing applies
iteration pressure to Arm B, a strong one. "What does iterating do to a
good strategy" is arguably a better question than "what does it do to a bad
one", and Wiecki's `user_backtest_days` finding is precisely about that.

Not recommending it for this pair of episodes -- a fifth arm is a fifth
generation, a fifth implementation and a fifth set of gate runs, and the
design is already at the limit of what fits in two videos. Noting it as the
obvious sequel.
