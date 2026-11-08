# PREREGISTRATION v19 — does candle shape carry information at all?

```
WRITTEN:  2026-09-11, BEFORE any mutual information has been computed
STATUS:   FROZEN
SUBJECT:  whether the last k candle shapes reduce uncertainty about what
          the next bar does -- separately for DIRECTION and MAGNITUDE
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. Why this comes before any sequence search

Eight candle shapes over three bars is **512 sequences**. Tested at
p < 0.05 that yields roughly **26 significant results by chance alone**,
and a correction across 512 tests is brutal enough to hide anything
real. Searching first and correcting afterwards is how pattern research
usually goes wrong.

**So ask whether the information exists before asking which sequence
carries it.** Mutual information between the last k shapes and the next
bar's outcome is one number with a clean null. If knowing the last three
candles does not reduce uncertainty about what comes next, no sequence
can work, and 512 questions are answered by one test.

## 2. The split that is the actual hypothesis

```
MI( last k shapes ; next bar DIRECTION )
MI( last k shapes ; next bar MAGNITUDE )
```

The theory being tested is specific: **a candle's range encodes
volatility, which is strongly autocorrelated; its shape encodes where
order flow balanced. Neither is a directional statement.** Most
candlestick claims are a directional prediction resting on a volatility
observation.

If that is right, the second line is clearly positive and the first is
indistinguishable from zero. **Both outcomes are made binary so the two
numbers are directly comparable** — which is the point of the design.

## 3. The alphabet, frozen

Each bar is reduced to one of **eight** states, from scale-free geometry
with no free thresholds:

```
direction     close >= open, or not                      2
body          |close-open| / range, above or below its median   2
wick          upper wick vs lower wick, whichever is larger     2
                                                      -> 8 states
```

This maps onto the ordinary vocabulary: *up, large body, small upper
wick* is a bullish marubozu; *down, small body, long lower wick* is a
hammer. The median cuts are computed across the whole sample — that is
an in-sample normalisation of the **alphabet**, not of the outcome, and
it is declared here rather than discovered later.

**Outcomes, both binary:**

```
DIRECTION   sign of (next bar close - next bar open)
MAGNITUDE   next bar range / ATR, above or below its median
```

Direction is defined so it is tradeable: you see bar *t* close, you
enter at bar *t+1*'s open, you exit at its close.

## 4. The null is a permutation, not a formula

**Empirical mutual information is biased upward.** With 512 sequence
states it is positive even under perfect independence — the bias runs
about `(|S|-1)(|Y|-1) / (2n ln2)` bits, which for k=3 is not small.
Reporting raw MI against zero would manufacture a finding.

So the null is built, not assumed: **shuffle the outcome labels, recompute
MI, repeat 1,000 times**, and compare the observed value to that
distribution. The permutation null carries exactly the same bias as the
observed statistic, so the comparison is clean.

Seed **20260911**, declared here.

## 5. Gate A is a positive control, and it is the most important gate

```
Gate A   MI(shapes ; MAGNITUDE) exceeds the 99th percentile of its
         permutation null
```

**A test that cannot detect a known-true effect cannot be trusted to
report absence.** Volatility clustering is one of the most robust
findings in finance; if this method cannot see it, then a null on
direction means the method is broken, not that the market is efficient.

**Gate A failing voids the entire run**, including the direction result.

```
Gate B   MI(shapes ; DIRECTION) exceeds the 99th percentile of its
         permutation null
Gate C   if B passes: the best sequence's edge, converted to basis
         points, exceeds 2x the measured round-trip spread
Gate D   if B passes: the direction effect is present in all three
         disjoint eras
```

Gate C exists because **detectable and tradeable are different
thresholds, separated by about a spread.** An MI that is statistically
real and economically worthless is the most likely way for this to半
pass, and it should be reported as a negative.

## 6. Predictions, registered before the run

- **Gate A passes clearly.** Magnitude MI well outside its null, at
  every k. This is the calibration.
- **Gate B fails.** Direction MI sits inside its permutation null.
- **k adds little.** If direction MI is near zero at k=1 it will be near
  zero at k=3; more history will not create information that one bar
  does not have.
- **If Gate B passes, Gate C fails** — the effect will be under a
  basis point.

**If direction MI comes out large I should suspect the code before the
market**, specifically a lookahead in how the next bar's outcome is
joined to the current bar's shape.

## 7. Kill conditions

- **No lookahead.** The shape of bar *t* uses only bar *t*'s OHLC. The
  outcome uses only bar *t+1*. The ATR used for the magnitude bucket is
  strictly prior.
- **Sequences must not straddle sessions.** A three-bar sequence ending
  at the open would otherwise splice yesterday's close onto today's
  open. Sequences are built within a session only.
- **Any MI above 0.05 bits** for direction is treated as a bug until
  proven otherwise — that would be a very large effect for a liquid
  index.
- **One run.** No changing the alphabet, k, or the outcome definition to
  find a pass.

## 8. Samples

```
PRIMARY     RTH bars only, 09:30-16:00 ET -- consistent with v17/v18
ROBUSTNESS  all bars, declared now, reported alongside and not swapped in
```

k = 1, 2 and 3, all reported. At k=3 the primary sample gives roughly
300 observations per sequence, which is thin — that limitation is
stated now, and it is exactly why the permutation null rather than an
asymptotic one.

## 9. What each outcome means

| | |
|---|---|
| **A passes, B fails** | Candles carry real information about **how much** and none about **which way**. The sequence search is not worth running, and the 512-sequence question is answered. |
| **A and B pass, C fails** | Direction is detectable and not tradeable. Honest and common. |
| **A, B, C, D pass** | A sequence search is justified — enumerate all sequences, rank on 2003-2014, test the top few on 2015-2026, report only the holdout. |
| **A fails** | The method is broken. Nothing else in the run is reportable. |

**Investigation thirty-five.**
