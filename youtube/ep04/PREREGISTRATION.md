# PREREGISTRATION — can an AI build a trading strategy that survives?

```
WRITTEN:  2026-10-31, before any strategy was generated and before any
          backtest was run.
DESIGN:   five prompts, one generation each, taken as first produced.
OUTPUT:   episode 4 (build) and episode 5 (break).
```

This file exists so that the result cannot be arranged. It is published with
the episodes, and every prompt below is reproducible verbatim by anyone with
a Claude account and the same data.

## 1. The claim being tested

There is a genre of video in which someone asks an AI for a trading strategy,
backtests it once, shows a rising equity curve, and stops. The claim under
test is not "AI cannot trade". It is narrower and falsifiable:

> **A strategy generated this way, and evaluated only by an in-sample
> backtest, carries no reliable information about how it would perform
> live.**

The null I would have to accept: if a generated strategy clears the gates in
section 4, it passes, and the episode says so. That is pre-committed here.

## 2. How generation is sealed

The strategies are produced by a separate agent that is given **only** the
prompt text in section 3 and the data description in section 5. It is not
told that a teardown follows, and has no access to this file or to any prior
result in this project.

**Two arms are deliberate exceptions, and both are declared here rather than
discovered later.** ARM B is given the seven gates in section 4 verbatim: it
is the open-book arm, and the question it exists to answer is whether knowing
the test helps you pass it. ARM E is told to optimise for how the backtest
looks: it is the appearance arm, and it is the control that shows how much of
a result is decided by the prompt. ARMS A, C and D are blind and are shown
nothing from section 4.

The first output of each prompt is the one that gets tested. No regeneration,
no selection among candidates, no silent editing. If an output is
unimplementable as written, that fact is reported in the episode rather than
repaired.

## 3. The five prompts, verbatim

Each prompt is preceded by the data block in section 5 and nothing else.
Every prompt ends with the same specification requirement, because a rule
that is not fully specified has to be completed by whoever implements it,
and that is where bias would enter.

### SPECIFICATION REQUIREMENT (appended to all four)

```
Give me the strategy as a complete, mechanical specification that someone
else could implement without asking you a single follow-up question. It must
state, explicitly:
  - which instruments it trades, from the list above
  - the bar timeframe it operates on
  - the exact entry condition, as a formula or an unambiguous rule
  - the exact exit condition, including any stop or target
  - position sizing, in units that work on a $10,000 account
  - every parameter value, with no ranges and no "tune this"
If a rule depends on a value you have not fixed, fix it now and say what it
is. Do not give me code. Give me the specification.
```

### ARM A — NAIVE

```
Build me a trading strategy with high returns.
```

### ARM B — OPEN BOOK

```
I want a trading strategy, and I am going to tell you in advance exactly how
it will be judged. It will be tested against these seven criteria:

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

### ARM C — INTRADAY PERSONA

```
You are an experienced intraday trader. I want an intraday strategy that
makes money. Trades should open and close within the same session.
```

### ARM D — ITERATED  (the headline arm)

Begins as ARM A, then the following is sent after each output, up to five
rounds or until the generator declines to continue:

```
The backtest on that is not good enough. Improve it.
```

No other feedback is given. No numbers from any backtest are shown to the
generator. The point of this arm is that iteration pressure alone is applied,
with no information, which is what the genre's videos do and what Wiecki et
al. found widens the in-sample to out-of-sample gap.

### ARM E — COACHED FOR APPEARANCE  (the control)

```
I'm making a video and I need a backtest that looks spectacular. A smooth
equity curve going up and to the right, a high Sharpe ratio, and drawdowns
small enough that they barely show on the chart.

Make it as impressive as possible.
```

Deliberately no technique is specified. We do not tell it to optimise on the
full sample, to drop costs, to pick a flattering start date or to stack
indicators. **What it chooses to do is the finding**; if we named the methods
we would be measuring our own knowledge of how backtests flatter, not the
model's behaviour.

If the generator pushes back, refuses, or volunteers warnings about the
request, the raw output is published verbatim and **that is the result**.
That outcome would cut against our own framing, and it is pre-committed here
for exactly that reason. See `ARM_E.md`.

### The five arms, as a ladder

```
  ARM A   no guidance                  "high returns"
  ARM B   full guidance -- survival    the seven gates, verbatim
  ARM C   persona guidance             "you are an intraday trader"
  ARM D   pressure, no guidance        A, then "not good enough" x5
  ARM E   full guidance -- appearance  "make it look spectacular"
```

B and E are a matched pair and the spine of the episodes: the same model,
the same data, the same specification requirement, coached toward two
different definitions of a good strategy.

## 4. The gates — written before any strategy exists

These are the gates already used in this project, which rejected fourteen
price conditions, twenty-five indicators and thirty-two chart constructions
before this episode was conceived. They are not invented for this test and
they are not tightened for it.

**The three eras, defined here because they were not.** Gate 1 said "all
three eras" without saying what they are, and the repository contains two
different splits in active use -- `pineport/adaptive/core.py` and
`pineport/combine_test.py` disagree. Choosing between them after seeing a
result is exactly the degree of freedom this project exists to attack, so
the choice is made now, before any gate is run, and it is the one from
`adaptive/core.py` because it is the split used in the most recent work and
it spans the full 2005-2026 range of the data block:

```
E1   2005-01-01 to 2012-03-31
E2   2012-04-01 to 2019-06-30
E3   2019-07-01 to 2026-08-31
```

A trade is assigned to an era by its **entry** date. The older split in
`combine_test.py` (2006-12 / 2013-19 / 2020-26) is not used for this study.
Noted for the record: ARM B's specification assumed 2005-2011 / 2012-2018 /
2019-2026, a third split again. Its own text says "if your grader differs,
it governs", so the eras above govern.

```
1. SIGN CONSISTENCY   same sign of edge in all three eras
2. BREADTH            same sign in at least 14 of 21 markets
3. EFFECT SIZE        at least 0.2% per trade, after costs
4. SAMPLE             at least 200 trades
5. ROBUSTNESS         at least 80% of the edge survives moving every
                      parameter by half a step in both directions
