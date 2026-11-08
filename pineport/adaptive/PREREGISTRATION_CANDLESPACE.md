# Pre-registration — L1, discovered candle geometry

Written 2026-09-05, before any clustering is run.

## The question

Every pattern test in this project so far (B1-B3, the zoo) took a **named**
pattern — engulfing, hammer, head-and-shoulders, wedge — and asked whether it
predicts. This asks the inverse: **let the data say which candle shapes exist,
then test those.** No pattern is defined in advance; the vocabulary is
discovered and only then scored.

## What the literature already says, recorded before we run

Two prior attempts, both found before designing this:

**Mann & Gorse, "Deep Candlestick Mining" (UCL/ICONIP).** Random decision
trees to rank OHLC-derived factors, an LSTM for direction, k-means++ to
cluster the predictive factors. Reported **57.04% (Bund) and 57.7% (EURUSD)**
directional accuracy against traditional patterns' 54.04% and 55.35%.

Two reasons that number cannot be taken at face value here. It is reported as
**directional accuracy, never as return or Sharpe** — on hourly bars, 57%
accuracy is entirely compatible with losing money once the spread is paid,
and this project's own history says the gap between an accuracy figure and a
net Sharpe is where results die. The authors themselves call it "only an
early indication".

**An independent k-means replication (sesen.ai, 2025).** Clustered body,
upper shadow, lower shadow, trend and volatility; k = 5 / 6 / 8 by elbow;
tested 14 discovered patterns with Bonferroni correction. **No pattern
survived.** The evening star came out *positive* despite being traditionally
bearish. Their conclusion: the discovered shapes are "geometrically real but
predictively empty".

**Prior recorded in advance: low.** We are running this because it is the one
family never tested, the data is in hand, and — unlike both prior attempts —
it will be held to era consistency, a destroyed-timing null, N_eff-corrected
significance and a genuinely held-out era.

## The failure mode this test exists to avoid

That same replication states it plainly:

> "Without scaling, higher-variance features dominate the Euclidean distance
> and K-Means effectively clusters on volatility alone."

**This project has been ambushed by exactly that three times.** I1's G3 gate
found plain volatility ordering Sharpe 15x more strongly than tick size. J1's
mirror control scored -0.259 on volatility against +0.016 for the momentum
signal it was controlling for. E2's whole VRP sizing result was realised
volatility appearing on both sides.

If a naive clustering is run here it will rediscover volatility for a fourth
time. So:

1. **Every feature is divided by ATR(14) measured at the bar BEFORE the
   window opens.** Causal, and scale-free by construction (GAUNTLET 1.3).
2. **Features are standardised across the pooled sample before clustering**,
   so no single dimension dominates Euclidean distance.
3. A **vol-capture gate** (G1 below) that can withdraw the whole result.

## Representation — frozen

For a window of k consecutive candles ending at bar t, with A = ATR(14) at
bar t-k:

    body_i   = (close_i - open_i) / A
    upper_i  = (high_i - max(open_i, close_i)) / A
    lower_i  = (min(open_i, close_i) - low_i) / A
    gap_i    = (open_i - close_{i-1}) / A        [i > 1 only]

k in {1, 2, 3}, giving 3, 7 and 11 dimensions. Nothing else — no trend term,
no volatility term, no volume. Adding a trend or volatility feature, as the
prior work did, guarantees the clusters encode trend and volatility; that is
the thing we are trying not to do.

## Method

1. Pool windows across all 21 markets, 2005 to 2026-08-07.
2. Standardise each dimension (mean 0, sd 1) on the **training era only**.
3. k-means, k in {6, 10, 16, 24}, on the training era only.
4. Assign every out-of-sample window to its nearest centroid.
5. Score each cluster's forward return at h in {1, 5, 21} bars against the
   matched control pool.

## Train/test split — new to this project

Cluster on **E1 + E2 (2005 to 2019-06-30)**. Score on **E3 (2019-07-01
onward)**, never touched during clustering or standardisation.

This is the first genuinely held-out discovery test here, and it is
non-optional: an unsupervised search over 21 markets and four values of k
is a large enough hypothesis space that in-sample scoring would be
meaningless. Every headline number comes from E3.

## Control

The b3 matched control, unchanged: for each cluster, the comparison is the
mean forward return of every **non-member** day in the same era, prior-return
decile and volatility decile. Not a global mean, and **not** a window
excluding a band around each detection — that was the b3 defect that
manufactured a +4.67% baseline against a +0.76% unconditional and produced
nine false passes.

## Pass criteria — fixed in advance

A cluster passes only if ALL of:

1. **Held-out effect.** Mean E3 forward return minus its matched control,
   |t| >= 3.0 with the t computed on N_eff, not on the raw row count.
2. **Multiple comparisons.** Benjamini-Hochberg across every cluster x
   horizon x k tested (up to 4 x 3 x 56 = 672 tests). Reported q-value, not
   a raw p. A cluster that needs the uncorrected p is not a result.
3. **Era consistency.** Same sign in E1 and E2 (the training eras) as in E3.
   Cheap to check and it costs nothing to require.
4. **Cluster stability.** Re-cluster with five different random seeds; the
   cluster's membership must reproduce at **>= 80% overlap**. This is B1's
   pivot-perturbation test, which killed the wedges at 41% and 49%, applied
   to centroids instead of pivots.
5. **k-stability.** The cluster must persist as a recognisable centroid at a
   neighbouring k. A shape that exists only at k = 16 is a partition
   artefact.
6. **Cost.** Survives 1bp; reported at 0 and 3bp.

## Gates that can withdraw the result outright

- **G1 vol-capture.** Cramer's V between cluster label and volatility decile.
  If V >= 0.25 the clustering has found volatility regimes rather than candle
  shapes, and the entire run is withdrawn regardless of any cluster's
  p-value. This is the pre-committed answer to the failure mode named above.
- **G2 market-identity.** Same test against market identity. If clusters map
  onto instruments, we have rediscovered that gold is not the Bund. This is
  the a2 defect (88% of bcousd rows in one pooled tercile) in a new place.
- **G3 destroyed timing.** Cluster labels shifted 750 bars. Must not produce
  passes at more than the BH false-discovery rate.

## Kill condition

If no cluster clears criteria 1-6 at any k, discovered candle geometry is
closed for this universe. We would not then move to a different clustering
algorithm, a different window length, or a neural encoder looking for a
version that works — the search space is the problem, not the method.

## What a pass would and would not mean

Even a clean pass would be a **statistical** result on a held-out era, not a
tradeable one. It would still have to clear the noise floor (0.096 Sharpe at
N_eff 5 over 21.6 years), still be expressible through a CFD, and still
survive the forward test that nothing in this project has yet been through.
The honest ceiling on this test is "worth pre-registering a strategy around",
not "worth trading".
