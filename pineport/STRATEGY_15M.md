# Gold 15m v6 — first pass

> **CAVEAT FIRST: the port is not verified for this version.** Every number below
> comes from my Python port running your config on native OANDA M15. I have not
> been able to check it against your TradingView trade list, and this script
> removed the `plotchar(strategy.opentrades)` and stop/target plots I used to
> verify the 4H version at 99.6%. Treat everything here as provisional until
> that check is done. The 1H version matched at only 43%.

**To verify:** export the Strategy Tester trade list, or re-add
`plotchar(strategy.opentrades, "opentrades", "", location.top)` and export the
chart data.

---

## 1. Your split does exactly what a split should do

| window | trades | L/S | CAGR | Sharpe | max DD | PF | win% | expo | **vs random** |
|---|---|---|---|---|---|---|---|---|---|
| unseen 2006–2012 | 65 | 55/10 | 1.44% | 0.49 | −4.60% | 1.53 | 36.9% | 31.4% | **48.6** |
| **TRAIN 2013–2023** | 85 | 66/19 | **5.21%** | **1.49** | −4.35% | **3.84** | **62.4%** | 46.1% | **100.0** |
| unseen 2024–2026 | 16 | 12/4 | −1.10% | −0.20 | −13.24% | 0.86 | 50.0% | 26.4% | **15.2** |
| full 2006–2026 | 166 | 133/33 | 3.15% | 0.95 | −11.71% | 2.12 | 51.2% | 39.4% | 100.0 |

Perfect in-sample, random on one unseen side, below random on the other. That is
the textbook overfitting signature, and the two-sided holdout is what made it
visible — the 4H version could only ever show you one side.

**Two things genuinely improved:**

* **Concentration passes for the first time: 34.8%** of gross profit from the top
  10 trades, against a 40% pass mark and 71–100% in every previous version.
* **`longVal` / `shortVal` are now 0**, so the squeeze momentum test is a sign
  test rather than a dollar magnitude. That is a real scale-invariance fix.

**Median holding period is 772 bars = 8 days.** This is not a 15m strategy; it is
an 8-day swing strategy that uses 15m bars for entry timing. Good news for costs
(slippage is second-order at that horizon), but it explains why 485,843 bars
produce only 166 trades — still 8/year, still the measurability problem.

---

## 2. What helps and what doesn't

Each row removes **one** addition. A filter that earns its place should make the
unseen column *worse* when removed.

| variant | train trades | train CAGR | train pctile | **unseen trades** | **unseen CAGR** | **unseen pctile** |
|---|---|---|---|---|---|---|
| as written | 85 | 5.21% | 100.0 | 65 | 1.44% | **48.6** |
| **− rate filter (FRED)** | 138 | 4.95% | 100.0 | **89** | **3.25%** | **93.4** |
| − vol gate LONG | 87 | 5.06% | 100.0 | 65 | 1.41% | 47.2 |
| − vol gate SHORT | 89 | 4.72% | 100.0 | 68 | 0.51% | **34.8** |
| − ADX long | 90 | 5.09% | 100.0 | 67 | 1.44% | 50.8 |

**The FRED real-yield filter is actively harmful.** Removing it is neutral
in-sample (100.0 → 100.0) and takes the unseen window from the 48.6th to the
**93.4th percentile**, while restoring 24 trades. It also improves the *other*
unseen window:

| window | as written | **no FRED** |
|---|---|---|
| unseen 2006–2012 | 1.44% CAGR, 48.6 pctile | **3.25% CAGR, 93.4 pctile** |
| unseen 2024–2026 | −1.10% CAGR, 15.2 pctile | **+5.00% CAGR, 41.0 pctile** |
| full 2006–2026 | 3.15% CAGR, 166 trades | 4.08% CAGR, 253 trades |

**Why it fails.** The filter says "10y real yield below its 26-day average = buy
gold". Its actual forward-return edge, measured directly:

