# RESULT — wedges

```
RUN:      2026-09-11
SPEC:     PREREGISTRATION_v20, frozen before any wedge was detected
CODE:     wedge.py 1.0
SAMPLE:   SPX500_USD daily bars from RTH sessions, 5,842 days, 2003-2026
VERDICT:  FAIL on all five gates -- and not by being random. Wedges are
          ANTI-predictive, and it survives the drift control.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The grid, all nine cells, none selected

```
  w   N   wedges  rising  falling   mean R      t  stop%
  2  20      142     104       38   -0.190  -1.04  72.5%
  2  40      104      77       27   -0.506  -5.34  73.1%
  2  60       74      48       26   -0.450  -2.41  74.3%
  3  20       45      34       11   -0.375  -1.91  73.3%
  3  40       89      71       18   -0.154  -0.97  68.5%
  3  60       70      58       12   -0.501  -3.65  78.6%
  5  20        0                      too few
  5  40       55      40       15   -0.115  -0.61  63.6%
  5  60       61      53        8   -0.224  -1.24  70.5%
```

**Eight of eight usable cells are negative.** Median −0.299 R, pooled
t = −5.02 on 640 trades. Stop-out rate 64-79%.

```
[FAIL] Gate A  median cell -0.299 R, pooled t = -5.02
[FAIL] Gate B  8 of 8 cells agree in sign -- but agree on NEGATIVE
[FAIL] Gate C  vs matched control -0.985 R, t = -1.40
[FAIL] Gate D  -50.28 bp/trade against a 1.8 bp bar
[FAIL] Gate E  eras -0.259  -0.370  -0.302
```

Gate B is worth reading twice. The nine cells were meant to stop a
parameter search reporting its winner. Instead they came back
**unanimous** — which is unusual robustness for a pattern result, and
what they are robust about is losing.

## 2. It is entirely rising wedges

```
rising    n=485   mean -0.479 R   t -7.48
falling   n=155   mean +0.217 R   t +1.45
```

Shorting the breakdown of a rising wedge — the classic bearish setup —
loses **0.479 R per trade at t = −7.48**. Falling wedges are mildly
positive and not significant.

## 3. Is it the wedge, or is it just shorting a rising index?

485 of 640 trades are shorts, on an index that rose roughly five-fold
over the sample. That had to be checked before anything else, and the
matched-geometry control answers it — same stop and target distances,
same direction, random entry:

```
                          n    mean R       t
SHORT wedge trades      485    -0.479   -7.48
SHORT random control   2425    -0.207   -3.51
-> wedge minus random           -0.272   -3.13

LONG wedge trades       155    +0.217    1.45
LONG random control     775    +0.391    1.87
-> wedge minus random           -0.174   -0.68
```

**Drift explains part of it and not all of it.** Random shorts lose
0.207 R and random longs make 0.391 R — that is the equity drift, and it
is large. But rising-wedge shorts lose **0.272 R more than identical
random shorts**, at **t = −3.13**.

That survives the control. So the finding is not "wedges are noise". It
is:

> **Wedges carry directional information, and it points the wrong way.**

## 4. The trap this immediately invites

The obvious reaction is *so trade the opposite*. Three reasons that does
not follow from this run:

**Reversing a bracket is not flipping a sign.** The stop sits at the
window extreme and the target at the projected width; swap direction and
those two distances swap roles, so the geometry — and the break-even hit
rate — changes completely. The +0.272 does not become a +0.272 gain.

**The long side does not corroborate it.** Falling-wedge longs also
underperform their control (−0.174 R), just not significantly. If wedges
were cleanly inverted, the long side should be *above* its control.

**It would be chosen after seeing this.** v20 §6 says one run. An
inverted-wedge rule is a separate pre-registration with the inversion
fixed in advance — and it can fail, which is the point.

A mechanism worth naming as speculation, not finding: a rising wedge in
an uptrend may be a **continuation** consolidation more often than a
reversal, so the breakdown is a shakeout and price resumes. That would
sit alongside RESULT_SWEEP, where fading the breakout also lost. Both
sides of a narrowing range lost money — which is what you would expect
if the level carries no information and everyone pays the spread.

## 5. How much does "a wedge" depend on who draws it?

```
wedge counts across the grid: 45 to 142  (3.2x)
```

Same 23 years, same instrument, same frozen rules — only the pivot
lookback and window length move, and the number of wedges triples.
**That is the subjectivity objection, quantified.** Two analysts using
defensible settings would be looking at substantially different sets of
patterns.

## 6. Predictions

| | predicted | measured | |
|---|---|---|---|
| Gate A | fail, −0.15 to +0.05 R | fail, **−0.299 R** | direction held, magnitude missed |
| Gate B | cells will **disagree** | **8 of 8 agreed** | **missed** |
| wedge counts vary a lot | "several times" | 3.2× | **held** |

I under-predicted both the size and the consistency. I expected wedges
to be an incoherent detector producing noise; they are a coherent
detector producing a reliable loss.

## 7. What this cannot settle

**Whether a human drawing wedges by eye does better.** A frozen detector
disagrees with a chartist on some patterns, and that objection cannot be
answered in principle. It is also the objection that shelters every
unfalsifiable claim. What was measured is whether a **mechanical,
disclosed** wedge rule carries information. It does — the wrong way.

**Only the stated target.** The measured-move projection is the
conventional one; other targets were not tested.

---

**Investigation thirty-six.** The first pattern in this project that was
not merely useless but reliably backwards.
