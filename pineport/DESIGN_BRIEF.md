# Where the edge actually is — measured, not argued

> ## CORRECTION — §3 of this document was wrong, and its own test killed it
>
> I recommended time-series momentum on a basket as candidate 1, on the strength
> of the gold result in §1 plus the published literature. Then I ran it across
> the ten markets already downloaded. **It fails.**
>
> **Per-market, 3-month horizon, sign-consistent across all three eras:**
>
> | signal | AUD | BCO | DAX | EUR | GBP | SPX | JPY | XAG | **XAU** | XCU | score |
> |---|---|---|---|---|---|---|---|---|---|---|---|
> | close > SMA200 | −1.00 | −1.32 | −0.98 | +0.50 | +0.07 | −0.68 | −0.71 | −0.69 | **+1.01** | −1.89 | **0/9** |
> | Donchian mid200 | −0.86 | −0.56 | −1.41 | +0.37 | +0.18 | −0.85 | −1.45 | +0.65 | **+1.51** | −2.76 | **0/9** |
> | CCI(200) > 0 | −0.99 | −1.01 | −0.95 | +0.45 | +0.08 | −0.66 | −0.62 | −0.18 | **+1.19** | −3.95 | **0/9** |
> | Vortex(140) | −0.27 | −1.22 | −0.42 | +0.33 | −0.05 | −1.01 | −0.72 | −0.68 | **+0.92** | −1.23 | **0/9** |
>
> On seven of ten markets the sign is **negative** — above the 200-day average
> predicts *lower* forward returns. Gold is the outlier. That is the signature of
> a single-market fluke, which is precisely what §1 was.
>
> **Canonical TSMOM** (12-month sign → next month, monthly) does better but not
> enough: positive in all three eras on **3 of 9** non-gold markets (SPX500,
> USDJPY, copper). Full-sample t-stats reach 2.01 on gold, 1.87 on SPX500,
> 1.69 on USDJPY — suggestive, not conclusive.
>
> **The diversified portfolio — the actual published claim — also fails here:**
>
> | portfolio | ann ret | vol | **Sharpe** | max DD |
> |---|---|---|---|---|
> | TSMOM equal weight | 2.41% | 8.9% | **0.27** | −24.8% |
> | TSMOM inverse-vol scaled | 2.33% | 7.1% | **0.33** | −19.9% |
> | buy-and-hold basket | 6.13% | 11.6% | **0.53** | −34.3% |
> | **buy-and-hold GOLD** | **10.33%** | 17.3% | **0.60** | −41.9% |
>
> Diversified trend following returns a third of gold's buy-and-hold at half the
> Sharpe, before costs.
>
> **Caveats that matter, and do not rescue it:** these are spot/CFD prices, not
> futures excess returns, so roll yield and carry are missing — a real difference
> from the published work. Ten markets of which five are USD FX pairs is weak
> diversification against the 58+ futures across four asset classes the
> literature uses. And 2006–2026 was a documented drought for managed futures.
> All true. None of it changes what is tradeable on the data actually in hand.
>
> **Net: §3 below is superseded.** The reasoning in §1 and §2 stands — horizon
> and lookback dominate indicator choice, and that is a real finding. The
> conclusion drawn from it did not survive contact with nine other markets.



Written after re-reading every result in this project against the question
"how do we build something that works outside the training window".

**The short version: the problem was never indicator selection. It was horizon.**

---

## 1. The measurement that reframes everything

Forward-return edge = mean return when a condition is true, minus when false.
A condition worth trading should at minimum keep the same **sign** in every era.

### At the horizons you have been trading (15m–8 days), nothing does

| condition | fires | 2006–12 | 2013–19 | 2020–26 | consistent |
|---|---|---|---|---|---|
| close > SMA(20d) | 55% | −0.08 | +0.07 | −0.05 | no |
| close > SMA(50d) | 56% | −0.77 | +0.15 | +0.34 | no |
| close > SMA(200d) | 66% | −0.11 | −0.01 | +0.06 | no |
| 12m momentum > 0 | 66% | −0.77 | −0.01 | +0.07 | no |
| SMA20d > SMA50d | 56% | −0.68 | +0.40 | +0.45 | no |
| ATR above 50d avg | 41% | −0.33 | +0.03 | +0.46 | no |
| London session | 39% | −0.02 | −0.00 | −0.02 | yes, but ~0 |

