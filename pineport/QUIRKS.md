# What the Pine script actually does

Findings from translating `RSI Boll Squeeze Strategy` line by line. Each item
says what the code appears to do, what it does, and whether it changes results.

Everything here is **reproduced faithfully in the port**. Nothing is silently
"fixed" — the repairs live behind flags in `Params` so each can be switched on
individually and measured (`python variants.py`).

## Verification status: PASSED

Checked against a TradingView chart export of `OANDA:XAUUSD, 60`
(2026-05-13 17:00 → 2026-08-04 10:00, 1,341 bars), running the port on
TradingView's own bars:

| check | result |
|---|---|
| in-position state, bar by bar (`Chars` = `strategy.opentrades`) | **1341 / 1341 bars, 100%** |
| trades | 3 vs 3, same entry and exit bars |
| `Target Long` | max difference **0.00** |
| `profitLockinUp` (P5) | max difference **0.00** |
| `SL Long` (`price_stop_long`) | max difference **9.1e-13** |
| Bollinger basis / lower / upper | max difference **5e-08** (float noise) |
| `SL Short`, `Target Short` | empty in both — the short side never fired |

Independently cross-checked against the 231-trade history export. The three
trades in the chart window match on entry price, exit price, bar duration and
per-unit P&L to four decimal places:

| | TradingView | port |
|---|---|---|
| #229 | 4520.085 → 4451.411, 61 bars, −68.6733/unit | 4520.085 → 4451.4118, 61 bars, −68.6732 |
| #230 | 4458.83 → 4413.474, 89 bars, −45.3567/unit | 4458.830 → 4413.4745, 89 bars, −45.3555 |
| #231 | 4084.72 → 3974.86, 82 bars, −109.8600/unit | 4084.720 → 3974.8607, 82 bars, −109.8593 |

(The trade list is stamped in the chart's display timezone, one hour ahead of
the chart-data export. Position sizes differ — 3 vs 1 — only because
TradingView's equity had compounded to ~$11k over twenty years while the port
started fresh at $4,000; the sizing rule `ceil(equity/5000)` matches.)

Reproduce with:

```bash
python verify.py --tv-chart "OANDA_XAUUSD, 60.csv" --point-value 1 \
                 --capital 4000 --assume-squeeze-on
python trade_history.py --trades "Gold_1hr_New_....csv" --sweep --ml-check
```

The `--assume-squeeze-on` flag is needed because the export (1,341 bars) is
shorter than the script's own 942-bar `lengthKCS` lookback; see QUIRK 2 for why
that substitution is signal-neutral. Without it the port correctly reproduces
only the trade that begins after bar 942.

Numbers below quoted as "measured on synthetic bars" come from a generated
series, because the sandbox this was built in has no market data. Numbers quoted
against `OANDA:XAUUSD` come from your export. The *structural* findings — a
filter that can never be false, two conditions that are the same test — are
properties of the code and hold on any data.

---

## 1. `mult` is declared and never used

```pine
mult = input(2.0, title="BB MultFactor")
...
devL = multKC * ta.stdev(source1, lengthL)   // multKC, not mult
```

Both the "Bollinger" and the Keltner side of the squeeze use `multKC` (2.5).
The **"BB MultFactor" input on the settings panel does nothing**. If you have
ever optimised over it in TradingView, those runs were all identical.

*Effect:* none on results, but it means one of your optimiser dimensions was
inert.

---

## 2. The Keltner channel is built from price, not from range — the squeeze can never fire

```pine
range1 = useTrueRange ? high : (high - low)
```

The true-range branch returns the raw **high**, where a Keltner channel needs
`ta.tr()`. On the test sample the median true range was 5.05 points and the
median high was 2,638 — a factor of 520. So:

```
upperKC = vwma(close,76)  + vwma(high,76)  * 2.5   ≈  3.5 × price
lowerKC = vwma(close,942) - vwma(high,942) * 2.5   ≈ -1.5 × price
```

With gold near 2,600 that puts the channel at roughly **+9,200 / −4,000**, while
the Bollinger band sits within a few points of price. The squeeze test

