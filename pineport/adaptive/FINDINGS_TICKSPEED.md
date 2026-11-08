# Findings — I1, tick size x signal speed

Pre-registered in `PREREGISTRATION_TICKSPEED.md`, frozen before any outcome
was computed by tier. Run 2026-09-03 on the post-R4 daily bars.

## Verdict

**H1 FAIL. H2 FAIL. Kill condition MET.**

The volatility-normalised tick size does not order trend performance in this
universe. We stop testing speed and microstructure variants of the trend
family.

## H1 — Sharpe (2009+) vs ticks_per_sd

    rho = +0.014          pass required <= -0.45
    LARGE - SMALL mean Sharpe = -0.0480   shuffle p95 +0.1339   p = 0.729

Not merely insignificant — the sign is *wrong*. Positive rho means higher
ticks_per_sd (smaller tick) went with higher Sharpe, the opposite of the
paper's prediction.

Per-tier mean Sharpe, 2009+:

| tier | n | mean | median |
|---|---|---|---|
| LARGE | 7 | -0.0211 | -0.0094 |
| MID | 7 | -0.0820 | -0.0933 |
| SMALL | 7 | +0.0269 | -0.0242 |

Era signs disagree: E2 rho = +0.283, E3 rho = -0.208.

## H2 — speed slope by tier

    LARGE  +0.0159 Sharpe per doubling of lookback
    MID    +0.0325
    SMALL  +0.0154
    SMALL - LARGE gap = -0.0005

There is a mild general preference for slower signals — about +0.02 Sharpe
per doubling — but it is the *same* in every tier. The predicted interaction
(fast signals dying specifically in small-tick books) is absent.

## Shared-term gate

    G1 disjoint-sample vol:  rho = -0.019  (vs full-sample +0.014)
    G2 partial rho | sd:     rho = +0.019
    G3 mirror rho(Sharpe,sd) with tick held out: +0.206

G3 is the informative one. Plain volatility orders Sharpe **15x more
strongly** than ticks_per_sd does. Under the pre-registered rule this
withdraws the tick term as decoration — but since H1 failed on its own
criteria the point is moot.

## Robustness

    R1 cost 0bp   rho = +0.040
    R1 cost 3bp   rho = +0.018
    R2 OANDA grid rho = +0.183   (6/21 markets change tier)
    R3 no de30eur rho = -0.002

Nothing moves it off zero.

## The portfolio check — added after the fact, and why

The pre-registration compared *average per-market* Sharpe, but the paper
reports a *portfolio* Sharpe over ~100 futures. Those are not the same
number: with N_eff ~5 a diversified portfolio Sharpe is several times its
average constituent's. Declaring a kill on the wrong metric would have been
a mistake, so the comparison was redone properly — equal-weight, causally
vol-scaled, 1bp.

Portfolio Sharpe, pair (16,128):

| window | LARGE | MID | SMALL | ALL 21 |
|---|---|---|---|---|
| pre 2005-08 | +0.528 | +0.990 | +1.255 | **+1.259** |
| post 2009+ | +0.131 | +0.151 | +0.157 | **+0.201** |

Whole pair grid, post-2008: LARGE **+0.060**, MID -0.081, SMALL **+0.213**.

The conclusion survives the correction, and gets sharper: the LARGE-tick
tier is the *worst* of the three post-2008, not the best.

## What DID replicate

The collapse itself. The 21-market portfolio at (16,128) fell from +1.259
pre-2009 to +0.201 post-2008 — an **84% decline**, squarely in line with the
paper's 86% for its fastest signals. Monotone in speed, all markets pooled:

| slow | cal days | pre | post |
|---|---|---|---|
| 8 | 11 | -0.030 | -0.109 |
| 16 | 23 | +0.158 | -0.035 |
| 32 | 45 | +0.306 | -0.071 |
| 64 | 91 | +0.231 | -0.042 |
| 128 | 182 | +0.410 | +0.026 |
| 256 | 364 | +0.372 | +0.001 |

So we reproduce the *break*. What we cannot reproduce is the part that
mattered to us: the surviving post-break edge. The paper keeps 0.40 at
50 days; our slowest signals sit at +0.026 and +0.001.

## Why the survivor might not appear here

Stated as candidates, not conclusions:

1. **Universe.** 21 CFDs against their ~100 futures. Our LARGE tier is 7
   markets with N_eff well under that.
2. **Vehicle.** We hold CFDs. The mechanism the paper describes lives in the
   underlying exchange order book, which a CFD does not touch. If the
   residual edge is a book effect, this data cannot show it and we could not
   trade it anyway (GAUNTLET 4.6).
3. **Construction.** They vol-scale continuous positions across a large
   diversified book; we take sign(+/-1) per market.

Note that (2) is not a reason to keep looking with this data. It is a reason
to stop, because it says the test we would need is one this account cannot
run and this vehicle cannot express.

## Consequence

The kill condition is met and is being honoured. No further trend-speed,
trend-state or microstructure-conditioned variants.

One boundary case, decided rather than left open: the overnight/intraday
session split (Lou/Polk/Skouras) was on the shortlist. It is **not being
built**. Its mechanism is equity-specific — retail-versus-institutional flow
around the open and the closing auction — and 24/5 FX and commodity CFDs
have neither an auction nor a true overnight gap. It is also, structurally,
one more way of slicing the same trend data, which is what the kill condition
exists to stop.

What remains genuinely unexplored is not in this family at all: the
cross-sectional object (J1) and non-price positioning data (K1). Both are
pre-registered separately.
