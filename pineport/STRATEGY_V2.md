# Strategy v2 / v3 — same analysis, applied

> ## WHY MY NUMBERS DIFFER FROM YOUR TRADINGVIEW RUN
>
> Investigated with your v3 trade list (81 trades) and chart export (2,831 bars).
> **The port is correct. The difference is the data feed, and the size of the
> effect is itself the most important finding in this section.**
>
> **Verification on your own bars, v3:** where TradingView held a position, every
> value matches exactly — `price_stop_long` to 9.1e-13, `target_long` and
> `profitLockinUp` to 0.00, `bb_lower` to 1.5e-04. The one trade my port missed
> (2026-02-24) was a warm-up artefact: `kc_length_s = 569` needs 569 bars and the
> signal sits at bar 153 of the export. With warm-up handled, every gate agrees
> and the entry fires.
>
> **OANDA vs Dukascopy, 1,305 overlapping hours:**
>
> | | |
> |---|---|
> | mean absolute close difference | 0.390 (**0.0092%** of price) |
> | return correlation | **0.99933** |
> | BBlower crossovers, each feed | 47 and 47 |
> | **firing on the same bar** | **38 of 56 — 68%** |
>
> Both feeds see the same *number* of crossovers. But a band crossover is a
> knife-edge event — price below the band on one bar, above on the next — and a
> 0.009% difference flips roughly a third of them onto a different bar.
>
> **That compounds through the entry conditions.** Each knife-edge condition
> agrees ~68% of the time across feeds:
>
> | entry | knife-edge conditions | expected joint agreement | observed |
> |---|---|---|---|
> | long | 1 crossover + slow filters | ~68% × filters | **43%** (32 of 74) |
> | short | 3 crossunders + filters | 0.68³ ≈ 31% × filters | **~0%** (0 of 7 overlap) |
>
> My v2 took 12 shorts and yours took 7, on **entirely non-overlapping dates**.
> That is not a bug — it is exactly what the arithmetic predicts when a trade
> requires three simultaneous knife-edge conditions.
>
> ### The finding that matters
>
> This is not a measurement nuisance to be corrected away. **A strategy whose
> individual trades cannot be reproduced on a second feed of the same instrument
> has a robustness problem**, because your broker's execution feed is a third
> feed. The 65%-vs-50% win rate gap did not come from a logic difference; it came
> from choosing a data vendor.
>
> What survives across feeds is the *character* — win rate in the 50–65% band,
> profit factor 2–4.5, drawdown 8–22%. What does not survive is any specific
> trade, or any statistic precise enough to distinguish v1 from v3.
>
> **Consequences for everything in this file and `POSTMORTEM.md`:**
>
> * Comparisons *within* my dataset (v1 vs v2 vs v3, all on identical Dukascopy
>   bars) remain valid — the feed is held constant.
> * Comparisons of my absolute numbers against your TradingView numbers are not
>   like-for-like and never were.
> * The multi-market results stand: those tested whether the *logic* generalises,
>   using one feed throughout.
> * Differences of a few percentage points between strategy versions are below
>   the feed-noise floor and should not be treated as real.
>
> ---