**Zero of fourteen price-derived conditions hold their sign at an 8-day horizon.**
The only sign-consistent ones are session dummies worth −0.02%.

This is the same finding as everything else here: the 15m entry signal's forward
return was 0.37% against a 0.33% baseline; multi-market was 0 of 7 three times;
parameter search returned chance. **Gold, at intraday-to-weekly horizons, does
not carry stable directional information in price-derived indicators.** No
combination of them fixes that, because there is nothing to combine.

### At 3–12 month horizons, simple trend works — in every era

| condition | horizon | 2006–12 | 2013–19 | 2020–26 | mean |
|---|---|---|---|---|---|
| **close > SMA200d** | **3 months** | **+0.77** | **+0.78** | **+1.57** | **+1.04** |
| SMA50 > SMA200 | 3 months | +1.05 | +0.45 | +1.53 | +1.01 |
| 6m momentum > 0 | 3 months | +0.27 | +0.89 | +1.20 | +0.79 |
| close > SMA200d | 6 months | +0.61 | +1.64 | +3.14 | +1.80 |
| close > SMA200d | 12 months | +4.81 | +2.17 | +9.91 | +5.63 |
| SMA50 > SMA200 | 12 months | +6.64 | +0.60 | +9.84 | +5.69 |

Same instrument, same data, same indicators. The only thing that changed is the
holding period. This is time-series momentum, and it appears exactly where forty
years of published out-of-sample evidence says it should — monthly to annual,
not intraday.

**Caveats, stated honestly:** effect sizes are regime-dependent even where the
sign is not (2013–19 gives +0.45 where 2020–26 gives +1.53). Overlapping windows
inflate apparent significance. Twenty years at a 12-month horizon is ~20
independent observations — the same small-sample problem in different clothing.
Sign consistency across three eras is three observations, not proof. These are
conditional means, not a tradeable P&L: exposure, costs and drawdown still have
to be paid.

---

## 1b. The indicators this project had never tested

Fair objection: everything above came from one script's vocabulary. So here are
25 conditions from the families we had ignored entirely — MACD, Stochastic, CCI,
Williams %R, Supertrend, Donchian, Ichimoku, Aroon, Vortex, Hull, KAMA, OBV, MFI,
Choppiness — put through the same test (`indicator_scan.py`).

**At their standard settings, 1 of 25 is sign-consistent** — and that one
(MFI < 20) fires on 3% of days with a *negative* edge.

| condition | 2006–12 | 2013–19 | 2020–26 | consistent |
|---|---|---|---|---|
| MACD line > signal | −1.64 | +1.24 | +0.32 | no |
| Stochastic %K > %D | +0.16 | +0.04 | −0.01 | no |
| Supertrend long | −2.24 | +0.08 | +0.29 | no |
| Donchian 20 breakout | −1.94 | +0.33 | −0.14 | no |
| Ichimoku above cloud | −0.22 | −0.81 | +2.10 | no |
| Vortex VI+ > VI− | −1.36 | −0.04 | +0.49 | no |
| CCI(20) > 0 | −1.21 | +0.47 | +0.56 | no |
| close > Hull(20) | −0.86 | +0.58 | +0.71 | no |

### But every one of those is a SHORT-lookback indicator

Re-run the same indicators with their periods multiplied:

| lookback | sign-consistent |
|---|---|
| standard (MACD 12/26, CCI 20, Donchian 20, Vortex 14) | **0 of 6** |
| 4× | 1 of 6 |
| **10×** (CCI 200, Donchian 200, Vortex 140) | **3 of 6, all positive** |

| condition | 2006–12 | 2013–19 | 2020–26 | mean |
|---|---|---|---|---|
| Donchian mid (200) | +1.52 | +0.37 | +2.72 | +1.54 |
| CCI > 0 (200) | +1.28 | +0.80 | +1.56 | +1.22 |
| **Vortex VI+ > VI− (140)** | **+0.86** | **+0.97** | **+0.94** | **+0.92** |

The Vortex at 140 is the most stable thing measured in this entire project:
+0.86 / +0.97 / +0.94 across three eras.

**The indicator family is nearly irrelevant. The lookback is what decides it.**

### And they are all one signal

Daily agreement between the sign-consistent conditions:

