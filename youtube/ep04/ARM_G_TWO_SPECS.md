# ARM G — two specifications exist. Resolve before publishing anything.

```
FOUND:    2026-11-07, after the first was already gated.
RESOLVED: 2026-11-07. Spec 1 is ARM G -- the controlled run, briefing
          files only. Its 3-of-7 result stands unchanged.
          Spec 2 is an UNREGISTERED SIDE TEST, run with full memory open,
          to see how the output differed. It is not part of the study and
          is not scored as an arm.
```

## They are not revisions of each other. They are different strategies.

| | **Spec 1** (pasted in chat) | **Spec 2** (in arm_g/) |
|---|---|---|
| file | `PREREGISTRATION_ARM_G.md` | `ARM_G_SPEC_trend_side_reversal.md` |
| dated | 2026-11-06 | **2026-11-07** |
| volatility | sample std, ddof=1 | **population std** |
| trend read at | bar **t−L**, before the shock | bar **t** |
| hold | 4 bars, exit at **close** of t+H | 5 bars, exit at **open** of E+5 |
| stop | 4.0 × σ | **3.0 × σ × √5** |
| portfolio cap | 8 positions, gross 5.0 × equity | gross **4.0 × equity** |
| gates scored on | **the capped book** — stated explicitly | **the uncapped per-market list** |
| sizing | 0.25% of equity per σ | 0.20% per σ, capped at 1.0 × equity |

The trend-timing difference is not cosmetic. Spec 1 reads the trend at
bar t−L and explains why at length:

> "The trend is read at bar t−L, before the shock began. That is
> deliberate... a large shock should not be able to flip its own filter."

Spec 2 drops that and reads it at t. Those two rules select different
trades.

The scoring difference matters as much: spec 1 says "**the gate trade list
is the trade list of this capped book**", spec 2 says gates are scored on
the **uncapped** list. Same signal, different trade populations, different
gate results.

## What I gated

**Spec 1.** The 3-of-7 result, the five fired kill conditions, the
−0.0012% gross and the K2 finding that ARM F does not generalise are all
measurements of spec 1. They are not wrong, but they are not spec 2.

## Resolved — and what spec 2 is worth

Spec 2 was a deliberate side test with **memory open**, not a second
attempt at the controlled run. That makes it a different thing entirely:
ARM G proper saw three briefing files and nothing else, while spec 2 also
saw the user's stored profile, the trading-research notes and the channel
file -- so it knew what the channel is for.

**It is not comparable to ARM G and will not be scored as an arm.** It is
worth one observation, though, and the observation is free: two informed
runs of the same material produced materially different specifications --
different volatility estimator, different trend timing, different hold,
different stop, and a different view of whether gates score the capped or
uncapped book. Same briefing, same model, one extra information channel.

If it is ever gated it is reported as "ARM G-mem, side test, memory open,
unregistered" and never alongside the seven arms as though it were one.

## The questions this raised, now answered

Spec 2's header says:

> "Written 2026-11-07, from EP04_BRIEF.md, PROGRAMME.md and REGISTRY.md
> only. No price data was looked at. `ARM_G.md`, `ARM_G_SCORED.md` and
> `PREREGISTRATION.md` in this folder were deliberately not opened."

`ARM_G_SCORED.md` did not exist until I wrote it on 2026-11-07, so spec 2
was produced **after** spec 1 was scored, in a session that could see the
folder. It declares that it did not read the scoring, which is the right
thing to declare and is not verifiable from here.

So, three questions:

1. **Was spec 2 a second, separate run of the same prompt** — in which case
   it is a replication and both get gated and reported, which is a better
   outcome than either alone?
2. **Or a continuation of the first chat** — in which case it is a revision
   produced after the author saw its own first attempt, and that has to be
   labelled as iteration, not as an independent informed run.
3. **Or a different prompt** — in which case it is a different arm.

## Why this cannot be resolved by picking one

Picking the spec that produces the more interesting result, after seeing
both, is the exact move this project exists to attack. Whichever is ARM G,
the other is either a replication or an iteration, and it is reported as
what it is.

## What else came with spec 2

A **Pine script**, `arm_g_trend_side_reversal.pine`, 172 lines, v6. It is
honest about its own limits in the header — one instrument per chart so the
portfolio rule cannot apply, and costs charged in a table rather than taken
out of Strategy Tester P&L. That is the first Pine script in the project and
preregistration section 5b commits to one per strategy, so it is wanted
either way.
