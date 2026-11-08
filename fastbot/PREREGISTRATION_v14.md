# PREREGISTRATION v14 — the day-before session, on all three

```
WRITTEN:  2026-09-04, after RESULT_KUROV, and BEFORE any day-before
          session return has been computed for CPI or NFP
STATUS:   FROZEN
SUBJECT:  whether the segment that carried the FOMC effect pays on CPI
          and payrolls -- i.e. Gate E, re-asked on the right segment
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. Why the obvious version of this question is a trap

The natural move after RESULT_KUROV is "run CPI on the v12 window."
**That would be nearly a no-op, and the reason is arithmetic, not
data.** Computed from the clock alone:

```
FOMC 14:00      v10  14:00 D-1 -> 13:00 D    v12  09:30 D-1 -> 13:45 D
                v12 starts 4.50h EARLIER -- it adds a head, and that
                head is where the +38.26 bp was

CPI/NFP 08:30   v10  08:30 D-1 -> 07:30 D    v12  09:30 D-1 -> 08:15 D
                v12 starts 1.00h LATER -- there is no head to add
```

For an 08:30 release, **T−24h already falls in the D−1 pre-market**, so
RESULT_PREANN's window already contained the whole day-before session.
Running v12's window on CPI would reproduce RESULT_PREANN's CPI number
with a 1-hour trim and a 45-minute extension. That is a consistency
check, not a discovery, and it will be reported as one.

## 2. The question that is actually open

The FOMC decomposition said something more specific than "a longer
window pays":

```
09:30 D-1 -> 14:00 D-1   +38.26 bp   t 4.02   17/20 positive
14:00 D-1 -> 13:00 D     +12.72 bp   t 1.07    8/20
13:00 D   -> 13:45 D      -4.96 bp   t -2.10   8/20
```

**The money was made during the regular session on the day before the
announcement** — not, as Lucca & Moench's window implied, on
announcement-day morning. They could not have seen it: their window
began at 14:00 on D−1, after most of that session had already happened.

So the open question is not about window length. It is:

> **Does the regular cash session on the day before a scheduled release
> pay, for CPI and payrolls, the way it does for the FOMC?**

That is Gate E's question — does the mechanism generalise — asked on the
segment that carries the effect instead of the one that does not.

## 3. The measurement, frozen

> **SEGMENT: 09:30 ET to 16:00 ET on D−1, on M15 bars.**
>
> Entry: the OPEN of the 09:30 ET bar on D−1.
> Exit: the CLOSE of the bar ending at 16:00 ET on D−1.

**One construction, three event types.** This is the whole point: Gate E
failed on a uniform window, and it must be re-asked on a uniform
segment or the comparison means nothing.

- **D−1 is the previous calendar day**, matching v12 exactly. Where that
  is a weekend the event is dropped and counted. From the calendar this
  affects **4 of 412 CPI and 5 of 400 NFP** — 1% each — so it cannot
  drive a result, and the figure is stated here rather than discovered.
- **Control:** the same 09:30–16:00 segment on non-event days, ±1 day of
  any event excluded — the construction RESULT_PREANN, v11 and v12 all
  used.
- **Samples, fixed now:** all measurable events of each type; plus, for
  reference only, the 20 press-conference FOMC announcements of
  2011-2015; plus a pre-2016 / post-2015 split, because v13 showed the
  FOMC effect died at that break and the same break must be visible for
  the others or the comparison is confounded by era.

**Note the asymmetry, and it is inherent rather than a flaw.** For a
14:00 FOMC the D−1 session ends 22 hours before the release; for an
08:30 CPI it ends 16.5 hours before. "The session before the
announcement" is not the same distance from the announcement in the two
cases. There is no construction that fixes this without abandoning the
uniformity that makes the test a test.

## 4. The predictions, registered before the run

| | prediction |
|---|---|
| FOMC, all measurable | positive but diluted: **+5 to +20 bp** |
| FOMC, press conference 2011-15 | **+30 to +50 bp** — this is the known one, and it is the check that the segment is being built correctly |
| **CPI** | **near zero: \|x\| < 10 bp** |
| **NFP** | **near zero: \|x\| < 10 bp** |

The reasoning for CPI and NFP is not a hunch. RESULT_PREANN's window for
an 08:30 release **already contained this entire session**, and it
measured −1.86 bp excess for CPI and −7.48 for NFP. If the session were
carrying +38 bp the way it does for the FOMC, that blob could not have
come out negative.

**So this is close to a foregone conclusion, and that is exactly why it
is worth pre-registering rather than assuming.** The one thing that
would make it interesting is being wrong.

## 5. The falsification condition, which is the point of running this

> **If CPI's D−1 session pays more than +25 bp, the FOMC finding is not
> FOMC-specific.**

In that case:

- RESULT_KUROV §7's reading — that the drift is press-conference-
  conditional — is wrong;
- RESULT_PREANN's Gate E was answered on a segment that could not see
  the effect, and its FAIL verdict would need re-deriving rather than
  merely re-stating;
- and the phenomenon would be "the session before scheduled macro news"
  rather than anything about the Fed, which is a much larger claim and
  would need its own pre-registration before anyone believed it.

**Registering that in advance is what stops a positive CPI result being
quietly absorbed as a bonus rather than treated as a contradiction.**

## 6. Kill conditions

- **No bar at or after 16:00 ET on D−1** may enter the segment; the
  release is the following morning for CPI and NFP, so there is no
  announcement contamination risk here — but the boundary is checked per
  event rather than trusted.
- **Above 70 bp** on any sample → treated as a construction fault, per
  v10 §6, and investigated before reporting.
- **One run.** No sweeps over segment boundaries, no shifting 16:00 to
  find something. If the answer is null it is recorded as null.
- The **20/20** press-conference FOMC figure is the calibration line. If
  it does not land in the +30 to +50 band the segment is being built
  differently from v12's decomposition and **the whole run is void**,
  including the CPI numbers.

## 7. What this cannot settle

**Whether CPI pays anywhere else.** This measures one segment. A null
here says the day-before session does not pay for CPI; it does not say
no window does.

**Tradeability.** Nothing here touches cost, and the segment is a
6.5-hour hold rather than a 23-hour one, so RESULT_PREANN's cost
arithmetic does not transfer — the financing is smaller and the spread
is the same two fills.

**Investigation thirty.**
