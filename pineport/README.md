# RSI Boll Squeeze — Pine v5 → Python port

A bar-for-bar translation of the `RSI Boll Squeeze Strategy` ("Gold 1hr New")
TradingView script, plus the harness to verify it against TradingView before
trusting it.

The port is **faithful, not tidied**. Several constructs in the original do not
do what their names suggest; those are reproduced exactly and documented in
[`QUIRKS.md`](QUIRKS.md), with repairs available behind flags so each can be
measured on its own.

> **Read `QUIRKS.md` before doing anything else with this.** Two of the three
> long entry conditions are the same test, the squeeze filter can never be
> false, and the short side never fires. Those findings change what the
> optimisation and ML work should target.

---

## Install

**macOS — run this once:**

```bash
bash setup_mac.sh
```

It creates a virtual environment in `.venv`, installs everything, and runs the
test suites to confirm it worked.

Why a venv rather than `pip install pandas`: recent macOS Pythons (both Apple's
`/usr/bin/python3` and Homebrew's) ship marked *externally managed* under PEP
668, and pip refuses to install into them —

```
error: externally-managed-environment
× This environment is externally managed
```

The common workaround is `--break-system-packages`, which does exactly what it
says. A venv is the same amount of typing, needs no admin rights, touches
nothing outside this folder, and is deleted by removing one directory.

**Anywhere else**, or to diagnose a broken setup:

```bash
python3 check_env.py
```

That prints which interpreter you're on, what's missing, and the exact install
command — using *that* interpreter's own pip, so the two can't disagree. It's
stdlib-only, so it runs even when nothing is installed.

Python 3.9+. `pyarrow` is optional (faster data cache) and setup skips it
silently if no wheel is available.

**Two Pythons, one gotcha.** The interpreter in your Terminal and the one
reticulate binds to in RStudio are frequently different — that's the usual cause
of "but I definitely installed pandas". `pineport.R` binds to `.venv`
automatically if `setup_mac.sh` created one; otherwise `pineport_env()` shows
which one is live.

## Getting data

```bash
python fetch_data.py --ticker GC=F --interval 1h --years 2   # the hourly max
python fetch_data.py --ticker GC=F --interval 1d --years 6   # full span, daily
python fetch_data.py --alternatives                          # deeper sources
```

**Yahoo holds 730 days of hourly data and no more.** Six years at 1h is not
available from Yahoo or Google at any request size — it's a limit on what
exists, so chunking doesn't help. Google has no historical API at all
(`GOOGLEFINANCE()` is Sheets-only, no intraday history). `fetch_data.py` clamps
the request, says so, and validates what arrives.

Use `GC=F`, not `XAUUSD=X` — the latter reports zero volume on every bar, and
since every band in this strategy is a `ta.vwma()`, that turns every signal into
NaN and produces a zero-trade backtest that looks like a result.

### Deep history — Dukascopy

For the full 2006–2026 span at hourly, use `dukascopy.py`. Free, no account.

```bash
python dukascopy.py --self-test                    # offline, 27 checks
python dukascopy.py --probe --year 2024 --month 6  # ALWAYS do this first
python dukascopy.py --start 2006 --out xauusd_1h.csv
```

240 requests for twenty years, roughly two minutes at the default pacing. Raw
`.bi5` files are cached, so a re-run or an interrupted pull resumes rather than
re-downloading.

Three things that make this format easy to get wrong, all handled and all
unit-tested:

- **The month in the URL is zero-indexed.** January is `00`, December is `11`.
  Get it wrong and you silently receive the wrong month rather than an error.
- **The binary field order is open, close, low, high** — not OHLC. Reading it as
  OHLC produces bars that look plausible and are wrong.
- **Non-trading hours are padded, not omitted.** Dukascopy publish a bar for
  every calendar hour; outside market hours they repeat the last price at zero
  volume. A raw month is 24 × days bars rather than the ~24 × 5/7 × days a 24/5
  market trades. That padding is dropped by default (`--keep-flat` to retain
  it), because it would otherwise turn every `ta.vwma()` window into 0/0, zero
  out ATR and `stdev`, make `ta.rsi(close, 1)` undefined, and — worst — shift
  every bar index away from OANDA's, which omits closed hours. This strategy
  indexes into history directly (`close[since_entry_long]`, a 942-bar lookback,
  a 4H resample), so a misaligned index yields a backtest that runs cleanly and
  means nothing.

Expect roughly 470 bars per month after filtering, so ~113,000 for 2006–2026.

Dukascopy is a different venue from OANDA, so this will **not** reproduce your
TradingView trade list exactly. Keep the OANDA chart export as the verification
reference and use Dukascopy for research — different jobs, and it's fine for
them to use different data.

## Run

```bash
# faithful backtest
python run.py backtest --ticker GC=F --period 730d --interval 1h

# why signals do and don't fire: gate pass rates, dead filters, redundancy
python run.py diagnose --ticker GC=F --period 730d

# change one thing at a time and see what it costs
python variants.py --ticker GC=F --period 730d

# check the port against a TradingView "List of Trades" CSV export
python run.py compare --tv-trades tv_export.csv

# analyse the full trade history (goes back further than any chart export)
python trade_history.py --trades "Gold_1hr_New_....csv" --sweep --ml-check

# does the entry rule beat random entry at matched exposure?
python null_test.py --csv xauusd_1h.csv --keltner-fix

# walk-forward parameter search. Long runs are resumable fold by fold:
python optimise.py sensitivity --csv xauusd_1h.csv
python optimise.py walkforward --csv xauusd_1h.csv --list-folds
python optimise.py walkforward --csv xauusd_1h.csv --fold 1 --trials 30
python optimise.py walkforward --csv xauusd_1h.csv --score-fold 1
python optimise.py walkforward --csv xauusd_1h.csv --summarise

# tests (no network needed)
python test_port.py
```

Useful flags: `--capital`, `--point-value`, `--commission-pct`, `--slippage`,
`--csv path.csv` to use your own OHLCV instead of yfinance.

## Files

| file | what it is |
|---|---|
| `pine_ta.py` | Pine `ta.*` equivalents — `rma`, `rsi`, `vwma`, `dmi`, `linreg`, … |
| `data.py` | yfinance loading, caching, and `request.security` with no lookahead |
| `broker.py` | TradingView's execution model: next-bar fills, `pyramiding=0`, stops |
| `strategy.py` | the ported strategy — `Params`, indicators, and the bar loop |
| `metrics.py` | Sharpe/Sortino/drawdown/profit factor, computed from the equity curve |
| `variants.py` | one-switch-at-a-time ablation table |
| `verify.py` | **bar-by-bar diff against a TradingView chart export** |
| `trade_history.py` | **20-year trade-list analysis, exit counterfactuals** |
| `null_test.py` | random-entry null — is the entry signal adding information? |
| `optimise.py` | **walk-forward parameter search with overfitting controls** |
| `fetch_data.py` | Yahoo downloader with validation; honest about the 730-day cap |
| `dukascopy.py` | **free XAUUSD hourly back to ~2003** — the deep-history source |
| `pineport.R` | reticulate wrapper, returns R data frames |
| `run.py` | CLI: `backtest`, `diagnose`, `compare` |
| `test_port.py` | 50-odd assertions covering indicators, execution and lookahead |
| `synth.py` | deterministic synthetic bars, so tests run without a data feed |
| `QUIRKS.md` | **what the original script actually does** |
| `FINDINGS.md` | 20-year results, out-of-sample tests, optimisation verdict |
| `TUNING.md` | **which parameters are worth tuning, and which are inert** |

---

## What "faithful" means, and where it can't be exact

Reproduced deliberately:

- **Execution latency.** Signals are evaluated at bar close; market orders fill
  at the *next* bar's open. Getting this wrong is the most common way a Python
  port ends up looking better than the TradingView chart.
- **`pyramiding = 0`.** A same-direction entry while in a position is rejected.
  On this strategy that rejects 19 of every 24 signals — it is doing more work
  than any of the filters.
- **No stop on the entry bar.** The script only learns it has a position at the
  close of the fill bar, so `strategy.exit` first arms on the bar after.
- **Wilder smoothing seeded with an SMA.** Pine's `ta.rma` seeds from
  `sma(src, n)`. Most Python TA libraries seed from the first observation, which
  leaves a persistent offset in RSI, ATR and ADX.
- **Population standard deviation.** Pine's `ta.stdev` uses ddof=0.
- **`request.security` with `lookahead_off`.** While a 4H bar is forming, the
  value returned is the *previous closed* 4H bar's. `test_port.py` asserts that
  no unfinished 4H close ever reaches a 1H bar.

What cannot match exactly, and why:

- **Different bars.** yfinance `GC=F` (COMEX futures) is a different instrument
  from `OANDA:XAUUSD` (spot CFD) — different sessions, different closes,
  different gaps. If your TradingView chart is spot and your Python run is
  futures, the trade lists will diverge no matter how correct the logic is.
- **`syminfo.pointvalue`.** 1 on spot XAUUSD, 100 on COMEX gold. Same script,
  100× the position size. Set `--point-value` to match your chart.
- **Intrabar path.** OHLC bars don't record whether the high or the low came
  first. This engine only ever has one live stop, so the ambiguity never has to
  be resolved — but a strategy with both a stop and a reachable target inside
  one bar would need tick data to settle.
- **Zero-volume feeds.** Every band here is a `ta.vwma`. yfinance `XAUUSD=X`
  reports zero volume on every bar, which would make every signal NaN.
  `data.py` detects this and warns loudly rather than returning an empty trade
  list that looks like a strategy result.

Expect **same logic and a near-identical trade list**, not identical P&L to the
cent.

---

## Verifying against TradingView

**Run the port on TradingView's own exported bars.** Your chart is
`OANDA:XAUUSD` — a spot CFD. yfinance has no matching feed (`GC=F` is COMEX
futures; `XAUUSD=X` reports zero volume, which breaks every VWMA here). If you
verify across two different feeds, every difference is ambiguous: data or logic?
Feeding TradingView's bars back into the port removes the data variable, so
anything left over is logic and can actually be fixed.

Once it's verified there, point it at whatever feed you like for research.
Verification and research are separate jobs.

### Getting the exports

**Chart data** — the valuable one, it carries every plotted series:
chart toolbar → the **⋯** menu (top right of the chart) → *Export chart data…* →
tick **Include plotted values** → Export.

**List of Trades**: Strategy Tester panel → *List of Trades* tab → the download
icon → CSV.

Check the strategy's **Properties** tab first and note: initial capital (4000),
order size, pyramiding (0), commission, slippage, and the chart's date range.

### Running it

```bash
python verify.py --tv-chart chart_export.csv --tv-trades list_of_trades.csv \
                 --capital 4000 --point-value 1
```

It reports, per plotted series, how many bars matched, the largest absolute and
relative difference, and — the useful bit — **the first bar where the port and
TradingView disagree**, with surrounding context:

```
First divergence: bb_lower at bar 2500 (2024-04-14 04:00:00+00:00)
                                close  tradingview      python     diff
2024-04-14 03:00:00+00:00 2,372.64339  2,361.60471 2,361.60471 -0.00000
2024-04-14 04:00:00+00:00 2,374.10609  2,363.12844 2,362.62844  0.50000
```

Work from the earliest divergence. A single early difference cascades through
everything after it, so the first one is usually the only real bug.

Two columns worth reading carefully:

- **`py_only`** — bars where the port holds a position and TradingView doesn't.
  This is the fastest route to a trade-list discrepancy.
- **`tv_only`** — the reverse. Often an entry the port declined.

The script titles *fifteen* separate plots "SL Long", so the exporter emits
duplicate column names. `verify.py` un-mangles them by export order: the first
"SL Long" is P1 (`price_stop_long`), the second is P5, the third is P6.

If entry counts match but P&L doesn't, check point value and commission before
suspecting the logic.

---

## RStudio / reticulate

`pineport.R` wraps the Python side and returns R data frames.

```r
source("pineport.R")
pineport_env()                                       # which interpreter is bound?
res <- pineport_backtest(csv = "chart_export.csv", point_value = 1)
head(res$trades)
plot(res$equity$time, res$equity$equity, type = "l")

pineport_variants(csv = "chart_export.csv")          # ablation table
pineport_verify("chart_export.csv", "list_of_trades.csv")
```

Run `pineport_env()` first, every time you hit a missing-package error. The
common Mac failure is silent: **RStudio binds to a different Python than your
Terminal**, so something you definitely installed isn't there. That's the same
mechanism behind the Apple Silicon `deep-forest` source build being visible in
one interpreter and not the other. Install into the bound interpreter with
`reticulate::py_install(..., pip = TRUE)`, not Terminal pip.

To force a specific interpreter, call it before any other Python touch — once
reticulate initialises, the binding is fixed until you restart R
(*Session → Restart R*):

```r
pineport_use_python("/usr/local/bin/python3")   # or your venv's bin/python
```

---

## Performance

The bar loop is plain Python — roughly 1–2 seconds per 10,000 bars, most of it
in the `linreg(942)` warm-up. For parameter sweeps, `compute_indicators` is
separated from `run_strategy` so indicator series can be computed once and
reused across parameter sets that don't change them:

```python
ind = compute_indicators(df, base_params)
for p in candidates:           # only stop/exit params vary
    res = run_strategy(df, p, cfg, indicators=ind)
```

If that isn't fast enough, the bar loop is the thing to move to numba — not the
indicators, which are already vectorised.

---

## Hooking up a model

`run_strategy` takes a `signal_filter` argument: a boolean array aligned to the
bars, where `False` suppresses an entry. That is the whole interface an ML
overlay needs.

```python
res = run_strategy(df, params, cfg, signal_filter=model_says_take_it)
```

Two things to get right when you use it:

- Build features from data available **at or before the signal bar's close**.
  The entry fills at the next open, so the signal bar's close is fair game, but
  nothing after it is.
- Fit inside walk-forward folds, never on the whole sample. The equity curve
  from a model fitted on all the data is not a backtest.

Before doing any of that, read the last section of `QUIRKS.md` — on this
strategy as written there are around 5 trades per 8,000 bars, which is not
enough to train or validate anything. Raising the trade count comes first.