| window | real yield mean | filter passes | edge added |
|---|---|---|---|
| unseen 2006–2012 | 1.32 | 57.6% | +0.0080% |
| **TRAIN 2013–2023** | **0.32** | 49.6% | **+0.0153%** |
| unseen 2024–2026 | 1.97 | 48.8% | **−0.0281%** |

The training decade is the *only* one where real yields sat near zero. The
relationship is strongest there, halves in 2006–2012, and **changes sign** in
2024–2026. You fitted a macro filter on the one regime in which it worked.

**Verdict on each addition:**

| addition | keep? | evidence |
|---|---|---|
| FRED rate filter | **remove** | hurts both unseen windows, neutral in-sample |
| vol gate SHORT | **keep** | removing it drops unseen 48.6 → 34.8 |
| vol gate LONG | drop on parsimony | 47.2 vs 48.6 — indistinguishable |
| ADX long | drop on parsimony | 50.8 vs 48.6 — indistinguishable |
| ADX short, squeeze, ladder | pending | ablation still running |

---

## 3. Where this leaves it

Dropping the FRED filter gives the **best out-of-sample number in the whole
project** — 93.4th percentile on 89 unseen trades. But two things temper it:

1. The second unseen window still sits at the **41st percentile**. Removing the
   filter makes it less bad, not good.
2. **I found this by searching.** By the project scoreboard, twelve things have
   been tested, two survived, and *both were bug fixes rather than discoveries* —
   nothing found by searching has ever held up.

So the honest reading is: the rate filter is confirmed harmful (that direction is
well supported — it fails in-sample-neutral and hurts both holdouts), but
"removing it produces an edge" is a hypothesis, not a result.

**Next step, in order:**

1. Verify the port against your trade list. Nothing above means much until then.
2. Re-run without the FRED filter and **pre-register** the criterion before
   looking: multi-market on the 7 unseen instruments at M15, ≥6 of 7 above the
   80th percentile.
3. The ladder is still dollar-denominated (`markUp` 170, `rangeL` 60). Gold ran
   1050–2118 in training and 1987–5563 in 2024–2026. Convert to ATR multiples
   before the next retrain, not after.

---

## 4. The losing streak from December 2025

**Short answer: there is nothing anomalous to fix.**

Reshuffling the same 253 trades 4,000 times — same trades, same distribution,
random order — gives the distribution of drawdowns this strategy *should*
produce:

| | actual | shuffled median | shuffled 5–95% | **P(at least this bad)** |
|---|---|---|---|---|
| worst drawdown | **−14.55%** | −16.52% | −24.63% to −11.89% | **71.9%** |
| longest losing streak | **6** | 7 | — | **88.5%** |

The current drawdown is **milder than the median** you would expect from
reordering its own trades, and the streak is **shorter** than the median. 72% of
random reorderings produce a worse drawdown. This is the ordinary bad patch, not
a broken filter.

### What actually happened

Gold swung **−29.2% peak-to-trough in 2026** (5586 → 3958). The nine trades since
December 2025:

| date | dir | entry | exit | return |
|---|---|---|---|---|
| 2025-10-30 | LONG | 3959.6 | 4129.6 | +4.29% |
| 2025-12-02 | LONG | 4212.5 | 4382.5 | +4.04% |
| **2026-01-16** | **SHORT** | 4565.2 | 4828.9 | **−5.78%** |
| 2026-04-02 | LONG | 4646.3 | 4816.3 | +3.66% |
| 2026-04-17 | LONG | 4797.1 | 4739.6 | −1.20% |
| 2026-05-11 | LONG | 4690.6 | 4627.5 | −1.35% |
| 2026-06-10 | LONG | 4179.3 | 4056.7 | −2.93% |
| 2026-06-19 | LONG | 4179.1 | 4089.2 | −2.15% |
| **2026-07-01** | **SHORT** | 3981.6 | 4199.4 | **−5.47%** |
| 2026-07-10 | LONG | 4115.1 | 3999.5 | −2.81% |

**Two short trades carry most of the damage.** Both hit the full 6% short stop.
Every long loss stayed inside 3%.

