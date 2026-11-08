# Findings — SPX500 5m / 1h / 4h retrained with holdouts

VERDICT: FAILS — all three arms (H4, H1, M5) fail their holdout kill conditions. Stop all three live SPX500 strategies. H4 additionally shown not economic after carry, see FINDINGS_SPX500_H4_CARRY.md.

**Registration:** `PREREGISTRATION_SPX500_timeframes.md` (2026-09-27)
**Scored:** 2026-10-02 by `score_holdouts.py`, which applies the five kill
conditions literally so the verdict is arithmetic rather than judgement.
**Decision this informs:** whether to stop three live SPX500 strategies.

| arm | stages accepted | verdict | conditions fired |
|---|---|---|---|
| H4 | 1 of 6 (`bands`) | **FAILS** | 1, 4 |
| H1 | **0 of 6** | **FAILS** | 1, 2, 4, 5 |
| M5 | 2 of 6 (`bands`, `stops`) | **FAILS** | 1, 4, 5 |
| *M15* | *1 of 6* | *failed (control, 2026-09)* | *1* |

**All three arms scored; all three fail.** M5 was first recorded here as
not yet run. That was wrong: it finished on 2026-09-28 as the last arm of
`tf.log`, and was scored later the same day (2026-10-02) — see §4.

---

## 1. Data vintage — fixed before scoring

On 2026-10-01 the four SPX500 files ended seven weeks apart (h1 and h4 at
7 Aug, m15 14 Aug, m5 25 Sep). Training timeframes across that would read a
vintage difference as a timeframe difference — standing rule 5. All four were
refreshed to **2026-10-02** by `pull_data.sh` and verified by `verify_feed.py`
before any scoring here.

The H1 and H4 training runs predate the refresh. They remain valid because the
refresh only *appended* rows after 7 Aug 2026, leaving the 2009–2022 training
window byte-identical, and the holdout windows are sliced with explicit end
bounds.

**Spreads re-measured on the fresh data confirm the registered cost:** SPX500
median daily spread 0.50 over the last five years, **0.25 per fill**. Pre-2011
is backfilled at bid = ask, which is why condition 4 stresses the pre-holdout at
1.00.

---

## 2. H4 — fails conditions 1 and 4

| window | bars | trades | Sharpe | net% | maxDD% | B&H dd% | break-even |
|---|---|---|---|---|---|---|---|
| 2005-2008 | 6,146 | 59 | **0.53** | +5.4 | −2.7 | −68.1 | 2.508 |
| ↳ at 1.00/fill | | 59 | **0.36** | +3.6 | −2.8 | | |
| 2023-2026 | 5,586 | 53 | 1.31 | +63.2 | −13.6 | −33.1 | 3.000 |

- **Condition 1 FAILED** — 2005-2008 Sharpe 0.53 against a 0.8 bar.
- **Condition 4 FAILED** — at 1.00/fill the pre-holdout Sharpe drops to 0.36.
- Conditions 2, 3, 5 passed.

**This is the closest thing to a positive result in the arm set, and it still
fails.** It is profitable on *both* holdouts, trades enough to be measured, and
the post-2023 window is genuinely strong: Sharpe 1.31, +63.2%, break-even 3.0
points against a 0.25 cost.

### Correction (2026-10-10): the "crash protection" is absence, not skill

This section first said the −2.7% drawdown against buy-and-hold's −68.1% meant
it "protects extremely well", and §6 called that "protecting 25x better than
the index". **Both claims were wrong, and were made without measuring
exposure.** The measurement:

| window | trades | exposure | shorts | short exposure |
|---|---|---|---|---|
| 2005-2008 | 59 | 50.9% | 12 | 1.7% |
| **2008 alone** | **8** | **8.6%** | **0** | **0.0%** |
| 2023-2026 | 53 | 51.5% | 13 | 2.0% |

Through the crash itself (2007-10 .. 2009-03, index −56% at worst) it was in
the market **12.2% of bars**, took **one** short trade worth 0.2% of bars, and
its longs lost −3,777 while its shorts made +146. In 2008 it took eight trades,
**all long**, and was out of the market 91% of the time.

So the small drawdown is **non-participation**, not downside skill. Its entry
conditions simply stopped firing — normal exposure is ~51% of bars and it fell
to 12%. Whether that fall *leads* the decline (market timing) or merely
coincides with it (stop-outs) has not been measured and is not established by
anything here.

