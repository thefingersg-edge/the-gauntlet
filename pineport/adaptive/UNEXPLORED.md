# Unexplored territory — literature scan, 2026-09-03

What we have NOT tested, ranked by (evidence quality) x (data we already
hold) x (can it be expressed in an OANDA CFD account).

Everything tested to date has been **time-series**: each market against its
own history. That is one family out of six or seven.

---

## The single most important paper for this project

**"Is Trend Still Your Friend? A Microstructural Account of the Demise of
Short-Term Trend-Following"** — arXiv:2607.01550. ~100 liquid futures,
1995-2025.

Sharpe by signal speed, pre- vs post-2008/09 break:

| Signal | Pre-2009 | Post-2008 | Change |
|---|---|---|---|
| 5-day  | 0.84 | 0.12 | -86% |
| 10-day | 0.83 | 0.22 | -73% |
| 20-day | 0.79 | 0.27 | -66% |
| 50-day | 0.70 | 0.40 | -43% |

The discriminant is **volatility-normalised tick size**, not asset class and
not liquidity. Small-tick contracts show complete PnL collapse at every
horizon. Large-tick contracts are essentially unchanged. Commodities and
government bonds largely escaped.

Mechanism: trend was a self-fulfilling feedback loop — trend trades' own
market impact reinforced the move that generated the signal. Post-2008 HFT
market-making withdrew from sparse (small-tick) books, so predictable
directional flow no longer finds liquidity to push against. In dense
(large-tick) books enough residual depth remains for the loop to survive.

Authors: *"The break is structural; we see no plausible scenario in which it
reverts absent a corresponding structural change."* They recommend capacity
be estimated **at the tick-size tier**, not the asset class.

### Why this matters to us specifically
1. It explains our nulls without needing our tests to be wrong. We were
   testing fast signals (SMA 16, 15-minute and daily bars) on a mostly
   small-tick universe, over a sample dominated by the post-break era.
2. It is a **testable discriminant we have never applied**: stratify our own
   existing results by volatility-normalised tick size and by signal speed.
   That is a reanalysis of data we already hold — no new fetch.
3. It is bad news for the vehicle. A CFD has no order book of its own; the
   effective tick and spread are the broker's. If the surviving edge lives in
   large-tick order-book structure, a CFD is the wrong wrapper for it
   (GAUNTLET 4.6 — name the implementation vehicle).

---

## Tier A — testable on data we already hold

### A1. Tick-size x speed stratification of our own results
Re-cut every Part A/B/D result by (a) signal lookback in *calendar* days
(not bars — see CODE_REVIEW R4) and (b) volatility-normalised tick size of
the underlying. Pre-registered prediction from the paper: slower signals on
large-tick markets should be the only cell with a positive mean, and it
should be weak. If our data shows the effect at *every* speed and tick tier
equally, our null is a measurement artefact rather than a real absence.
Cost: zero new data. This is the highest-information test available to us.

### A2. Cross-sectional momentum — never tested at all
Rank the 21 markets each month, long the top quintile / short the bottom.
This is a different statistical object from time-series momentum: it is
market-relative, it is dollar-neutral, and it survives some regimes where
time-series momentum dies.

Evidence is mixed and worth knowing before we run it: in 35 commodity
futures over 2004-2020, a *trend* factor built from short/intermediate/long
moving averages "outperforms the momentum factor by more than nine times in
the Sharpe ratio", while conventional cross-sectional momentum "delivered
insignificant results" in the financialised era. Equity XS momentum has
declining returns and is crash-prone, though volatility scaling and
market-state conditioning help.

So the honest prior is *weak*. But it is the one whole family we have never
looked at, and it costs nothing to run.

Caution: with N_eff ~4.7-6 across our 21 markets (CODE_REVIEW R1), a
quintile sort gives roughly 4 names a side and the cross-section is close to
degenerate. Pre-register that N_eff constraint before running, or we will be
sorting noise.

