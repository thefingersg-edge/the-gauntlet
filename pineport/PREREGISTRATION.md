# Pre-registration: does gold-in-EUR confirmation improve the strategy?

> ## RESULT: BOTH HYPOTHESES REJECTED (2/6 each)
>
> Run on XAUEUR derived from Dukascopy EURUSD, 2006–2026, all six folds usable.
>
> | hypothesis | mean Calmar | median | avg trades | beats H0 | verdict |
> |---|---|---|---|---|---|
> | H0 control (XAUUSD macro) | **0.989** | **0.397** | 13.8 | — | — |
> | H1 swap (XAUEUR macro) | 0.805 | 0.258 | 14.5 | **2/6** | rejected |
> | H2 both (USD and EUR) | 0.920 | 0.264 | 12.5 | **2/6** | rejected |
>
> Trade counts stayed at 12.5–14.5 per window, above the ~10 floor, so this is a
> genuine negative rather than the inconclusive-through-thinness failure mode
> anticipated below.
>
> **Why** (diagnosed after the fact, so treat as explanation not evidence):
> hourly XAUUSD and XAUEUR log returns correlate at **0.870**, and the two macro
> filters agree on **81.8%** of bars (53.8% vs 53.2% bullish). The
> EUR-denominated filter is largely a noisier copy of the USD one. Compounding
> that, §10 of `FINDINGS.md` had already measured the XAUUSD macro filter itself
> as roughly a wash — so this swapped one near-inert filter for another.
>
> The structural rationale still holds: XAUUSD *is* a ratio and half of every
> move *is* the denominator. What the data says is that at a 10–40 day holding
> period, on this entry logic, the distinction does not survive the correlation
> between the two series. A basket (EUR/JPY/GBP/CHF) would decorrelate further
> than EUR alone, which is the honest follow-up — but on this evidence I would
> not expect it to rescue the idea.
>
> ---

**Written before any XAUEUR data was fetched or examined.** The point of writing
it first is that every decision that could be tuned after seeing results — the
filter form, the lookback, the success criterion — is fixed here. §8 of
`FINDINGS.md` showed that searching this data finds noise; the only credible
finding so far (the stop-loss plateau) came from a pre-specified test. This
follows the same discipline.

---

## Rationale (structural, not empirical)

XAUUSD is a ratio. Half of every move is the denominator. A strategy built only
on XAUUSD price cannot distinguish:

* **gold demand** — gold rising against all currencies, and
* **dollar weakness** — the USD falling against everything, gold included.

Those have different persistence. A gold-demand move is driven by real yields,
central bank buying and investment flows; a dollar move can reverse on a single
Fed communication. The existing 4H macro filter (`close > sma(close, 20)` on
XAUUSD) cannot tell them apart, because it is computed on the ratio itself.

Gold priced in EUR isolates the numerator. If gold is rising in both USD and EUR
terms, that is gold demand. If only in USD, it is a dollar move.

This rationale does not depend on the backtest. **A null result is still
informative** — it would say the distinction does not matter at this horizon,
which is worth knowing.

---

## Hypotheses (fixed)

Both use the *same filter form* as the existing macro filter — 4H close above a
20-period 4H SMA — changing only which series it is computed on. Keeping the
shape identical means the comparison isolates the denominator, not the filter
design.

| id | description |
|---|---|
| **H1 (swap)** | Replace the macro filter: require `XAUEUR 4H close > XAUEUR 4H SMA(20)` instead of the XAUUSD version |
| **H2 (both)** | Require *both*: XAUUSD macro bullish **and** XAUEUR macro bullish |
| **H0 (control)** | Current logic, XAUUSD macro filter only |

No other parameter changes. `bullish_sma` stays at 20; it is **not** re-tuned
for the new series. Re-tuning it would reintroduce the search problem this test
exists to avoid.

## Base configuration

`fix_keltner_range=True`, `fix_long_stop_ratchet=True`, everything else at
script defaults. Long side only (the short leg produces an identical trade list).