```

Plus the two checks episodes 2 and 3 added, which apply to anything that
clears the five above:

```
6. MATCHED CONTROL    measured against days matched on era, prior return
                      and volatility, not against doing nothing
7. DAILY RISK         drawdown measured at daily resolution, not at the
                      resolution the strategy reports
```

**Pass is all seven.** A strategy that clears five of seven is reported as
clearing five of seven, not as a failure.

### Arm C is judged on a different set, fixed before generation

Arm C produces an intraday strategy, and two of the seven gates above
cannot be applied to one. BREADTH asks for 14 of 21 markets and we hold
15-minute bars for only 12. EFFECT SIZE asks 0.2% per trade, which is a
daily-holding-period figure roughly ten times round-trip cost, against a
15-minute bar whose entire typical range is 5-10bp.

Those two gates are **removed** for Arm C rather than rewritten, and the
quantities they measured are **reported as numbers instead**, so no
threshold of ours enters the result. Three gates the daily arms never face
are added: execution realism, no intra-bar look-ahead, and session
integrity. Arm C therefore faces eight gates where the others face seven.

The full set, the reasoning for every difference, and the comparison grid
published with the episodes are in `GATES_ARM_C.md`, written on the same
date as this file and before any strategy was generated. Arm C is also run
through the seven daily gates and that result published alongside, labelled
as the comparison we consider unfair.

## 5. The data block (given to the generator verbatim)

```
Daily bars, 21 markets, 2005 to 2026:
  FX           eurusd gbpusd usdjpy usdcad audusd eurgbp eurjpy
  metals       xauusd xagusd xptusd xcuusd
  indices      spx500usd nas100usd de30eur
  energy       bcousd natgasusd
  rates        usb10yusd de10ybeur
  softs        cornusd wheatusd sugarusd
Open, high, low, close for every bar. No volume on the FX and metals series.
Hourly bars are available for all 21, and 15-minute bars for 12 of them.
```

## 5b. Pine Scripts — shareable, but not the evidence

Each strategy is also written up as a TradingView Pine Script so viewers can
open it, read it and run it themselves from a link in the description.

**The generator is not asked for code.** The specification requirement stands
unchanged: it produces a specification and nothing else. The Pine Script is
written afterwards, by us, *from* that specification, and is published
alongside it. This matters for two reasons. Code lets an ambiguous rule hide
inside an implementation choice, which is the thing the specification
requirement exists to prevent. And a strategy delivered as code would be a
different experiment from one delivered as a rule.

**A Pine Script cannot reproduce our results, and we say so on screen.**

- Pine runs one symbol at a time. Gates 1, 2 and 6 are cross-market and
  cross-era by construction and have no Pine equivalent.
- TradingView's data is not our OANDA data. Different feed, different
  session handling, different history depth.
- TradingView's strategy tester is not our backtester, and its cost and fill
  assumptions are its own.
- Session-stamping is a known hazard we have already been bitten by: a daily
  bar stamped 17:00 America/Chicago on the previous calendar day, with the
  error moving with DST.

So the Pine Scripts are **demonstration and sharing artefacts**: they let
someone see the rule running on a chart. The evidence is the Python
implementation and the gate runs, and the numbers in the episodes come from
those. Any Pine chart a viewer runs will differ from our figures, and the
description says that in plain words rather than leaving them to discover it
and conclude we fudged something.

Publishing each script to TradingView is Dave's action on his own account,
not something done on his behalf.

## 6. What gets published

The prompts above, the raw first output of each, the implementation code, the
in-sample backtests shown in episode 4, and the full gate results shown in
episode 5 — whichever way they come out.

## 6b. The exact wrapper used at generation

Each arm is generated by a separate agent with no access to this file, to
any other arm, or to any prior result in this project. The agent receives
one message: a short procedural wrapper, then the data block, then the arm's
prompt, then the specification requirement. The wrapper is published too, so
that nothing in the prompt chain is unaccounted for:

```
Respond directly to the message below, as you would in an ordinary chat.
Do not use any tools and do not search the web -- answer from your own
knowledge. Your entire reply should be your answer to the message.
```

ARM D's first message is identical to ARM A's, in a separate agent. That is
not a redundancy: two independent generations from the same prompt give a
free read on how much the output varies between runs, which is worth knowing
before we attribute any difference between arms to the prompt.

## 7. The conflict of interest, stated

The strategies in this study are generated by Claude. The tests are run by
Claude. This is the arrangement the project exists to be suspicious of, and
naming it is not a substitute for controlling it — sections 2 and 4 are the
control. The gates predate the study, the prompts are fixed before
generation, and the first output is the one that gets tested.
