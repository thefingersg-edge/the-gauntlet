# PREREGISTRATION v20 — wedges, with the detector frozen

```
WRITTEN:  2026-09-11, BEFORE any wedge has been detected
STATUS:   FROZEN
SUBJECT:  do rising and falling wedges predict the breakout direction
          the literature assigns them, beyond the trade's own geometry
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The parameter problem, and how it is handled

A wedge detector cannot be built with zero free parameters. Pretending
otherwise would be the dishonesty this document exists to avoid. It
needs: a pivot lookback, a window length, a minimum touch count, a
convergence criterion, and a breakout definition.

**Two of those are eliminated by construction:**

```
touches      exactly the LAST TWO swing highs and LAST TWO swing lows.
             "Which subset of pivots" is the biggest single degree of
             freedom in wedge drawing; taking the last two removes it.
breakout     a close beyond the line, extended. No buffer, because a
             buffer is a parameter with no canonical value.
```

**Two are irreducible, so they are declared as a grid, not a choice:**

```
pivot lookback  w in {2, 3, 5}
window length   N in {20, 40, 60}
                                    -> 9 cells, all reported
```

**The gate is on the grid, not on a cell.** A result must hold at the
median of the nine and agree in sign in at least seven. **No single cell
can carry the finding**, which is what stops this becoming a search for
the parameters that work.

One is fixed at a round value and declared: **convergence ≤ 0.75**, the
width at detection must be under three-quarters of the width at the
earlier anchor. There is no canonical number; 0.75 is chosen now and not
moved.

`N` is reused as the forward scan limit and the time stop, so neither
adds a parameter.

## 2. The detector, frozen

At each bar *t*, using only bars in `[t-N+1, t]`:

```
1  swing high at i   high[i] = max(high[i-w .. i+w]),  i+w <= t
2  swing low  at i   low[i]  = min(low[i-w .. i+w]),   i+w <= t
3  need >= 2 of each
4  upper line through the last two swing highs
   lower line through the last two swing lows
5  slopes must share a sign      both up -> RISING, both down -> FALLING
6  converging: width(t) <= 0.75 x width(earlier anchor)
7  breakout: within the next N bars, a close beyond the line --
   BELOW the lower line for a rising wedge, ABOVE the upper for a
   falling one, which is the direction the literature assigns
```

**No lookahead:** a pivot at *i* requires bars to *i+w*, and *i+w ≤ t*,
so every pivot is confirmed before it is used.

**The trade, on the same basis as v18:**

```
entry    mid OPEN of the bar after the breakout bar   (tradeable)
stop     the wedge's opposite extreme inside the window
target   the wedge's widest width, projected from entry  (measured move)
metric   mean R per trade;  null = 0.00 R by optional stopping
```

A bar reaching stop and target together is scored as the **stop**.

## 3. Samples

```
PRIMARY      DAILY bars built from RTH sessions -- 5,842 bars, 2003-2026.
             The classical wedge timeframe, and no session-splicing to
             distort a trendline.
ROBUSTNESS   M15, windows constrained to fit INSIDE one session (N=20),
             declared now and reported alongside, never swapped in.
```

## 4. The gates

```
Gate A   median mean R across the 9 cells > 0, t >= 2.0 on the pooled set
Gate B   >= 7 of 9 cells agree in sign
Gate C   beats a matched-geometry control (identical bracket, random
         entry, same stop and target distances), t >= 2.0
Gate D   the pooled edge exceeds 2x the measured round-trip spread
Gate E   present in all three disjoint eras
```

Gate B is the one that makes the grid honest. A finding in two of nine
cells is a parameter search reporting its winner.

## 5. Predictions

- **Gate A: FAIL.** Median mean R between −0.15 and +0.05.
- **Gate B: most likely FAIL** — I expect cells to disagree, which is
  itself the finding about wedge robustness.
- **If Gate A passes and Gate C fails**, the measured-move geometry is
  doing the work, not the wedge.
- **Wedge counts will vary enormously across the grid** — I expect the
  most permissive cell to find several times the wedges of the
  strictest. That variation is worth reporting whatever the returns do,
  because it quantifies how much "a wedge" depends on who is drawing it.

The prior from v19 is poor: a single candle's directional information is
worth **0.355 bp** against a 1.8 bp bar. A wedge would have to carry
five times a candle's directional content to pay. **But a prior is not a
measurement**, which is why this runs.

## 6. Kill conditions

- **Any lookahead** in pivot confirmation voids the run.
- **Mean R above +0.50** is a bug until proven otherwise.
- **One run.** The grid is the grid; no cell is added, and 0.75 does not
  move.

## 7. What this cannot settle

**Whether a human drawing wedges by eye does better.** A frozen detector
will disagree with an experienced chartist on some patterns. That
objection is unanswerable in principle — and it is also the objection
that shelters every unfalsifiable claim, so it does not stop the test.
What this measures is whether a *mechanical, disclosed* wedge rule
carries information.

**Investigation thirty-six.**
