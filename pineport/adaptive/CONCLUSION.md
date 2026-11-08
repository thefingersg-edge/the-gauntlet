# Conclusion — v2, 2026-09-20

Seventeen pre-registrations across fifteen families. Fourteen did not clear
their bar. **Family F passed its primary** — see the correction below.

> **CORRECTION 2026-09-21.** v1 and v2 of this file listed family F as "no
> improvement over constant sizing". That describes only its *secondary*
> claim (Sharpe), which its pre-registration predicted would not be
> established. Its *primary* — implied vol targets realised risk better than
> trailing realised vol — passed every gate and replicated out of sample
> (`FINDINGS_IVSIZE.md`, `FINDINGS_IVSIZE_REPLICATION.md`). The error was
> carried from v1 into v2 without reopening the source file.
>
> **The view across all projects is `../../PROGRAMME.md`.** This file is
> pineport's conclusion only; `fastbot/` measured four real premia that this
> file does not cover.
Supersedes v1 (2026-09-03, eleven families) — kept at `CONCLUSION_v1.md.bak`.

## The record

| | family | predictor | result |
|---|---|---|---|
| A | trend, adaptive lookback | price | no state variable predicts the right lookback |
| B | chart shapes, reversals, pattern zoo | price | t +0.18 / +1.25; H&S t +1.47 after the control fix |
| C | cross-market agreement | price | inside null |
| D | real-yield macro | rates | sign map not reproducible out of sample |
| E | variance risk premium | implied vol | as a *direction* signal: 0 of 5 gates, withdrawn. The premium itself exists at 10 sigma — `fastbot/RESULT_VRP.md` |
| F | IV-based position sizing | implied vol | **primary PASSED** — IV targets risk better than trailing RV on 4/4, replicated on NAS100 and silver; secondary (Sharpe) not established, as pre-registered |
| G | portfolio construction | price | Gate 3 now PASSES post-R2/R3; G1 bootstrap 5.06–7.24 straddles the 6.0 gate |
| H | combined stack | price | basket was hand-picked post hoc |
| I | tick size x signal speed | microstructure | rho +0.014 vs required -0.45; wrong sign |
| J | cross-sectional ranking | price | +0.016 / -0.076 / +0.033 vs +0.29 |
| K | hedging pressure | positions, not price | +0.215 vs +0.29; eras +0.43 / -0.42 / +0.44 |
| L | discovered candle geometry | price, unsupervised | 462 tests, max abs t 1.97, min q 0.9884, 0 pass |
| M | volatility asymmetry (RSJ) | realised higher moments | -0.118, wrong direction; plain reversal beat raw RSJ |
| N | pattern zoo on H1 | price, intraday | 75 tests, min q 0.9810, 0 era-consistent |
| O | Kalman velocity trend | state-space filter | +0.5396, clears floor 3.5x, **dies on eras** |

## How they died — the failure modes are not uniform

    inside the noise band          A, C, G, J, L, N
    wrong sign / direction         I (rho +0.014 vs -0.45), M (RSJ opposite to literature)
    era sign inconsistency         K (+0.43/-0.42/+0.44), O (+0.94/-0.03/+0.63)
    beaten by the dumb version     M (plain reversal > raw RSJ)
    withdrawn on a control         E (shared term), H (post-hoc basket)
    not reproducible out of sample D

Six families died on effect size. Four died on something more informative
than size — direction, stability, or losing to a simpler rule. Those four are
where the actual knowledge is.

## The one variable that recurs: volatility

Four independent families found volatility either outscoring the hypothesis
or requiring explicit control to stop it masquerading as one:

    I1  G3 mirror        vol orders Sharpe 15x more strongly than tick size
    J1  mirror on 1/vol  -0.2594, larger than all three momentum signals
    L1  G1 Cramer's V    0.031-0.068 — passed only because the prereg
                         anticipated k-means clustering on vol alone
    E   VRP              whole family collapsed under IV-normalisation

**In this universe volatility is the only variable that reliably orders
anything.** Ordering by volatility is not a directional edge — it is a
risk-scaling fact — but it is the single most robust empirical regularity the
project has produced, and every family that failed to control for it would
have produced a false positive.

## What replicated — the trend break, now measured three times

The break is the most reproducible result in the project, and none of the
three measurements was designed to find it:

    G/I  21-market portfolio (16,128)   +1.259 pre-2009  ->  +0.201 post-2008   (-84%)
    I1   slowest daily signals          +0.410 pre       ->  +0.026 post  (182 cal days)
                                        +0.372 pre       ->  +0.001 post  (364 cal days)
    O1   EMA(200) component, 4h         +1.205 E1        ->  +0.079 E3

arXiv:2607.01550 reports -86% for its fastest signals. We get -84%.

**O1 independently reproduces I1 without being built to.** Family O was a
replication of an external crypto strategy on a 4h grid; its trend component
collapses from +1.21 in E1 to +0.08 in E3, landing on top of I1's +0.026 /
+0.001 for slow daily signals post-2008. Two families, different data
granularity, different construction, same number.

What does NOT replicate is the paper's *survivor*: large-tick markets keeping
Sharpe 0.40. In our data the large-tick tier is the worst of the three, and
our slowest signals sit at +0.026 and +0.001, not +0.40.

I1's kill condition explicitly closed trend-speed variants. O1's result does
not reopen them — it corroborates the closure.

## The sharpest single result: sophistication does not pay