The lesson is the one standing rule 4 states: a drawdown comparison is not a
measurement of protection. Exposure is, and it was one query away.

The failure is specific: in 2005-2008 it earns a positive return with a poor
risk-adjusted ratio, and that ratio is what was pre-registered. Picking the
post window, or relaxing the bar to 0.5, would turn this into a pass — which is
exactly what §6 forbids and exactly why the bar was written down first.

**Registered prediction 4 was "at least one arm shows a positive full-history
number while failing its holdout". H4 is that arm**, in a sharper form than
predicted: it is positive on the holdouts themselves and still fails.

---

## 3. H1 — fails conditions 1, 2, 4 and 5, and is not a measurement

| window | bars | trades | Sharpe | net% | maxDD% | B&H dd% | break-even |
|---|---|---|---|---|---|---|---|
| 2005-2008 | 24,185 | **20** | −0.12 | −0.8 | −2.5 | −68.7 | **0.000** |
| ↳ at 1.00/fill | | 20 | −0.21 | −1.4 | −2.7 | | |
| 2023-2026 | 21,369 | **6** | 0.54 | +15.5 | −11.4 | −34.3 | 3.000 |

**Training accepted zero of six stages**, so this is the untrained base
config. Nothing the search tried improved the unseen validation slice under
4-seed consensus.

**Condition 2 is the one that matters: 20 trades and 6 trades.** Below the
registered 30-trade floor, a Sharpe is not a measurement, so the −0.12 and the
+0.54 should not be read as performance at all. The +15.5% on six trades is
noise with a sign.

The honest statement is not "H1 performed badly" but **"the H1 arm produced no
usable configuration"** — the structure at this timeframe, with these triggers,
barely fires. That is a more useful finding than a bad Sharpe would have been.

---

## 4. M5 — fails conditions 1, 4 and 5, on signal rather than cost

**It had already run.** This section first said "not run". In fact the M5 arm
finished on **2026-09-28 11:58** as the third arm of the full
`bash runlog.sh tf.log bash run_spx500_tf.sh` run (`tf.log.DONE`; six stages,
1,656–2,560 s each, ~3.3 h). The `m5_staged.log` written 2026-10-02 08:22 is a
re-invocation that resumed from `state.json`, found all six stages done, and
exited. No `m5.log` exists. Nothing was re-trained.

**Still valid after the data refresh.** The M5 pull of 2026-10-02 was a resume
from 2026-09-25 20:55 (1,469,822 rows kept), so it only appended bars and the
2009-2022 training window is unchanged (952,543 bars, the same count training
reported). `configs/spx500_M5_base.json` is unchanged since 2026-09-28 08:40.

Training: `sma`, `rsi`, `squeeze`, `ladder` rejected (0–1 of 4 seeds);
**`bands` accepted** (3/4, validation Calmar −0.04 → 0.35) and **`stops`
accepted** (3/4, 0.35 → 0.50; validation Sharpe 0.91, 69 trades).

| window | bars | trades | Sharpe | net% | maxDD% | B&H dd% | break-even |
|---|---|---|---|---|---|---|---|
| 2005-2008 | 252,998 | 69 | **−0.06** | −1.2 | −15.6 | −69.2 | **0.000** |
| ↳ at 1.00/fill | | 69 | **−0.19** | −3.4 | −16.8 | | |
| 2023-2026 | 256,049 | 39 | 0.89 | +54.5 | −38.1 | −34.5 | ≥3.000 |

(Break-even is bisected up to 3.0, so 3.000 means "at least 3.0".)

- **Condition 1 FAILED** — 2005-2008 Sharpe −0.06 against a 0.8 bar. The post
  window clears it (0.89).
- **Condition 4 FAILED** — at 1.00/fill the pre-holdout is −0.19, −3.4%.
- **Condition 5 FAILED** — 2005-2008 break-even 0.000: **it loses money before
  any cost is charged.**
- Conditions 2 (69 and 39 trades) and 3 (−15.6% vs B&H −69.2%) passed.

It is the same shape as H4, in a weaker form: good on the post window, and
the pre window — the one with the crash — kills it. Two things to notice
about the post window, neither a reason to treat it as a pass: its drawdown of
−38.1% is *worse* than buy-and-hold's −34.5% over the same period (condition 3
is registered on 2005-2008 only, so this does not fire, but it does not look
like a protective strategy); and 39 trades is barely above the 30-trade floor.