### A3. Overnight vs intraday decomposition — never tested
Lou, Polk and Skouras ("A Tug of War: Overnight Versus Intraday Expected
Returns") show that momentum and reversal accrue in *opposite* sessions, and
that pooling them cancels much of the effect. Every test we have run pools
them. We hold M15 and H1 bars, so the split is free.

Pre-registration sketch: decompose each market's daily return into
close-to-open and open-to-close, re-run the Part A signal battery separately
on each, and require the sign to be consistent across eras in the *same*
session. Direct test of whether our nulls are two opposing effects cancelling.

---

## Tier B — needs data we can get free, but new plumbing

### B1. Hedging pressure from CFTC Commitments of Traders
The most attractive untested item after A1. Free, weekly, back to the 1980s.

Fernandez-Perez et al., 1992-2016, signal = net short positions of hedgers
averaged over a **12-month** lookback (long window deliberately, to strip
seasonal production swings and short-horizon speculator noise):

| Asset class | Ann. return | Sharpe |
|---|---|---|
| Commodities | 3.71% | 0.506 |
| Equities | 4.46% | 0.486 |
| Currencies | 1.77% | 0.375 |
| Fixed income | -0.70% | -0.238 |

Panel logit t-stats: commodities 2.98, currencies 1.71, equities 0.13.

Notes before we get excited: fixed income shows *nothing*, which means the
mechanism is not universal; the 12-month average is a very slow signal, so
this is an allocation tilt not a trading rule; and the published Sharpes are
gross of the CFD funding we now know to charge (CODE_REVIEW R5).

Data path: `publicreporting.cftc.gov` has a downloadable API. Legacy and
disaggregated reports both available. Weekly, Tuesday snapshot published
Friday — so a 3-day reporting lag that must be honoured in the backtest.

### B2. Carry and term structure — the best-documented non-price family
Quantpedia's canonical commodity term-structure spec: each month buy the 20%
of commodities with the highest roll return, short the lowest 20%, equal
weight. 1979-2004: **11.73%/yr, 23.84% vol, Sharpe 0.49, max drawdown
-78.06%.** Koijen/Moskowitz/Pedersen show carry predicts returns across most
asset classes and that diversifying carry across classes beats currency-only.

Two caveats that matter: the carry factor loads on innovations in global
equity volatility, so it pays badly exactly when you need it; and
performance degraded markedly in financialised commodity markets after 2004.

**Implementation blocker.** An OANDA CFD does not expose the futures curve.
We can observe the front-month proxy price and the broker's funding rate,
but not the basis between contract months, which *is* the signal. Two
sub-cases:
- **FX carry is reachable** — the swap/funding differential is the carry, and
  we already pay or receive it. Testable now.
- **Commodity carry is not reachable** without a futures curve feed. Adding
  one is a real data project, not a script change.

### B3. Calendar and seasonality — cheap, poor prior
Turn-of-month in US equities is **gone**: through Feb 2025 the classical
[0:3] window is not statistically significant. The wider [-3:3] window still
shows 5-12bp/day with significance, strongest outside the US (Brazil 23bp,
then Sweden, Hong Kong). Critically for us: *"bonds, commodities and Bitcoin
show minimal TOM effects"* — which is most of our universe.

Commodity seasonality is stochastic rather than deterministic; the amplitude
of the seasonal cycle has decreased over the sample, particularly at the end,
and the term-structure literature does not establish that any of it is
unpriced.

Verdict: run it because it is nearly free, but pre-register a low prior and
do not go looking for the one month that worked.

---

## Tier C — evidence says don't bother, or we can't reach it

### C1. News and sentiment
"Buy the Rumor, Sell the News: When Is News Priced In?" (arXiv:2608.14014)
— 1.68M stock-day events, 4.57M articles, LLM-tagged.

The headline result is a warning, not an opportunity: **by the close on
publication day, prices had already moved 2.8x further in the news direction
than where they would sit 20 days later.** For rumour-flagged events, "the
rumour day captures the entire move and the subsequent confirmation
contributes nothing."

After controlling for background drift with neutral-sentiment events, the
residual splits:
- *Fundamental* news (earnings, guidance, analyst actions): +0.22% to +0.35%
  drift over days 6-20.
- *Story* news (product launches, leadership changes, macro commentary):
  **-0.18% to -0.34%** — it reverses.
- Scheduled events: +0.08% adjusted drift (p=0.03). Unscheduled: none.

Why this is not for us: the surviving effects are single-name equity events
and need an LLM-tagged corpus with story clustering and a placebo control
group. Our universe is FX, metals, energy, ags and index CFDs, where there
is no per-name earnings event to tag. The infrastructure is a project in
itself and the residual is a third of a percent.

### C2. Options skew, risk reversals, gamma
Requires an FX/commodity implied-volatility surface, not just the ATM
indices we pulled from FRED. That is a paid feed. Park it.

### C3. Variance risk premium — independent confirmation we were right
Chicago Fed WP 2025-17 finds a structural break in the VRP around 2010, with
the tests dating the inflection to **May 2012**. Traded index-option
information ratios moved from about -0.75 (1987-2005) to **+0.09** after.
Dealer net gamma went from consistently negative pre-2012 to centred on zero.
Cause: reduced intermediary constraints — spreads narrowed, basis risk fell
roughly tenfold, and hedge funds and structured-product desks took over the
risk-bearing.

This matters for our own VRP work. We withdrew it because of a shared-term
artefact, which was the right call for the wrong reason: the premium itself
substantially left the market in 2012, which is *inside* our sample. A
strategy premised on it would have been fitting a regime that had already
ended.

---

## STATUS 2026-09-03 — A1 run, and it failed

A1 was pre-registered (`PREREGISTRATION_TICKSPEED.md`) and run
(`FINDINGS_TICKSPEED.md`). **The tick-size discriminant does not appear in
this universe.** rho = +0.014 against a required <= -0.45, wrong sign, era
signs disagree, and plain volatility orders Sharpe 15x more strongly than
ticks_per_sd does. On the paper's own metric — portfolio rather than average
Sharpe — the LARGE-tick tier is the *worst* of the three post-2008 (+0.060
vs SMALL +0.213).

What did replicate is the break itself: the 21-market portfolio fell from
+1.259 pre-2009 to +0.201 post-2008, an 84% decline against the paper's 86%.
What does not replicate is the survivor.

The pre-registered kill condition fired. **A3 (overnight/intraday) has been
dropped rather than built** — its mechanism is equity-specific (retail flow
around the open, the closing auction) and 24/5 CFDs have neither, and it is
structurally one more slice of the same trend data.

**J1 and K1 have since been run. Both failed; both kill conditions fired.**

- J1 cross-sectional: S1 +0.016, S2 -0.076, S3 +0.033 against a +0.29 bar.
  All three flip sign across eras and sit inside their own destroyed-timing
  null bands. See `FINDINGS_XSECTION.md`.
- K1 hedging pressure: +0.215 against +0.29, eras +0.43 / -0.42 / +0.44.
  See `FINDINGS_COT.md`.

That closes every family listed in this document. The testing arc is
complete; see `CONCLUSION.md`.

## Recommended order (as written before A1 ran)

1. **Fix R4 first** (see CODE_REVIEW.md). Everything below is denominated in
   bars-per-year and would need re-running otherwise.
2. **A1** — tick-size x speed stratification. Zero new data, and it is the
   test that distinguishes "no edge exists" from "we measured it wrong".
3. **A3** — overnight/intraday split. Zero new data, direct test of whether
   our nulls are cancellation.
4. **A2** — cross-sectional momentum, with the N_eff constraint
   pre-registered up front.
5. **B1** — COT hedging pressure. Free data, new fetch script, honour the
   3-day reporting lag.
6. **B2 (FX leg only)** — carry via the funding differential we already pay.
7. Everything else: park.

## Sources
- Is Trend Still Your Friend? — arXiv:2607.01550
- Buy the Rumor, Sell the News — arXiv:2608.14014
- Fernandez-Perez et al., Hedging Pressure and Returns in Futures: Evidence
  Across Asset Classes (AUT Centre for Financial Research)
- Koijen, Moskowitz, Pedersen, Carry (NBER w19325 / JFE 2018)
- Chicago Fed WP 2025-17, The Decline of the Variance Risk Premium
- Lou, Polk, Skouras, A Tug of War: Overnight Versus Intraday Expected
  Returns (JFE 2019)
- Quantpedia: Term Structure Effect in Commodities
- quantseeker.com: Turn-of-the-Month Strategies: Do They Still Work?
- Macrosynergy: Seasonal effects in commodity futures curves