## Test procedure

The six rolling walk-forward windows already defined in `optimise.py`
(6y train / 2.5y test, 2012–2026). Parameters are **not** selected on the
training windows — these are fixed configurations, so every window is an
out-of-sample observation.

## Primary metric

Calmar in each test window. Reported: mean, median, and windows won against H0.

## Success criterion (fixed in advance)

* **≥ 5 of 6 windows** beating H0 → treat as a real improvement. This is the bar
  the stop-loss finding cleared (5/6).
* **4 of 6** → **not evidence.** §8 established that 4/6 is what chance produces
  here; the wide7 search hit 4/6 and collapsed to 2/6 when re-run with fewer
  parameters.
* **≤ 3 of 6** → reject.

Secondary check: the trade count per window must stay above ~10, or the Calmar
values are noise regardless of which way they point.

## Anticipated failure modes

* **Fewer trades.** Both H1 and H2 can only remove signals, never add them. H2 in
  particular is a strict subset of H0. If the trade count drops below ~10 per
  window the test is inconclusive rather than negative.
* **EUR is not a neutral yardstick.** EURUSD has its own drivers; "gold in EUR"
  is gold against one currency, not against a basket. A stronger version would
  use a basket (EUR, JPY, GBP, CHF). If H1/H2 look promising, that is the
  follow-up — not a re-tune of this one.
* **Correlation.** XAUUSD and XAUEUR are highly correlated, so the filter may
  simply be a noisier copy of the existing one and change little.

---

## Data required

Dukascopy hourly, same pipeline and filtering as XAUUSD:

```bash
.venv/bin/python dukascopy.py --instrument XAUEUR --start 2006 --out xaueur_1h.csv
```

Alternatively fetch `EURUSD` and derive `XAUEUR = XAUUSD / EURUSD`; the derived
form is a useful cross-check on the direct series if both are available.

---
---

# Test 2 — does a real-yield regime filter improve the strategy?

> ## RESULT: H1 CLEARS THE BAR (5/6). H2 REJECTED (2/6).
>
> DFII10, 5,900 daily observations 2003–2026, 1 business day lag, all six folds.
>
> | hypothesis | mean | median | avg trades | beats H0 | verdict |
> |---|---|---|---|---|---|
> | H0 control (price macro) | **0.989** | 0.397 | 13.8 | — | — |
> | H1 swap (real yield) | 0.973 | **0.691** | 12.8 | **5/6** | **clears the bar** |
> | H2 both | 0.869 | 0.293 | 10.0 | 2/6 | rejected |
>
> **The anticipated failure mode did not occur.** The two filters agree on only
> **55.8%** of bars, against 81.8% for XAUEUR. The real yield carries genuinely
> different information — which is exactly the reason this was worth testing
> after Test 1 failed.
>
> **Robustness (checks, not a search — 20d was kept regardless):**
>
> | MA length | 5d | 10d | **20d** | 30d | 50d | 100d |
> |---|---|---|---|---|---|---|
> | beats H0 | 3/6 | 4/6 | **5/6** | 5/6 | 4/6 | 1/6 |
>
> A plateau from ~10–50 days, degrading at 5 (too noisy) and 100 (too slow).
> Plateau, not spike.
>
> | publication lag | 0d | **1d** | 2d | 3d | 5d |
> |---|---|---|---|---|---|
> | beats H0 | 4/6 | **5/6** | 4/6 | 5/6 | 5/6 |
>
> **Completely insensitive to the lag.** This matters more than it looks: a
> result exploiting publication timing would collapse as the lag grew. It does
> not, which rules out the most plausible lookahead artefact.
>
> **What it does NOT show.** On the full sample it is a *tie* — Calmar 0.468 vs
> 0.467, Sharpe 1.01 vs 1.13 (worse), drawdown −9.21% vs −10.33% (better). It is
> better out-of-sample (Calmar 0.274 vs 0.214) and **worse** in 2023–26 (1.757 vs
> 2.513). The win is on *consistency*, not return: it beat H0 in five windows
> including both of H0's negative ones, and lost only the single largest window.
> That is the profile of a risk-reducing regime filter — improving the worst
> periods while giving up some of the best.
>
> 5/6 is p ≈ 0.11 one-sided. It clears the bar set in advance, and the
> robustness checks are the kind the wide7 search failed. Treat as a real but
> modest effect, worth deploying and worth re-checking on new data.
>
> ---

