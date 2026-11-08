# 4H "repaired and optimised" — validation

**Two questions asked: is it doing what we think, and is it profitable?**

1. **Is it doing what we think?** Yes. The port reproduces **99.6%** of your
   trades. This is the cleanest verification in the project.
2. **Is it profitable?** On 2013–2026, emphatically. On the seven years your
   chart does not cover, it loses money and is beaten by random entry at the
   **0.6th percentile**.

---

## 1. Verification: the port is right

Native OANDA H4, your exact configuration:

| | TradingView | my port |
|---|---|---|
| trades | 266 | 286 |
| long / short | 139 / 127 | 151 / 135 |
| win rate | 55.6% | 53.8% |
| profit factor | 6.91 | 5.59 |

**265 of your 266 trades matched (99.6%).** The 20 extra are mine alone —
my data starts 2012-03, your chart starts 2013-03. Restricted to your window the
figures line up.

This is a materially better match than the 1H version managed (43%), and the
reason matters: this script uses **states** (`LSMAS > LSMAL`) where the earlier
ones used **crossovers**, and its entry band is **0.51σ** rather than 2.03σ.
Both changes move it away from knife-edge triggers — exactly the design rule in
`NEXT_STEPS.md`. **You have independently arrived at the more robust
construction.**

Genuine improvements over the previous versions, all confirmed:

* `range1 = ta.tr(true)` — FIX 1 is in.
* The short leg **works**: 127 shorts against 0–20 previously. RSI(3) crossing
  43 and a 1.17σ band are compatible conditions, where RSI(5) below 20 and a
  1.6σ band were near-contradictory.
* Concentration much improved: top 10 trades are **71.5%** of profit, against
  92–100% in earlier versions.
* Long and short each have their own ADX, tested in opposite directions.

One thing to know about: `lockProfitUp = 10000`. When price crosses
`entry + 470`, the stop is set to `entry + 10000` — far above market. Pine and
this port both fill that at the next bar's open, so **it behaves as a
take-profit at roughly +470**, not as a stop. That is probably what you intend,
but the mechanism is not what the input name suggests.

---

## 2. Profitability: it depends entirely on the period

| period | trades | CAGR | Sharpe | max DD | PF | win% | **vs random** |
|---|---|---|---|---|---|---|---|
| **2006–2013 (unseen)** | 154 | **−0.82%** | **−0.07** | −18.82% | **0.94** | 40.3% | **0.6th** |
| 2013–2026 (your chart) | 266 | **16.50%** | **1.80** | −11.98% | **6.66** | 55.6% | 100.0 |
| — 2013–2019 | 136 | 4.06% | 0.67 | −11.98% | 1.57 | 49.3% | 99.9 |
| — 2020–2026 | 130 | **32.40%** | 2.42 | −11.22% | 9.38 | 62.3% | 100.0 |
| full 2006–2026 | 424 | 10.51% | 1.22 | −25.71% | 4.04 | 50.0% | 99.9 |

Sizing-independent per-trade returns tell the same story:

| era | trades | sum of % returns | mean | win rate |
|---|---|---|---|---|
| 2006–2012 | 150 | **+12.9%** | +0.09% | 40.7% |
| 2013–2026 | 274 | **+254.8%** | +0.93% | 55.1% |

**Seven years of unseen data produce a −0.82% CAGR, a profit factor of 0.94, and
a 0.6th-percentile score against random entry.** The strategy did not merely
fail to work there — it was beaten by picking entry dates at random, at matched
exposure, in 99.4% of draws.

That is the signature of parameters fitted to 2013–2026. The 2020–2026 sub-period
alone carries a 32.4% CAGR and a 9.38 profit factor; nothing sustains those
numbers outside it.

---

## 3. Alignment sensitivity

The previous 4H version swung from the 48th to the 99.7th percentile depending
on where the 4H bar boundary sat. This version is stable — and stable at the
wrong end:

| alignment | trades | CAGR | Sharpe | PF | **2006–2019 percentile** |
|---|---|---|---|---|---|
| UTC +0h | 505 | 5.97% | 0.65 | 1.64 | 7.0 |
| UTC +1h | 429 | 9.89% | 1.12 | 3.58 | 7.4 |
| UTC +2h | 443 | 6.98% | 0.70 | 2.07 | 1.3 |
| UTC +3h | 501 | 4.31% | 0.45 | 1.42 | 9.3 |
| **native (17:00 NY)** | 424 | **10.51%** | **1.22** | **4.04** | **30.4** |

Spread of **1.3 to 30.4**, against the previous version's 48.0 to 99.7. The
state-based triggers have removed the alignment fragility — a real improvement —
but every alignment agrees the pre-2020 performance is below random.

Note also that native alignment gives the best headline numbers of the five
(CAGR 10.51% vs 4.31–9.89%). That is the alignment you trade, so it is not
wrong to use it, but it is the top of the range rather than the middle.

---

## 4. Verdict

