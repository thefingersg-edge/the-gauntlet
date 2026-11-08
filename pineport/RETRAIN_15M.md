# 15m retrain — walk-forward result

**Verdict: adopt the structural changes, reject the retrained parameters.**

Method: 5 rolling folds across 2006–2023 (6-year train, 2-year test), parameters
chosen in-sample only and scored on the next block, six parameters searched,
50 random draws per fold. 2024–2026 sealed until one final look. ~250
evaluations in about 8 minutes on 4 cores — the equivalent sweep by hand in
TradingView is a day's work and cannot be nulled.

---

## 1. The search found nothing stable

| fold | test window | in-sample | **out-of-sample** | baseline | random | trades |
|---|---|---|---|---|---|---|
| 0 | 2012-03 – 2014-03 | 1.25 | −0.09 | −0.10 | −0.31 | 19 |
| 1 | 2014-03 – 2016-03 | 0.69 | 0.23 | −0.22 | −0.19 | 57 |
| 2 | 2016-03 – 2018-03 | 0.32 | 1.01 | **1.87** | −0.17 | 28 |
| 3 | 2018-03 – 2020-03 | 0.52 | −0.37 | **1.02** | 0.25 | 9 |
| 4 | 2020-03 – 2022-03 | 0.36 | 0.53 | **3.14** | −inf | 14 |

* **Optimised beat the untouched baseline in 2 of 5 folds.** That is a coin flip.
* Beat random draws in 4 of 5 — which only says the baseline's neighbourhood is
  better than random, not that the search improved on the baseline.
* In-sample Calmar 0.52 → out-of-sample 0.23.

**No parameter converged.** A parameter that matters settles to similar values
across folds; these ranged over 58–90% of their search interval:

| parameter | median | min | max | spread |
|---|---|---|---|---|
| bb_period_long | 97 | 21 | 129 | **90%** |
| bb_stdev_long | 1.00 | 0.70 | 2.13 | **71%** |
| sl_percent_long | 3.11 | 1.80 | 5.83 | **90%** |
| limit_percent_long | 4.72 | 3.14 | 6.89 | 58% |
| rsi_oversold | 52.6 | 40.2 | 60.2 | **80%** |
| lsma_length_long | 56 | 16 | 66 | 62% |

---

## 2. The holdout looked good — and it is one parameter, one window

| holdout 2024–2026 | trades | CAGR | Sharpe | max DD | PF | vs random |
|---|---|---|---|---|---|---|
| baseline | 31 | 6.94% | 0.77 | −20.55% | 1.47 | 34.5 |
| retrained | 37 | **16.57%** | 1.53 | −13.73% | 2.26 | 77.3 |

Tempting. But changing one parameter at a time shows where it comes from:

| change | **holdout** | **train 2006–2023** |
|---|---|---|
| baseline | 6.94% | 3.42% |
| `bb_stdev_long` 1.13 → 1.005 | **22.94%** | **3.26%** *(worse)* |
| `lsma_length_long` 49 → 56 | 0.28% | 3.06% |
| `sl_percent_long` 2.94 → 3.11 | 5.97% | 3.08% |
| `rsi_oversold` 54 → 52.6 | 5.97% | 3.34% |
| `limit_percent_long` 3.14 → 4.72 | 10.72% | 3.53% |
| all six | 16.57% | 3.11% |

Three of the six changes make the holdout **worse** on their own. The full set
(16.57%) is worse than the single best change (22.94%). And the whole gain sits
in `bb_stdev_long`, which **slightly reduces** returns across 17.8 years of
training data while tripling them in one 2.6-year window.

`limit_percent_long` is worse than useless as evidence: above ~4.7 the
take-profit never binds, so 4.72, 5.0 and 6.8 give byte-identical results. The
optimiser picked a value from a flat region — visible proof it was fitting noise
on that axis.

Holdout significance is weak in any case: 37 trades, +72.2% total, bootstrap
5th–95th percentile **+11% to +168%**.

---

## 3. What to adopt

**Adopt — justified by ablation, not by search:**

1. **Scale-free ladder.** `markUp`/`lockProfitUp`/`markDown`/`lockProfitDown`/
   `rangeL`/`rangeS` expressed as % of entry price. Verified equivalent at the
   calibration point (243 vs 242 trades, CAGR 3.69 vs 3.42 on 2006–2023).
2. **Scale-free sizing.** Divide by the actual stop distance, not the hardcoded
   50. At gold 4,565 the old rule sized ~3× too large and asked for positions
   worth 107% of the account.
3. **Cut three filters** the ablation cleared: the FRED rate gate (harmful out
   of sample), the long volatility gate and the long ADX filter (no measurable
   effect). 57 → 50 parameters and 150 → 243 trades on the training window.

**Reject:** the six retrained parameter values. Keep the baseline.

**Hypothesis worth forward-testing, not adopting:** `bb_stdev_long` near 1.0
instead of 1.13. It is one parameter that helps in one window and doesn't help
across 17.8 years. If it is real it will show up in the multi-market test and in
2026–2027 data; if it is noise, adopting it now costs real money.

---

## 4. The standing problem

57 parameters against 166 trades was 2.9 observations each; the structural cuts
take it to roughly 4.9. The usual minimum is 10. **This strategy still cannot
support the number of parameters it exposes**, and no date range fixes that —
only cutting parameters or generating more trades will.

That is also why this retrain came back empty, and why it was always likely to.
Running it was still worth it: an eight-minute null result is much cheaper than
adopting a parameter set that would have looked excellent on your chart.
