# PREREGISTRATION v11 — why Kurov's number and mine disagree

```
WRITTEN:  2026-09-04, after RESULT_PREANN.md closed and BEFORE any
          return from the 45-minute segment or from the 14 excluded
          2011-2012 events has been looked at
STATUS:   FROZEN
SUBJECT:  reconciling Kurov, Wolfe & Gilbert's +44.5 bp (2011-04 ..
          2015-12) with the +0.36 bp measured here for 2012-2015
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The gap, stated exactly

Both figures are **raw** window means — RESULT_PREANN's by-period table
does not subtract the control, and neither does Kurov. So they compare
directly:

```
Kurov, Wolfe & Gilbert   2011-04 .. 2015-12    +44.50 bp
RESULT_PREANN            2012    .. 2015       + 0.36 bp
                                               ---------
gap                                             -44.14 bp
```

RESULT_PREANN declined to chase this, on the grounds that re-specifying
a window after seeing a result is the thing the apparatus exists to
prevent. This document exists so the chase is specified first.

## 2. What is already known without looking at any return

Two facts were established from the **calendar and the VIX series
only** — no window return from the disputed events has been observed,
and this matters, because §5's predictions are derived from them.

**Fact one — 37% of his sample is not in mine.**

```
scheduled FOMC meetings in 2011-04 .. 2015-12      38
flagged UNCERTAIN in events.csv, excluded          14
measured in RESULT_PREANN                          23
missing for other reasons                           1
```

All fourteen fall between 2011-04-27 and 2012-12-12:

```
2011-04-27  2011-06-22  2011-08-09  2011-09-21  2011-11-02  2011-12-13
2012-01-25  2012-03-13  2012-04-25  2012-06-20  2012-08-01  2012-09-13
2012-10-24  2012-12-12
```

They are UNCERTAIN because `event_table.py` cannot tell, for 2011-2012,
which meetings had a press conference — and in that era **a
press-conference meeting released its statement at 12:30 ET while a
non-press-conference meeting released at 14:15**. An hour and three
quarters of ambiguity is not a window this project will guess at.

**Fact two — the missing block is the high-uncertainty half.**

```
mean VIX 2011-04 .. 2012-12   (his, not mine)     21.35
mean VIX 2013-01 .. 2015-12   (shared)            15.03
mean VIX across his window                        17.35
RESULT_PREANN Gate D median split                 17.12
```

The block I am missing sits **entirely above** Gate D's median. The
block we share sits **entirely below** it. Gate D established that the
high half earns +50.05 bp and the low half +8.29.

So before measuring anything: my 2012-2015 figure is, in Gate D's terms,
**a low-VIX-only sample**, and his is a mixture. That is a composition
difference, not a disagreement about the world.

## 3. The candidate explanations, and the two this can test

| | explanation | testable here |
|---|---|---|
| **A** | The window. Mine ends at **T−1h**; his ends at **T−15m**. The 45 minutes in between are excluded by construction. | yes — §4 arm 1 |
| **B** | The sample. The 14 events above, all high-VIX. | yes — §4 arm 2 |
| **C** | The control. I subtract a 4.69 bp control mean in the headline; the by-period table does not, so this is worth **0 bp** to this particular gap. | already settled |
| **D** | The instrument. He measures S&P 500 index/futures; this measures OANDA's SPX500_USD CFD. | **no** |
| **E** | The window's head. His starts 15 min earlier than mine. Overnight, so near zero. | no, and not worth it |

**D is not resolvable with anything on this disk**, and §5 registers in
advance that a residual is expected because of it.

## 4. The two measurements, frozen

### Arm 1 — the missing 45 minutes

> **SEGMENT: from T − 1 hour to T − 15 minutes, on M15 bars.**
>
> Entry: the OPEN of the bar starting at T−60m.
> Exit: the CLOSE of the bar starting at T−30m, which ends at T−15m.
> Three bars, 45 minutes.

**This is disjoint from the window already measured.** It abuts it and
does not overlap it, so the segment return *adds* to RESULT_PREANN's
window to reconstruct the fuller T−24h → T−15m window. Nothing is
counted twice and no window length is being swept.

Reported on two samples, both fixed now:

- **all measurable FOMC events** (the powered estimate)
- **2013-2015 only** (the reconciliation figure, n≈23)

Control: the same clock segment on non-event days, excluding ±1 day of
any event — identical construction to RESULT_PREANN, so the two are
comparable.

### Arm 2 — the fourteen excluded events

Recover the true statement time for each of the fourteen by determining,
**from a Federal Reserve source**, which 2011-2012 meetings had a press
conference. Then measure them on the **unchanged** RESULT_PREANN window,
T−24h → T−1h.

**Precondition, and it is a hard one.** If the press-conference list
cannot be sourced to federalreserve.gov, this arm reports
**UNDETERMINED** and stops. It does not fall back to inferring the
schedule from a quarterly pattern, and it does not fall back to
assuming 14:15 for all of them. `event_table.py` went through seven
versions because every wrong version looked fine in its output; a
guessed schedule here would look fine too.

## 5. The predictions, registered before either arm runs

Derived from §2's calendar and VIX facts alone.

**Arm 1: I expect the 45-minute segment to be SMALL — under 15 bp — and
therefore NOT the explanation.**

Lucca & Moench locate the bulk of the drift across announcement-day
morning, roughly 09:30 to 14:00 — four and a half hours. Forty-five
minutes is 17% of that. If the whole morning is worth on the order of 25
bp on this sample, the segment should be worth about 4.

**Arm 2: I expect the fourteen to pay high-VIX magnitude, and to close
under half the gap.**

At Gate D's high-half mean of +50 bp:

```
pooled 2011-2015 = (14 x 50.0 + 24 x 0.36) / 38  =  +18.6 bp
```

against Kurov's +44.5. **That closes about 42% of the 44.1 bp gap and
leaves roughly 25 bp unexplained.**

**Combined: I expect a residual to remain.** If the two arms reconcile
the gap completely, that is a worse outcome than a partial
reconciliation, not a better one — it would mean two independent
corrections landed exactly on a third party's number, and the most
likely cause of that is a mistake in my favour rather than three
measurements agreeing.

## 6. Kill conditions

- **Arm 1's segment ends 15 minutes before a release.** That is the
  closest this project has ever put a measurement to an announcement,
  and it is the one place a timestamp error becomes a large clean
  spurious result. Therefore:
  - **no bar in the segment may be stamped at or after T−15m**, checked
    per event, run void if violated;
  - events with `time_quality == UNCERTAIN` are excluded from arm 1
    entirely;
  - the **T−15m → T** interval and the **T → T+1h reaction** are
    measured and reported alongside as diagnostics. If the segment's
    magnitude resembles the reaction's rather than the window's, it is
    treated as contamination and the arm is void.
- **A segment above 30 bp** is treated as a bug until proven otherwise —
  it would be two-thirds of Lucca & Moench's entire 24-hour figure
  earned in 45 minutes.
- **Arm 2 without a Fed source** → UNDETERMINED, per §4.
- **Arm 2 may not touch the window.** It measures the same T−24h → T−1h
  interval as RESULT_PREANN. If it needs a different window to produce a
  result, it is abandoned and recorded as abandoned.
- **One run per arm.** No sweeps over segment length, no sign flips.

## 7. What a result here does and does not license

**It does not reopen RESULT_PREANN's verdict.** That run is closed and
its verdict was FAIL on Gate E. Nothing measured here can change it:
arm 1 measures an interval that was deliberately excluded, and arm 2
adds events to a period, neither of which touches whether the effect
generalises to CPI and payrolls.

**It does not become a trading rule.** A 45-minute hold entered an hour
before an FOMC statement is a different instrument from the one costed
in RESULT_PREANN section 6, and the spread is paid on a much smaller
gross. If arm 1 returns something material, the cost question starts
over rather than being inherited.

**What it can settle** is whether this project's measurement disagrees
with the published literature, or merely covers a different sample.
Those are very different things to be carrying forward, and right now I
do not know which one is true.

## 8. Scoreboard

**Investigation twenty-seven.** The first written to reconcile against
someone else's published number rather than to test an idea of our own —
and the first where the pre-registered expectation is that the
reconciliation will *fail to fully close*.