| criterion | result |
|---|---|
| port verified | ✅ **99.6% of trades reproduced** |
| feed/alignment robust | ✅ spread 1.3–30.4, far tighter than before |
| shorts functional | ✅ 127 shorts, no longer contradictory |
| concentration | ✅ top 10 = 71.5% (best yet) |
| enough trades | ✅ 424 over 20 years |
| **beats random, unseen data** | ❌ **0.6th percentile, 2006–2013** |
| **profitable on unseen data** | ❌ **−0.82% CAGR, PF 0.94** |

**The engineering is much better and the evidence is worse.** Every structural
criticism from earlier versions has been addressed — states instead of
crossovers, working shorts, spread concentration, a repaired Keltner, alignment
stability. What that bought is a strategy whose failure is now *measured
cleanly* rather than obscured by noise.

The 55.6% win rate and 6.91 profit factor on your chart are real. They are also
what 13 years of parameter fitting produces, and the seven years the fitting
never saw return a profit factor of 0.94.

**What would change my mind:** run it forward on 2026 data as it arrives, with
parameters frozen today. Six months of live-equivalent out-of-sample results at
anything near the backtest would be worth more than any further historical
analysis — and unlike everything else here, it cannot be fitted.

---

## 5. What actually differed in 2006–2013 — and what didn't

**It is the short side, and nothing else.**

| era | trades | long return | **short return** | stopped out | ann vol |
|---|---|---|---|---|---|
| 2006–2013 | 154 | **+53.3%** | **−47.0%** | 30.5% | 21.2% |
| 2013–2019 | 140 | +43.3% | +14.4% | 12.1% | 14.0% |
| 2020–2026 | 130 | +146.5% | +57.1% | 20.8% | 17.8% |

The long book was **profitable in all three eras**. The entire era gap sits in
the shorts, which lost 47% in 2006–2013 and made money in both later periods.

### Three market-behaviour explanations, all tested, all rejected

**1. "Gold trended up, so shorts lost."** No. 2020–2026 had the *same* drift
(+17.3% vs +16.2% annualised) and the shorts made **+57.1%** there.

**2. "Volatility was higher, so the fixed 5.79% stop was too tight."** No.
Vol-scaling the stop to each era made 2006–2013 *worse*:

| era | trade vol | fixed stop → | vol-scaled stop → |
|---|---|---|---|
| 2006–2013 | 0.611% | PF 0.94, CAGR −0.82% | **PF 0.92, CAGR −1.17%** |
| 2013–2019 | 0.456% | PF 1.57, CAGR 4.06% | PF 1.36, CAGR 2.86% |
| 2020–2026 | 0.525% | PF 9.38, CAGR 32.40% | PF 9.38, CAGR 32.39% |

**3. "Pullbacks were shallower, so shorts had no room."** No. The correction
structure of the two up-trending eras is nearly identical:

| era | drift | corrections >5% | >10% | median depth | median duration |
|---|---|---|---|---|---|
| 2006–2013 | +16.2% | 13 in 7y | 3 | 7.7% | 131 bars |
| 2013–2019 | −0.6% | 0* | 0 | — | — |
| 2020–2026 | +17.3% | 10 in 7y | 3 | 7.4% | 142 bars |

\* artefact: 2013–2019 never made a new high, so a running-peak counter cannot
close a correction. That era was one continuous drawdown from the 2011 peak.

### The honest conclusion

**There is no regime difference that survives testing.** Set against the earlier
finding that the entry signal has no forward-return predictive power in *any*
era — mean 30-bar forward return after a signal is 0.37% vs 0.33% baseline
(2006–13), 0.01% vs 0.01% (2013–19), 0.36% vs 0.32% (2020–26) — the short book's
era-to-era swing is **variance, not regime**. A rule with no edge produces −47%
in one seven-year window and +57% in another. That is what no edge looks like
over samples this small.

### The one robust result: dropping shorts removes damage but adds no edge

2006–2013 percentile vs random entry, across all five bar alignments:

| alignment | as written | **long only** |
|---|---|---|
| UTC +0h | **0.0** | 10.9 |
| UTC +1h | **0.0** | 34.9 |
| UTC +2h | **0.5** | 58.2 |
| UTC +3h | **2.1** | 11.0 |
| native 17:00 NY | **0.5** | 77.5 |

The as-written column is the most consistent result in this entire project:
**beaten by random entry at every single alignment, 0.0–2.1st percentile.** The
shorts are reliably harmful, not unluckily harmful.

Long-only scatters 10.9–77.5 — centred near random. It removes the damage
without creating an edge, and costs return: 3.67–6.17% CAGR by alignment,
against gold's **10.61% buy-and-hold**. Since the stated goal is to beat
buy-and-hold, long-only does not reach it either.

**Net:** the 2006–2013 failure is not a regime the strategy can be filtered
around. It is the short book having no edge and a seven-year window in which
that showed up as a loss.