**Written before the FRED data was fetched.** Same discipline, same fixed
criterion. Test 1 was rejected; this is a different driver, not a re-run of the
same idea with a knob moved.

## Rationale (structural)

Gold pays no yield, so its opportunity cost is the real interest rate. This is
the most-cited driver in the literature and the dominant one in current
conditions — J.P. Morgan's July 2026 work put it at roughly **$20/oz per basis
point** of 10-year real yield since late February 2026.

Crucially, and unlike Test 1, **this is not a rearrangement of the same price
series.** XAUEUR failed largely because it correlates 0.870 with XAUUSD. The
10-year TIPS yield is a different instrument in a different market, so it can
carry information the gold chart does not already contain. That is the specific
reason this is worth a second test after the first was rejected.

## Direction

Gold rises when real yields fall. So the gold-bullish state is the **inverse**
of the price filter: yield *below* its own moving average, not above.

## Hypotheses (fixed)

| id | description |
|---|---|
| **H1 (swap)** | Replace the macro filter: require `DFII10 < SMA(DFII10, 20d)` |
| **H2 (both)** | Require *both*: XAUUSD 4H macro bullish **and** real yield falling |
| **H0 (control)** | Current logic, XAUUSD macro filter only |

`rate_sma_days = 20`, chosen to mirror `bullish_sma = 20`. **Not tuned.** If
this is rejected, it is rejected — trying 10, 50 and 100 afterwards and keeping
the best is precisely the search that §8 showed produces chance results.

## Data handling (fixed in advance)

* Series: **DFII10**, 10-year TIPS yield, daily from 2003-01-02 — covers the
  whole 2006–2026 sample.
* **One business day publication lag applied**, in
  `fetch_fred.load_daily_series(lag_days=1)`. The H.15 release lands in the
  afternoon of the day it describes, so treating it as knowable that morning
  would be lookahead. One day is immaterial at a 10–40 day holding period and
  removes the question.
* Reindexed onto hourly bars with `ffill` — carries the last *known* value
  forward, never reaches forward to an unpublished one.
* FRED's `.` missing markers dropped, not interpolated.

## Success criterion (identical to Test 1)

* **≥ 5 of 6 windows** beating H0 → real improvement
* **4 of 6** → not evidence
* **≤ 3 of 6** → reject

Secondary: trade count must stay above ~10 per window or the result is
inconclusive rather than negative.

## Anticipated failure modes

* **Too slow a signal.** A 20-day MA on a daily series is a slow regime flag; the
  strategy's entries are hourly. It may simply be too coarse to matter.
* **Regime-dependence.** Real yields mattered enormously in 2013 (taper tantrum)
  and 2022–2026; they may have been irrelevant in between. Six windows may split
  along that line, which would show up as a 3/6 rather than a clean answer.
* **Correlation with the existing filter.** If "real yield falling" and "gold
  above its 4H MA" agree most of the time, this fails for the same reason
  Test 1 did. That agreement rate will be measured and reported either way.

---
---

# Test 3 — does the strategy generalise to silver?

**Written before any XAGUSD data was fetched.**

## Why this is the strongest test available

Every result so far comes from one instrument over one 20-year sample. The
repairs, the stop-loss range, the real-yield filter — all were found on gold,
and the same data has now been looked at many times. Even with pre-registration,
repeated use of one dataset erodes how much any single result means.

Silver has **never been touched**. Nothing has been tuned on it, no parameter
chosen with reference to it, and I have not seen a single silver number. It is
therefore the only genuinely clean out-of-sample test left.

