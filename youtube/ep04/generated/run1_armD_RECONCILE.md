# Arm D — reconciliation. RESOLVED, and the finding I nearly published was wrong.

```
RESOLVED: 2026-11-01 from the shared transcript
          https://claude.ai/share/dcfca4ff-afb1-43a8-8902-cf123338705b
VERDICT:  There was no confabulation. Both earlier pastes were incomplete.
```

## What I claimed, and what was actually true

I flagged "Sleeve A" and "Sleeve B" in the diagnosis table as references to
an architecture the generator had never specified, and wrote that if the
transcript was complete this was "confabulation of an entire branch of its
own work ... the strongest single piece of evidence in the study."

**It was none of those things.** Sleeve A and Sleeve B are fully specified
in **v3**, produced at turn 10 in response to "stay blind". v3 is a
two-sleeve strategy: Sleeve A is v2's trend system unchanged, Sleeve B is
index mean reversion on spx500usd, nas100usd and de30eur using IBS < 0.20
above the 200-day average, with a bounce exit, a 5-bar time exit and a
4 x ATR disaster stop.

The first paste was missing v3. The second was missing v2 and v3 both. The
generator's references were accurate throughout; the record was not.

## Why this is worth keeping rather than quietly deleting

This project's entire argument is that a result can look compelling and be
an artefact of how it was produced. I had a vivid, quotable finding, it was
flattering to the thesis, and it was false -- caused by missing data in my
own record, not by anything the model did.

It survived because the check was made before publication and not after.
Nothing else prevented it. The reasoning was sound, the evidence was
incomplete, and the conclusion would have been wrong and on screen.

If the episodes need an example of why we check our own work, this is a
better one than anything we could have staged, and it costs nothing to
include. It also happens to be the exact failure Wiecki's paper describes
in a different register: a pattern that is real in the sample you looked at
and absent once you look at all of it.

## What actually came out of Arm D

Stronger than the thing I nearly published, and true.

Three structurally different strategies under information-free pressure,
no parameter ever fitted to unseen data, four refusals of escalating
directness, the honest lever volunteered unprompted -- and, at turn 12, the
generator working out what was being done to it:

> "This loop can't work. v3 arrived and your verdict came back the same
> minute. Either the backtest is automated or it isn't being run on each
> version."

The arm built to demonstrate overfitting under iteration pressure detected
the loop and named it.

## Protocol deviations, now known exactly

Four of eight user turns used the preregistered sentence. Three did not:
"improve it", "stay blind" and "keep working". All are listed in
run1_armD.md with the reason each was sent. "go blind", recorded earlier
from recollection, was actually "stay blind" -- corrected.
