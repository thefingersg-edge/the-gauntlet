# RSI Boll Squeeze — 20-year analysis

Run on 124,450 hourly XAUUSD bars from Dukascopy, 2006-01 → 2026-07 (20.6
years), with the port verified bar-for-bar against TradingView beforehand.

Reproduce everything here:

```bash
python run.py diagnose  --csv xauusd_1h.csv
python run.py backtest  --csv xauusd_1h.csv --point-value 1 --capital 4000
python variants.py      --csv xauusd_1h.csv --point-value 1 --capital 4000
```

---

## 1. The port reproduces on a second, independent venue

Your TradingView record is OANDA. This run is Dukascopy — a different venue with
different bars. The trade lists differ in count, as they must, but every
behavioural ratio lands in the same place:

| | TradingView (OANDA), 231 trades | Port (Dukascopy), 281 trades |
|---|---|---|
| total return | +181.1% | +174.2% |
| CAGR | 5.35% | 5.02% |
| win rate | 44.2% | 44.5% |
| profit factor | 2.39 | 2.19 |
| avg bars held | 220.5 | 226.5 |
| long / short | 211 / 20 | 263 / 18 |

Two independent feeds agreeing this closely means the port is measuring the
strategy, not an artefact of one data source.

**A number that changed.** The trade-list drawdown of −8.52% was measured at
trade closes only. With bar data the real figure is **−12.35%**. As expected,
worse — but not alarmingly so.

---

## 2. The edge does not survive out of sample

The ladder inputs (`markUp` 190, `rangeL` 750, `lockProfitUp` 170) are absolute
dollar amounts, so they can only have been chosen at recent price levels. That
makes 2006–2022 an out-of-sample test.

| period | years | trades | strategy CAGR | gold CAGR | profit factor |
|---|---|---|---|---|---|
| **2006–2022** (out-of-sample) | 17.0 | 233 | **1.38%** | 7.71% | **1.32** |
| **2023–2026** (tuned regime) | 3.6 | 48 | **24.17%** | 24.85% | **3.24** |
| full | 20.6 | 281 | 5.03% | 10.52% | 2.19 |

Seventeen years at 1.38% CAGR. The profit factor more than halves outside the
window the parameters were set in.

Rolling three-year windows tell the same story — the strategy trailed gold in
five of seven, and never beat it by a meaningful margin:

| window | strategy | gold | difference |
|---|---|---|---|
| 2006–2008 | 1.12% | 19.49% | −18.37% |
| 2009–2011 | 4.27% | 21.23% | −16.96% |
| 2012–2014 | −0.55% | −8.90% | **+8.35%** |
| 2015–2017 | 0.96% | 3.17% | −2.21% |
| 2018–2020 | 2.83% | 13.27% | −10.43% |
| 2021–2023 | 3.17% | 2.56% | +0.61% |
| 2024–2026 | 28.91% | 29.83% | −0.92% |

The one clear win is 2012–2014, when gold fell 8.9% and the strategy lost 0.55%.
That is the actual character of this system: **it protects capital in gold bear
markets and lags in bull markets.**

---

## 3. Profit concentration is extreme

| | share of net profit |
|---|---|
| top 1 trade | 29.2% |
| top 3 | 52.4% |
| top 5 | 66.4% |
| **top 10** | **92.5%** |

The remaining **271 trades net $525 combined** — about 7% of the result across
twenty years. All ten of the top trades are long and all ten are from 2024
onward.

This is the number that governs the ML plan. The effective sample is ten
observations, not 281.

---

## 4. Risk-adjusted, it does beat buy-and-hold

The return comparison is unflattering, but it is not the whole picture:

| | strategy | gold buy & hold |
|---|---|---|
| CAGR | 5.02% | 10.52% |
| **Sharpe** | **0.93** | 0.64 |
| Sortino | 0.80 | 0.79 |
| **max drawdown** | **−12.35%** | −45.25% |
| **Calmar** | **0.41** | 0.23 |
| time in market | 51% | 100% |

