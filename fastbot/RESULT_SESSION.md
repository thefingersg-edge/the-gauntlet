# RESULT — the day-before session, on CPI and payrolls

```
RUN:      2026-09-04
SPEC:     PREREGISTRATION_v14, frozen before any CPI session was measured
CODE:     preann_session.py 1.0
VERDICT:  CPI does not pay. Gate E's FAIL survives being re-asked on the
          segment that carries the FOMC effect.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The obvious version of this question was a trap

"Run CPI on the window that worked for the FOMC" sounds like the right
next step. It is nearly a no-op, and the reason is arithmetic — settled
from the clock before any price was touched:

```
FOMC 14:00      v10  14:00 D-1 -> 13:00 D    v12  09:30 D-1 -> 13:45 D
                v12 starts 4.50h EARLIER -- that head held the +38.26 bp

CPI/NFP 08:30   v10  08:30 D-1 -> 07:30 D    v12  09:30 D-1 -> 08:15 D
                v12 starts 1.00h LATER -- there is no head to add
```

For an 08:30 release, **T−24h already falls in the D−1 pre-market**, so
RESULT_PREANN's window already contained the entire day-before session.
Running v12's window on CPI would have re-printed RESULT_PREANN's answer
with a one-hour trim, and reported it as new.

## 2. What was measured instead

The FOMC decomposition said something narrower than "a longer window
pays":

```
09:30 D-1 -> 14:00 D-1   +38.26 bp   <- the money
14:00 D-1 -> 13:00 D     +12.72 bp
13:00 D   -> 13:45 D      -4.96 bp
```

**The money was made during the regular session on the day before.** So
the open question is whether *that session* pays for CPI and payrolls —
Gate E's question, asked on the segment that carries the effect rather
than the one that does not.

> **SEGMENT: 09:30 → 16:00 ET on D−1. One construction, three event
> types.**

## 3. The calibration ran first, and could have voided everything

v14 §6 required the 20 press-conference FOMC announcements of 2011-2015
to land between +30 and +50 bp on this segment — a figure known from
v12's decomposition. If they had not, this file would have been building
the segment differently and every number below, CPI included, would have
been discarded.

```
FOMC press conference 2011-15   n=20   +31.95 bp   OK
```

(+38.26 over 09:30→14:00, +31.95 over the full 09:30→16:00 — the last
two hours of D−1 give back about 6 bp.)

## 4. The result

```
event      n   mean bp   median    ctrl   excess      t  positive
FOMC     194      6.30     6.34    3.42    +2.88   0.41   107/194
CPI      293      1.58     8.39    3.42    -1.85  -0.28   165/293
NFP      279     -2.59     6.18    3.42    -6.01  -1.05   156/279
```

```
BY ERA        pre-2016    n      2016+    n
FOMC            +5.79   109      -0.86   85
CPI             -5.10   162      +2.17  131
NFP             -7.90   153      -3.72  126
```

**CPI pays nothing on this segment, in either era.** Neither does
payrolls. The FOMC line is positive only before 2016, matching v13.

Note how concentrated the FOMC effect is: **+31.95 bp on 20
press-conference announcements against +2.88 across all 194.** Twenty
events out of 194 carry essentially the whole thing.

## 5. The falsification condition was not triggered

v14 §5 registered, before the run:

> If CPI's D−1 session pays more than +25 bp, the FOMC finding is not
> FOMC-specific — RESULT_KUROV §7 is wrong and Gate E must be
> re-derived, not merely restated.

CPI came in at **−1.85**. So:

- **the FOMC effect stays FOMC-specific**, and press-conference-
  conditional as RESULT_KUROV read it;
- **RESULT_PREANN's Gate E FAIL survives** being re-asked on the right
  segment. It was the correct verdict even though it was reached on a
  window that could not see the phenomenon — the right answer for an
  incomplete reason, now confirmed for the complete one;
- and the phenomenon is **not** "the session before scheduled macro
  news." It is something about the FOMC, in an era that has ended.

## 6. Predictions

| | predicted | measured | |
|---|---|---|---|
| FOMC, all | +5 to +20 | **+2.88** | **missed, low** |
| FOMC, press conference 2011-15 | +30 to +50 | +31.95 | held (calibration) |
| **CPI** | −10 to +10 | **−1.85** | **held** |
| **NFP** | −10 to +10 | **−6.01** | **held** |

The FOMC miss is instructive. I anchored on RESULT_PREANN's +24.48
all-events excess and expected the segment to inherit some of it. It
does not: on this segment the effect lives almost entirely in the 20
press-conference events, and diluting across 194 leaves +2.88. The
concentration was larger than I allowed for.

## 7. The drop audit

293 of 412 CPI events measured, which is a 29% drop rate and deserves
showing rather than asserting to be innocent:

```
event   dropped   before the price history   after
FOMC         86                         74      12
CPI         119                        112       7
NFP         121                        112       9
```

The M15 series begins **2003-03-21**; `events.csv` begins 1994. So the
overwhelming majority of drops are events with no price data at all.

Every remaining drop is a **weekend or a market holiday**, checked
individually: the four Monday CPI releases v14 §3 named in advance,
Presidents' Day (2013-02-19, 2014-02-18, 2017-02-13, 2019-02-11,
2021-02-08 all have a closed D−1), Independence Day (2013-07-05,
2019-07-05, 2024-07-05), and eleven FOMC meetings scheduled in the
future. **No drop depends on a return.**

## 8. Where this leaves things

The pre-FOMC line is now closed on every side it can be closed on:

```
does it exist?             yes -- replicated to -0.14 SE (RESULT_KUROV)
where does it live?        the session before announcement day
is it still there?         no -- dead after 2015 (v13)
does it generalise?        no -- CPI -1.85, NFP -6.01 (this document)
what does it cost?         10.0% of gross, measured (RESULT_PREANN)
```

The one thing that would have reopened it — CPI paying on the segment
FOMC pays on — was tested with the falsification condition written down
first, and it did not.

**What is worth keeping is the apparatus, not the trade.** It reproduced
a published result and its null on the first attempt, caught a lookahead
bug in its own code before the gate ran, caught nine years of
bid-equals-ask masquerading as zero cost, and caught two of my own
errors — a misread comparand carried across two documents, and a
financing convention I asserted from the wrong market. Each of those was
found by a check that could have failed and did.

**Investigation thirty.**
