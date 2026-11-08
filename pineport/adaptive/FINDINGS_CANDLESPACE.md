# Findings — L1, discovered candle geometry

Pre-registered in `PREREGISTRATION_CANDLESPACE.md`, written before any
clustering ran. Executed 2026-09-05. 21 markets, clustered on 2005 to
2019-06 (75,707 windows), scored on 2019-07 onward (38,414 windows) — an era
never touched by the clustering or the standardisation.

## Verdict

**FAIL. Kill condition MET.** No discovered shape survives.

    462 cluster x horizon x k tests, Benjamini-Hochberg corrected
    max |t| = 1.97        min q = 0.9884
    clusters passing all six criteria: 0

After the N_eff deflation, exactly **one** of 462 tests reaches even an
uncorrected two-sided p < 0.05. Nothing is close to surviving correction.

## The gate that passed, and why it is the real result

**G1 vol-capture: clear at every configuration.** Cramer's V between cluster
label and volatility decile ran **0.031 to 0.068** against a 0.25 withdrawal
threshold.

That matters more than the null. The published k-means replication states the
failure mode plainly — *"without scaling, higher-variance features dominate
the Euclidean distance and K-Means effectively clusters on volatility alone"*
— and this project has been ambushed by exactly that three times before: I1's
tick-size gate, where volatility ordered Sharpe 15x more strongly than the
predictor; J1's mirror at -0.259 against a +0.016 signal; and E2's entire VRP
sizing result, which was realised volatility on both sides of the equation.

Here it did not happen, because it was designed out rather than caught after:
every feature divided by an ATR measured *before* the window opens, no trend
or volatility feature admitted, and standardisation fitted on the training
era only. **This is the first time in the project that the volatility
artefact was prevented by construction instead of detected in post.**

G2 market-identity also clear (V = 0.045 to 0.097) — the clusters are not
instrument proxies, which was the `a2` defect in a new place.

So the vocabulary is real geometry. It just does not predict.

## What actually killed it

Two things, independently.

**Stability.** Only 2 of 12 configurations reach the pre-registered 0.80
membership-overlap bar under re-seeding:

| window | k=6 | k=10 | k=16 | k=24 |
|---|---|---|---|---|
| 1 candle | **0.94** | 0.69 | **0.83** | 0.67 |
| 2 candles | 0.62 | 0.71 | 0.71 | 0.76 |
| 3 candles | 0.45 | 0.66 | 0.70 | 0.69 |

Re-run k-means with a different random seed and most of the discovered
vocabulary reshuffles. This is B1's finding in a new form: there, moving the
swing-pivot window by one bar destroyed 51-59% of wedge detections. Here,
changing a random seed does the same to the cluster memberships. **A pattern
that depends on the seed is not a pattern.** Only the single-candle space at
low k is stable — which is to say the only reproducible discovered shapes are
the ones already named: long body, small body, long upper shadow.

**Effect size.** Even setting stability aside, max |t| = 1.97 across 462
tests. There is nothing to correct for.

## Comparison to the published attempts

Both prior results were recorded in the pre-registration before this ran.

**Mann & Gorse (UCL)** reported 57.0% / 57.7% directional accuracy against
traditional patterns' 54.0% / 55.4%. This run does not contradict that — it
was never tested here, because accuracy is not the measurement. On hourly
bars, 57% directional accuracy is entirely compatible with losing money once
the spread is paid, and translating an accuracy figure into a net return is
precisely where this project's results have historically died. Their own
paper calls it "only an early indication".

**The independent k-means replication** found no pattern surviving Bonferroni
across 14 tested shapes, and concluded the discovered patterns were
"geometrically real but predictively empty". **This run agrees with that,
from a different representation, on a held-out era, with a stability test
they did not run.**

## What this closes

The kill condition is met and is being honoured: no different clustering
algorithm, no fourth window length, no neural encoder. The pre-registration
named the reason in advance — *the search space is the problem, not the
method*. An unsupervised sweep over 21 markets, 3 window lengths and 4 values
of k is a large enough hypothesis space that the correction needed to make it
honest is also large enough to erase anything it finds.

Which is the general lesson, and it is not specific to candles: **at 21.6
years and N_eff near 5, this dataset cannot support a search. It can only
support a small number of pre-specified tests.** Twelve families have now
established that from twelve directions.