And the longs are not the problem at all — 2024–2026 is their **best era**:

| window | longs | win% | sum ret | shorts | win% | sum ret |
|---|---|---|---|---|---|---|
| 2006–2012 | 79 | 41.8% | +76.9% | 10 | 60.0% | +11.7% |
| 2013–2023 | 119 | 50.4% | +129.6% | 19 | 73.7% | +19.4% |
| **2024–2026** | 22 | **59.1%** | **+42.8%** | 4 | **25.0%** | **−14.3%** |
| FULL | 220 | 48.2% | +249.3% | **33** | 63.6% | **+16.8%** |

### Two responses tested — neither fitted to the streak

| | full 2006–26 | unseen 2006–12 | unseen 2024–26 | the streak |
|---|---|---|---|---|
| no-FRED base | 4.08% / DD −14.55 | **3.25%** | 5.00%, PF 1.36 | **−13.71%** |
| **+ long only** | 3.75% / **DD −11.19**, PF **2.13** | 2.15% | **11.15%, Sh 1.52, PF 2.77** | **−3.92%** |
| + ATR stops | **1.60%** | **0.37%** | 3.99% | +2.29% |
| + both | 1.62% | 0.27% | 6.72% | +5.22% |

**ATR-scaled stops "fix" the streak and destroy the strategy** — full-sample CAGR
4.08% → 1.60%, and the 2006–2012 window collapses from 3.25% to 0.37%. This is
the textbook shape of a repair fitted to recent pain. Reject.

**Long-only is the only defensible change**, and it is a *risk* decision, not a
return improvement:

* better: max drawdown −14.55% → −11.19%, profit factor 1.95 → 2.13, and
  2024–2026 goes from 5.00% CAGR / Sharpe 0.63 to **11.15% / Sharpe 1.52**
* worse: full-sample CAGR 4.08% → 3.75%, and unseen 2006–2012 drops 3.25% → 2.15%
* structural case: **33 short trades in 20 years for +16.8% total** is not a
  business. They win often and small, lose rarely and large, and they produced
  both big losses in this streak. The independent 4H analysis reached the same
  conclusion from different data.

### On adding a new indicator

Don't. The evidence against it is in section 2 of this document: the last macro
filter added — the FRED real-yield gate — looked neutral in-sample and cost the
strategy 45 percentile points out-of-sample, because it was fitted to the one
decade where real yields sat near zero. Adding another indicator to explain six
trades, in a drawdown that is milder than its own bootstrap median, is the same
mistake against a smaller sample.

The strategy does not have a December-2025 problem. It has a **33-shorts-in-20-
years** problem, and that was true before this streak started.

---

## 4b. MULTI-MARKET GAUNTLET — 2 of 9, REJECT

The scale-free config, run on native M15 for all ten markets. Stop scaled by
each instrument's own ATR; nothing else tuned per market. Criterion fixed before
running: ≥80th percentile vs random entry at matched exposure, ≥6 of 9 non-gold.

| market | vol | stop% | trades | CAGR | Sharpe | max DD | **pctile** |
|---|---|---|---|---|---|---|---|
| *XAUUSD (known)* | 1.00 | 2.94 | 273 | *3.97%* | *0.99* | *−7.15%* | *100.0* |
| XAGUSD | 1.80 | 5.30 | 296 | 1.30% | 0.45 | −7.18% | 75.0 |
| XCUUSD | 1.59 | 4.68 | 267 | 0.61% | 0.24 | −16.04% | 27.0 |
| BCOUSD | 2.02 | 5.94 | 306 | 0.06% | 0.04 | −13.36% | 18.0 |
| SPX500USD | 0.86 | 2.53 | 360 | 2.40% | 0.51 | −14.08% | 52.8 |
| DE30EUR | 1.31 | 3.85 | 177 | 2.24% | 0.21 | −62.47% | 13.2 |
| **EURUSD** | 0.53 | 1.56 | 351 | 0.81% | 0.26 | −10.69% | **98.5** |
| **GBPUSD** | 0.55 | 1.62 | 348 | 0.15% | 0.06 | −11.51% | **88.5** |
| USDJPY | 0.58 | 1.71 | 265 | 0.27% | 0.10 | −14.22% | 27.5 |
| AUDUSD | 0.71 | 2.09 | 303 | −0.56% | −0.17 | −14.15% | 13.0 |

