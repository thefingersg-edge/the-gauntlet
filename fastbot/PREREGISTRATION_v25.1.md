# PREREGISTRATION v25.1 — amendment: the runway floor was unsatisfiable

```
WRITTEN:  2026-09-19, before the first forward event and before any
          forward observation exists
AMENDS:   PREREGISTRATION_v25 section 6, the calendar-runway abort only
CHANGES:  nothing else. Not the rule, the instruments, the statistic,
          the stopping rule, the boundary, or any prediction.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. What was wrong

v25 §6 required the event list to hold **at least 90 days of future
releases**, halting below that. I set that number without checking how
far ahead the source actually publishes.

Measured, today:

```
BLS schedule pages reach   CPI 2026-12-10    payrolls 2026-12-04
runway from 2026-09-19     82 days           76 days
```

**The floor is breached on the day the test would begin**, and not
because anything is broken — the 2027 schedule simply is not published
yet.

BLS publishes roughly a year ahead and rolls forward. The forward window
therefore **oscillates**: wide just after the next year's schedule
appears, narrowing to a month or two by the following autumn. **A fixed
90-day floor is unsatisfiable for part of every year, whatever the
market does.** It would halt the test each autumn and restart it each
winter, on a cycle that has nothing to do with the thing being measured.

## 2. What replaces it

The thing that actually matters is not a day count. It is whether the
test **knows when the next event is**. That is what "running blind"
means.

```
HARD ABORT   fewer than 2 future CPI/NFP releases remain in the table,
             or the next one is in the past
WARNING      fewer than 90 days of runway -- refresh the calendar,
             do not halt
```

Two events rather than one, deliberately: one is what you need to take
the next trade, and the second is what tells you the calendar has not
silently ended behind it. Today the table holds **six**.

The 90-day number is kept, demoted from an abort to a prompt, because it
is a reasonable moment to go and fetch — it is just not a reason to stop
measuring.

## 3. Why this amendment is admissible

**§6 is apparatus, not measurement.** It governs when the machinery
stops, not what the machinery computes. Changing it cannot make the
result more favourable or less, cannot move a gate, and cannot change
what counts as a pass — v25 §5's stopping rule, the Haybittle-Peto
boundary at |t| ≥ 3.5, and every prediction in §9 stand exactly as
written.

That is the same test v24.1 had to meet, and it is why that amendment
needed a restriction and this one does not: **there is no direction in
which this change can flatter a finding.**

It is also written **before the first forward observation exists**, so
there is nothing yet to be tempted by.

## 4. The floor did its job

It was breached immediately, and that surfaced a property of the source
I had not checked — that BLS's forward window is a sawtooth rather than
a constant. That is the gate working, not failing. **A floor that never
fires teaches you nothing; this one fired on day zero and cost nothing
but an amendment.**

## 5. Unchanged

- The rule (variant A), the six instruments, the recording format.
- The stopping rule: 271 SPX events or 2036-09-30, whichever first.
- Interim looks on 31 January, verdict-free, |t| ≥ 3.5 to stop early.
- The other two aborts: a 7-day quiet pipeline, and the execution model
  being shown wrong.
- §8's fast arm and §9's predictions, including that realised cost will
  exceed the backtest's assumption.

---

**Investigation forty-one, amended before it started.**