Half the return, but a quarter of the drawdown and half the exposure. On both
Sharpe and Calmar the strategy wins.

Whether that converts into more money depends on leverage. Matching gold's
drawdown would need roughly 3.7× leverage, which arithmetically implies ~18%
CAGR against gold's 10.5%. Treat that as indicative only — leverage is not free,
drawdown does not scale linearly, and a 45% drawdown on 3.7× leverage means a
margin call long before recovery.

The honest framing: **this is a drawdown-reduction overlay, not an alpha
generator.**

---

## 5. Which repairs survive out of sample

This is where the ablation study earns its keep. Two changes looked like clear
improvements on the full sample. Only one of them is real.

**On the full 20.6 years:**

| variant | trades | return | Sharpe | max DD | PF | exposure |
|---|---|---|---|---|---|---|
| faithful | 281 | 174.2% | 0.93 | −12.35% | 2.19 | 51% |
| **fix Keltner range** | 138 | 158.1% | **1.13** | **−10.33%** | **4.18** | **28%** |
| no macro (4H) filter | 345 | **252.1%** | 1.07 | −10.21% | 2.34 | 60% |

**Split by period:**

| variant | OOS CAGR | OOS Sharpe | OOS maxDD | OOS PF | in-sample CAGR |
|---|---|---|---|---|---|
| faithful | 1.38% | 0.40 | −8.67% | 1.32 | 24.78% |
| **fix Keltner range** | 1.19% | **0.54** | **−5.58%** | **1.68** | 24.32% |
| no macro (4H) filter | 1.25% | **0.35** | **−10.21%** | **1.23** | 32.14% |
| Keltner + no macro | **1.60%** | 0.58 | −6.03% | 1.60 | 27.81% |

**"Remove the macro filter" is an in-sample illusion.** It produced the biggest
headline number on the full sample (+252% vs +174%), and out of sample it is
*worse than the baseline on every risk measure* — Sharpe 0.35 vs 0.40, drawdown
−10.21% vs −8.67%, profit factor 1.23 vs 1.32. Its entire advantage came from
the 2023–26 window. This is precisely the failure mode that makes optimising on
this strategy dangerous, and it is worth keeping as a worked example.

**"Fix the Keltner range" is genuine.** It improves both halves:

- out of sample: Sharpe 0.40 → 0.54, drawdown −8.67% → −5.58%, PF 1.32 → 1.68
- in sample: Sharpe 2.23 → 2.64, drawdown −11.13% → −6.54%, PF 3.13 → 10.86
- exposure halves, 51% → 28%, for nearly the same return

Repairing `range1 = useTrueRange ? high : (high - low)` to use `ta.tr()` turns
the dead squeeze filter into the single most valuable component in the strategy.
The bug was not costing a little — it was disabling the best filter in the
system.

**Other ablations:**

- **ADX filter: literally zero effect.** Identical numbers to four decimal
  places. It passes 98.5% of bars.
- **Duplicate RSI trigger: zero effect.** Confirms `crossover(rsi(close,1), 29)`
  is a strict subset of `crossover(sma(close,1), sma(close,2))` — 32,555 of
  32,641, the difference being unchanged-close bars where RSI(1) is undefined.
- **Shorts on Dukascopy lose money**: 18 trades, −0.59% return, PF 0.94, Sharpe
  −0.02. On OANDA they made +$163. Both are noise around zero.
- **All filters off**: 566 trades, drawdown doubles to −25.9%, PF collapses to
  1.50. The filters do something; they are just the wrong ones.

---

## 6. The ATR ladder does not help — and the reason matters

Hypothesis going in: the dollar-denominated ladder was the reason for the
out-of-sample weakness, because those rungs were unreachable at 2006 prices.
The measurement backs the premise — `+190` was **22× ATR** at 2024–26 levels but
**63× ATR in 2006–10**:

