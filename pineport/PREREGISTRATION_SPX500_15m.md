# Pre-registration — SPX500 15m, state triggers, staged training

**Registered:** 2026-09-21, before the run.
**Supersedes:** the unregistered SPX500 run of 2026-09-20, which is void — it
inherited gold's FRED real-yield filter from its base config and fitted
parameters around a macro variable belonging to a different instrument.

---

## 1. Hypothesis

The RSI / Bollinger / squeeze conjunction, expressed as **state** tests
(`RSI > level`, `close < band`) rather than crossovers, and fitted on SPX500
15m bars with every instrument-specific filter switched off, produces
out-of-sample performance that survives both a crash regime and a bull regime.

**Why state rather than crossover, for this instrument.** On gold the switch
collapsed the strategy: a crossover is rare, a state is common, so the
four-way conjunction stopped being selective. On SPX500 the same switch at
fixed parameters *halved* the trade count (50 → 23) and improved Sharpe
(0.74 → 0.88). That is the opposite direction and is the reason this is worth
a run. It is an observation on untrained parameters, not a result.

---

## 2. Data and windows

| window | role | note |
|---|---|---|
| 2005-01 .. 2008-12 | **holdout (pre)** | contains the 2008 crash |
| 2009-01 .. 2018-10 | fit | searched |
| 2018-10 .. 2022-12 | validation | accepts/rejects stages; never searched |
| 2023-01 .. 2026-08 | **holdout (post)** | untouched until §5 |

`spx500usd_oanda_m15.csv`, 499,775 bars, flat bars below 0.34% in every era.

The pre-holdout is the point of this design. Fifteen families in `pineport/`
and everything in the gold work were tested on regimes that never included an
equity crash. 2005–2008 is the one window that can break an index strategy for
the right reason.

---

## 3. Method

- `train_staged.py`, six stages in order: sma, rsi, squeeze, bands, stops, ladder
- base: `configs/spx500_clean_base.json` from `make_base.py` — all filters off,
  stops carried from gold as ATR multiples (24.6x / 26.2x / 50.0x / 43.9x),
  not as copied percentages
- 4 seeds x 200 samples per stage; a stage is **accepted only if a majority of
  seeds improve the validation metric**
- objective: Calmar
- slippage: **0.25 points per fill** — measured, see §6

Filters (ADX, volatility, macro) stay **off**. They may be tested afterwards as
a separate registered step; they are not part of this hypothesis.

---

## 4. Kill conditions — fixed before the run

The strategy **fails** if any of these is true:

1. **Sharpe < 0.8 on either holdout window**, scored at the measured spread.
2. **Break-even spread below the measured SPX500 spread.** Priced in §6; if the
   edge does not survive what it costs to trade, it is not an edge.
3. **Fewer than 30 trades in either holdout window.** Below that a Sharpe is
   not a measurement. (2023–26 produced 17 trades in the void run — this
   condition would have fired.)
4. **Max drawdown worse than buy-and-hold on the 2005–2008 window.** An index
   strategy that does not protect in a crash has no reason to exist, given
   buy-and-hold is the free alternative.
5. **The 2005–2008 result does not survive a crash-realistic spread.** Because
   that era's spread is backfilled (§6), the window is scored at 0.25 AND at
   1.00 per fill. If it passes only at 0.25 it has passed on a cost that was
   not available in 2008, and condition 1 is treated as failed there.

It **passes** only if all five are cleared on **both** holdout windows.

Anticipated failure, recorded now: condition 1 on the 2005–2008 window. The
void run returned Sharpe 0.24 there. It cleared condition 4 comfortably
(−7.4% against buy-and-hold's −52.8%), which is why condition 4 is separate —
"failed on Sharpe" and "was useless in the crash" are different claims and
last time only the first was true.

---

## 5. Holdout procedure

Both holdout windows are scored **once**, after all six stages have completed
and the config is frozen. No parameter is adjusted afterwards. If the result
fails, the family closes — it is not reopened with a filter, a seventh stage
or a different objective (standing rule 2).

---

## 6. Costs — MEASURED 2026-09-21

OANDA daily bid vs ask, `spx_bid_d.csv` / `spx_ask_d.csv`, 5,665 candles:

| period | median spread | bps |
|---|---|---|
| last 5 years | **0.50 pts** | **0.90** |
| 2024-2026 | 0.50 pts | 0.70-0.90 |
| 2012-2013 | 0.70-1.50 pts | 5.2-8.9 |
| 2005-2011 | **0.00** | — backfilled, bid = ask |

**`--slippage 0.25`** — the half-spread, charged per fill, so a round trip
costs the measured 0.50. The earlier placeholder of 0.5 was the round trip and
would have charged double.

**The 2005-2011 spread is not measurable.** OANDA's quoted history begins
around 2012; before that bid equals ask, exactly as on NAS100. Prices for that
era look sound — flat bars 0.00%, consistent bar counts — so the crash window
stays usable, but charging it 0.25 assumes a spread that did not exist. Real
2008 spreads, particularly intraday during the crash, were certainly wider.

Standing rule 6: costs are the usual killer, four for four in `fastbot`.

---

## 7. Known limitations, recorded in advance

- **Reproducibility is untested here.** The gold version of this strategy
  reproduced only 46.7% of its trades across two data vendors. No second feed
  for SPX500 has been fetched, so this run cannot say whether its trades are
  vendor artefacts. If it passes §4, that test comes next and may still kill it.
- **Trade counts will be low.** The gold analogue took ~10 trades a year.
  Condition 3 exists because of it.
- **The stop geometry is borrowed** from gold via ATR multiples. Defensible,
  but it is an assumption that gold's risk geometry suits an index.
