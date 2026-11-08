# Findings — K1, hedging pressure from CFTC COT

Pre-registered in `PREREGISTRATION_COT.md`. Run 2026-09-03 on 16 markets,
2005-01-03 to 2026-08-07, post-R4 daily bars.

The first test in this project whose predictor is not a price.

## Verdict

**FAIL. Kill condition MET.**

| criterion | required | actual | |
|---|---|---|---|
| 1. Sharpe | >= +0.29 | **+0.2150** | FAIL |
| 2. era sign consistency | all three agree | +0.427 / **-0.425** / +0.435 | FAIL |
| 3. beats destroyed-timing null | > null p95 | +0.215 vs p95 **+0.435** | FAIL |
| 4. holds at 3bp | >= +0.29 | +0.2057 | fails 1, robust to cost |
| 5. plateau 9/12/18m | same sign | +0.210 / +0.215 / +0.204 | PASS |
| 6. class check | reported | see below | PASS (reported) |

Ann return +1.40%, ann vol 7.94%, turnover 3.7 units/yr. Noise floor for
21.6 years at N_eff 5 is 0.096, so +0.215 is about 2.2 SE — real enough to
see, well under the 3 SE bar set in advance.

## The three failures, in order of how much they matter

**Criterion 3 is the serious one.** The destroyed-timing null — the same
signal lagged 750 bars, so any real timing content is destroyed — scores
+0.070, but its block-bootstrap 95th percentile is **+0.4348**. The live
result of +0.2150 sits comfortably inside that band. With N_eff around 5,
the sampling distribution of this Sharpe is wide enough that +0.215 is not
distinguishable from a signal with its timing deliberately destroyed.

**Criterion 2 is the most informative.** The eras do not merely disagree in
magnitude, they invert: **+0.427, -0.425, +0.435**. A signal that pays,
reverses, then pays again is not a weak edge — it is a coin that landed
heads twice out of three. The reversal is not isolated to one bloc; it shows
up in commodities (+0.39 / -0.26 / +0.31) and FX (+0.15 / -0.31 / -0.13)
alike.

**Criterion 1** it misses by a distance that criteria 2 and 3 make moot.

## What passed, and it is worth recording

- **Cost robustness.** +0.220 at 0bp, +0.215 at 1bp, +0.206 at 3bp. Turnover
  is only 3.7 units/yr — the 12-month averaging makes this an allocation
  tilt, not a trading rule, exactly as the published construction intends.
- **Plateau, not spike.** 9m +0.210, 12m +0.215, 18m +0.204. Whatever is
  there is not a single lucky parameter.
- **The mirror check clears.** Ranking on 1/OI alone scores **-0.048**. So
  the signal is not an open-interest tilt wearing a hedger label. Unlike the
  VRP result, this one is not an artefact — it is simply too weak and too
  unstable.

## By class

The published result is not uniform, so the prereg required this split.

| basket | n | ours | published (1992-2016) |
|---|---|---|---|
| commodities | 8 | **+0.185** | 0.506 |
| FX | 5 | **-0.056** | 0.375 |
| equity index | 2 | +0.376 | 0.486 |
| rates | 1 | no cross-section possible | -0.238 |

Commodities — the basket with the strongest published result and the
clearest economic story — comes in at about a third of the published Sharpe
and still inverts in E2.

FX comes out **negative** against a published +0.375.

Equity is the only cell above the 0.29 bar, and it is not a finding:
n = 2 makes the "cross-section" a single spread, long one of S&P and Nasdaq
and short the other. Its E1 is negative (-0.05), and it is the best of four
cells inspected. The published equity result itself carried a panel logit
t of 0.13 — a respectable Sharpe attached to no significance at all.

## A bug found in this run

The first pass reported `nan` for the FX and equity baskets. `zweights()`
required at least 8 live markets for a date to be ranked — a threshold
written for the 16-market panel and then applied unchanged to sub-baskets of
5 and 2, so **pre-registered criterion 6 did not execute at all**. The width
rule now scales with the basket.

Worth noting how it presented: not as an error, but as a `nan` in a results
table, next to numbers that looked fine. Same failure shape as the COT
contract renames — the thing that stops working does not announce itself.

## Why this might not replicate

Candidates, not conclusions:

1. **Sample.** Ours is 2005-2026; theirs 1992-2016. The overlap is partial
   and our window is the more recent, so post-publication decay is available
   as an explanation and cannot be separated from the others here.
2. **Universe.** 16 markets at N_eff ~5 against their much larger panel. Our
   commodity basket is 8 names covering metals, grains and energy — three
   blocs, not eight bets.
3. **Vehicle.** GAUNTLET 4.6. The positions are in the futures; we would
   hold a CFD referencing the same underlying, with different basis and
   funding.
4. **Revisions.** CFTC restates, and the Socrata series is presumably
   as-revised. That biases *towards* a false pass, so it cannot explain a
   failure — noted for completeness.

## Kill condition

Pre-registered: "If S fails criterion 1 in the cross-sectional specification
and the commodities sub-basket alone also fails, positioning data is closed
for this universe."

Criterion 1 failed (+0.215). Commodities alone failed (+0.185). **The kill
condition is met.** We do not now move to the disaggregated or
traders-in-financial-futures reports looking for a version that works.

## Standing — the point the pre-registration anticipated

With K1 closed, this project has tested, each pre-registered in advance:

    A  price-based trend and adaptive lookback
    B  chart shapes and reversal patterns
    C  cross-market agreement
    D  real-yield macro conditioning
    E  implied-volatility / variance risk premium
    F  IV-based position sizing
    G  portfolio construction and diversification
    H  combined multi-signal stack
    I  microstructure: tick size x signal speed
    J  cross-sectional ranking (pre-registered, not yet run)
    K  non-price positioning data

Nothing has cleared its pre-registered bar. The nulls are not the product of
broken tests — the code review found 13 material defects and none of them
manufactured a rejection; every one made finding something *easier*.

The honest conclusion is the one written into the K1 pre-registration before
this ran: **this universe, at this cost structure, through this vehicle,
does not support a systematic edge we can find.** The remaining options are
to change the vehicle — futures access, where the tick-size mechanism in I1
actually lives and where the COT positions actually sit — or to stop.

J1 remains pre-registered and unrun. It should be run for completeness of
the record, with the expectation stated in its own prereg: a low prior, and
a cross-section of 21 names that is really about five independent blocs.
