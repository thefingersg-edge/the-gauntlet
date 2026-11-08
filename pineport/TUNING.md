# Which parameters are worth tuning

Every input in the script measured one at a time on 124,450 hourly XAUUSD bars
(2006–2026), then cross-checked against the walk-forward harness. "Impact" is
the Calmar spread produced by moving the input across a sensible range;
baseline is the repaired config (138 trades, Calmar 0.467).

Reproduce with `python optimise.py sensitivity --csv xauusd_1h.csv`.

**The important distinction is not impact — it is whether the impact survives
walk-forward.** A parameter can move results a lot in-sample and still be
untunable, because the best value in one period is not the best value in the
next. `bullish_sma` is the cautionary example: third-highest impact, and its
chosen value scattered across 96% of its range between folds.

---

## Tier 1 — worth tuning (impact survives out of sample)

| parameter | Pine input | impact | evidence | suggested |
|---|---|---|---|---|
| `sl_percent_long` | `SL_percent_basedL` | 0.375 | **plateau at 2–3%**, beat the 6% setting in **5 of 6** walk-forward windows, degrades above 4% and below 1.5% | **2.0–2.7** |
| `bb_stdev_long` | `BBmultL` | **0.556** | highest impact of any input; the **only** parameter that converged in both walk-forward searches (42–46% spread) | 1.6–2.1 |

Only two. Both are essentially *exposure dials* — lower values take more trades
and spend more time in the market, which §7 of `FINDINGS.md` identifies as the
binding constraint. That coherence across three independent analyses is why
these two are worth touching and the rest are not.

Tune them by **sweeping and looking for a plateau**, not by running a search. A
broad good region is evidence; a single spiky best value is not.

---

## Tier 2 — real impact, but did NOT survive walk-forward

Set these to something sensible and leave them. Optimising them produced results
indistinguishable from chance (`FINDINGS.md` §8).

| parameter | Pine input | impact | why not to tune |
|---|---|---|---|
| `bullish_sma` | `bullish SMA` | 0.349 | chosen value scattered across **96%** of its range between folds |
| `lsma_length_long` | `LSMAlengthL` | 0.309 | at 10 the strategy collapses to 11 trades; 2 is the sane value |
| `bb_period_long` | `BBlengthL` | 0.270 | scattered 68% across folds |
| `profit_line_up` | `Profit Line Up` | 0.132 | untested out of sample |
| `r_ratio_long` | `r_ratioL` | 0.120 | feeds the target, which feeds the stop; interacts with `limit_percent_long` |
| `kc_length_l` | `lengthKCL` | 0.112 | live only since FIX 1 |
| `long_val` | `longVal` | 0.105 | live only since FIX 1 |
| `limit_percent_long` | `L_percent_basedL` | 0.101 | |
| `bb_length_l` | `lengthL` | 0.082 | live only since FIX 1 |
| `atr_long` | `atr_long` | 0.069 | scattered **100%** across folds |
| `vol_long` | `Vol Long` | 0.057 | scattered 83% |
| `kc_mult` | `multKC` | 0.054 | |

---

## Tier 3 — measured at essentially zero. Do not touch.

| parameter | Pine input | impact | why |
|---|---|---|---|
| `rsi_oversold` | `Over Sold` | **0.000** | any value from 5 to 80 gives the *identical* trade list. RSI(1) is only ever 0 or 100, so every threshold between them is the same test |
| `rsi_length_long` | `RSIlengthL` | 0.000 | the whole condition is a strict subset of the SMA crossover |
| `ladder_steps` | (rungs 1–5) | 0.000 | only the first rung is ever reached |
| `bb_period_short` | `Bollinger Period Length S` | 0.000 | short side |
| `flex_up` | `Limit Flex` | 0.000 | |
| `gap_up` | `Gap reducer Up` | 0.001 | |
| `trace_line_up` | `Trace Line Up` | 0.001 | |
| `adx_threshold` | `adx var` | 0.005 | the ADX filter passes 98.5% of bars |
| `adx_len` | `ADX DI Length` | 0.011 | |
| `adx_smooth` | `ADX Smoothing Length` | 0.019 | |
| `mult` | `BB MultFactor` | — | **declared and never referenced in the code.** The bands use `multKC` |
| all short-side inputs | `markDown`, `rangeS`, `lockProfitDown`, `SL_percent_basedS`, `L_percent_basedS`, `RSIoverBought`, `BBmultS`, `SSMAlength*` | — | the short leg fires 18–20 times in 20 years and produces an identical trade list when removed entirely |

That is **eleven inputs plus the entire short side** that can be left alone
permanently. If you have been including them in optimiser runs, you have been
paying for dimensions that cannot affect the answer — and every extra dimension
gives the search more room to fit noise.

---

## How to tune, given all of the above

1. **Sweep, don't search.** One parameter at a time, across a range, looking for
   a plateau. `FINDINGS.md` §8 shows that searching 7 or even 2 parameters beat
   the untuned baseline in 6 of 12 folds — exactly chance. The one credible
   improvement found in this entire exercise came from a pre-specified sweep.
2. **Check the trade count.** Below roughly 10 trades per test window, Calmar
   and Sharpe are noise. At `SL = 6%` the strategy takes 6.5 per window; part of
   what a tighter stop buys is simply a measurable strategy.
3. **Change one thing at a time.** Dave's three simultaneous edits were each
   neutral-to-positive alone and the worst configuration tested together
   (`FINDINGS.md` §9).
4. **Expect small gains.** Fixing the Keltner bug moved Calmar 0.32 → 0.46.
   Nothing found by tuning has come close to that. On this strategy, reading the
   code has paid better than searching the parameter space.
