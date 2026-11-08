# The 4-hour strategy — same analysis

> ## CORRECTION AND MAIN FINDING: bar alignment decides the answer
>
> The analysis below used OANDA H1 resampled to 4H on midnight-UTC boundaries.
> Native OANDA H4 aligns to **17:00 New York**, so its bars start at hours
> 1,2,5,6,9,10,13,14,17,18,21,22 (twelve, because the anchor shifts with US
> daylight saving). **Not one timestamp coincides with the resampled bars.**
>
> Re-running on native H4 gave a completely different answer — so I tested every
> alignment. Same H1 data, same code, only the bar boundary moved:
>
> | alignment | trades | Sharpe | Calmar | **out-of-sample percentile** |
> |---|---|---|---|---|
> | UTC +0h *(used below)* | 142 | 0.59 | 0.139 | **48.0** |
> | UTC +1h | 137 | 1.22 | 0.550 | **99.5** |
> | UTC +2h | 131 | 0.77 | 0.266 | 88.6 |
> | UTC +3h | 155 | 0.63 | 0.275 | 58.3 |
> | **native (17:00 NY)** | 127 | **1.17** | **0.622** | **99.7** |
>
> **The out-of-sample verdict swings from "indistinguishable from random" to
> "99.7th percentile" on a one-hour shift of an arbitrary boundary.**
>
> Trade overlap between alignments confirms these are different strategies, not
> noisy versions of one:
>
> | | +0h | +1h | +2h | +3h | native |
> |---|---|---|---|---|---|
> | **+0h** | 100% | 30% | 25% | 33% | 27% |
> | **+1h** | 31% | 100% | 28% | 24% | **70%** |
> | **+2h** | 27% | 29% | 100% | 34% | 50% |
> | **+3h** | 30% | 21% | 29% | 100% | 22% |
> | **native** | 30% | **76%** | 51% | 27% | 100% |
>
> Typically **21–34% overlap**, against the 80% feed-robustness pass mark. Two
> alignments of the same data share fewer trades than two *vendors* did at 1H
> (61%).
>
> ### What this means
>
> **The native-H4 result is not a discovery.** It is one draw from a
> distribution spanning the 48th to the 99.7th percentile, and it happens to be
> a high draw. Reporting 99.7 without the other four would be the single most
> misleading thing in this project.
>
> It is also **not merely a measurement artefact**. The strategy trades on bar
> closes, so a platform that aligns 4H bars differently genuinely trades
> differently. TradingView on OANDA gives the 99.7 version; a broker anchoring
> to UTC midnight gives the 48 version. That is live-execution risk, not just
> backtest ambiguity.
>
> **This is the feed-robustness problem in a new form, and it is specific to
> timeframes above 1H.** Hourly bars have one sensible alignment. Every higher
> timeframe carries an arbitrary anchor choice that the strategy is exposed to.
> The 85.6% feed-reproducibility score below is therefore real but incomplete:
> it held the alignment constant while varying the vendor, and alignment turns
> out to matter more than the vendor did.
>
> **Corrected verdict:** the 4H strategy fails on alignment sensitivity. Its
> apparent out-of-sample edge exists on two of five alignments tested and
> vanishes on the other three.
>
> ---

Run through the full pipeline. **It is the first version to pass the feed
robustness gate, and the first whose out-of-sample entry edge measures as
exactly nothing.** Those two facts are related, and together they are the most
useful result in the project.

Data: OANDA H1 resampled to 4H (native H4 pending — see caveat at the end).

---

## 1. It is not the 1H strategy on a different timeframe

Despite the name, this is different code:

| | 1H version | 4H version |
|---|---|---|
| RSI trigger | RSI(**1**) crossing 29 — degenerate, = "up bar" | RSI(**3**) crossing 49 — a real momentum flip |
| entry band | BB(15, **2.03σ**) | BB(**4**, **0.38σ**) — far tighter |
| Keltner range | `ta.tr` (repaired) | **`high`** — QUIRK 2 is back |
| long stop ratchet | `price_stop_long[1]` (repaired) | **current bar** — QUIRK 5 is back |
| higher-timeframe filter | 4H close vs 4H SMA | **none at all** |
| new filters | — | `close > SMA(40)`, `close > EMA(40)` |
| squeeze lengths | KC 76 / 942 | KC 9 / 64, BB 1513 / 7 |
| stop / limit | 2.7% / 6.7% | 3.03% / 1.52% |

Two dead-code notes: `EMALong = 50` is declared but the EMA filter is written
`ta.ema(price, SMALong)`, so it uses **40** and `EMALong` does nothing. And
`mult = 2.0` is unused again — the bands use `multKC`.

---

## 2. It PASSES the feed robustness gate — the only version that does

Dukascopy vs OANDA, both resampled to 4H, 32,590 shared bars:

| | Dukascopy | OANDA |
|---|---|---|
| trades | 150 | 140 |
| win rate | 46.0% | 45.7% |
| profit factor | 1.72 | 2.08 |
| CAGR | 2.28% | 2.43% |
| Sharpe | 0.56 | 0.69 |
| max drawdown | −13.43% | −12.17% |