**Registered prediction 2 — "5m fails hardest, and on costs as well as
signal" — is WRONG on both halves.**

- *Not hardest.* M5 fires three conditions; H1 fires four and produced no
  usable configuration at all. M5 trades enough to be measured (69 / 39) and
  is positive on one holdout. By number of conditions and by usefulness of the
  result, H1 failed harder. M5 sits in the middle, between H4 and H1.
- *Not on costs.* M5 dies on signal. The pre window loses gross (break-even
  0.000), so conditions 4 and 5 fire because of the sign of the gross return,
  not because of the spread. Where M5 *is* gross-positive (post), its
  break-even is ≥3.0 points, more than 12x the 0.25 cost. The reasoning
  carried over from gold M5's 1.38x cost margin did not transfer: the stops
  stage accepted ~3–6% stops, so the trained M5 config holds through moves far
  larger than the spread, and cost is not what binds.

---

## 5. Predictions scored

| # | prediction | outcome |
|---|---|---|
| 1 | all three fail condition 1 | **RIGHT** — H4 0.53, H1 −0.12, M5 −0.06 on 2005-2008 |
| 2 | 5m fails hardest, on costs as well as signal | **WRONG** — H1 failed harder, and M5 fails on signal (gross loss pre-2009), not cost (§4) |
| 3 | 4h comes closest | **RIGHT** — H4 is the strongest of the three |
| 4 | at least one arm is positive while failing its holdout | **RIGHT** — H4, and more sharply than predicted |

Prediction 3 held for the reason given when it was written: longer holds, fewer
trades, more edge per trade against a fixed spread. H4's break-even is 2.5-3.0
points against a 0.25 cost — a 10x margin — where H1's pre-holdout break-even is
0.000 because it loses money gross.

---

## 6. What this means for the live strategies

Per registration §1, these arms test the **structure**, not the live parameter
values, which were fitted on full history and cannot be validated at all.

- **H1 live: stop.** The structure produced no configuration, and six trades in
  nearly four years means the live config's apparent record cannot be
  distinguished from noise either.
- **H4 live: stop as registered.** It failed a pre-registered risk-adjusted bar
  in one window while clearing a 10x spread margin. The "crash protection" that
  first made this look worth revisiting does not exist — see the correction in
  §2 — so the crash-protection registration floated here has been dropped
  rather than written.

  What IS open is a cost question the registration never asked. Spread is not
  the only charge: this holds a CFD position **50.9% of the time at a
  time-weighted financed notional of 0.138x equity** in the pre window and
  **0.614x** in the post window, for a median 21-32 bars (3.5-5.3 days) per
  trade. Financing has never been priced here, and the pre window earns only
  **+1.32%/yr** — gold 15m died at exactly this step (break-even carry 4.35%,
  worse than cash). Registered as `PREREGISTRATION_SPX500_H4_CARRY.md`.
- **M5 live: stop.** The structure, fitted honestly, loses money gross across
  2005-2008, so the live 5m values have nothing behind them. Its post-2023
  Sharpe of 0.89 comes with a drawdown worse than holding the index.

What is **not** permitted: selecting H4's or M5's post-2023 window, relaxing
the Sharpe bar, or adding a filter to rescue any arm (§6, and standing rule 2).

---

## 7. Added to the programme record

The H4 result sharpens a pattern this tree keeps producing. Twelve directional
families in pineport, four effects in fastbot and now three SPX500 timeframes all
died on the same shape: **the effect is real enough to see and too small to
clear a bar set in advance.** H4 is the cleanest example yet, because it is
profitable on both holdouts and still fails — the bar did its job precisely
because it was written down before the number was known.

**A second lesson, from the correction in §2, worth carrying further than this
file.** The claim that H4 "protects 25x better than the index in a crash" was
derived from two drawdown numbers and survived into a findings document and a
recommendation to open a new registration. It took one exposure query to show
the strategy was simply absent — 8.6% exposure in 2008, zero shorts. Standing
rule 7 says reopen the source before restating a verdict; this is the same
failure one level down: **a ratio of two summary statistics is not a
measurement of the mechanism it appears to describe.** Before a comparison
becomes a property ("it protects", "it times", "it hedges"), the thing doing
the protecting has to be measured directly.

*Not financial advice. Measurement, not recommendation.*
