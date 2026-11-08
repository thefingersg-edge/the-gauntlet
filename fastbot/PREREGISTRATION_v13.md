# PREREGISTRATION v13 — is it still there?

```
WRITTEN:  2026-09-04, after v12 replicated Kurov to -0.14 SE and BEFORE
          any post-2015 return on that window has been computed
STATUS:   FROZEN
SUBJECT:  the same window, on 2016-2026, which v12's sample stopped short of
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. Why this is the only question left

v12 transcribed Kurov's window and reproduced both of their figures on a
different instrument:

```
                                    mine        theirs     SE away
with press conference 2011-15     +46.29 (20)   +44.50      -0.14
without,        2011-04..2018-12   -5.14 (30)    -5.10      +0.00
```

Decomposing it showed **where the drift actually lives**, and it is not
where RESULT_PREANN looked:

```
D-1 morning   09:30 ET -> T-24h    +38.26 bp   t 4.02   17/20 positive
RESULT_PREANN T-24h    -> T-1h     +12.72 bp   t 1.07    8/20
arm 1 tail    T-1h     -> T-15m     -4.96 bp   t -2.10   8/20
their window  09:30 D-1 -> T-15m   +46.29 bp   t 3.63   17/20
```

**83% of the effect is in the four and a half hours RESULT_PREANN
excluded**, and the part it did measure is the weak part.

Two things follow, and both are why the sample must now be extended
rather than left at 2015:

1. **The decay may be an artifact of window placement.** In the D−1
   morning the effect is nearly identical across the regime break —
   +39.73 (2011-12) against +37.28 (2013-15) — while RESULT_PREANN's
   window collapses from +35.47 to −2.45 across the same break. The
   thing that "decayed" may be my window, not the phenomenon.
2. **The conditioner has since stopped conditioning.** The effect is
   press-conference-specific: without one it is −4.48 in the D−1
   morning. **Since 2019-01-30 every scheduled meeting has a press
   conference**, so the variable that separates +46 bp from −5 bp no
   longer separates anything.

## 2. The measurement, frozen

> **The v12 window, unchanged: 09:30 ET on D−1 to T−15m, on M15 bars.**

Three disjoint samples, fixed now:

```
A   2016-01-01 .. 2018-12-31   press-conference meetings only     n=12
B   2019-01-01 .. 2026-08-31   all scheduled meetings             n~60
C   2016-01-01 .. 2018-12-31   non-press-conference meetings      n=12
```

Sample B is *all* meetings because from 2019 all of them carry a press
conference. That is a fact about the Fed's programme, not a choice about
this measurement, and it is the reason B cannot be split the way A and C
can.

The D−1-morning decomposition is reported for each, because that is
where v12 found the effect and it is the component that must be watched.

## 3. The predictions, registered before the run

Kurov report **+0.092%** for press-conference meetings in 2016-2019,
down from +0.445%. So:

- **Sample A comes in well below +46 bp** — I expect roughly **+10 to
  +20**.
- **Sample B is lower again, and may be indistinguishable from zero.**
  Once every meeting has a press conference, whatever the press
  conference was marking is no longer marked. I expect **under +15 bp,
  and I would not be surprised by zero.**
- **Sample C stays negative or near zero**, as it was for 2011-2018.

**If sample B comes in near +46 bp, I am wrong and should suspect the
measurement before celebrating** — it would mean an effect survived the
removal of the only variable that distinguished it, which is not how the
2011-2018 evidence reads.

## 4. Kill conditions

- No bar at or after T−15m; checked per event, run void if violated.
- Above 70 bp on any sample → treated as the window having crept past T.
- **One run.** No further sample slicing. If B is ambiguous it is
  reported as ambiguous, not subdivided until something is significant.
- The "every meeting from 2019" claim is load-bearing for sample B. If
  it is wrong, B is mis-specified — so it is stated here as the
  assumption it is, and B is reported with its meeting count so the
  claim is visible rather than buried.

## 5. What each outcome means

| | |
|---|---|
| **A moderate, B near zero** | The drift was real, is documented, and is now gone — killed by the Fed making every meeting a press-conference meeting. A clean, dated obituary. |
| **A moderate, B moderate** | It survived the programme change. Then the cost question reopens on the *correct* window, and RESULT_PREANN's economics were understated. |
| **A near zero** | The 2016-2019 decay Kurov reported is confirmed out of sample, and the 2011-2015 result is history rather than a strategy. |
| **B large** | Suspect the measurement, per §3. |

## 6. What this cannot do

It cannot re-open RESULT_PREANN's Gate E. CPI and payrolls were
negative on RESULT_PREANN's window and this document does not measure
them; whether they would be positive on the D−1-morning window is
**unasked and unanswered**, and is the obvious next pre-registration
rather than something to infer from here.

**Investigation twenty-nine.**
