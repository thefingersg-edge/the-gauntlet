# FORWARD TEST — how to operate it

```
SPEC      PREREGISTRATION_v25, amended by v25.1
STARTED   2026-09-19
FIRST     payrolls, 2026-10-02
RECORDS   it does not trade. Nothing here places an order.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## What it does, and how long it takes

Fades the 08:30 ET CPI and payrolls bar on six instruments — in at
08:45, out at 09:45, no stop — and records each one with real bid and
ask.

```
validate the execution model    ~5 months   (60 records)
confirm the GROSS effect        ~7 years
confirm it NET of cost          ~23 years
```

**It cannot tell you whether this makes money in any useful
timeframe.** That was known and registered before it started; v25 §1
has the arithmetic. It is running for the fast arm, for the chance the
effect dies visibly, and because the plain rule has never been run
forward.

## What runs

```
forward_tick.sh            every 6 hours via launchd
  1 calendar_forward.py    BLS schedule -> events_v3.csv
  2 pull_m1.py             OANDA M15 bid/ask -> data/v24  (resumes)
  3 forward_ledger.py      appends any new events -> forward_ledger.csv
```

Idempotent by design: the ledger only appends dates it has not seen, the
pull resumes from the last row on disk. Extra runs cost nothing, which
is why it runs on an interval rather than at a fixed hour.

## Checking on it

```
python3 forward_ledger.py --status      # what is recorded, what is next
cat ../data/forward_heartbeat.txt       # OK / HALT and when
tail -40 ../data/forward_tick.log
python3 verify_pull.py --data-dir ../data/v24
```

A heartbeat older than **7 days** is itself an abort condition (v25 §6).

## When it halts

| it says | what happened | do |
|---|---|---|
| `calendar_forward exit 3` | BLS unreachable | check the network; it must run in a real shell, the sandboxes are blocked |
| `calendar_forward exit 4` | two releases shared dates — page furniture parsed as releases | do not touch the calendar; read the diff first |
| `forward_ledger: calendar exhausted` | fewer than 2 future releases known | run `calendar_forward.py` |
| `pull_m1 failed` | OANDA or token | `pull_m1.py --check` |

**A runway warning under 90 days is not a halt.** v25.1 demoted it —
BLS publishes about a year ahead on a rolling basis, so the window is a
sawtooth and a fixed floor is unsatisfiable for part of every year.

## The rules that make it worth anything

- **History is never recomputed.** The ledger only appends, and every
  row carries the code version that wrote it. A bug fix applies forward;
  old rows stay and are marked.
- **Look on 31 January only**, and render no verdict. Stopping early
  needs |t| ≥ 3.5, far above the final 2.0, so nine annual peeks cost
  almost nothing.
- **Stopping because it looks good is forbidden.** The horizon is 271
  SPX events or 2036-09-30, whichever comes first.
- **No variant selection, ever.** Variant A only. The 30-minute signal
  bar was tried and died in RESULT_INSTRUMENTS at −0.09 bp on 2,626
  events; finding a better variant mid-test and switching is the failure
  this line has already demonstrated twice.

## Known and deliberate

- The forward copy of SPX500_USD in `data/v24` starts 2005; the
  historical file in `data/` starts 2003 and is never written to, so
  every closed result keeps the exact input it ran against.
- `events_v2.csv` is likewise never modified. `events_v3.csv` is
  regenerated from it on each tick.
- Three equity indices are bid == ask for 2005-2011. Cost is
  unmeasurable there. It does not affect the forward test, which only
  records from 2026-09-18.
- The TradingView side, when it exists, is a **window and not an
  instrument** — alerts carry mid prices only. Disagreements are
  resolved in the ledger's favour, or investigated as a bug, never
  averaged.