Family O cleared its noise floor — the only externally-sourced strategy to do
so — at +0.5396 against a 2 SE floor of 0.1528, bootstrap p 0.0146, q 0.0292.
Then:

    full rule (Kalman + EMA200 + chandelier)   +0.5396
    EMA(200) alone, no Kalman at all           +0.4163
    margin                                     +0.1233
    noise floor on that estimate                0.1528

**The margin over a 200-period moving average is smaller than the measurement
error.** A two-state filter with a covariance recursion and a tuned
process-noise ratio bought nothing detectable over an idea from the 1970s.

Read across the whole programme, the families ascend in sophistication —
moving averages, chart shapes, cross-market agreement, macro, options-implied,
portfolio construction, microstructure, cross-section, positioning data,
unsupervised discovery, realised higher moments, state-space filtering — and
the most sophisticated do not outperform the simplest. O1 is the cleanest
demonstration because it contains its own control.

## Why O1 actually failed — turnover against a thin gross edge

At zero cost O1 is the **only** era-consistent row in its table:

    0 bp/side   +1.287 / +0.425 / +1.044     era-consistent
    1 bp/side   +0.944 / -0.026 / +0.631     FAILS
    3 bp/side   +0.258 / -0.926 / -0.192     FAILS

    break-even 2.36 bp/side (~4.7 bp round trip), 36.1 trades per market-year

E2 is not a period where the signal stops working. It is a period where the
gross edge is too thin to pay for its own turnover. That is a more useful
statement than "the edge disappeared", and it generalises: at 36 trades per
market-year, an edge must clear ~4.7 bp round trip before it exists at all.

This is a diagnosis of the failure, not a rescue of it. The pre-registered
primary is 1 bp and it failed on its own terms.

## The methodological finding worth keeping

Realised N_eff on cross-sectional portfolios is **8.8–9.9**, against 4.7–6.0
for every time-series portfolio here. Dollar-neutral construction differences
out the common market factor, so the same 21 names carry roughly twice the
independent information. The J1 pre-registration predicted the opposite.

**If anything is ever traded here, build it cross-sectionally.** The
diversification is free and substantial.

## Why the nulls are trustworthy

The adversarial review found 13 material defects (`CODE_REVIEW.md`). **Not one
manufactured a rejection** — every one made finding an effect easier. The
defects that sat under reported numbers were all in the G/H portfolio cluster
and all flattering.

Two of our own false positives were caught by pre-registered controls rather
than by review: VRP's shared term (`IV - RV` against `|fwd| / RV`), and the
pattern zoo's control pool, where excluding a +/-21 bar window around each
detection produced a +4.67% baseline against a +0.76% unconditional and nine
"passes" vanished.

Two data defects of the same class were found and fixed, a year apart in the
code and one timeframe apart in effect:

    R4   daily bars rolled at 21:00 UTC instead of 17:00 New York
         1,590 eurusd bars misassigned, touching 28.0% of all days
    h4   resampled_h4/ built on the 00/04/08/... UTC grid; ZERO timestamps
         shared with OANDA's native H4. Rebuilt DST-aware: 316,570 bars
         validated against native, 0 mismatches

Both were found by asking what the broker's own clock does, not by a test
failing.

## What is entangled and cannot be separated with this data

- **The vehicle.** GAUNTLET 4.6 kept returning. I1's mechanism lives in the
  exchange order book, which a CFD does not touch; K1's positions are in the
  futures, not the CFD. Twice the test we needed is one this account cannot run.
- **The sample.** 21.6 years at N_eff ~5 gives a noise floor of 0.096. Any
  edge below roughly 0.3 Sharpe is undetectable here whether or not it exists.
- **The era.** Most of the sample is post-2008, and the one effect we can
  measure cleanly is that trend died then.

## The honest conclusion

This universe — 21 OANDA CFDs, 2005–2026, at retail cost — does not support a
systematic edge this programme can find. That is a statement about the search,
the sample and the vehicle, not a proof that none exists.

## What is left

1. **The forward test.** The only source of genuinely new information. RULES
   v2 frozen, Pine restored from 20 parameters of drift, sizing floored to the
   0.1 OANDA grid, limits set. ~33 trades, about 2.2 years to a verdict.
   Everything else re-cuts the same 21 markets over the same 21.6 years.
2. **Open decision.** Risk per trade is 2.0%; 0.8% is now known reachable
   (floor ~$2,940, not $11,750). Reverting needs RULES.md and one Pine input.
3. **Two leads deliberately not chased.** Volatility as a cross-sectional
   orderer, and NYMEX Brent in the COT data. Both require fresh
   pre-registration. Note honestly that vol-as-orderer keeps appearing
   *because it was always the control* — promoting a control to a hypothesis
   after seeing its number is precisely what this apparatus exists to prevent.
   It is testable cleanly, on held-out construction, or not at all.
4. **Change the vehicle.** Priced: ~$4,560/yr and ~$1M capital, and integer
   contract granularity breaks the one surviving construction result.
   Recommended against at this account size.
5. **What NOT to do.** Reopen a closed family with a fourth parameter. Every
   kill condition here was written before its result was known and each fired
   on its own terms.

The most valuable asset the project now holds is not a signal. It is fifteen
pre-registered negatives with adversarial review, two self-caught false
positives, a published trend break reproduced three separate ways, and a
state-space filter that loses to a moving average.
