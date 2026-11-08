# PREREGISTRATION FORWARD_NQ_STOP — the same NQ forward record, with a fixed 0.5% stop

```
WRITTEN:   2026-10-11, before the first FORWARD_NQ session (2026-10-12). Frozen at its first
           commit; forward_nq.py pins its sha256.
FROM:      stops_nq.py (descriptive, commit 0b09a15): on NQ 2013-01..2026-08, a FIXED stop at
           0.5% of the entry price raised the profit factor from 1.239 to 1.275 (1.044->1.061,
           1.345->1.379, 1.311->1.368 by era) and net from +5.76 to +6.42 bp per trade-session.
           It was the best of 28 settings looked at (paired t +1.80), so it is a lead, not a
           result. Trailing stops lowered the profit factor at every width.
STATUS:    RECORDS ONLY. Paper. No order is placed, and no broker account is touched.
           FORWARD_NQ (the rule without a stop) is unchanged and keeps its own verdict.
```

*Measurement, not a recommendation. Not financial advice.*

## 1. What is recorded

Everything in PREREGISTRATION_FORWARD_NQ.md §1 (rule N unchanged, NQ.v.0
1-minute bars from Databento, 5-minute construction, costs, roll handling,
first session 2026-10-12, one row per session written once), plus one
addition:

- **Stop:** when a trade is filled, a stop is set at **0.5% of the fill
  price** below a long or above a short. It never moves.
- It is checked on every 5-minute bar while the trade is open, starting
  with the entry bar. It is hit when the bar's low (for a long) or high (for
  a short) reaches it.
- It fills at the stop level, or at the bar's open if the price gapped
  through, with one tick against the trader, as on every fill.
- After a stop the rule may re-enter at a later checkpoint, exactly as after
  its own exit.
- The code is `nq_stop_rule.py`, `fixed-pct` with D = 0.5. It must reproduce
  stops_nq.py's `fixed-pct 0.5%` line exactly on 2013–2026 history (§4).
- Ledger: `data/forward_nq_stop.csv`, with the same columns as the base plus
  `stops_hit`.

## 2. Evaluation, fixed now

**Its own verdict** uses the same gates and timing as the base: one
evaluation at its 500th trade-session, F1 (mean net > 0, t ≥ 1.65) ∧ F2 (mean
net ≥ +2.0 bp). There is one interim kill at 250 (mean net ≤ −2 bp).

**The comparison with the base** (the question that motivated this) is
**S1**, judged at the base's 500th trade-session:

| gate | pass |
|---|---|
| **S1a** | profit factor with the stop > profit factor without, over the same sessions |
| **S1b** | mean of (stop − base) per session > 0 |

S1 is stated as **underpowered**, and that is fixed now. In the backtest the
session-by-session difference has an SD of about 16 bp. Over 500
trade-sessions that is a standard error of about 0.7 bp against a hoped-for
+0.66 bp improvement, so S1 is a sign test, not proof. A PASS on S1 makes
the stop worth keeping in mind. It does not make it proven. A FAIL closes
the stop question.

## 3. Reports

The amendment A1 schedule applies: every 50 trade-sessions of this ledger,
a descriptive report goes to `data/forward_nq_reports/stop_report_NNN.md`.
It shows the same figures as the base reports, plus the side-by-side profit
factors and the running (stop − base) difference on shared sessions.
Reports gate nothing.

## 4. Before the first session

`forward_nq.py --self-test` must show:

1. the base checks still pass;
2. `nq_stop_rule.py` with no stop reproduces `momentum_v36.noise_rows`
   exactly;
3. with the 0.5% fixed stop it reproduces stops_nq.py's 2013–2026 figures:
   trades 3,374, profit factor 1.275, +6.42 bp per session.

## 5. Nothing changes

No change to the stop (its size, type or fill), the rule, the costs or the
dates. A change means a new document with a new start date.