```pine
sqzOn = (lowerBB > lowerKC) and (upperBB < upperKC)
```

is therefore **true on every bar** once the 942-bar warm-up has passed. Measured:
100% of warmed-up bars.

`sqzUp` and `sqzDown` collapse to their linreg conditions alone:

- `sqzUp = valL > 0` — close to a coin flip, true on 59.8% of warmed-up bars.
- `sqzDown = valS < 960` — `valS` is a linear regression of a **de-meaned**
  series, so it oscillates around zero and never approaches 960. Measured range
  was −103.5 to +156.1. **`sqzDown` is true on 100% of warmed-up bars.**

*Effect:* the **Keltner/Bollinger comparison** is dead — it costs a 942-bar
lookback (about 40 days of any sample) and rejects nothing.

**Correction to an earlier draft of this note:** the squeeze *block* is not
entirely inert. `sqzOn` is, but the `valL > 0` test sitting beside it is a live
filter on the long side, and it earns its place. Verification against your
OANDA:XAUUSD export caught a signal on 2026-07-27 14:00 where every other
condition passed and `valL = −45.79` — TradingView correctly declined that
trade. So: delete `sqzOn`, keep `valL`. The short-side `valS < 960` genuinely
does nothing.

*Repair flag:* `fix_keltner_range=True`.

*Warm-up shortcut:* `assume_squeeze_on=True` substitutes `sqzOn = True` (its
provably-always-true warm value) while keeping the `valL`/`valS` tests. This
drops the long side's warm-up from 942 bars to 76 without changing a single
signal — `test_port.py` asserts that equivalence. It is what makes a short
TradingView chart export verifiable at all.

---

## 3. Two of the three long triggers are the same condition

```pine
vrsiL = ta.rsi(price, 1)                        // RSIlengthL = 1
... ta.crossover(vrsiL, 29) ...                 // RSIoverSold = 29

LSMAL = ta.sma(price, 2)                        // LSMAlengthL = 2
LSMAS = ta.sma(price, 1)                        // LSMAlengthS = 1
... ta.crossover(LSMAS, LSMAL) ...
```

RSI at length 1 has smoothing constant α = 1, so it is not an oscillator at all:
it is exactly **100 on an up bar and 0 on a down bar**. Crossing 29 upward
therefore means "this bar closed up and the previous one didn't".

`sma(close,1)` is `close`; `sma(close,2)` is `(close + close[1])/2`. `close`
crossing above that means `close > close[1]` and `close[1] <= close[2]` —
**the identical statement**.

The port verifies this empirically: over 8,000 bars both conditions fired on the
same 1,986 bars, with zero disagreement.

*Effect:* the long entry has two real conditions, not three. The `RSI Period
LengthL` and `Over Sold` inputs are near-decorative — any `RSIoverSold` between
0 and 100 gives the same signal.

*Repair flag:* `drop_duplicate_long_trigger=True`.

---

## 4. The short side is structurally dead

The short entry requires all three at once:

```pine
ta.crossunder(vrsiS, 20)          // RSI(5) crossing below 20 -> deeply oversold
ta.crossunder(sourceS, BBupper)   // price falling away from the UPPER band
ta.crossunder(SSMAS, SSMAL)       // sma(2) crossing below sma(26)
```

The first two are close to mutually exclusive: RSI(5) below 20 means price has
collapsed over the last five bars, while touching the upper Bollinger band means
it is extended to the upside. Over 8,000 synthetic bars they **never co-occurred
once** (RSI trigger fired 190 times, band trigger 198 times, overlap: 0).

**Correction, from the 20-year trade history.** "Structurally dead" was too
strong — I inferred it from 8,000 synthetic bars and an 11-week chart export,
and the full record disproves it. The short side **does** fire: **20 short
trades between 2006 and 2026**, about one a year. They net +163 USD, which is
2.3% of total profit, at a 30% win rate.

So the accurate statement is: the short trigger is not impossible, it is
*vanishingly rare*. One trade a year is too few to tune, too few to model, and
too few to matter. The eleven short-side inputs (`markDown`, `lockProfitDown`,
`rangeS`, and the rest) are still carried through every optimisation for a leg
that contributes 2% of the result.

