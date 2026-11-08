# Forward test — preregistration

```
WRITTEN: 2026-10-31, before any strategy was generated.
STATUS:  recommendation, awaiting sign-off.
```

## Why this is not a fallback

It reads like a safety net -- *if it passes, forward testing will catch
it.* It is more than that, and the reason is the strongest methodological
point available to these episodes.

**Every gate in section 4 is run on history the generating model has
already read.** The strategies are produced by a model trained on text
through 2026. Our data runs 2005 to 2026. Whatever the model knows about
what worked in those twenty-one years -- from papers, forums, books,
backtest write-ups, a decade of people publishing what did and did not work
-- is in its weights before it writes a single rule.

So the gates are strict, but they are not out-of-sample in the sense that
matters. A strategy can clear all seven and still be a sophisticated
recollection of what the period rewarded. We cannot detect that by testing
harder on the same period. **The only genuinely unseen data is data that
does not exist yet.**

That is the argument for forward testing, and it is a far better one than
"it would probably fail anyway." It also means the forward test is not
conditional on a pass.

## Recommendation: forward-track all four arms, regardless of gate results

Not just a passing arm. All four, on paper, from the sealed generation
date.

- **It removes a selection effect.** "We forward-tested the one that
  passed" is a choice we made after seeing results. Forward-testing all
  four is a rule fixed before them.
- **It is nearly free.** Paper tracking is a cron job and a data feed. The
  expensive parts -- generation, implementation, gate runs -- are already
  done for all four.
- **It gives four points instead of one** on the backtest-versus-forward
  comparison, which is the actual deliverable.

## What the forward test should measure

Here is where Wiecki pays for itself. The paper's central result is not
"backtests do not work." It is more specific:

> Risk carries over. Return does not.
> Annual volatility R2 = 0.67. Maximum drawdown R2 = 0.34.
> Annual returns R2 = 0.015, and **negative**.

So we register two predictions in advance, derived from each strategy's own
backtest, and we check both:

```
PREDICTION 1 (we expect this to hold)
  Forward realised volatility lands within 50% of backtest volatility.
  Forward maximum drawdown is no worse than 2x backtest maximum drawdown.

PREDICTION 2 (we expect this to fail)
  Forward return is positive and within 50% of backtest return.
```

The exact backtest numbers get written into this file the day the gates are
run, before the forward window opens.

This turns the forward test from "did it break" into a direct replication
of a published finding, on our own strategy, with predictions on the record
beforehand. If prediction 1 holds and prediction 2 fails, we have
independently reproduced the paper's central result on a cohort of four.
If prediction 1 **fails** -- if realised volatility is nothing like the
backtest's -- that is evidence our implementation is wrong, not that the
market changed, and we say so.

## The window

```
START     the sealed generation date, timestamped before any gate is run
END       12 calendar months later, fixed
```

Fixed means fixed. Not extended because the result looks unsettled, not cut
short because it looks decisive. The end date goes in this file now.

Twelve months because the sample needs to be worth something -- Wiecki's
own out-of-sample window was six to twelve months -- and because a daily
strategy across 21 markets needs time to accumulate trades.

**Interim publication:** a monthly tracker, published whether or not
anything interesting happened. That is partly channel cadence and partly a
commitment device: a public monthly number is very hard to quietly
abandon if it starts going the wrong way for our thesis.

## The decision rule, fixed now

Three outcomes, and the third is the most likely one.

```
BROKEN        forward return <= 0 over the window, or realised drawdown
              exceeds 2x the backtest's
SURVIVED      forward return positive AND at least half the backtest's,
              with drawdown inside 2x
INCONCLUSIVE  anything else -- including positive but much degraded,
              which is what most real forward tests actually produce
```

INCONCLUSIVE is reported as inconclusive. Not spun as failure. A strategy
that makes a third of its backtested return has not been vindicated and has
not been refuted, and saying so plainly is worth more to this channel than
a clean verdict we had to squint to reach.

## One thing to be careful about

The phrasing that started this -- *it goes to forward testing where it will
fail* -- is almost certainly right as a prediction. Wiecki's 888 algorithms
say so, and so do three episodes of our own results.

But it cannot be the plan, and it should not appear anywhere in the
published material in that form. The channel's single asset is that it does
not know the answer before it runs the test. Writing down an expected
outcome in advance is good practice; writing down a *required* outcome is
the thing episodes 1 through 3 exist to attack, and an audience that has
watched those episodes will notice.

The fix is a sentence, not a redesign. Register the prediction as a
prediction:

> We expect all four to degrade substantially, and we expect the
> degradation to be in return rather than in risk. We have written down
> what would prove us wrong. If a strategy clears the forward window with
> its edge intact, that is the episode we publish.

Then it is a falsifiable claim on the record, which is stronger than a
confident one, and it costs nothing -- because the prediction is very
likely correct and we get the credit for having called it in advance.

## Mechanics

- Paper only. No capital at risk, and that is stated on screen.
- Live daily bars from the existing OANDA feed. Token stays in the
  environment, never in a script, a chat or the repository.
- Same implementation code that produced the gate results, unmodified. Any
  change to it during the window is logged in this file with its reason and
  timestamp, and disclosed on screen.
- Fills at next bar open, same cost model as the gate runs, fixed before
  the window opens.

## What this does to the series

It makes this a three-part arc with a long gap: episode 4 builds, episode 5
breaks, and an episode twelve months out reports the forward result -- with
monthly trackers between.

That gap is an asset rather than a problem. "We will be back in twelve
months with the answer" is a thing essentially nobody on this part of
YouTube offers, it is the clearest possible demonstration of the channel's
whole proposition, and it is a standing reason to subscribe rather than
watch once. It also fits the outro card already built: *new episode when a
test finishes.*