The logic under test is not gold-specific in its construction: "buy when price
crosses up through a Bollinger lower band while a Keltner squeeze is on and
momentum is positive, exit on a ratcheting trailing stop" makes no reference to
anything unique to gold. If it captures a real mean-reversion-into-trend effect
it should appear in a correlated but distinct precious metal. If it appears only
in gold, it was fitted to gold's particular history.

**A null result here is more valuable than another gold success**, because it
would say the 20 years of gold work described one instrument's past rather than
a market behaviour.

## Configuration (fixed, nothing tuned)

`fix_keltner_range=True`, `fix_long_stop_ratchet=True`, long side only, and
**every other parameter exactly as used for gold**. No re-fitting of any kind.

## Primary metric

Percentile against the random-entry null at matched exposure and holding
periods (`null_test.py`) — the same measure that showed gold's entry logic
carries information (99.5th full sample, 86.7th out-of-sample).

## Success criterion (fixed in advance)

Full silver sample, percentile vs random entry:

* **≥ 95th** → generalises. The edge is a market behaviour, not a gold artefact.
* **80th–95th** → weak generalisation. Consistent with a small real effect.
* **< 80th** → **does not generalise.** Treat the gold results as instrument-
  specific and stop building on them.

Secondary, reported but not decisive: Calmar and Sharpe against silver
buy-and-hold, and the out-of-sample (2006–2022) split.

## Anticipated failure modes — read these before interpreting

* **Volatility mismatch, the big one.** Silver is roughly twice as volatile as
  gold. The 2.7% trailing stop was chosen in gold's volatility regime and will
  be far tighter in silver terms, cutting trades short. **A failure caused by
  this is not the same as the logic failing.** So a secondary run scales the
  stop by the ratio of silver's median ATR% to gold's, a single deterministic
  number with no search involved. The identical-parameter run stays primary;
  the scaled run is reported alongside and clearly labelled.
* **Different market structure.** Silver has a large industrial demand component
  gold does not, and is more prone to squeezes and manipulation episodes
  (2011, 2021). Its trend behaviour genuinely differs.
* **Thinner history.** Dukascopy's XAGUSD may start later or have more gaps than
  XAUUSD. Coverage will be reported; folds without coverage are dropped.

## Data required

```bash
.venv/bin/python dukascopy.py --instrument XAGUSD --start 2006 --out xagusd_1h.csv
```

---
---

# Test 4 — does the entry logic work across markets when volatility-scaled?