**2 of 9. REJECT.**

And the two that pass are economically empty: EURUSD clears the 98.5th percentile
on **0.81% CAGR at Sharpe 0.26**, GBPUSD the 88.5th on **0.15%**. A high
percentile against random entry means the *timing* carries information; it does
not mean the result survives a spread. Both would be consumed by costs.

Previous versions scored 0/7, 1/7 and 0/7. This one scores 2/9 with the bugs
fixed, the parameters made scale-free and the dead filters removed. **The
engineering improved and the generalisation did not.**

### What this does and does not prove

Gold reaches the 100th percentile on 273 trades with Sharpe 0.99 and a −7.15%
drawdown. That is a genuinely good result and it cannot be trusted, because gold
is where the strategy was built, tuned, and re-tuned. Nine other markets say the
logic does not transfer.

Two readings fit the evidence:

1. **It is fitted to gold.** Strongly favoured by the base rate here — fifteen
   ideas tested in this project, two survived, both bug fixes.
2. **Gold genuinely differs.** Possible; it is the only asset in this set that
   is simultaneously a currency, a commodity and a reserve holding. But nothing
   in the data distinguishes this from (1).

**No amount of further backtesting separates them**, because every historical
test on gold reuses the data the strategy was shaped on. The only evidence that
can settle it is forward performance on data that did not exist when the
parameters were frozen.

---

## 5. BUG: results change with the loaded chart history

**Symptom:** full history shows several 2026 trades; a 365-day range shows two,
both winners.

**Cause:** `entryCloseL := close[since_entry_long]` uses a *dynamic* history
offset. Pine's default `max_bars_back` buffer is **300 bars**, and the holding
periods are far longer:

| config | median | 90th | **max** | trades needing >300 bars |
|---|---|---|---|---|
| as written | 772 | 2,368 | **6,595** | **81%** |
| no FRED | 727 | 2,031 | 5,670 | 77% |

Pine determines the buffer by scanning the loaded history, so **the amount of
chart history loaded changes the buffer, which changes the trades.** Raising
`max_bars_back` is not a complete fix either — it caps at 5,000, below the
6,595-bar maximum hold.

This is also why the 4H version verified at 99.6% while this one drifts: 4H held
~59 bars median, comfortably inside the 300-bar default. At 15m it is 2–20×
past it.

### Fix — capture the entry close in a `var` instead of looking it back up

```pine
// was: entryCloseL = 0.0 / entryCloseS = 0.0  (plain, reset every bar)
var float entryCloseL = 0.0
var float entryCloseS = 0.0

// set them at the moment the position opens -- `bought` / `sold` are already
// defined above. This is the same value close[since_entry_long] was meant to
// return, with no history lookup and no buffer dependency.
if bought
    entryCloseL := close
if sold
    entryCloseS := close
```

Then delete these two lines from inside the position blocks:

```pine
    entryCloseL := close[since_entry_long]      // DELETE
    entryCloseS := close[since_entry_short]     // DELETE
```

`since_entry_long` / `since_entry_short` and their `ta.barssince` calls become
dead once this is done and can be removed.

**Why this is exact, not an approximation:** `ta.barssince(bought)` is 0 on the
bar `bought` turns true, so `close[since_entry_long]` resolves to the close of
the bar the position opened on — which is precisely the value the `var` holds.

### Consequence

The Python port computes this correctly (no buffer limit), so **the port's
numbers in sections 1–4 are the valid ones and the TradingView figures for this
15m version are not.** Re-run the training after applying the fix — the
parameters were fitted against corrupted exits.
