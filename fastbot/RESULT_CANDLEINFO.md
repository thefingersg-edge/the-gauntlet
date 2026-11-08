# RESULT — do candles carry information?

```
RUN:      2026-09-11
SPEC:     PREREGISTRATION_v19, frozen before any MI was computed
CODE:     candle_info.py 1.0
SAMPLE:   SPX500_USD M15, 5,842 RTH sessions, 146,037 bars, 2003-2026
VERDICT:  Yes -- measurably, and it is worth 20% of its own cost.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The answer in one table

```
  k  states        n    outcome        MI   null p99  null mean  beats
  1       8  139,391  direction   0.00053    0.00009    0.00004    YES
  1       8  139,391  magnitude   0.00396    0.00010    0.00004    YES
  2      64  133,723  direction   0.00139    0.00052    0.00034    YES
  2      64  133,723  magnitude   0.00798    0.00050    0.00034    YES
  3     512  128,028  direction   0.00413    0.00330    0.00289    YES
  3     512  128,028  magnitude   0.01469    0.00332    0.00288    YES
```

**Candle shape carries real information — about both magnitude and
direction.** I predicted direction would be indistinguishable from
noise and that was **wrong**.

But the ratio is the hypothesis, and it survives:

```
k=1   magnitude carries 7.5x the information of direction
k=2                     5.7x
k=3                     3.6x
```

## 2. The gates

```
[PASS] Gate A  magnitude MI beats its null at every k   <- POSITIVE CONTROL
[PASS] Gate B  direction MI beats its null at every k
[FAIL] Gate C  best shape's edge +0.355 bp vs a 1.8 bp bar
[PASS] Gate D  eras +0.122  +0.279  +0.815 bp
```

**Gate A mattered more than any other gate here.** Volatility clustering
is about as robust as findings get; a method that could not detect it
could not be trusted to report absence of anything else. It detected it
cleanly, so the direction result is worth reading.

**Gate C is where it dies.** The single most informative shape is worth
**0.355 bp of excess return**. It needs 1.8 bp — twice the measured
round-trip spread — to be worth placing. **It is 20% of the bar it must
clear.**

## 3. The shape that carries the information points the wrong way

```
shape                     n   mean bp       t
ALL BARS            146,037     0.050    1.10
dn small upper       16,255     0.405    2.91   <- the informative one
up small lower       19,709    -0.170   -1.40
dn large lower       18,054     0.163    1.21
up large upper       21,385    -0.085   -0.75
```

A down bar with a small body and a dominant upper wick — a **shooting
star**, in the traditional vocabulary — is followed by a mildly
**positive** bar. The folklore reads that shape as bearish. Measured
over 16,255 instances, it is the opposite sign.

It survives multiplicity across the eight shapes (t = 2.91 against a
Bonferroni threshold of 2.73), and Gate D shows it in all three eras and
**strengthening**: +0.122, +0.279, +0.815 bp. That is unusual — most
anomalies decay. This one grows, and all three numbers are far below
cost.

## 4. The sequence question, answered by watching the trap operate

Dave's question was whether *this candle, then this, then this* predicts
something. The run shows exactly what happens when you look:

```
k=1   best of   8 sequences ->  53.45% up   on n = 17,292
k=2   best of  64 sequences ->  56.44% up   on n =  1,958
k=3   best of 439 sequences ->  62.72% up   on n =    228
```

**Longer sequences look better and mean less.** The apparent edge nearly
triples while the sample collapses by 75×. That is the signature of
selection, not signal, and it is measurable:

```
k=1   53.45% vs a 51.52% base, n=17,292  ->  5.1 SD
      expected max of   8 draws          ->  ~1.4 SD    REAL

k=3   62.72% vs a 51.52% base, n=228     ->  3.4 SD
      expected max of 439 draws          ->  ~2.9 SD    CHANCE
```

**Only k=1 is genuinely beyond what selection produces.** The
three-candle sequence that looks most impressive is the one most likely
to be an artifact of having looked at 439 of them — and it would have
been the headline of any study that did not compute that second column.

This is why v19 measured information before searching sequences. The
512-sequence search is not worth running, and now there is a number
saying so rather than an opinion.

## 5. So: is there a rationale for candles meaning something?

**Yes, and it is narrower than the claims.**

- **Range encodes volatility, and volatility clusters.** That is the
  0.00396 bits at k=1, and it is 7.5× the directional information. Real,
  robust, and not a directional statement.
- **Shape encodes a little about direction too** — about 0.0005 bits,
  which is roughly a 2-percentage-point tilt on a coin flip.
- **That tilt is worth 0.355 bp against a 0.9 bp round trip.**

So the honest formulation is not "candlesticks are nonsense". It is:
**candles carry genuine information, mostly about how much and slightly
about which way, and the directional part is about one fifth of the size
needed to pay for the trade that would exploit it.**

That is a more useful answer than either side of the usual argument, and
it explains why the pattern literature is so persistent: **the effects
are real. They are just smaller than the spread.**

## 6. On wedges, now that this is measured

The distinction stands and this sharpens it. A candle is four numbers
with **one** arbitrary threshold — here, the body/range median at
0.4615, declared in advance. A wedge needs six to eight interacting
choices *and* a window whose endpoints are chosen after seeing the
chart, which makes the usual claim unfalsifiable rather than merely
imprecise.

A wedge study is testable only with the detector frozen and its output
accepted. Given that a single candle's directional information is worth
0.355 bp, the prior for a wedge clearing 1.8 bp is not encouraging — but
that is a prior, not a measurement, and it is not a reason to refuse the
test.

## 7. Predictions

| | predicted | measured | |
|---|---|---|---|
| Gate A | pass clearly | pass at every k | **held** |
| Gate B | **fail** | **pass at every k** | **missed** |
| k adds little | near zero at 1 → near zero at 3 | direction MI rose 0.0005 → 0.0041, but so did the null | half held |
| Gate C | fail, under a basis point | fail, **0.355 bp** | **held** |

The Gate B miss is the useful one. I said candles carry *no* directional
information and they carry a little. The economic conclusion did not
change, but the factual claim I would have made was wrong, and it took a
permutation null on 139,391 bars to find that out.

---

**Investigation thirty-five.** The first in this project where a pattern
claim was partly **right** — and still not tradeable.