> ## RE-RUN ON OANDA DATA: 1 of 7. Still rejected.
>
> The original run used Dukascopy. Repeated on OANDA — the feed the TradingView
> charts use, with deeper CFD history (21.6y rather than 12.8–14.6y) — the
> verdict is unchanged, but the detail is instructive.
>
> | market | years | trades | **OANDA pctile** | *Dukascopy pctile* | drift |
> |---|---|---|---|---|---|
> | *GOLD* | 20.4 | 120 | ***85.2*** | *99.4* | 10.63% |
> | *SILVER* | 20.4 | 128 | ***80.7*** | *70.7* | 9.28% |
> | *EURUSD* | 21.6 | 133 | ***81.6*** | *88.9* | −0.74% |
> | **BRENT** | 21.6 | 109 | **84.9** ✅ | 79.2 | 3.73% |
> | USDJPY | 21.6 | 139 | 54.0 | 37.1 | 2.02% |
> | GBPUSD | 21.6 | 137 | 51.5 | 79.3 | −1.62% |
> | COPPER | 21.6 | 95 | 51.3 | 86.9 | 7.22% |
> | AUDUSD | 21.6 | 133 | 38.6 | 58.7 | −0.47% |
> | DAX | 21.6 | 107 | 17.3 | 19.8 | 8.77% |
> | S&P500 | 21.6 | 122 | 11.7 | 4.2 | 8.98% |
>
> **1 of 7 clears the 80th percentile.** The criterion required 6 of 7.
>
> **What changed, and what it means.** Gold fell from the 99.4th percentile to
> the 85.2nd simply by changing vendor. Copper went 86.9 → 51.3; GBPUSD
> 79.3 → 51.5; the one market that passes on OANDA (Brent, 84.9) scored 79.2 on
> Dukascopy and would have failed. **The per-market percentile is not stable to
> the data source.** Only the aggregate verdict is: 0 of 7 on one feed, 1 of 7
> on the other. Both reject.
>
> Gold's 99.4th percentile — the single most encouraging number in this project,
> the one that motivated the whole multi-market investigation — was substantially
> a feed artefact. On the feed that matches the charts, it is 85.2.
>
> **The equity indices remain the most damning result.** S&P 500 at 11.7 and DAX
> at 17.3, on 21.6 years each, with the strongest upward drift of anything
> tested (9.0% and 8.8% CAGR). A long-only dip-buying strategy is beaten by
> random entry at matched exposure in precisely the two markets where it should
> work best. That holds on both feeds.
>
> ---
>
> ## Original Dukascopy result: 0 of 7 never-tested markets cleared the bar.
>
> | market | years | vol | stop% | trades | exposure | strategy | random | **percentile** | drift |
> |---|---|---|---|---|---|---|---|---|---|
> | *GOLD* | 20.6 | 1.00 | 2.70 | 138 | 27.8% | +334.5% | +85.5% | ***99.4*** | 10.52% |
> | *EURUSD* | 20.6 | 0.52 | 1.39 | 134 | 26.4% | +22.9% | −0.0% | ***88.9*** | −0.14% |
> | *SILVER* | 20.6 | 2.09 | 5.63 | 155 | 31.5% | +158.3% | +121.6% | *70.7* | 9.60% |
> | GBPUSD | 20.6 | 0.53 | 1.43 | 135 | 24.8% | +8.0% | −5.1% | **79.3** | −1.19% |
> | BRENT | 14.6 | 1.94 | 5.25 | 70 | 25.1% | +55.0% | +13.2% | **79.2** | −1.25% |
> | AUDUSD | 20.6 | 0.72 | 1.94 | 119 | 24.0% | +4.5% | +1.0% | **58.7** | −0.20% |
> | COPPER | 14.4 | 1.41 | 3.82 | 89 | 23.3% | +7.0% | +18.1% | **46.3** | 3.61% |
> | USDJPY | 20.6 | 0.57 | 1.53 | 129 | 27.9% | +2.6% | +10.8% | **37.1** | 1.42% |
> | DAX | 12.8 | 1.00 | 2.69 | 81 | 15.0% | −4.5% | +18.9% | **19.8** | 8.93% |
> | S&P500 | 14.5 | 0.81 | 2.19 | 71 | 28.3% | +14.4% | +67.0% | **11.2** | 12.73% |
>
> *Italic rows are the previously-examined markets and carry no evidential
> weight, as fixed in advance.*
>
> **Zero of seven.** Every market had 70+ trades, so none is inconclusive on
> sample size. Mean pairwise correlation of strategy returns was −0.058, so
> these were close to genuinely independent tests rather than one test repeated.
>
> **The pre-registered reading applies without qualification: the vol-scaling
> was fitted to gold and EURUSD.** Two markets clearing a threshold out of nine
> examined is what chance produces.
>
> Two details worth keeping:
>
> * **GBPUSD (79.3) and BRENT (79.2) came within a whisker of the 80 bar.** With
>   a threshold of 75 the headline would read "2 of 7" and I would have been
>   writing about a promising partial result. The bar was set in advance
>   precisely so that near-misses could not be reinterpreted after the fact.
> * **The equity indices are the most damning.** S&P500 (11.2) and DAX (19.8)
>   are the two markets with the strongest upward drift — 12.7% and 8.9% CAGR —
>   and the strategy did *worse than random entry* in both. If the logic were
>   "buy dips in a rising market", these are where it should shine. It is
>   beaten by picking dates out of a hat.
>
> ---