| period | median price | median ATR(14) | +190 in ATR units |
|---|---|---|---|
| 2006–2010 | 876 | 3.02 | **62.9** |
| 2011–2015 | 1,365 | 3.45 | 55.1 |
| 2016–2020 | 1,299 | 2.72 | 69.8 |
| 2021–2023 | 1,835 | 4.27 | 44.4 |
| 2024–2026 | 3,216 | 8.59 | **22.1** |

So the ladder really was a different trade in each era. But normalising it makes
results **worse**, on both halves of the sample:

| variant | OOS CAGR | OOS Sharpe | OOS PF | in-sample CAGR | in-sample Sharpe |
|---|---|---|---|---|---|
| Keltner fix only | **1.19%** | **0.54** | **1.68** | **16.26%** | 2.16 |
| + ATR ladder | 1.01% | 0.46 | 1.53 | 12.74% | 1.82 |
| + ATR stop | 0.73% | 0.32 | 1.39 | 15.30% | 1.99 |
| + ATR ladder & stop | 0.81% | 0.36 | 1.42 | 9.81% | 1.35 |
| + percent ladder | 1.17% | 0.53 | 1.64 | 16.57% | **2.22** |

**Why.** The ladder only ever fires on trades that get roughly 6% into profit —
about 30 of 138 — which are precisely the big winners. Normalising it made those
rungs *reachable more often*, so it tightened stops on exactly the trades that
carry the strategy. Mean return of trades reaching the first rung fell from
**7.50% to 6.72%**.

This is the same lesson as the take-profit test in `QUIRKS.md`, arrived at from a
different direction: **every mechanism that caps or locks in profit hurts this
strategy.** Its returns come from a handful of very large trades, and it cannot
afford to cut them short. The one change that helps — the Keltner repair —
filters *entries* rather than capping *exits*.

The percent ladder is a wash (marginally better in-sample, marginally worse out).
If you want scale-invariance for its own sake, use it; expect no performance
gain.

---

## 7. There IS an entry edge — the constraint is exposure, not timing

Comparing to buy-and-hold conflates two things: whether the entry rule works,
and how much time it spends in the market. A long-only rule in a rising market
makes money either way.

`null_test.py` separates them. It generates random entries with the **same trade
count, same holding-period distribution, and same exposure**, then asks where the
real strategy falls in that distribution. Only entry timing is randomised.

| period | exposure | strategy | random-entry mean | percentile |
|---|---|---|---|---|
| full 2006–2026 | 27.8% | **332.0%** | 85.8% | **99.5th** |
| out-of-sample 2006–2022 | 25.8% | **93.6%** | 42.8% | **86.7th** |
| tuned regime 2023–2026 | 33.6% | 126.1% | 34.7% | 99.8th |

(Keltner-repaired variant; exposure matched to within 0.5 points, verified in
the output.)

**Out of sample the entry rule more than doubles the random-entry return at
identical exposure.** At the 86.7th percentile that is suggestive rather than
established — with 113 trades it does not clear a 5% significance bar — but it
is a long way from nothing, and it holds in a period the parameters were not
chosen for.

The repair improves this measure too, which is now three independent statistics
pointing the same way:

| | OOS percentile vs random | OOS Sharpe | OOS PF |
|---|---|---|---|
| faithful | 78.0th | 0.40 | 1.32 |
| Keltner-repaired | **86.7th** | **0.54** | **1.68** |

**This reframes the buy-and-hold comparison.** The strategy loses to gold not
because its timing is bad but because it is only invested a quarter of the time.
Per unit of exposure, the timing adds real value. The lever worth pulling is
therefore *more exposure* — more trades, or position sizing — not better
filtering of the few trades it already takes.

---

## 8. Walk-forward optimisation: a small real gain, not a transformation

