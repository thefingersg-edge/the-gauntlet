# PREREGISTRATION v25 — the forward test

```
WRITTEN:  2026-09-18, before the first forward event
STATUS:   FROZEN
SUBJECT:  the plain release fade (variant A), recorded forward on six
          instruments, with real bid and ask
RECORDS:  it does not trade. Nothing in this design places an order.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. What this can and cannot do, before anything else

```
to reach t = 2.0                    events    years (1 instr)   (6 instr)
gross effect   +3.79 bp                271          11.3            6.6
NET of cost    +2.02 bp                954          39.8           23.2
```

**This test cannot answer whether the rule makes money.** Forty years on
one instrument, twenty-three across six, and adding instruments does not
rescue it — they react to the same releases, so they raise return and
risk together and leave the Sharpe at 0.32.

**It is registered anyway, for three things it CAN do:**

1. **Validate the execution model**, which returns in months rather than
   years and is the part every backtest gets wrong.
2. **Confirm the gross effect** in roughly seven years across six
   instruments.
3. **Detect that the effect has died.** Pre-FOMC drift was real until
   2015 and then was not. Nothing in a historical backtest can tell you
   which side of that line you are standing on.

Anyone reading a running total before §5's dates should read §5 first.

## 2. The rule, unchanged from v22 §3

```
trigger    a scheduled 08:30 ET US release -- CPI or payrolls
signal     the 08:30-08:45 ET bar
direction  FADE.  close > open -> SHORT.  close < open -> LONG.
                  close = open -> no trade
entry      the OPEN of the 08:45 bar
exit       the OPEN of the 09:45 bar.  Four bars. No stop, no target.
```

**This is variant A**, the pre-registered rule — not variant C, which
died in RESULT_INSTRUMENTS at −0.09 bp on 2,626 events. **Claims stays
excluded.** No variant selection is available in this test, and adding
one later is the kill condition in §7.

## 3. The instruments, fixed now

```
SPX500_USD   NAS100_USD   US30_USD   DE30_EUR   EUR_USD   XAU_USD
```

Six, no additions, no removals. An instrument that stops quoting is
reported as stopped; its record is not backfilled from elsewhere.

## 4. What is recorded, per event per instrument

Append-only. **History is never recomputed** — a ledger you can rebuild
is a ledger you can quietly improve.

```
date, instrument, release, signal_open, signal_close, direction,
entry_bid, entry_ask, exit_bid, exit_ask, mid_gross_bp, net_bp,
spread_entry_bp, spread_exit_bp, bars_present, written_at
```

`bars_present` records whether all four bars existed. A missing bar is a
**skipped** event, recorded as skipped, never silently dropped — an event
that vanishes from a forward test is indistinguishable from one that lost
money unless it is written down.

## 5. The stopping rule, which is the whole point

A forward test you can stop whenever is worth nothing. Registered now:

```
PRIMARY HORIZON   271 recorded events on SPX500_USD,
                  or 2036-09-30, whichever comes FIRST
```

**Interim looks are permitted only on 31 January each year**, and they
report `n` and the running mean and **do not render a verdict.**

**An interim look may stop the test only on a Haybittle-Peto boundary:**

```
interim look   |t| >= 3.5   -> may stop and report
final look     |t| >= 2.0   -> the registered threshold
```

The boundary is deliberately far above the final threshold so that nine
annual peeks cost almost nothing in false-positive rate. **A result of
t = 2.5 at an interim look is not a finding.** It is a reason to keep
going.

**Stopping early for a good result is forbidden.** The only other exits
are the aborts in §6.

## 6. Aborts — ending without a verdict

Each of these ends the test as a finding about the *apparatus*, not
about the market:

- **The calendar runs out.** The event list must always hold at least
  90 days of future releases. Fewer and the test halts loudly. *(A
  strategy whose calendar has expired reports a confident zero — this
  project has produced that failure four times.)*
- **The pipeline goes quiet.** If no new bar has been fetched for 7
  days, halt and say so.
- **The execution model is shown wrong** by §8, in which case the model
  is corrected and the test restarts with a new registration. Records
  already taken are kept and marked as belonging to the old model.

## 7. Kill conditions

- **No variant selection.** Variant A only. No horizon, slot, or signal
  length changes. Discovering a better variant mid-test and switching is
  the failure this whole line has already demonstrated twice.
- **No instrument added or dropped** to improve a number.
- **No stopping outside §5 and §6.**
- **No sign flips.** Fade is positive, fixed in §2.
- **History is never recomputed**, including after a bug fix. A fix
  applies forward; the old records stay and are marked.

## 8. The fast arm — validating the execution model

The one part that returns quickly, and registered separately because it
answers a different question.

```
FIRST CHECK at 60 recorded trades total (~5 months across six
instruments), then at every interim look.

REPORTED    realised round-trip cost per instrument, against the
            backtest's assumption
FLAG        realised cost exceeding the assumption by more than 50%
```

**Registered prediction: realised cost will EXCEED the assumption.** The
backtest measures the spread at a bar's close; a real fill at 08:45 sits
fifteen minutes from a release, where the spread is wider. If that is
right, every net figure in RESULT_CONFIRM and RESULT_INSTRUMENTS is too
kind, and by how much is worth knowing years before the edge question
resolves.

## 9. Predictions, registered before the first event

- **The gross effect stays positive but does not reach t = 2.0 within
  three years.** Arithmetic, not optimism — 271 events is 11 years on
  SPX500 alone.
- **Realised cost exceeds the assumption** (§8).
- **No interim look crosses |t| = 3.5.**
- **If any interim look DOES cross it, I expect it to be downward**, not
  up — the effect dying rather than proving itself, because that is what
  happened to pre-FOMC drift.

My registered predictions have been wrong in five of ten this line,
including three sign errors. These are priors, and the boundary in §5 is
what protects the result from them.

## 10. The two halves, and which one is the measurement

**The ledger is the measurement.** It runs on OANDA data with real bid
and ask and it is what §5 scores.

**The TradingView side is a window, not an instrument.** Alerts carry mid
prices only, so it can show gross and never net. Nothing on that side
feeds the ledger, and a disagreement between them is resolved in the
ledger's favour — or investigated as a bug, never averaged.

---

**Investigation forty-one.** The first that cannot be finished in this
conversation, or this year.