Note also the short exits: of 20 shorts, only **6** closed on their own stop.
The other **14** were closed by a long entry reversing the position — so most
shorts are ended by the long side, not by their own exit logic.

Note also that the short leg carries **no macro filter, no ADX filter and no
volatility gate** — the gating is entirely asymmetric — but that is moot while
the trigger never fires.

*Effect:* this is a long-only strategy. All the short-side stop machinery
(`markDown`, `lockProfitDown`, `rangeS`, the whole short ladder) is unreachable
code. That also explains why those inputs are set to 10,000: nothing ever tested
them.

---

## 5. The long trailing stop reads a variable that is always zero

This is the one genuine bug, as opposed to a dead filter.

```pine
price_stop_long = 0.0                                    // re-initialised EVERY bar
...
if close > targetvalue_long_1
    stopvalue_long_1 := price_stop_long + ((close - price_stop_long) * gapUp)
```

Pine re-executes the whole script body on each bar, so at the moment that line
runs, `price_stop_long` has just been reset to `0.0` and has not yet been
assigned. The expression collapses to:

```
stopvalue_long_1 := 0 + (close - 0) * 0.995 = close * 0.995
```

The intent was clearly a ratchet from the *previous* stop — and the short-side
mirror of the same block gets it right, using `price_stop_short[1]`:

```pine
stopvalue_short_1 := price_stop_short[1] - ((price_stop_short[1] - close) * gapDown)
```

So the two directions do different things from identical-looking code.

*Effect:* smaller than you would expect, because `price_stop_long` is finally
assigned via `math.max(..., price_stop_long[1], ...)`, which restores a ratchet.
The bug means the *candidate* stop is 0.5% below the close rather than a
proportional step up from the old stop. Measured difference on the test sample:
about 0.01% of return. Worth fixing for clarity, not for performance.

*Repair flag:* `fix_long_stop_ratchet=True`.

---

## 6. The take-profit is displaced so far it can never fill

```pine
strategy.exit("long exit",  limit = targetvalue_long_1 + 10000, stop = price_stop_long, ...)
strategy.exit("short exit", limit = targetvalue_short_1 - 10000, stop = price_stop_short, ...)
```

With gold near 2,600, a long limit around 13,000 and a short limit around
−7,400 are unreachable. **Every exit in this strategy is a stop exit.** The port
confirms it: `exit_reason` is never `limit` in any run.

Meanwhile the targets themselves feed the stop logic, so they are not inert —
`targetvalue_long_1 = entry_close × (1 + 6.7/100 × 3) = entry × 1.201`, a 20%
move that on hourly gold takes months, if it happens at all.

*Effect:* the risk/reward inputs (`Limit % Stop Multiplier`, `Risk Reward Ratio`)
shape the trailing stop but never produce a take-profit fill.

*Repair flag:* `enable_take_profit=True`.

**This one turns out to be a feature, not a bug.** The excursion columns in the
trade history make it testable: the average trade peaks at +3.63% and closes at
+0.90%, giving back 75% of its best gain, and 63 of 231 trades went more than 1%
into profit and still lost. That looks damning for a disabled take-profit.

It isn't. Re-simulating the whole 231-trade population with a take-profit at
every level from 1% to 10% (`trade_history.py --sweep`):

| exit rule | return | profit factor |
|---|---|---|
| as-is (stop only) | **181%** | **2.39** |
| take-profit 2% | 34% | 1.35 |
| take-profit 5% | 99% | 1.94 |
| take-profit 7.5% | 145% | 2.09 |
| take-profit 10% | 132% | 2.12 |

Every level loses to the baseline, and that conclusion is robust: the
counterfactual is biased *in favour* of the variants (see QUIRK 10), so a
variant that still loses really does lose. Capping winners destroys this
strategy, because a handful of very large trades carry all of it.

**Do not "fix" this one.** Leave `enable_take_profit=False`.

---

## 7. `stop value Long` / `stop value Short` are not stops

