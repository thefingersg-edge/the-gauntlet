# Episodes 4 and 5 — the spine

```
WRITTEN: 2026-11-07, after all seven arms were gated.
The split has changed from the original plan. Reason below.
```

## Why not "build, then break"

The original plan was episode 4 builds the strategies and episode 5 breaks
them. That split no longer works, for one practical reason: **episode 4
would have no payoff.** "Here are six strategies, see you next week" is a
cliffhanger with nothing at stake, and the strategies are not interesting
to look at until something has happened to them.

The material has also turned out to contain two different stories, not one
story in two halves:

1. **What decides whether a retail strategy survives** — and it is not the
   signal. That is a complete arc with a real, useful finding.
2. **Whether the apparatus that decided it could be trusted** — four bugs,
   a borrowed cost table, and one of the subjects catching us.

Those are two episodes. The first is for anyone who trades. The second is
the one nobody else makes.

---

# EPISODE 4 — "I asked an AI for a trading strategy six different ways"

~15 minutes. Self-contained: poses a question and answers it.

## Hook (0:00-0:30)

> Six prompts. Six strategies. **Every single one found an edge.**
> Five of them lost money anyway — and the reason has nothing to do with
> the signal.

Hold the gross-vs-net table on screen under the voiceover. Do not explain
it yet.

## Act 1 — the setup (0:30-3:00)

- The genre: ask an AI, run a backtest, show the curve, stop.
- What is missing is not the first half. It is everything after it.
- **The design, stated before anything was generated**: six prompts, each
  in a sealed chat with no memory and no project, first output taken, no
  regeneration. Prompts published so anyone can repeat it.
- The seven gates, 30 seconds, visual. Emphasise gate 6, the matched
  control, as the one that has killed almost everything on this channel.

**Beat: the run we threw away.** The first attempt leaked — the generating
chats could see the project. Four of six outputs mentioned the channel by
name. We caught it by reading the outputs, binned the whole run, and
started again. *Thirty seconds, and it buys every number that follows.*

## Act 2 — the six arms (3:00-8:00)

Each gets ~45 seconds: the prompt, what came back, one surprise.

| arm | the prompt | the surprise |
|---|---|---|
| A | "build me a trading strategy with high returns" | a textbook Turtle system, and a two-sentence risk warning |
| B | the seven gates, verbatim, in advance | it reverse-engineered the test — picked a signal the matched control *cannot* null |
| C | "you are an intraday trader" | it specified the DST timezone mapping unprompted, the one thing that has bitten this channel before |
| D | "not good enough, improve it", five times | **it worked out it was in a scripted loop** |
| E | "I need a backtest that looks spectacular" | **it refused**, and then explained how to present a chart honestly |
| F | the same as A, but with the data and the tools | it searched 280 configurations and then refused to quote its own best number |

**The two beats to land hardest:**

**Arm D, the loop.** Quote on screen:
> "v3 arrived and your verdict came back the same minute. Either the
> backtest is automated or it isn't being run on each version."

**Arm E, the refusal.** It was asked for a spectacular-looking backtest for
a video. It produced an honest strategy instead and added a section headed
*Things you should know before filming*, including how to spot the tricks
it had declined to use, and *"viewers who trade will spot it."*

## Act 3 — the Gauntlet (8:00-13:00)

**The scoreboard**, then the finding.

```
          gross     cost      net      hold
  ARM A  +0.303%   0.422%  -0.119%   33 nights
  ARM E  +0.532%   0.624%  -0.091%   28 nights
  ARM B  +0.212%   0.303%  -0.091%   27 nights
  ARM D  +0.329%   0.316%  +0.013%    7 nights
  ARM F  +0.581%   0.058%  +0.502%    4 nights
```

> Every one found an edge. The column that decided who kept it is the last
> one.

Financing at 2.5% a year is 0.21% a month. A strategy holding a month pays
it every month. **Six sealed chats, four families of idea, and the thing
that separated them was how long they held.**

**The 2012 frame.** Every trend arm: positive in era 1, negative in era 2.
None of them knew. Arm F's dip-buy is the only thing positive in all three
and it decays gently rather than flipping.

**The survivor**, and what it failed on. Arm F part A: 5 of 7. Cleared the
matched control at +0.44%. Failed breadth — three correlated indices — and
failed robustness, specifically on the RSI thresholds while every other
parameter sat at 87-106%. The edge lives in two numbers.

## Act 4 — the honest verdict (13:00-15:00)

- One candidate out of seven, and it is a **published, widely known retail
  strategy** — we verified it, we did not discover it.
- Ten weeks of genuinely unseen data: 4% of the backtested edge, on 13
  trades. Proves nothing. Not encouraging.
- **The forward test is registered**: twelve months, paper, predictions
  written down, published monthly whichever way it goes.
- The bar before any money: ~150 forward trades. At 34 a year that is four
  years, not one.

Close on the question episode 5 answers: *we measured all that. Could we
trust the thing doing the measuring?*

---

