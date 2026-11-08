# PREREGISTRATION v28.1 — amendment: Gate 0 was specified loosely

```
WRITTEN:  2026-09-25, after v28 was frozen and BEFORE it was run. No
          decomposition, regression or coefficient exists yet.
AMENDS:   PREREGISTRATION_v28 section 4, Gate 0 only -- the positive
          control.
CHANGES:  nothing else. Not the decomposition, not G1, G2 or G3, not a
          threshold, not a prediction.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. What was wrong

v28 section 4 required rule A's mean fade on the **four equity indices**
to land within 0.30 bp of **+3.61 bp**, which is v27's mean over **six
instruments**. Those are different populations. NAS100 and US30 alone
differ by more than 5 bp from each other, so a four-instrument mean
sitting outside a 0.30 bp band around a six-instrument mean would say
nothing about the pipeline -- it would say the two averages cover
different instruments.

A control that can fire for a benign reason is not a control. This one
could have voided the run on arithmetic.

## 2. What replaces it

The comparison is made **trade by trade** instead of on an average, and
against the file v27 actually wrote:

```
Gate 0   for every (instrument, morning) present both here and in
         data/horizon_v27_trades.csv, this file's fade at 09:45 must
         equal v27's gross_H0 to 1e-6 bp.
         Any mismatch -> VOID, as a pipeline failure.
REPORTED the four-equity mean beside v27's six-instrument +3.61 bp,
         with no threshold attached.
```

This is strictly stronger. An average can agree while individual trades
are wrong; a trade-by-trade identity cannot.

## 3. Why this amendment is admissible

**It tightens a control and loosens nothing.** It cannot make any
finding more favourable: Gate 0 decides only whether the new file reads
the same bars the same way, and the replacement is a harder test than
the original. The measurement, the gates that decide the question, and
every prediction in v28 section 6 stand exactly as frozen.

It is also written before the first run, so there is no result to be
tempted by.

---

**Investigation forty-four, amended before it ran.**