> ## v3 UPDATE: the short fix works, and reduces to one line
>
> v3 adds `rates_bearish and macro_bearish` to the short entry. It successfully
> removes the −30% drawdown — but by eliminating the short side entirely.
>
> | short entry funnel (124,450 bars) | signals |
> |---|---|
> | 4 original conditions | 14 |
> | + `macro_bearish` | **0** |
> | + `rates_bearish` | 1 |
> | + both (v3 as written) | **0** |
>
> `macro_bearish` alone removes all 14, despite being true on 46% of bars. The
> reason is structural and familiar: `crossunder(close, BBupper)` requires price
> at the *upper* band, which essentially never coincides with the 4H close being
> *below* its average. Same contradiction as the RSI(5)-below-20 condition, one
> layer up.
>
> **v3 is therefore bit-identical to v2 with `allow_shorts = false`** — verified:
> 72 trades, same equity to the last decimal.
>
> | | trades | L/S | CAGR | Sharpe | max DD | Calmar | PF |
> |---|---|---|---|---|---|---|---|
> | v1 repaired | 138 | 138/0 | **4.83%** | **1.13** | −10.33% | **0.467** | **4.30** |
> | v2 (shorts on) | 88 | 76/12 | 1.15% | 0.27 | −30.55% | 0.038 | 1.27 |
> | **v3 (regime-gated)** | 72 | 72/0 | 2.80% | 0.67 | **−7.67%** | 0.365 | 2.63 |
>
> **The result is right; the mechanism is redundant.** Two extra filters, two
> extra `request.security` dependencies, and a FRED data dependency on the short
> path all achieve exactly what `allow_shorts = false` achieves. Given
> `POSTMORTEM.md` §5 showed the short side sits at the 33rd percentile against
> random short entry, deleting it outright is the simpler and more honest
> expression of the same conclusion.
>
> Everything else carries over unchanged from v2 long-only: entry quality at the
> **62.5th percentile** against random (v1: 99.5th), out-of-sample **61.3rd**
> (v1: 86.8th), and **1 of 7** never-tested markets clearing the bar.
>
> v3's genuine wins: the best drawdown of the three (−7.67%) and better profit
> concentration than v1 (81% vs 93% in the top ten trades).
>
> ---

Your revised script run through the full pipeline used on v1: verification,
20-year backtest, out-of-sample split, concentration, random-entry null,
and the seven never-tested markets.

**Verdict: worse than v1 on almost every measure, and it contains one new bug
that makes it untestable outside gold.**

---

## What changed

Structural changes — mostly things I recommended:

| change | my advice | correct? |
|---|---|---|
| removed RSI(1) trigger | "exactly zero effect" | **partly wrong — see below** |
| removed SMA(1)×SMA(2) trigger | "exactly zero effect" | **partly wrong** |
| removed ADX filter | "exactly zero effect" | yes |
| added real-yield filter | "modest, 5/6 windows" | yes, but at `rate_sma_len=5` not 20 |
| kept both code repairs | — | yes |

Plus roughly twenty parameter changes: stop 2.7% → 5.77%, limit 6.7 → 2.86,
`markUp` 190 → 135, `rangeL` 750 → 10, `lengthKCS` 942 → 569, `longVal` 0 → 1,
band periods and deviations, and the short-side stop 3.3% → 11.78%.

---

## Correction I owe you on the redundancy advice

I said removing the RSI and SMA triggers "changes nothing". That was true of
**v1's exact configuration** and is not a general property.

| | BB crossover bars | also SMA-cross | differ |
|---|---|---|---|
| v1 parameters | 3,429 | 2,637 | **792** |
| v2 parameters | 3,869 | 2,975 | **894** |

At the raw signal level they were never identical. The final *trade lists* were
identical at v1's settings because the other filters — chiefly ADX and the
squeeze — caught the extra 792. You removed those triggers **and** the ADX
filter **and** changed the band parameters, so the containment broke and v2 now
takes signals v1 rejected. I should have stated the condition, not the
conclusion.

---

## The new bug: `longVal = 1` is price-scale dependent

`valL` is a linear regression of a **de-meaned price series**, so its magnitude
scales with the instrument's price level. Changing the threshold from 0 to 1
converts a scale-invariant sign test into an absolute magnitude in the
instrument's own units.

| market | price level | `valL > 1` passes |
|---|---|---|
| GOLD | ~1,331 | 49.9% |
| GBPUSD | ~1.5 | **0.0%** |

The strategy **cannot trade any instrument priced below roughly 100.** GBPUSD
and AUDUSD produced literally zero trades; USDJPY produced one. This is the same
class of error as the dollar-denominated `markUp` ladder in v1 — a threshold
that only means something at the price level it was chosen at.

On gold, where it is testable, it is roughly neutral: Calmar 0.365 with
`longVal=1` against 0.301 with 0, on 72 vs 74 trades. **Set it back to 0.** It
buys almost nothing and costs the ability to test anywhere else.

---

## Results on gold, 20.6 years