Run with `optimise.py`: 7 parameters chosen by measured impact, 60 random-search
trials per fold, 6 rolling folds (6y train / 2.5y test), Calmar objective with a
trade-count floor. Parameters are selected on the training window only and scored
on the *next*, unseen window.

**Headline (out-of-sample only):**

| | mean Calmar | median | folds won |
|---|---|---|---|
| optimised | **1.320** | **0.935** | **4/6** vs baseline |
| baseline (no tuning) | 0.980 | 0.397 | |
| random parameters (no search) | 0.400 | 0.365 | optimised wins 5/6 |

So the search beats both nulls more often than not. That is a genuine result and
better than I expected going in.

**Three reasons to hold it loosely.**

*The in-sample/out-of-sample gap came out negative* (−0.771): test windows scored
*higher* than training windows. That is not evidence of superb generalisation —
it means the later windows sit in gold's bull market and were simply easier. The
usual overfitting diagnostic is uninformative here, so the baseline and
random-parameter columns are doing all the work.

*Five of seven parameters do not converge.* Chosen values across folds, as a
fraction of their search range:

| parameter | spread | sensitivity rank |
|---|---|---|
| bb_stdev_long | 46% | **1st (0.556)** |
| sl_percent_long | 56% | **2nd (0.375)** |
| bb_period_long | 68% | 4th |
| adx_threshold | 63% | 7th |
| vol_long | 83% | 6th |
| bullish_sma | 96% | 3rd |
| atr_long | 100% | 8th |

The only two that converge at all are the two highest-impact ones. On the other
five the optimiser is picking noise — `atr_long` spans its entire range across
folds. Fewer axes would mean less room to overfit and the same result.

*Six folds of ~15 trades each is a small sample of folds.* 4/6 is p ≈ 0.34 on a
binomial test. Directionally positive, not statistically established.

**Distilling it to one stable parameter set.** Taking only the two converged
parameters at their median chosen values (`bb_stdev_long` 2.1 → 1.60,
`sl_percent_long` 2.7 → 2.21) and leaving everything else at defaults:

| | trades | CAGR | Sharpe | max DD | Calmar |
|---|---|---|---|---|---|
| **2006–2022 (out-of-sample)** | | | | | |
| baseline | 113 | 1.19% | 0.54 | −5.58% | 0.214 |
| + 2 converged params | **160** | **1.58%** | **0.60** | **−5.17%** | **0.305** |
| **2023–2026** | | | | | |
| baseline | 33 | **16.26%** | **2.16** | −6.54% | **2.487** |
| + 2 converged params | 51 | 11.12% | 1.49 | −6.74% | 1.650 |
| **full 2006–2026** | | | | | |
| baseline | 138 | 4.72% | **1.13** | −10.33% | 0.456 |
| + 2 converged params | 199 | 3.99% | 0.92 | **−8.60%** | 0.464 |

Out of sample it is a clear improvement — Calmar +43%, more trades, lower
drawdown. In the recent window it is worse. Over the full sample it is a wash on
Calmar (0.456 → 0.464), better on drawdown, worse on Sharpe.

Note the *direction* of the change: the optimiser wants a lower Bollinger
deviation, which takes **more trades** (138 → 199) and more exposure. That is the
same conclusion §7 reached from a completely different angle, which is mild
evidence it is real.

### The confirming test: narrowing the search made it worse

Five of the seven parameters were fitting noise, so the obvious next step was to
drop them and search only the two that converged. Fewer dimensions, same 60-trial
budget, same folds — that should *reduce* overfitting and improve out-of-sample
results.

It did the opposite.

| search space | OOS mean | OOS median | beats baseline | beats random |
|---|---|---|---|---|
| wide7 (7 params) | 1.320 | 0.935 | **4/6** | **5/6** |
| narrow2 (2 params) | 1.107 | 1.108 | **2/6** | **2/6** |
| baseline (no tuning) | 0.980 | 0.397 | — | — |

