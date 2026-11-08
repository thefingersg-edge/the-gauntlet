# Pre-registration — I1, tick size x signal speed

Written 2026-09-03, BEFORE computing any relationship between the predictor
and any return. The predictor (tick size) is a static instrument property and
was measured first; no Sharpe was inspected by tier before this file was
frozen.

## Motivation

arXiv:2607.01550 finds that short-term trend-following died after 2008/09 and
that the discriminant is **volatility-normalised tick size**, not asset class
or liquidity. Small-tick contracts collapsed at every horizon; large-tick
contracts were essentially unchanged. Reported Sharpe by signal speed:

| signal | pre-2009 | post-2008 |
|---|---|---|
| 5d | 0.84 | 0.12 |
| 10d | 0.83 | 0.22 |
| 20d | 0.79 | 0.27 |
| 50d | 0.70 | 0.40 |

This study has run a large battery of trend and state-conditioned tests and
found nothing. Two explanations are observationally similar so far:
(a) there is no edge; (b) there is an edge but it lives only in a cell we
never isolated. This test discriminates between them on data we already hold.

## Predictor — frozen

`ticks_per_sd = daily_sd_log * median_price / tick`

Low value = LARGE tick (price moves few ticks per day, dense book).
High value = SMALL tick.

`tick` is the **underlying exchange's** minimum price increment, not OANDA's
quote precision, because the liquidity feedback loop the paper describes
happens in the underlying book. OANDA quotes 1x-15.6x finer than the
exchange depending on instrument, which reorders 6 of 21 markets; rank
correlation between the two measures is 0.842.

Exchange ticks used (in OANDA quote units), sourced from contract specs:

    spx500usd 0.25 (ES)    nas100usd 0.25 (NQ)     de30eur 1.0 (FDAX)*
    cornusd 0.0025 (ZC)    wheatusd 0.0025 (ZW)    sugarusd 0.0001 (SB)
    natgasusd 0.001 (NG)   bcousd 0.01 (ICE B)     usb10yusd 1/64 (ZN)
    de10ybeur 0.01 (FGBL)

    * FDAX tick is the least certain entry — Eurex has revised it. Robustness
      check R3 below re-runs with de30eur dropped.

Spot FX, XAU, XAG, XPT, XCU are OTC and have no exchange tick, so the OANDA
grid is the market grid and is used unchanged.

Resulting terciles (frozen here, before any outcome is computed):

    LARGE : cornusd usb10yusd sugarusd wheatusd de10ybeur spx500usd natgasusd
    MID   : de30eur bcousd nas100usd eurgbp audusd eurusd usdcad
    SMALL : usdjpy gbpusd eurjpy xcuusd xauusd xptusd xagusd

That the LARGE tier came out as commodities plus government bonds — exactly
the group the paper says escaped — is a point in the measure's favour, and it
was not engineered.

## Outcome

Sharpe of each (fast, slow) crossover pair from `core.PAIRS`, net of 1bp per
unit turnover, per market, on the post-R4 daily bars.

## Hypotheses

**H1 (primary).** Over 2009-01-01 onward, market-level mean Sharpe across the
pair grid is *decreasing* in `ticks_per_sd`.
Test: Spearman rho between market rank on `ticks_per_sd` and market rank on
mean Sharpe, n = 21.

**H2.** Sharpe is increasing in signal slowness, and the slope on
`log2(slow)` is *steeper* in the SMALL tier than in the LARGE tier — fast
signals died specifically in small-tick books, slow ones survived everywhere.

**H3 (declared underpowered, reported but NOT scored).** Pre-2009 vs
post-2008 decline is larger for faster signals and for small-tick markets.
Our pre-break window is 2005-2008 = 4.0 years, so SE(Sharpe) per market is
about 1/sqrt(4) = 0.50, and pooled over N_eff ~ 5 blocs about 0.22. The
paper had 14 pre-break years. A null here is uninformative about the paper
and will not be reported as evidence either way.

## Pass criteria — fixed in advance

H1 passes only if ALL of:

1. `rho <= -0.45`.
2. Mean Sharpe of the LARGE tier exceeds the SMALL tier by more than the
   95th percentile of that difference under 2,000 tier-label shuffles.
3. The sign of rho is the same in E2 (2012-2019) and E3 (2019-2026) taken
   separately. E1 is mostly pre-break and is excluded from the consistency
   requirement by design, not after seeing it.
4. The shared-term gate below is cleared.

H2 passes only if the SMALL-tier slope exceeds the LARGE-tier slope and the
gap survives the same shuffle test at the 95th percentile.

## Shared-term gate — GAUNTLET 1.1

`ticks_per_sd` has daily sd in its NUMERATOR. Sharpe has strategy sd in its
DENOMINATOR, and strategy sd is proportional to underlying sd because the
position is +/-1. **The predictor and the outcome share a term**, which alone
would produce a negative rho with no microstructure content whatsoever. This
is the same defect that killed the VRP result, and it is the most likely way
for this test to produce a false pass.

Three checks, all required:

- **G1 disjoint-sample vol.** Recompute `ticks_per_sd` using vol measured on
  2005-2008 only, and correlate against Sharpe measured on 2009+ only. If the
  effect is a shared-term artefact it weakens sharply; if it is real it
  survives, because tick size is a persistent instrument property.
- **G2 partial rank correlation.** rho(Sharpe, ticks_per_sd | daily_sd) must
  keep its sign and retain at least half its magnitude.
- **G3 mirror test.** Compute rho(Sharpe, daily_sd) with tick held out. If
  vol alone explains as much as `ticks_per_sd` does, the tick term is
  decoration and H1 is **withdrawn regardless of its own p-value**.

## Effective sample size — GAUNTLET 3.2

21 markets are not 21 independent observations; N_eff on strategy returns has
been measured at 4.70-6.01 for this universe. All shuffle tests resample
whole markets (stationary block bootstrap, mean block 63 bars) rather than
rows, and no result is reported with a t-statistic that assumes n = 21.

## Robustness

- R1: repeat with cost 0bp and 3bp.
- R2: repeat on the OANDA-grid tick measure; note tier moves, do not rescore.
- R3: repeat dropping de30eur (uncertain FDAX tick).
- R4: repeat with terciles replaced by a continuous rank regression.

## Kill condition

If |rho| < 0.20 AND the H2 slope gap is within the shuffle band, then the
microstructure account does not explain our nulls. In that case there is no
surviving cell of the trend family to target, and we stop testing trend
variants rather than looking for a fourth way to slice the same data.

## What this test cannot do

It cannot establish that a large-tick trend edge is *tradeable by us*. Even a
clean pass leaves GAUNTLET 4.6 open: the mechanism lives in the underlying
exchange order book, and an OANDA CFD is not that book. A pass is a reason to
price futures access, not a reason to trade the CFD.