| | trades | CAGR | Sharpe | max DD | Calmar | PF |
|---|---|---|---|---|---|---|
| **v1 repaired** | 138 | **4.83%** | **1.13** | −10.33% | **0.467** | **4.30** |
| v2 as written | 88 | 1.15% | 0.27 | **−30.55%** | 0.038 | 1.27 |
| v2 long-only | 72 | 2.80% | 0.67 | **−7.67%** | 0.365 | 2.63 |
| gold buy & hold | — | 10.52% | 0.64 | −45.25% | 0.230 | — |

**The shorts are catastrophic.** Twelve short trades turn a −7.67% drawdown into
−30.55% and cut Calmar from 0.365 to 0.038. The cause is the 11.78% short stop
in a market that rose 980% over the sample — a losing short can run nearly 12%
against you before it closes.

Changing `lengthKCS` from 942 to 569 is what let the shorts fire at all; in v1
the squeeze filter blocked every one. That was not an improvement. §5 of
`POSTMORTEM.md` established the short side sits at the **33rd percentile against
random short entry** — there is no edge there to unlock, only exposure to add.

By period:

| | v1 | v2 as written | v2 long-only |
|---|---|---|---|
| 2006–2022 CAGR | 1.19% | **1.78%** | 1.31% |
| 2006–2022 Calmar | **0.214** | 0.192 | 0.174 |
| 2023–2026 CAGR | **16.42%** | 1.45% | 7.76% |
| 2023–2026 Calmar | **2.513** | 0.058 | 0.977 |

v2 has slightly better out-of-sample CAGR and worse risk-adjusted numbers
everywhere.

---

## The signal itself got weaker

Random-entry null at matched exposure — long trades only, so the short damage is
excluded and this is a clean comparison of entry quality:

| | trades | exposure | strategy | random | **percentile** |
|---|---|---|---|---|---|
| v1, full sample | 138 | 27.8% | +334.5% | +84.9% | **99.5** |
| **v2, full sample** | 72 | 42.7% | +166.7% | +151.5% | **62.5** |
| v1, out-of-sample | 113 | 25.8% | +93.6% | +41.6% | **86.8** |
| **v2, out-of-sample** | 58 | 43.8% | +87.6% | +80.5% | **61.3** |

v2 holds positions far longer (exposure 43% vs 28%, from the wider stop), which
raises the random-entry benchmark as well — so more of its return is explained
by simply being in the market. **Timing quality fell from the 99.5th percentile
to the 62.5th.**

One genuine improvement: concentration. Top 10 trades are 81% of profit for v2
long-only against 93% for v1. Spread across more trades, which is the direction
you want — it is just attached to a weaker signal.

---

## Multi-market (with `longVal` set to 0 so it can trade)

| market | trades | **percentile** |
|---|---|---|
| COPPER | 48 | **86.9** ✅ |
| GBPUSD | 64 | 60.0 |
| AUDUSD | 60 | 45.0 |
| DAX | 50 | 29.5 |
| BRENT | 46 | 29.0 |
| USDJPY | 47 | 17.4 |
| S&P500 | 53 | 4.2 |

**1 of 7** clears the 80th percentile, against v1's 0 of 7. Both fail the
pre-registered criterion (≥6 of 7). One market clearing out of seven is what
chance produces.

---

## What to do

1. **Turn the shorts off.** `allow_shorts = false`, or revert `lengthKCS` to 942
   so the squeeze blocks them again. This single change takes Calmar from 0.038
   to 0.365 and drawdown from −30.55% to −7.67%. It is by far the biggest item.
2. **Set `longVal` back to 0.** Scale-dependent thresholds are the same trap as
   the dollar ladder, and this one is near-neutral on gold anyway.
3. **Reconsider the stop at 5.77%.** The pre-specified sweep in `FINDINGS.md` §9
   found a plateau at 2–3%, degrading above 4%, and 5.77% sits well outside it.
4. **Keep the real-yield filter, but at 20 days, not 5.** The robustness sweep
   showed 5d scoring 3/6 windows against 20d's 5/6 — 5 is on the noisy edge.

Even with all four applied, v2 would be roughly v1 with a weaker entry. **The
honest summary is that v1 repaired remains the better version**, and neither
clears the multi-market bar that determines whether any of this is worth
trading.
