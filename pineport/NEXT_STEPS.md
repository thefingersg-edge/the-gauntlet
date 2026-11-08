# What a strategy has to satisfy, and how to get one

Written at the end of the RSI Boll Squeeze project. Every criterion below is
here because this strategy failed it, and the measurement that revealed the
failure is named. That is the value of the work: not the strategy, but a list of
tests that reliably say no, and a set of design rules derived from watching one
fail in nine different ways.

---

## 1. The acceptance criteria

Fix these **before** building anything. A criterion agreed after seeing results
is not a criterion.

| # | criterion | test | how this strategy did |
|---|---|---|---|
| 1 | **Feed-robust** — trades reproducible on a second data vendor | run identically on two feeds, compare trade lists | ❌ 43% of longs, ~0% of shorts |
| 2 | **Beats random entry at matched exposure** | `null_test.py` | ✅ gold 99.5th, ❌ 0 of 7 other markets |
| 3 | **Generalises across markets** | `multi_market.py`, unseen instruments | ❌ 0 of 7 |
| 4 | **Not concentrated** | top-10 share of profit | ❌ 92% from 10 trades |
| 5 | **Survives walk-forward** | `optimise.py`, params chosen out-of-sample | ❌ 6/12 folds = chance |
| 6 | **Enough trades to measure** | ≥30 per test window | ❌ 7/year on gold |
| 7 | **Scale-invariant parameters** | re-run at a different price level | ❌ three separate dollar-denominated bugs |
| 8 | **Survives costs** | re-run with realistic spread | ✅ −2.4% at 0.35 points |
| 9 | **Beats buy-and-hold, or has a risk case** | vs the instrument | ⚠️ half the CAGR, quarter the drawdown |

**Nine criteria, six clear failures.** Any one of 1–7 failing is disqualifying.

---

## 2. Design rules, each derived from a measurement

**Avoid triggers that depend on rare tail excursions.** Measured cross-feed
agreement on the same instrument, 1,305 overlapping hours:

| condition type | example | occurrences | agreement |
|---|---|---|---|
| rare tail excursion | close crosses BBlower(2.03σ) | 47 | **68%** |
| rare tail excursion | close below BBlower | 71 | 77% |
| common oscillator state | RSI(14) < 35 | 217 | 98% |
| slow trend state | close > SMA(50) | 530 | **99%** |
| volatility regime | ATR(14) > its 50-bar mean | 532 | 96% |

A 2σ band is *defined* as a rare event, and rare events happen where price moves
fastest — precisely where two feeds disagree most. This is not a data-quality
problem to be fixed with a better vendor; it is a property of the signal.

**Bar alignment is a second robustness axis, for any timeframe above 1H.**
Measured on the 4H strategy: shifting the 4H boundary by one hour moved the
out-of-sample percentile from 48.0 to 99.7, and two alignments of the same data
shared only 21-34% of their trades -- worse than two different vendors at 1H
(61%). Hourly bars have one sensible anchor; every higher timeframe does not.
Test at least four offsets plus the platform native, and treat the spread as the
error bar on every statistic.

**Minimise conjunctions.** Fragility multiplies. Three conditions at 84% average
agreement give 60% joint; at 93% they give 79%. The short leg needed three
simultaneous crossunders and produced **zero** reproducible trades.

**Never cap winners.** Tested four ways — take-profits at 1–10% all lose, the
ATR ladder lost, the dollar ladder converted large winners into small ones, and
MFE analysis showed the average trade gives back 75% of its peak. Returns live
in a handful of large trades.

**Scale-invariant parameters only.** Three separate instances here: `markUp` in
dollars, `longVal` as an absolute linreg magnitude, `rangeL` in dollars. Each
made the strategy silently untestable outside the price level it was tuned at.
Express thresholds in ATR multiples, percentages, or standard deviations.

**Exposure is half the problem.** The gold entry beat random entry 2.2× at
matched exposure and still lost to buy-and-hold, because it was invested 27% of
the time. Edge × exposure is what pays.

---

## 2b. Phase 0 result — the gate now exists, and the strategy is at its boundary