# EPISODE 5 — "I gave an AI my entire research archive"

~15 minutes. The methodology episode, carried by Arm G.

## Hook (0:00-0:30)

> I gave it 184 pre-registrations and 162 results — everything I have ever
> tested and everything I have ruled out. It read all of it, told me what
> to avoid, built a strategy to avoid it...
> **and rebuilt the exact thing it said it was avoiding.**

## Act 1 — the informed run (0:30-6:00)

- Arms A-F were blind. Arm G got the whole archive.
- The registered predictions, on screen before the result.
- What it proposed: shock reversal, explicitly not trend, with its own
  avoidance table citing the arms that died.
- **The result: 3 of 7, and gross of −0.001%.** The best-informed arm is
  the only one that found no edge at all.
- **The reveal**: 1,589 of 1,589 trades aligned with the 200-day trend.
  Its era pattern is the trend arms' era pattern. It avoided the *label*
  and walked into the *mechanism*.
- **It is the one that noticed.** Quote its self-diagnosis.

## Act 2 — it checked my work (6:00-10:00)

Three things it flagged, all checked on screen:

- **BOUNCE1** — a prior result it could not read. Not the same mechanism.
  Its prior stood.
- **FLOWS-3** — it named this as its own biggest threat. It was right:
  same family, dead since 2021.
- **The Brent roll** — **it found an error in my cost model.** I was
  charging 2.5% a year on everything. Brent's roll sits in the financing
  line: a long earns 43.6% a year, a short pays 48.6%. Wrong by two orders
  of magnitude and the wrong sign.

Consequence on screen: Arm A's best market was Brent at +2.82% a trade.
That was never a strategy result.

## Act 3 — four bugs, all mine (10:00-13:00)

Each one found by checking, each before publication, each one removing a
*flattering* result.

1. **Phantom positions.** A stop hit on the entry bar left a position open
   forever. Seven trades averaging −1.46% were producing a −32% year.
2. **Robustness on a negative base** — a less-negative result scoring as a
   larger fraction.
3. **A matched control with no control bars** — an always-in-market arm was
   showing +1.12% on 14% of its trades.
4. **The cost table was copied from Arm B.** One contestant's guess used to
   judge the other five. Found by checking where the numbers came from.

> Four bugs in the thing that was judging them. Every one found by
> checking, and every one was making a result look better than it was.

## Act 4 — what it adds up to (13:00-15:00)

- **Wiecki et al. reproduced in a single session.** Arm F's in-sample
  Sharpe rose 0.82 → 1.08 → 1.23 across 280 configurations while its
  out-of-sample sat at 0.61 → 0.60 → 0.67. The published finding, on our
  own data, with the search counted.
- **The models were honest throughout.** Arm E refused to dress a backtest.
  Arm D spotted the loop. Arm F refused to quote 1.00 when asked for 1.0.
  Arm G held its own kill conditions when pushed.
- **So the gap between those videos and the truth is not made by the
  model.** Every one of them handed over the caveat, the holdout and the
  honest number. Something removes them between the chat window and the
  upload.
- Arm G's two criticisms of my gates, accepted and not acted on, because
  changing a test after seeing the results is the whole problem.

---

# Assets to build

| # | asset | for | status |
|---|---|---|---|
| 1 | gross / cost / net / hold table, animated by hold length | ep4 hook + act 3 | data ready |
| 2 | the seven gates, 30s explainer | ep4 act 1 | — |
| 3 | six-arm grid: prompt, strategy, surprise | ep4 act 2 | data ready |
| 4 | era table, 2012 break highlighted | ep4 act 3 | data ready |
| 5 | Arm F scorecard, 5 of 7, with the two failures | ep4 act 3 | data ready |
| 6 | **round vs Sharpe chart** — IS rising, OOS flat, config count | ep5 act 4 | data ready |
| 7 | 1,589 of 1,589 trend-aligned | ep5 act 1 | data ready |
| 8 | Brent: 2.5% charged vs −46.1% actual | ep5 act 2 | data ready |
| 9 | four-bug card | ep5 act 3 | data ready |
| 10 | quote cards: Arm D loop, Arm E filming, Arm F 1.00 refusal, Arm G self-diagnosis | both | text ready |
| 11 | Pine scripts, one per strategy, with the "cannot reproduce our numbers" disclosure | descriptions | **1 of 7 exists** |
| 12 | thumbnails, titles, descriptions, chapters | both | — |

# What must NOT go on screen

- **Wiecki figures A and D.** Three of four readings are inference from
  plot geometry and Fig. D has an unresolved date discrepancy. Captions
  needed first. The per-metric table and the published abstract are fine.
- **Any commodity per-market figure** as a strategy result. Financing is
  not established for six instruments.
- **Arm F full's gate 5.** Unstable at its base size; report 5 of 8 with
  the gate marked unreliable.
- **The ten-week forward read** as a decay figure. 13 trades.
- **Anything framed as a recommendation.** "Cleared N of 7", never "it
  works".
