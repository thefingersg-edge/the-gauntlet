# Pre-registration — SPX500 5m / 1h / 4h, retrained with holdouts

**Registered:** 2026-09-27, before any arm runs.
**Decision this informs:** whether to stop three live SPX500 strategies.

---

## 1. Why retraining, not scoring the live configs

The live 5m, 1h and 4h strategies were each fitted on the **full history**.
There is therefore no window anywhere that can serve as a holdout for them, and
scoring their current values on 2005-2008 or 2023-2026 would be scoring them on
their own training data. Their reported performance cannot be checked.

So the question is not "are these parameter values good" — that is unanswerable
from the data that produced them. It is:

> Does this strategy STRUCTURE, fitted honestly with data held back, produce
> out-of-sample performance on SPX500 at 5m, 1h or 4h?

If it does not at a given timeframe, the live strategy there rests on values
chosen by fitting everything, and should stop. If it does, the retrained values
are the ones worth running, not the originals.

**The 15m case is the control.** It has already been through this exact
procedure and failed (holdout Sharpe -0.87 on 2005-2008). Its full-history
number was +155.6% net, PF 1.32 — a figure that looks like a working strategy
and is not one. That gap is the reason this registration exists.

---

## 2. Arms — three timeframes, all reported

| arm | timeframe | bars | status |
|---|---|---|---|
| 5m | `spx500usd_oanda_m5.csv` | to be fetched | **live** |
| 1h | `spx500usd_oanda_h1.csv` | 129,175 | **live** |
| 4h | `spx500usd_oanda_h4.csv` | 33,272 | **live** |
| *15m* | *already run* | *499,775* | *failed — control* |

**All three are reported whatever they show.** An arm that fails is reported as
failed; an arm that cannot run (missing data, too few trades) is reported as
such. No arm may be omitted, and the decision for each timeframe is taken on
that timeframe's own result.

---

## 3. Windows — identical across arms

| window | role |
|---|---|
| 2005-01 .. 2008-12 | **holdout (pre)** — contains the 2008 crash |
| 2009-01 .. 2018-10 | fit |
| 2018-10 .. 2022-12 | validation — accepts/rejects stages, never searched |
| 2023-01 .. 2026-08 | **holdout (post)** |

Same split as the 15m run, so results are comparable across timeframes rather
than each arm having its own convenient boundaries.

Method: `train_staged.py`, six stages, base from `make_base.py` with all
instrument-specific filters off, 4 seeds x 200 samples, stage accepted only if
a **majority of the four seeds** improves the unseen validation slice.

---

## 4. Costs

Measured, per `PREREGISTRATION_SPX500_15m.md` §6: **0.25 points per fill**
(half of the 0.50 median spread over the last five years).

2005-2011 spreads are backfilled at bid = ask, so the pre-holdout is scored at
both **0.25 and 1.00** per fill. Costs matter more at 5m than at 4h — a fixed
spread against a smaller per-trade move — and the 5m arm is the one most likely
to die on this rather than on signal.

---

## 5. Kill conditions — per arm, fixed before running

An arm **fails**, and the live strategy at that timeframe should stop, if any of:

1. **Sharpe < 0.8 on either holdout window**, at the measured spread.
2. **Fewer than 30 trades in either holdout window** — below that a Sharpe is
   not a measurement.
3. **Max drawdown worse than buy-and-hold on 2005-2008.** A strategy that does
   not protect in a crash has no reason to exist over holding the index.
4. **The 2005-2008 result does not survive 1.00/fill.** Passing only at a
   spread that did not exist in 2008 is not passing.
5. **Break-even spread below 0.25 points.**

An arm **passes** only if all five clear on **both** holdout windows.

---

## 6. Predictions, recorded before running

1. **All three fail condition 1.** The 15m failed, twelve directional families
   in `pineport/` failed, and nothing in this programme has yet produced a
   directional edge that survived a holdout.
2. **5m fails hardest, and on costs as well as signal.** On gold, M1 came in
   below break-even and M5 carried only a 1.38x margin.
3. **4h comes closest.** Longer holds, fewer trades, more edge per trade
   against a fixed spread — the relationship measured across gold timeframes.
4. **At least one arm shows a positive full-history number while failing its
   holdout**, as the 15m did. That is the specific trap this exists to catch.

If prediction 1 is wrong and an arm passes, it is not evidence the live
strategy is working — the live values were fitted on everything and are still
unvalidated. It would mean the structure is worth running with the RETRAINED
values.

---

## 7. Deliverable per arm

Whatever the outcome: a Pine v6 script from `make_pine.py`, carrying the fixes
the older scripts predate — `margin_long/short = 0` (the v6 default silently
rejects entries above equity), `max_bars_back` computed from the config rather
than left at 300, the `var`-captured entry close in place of a dynamic history
offset, the `strategy.opentrades` guard, scale-free percent ladder rungs, and
stop-distance sizing.

A failing arm still gets its script, clearly labelled with the holdout result
in the header, so the record shows what was tested rather than only what passed.
