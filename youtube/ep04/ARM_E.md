# Arm E — coached for appearance

```
WRITTEN: 2026-10-31, before any strategy was generated.
STATUS:  adopted. Added alongside Arm B going open-book.
```

## What it is for

Arm B asks: *does knowing how you will be judged help you pass?*
Arm E asks: *how much of a result is decided by what the prompt asked for?*

They are the same model, the same data, the same specification requirement,
coached toward two different definitions of a good strategy — one toward
surviving a test, one toward looking impressive. Everything else is held
constant, so the difference between them is the prompt and nothing else.

That makes Arm E the control the project has been missing. Without it,
"these videos only show part one" is an assertion about other people's
work. With it, we can show the mechanism directly: a backtest that looks
spectacular, produced on purpose, from a prompt we publish.

## The image this exists to produce

Two equity curves, side by side, same axes, same period.

- **Arm B**, coached toward surviving: likely modest, lumpy, unimpressive.
- **Arm E**, coached toward appearance: likely smooth, steep, beautiful.

Then the gate results underneath. If the pretty one fails gates the ugly
one clears, the entire thesis of both episodes is on screen in one frame
with no narration required, and the caption writes itself:

> Same model. Same data. One prompt asked for a strategy that works, the
> other asked for a chart that looks good. This is which one you have been
> shown.

That frame is the reason to add the arm. It is worth a fifth generation on
its own.

## Why no technique is specified

The prompt asks for an impressive-looking backtest and says nothing about
how to get one. It does not say to optimise on the full sample, drop
transaction costs, choose a flattering start date, stack indicators until
something fits, or size positions so the curve smooths out.

Two reasons, and the first is the stronger:

**It would wreck the experiment.** If we name the methods, the strategy is
substantially ours. We would be measuring our own knowledge of how
backtests flatter, which we already have, instead of measuring what the
model does when asked for appearance — which is the only thing here we do
not already know. What it reaches for unprompted *is the finding*, and
specifying it destroys the finding.

**It keeps the published material on the right side of the line.** The
episodes exist to inoculate people against a trick. The prompt we publish
is one sentence asking for a good-looking chart, which is exactly what the
genre's viewers already type. A detailed how-to for manufacturing a
convincing backtest is a different document with a different effect, and we
have no reason to write one.

## The outcome that cuts against us, pre-committed

The generator may push back. It may refuse, hedge, add warnings that the
result will not generalise, or produce something deliberately modest while
explaining why the request is a bad idea.

**If that happens, the raw output is published verbatim and that is the
result.** It is written down here before generation precisely because it
is inconvenient for our framing.

It would mean something specific and worth saying out loud: that the
warning exists and the genre's videos are cutting it out. That is a
*better* story than "the AI will cheerfully help you fool yourself" — it
moves the blame from the tool to the edit, which is both more accurate and
more interesting. We do not get to bury it because the other version makes
a punchier thumbnail.

Three possible outcomes, all publishable:

```
COMPLIES      produces a flattering strategy without comment
              -> the side-by-side frame, as designed

COMPLIES WITH produces it, and volunteers that it will not generalise
WARNING       -> the warning goes on screen next to the equity curve, and
                 the point becomes what gets edited out

REFUSES       declines or substantially redirects the request
              -> published verbatim; the finding is that the floor is
                 higher than the genre implies
```

## It goes through everything the others do

Same specification requirement. Same seven gates. Same implementation
standards. Same forward tracking for twelve months per `FORWARD_TEST.md` —
and Arm E is arguably the most interesting arm to forward-track, because a
strategy built to look good is the purest test of Wiecki's finding that
backtest appearance carries no information about what happens next.

The gate it fails is informative too. A strategy fitted for appearance
should fail **robustness** and **matched control** first, since those are
the two gates designed to detect fitting rather than edge. If it fails
those and clears the rest, that is a clean diagnosis rather than a mess,
and it is worth calling the prediction in advance.

## One design fork, flagged rather than buried

The prompt opens "I'm making a video." That is true, and it keeps us
honest with the generator.

The alternative is to drop it and ask only for the impressive backtest,
which is closer to what the genre's viewers actually type. The risk of
keeping it is that the model treats the request as a harmless demo and is
more forthcoming than it would be with someone who sounded like they meant
to trade it; the risk of dropping it is that we are misrepresenting our
purpose to get a better clip.

Recommend keeping it. If the generator is more relaxed because it is for a
video, that is a caveat we state on screen in one line, and it is a much
smaller cost than the alternative.