| | SMA200 | Donchian200 | CCI200 | Vortex140 |
|---|---|---|---|---|
| close > SMA200 | 100% | **96%** | **96%** | 90% |
| Donchian mid 200 | 96% | 100% | 94% | 88% |
| CCI(200) > 0 | 96% | 94% | 100% | 88% |
| Vortex(140) | 90% | 88% | 88% | 100% |

88–96% agreement. These are not four discoveries; they are **one effect —
long-horizon trend — measured four ways**. Stacking them is confirmation bias,
not diversification, and it is exactly the mistake that produced 57 parameters on
one market. Pick the cheapest one and spend the effort on more markets instead.

---

## 1c. Non-price data: COT positioning — also rejected

CFTC Commitments of Traders, 1,180 weeks per market, joined on `available_from`
so the Friday publication lag cannot leak. Criterion set before looking:
sign-consistent across all three eras in ≥6 of 8 markets.

| signal | 1-month | 3-month |
|---|---|---|
| net spec z > 0 | 2/8 | 1/8 |
| z > +1 (crowded long) | 2/8 | 1/8 |
| **z < −1 (crowded short)** | **3/8** | **3/8** |

**Rejected.** The one direction with any life is crowded *shorts* in metals —
silver returns +5.06 / +2.42 / +0.62 over three months across the three eras,
copper +9.51 / +1.36 / +0.73. Economically sensible (short squeezes in
commodities), consistent in sign, and **decaying hard**: copper's edge falls by
92% from the first era to the last. That is what an effect looks like as it gets
arbitraged away. Not tradeable on this evidence.

---

## 1d. The one thing that has NOT failed: volatility targeting

Not a signal at all — just position sizing by trailing volatility, on plain
buy-and-hold gold. Nothing fitted to returns; sizing uses yesterday's realised
vol, leverage capped at 3×.

| | ann ret | vol | **Sharpe** | max DD |
|---|---|---|---|---|
| buy and hold | 8.53% | 16.5% | **0.52** | −44.8% |
| vol target 10%, 20d | 6.49% | 11.3% | 0.57 | −46.3% |
| **vol target 10%, 60d** | 6.83% | 10.7% | **0.64** | **−38.1%** |
| vol target 15%, 20d | 9.39% | 16.9% | 0.55 | −61.4% |
| **vol target 15%, 60d** | 9.95% | 16.0% | **0.62** | −52.4% |
| vol target 20%, 20d | 12.12% | 22.5% | 0.54 | −71.4% |
| **vol target 20%, 60d** | 12.83% | 21.4% | **0.60** | −64.0% |

**Every one of six settings beats buy-and-hold on Sharpe, and the 60-day window
beats the 20-day at all three target levels.** That is a PLATEAU, not a SPIKE —
the robustness signature that `sweep.py` looks for and that nothing else in this
project has produced. The gain is modest (~0.10 Sharpe) and matches the
published volatility-managed-portfolio literature, which is the point: it is a
known effect reproducing at the expected size, not a discovery.

**The lesson worth extracting:** fourteen attempts to predict *direction* failed.
The one thing that worked was managing *size*. Risk management is where the
robust, repeatable gains have been in this entire project — the stop-loss
plateau (5 of 6 windows), the scale-free sizing fix, and now vol targeting.
Every directional signal has failed out of sample.

---

## 2. Answering your questions directly

### Which indicators are most robust?

Two measurements from this project, and they agree:

**Cross-feed reproducibility** — the same condition on two data vendors:

| condition type | example | agreement |
|---|---|---|
| slow trend state | close > SMA(50) | **99%** |
| volatility regime | ATR > its 50-bar mean | 96% |
| common oscillator | RSI(14) < 35 | 98% |
| rare tail excursion | close crosses BB(2.03σ) | **68%** |

**Era sign-consistency** — the table in §1.

Both point the same way: **slow, common states over long horizons.** The 200-day
moving average is robust in both senses. A 2σ band crossing on a 15m chart fails
both — it is a rare event, and rare events happen where feeds disagree most.

The robust set for gold, measured: `close > SMA200d`, `SMA50 > SMA200`,
`6–12 month momentum`, evaluated at 3–12 month horizons.

### Where do we set profit and loss?

Already measured here, and the answers were counterintuitive:

* **Never cap winners.** Tested four ways — take-profits at 1–10% all lost, the
  ATR ladder lost, the dollar ladder converted large winners into small ones.
  MFE analysis showed the average trade gives back 75% of its peak and capping
  still lost. Returns live in a handful of large trades; a profit target
  systematically removes exactly those.