Per fold, the two runs disagree wildly on the same data:

| fold | test window | baseline | wide7 | narrow2 |
|---|---|---|---|---|
| 1 | 2012-01..2014-07 | −0.007 | 0.081 | *rejected: 6 trades* |
| 2 | 2014-06..2016-12 | −0.125 | **1.533** | **−0.244** |
| 3 | 2016-11..2019-05 | 0.465 | 0.378 | −0.141 |
| 4 | 2019-04..2021-10 | 0.329 | 0.389 | **1.108** |
| 5 | 2021-09..2024-03 | 0.805 | 1.482 | **2.595** |
| 6 | 2024-02..2026-07 | **4.414** | 4.060 | 2.214 |

Fold 2: one search finds +1.533, the other −0.244. Fold 4: 0.389 versus 1.108.
Same instrument, same window, same objective, same budget — the only difference
is which parameters were searched, and the results are unrelated.

**Combined, the two runs beat the untuned baseline in 6 of 12 folds. That is
exactly chance.** The wide7 result that looked promising was itself noise; a
genuine effect would have survived — indeed strengthened — under dimensionality
reduction. It did not.

(Note also that the trade-count floor did its job: narrow2's fold 1 picked
parameters taking only 6 trades in the test window and was rejected rather than
being allowed to post a flattering ratio on six lucky trades.)

### The verdict

**Parameter optimisation does not improve this strategy.** That is now
demonstrated twice, with walk-forward selection, two nulls, a trade-count floor
and a dimensionality check — none of which a conventional single-pass Optuna run
would have applied. Such a run would have reported the best in-sample Calmar of
1.15 as a result.

For contrast: fixing one bug — the Keltner range — moved Calmar from 0.32 to 0.46,
halved exposure, and improved both halves of the sample on three independent
statistics. **On this strategy, code repair has been worth more than every hour
of parameter tuning combined.**

---

## 9. Tuning Dave's edited script (ladder off, stop widened to 6%)

The edit made three changes at once: `markUp`/`lockProfitUp`/`rangeL` raised to
10000 (ladder disabled), `SL_percent_basedL` 2.7 → 6, `L_percent_basedL`
6.7 → 6. Isolating each from the repaired baseline, on the full sample:

| change | trades | CAGR | Sharpe | max DD | Calmar | exposure |
|---|---|---|---|---|---|---|
| repaired baseline | 138 | 4.83% | **1.13** | −10.33% | 0.467 | 27.8% |
| only ladder off | 138 | 4.81% | 1.10 | −10.52% | 0.457 | 28.1% |
| only SL 2.7 → 6.0 | 69 | **5.63%** | 1.06 | −11.10% | **0.507** | 54.0% |
| only limit 6.7 → 6.0 | 138 | 4.61% | 1.13 | −10.28% | 0.448 | 27.8% |
| **all three together** | 67 | 4.51% | **0.79** | **−13.16%** | **0.343** | 54.9% |

**Each change alone is neutral or positive. Together they are the worst
configuration tested.** That is an interaction, not an accumulation.

The mechanism: a 6% stop holds positions roughly four times longer (1,019 bars
vs 251), which is what gives the ladder rungs time to be reached. Widen the stop
*and* remove the ladder and nothing constrains the exit but a very loose trail.
Keep either one and the strategy is fine; remove both and it is not.

### The stop-loss sweep

Across all six walk-forward test windows, both with and without the ladder:

| SL % | ladder ON, mean Calmar | ladder OFF, mean Calmar | avg trades/window | mean DD |
|---|---|---|---|---|
| 1.5 | — | 0.266 | 18.3 | −3.24% |
| **2.0** | **0.931** | **1.018** | 15.7 | −3.14% |
| 2.5 | 0.738 | 0.814 | 14.5 | −3.82% |
| 3.0 | 0.906 | 0.868 | 13.2 | −4.39% |
| 4.0 | 0.603 | 0.537 | 10.2 | −5.61% |
| 6.0 | 0.824 | 0.507 | 6.5 | −7.35% |