**Written before any of the new market data was fetched.**

## What prompted this, stated plainly

Test 3 concluded the strategy does not generalise, based on silver reaching only
the 70th percentile. That conclusion was then undermined by an inconsistency in
my own method: silver had been volatility-scaled, EURUSD had not. Applying the
same scaling to EURUSD put it at **89.3rd percentile — on an instrument with
essentially zero drift (−0.14% CAGR)**.

That matters because it rules out the most likely benign explanation. If the
edge were merely "buy dips in something that goes up", it could not work on a
driftless instrument. It appears to.

**This insight is post-hoc.** It came from re-examining data already used
repeatedly, which is precisely the process that produced false positives in §8
of `FINDINGS.md`. Two of three markets clearing a threshold could easily be
luck. It therefore needs testing on markets that have never been touched, with
the criterion fixed in advance. That is what this is.

## Markets (fixed now, so they cannot be selected later)

Ten instruments, chosen for structural variety rather than expected results —
metals, FX majors, a commodity currency, equity indices, energy, industrial
metal:

| already held | never tested |
|---|---|
| XAUUSD, XAGUSD, EURUSD | GBPUSD, USDJPY, AUDUSD, USA500IDXUSD, DEUIDXEUR, BRENTCMDUSD, COPPERCMDUSD |

**The seven "never tested" instruments are the actual test.** The three already
held are reported for continuity but carry no evidential weight — their results
are already known and cannot count as confirmation.

Any instrument that fails to download is dropped and reported. Instruments are
**not** substituted after the fact; if GBPUSD fails, the test runs on six, it
does not acquire NZDUSD as a replacement.

## Configuration (fixed, nothing per-market tuned)

`fix_keltner_range=True`, `fix_long_stop_ratchet=True`, long only, everything
else at the gold defaults, with exactly one adjustment:

    sl_percent_long = 2.7 × (median ATR%(14) of market ÷ median ATR%(14) of gold)

One deterministic number per market, computed once, no search. This is the
whole point of the test — the claim is that the logic works when the stop is
expressed in the instrument's own volatility units rather than in gold's.

Position sizing is volatility-scaled too, so a unit position carries comparable
risk across instruments. The `ceil(equity/5000)` rule is calibrated to gold's
price level and made silver's and EURUSD's returns meaningless.

## Primary metric

Percentile against random entry at matched exposure and holding periods
(`null_test.py`). It is the only measure that is sizing-independent and
separates timing skill from market drift.

## Success criterion (fixed in advance)

Counting **only the seven never-tested markets**, at ≥80th percentile:

* **≥ 6 of 7** → the edge is a market behaviour. Worth building a portfolio on.
* **4–5 of 7** → weak and inconsistent. Not tradeable on its own.
* **≤ 3 of 7** → **reject.** Gold and EURUSD were luck; stop here.

Secondary, reported but not decisive: whether a vol-scaled equal-weight
portfolio of the markets that clear beats an equal-weight buy-and-hold of the
same markets, and what its drawdown looks like.

## Anticipated failure modes

* **Shorter history on CFDs.** Index and commodity CFDs start around 2010–2013,
  so those markets get ~13 years rather than 20. Fewer trades, noisier
  percentiles. Trade counts are reported; any market with under 40 trades is
  flagged as inconclusive rather than counted as a pass or fail.
* **Correlation.** GBPUSD, EURUSD and AUDUSD share a USD leg; the two indices
  are correlated. Seven markets are not seven independent tests. The
  cross-market correlation of strategy returns will be measured and reported,
  and the effective number of independent tests is lower than seven.
* **Equity indices have strong positive drift**, so a long-only strategy will
  look good there regardless. This is exactly what the random-entry null exists
  to control for — the comparison is against random entry *in the same market*,
  not against zero.
* **The vol-scaling could itself be the overfit.** It was derived from three
  markets. If results are mediocre across the seven, the honest reading is that
  the scaling was fitted to gold/EURUSD, not that the markets are unsuitable.