```pine
stopvalue_long_1 = input.float(0, "stop value Long")
...
stopvalue_long_1 := <something>       // reassigned inside the position block
```

Because they are plain (non-`var`) declarations, they reset to the input default
on **every bar** rather than persisting. They are per-bar seed values, not state.
Setting "stop value Short" to 1,000,000 is what keeps it out of the way of the
`math.min()` that follows; it is a sentinel, not a stop level.

*Effect:* none, once you know. Flagged because the names invite the opposite
reading.

---

## 8. `markUp`/`rangeL` ladder levels are absolute points, not percentages

```pine
if ta.crossover(close, entry + markUp)              // markUp = 190
    stopvalue_long_1 := entry + lockProfitUp        // lockProfitUp = 170
... + (markUp + rangeL*1) ... rangeL = 750
```

The ladder locks in +170 once price is +190 above entry, then +920 at +940, then
+1,670 at +1,690, and so on. These are **dollars of gold**, so they are tied to
the price level at the time you tuned them. The +190 rung is reachable; the
+940 rung is a 36% move; the rest are unreachable. On the short side `markDown`
= 10,000 puts the first rung below zero.

*Effect:* effectively one working ladder rung on the long side, none on the
short side. If gold moves materially, the tuning goes stale — consider ATR
multiples instead of fixed points.

---

## 9. Position sizing is a coarse step function

```pine
cashRisk = (strategy.equity * 1) / 100
long_position_size = math.ceil((cashRisk / (50 * syminfo.pointvalue) * 1)) / 1
```

With `pointvalue = 1`, this is `ceil(equity / 5000)`. At the 4,000 starting
capital it is `ceil(0.8) = 1`, and it stays at 1 until equity passes 5,000, then
jumps to 2. The name says "1% risk", but the formula never references the stop
distance, so **actual risk per trade varies with volatility** and the "50" is an
unexplained constant.

Also worth checking: `syminfo.pointvalue` differs between symbols. On
`OANDA:XAUUSD` it is 1; on COMEX `GC1!` it is 100. The same script gives
100× different position sizes on the two charts. The port exposes this as
`--point-value` rather than guessing.

---

## 10. The bigger structural point: ten trades are the whole strategy

The full trade history — 231 trades, September 2006 to July 2026 — is the only
honest view of this strategy, and it is dominated by a handful of trades.

| | 2006-09 → 2026-07 (19.8 years) |
|---|---|
| trades | 231 (211 long, 20 short) |
| trade frequency | 11.6 per year |
| final equity | 11,243 from 4,000 |
| total return | **+181%** |
| CAGR | **5.35%** |
| gold buy & hold, same window | **+575%**, CAGR **10.11%** |
| win rate | 44.2% |
| profit factor | 2.39 |
| approx. exposure | 41% of market hours |
| max drawdown (trade-close basis) | −8.52% |

Two things to sit with.

**First: profit concentration.**

| | share of net profit |
|---|---|
| top 1 trade | 28.1% |
| top 3 trades | 56.6% |
| top 5 trades | 70.7% |
| **top 10 trades** | **100.0%** |

The other 221 trades net to **zero**. All ten of the top trades are long, and
all ten are from 2024 onward. Remove the best three and twenty years of trading
is roughly flat.

**The effective sample size is about 10, not 231.** Every ratio above — the
profit factor, the CAGR, the exit counterfactuals — is a restatement of what
those ten trades did during gold's 2024–2026 run.

**Second: dollars versus percentages.**

| | trades | USD | share | sum of % returns | mean % | avg entry |
|---|---|---|---|---|---|---|
| 2006–2022 | 187 | 1,075 | 15% | 104.3 | 0.56% | $1,272 |
| 2023–2026 | 44 | 6,168 | 85% | 102.6 | 2.33% | $3,073 |

In dollars the recent period looks like the entire story, but percentage
returns split about evenly — so part of the skew is just gold going from $600
to $4,700. Not all of it, though: mean return per trade improved 4.2×, which
price level alone does not explain.