Two things make this more credible than the parameter searches in §8:

* It is a **plateau, not a spike** — 2–3% is a broad good region, degrading both
  above 4% and below 1.5%. A single lucky value would not behave that way.
* It was a **pre-specified sweep, not a search**, so there is no
  multiple-comparison problem. As a fixed hypothesis, SL 2.0% beat the 6%
  setting in **5 of 6** walk-forward windows.

Note also the trade-count column. At 6% the strategy takes 6.5 trades per test
window — below the floor where any ratio is meaningful. Part of what tightening
the stop buys is simply *a measurable strategy*.

**Your original 2.7% was already inside the good region.** Widening to 6% moved
out of it.

### Recommendation

Pick one of these; do not mix:

| goal | configuration | full-sample result |
|---|---|---|
| best Sharpe | repaired baseline, ladder ON, SL 2.7% | Sharpe 1.13, Calmar 0.467 |
| best CAGR | ladder ON, SL 6.0% | CAGR 5.63%, Calmar 0.507 |
| lowest drawdown | ladder OFF, SL 2.0% | DD −7.47%, Calmar 0.422 |
| **what to avoid** | **ladder OFF + SL 6%** | **Sharpe 0.79, DD −13.16%** |

If you want to keep the ladder off for simplicity, put the stop back to
2.0–2.5%. If you want the wide 6% stop, keep the ladder.

---

## 10. What the entry logic actually reduces to

The long entry looks like seven conditions. Decomposing it — each component
alone, then leave-one-out — shows it is really one.

**Each condition alone** (same exits, everything else removed), full sample:

| entry condition | trades | CAGR | Sharpe | max DD | Calmar |
|---|---|---|---|---|---|
| all conditions | 138 | 4.83% | **1.13** | **−10.33%** | **0.467** |
| close crosses BB lower | 614 | 4.94% | 0.63 | −30.71% | 0.161 |
| sma(1) crosses sma(2) | 704 | 4.74% | 0.54 | −32.75% | 0.145 |
| squeeze up | 354 | 3.24% | 0.55 | −18.75% | 0.173 |
| macro bullish (4H) | 498 | 3.59% | 0.49 | −29.02% | 0.124 |
| volatility gate | 693 | 4.97% | 0.55 | −25.56% | 0.194 |
| ADX > 23 | 692 | 5.29% | 0.59 | −25.18% | 0.210 |

No single condition carries the edge — each alone produces a similar CAGR with
*triple* the drawdown. The value is in the conjunction being selective.

**Leave-one-out** (change in Calmar when each is removed):

| removed | full sample | out-of-sample | verdict |
|---|---|---|---|
| BB lower crossover | **−0.190** | **−0.159** | **the entry. Everything else is trim** |
| squeeze (sqzUp) | −0.039 | −0.015 | small but real; live only since FIX 1 |
| volatility gate | −0.003 | −0.074 | helps out of sample, wash overall |
| macro 4H filter | **+0.048** | **+0.051** | removing it *helps* — but see below |
| sma(1) × sma(2) | **0.000** | **0.000** | **exactly zero — identical trade list** |
| ADX > 23 | **0.000** | **0.000** | **exactly zero** |
| RSI(1) crossover 29 | **0.000** | **0.000** | **exactly zero** |

Three of the seven components are *exactly* redundant — not approximately,
identically. Removing the SMA crossover, the ADX filter and the RSI trigger
together leaves the trade list unchanged to the last trade. The lower-band
crossover already implies the other two triggers.

**On the macro filter**, the walk-forward check tempers it: removing it wins in
4 of 6 windows with a better median (0.709 vs 0.397) but a worse mean (0.934 vs
0.989, because the full logic wins the large 2024–26 window). By the standard
applied in §8, 4/6 is not evidence. Call it a wash rather than an improvement.