OANDA v20 data pulled for all ten markets (`fetch_oanda.py`), cleaned
(`clean_feeds.py`), and run through the gate (`feed_compare.py`).

**Gold, identical strategy, two feeds, 122,303 shared hours:**

| | Dukascopy | OANDA |
|---|---|---|
| trades | 132 | 123 |
| win rate | 47.7% | 45.5% |
| **profit factor** | **4.49** | **2.83** |
| **CAGR** | **4.86%** | **2.92%** |
| **Sharpe** | **1.14** | **0.77** |
| max drawdown | −10.40% | −10.00% |

**Trade reproducibility: 61.3%** — marginal, barely above the 60% fail line.

The prices agree to 0.03% and returns correlate at 0.989. Yet the same code, on
the same instrument, over the same twenty years, gives Sharpe 1.14 on one
vendor and 0.77 on the other. **That is the difference between "promising" and
"mediocre", produced by nothing but a data-vendor choice.**

Two consequences worth stating plainly:

1. **Every comparison made in this project between strategy variants was at a
   precision finer than the feed noise.** v1 vs v3 differed by less than
   Dukascopy vs OANDA differs from itself. Those rankings should be treated as
   undetermined, not as findings.
2. **OANDA should now be the primary feed** — it is the feed the TradingView
   charts use, the feed execution would happen on, and it has *deeper* history
   than Dukascopy for the CFDs (indices and commodities from 2005 rather than
   2012, taking the S&P 500 from 14.5 to 21.6 years).

Keep Dukascopy as the second feed. The point is not that one is right; it is
that a strategy worth trading must survive both.

---

## 3. The programme

### Phase 0 — instrument the harness for feed robustness (1 session)

Make dual-feed testing the default, not an afterthought. Every candidate runs on
two vendors from the first backtest, and any strategy reproducing under ~80% of
its trades is rejected before anything else is measured.

This is the single highest-value change. It was discovered last on this project
and would have killed the strategy in an afternoon.

Data already held: Dukascopy for ten markets, plus TradingView exports. A second
free vendor for cross-checking is the only gap.

### Phase 1 — candidate generation from structural hypotheses (ongoing)

Not from screening published scripts. Those are selected *because* they
backtested well on someone's data, which is survivorship bias at the source, and
this project is one long demonstration of what that produces.

Each candidate needs a stated reason to work that does not reference a backtest.
Examples with published out-of-sample records: time-series momentum, carry,
volatility risk premium, post-earnings drift. The test is then whether the
effect survived *after* it was written down.

Budget: **three to five candidates**, fixed in advance. Not fifty.

### Phase 2 — the gauntlet, in cost order (cheap rejections first)

1. **Feed robustness** — two vendors, ≥80% trade overlap
2. **Trade count** — ≥30 per test window, or it is unmeasurable
3. **Random-entry null** at matched exposure, on the development market
4. **Walk-forward** — parameters chosen out-of-sample only
5. **Multi-market** — ≥6 of 7 unseen instruments, pre-registered
6. **Costs** — realistic spread and slippage
7. **Concentration** — no more than ~40% of profit from the top 10 trades

Pre-register every criterion. On this project, pre-registration is what
distinguished the one credible finding (the stop-loss plateau, 5/6 windows) from
the false positives (the 7-parameter search at 4/6, which collapsed to 2/6 when
re-run).

### Phase 3 — only then, portfolio construction

Multiple uncorrelated markets rather than more cleverness on one. That is the
real answer to the exposure constraint, and it is why managed-futures funds are
built that way.

---

## 4. Realistic expectations

Twelve things were tested here. Two survived, and **both were bug fixes rather
than discoveries** — repairing the Keltner range and the stop ratchet. Every
attempt to find an edge by searching returned chance.

That is not pessimism, it is the base rate. A process that rejects nine ideas
out of ten is working correctly. The cost of the tenth being real is that you
have to run the other nine through the same gauntlet without flinching when one
of them looks good in-sample.

The most transferable lesson from the whole project: **the largest single gain
came from reading the code closely enough to notice that a Keltner channel was
built from price levels instead of ranges.** No optimiser finds that, because no
optimiser asks whether an indicator computes what its name says.
