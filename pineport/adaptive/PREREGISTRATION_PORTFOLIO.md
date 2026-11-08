# Pre-registration — portfolio construction

Written **before the diversifying instruments are pulled**, 2026-08-27. Held to
`../GAUNTLET.md`. This is Phase 3 of the project's own roadmap
(`NEXT_STEPS.md`): *"multiple uncorrelated markets rather than more cleverness
on one"*. It has never been reached.

## What has actually been done so far, and why it is not this

Every result in this project is **per-market, then equal-weighted**. That is an
average, not a portfolio. It says nothing about whether allocating by risk and
correlation turns a 0.2-Sharpe rule into something a portfolio would want.

## The gate that comes first

`g1_diversify.py` measures the effective sample size of the expanded set.
Current state, eleven markets:

| | mean pairwise ρ | N_eff | ceiling (1/ρ) |
|---|---|---|---|
| asset returns | +0.294 | **2.79** | 3.4 |
| strategy returns | +0.206 | **3.60** | 4.9 |

**Pre-registered gate: N_eff on strategy returns must reach ≥ 6.0** before any
portfolio rule is tested.

If the ten diversifying instruments do not lift it that far, **the portfolio
question is answered without running it** — correlation-aware weighting cannot
deliver what the diversification argument promises across three or four
effective bets, and reporting that is the result. This is written down now so
that a disappointing N_eff cannot be followed by "let's test the rules anyway
and see".

## The claim, if the gate passes

Allocating the same per-market rule by risk and correlation delivers materially
better risk-adjusted return than equal weighting, and the improvement grows with
the number of effective bets.

The mechanism does not reference a backtest: with N independent bets of equal
edge, portfolio Sharpe scales as √N. That is arithmetic, not a discovery — which
is exactly why the interesting question is how far short of it the real,
correlated set falls.

## Rules compared

Direction and sizing per market are **frozen** — `sign(A)` with the
inverse-volatility sizing from `FINDINGS_IVSIZE.md` where a volatility index
exists, trailing realised elsewhere. Only the allocation across markets varies.

| rule | weights |
|---|---|
| **equal weight** | the incumbent, and the benchmark to beat |
| inverse volatility | ∝ 1 / trailing vol |
| risk parity | inverse vol adjusted for the correlation matrix |
| cluster-capped | equal weight within correlation clusters, equal across clusters |

Every estimate causal: rolling or expanding windows, no full-sample covariance.

## Gates

| # | criterion | threshold |
|---|---|---|
| 0 | **N_eff on strategy returns** | ≥ **6.0**, or stop |
| 1 | pooled Sharpe beats equal weighting | yes |
| 2 | beats it in **all three eras** | 3 of 3 |
| 3 | **plateau** across the covariance estimation window (GAUNTLET 3.6) | plateau, not spike |
| 4 | beats a **destroyed-timing null** — same weight distribution, 750-day lag (GAUNTLET 3.5) | yes |
| 5 | **shared-term check** (GAUNTLET 1.1): volatility appears in the per-market sizing *and* in the weights. Re-run with per-market sizing held constant so the allocation is the only thing varying | must survive |
| 6 | survives **5bp**, and turnover is reported per rule | yes |
| 7 | beats **buy-and-hold the same basket**, or the risk case is stated explicitly in writing | one or the other |

Gate 5 is the one this project has already paid for twice. Inverse-vol sizing
inside the market and inverse-vol weighting across markets are the same quantity
used twice; if the second is not tested with the first held fixed, any gain is
unattributable.

Gate 7 is the one that has ended every previous study. The best rule measured so
far returns Sharpe 0.382 against the basket's 0.571.

## Stated in advance

The honest prior is that risk parity beats equal weighting by a **small** margin
and that most of the gain is volatility scaling, which this project has already
established works. A result in that range is a confirmation of something known,
not a discovery, and will be reported as such. The finding worth having is
whether raising N_eff changes anything at all — and if the gate fails, that
the ceiling was structural rather than a matter of effort.
