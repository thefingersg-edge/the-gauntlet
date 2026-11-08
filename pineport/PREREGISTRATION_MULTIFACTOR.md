# Pre-registration — SPX500 Multi-Factor Strategy, bugs fixed

**Registered:** 2026-10-01, before any window below is scored.
**Subject:** a NEW strategy structure, ported to `multifactor.py`. Not a member
of the RSI/Bollinger/squeeze family in `strategy.py`, and not a reopening of
anything. Six factors vote; a weighted score crossing a threshold enters; a
stop/target/trailing bracket manages the position.

---

## 1. What has already been run, and why it is not the result

Before this registration, three diagnostic runs were made on 2024-01..2026-08
(61,874 bars) to characterise the port and verify it against the Pine source:

1. **Cost sensitivity** — gross, 0.25/fill, +0.01% commission, and Pine's 0.1/fill.
2. **Entry threshold x reversal exit** — 3 x 2 grid.
3. **Bug attribution** — the four Pine bugs reproduced one at a time via
   `bug_compat`, to price each rather than assert it.

These are **debugging and attribution, not a verdict**. They were run on a
single recent window at author-default parameters, and they are reported in
`FINDINGS_MULTIFACTOR.md` labelled as such. They are disclosed here because
registering after looking is only honest if what was already seen is stated.

**What they showed, recorded now so this registration cannot be read as naive:**
gross profit factor was 0.95 at defaults and did not exceed 0.98 in any of the
six threshold/reversal cells. That is the basis for prediction 1 below.

---

## 2. The question

> Does this structure, at the author's parameters with the four risk-block bugs
> fixed, produce a positive **gross** profit factor on SPX500 15m on any window
> of the available history?

**Gross, deliberately.** Costs are the usual killer in this tree (standing rule
6), but a structure that cannot clear PF 1.0 before costs cannot be rescued by
better execution, a cheaper venue, or a lower trade rate. Asking the gross
question first makes the answer unambiguous: if gross fails, the strategy is
dead and no cost work is warranted; if gross passes, costs become the next test
rather than a confound.

**No parameters are fitted in this test.** The config is the Pine author's
defaults. That has a useful consequence: with nothing fitted, *every* window is
out-of-sample, so all four are scored and none is privileged. This is not a
training run and must not become one — see §6.

---

## 3. Windows — all four scored, all four reported

| window | bars | role |
|---|---|---|
| 2005-01 .. 2008-12 | | includes the 2008 crash |
| 2009-01 .. 2018-10 | | the long bull |
| 2018-10 .. 2022-12 | | includes 2020 and 2022 |
| 2023-01 .. 2026-08 | | recent; the diagnostic window is inside this |

Same boundaries as `PREREGISTRATION_SPX500_timeframes.md` §3, so the result is
comparable with the 15m staged run rather than sitting on its own grid.

The fourth window **overlaps the diagnostics in §1** and is therefore the weakest
evidence here. It is scored and reported anyway, flagged, rather than quietly
dropped — dropping it would be selecting windows on what has been seen.

---

## 4. Costs

Gross is the primary measure (§2). Each window is **also** reported at the
measured **0.25 points per fill** plus 0.01% commission, for the record.

2005-2011 OANDA spreads are backfilled at bid = ask, so the cost figure on the
first window is a floor, not a measurement. The gross primary is unaffected.

---

## 5. Kill conditions — fixed before scoring

The strategy **fails, and is closed**, if:

1. **Gross profit factor < 1.05 on every one of the four windows.** 1.00 is not
   the bar: a structure that only breaks even gross has no room for the 0.25/fill
   that trading it would cost.
2. **Fewer than 100 trades in a window** makes that window's figure
   uninformative; it is reported as such and cannot be cited as a pass.
3. **Any window that passes gross must also beat PF 1.0 net at 0.25/fill** to
   count as a live candidate. A gross-only pass is a research note, not a
   strategy.

It **passes to the next stage** — proper staged training with holdouts under its
own registration — only if at least one window clears both 1 and 3 with >= 100
trades.

---

## 6. What is NOT permitted afterwards

- **Fitting parameters on these windows and reporting the result as this test.**
  If it passes, the training run is a new registration with its own holdouts.
- **Selecting the best window.** The conclusion is taken across all four.
- **A fifth window, or a different timeframe, added after seeing these.** If 15m
  fails, the honest statement is "this structure failed on SPX500 15m", not a
  hunt through 5m and 4h for one that works. Another timeframe needs its own
  registration written before it is run, with a stated reason that is not "15m
  failed".
- **Reopening via the entry threshold or the weights.** Those were swept in the
  diagnostics (§1) and the best cell was PF 0.98 gross. Standing rule 2.

---

## 7. Predictions, recorded before scoring

1. **It fails condition 1 on all four windows.** Gross PF was 0.95 at defaults
   and peaked at 0.98 across the threshold grid on the recent window. The
   diagnostics already make this the expected outcome, which is why they are
   disclosed in §1 rather than presented as independent support.
2. **2009-2018 is the least-bad window**, because a long-only-biased trend vote
   in a sustained bull market is the one regime this factor mix is aligned with.
3. **2005-2008 is the worst**, on whipsaw plus the backfilled-spread floor.
4. **The reversal exit closes the majority of trades in every window**, as it did
   at 63% in the diagnostics. That is the structural reason the stop and target
   geometry barely matters, and the reason the trailing-stop bug was invisible in
   TradingView: most positions never reached a stop at all.

If prediction 1 is wrong, the result is interesting precisely because it would
contradict what the recent window showed, and the first response is to check the
data vintage on the passing window (standing rule 5) before believing it.

---

*Not financial advice. Measurement, not recommendation.*