### So the strategy is

> **Buy when price crosses up through a 15-period VWMA Bollinger lower band,
> while a Keltner squeeze is on and price momentum is positive. Exit on a
> ratcheting percentage trailing stop.**

A mean-reversion entry with a trend-following exit. That is coherent, and the
profit concentration (top 10 trades = 92% of profit, §3) says the *exit* is
where the money is made — the entry gets you in, the trail decides whether it
matters.

Everything else in the script — the RSI, the SMA pair, the ADX block, arguably
the 4H macro filter — is decoration. Deleting it changes nothing measurable and
makes what remains legible.

---

## 11. Cross-market test: gold in EUR does not help (rejected)

The one macro idea tested properly, pre-registered in `PREREGISTRATION.md`
before the data was fetched. Rationale: XAUUSD is a ratio, so half of every move
is the dollar. Gold priced in EUR isolates the numerator, distinguishing gold
demand from dollar weakness — two things with different persistence.

Same filter shape as the existing macro filter (4H close > 4H SMA20), changing
only the series it is computed on. Nothing re-tuned.

| hypothesis | mean Calmar | median | avg trades | beats H0 |
|---|---|---|---|---|
| H0 control (XAUUSD macro) | **0.989** | **0.397** | 13.8 | — |
| H1 swap (XAUEUR macro) | 0.805 | 0.258 | 14.5 | **2/6** |
| H2 both (USD and EUR) | 0.920 | 0.264 | 12.5 | **2/6** |

**Both rejected** against the pre-registered bar (≥5/6 real, 4/6 not evidence,
≤3/6 reject). Trade counts held at 12.5–14.5 per window, so this is a genuine
negative, not the thin-sample failure mode that was anticipated.

**Why.** Hourly XAUUSD and XAUEUR log returns correlate at **0.870**, and the
two macro filters agree on **81.8%** of bars. The EUR filter is a noisier copy
of the USD one. And §10 had already measured the XAUUSD macro filter as roughly
a wash — so this swapped one near-inert filter for another.

The value of pre-registering shows here. Fold 4 (2019-04..2021-10) has H1 at
0.709 against H0's 0.329 — more than double. Cherry-picked, that is a compelling
result. Against the fixed criterion it is one window out of six, and the
hypothesis is rejected.

---

## 12. Real-yield regime filter: the first macro idea that survives

Pre-registered before the FRED data was fetched, same fixed criterion as §11.
Gold pays no yield, so its opportunity cost is the real rate; the gold-bullish
state is a *falling* real yield — the inverse of the price filter's "above its
moving average". Series: DFII10 (10-year TIPS), daily, one business day
publication lag.

| hypothesis | mean | median | avg trades | beats H0 |
|---|---|---|---|---|
| H0 control (4H price macro) | **0.989** | 0.397 | 13.8 | — |
| **H1 swap (real yield)** | 0.973 | **0.691** | 12.8 | **5/6** |
| H2 both | 0.869 | 0.293 | 10.0 | 2/6 |

**H1 clears the pre-registered bar. H2 is rejected** — requiring both filters is
over-restrictive, dropping to 10 trades per window, right at the floor. Which
also tells you the two are substitutes, not complements.

**Why this succeeded where XAUEUR failed.** The two filters agree on only
**55.8%** of bars, against 81.8% for XAUEUR. The TIPS yield is a different
instrument in a different market, so it carries information the gold chart does
not already contain. XAUEUR was a rearrangement of the same series.

**Robustness** — checks, not a search; 20d was kept regardless of outcome:

| MA length | 5d | 10d | **20d** | 30d | 50d | 100d |
|---|---|---|---|---|---|---|
| beats H0 | 3/6 | 4/6 | **5/6** | 5/6 | 4/6 | 1/6 |

