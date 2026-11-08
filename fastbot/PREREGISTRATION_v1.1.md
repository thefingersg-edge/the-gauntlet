# Pre-registration v1.1 — arithmetic correction to v1

```
WRITTEN:   2026-08-17, same day as v1
STATUS:    CORRECTION. Still frozen. STILL NO BACKTEST HAS BEEN RUN.
AMENDS:    PREREGISTRATION_v1.md sections 7 (Gate A, Gate B)
UNCHANGED: hypothesis, instrument, sample, split, signal, parameters,
           execution model, nulls, secondaries, limitations
```

> **This is not a design change and it is not a response to a result.** No P&L
> has been computed on this data. The error was found while writing the engine
> — the formula had to be coded, and coding it exposed it.
>
> **The correction makes the test harder, in every cell of the table.** An
> error corrected before any run, in the direction that raises the bar, is the
> one kind that cannot be self-serving. Recorded here rather than quietly
> fixed, because a silently-corrected number is indistinguishable from a
> tuned one.

---

## 1. What was wrong

v1's hurdle came from `REGIME_FINDINGS.md`, which computed the cost drag as:

```
WRONG:   drag = (round trips per year x spread) / annualised SESSION volatility
```

That divides the strategy's cost by **the asset's** volatility over the whole
session. It is only correct for a bot in the market every minute of every
session. This bot holds 30 minutes, 4 times a day, inside a 7-hour session —
it is exposed roughly **2 hours of 7**, so its own volatility is far below the
session's, and the drag was divided by a number ~1.9× too large.

The correct decomposition, which is just algebra:

```
net SR = (g - c)/s * sqrt(T) = gross SR - (c/s) * sqrt(T)

  g = gross return per trade      c = cost per trade
  s = per-trade return sd         T = trades per year

and  c/s  IS cost/vol at the hold, so

RIGHT:   drag = cost/vol(H) x sqrt(trades per year)
```

The wrong version also made drag scale **linearly** in trade count. It does
not: more trades buy more cost *and* more exposure together, so drag grows as
`sqrt(N)`.

**silver15 already had this right.** `FINDINGS.md` states plainly: *"Cost drag
adds on top and scales as `sqrt(trades per year)`."* So did the first version
of `interval_budget.py`, before a later edit replaced it with the linear form.
The correct answer was written down in this project twice and overwritten.

## 2. The corrected numbers

Session 09:00–16:00 America/New_York, 2019+ regime: spread 0.436bp, vol
3.59bp/min, hold 30 minutes → **cost/vol(30m) = 0.0222**.

| round trips/day | drag | required GROSS, fit (7.0y) | required GROSS, holdout (5.6y) |
|---|---|---|---|
| 1 | 0.35 | 1.11 | 1.20 |
| 2 | 0.50 | 1.25 | 1.34 |
| **4** | **0.70** | **1.46** | **1.55** |
| 6 | 0.86 | 1.62 | 1.71 |
| 12 | 1.22 | 1.98 | 2.06 |

Against v1's table, which gave 0.94 at 4 round trips/day on the full sample.
**The requirement rose by roughly 60%.**

Note the drag now *falls* with fewer trades much more slowly than v1 implied
(`sqrt` not linear), so trading less often buys less relief than v1 suggested.
Conversely a **longer hold** is now the effective lever: drag scales as
`1/sqrt(H)` at fixed trade count.

## 3. What this changes in v1 §7

**Both gates are restated on NET Sharpe.** The engine charges the actual
per-bar spread, so net is what it produces; testing net directly removes the
gross/drag decomposition from the gate entirely and with it this whole class
of error. The drag table above becomes context, not a threshold.

### Gate A — replaces v1 §7 Gate A

```
WAS:  PROCEED only if GROSS Sharpe >= 0.94 on 2014-2020
NOW:  PROCEED only if NET   Sharpe >= 0.76 on 2014-2020    (= 2/sqrt(7.0))
      AND >= 200 non-overlapping trades
      AND realised round trips <= 4/day
```

Net 0.76 on the fit window corresponds to gross ~1.46 at 4 round trips/day —
harder than v1's gross 0.94, which is the point.

**Unchanged: if Gate A fails, the project stops.** No retuning, no v2 with
different N/k/H. The holdout stays sealed.

### Gate B — v1 §7 criterion 1 is unchanged

```
NET Sharpe >= 0.85 on 2021-2026     (= 2/sqrt(5.6))
```

This was always the detectability bar and the detectability bar is untouched
by the cost error. **Criteria 2–5 of v1 Gate B stand exactly as written.**

## 4. Does the strategy still clear its own budget?

Honestly: this is now a demanding target. Net Sharpe 0.85 on a single
instrument, out of sample, is a good systematic strategy — not a spectacular
one, but not a gimme either. At 4 round trips a day it requires gross 1.55.

Two things are worth stating before the run rather than after:

- **The `H` lever is real and is already declared.** Drag falls as `1/sqrt(H)`,
  so the declared secondary `H = 12` (60 minutes) halves the drag term to 0.50
  at the same trade count. It remains a **declared secondary** and cannot
  become the primary — v1 §5 already binds: *"If H=6 fails and H=12 passes,
  the strategy has failed."* That clause was written before this correction
  and is exactly what stops the correction being used to reach for a better
  parameter.
- **If the corrected bar is not clearable, that is a finding**, and it is the
  same finding silver15 reached eleven times. It would be reached here in four
  days rather than eleven attempts, which is the tooling working.

## 5. Also corrected

`interval_budget.py` — `cost_sharpe()` restored to the `sqrt` form, with a
self-test that now asserts the scaling explicitly:

```
[PASS] cost Sharpe scales as SQRT of trade count, not linearly   4x the trades is 2x the drag
[PASS] drag is cost/vol times sqrt(trades)
[PASS] a longer hold lowers the drag at equal trade count
```

There was no such assertion before, which is why an edit could silently
replace the formula with a wrong one and every test still passed. **A property
that is never asserted is not protected** — the same lesson as a gate never
observed to fail, arriving through a different door.

`REGIME_FINDINGS.md` §3 is superseded by the table in §2 above.

---

```
FROZEN 2026-08-17. Corrected before any P&L was computed on this data.
```
