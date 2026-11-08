# Findings — SPX500 Multi-Factor Strategy

VERDICT: FAILS — closed. Cleared the gross bar on one of four windows (2018-2022, PF 1.090) then failed the cost condition: break-even 0.15 points/fill against a measured 0.25.

**Registration:** `PREREGISTRATION_MULTIFACTOR.md` (2026-10-01)
**Code:** `multifactor.py` — port of the Pine source, four risk-block bugs fixed
**Outcome: CLOSED.** Cleared the gross bar on one of four windows, then failed
the cost condition. Break-even 0.15 points/fill against a measured 0.25.

---

## 1. The four bugs in the Pine source

Found by audit, each fixed in the port and each reproducible via `bug_compat`
so its cost is measured rather than asserted.

| # | bug | why it bit |
|---|---|---|
| 1 | **Shorts had no hard stop when `useTrailing` was on.** The long branch passed `stop=longStop`; the short branch passed only `limit` and the trail. | `useTrailing` defaults true, and a trail cannot arm until the trade is already profitable. Every short that went against you from the open had nothing beneath it. |
| 2 | **`trail_points`/`trail_offset` are in TICKS, not price.** The script passed `atr * trailATR`, a price quantity. | At SPX500's 0.1 mintick a 50-point intended trail became 50 ticks = 5.0 points. **~10x too tight.** |
| 3 | **The stop floated with current ATR.** `longStop = position_avg_price - atr*stopATR` was recomputed every bar and re-issued. | The stop *widened* as volatility expanded — it retreated as the trade went against you. The port captures ATR once on the entry bar. |
| 4 | **Slippage under-charged.** `slippage=1` is one tick = 0.1 points. | Measured OANDA SPX500 spread is 0.50 round trip, **0.25 per fill** — 2.5x what was charged. |

### What they cost, measured

SPX500 15m, 2024-01..2026-08, 0.25/fill + 0.01% commission:

| variant | trades | net% | Sharpe | PF |
|---|---|---|---|---|
| all four fixed | 4,142 | −8.0 | −4.55 | 0.76 |
| bug 1 only (shorts unprotected) | 4,046 | −8.6 | −4.76 | 0.73 |
| bug 3 only (floating stop) | 4,336 | −7.4 | −4.17 | 0.80 |
| bug 2 only (trail in ticks) | 5,170 | −8.0 | −6.31 | 0.73 |
| **all four — the Pine as written** | 5,083 | −8.6 | **−6.52** | 0.69 |

**The bugs cost 1.97 Sharpe** (−6.52 → −4.55) and 0.07 PF. Bug 2 is the
expensive one, and the exit mix shows why:

| | stop exits | limit exits |
|---|---|---|
| fixed | 970 | **553** |
| as written | **2,768** | **56** |

The 10x-tight trail fires stops 2.9x more often and reaches the 4-ATR target
**56 times instead of 553** — a 90% reduction. Positions were strangled before
they could reach profit. That is the trailing-stop problem, quantified.

**Why it was invisible on the chart:** the reversal exit closes **62-65% of
trades in every window tested**. Most positions never reach a stop at all, so
the broken geometry only showed up as a vague sense that the trailing stop was
wrong rather than as an obvious failure.

---

## 2. The registered test — nothing fitted, so every window is out-of-sample

Author's default parameters, four bugs fixed. Primary measure gross PF.

| window | bars | trades | **gross PF** | gross% | net PF | net% | rev exits |
|---|---|---|---|---|---|---|---|
| 2005-01..2008-12 | 88,888 | 6,643 | 1.001 | 0.0 | 0.600 | −30.3 | 65% |
| 2009-01..2018-10 | 225,973 | 15,606 | 1.036 | +4.0 | 0.647 | −49.0 | 62% |
| **2018-10..2022-12** | 99,568 | 6,602 | **1.090** | +5.1 | 0.856 | −13.9 | 62% |
| 2023-01..2026-08 * | 85,437 | 5,588 | 0.995 | −0.1 | 0.779 | −11.1 | 63% |

\* overlaps the §1 diagnostic runs — flagged as the weakest evidence, reported
anyway rather than dropped.

**Condition 1 did NOT fire.** 2018-2022 cleared gross PF 1.05, against a
registered prediction that all four would fail. That prediction was wrong.

**Condition 3 fired instead.** A gross pass must also clear net PF 1.0 at
0.25/fill; that window gets **0.856**. Cost sweep on it:

| slippage/fill | PF | net% |
|---|---|---|
| 0.00 | 1.090 | +5.1 |
| 0.06 | 1.053 | +3.0 |
| 0.10 | 1.029 | +1.7 |
| **0.15** | **0.999** | **−0.0** ← break-even |
| **0.25** | 0.943 | −3.5 ← measured OANDA |

**Break-even 0.15 points/fill. Available 0.25.** It needs a spread 1.7x tighter
than the broker quotes. Closed.

---

## 3. Predictions scored honestly

| # | prediction | outcome |
|---|---|---|
| 1 | fails gross on all four windows | **WRONG** — 2018-2022 cleared 1.090 |
| 2 | 2009-2018 is least-bad | **WRONG** — it was third of four; 2018-2022 was best |
| 3 | 2005-2008 is worst | **roughly right** — 1.001, though recent was marginally lower at 0.995 |
| 4 | reversal exit closes the majority in every window | **RIGHT** — 62-65%, all four |

Two of four wrong. The diagnostics in §1 of the registration anchored
predictions 1 and 2 on a single recent window, and a single window did not
generalise — which is the same lesson this tree has recorded before (standing
rule 7, and the IS/OOS correlation of −0.18 measured in `adaptive/`).

---

## 4. What this adds to the programme

**Standing rule 6 again: costs are the killer, not absence.** The gross edge was
real but tiny — PF 1.09 at best, and that on the single most volatility-rich
window of the four (2020 and 2022). It needed a spread 1.7x tighter than exists.
This now joins family O in pineport (break-even 2.36 bp/side) and four-for-four
in fastbot.

**A new note worth carrying: an exit rule can hide a broken stop.** The reversal
exit closed ~63% of trades, which meant three genuine risk-management bugs —
including shorts running with no stop at all — produced no obvious symptom on a
TradingView chart. The bugs were found by reading the source, not by looking at
results. Had the trailing stop been the only exit, bug 1 would have been obvious
within a dozen trades.

**And: fixing bugs is not the same as finding an edge.** The four fixes were
worth 1.97 Sharpe, a large improvement, on a strategy that remained firmly
negative. Worth remembering the next time a fix produces a big relative gain.

---

## 5. Not reopened

Per registration §6, this is not pursued by fitting parameters on these windows,
by selecting the 2018-2022 window, or by moving to 5m/1h/4h because 15m failed.
The entry threshold and the reversal exit were already swept (best cell gross PF
0.98 on the recent window); standing rule 2 applies.

*Not financial advice. Measurement, not recommendation.*