* **The stop is where the real decision is.** The stop-loss plateau was the one
  credible parameter finding in the whole project — it held in 5 of 6 windows,
  where a 7-parameter search collapsed from 4/6 to 2/6 on re-run.
* **Prefer a plateau to a peak.** `sweep.py` labels each parameter PLATEAU or
  SPIKE. Both sweeps run so far came back SPIKE, which is why they do not hold up.
* For a trend system the exit is not a target at all — it is the trend condition
  turning off. Exit when `close < SMA200d`, not at +N%.

### How do we validate?

The gauntlet is already built and has correctly rejected everything so far:

1. **Era sign-consistency** (new, cheapest) — same sign in every era, or reject
2. **Feed robustness** — ≥80% trade overlap across two vendors (`feed_compare.py`)
3. **Trade count** — ≥30 per test window, and ≥10 per fitted parameter
4. **Random-entry null at matched exposure** (`null_test.py`)
5. **Walk-forward, parameters chosen out-of-sample only** (`retrain_15m.py`)
6. **Multi-market, pre-registered** — ≥6 of 7 unseen instruments
7. **Costs and concentration** — top 10 trades under ~40% of profit

Pre-register the criterion before looking. On this project pre-registration is
what separated the one credible finding from the false positives.

### How do we complement them?

Not by stacking more filters on gold. That is what produced 57 parameters against
166 trades, and every filter added cost trades without adding edge — the FRED
gate cost 45 percentile points out of sample.

**Complement across markets, not across indicators.** A trend rule with a small
edge applied to fifteen weakly-correlated markets is a business; the same rule on
one market is a coin flip with good months. That is why managed-futures funds are
built that way, and it is the real answer to "profitable in most market
situations" — no single strategy is, and a portfolio of weakly-correlated ones
does not need to be.

### How do we use market knowledge others ignore?

This is the best question in your list, and it is where genuine differentiation
lives, because it is the one input that is not price. The candidates for gold,
all slow-moving and therefore matched to the horizon that actually works:

* **Real yields (10y TIPS)** — the economic driver of gold. It failed as a 15m
  entry filter here, but that tested it at the wrong horizon and as a binary gate.
  At 3–12 months, with the level rather than a 26-day crossover, it is the single
  most defensible non-price input.
* **Central bank net purchases** — quarterly, published, and a structural demand
  shift most discretionary traders never look at.
* **ETF flows and COMEX inventory** — positioning and physical tightness.
* **Futures basis / roll yield** — carry, one of the few effects with a published
  out-of-sample record.
* **CFTC Commitment of Traders positioning** — crowding, weekly.

The rule that makes these useful rather than another overfit: **each candidate
needs a stated reason to work that does not reference a backtest**, written down
before testing.

---

## 3. What I would build

**Budget three to five candidates, fixed in advance.** Not fifty.

1. **Time-series momentum on a basket.** `close > SMA200d` (or 12-month
   momentum), long-only or long/short, monthly rebalance, position sized by
   inverse volatility, across the ten markets already downloaded. This is the
   most-replicated effect in systematic trading and it is measurable here today
   with existing data and existing tooling.
2. **The same, with a real-yield overlay for gold specifically** — the one place
   a non-price input has a defensible mechanism.
3. **Carry / roll yield** on the commodity futures, if the data can be sourced.

Expect most to fail. Twelve things were tested in this project and two survived,
both bug fixes. A process that rejects nine of ten is working correctly.

---

## 4. Was the existing work wasted?

No — but its value is the harness, not the strategy. Twenty-six modules that all
self-test, a Pine-exact port verified at 97.8%, a pinned execution model, random
entry nulls, walk-forward with dual nulls, feed comparison, per-parameter sweeps
with plateau detection, and a trade-list verifier. **That is the apparatus for
testing candidate 1 in an afternoon**, and it is the reason the 15m strategy's
failure could be measured cleanly rather than argued about.

The strategy itself, honestly stated: on the held-out window it returns 5.10%
CAGR at Sharpe 0.96 and −11.8% drawdown, against gold's 10.61% buy-and-hold at
roughly −45%. Better risk-adjusted, worse absolute, and it does not meet the
goal as you originally set it. What it does now have is a number you can trust.
