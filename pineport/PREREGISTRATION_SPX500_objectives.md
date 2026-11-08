# Pre-registration — does the objective function change what survives?

**Registered:** 2026-09-27, before any arm runs.
**Subject:** the training harness, not the SPX500 strategy.

---

## 1. Why this is not a reopening

`PREREGISTRATION_SPX500_15m.md` §5 closed the SPX500 15m family: condition 1
failed (holdout Sharpe −0.87 on 2005–2008), and it is not to be reopened with a
filter, a seventh stage or a different objective.

This asks a different question, about the tool rather than the instrument:

> When stages are accepted by seed consensus on unseen validation data, does the
> choice of objective function change **which stages survive**?

It matters because every future run in this tree picks an objective, and that
choice has never been examined. If `net` and `calmar` accept different stages
from the same data, the objective is a free parameter nobody has been counting.

**The result of this study is the COMPARISON ACROSS ARMS.** No single arm's
performance is a result, and no arm may be quoted as evidence about the SPX500
strategy. If one arm produces an attractive-looking config, that is an
illustration of the problem, not a finding.

---

## 2. Arms — all four run, all four reported

| arm | objective | drawdown-aware? |
|---|---|---|
| A | `net` | no |
| B | `calmar` | yes (CAGR / maxDD) |
| C | `sharpe` | yes (via volatility) |
| D | `pf` | no |

`net` and `cagr` are monotonic transforms of one another over a fixed window
(documented in `train_tf.py`), so they rank candidates identically and `cagr`
is not run separately. Arm A stands for both.

Everything else is held identical: `spx500usd_oanda_m15.csv`, fit 2009-01 to
2018-10, validation 2018-10 to 2022-12, base `configs/spx500_clean_base.json`,
state triggers, 4 seeds x 200 samples, slippage 0.25, `min_trade_frac` 0.6.

**Reporting is unconditional.** All four arms are reported whatever they show.
An arm that crashes or accepts nothing is reported as such.

---

## 3. Predictions, recorded before running

1. **Arm A (net) accepts more stages than arm B (calmar).** Net ignores
   drawdown, so a candidate that raises return by taking more risk improves the
   metric. Calmar charges for it.
2. **Arm A produces the worst holdout drawdown of the four.** Same reason.
3. **The accepted-stage SETS differ across arms** — not merely the parameter
   values within a stage. This is the substantive prediction.
4. **No arm clears the original §4 conditions on both holdout windows.** If one
   does, that is a warning about objective-shopping, not a rescue of the family.

---

## 4. Kill conditions for the STUDY

The study is inconclusive, and says so, if:

1. **Fewer than 3 of 4 arms complete.** A partial comparison is not a comparison.
2. **All four arms accept the identical stage set.** Then the objective does not
   matter under consensus acceptance, prediction 3 is wrong, and that is the
   finding — a useful one, since it would mean the objective is not a free
   parameter after all.
3. **Any arm's result differs from a repeat at the same seed.** The harness must
   be deterministic before its outputs can be compared. Checked on arm B, which
   has already been run once at these settings: it must reproduce exactly.

---

## 5. What is NOT permitted afterwards

- Quoting any single arm as an SPX500 result.
- Selecting an objective because it produced the best holdout, then presenting
  that config as trained. The selection would be on the holdout.
- A fifth arm added after seeing the four.

If the study shows the objective changes what survives, the correct response is
to **fix an objective in advance for future pre-registrations and say why** —
not to pick the winner here.

---

## 6. Costs and data

Unchanged from `PREREGISTRATION_SPX500_15m.md` §6: slippage 0.25 points per
fill, the measured half-spread. 2005–2011 spreads are backfilled at bid = ask,
so the 2005–2008 holdout is scored at both 0.25 and 1.00 as before.