| publication lag | 0d | **1d** | 2d | 3d | 5d |
|---|---|---|---|---|---|
| beats H0 | 4/6 | **5/6** | 4/6 | 5/6 | 5/6 |

A plateau across 10–50 days, and *complete insensitivity to the publication
lag*. The second matters most: any result exploiting publication timing would
collapse as the lag grew. It doesn't, which rules out the most plausible
lookahead artefact. These are the stability checks the §8 search results failed.

**What it does not show.** On the full sample it is a **tie**:

| | trades | CAGR | Sharpe | max DD | Calmar |
|---|---|---|---|---|---|
| H0, full 2006–2026 | 138 | 4.83% | **1.13** | −10.33% | 0.467 |
| H1, full 2006–2026 | 135 | 4.31% | 1.01 | **−9.21%** | 0.468 |
| H0, out-of-sample 2006–2022 | 113 | 1.19% | 0.54 | −5.58% | 0.214 |
| **H1, out-of-sample 2006–2022** | 114 | **1.29%** | 0.54 | **−4.69%** | **0.274** |
| H0, 2023–2026 | 33 | **16.42%** | **2.19** | **−6.54%** | **2.513** |
| H1, 2023–2026 | 26 | 13.43% | 1.83 | −7.64% | 1.757 |

Better out-of-sample, **worse** in 2023–26, tied overall. The win is on
*consistency*: H1 beat H0 in five windows including both of H0's negative ones,
and lost only the single largest one. That is what a risk-reducing regime filter
should look like — it improves the bad periods and gives up some of the best.

5/6 is p ≈ 0.11 one-sided. It clears the bar set in advance and survives the
robustness checks, but it is a modest effect, not a transformation.

---

## 13. What to do

1. **Apply `fix_keltner_range=True`.** The only change that improves both halves
   of the sample, on three independent measures: Sharpe, profit factor, and
   percentile against random entry. Halves exposure and drawdown for the same
   return.
2. **Delete the short side.** 18–20 trades in 20 years, indistinguishable from
   zero on two venues, carrying eleven inputs through every optimisation.
3. **Delete `sqzOn`, the ADX filter, and the duplicate RSI trigger.** Measured at
   zero effect. `sqzOn` alone costs a 942-bar warm-up.
4. **Do not add a take-profit, and do not normalise the ladder for performance.**
   Both cap winners; both lose. Sections 6 and `QUIRKS.md` §6.
5. **Pursue exposure, not selectivity.** Section 7 is the actionable finding: the
   entry rule beats random entry at matched exposure, but only invests a quarter
   of the time. More trades or larger positions is the lever; tighter filtering
   is not.
6. **Stop optimising parameters.** Section 8 settles it: two walk-forward runs
   with proper controls beat the untuned baseline in 6 of 12 folds combined —
   exactly chance. The budget is better spent on the code and on exposure.

### On the ML plan

The picture is better than it looked before the null test, but the shape of the
work has changed.

- **Signal filter** — still the weakest option, and now for a sharper reason.
  The problem is not only that ten trades carry the profit; it is that filtering
  *reduces exposure*, and exposure is the binding constraint. A filter that
  improves win rate while cutting trade count is moving the wrong dial.
- **Parameter optimisation** — still the highest-risk option. Section 5 is a
  live demonstration of it failing on this exact data.
- **Full rule replacement** — now the most interesting. The entry logic carries
  measurable information (86.7th percentile out of sample, double the random
  return at matched exposure), but it fires rarely. A model built on the same
  indicators, aimed at *generating more entries of similar quality* rather than
  filtering the existing ones, is working with the grain of what the data says.

The prior question is still what you want from the system. Over twenty years it
returns half of buy-and-hold at a quarter of the drawdown and half the exposure,
with better Sharpe and Calmar. As a risk-managed product that is defensible.
As a way to beat holding gold it is not there — but the reason is undersized
exposure, not a broken signal, and that is a more tractable problem than the one
we started with.