**Trade reproducibility 85.6%** (1H version: 61.3%).

**Why**, and it confirms the design rule derived in `NEXT_STEPS.md`: the entry
band is **0.38σ** rather than 2.03σ, so `crossover(close, BBlower)` fires on
**15.7%** of bars instead of 2.8%. A common event is robust to a 0.03% price
difference; a tail event is not.

The metrics are correspondingly stable — Sharpe 0.56 vs 0.69 across vendors,
where the 1H version swung 1.14 vs 0.77.

**This is what a measurable strategy looks like.** Its numbers mean something.

---

## 3. What the measurement says: no out-of-sample edge

Random entry at matched exposure:

| period | trades | exposure | strategy | random | **percentile** |
|---|---|---|---|---|---|
| full 2006–2026 | 142 | 23.4% | +96.0% | +67.0% | 73.8 |
| **out-of-sample 2006–2022** | 117 | 23.4% | +23.9% | **+33.1%** | **47.3** |
| 2023–2026 | 17 | 14.1% | +38.6% | +13.1% | 96.1 |

**Over the 17 years it was not tuned on, the entry rule performed at the 47.3rd
percentile — it was beaten by randomly chosen entry dates at the same
exposure.** All of its apparent skill sits in 2023–2026, where it reaches the
96th.

For comparison the 1H version scored 86.8th out-of-sample. The 4H version is
more *trustworthy* and has *less* edge.

Headline performance: CAGR 2.49%, Sharpe 0.59, max drawdown −17.96%, against
gold's 10.63% buy-and-hold over the same span.

---

## 4. Multi-market: 0 of 7

Same pre-registered protocol, vol-scaled stop, nothing tuned per market:

| market | trades | percentile |
|---|---|---|
| DAX | 71 | 77.3 |
| USDJPY | 99 | 76.0 |
| BRENT | 115 | 64.5 |
| COPPER | 108 | 50.8 |
| GBPUSD | 120 | 31.0 |
| S&P500 | 96 | 30.9 |
| AUDUSD | 101 | 30.2 |
| *GOLD (known)* | 140 | *71.8* |
| *SILVER (known)* | 176 | *44.4* |
| *EURUSD (known)* | 120 | *47.0* |

**0 of 7 clear the 80th percentile.** The 1H version scored 1 of 7 on OANDA and
0 of 7 on Dukascopy. Three versions, three feeds, same answer.

---

## 5. Repairing the bugs does not help here

The Keltner repair was transformative on the 1H version. On 4H it is not:

| | trades | CAGR | Sharpe | max DD | Calmar | PF |
|---|---|---|---|---|---|---|
| as written (`range1 = high`) | 142 | 2.49% | 0.59 | −17.96% | 0.139 | 1.85 |
| repaired (`range1 = ta.tr`) | **30** | 1.35% | 0.49 | **−9.37%** | 0.144 | **2.74** |
| + stop ratchet fix | 30 | 1.04% | 0.44 | −9.30% | 0.112 | 2.30 |

It cuts the trade count from 142 to 30 — below the measurability floor — and
leaves Calmar flat. With `lengthKCS = 64` rather than 942 the channel is a
completely different object, so the fix that mattered at 1H does not transfer.

Drawdown does improve markedly (−17.96% → −9.37%), so the repair is still worth
applying on risk grounds; it simply is not the transformation it was at 1H.

---

## 6. Verdict

| criterion | 1H version | **4H version** |
|---|---|---|
| feed-robust | ❌ 61.3% | ✅ **85.6%** |
| beats random, out-of-sample | ⚠️ 86.8th | ❌ **47.3rd** |
| generalises (multi-market) | ❌ 1 of 7 | ❌ **0 of 7** |
| enough trades | ✅ 142 | ✅ 142 |
| beats buy-and-hold | ❌ 2.5% vs 10.6% | ❌ 2.5% vs 10.6% |

The 4H version trades a real edge for a measurable one. That is not a bad
trade — an honest zero is worth more than an unmeasurable maybe — but the
answer it gives is zero.

**The most useful thing here is the contrast.** Widening the entry band from
2.03σ to 0.38σ took feed reproducibility from 61.3% to 85.6% while the edge
went from 86.8th to 47.3rd percentile out of sample. The 1H version's apparent
advantage was partly the fragility itself: a tail-event trigger produces
extreme, unstable statistics, and extremes look like skill.

---

## Caveat

These runs use OANDA H1 resampled to 4H, not native H4. TradingView's 4H bars
use OANDA's own alignment (daily-aligned at 17:00 New York), so bar boundaries
differ from the midnight-UTC buckets used here. Given that the entry now fires
on 15.7% of bars, alignment should matter far less than it would for a tail
trigger — but the numbers are provisional until:

```bash
python3 fetch_oanda.py --all --granularity H4 --start 2005-01-01
python3 clean_feeds.py --pattern '*_oanda_h4.csv' --apply
```