The likely reason is QUIRK 8. The ladder inputs (`markUp` 190, `rangeL` 750,
`lockProfitUp` 170) are absolute dollar amounts, and at gold $600 in 2006 a +190
rung was a 32% move — unreachable. Those numbers only make sense at recent
prices. Which means **2006–2022 is effectively an out-of-sample test of
parameters chosen for 2023–2026**, and over that out-of-sample stretch the
strategy returned ~104% cumulative simple while gold itself rose ~196%.

Against buy-and-hold, the fair summary is: **about half the CAGR, at
substantially lower exposure (41%) and, on the visible measure, lower
drawdown.** That is not nothing — it is a defensible risk profile. But the
drawdown figure is measured at trade closes only and ignores open-position
swings, so the true number is worse; the average trade's adverse excursion
alone is 1.23%. Computing it properly needs bar data.

---

## What this means for the ML plan

You asked for three ML treatments — signal filter, parameter optimiser, and
full rule replacement — benchmarked against each other. Now that the port is
verified, here is where each one actually stands.

231 trades sounds like a workable sample. It isn't, because ten of them are the
result. That single fact governs all three variants:

- **Signal filter.** The job would be "learn to keep the winners and drop the
  losers". But the winners are ten trades, all long, all from one bull run. Any
  model that improves the backtest will have learned to recognise 2024–2026 gold,
  which is not a transferable skill. This is the variant most likely to produce
  an impressive number and lose money live.
- **Parameter optimisation.** Mechanically easy, highest risk. Roughly 40
  tunable inputs against ~10 effective observations. Optuna will return an
  excellent Sharpe and it will be meaningless — the same failure mode as the
  ~900% / Sharpe 11 result from the overlapping-trades bug. A number that looks
  great because the measurement is broken, not because the edge is.
- **Full rule replacement.** Still the only variant that isn't structurally
  blocked, because it doesn't inherit the entry scarcity. But be honest that it
  is a new strategy reusing these indicators, not a port of this one.

There is also a prior question worth asking before any of it: **the strategy
returns half of buy-and-hold's CAGR.** If the goal is exposure-adjusted risk
control, it has a case — 41% exposure, lower visible drawdown. If the goal is
beating buy-and-hold on gold, twenty years of history says it doesn't, and no
filter layered on ten profitable trades will change that.

In rough order of expected value:

1. **Make the ladder scale-invariant.** Convert `markUp`, `lockProfitUp`,
   `rangeL` from absolute dollars to ATR multiples or percentages. This is the
   one change that would make the 2006–2022 record a meaningful test rather than
   a test of parameters that could not fire at 2006 prices. Everything else
   downstream depends on having a sample you believe.
2. **Delete `sqzOn`, keep `valL`.** Reclaims the 942-bar warm-up at zero signal
   cost — 40 days of usable data returned on any sample.
3. **Decide about the short side.** 20 trades in 20 years for 2.3% of profit,
   and 14 of those 20 were closed by a long reversal rather than their own exit.
   Either rewrite the trigger so it can fire, or delete it and stop carrying
   eleven dead inputs through every optimisation.
4. **Do not add a take-profit.** Tested above; every level loses. The winners
   are the strategy.
5. **Get bar data if you possibly can.** Not for more trades — you have 231 —
   but because without it you cannot compute a true drawdown, cannot test
   whether an exit change survives path-ordering, and cannot build any entry
   feature more informative than the hour of the day.
6. *Then*, if the sample still looks worth modelling, fit the ML layer with
   walk-forward splits and the non-overlapping trade logic you already fixed in
   the other codebase.

### A note on data sources

`XAUUSD=X` from yfinance reports **zero volume on every bar**. Every band in
this strategy is a `ta.vwma`, so that feed makes every signal NaN and produces
zero trades — a result that looks like "the strategy took no trades" rather than
like a broken input. `data.py` detects this and warns.

More generally: your chart is OANDA spot, and yfinance has no matching feed.
`GC=F` is COMEX futures — different instrument, sessions, gaps, and a
`pointvalue` of 100 rather than 1. **Keep verification and research on the same
bars.** The TradingView export is the source of truth; use it, or a broker
export from the same venue.
