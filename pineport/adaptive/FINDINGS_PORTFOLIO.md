# Portfolio construction — fails, and the reason is worth more than the test

Run 2026-08-27 against `PREREGISTRATION_PORTFOLIO.md`, written before the
instruments were pulled. Reproduce with `python3 g1_diversify.py` and
`python3 g2_portfolio.py`.

## Gate 0 passed — by 0.01

Ten instruments chosen for distance from the long-risk/short-dollar cluster, all
ten fetched:

| | mean pairwise ρ | N_eff | ceiling |
|---|---|---|---|
| original 11, strategy returns | +0.206 | 3.60 | 4.9 |
| **all 21, strategy returns** | **+0.125** | **6.01** | 8.0 |

Threshold was 6.0. It passed at **6.01**, which is a pass and nothing more.
Seven of the ten sit genuinely outside the cluster (mean correlation against the
original eleven under 0.10): corn, Bund, EUR/GBP, natgas, sugar, US 10y, wheat.

## And then the portfolio test fails on four of seven gates

| rule | Sharpe | 2005–12 | 2012–19 | 2019–26 | ann ret | max DD |
|---|---|---|---|---|---|---|
| equal weight | +0.114 | +0.172 | −0.045 | +0.185 | +0.49% | −25.5% |
| inverse vol | +0.078 | — | +0.022 | +0.168 | +0.27% | −21.3% |
| risk parity | +0.101 | — | +0.001 | +0.242 | +0.38% | −23.0% |
| cluster-capped | +0.164 | — | −0.020 | +0.403 | +0.80% | −23.9% |
| shuffled-weight null | −0.058 | — | −0.445 | +0.169 | −0.36% | −22.3% |
| **buy and hold the basket** | **+0.624** | +0.661 | +0.112 | +0.979 | **+4.95%** | −34.0% |

| gate | result |
|---|---|
| 1 · beats equal weighting | only cluster-capped, +0.164 vs +0.114 |
| 2 · in all three eras | **FAIL** — none |
| 3 · plateau across the estimation window | **FAIL** — 63/126/252/504 days give +0.104 / +0.089 / +0.101 / **−0.053**. A range of 0.157 and a sign flip. That is a SPIKE |
| 4 · beats the destroyed-timing null | pass — the null is −0.058 |
| 6 · survives 5bp | **FAIL** — risk parity −0.073, equal −0.051. Everything is negative |
| 7 · beats buy-and-hold, or states the risk case | **FAIL** — +0.164 against +0.624, and a fifth of the return |

Concentration, GAUNTLET 4.2 (gate: top ten under ~40% of profit): the top three
markets are **42%** of all positive contribution, the top five **63%**, the top
ten **90%**.

---

## The finding that matters, and it is not the allocation

**Adding ten uncorrelated markets halved the rule's Sharpe.** Equal weighting
across 21 markets returns +0.114; the same rule on the original eleven returned
+0.267 on direction alone and +0.382 vol-targeted.

The per-market table says why:

| | mean Sharpe | positive | sign-consistent across eras |
|---|---|---|---|
| original 11 | **+0.145** | 9 of 11 | — |
| **the ten unseen markets** | **+0.055** | 6 of 10 | **2 of 10** |
| the ten, excluding the single best | **+0.005** | | |

Sugar alone (+0.504) carries the entire average of the new set. Strip it and
nine genuinely unseen markets return **+0.005** — nil. Only two of the ten hold
their sign across all three eras, and one of those two is negative in all three
(EUR/GBP, −0.359).

**This is the cleanest out-of-sample test of the trend rule in the whole
project.** The eleven markets were the set this work has been circling for
years; these ten had never been looked at. The edge on them is about a
thirtieth of what the familiar markets suggested, once the best single result is
set aside.

## What my own pre-registration got wrong

Gate 0 required N_eff ≥ 6.0. It did not require that the added markets have any
**edge**. That was a real gap, and it let a doomed test through: diversification
multiplies edge, it does not create it, so adding ten uncorrelated markets with
no edge could only dilute — which is exactly what the halved Sharpe is.

The correct form is now **GAUNTLET 0.5**: a market added to raise the effective
sample size must also show edge of the same sign, checked before the portfolio
test rather than after it.

## Where this leaves Phase 3

`NEXT_STEPS.md` proposed portfolio construction as the answer to the exposure
problem — *"a trend rule with a small edge applied to fifteen weakly-correlated
markets is a business"*. The premise was **a small edge on each**. Measured, the
edge is present on a handful of familiar markets, concentrated in three of them,
absent on nine unseen ones, and buy-and-hold beats every version of it.

That is the phase answered. Not by a better allocation rule — by finding out
there was nothing to allocate.
