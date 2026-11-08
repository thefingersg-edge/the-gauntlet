#!/usr/bin/env python3
"""Train the 4H strategy structure on another timeframe, end to end.

Runs the whole pipeline that was done by hand for 4H:

    1. baseline           what the current config does on this timeframe
    2. group optimisation  sma / rsi / squeeze / bands / stops, searched
                           jointly within each group, applied before the next,
                           repeated until nothing moves
    3. filter ladder       ADX, volatility gate, FRED switched on one at a
                           time with their own parameters optimised; kept only
                           if win rate AND profit factor both improve
    4. cost sensitivity    spread applied at several levels
    5. Pine output         the input block to paste back into TradingView

THE RANGE-SCALING DECISION -- read this before changing it

Parameter ranges are defined in 4H-BAR EQUIVALENTS and multiplied by the number
of target bars per 4H bar (M5 -> 48x, M1 -> 240x). This is deliberate.

`adx_len_short = 99` on 4H spans 16 days. Ninety-nine M1 bars span 99 minutes.
Searching the same bar-counts on a faster timeframe does not test the same
strategy, it tests a completely different and much shorter horizon -- and the
strongest result in this whole project is that long lookbacks carry stable
information while short ones do not (DESIGN_BRIEF.md 1b: 0 of 25 standard-length
indicators were sign-consistent across eras; 3 of 6 became so at 10x length).

Ranges still start at 2 bars, so the search CAN choose to be fast if fast is
genuinely better. It simply is not forced to be.

    python train_tf.py --csv xauusd_oanda_m5.csv --tf M5
    python train_tf.py --csv xauusd_oanda_m1.csv --tf M1 --start 2015-01-01
    python train_tf.py --csv xauusd_oanda_m5.csv --tf M5 --report
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set FORCE_SPAWN=1 to reproduce macOS/Windows worker behaviour on Linux.
if os.environ.get("FORCE_SPAWN"):
    mp.set_start_method("spawn", force=True)

from broker import BrokerConfig                     # noqa: E402
from data import _normalise, _read_csv              # noqa: E402
from metrics import compute_metrics                 # noqa: E402
from strategy import Params, run_strategy           # noqa: E402
import fetch_fred                                   # noqa: E402

BASE_CFG = "configs/gold_4h_stripped.json"
CAPITAL = 6000.0

#: minutes per bar, used to scale every length-type range
TF_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30,
              "H1": 60, "H4": 240, "D": 1440}

#: (param, lo, hi_in_4H_bars, is_int, scales_with_timeframe)
#: WIDENED after the live hand-tuned script was found to sit OUTSIDE these
#: ranges on four parameters. Both working configs -- Dave's live one and
#: gold_15m_scalefree -- use stops of ~2.95% long / 6.00% short, while the old
#: stops range of 0.5-10.0 scaled by stop_scale=0.25 on M15 allowed only
#: 0.125-2.5%. Every M15/M5/M1 search ever run was confined to stops less than
#: half the size of the ones that demonstrably work, so those runs could not
#: have found the working strategy no matter how long they searched.
#:
#: Lengths now reach 150 in 4H-equivalent terms, and the squeeze momentum
#: thresholds span the full +/-250 the indicator actually produces.
GROUPS: dict[str, tuple[list, dict]] = {
    "sma": ([("lsma_length_long", 1, 150, True, True),
             ("lsma_length_short", 1, 150, True, True),
             ("ssma_length_long", 1, 150, True, True),
             ("ssma_length_short", 1, 150, True, True)],
            {"use_sma_trigger_short": True}),
    "rsi": ([("rsi_length_long", 2, 150, True, True),
             ("rsi_oversold", 5.0, 95.0, False, False),
             ("rsi_length_short", 2, 150, True, True),
             ("rsi_overbought", 5.0, 95.0, False, False)], {}),
    "squeeze": ([("bb_length_l", 1, 150, True, True),
                 ("bb_length_s", 1, 150, True, True),
                 ("kc_length_l", 2, 150, True, True),
                 ("kc_length_s", 2, 150, True, True),
                 ("kc_mult", 0.5, 6.0, False, False),
                 # The linreg momentum value is unbounded and routinely runs to
                 # the low hundreds on gold; the old -120..60 window clipped it.
                 ("long_val", -250.0, 250.0, False, False),
                 ("short_val", -250.0, 250.0, False, False)], {}),
    "bands": ([("bb_period_long", 2, 150, True, True),
               ("bb_stdev_long", 0.1, 5.0, False, False),
               ("bb_period_short", 2, 150, True, True),
               ("bb_stdev_short", 0.1, 5.0, False, False)], {}),
    # markUp / lockProfit / range are ABSOLUTE DOLLARS in the Pine script, so
    # they never scale with bar size. 10000 in the script means "disabled";
    # the upper bound here is deliberately past any reachable rung so the
    # search can still choose to switch the ladder off.
    "ladder": ([("mark_up", 5.0, 900.0, False, False),
                ("lock_profit_up", 5.0, 900.0, False, False),
                ("range_long", 5.0, 400.0, False, False),
                ("mark_down", 5.0, 900.0, False, False),
                ("lock_profit_down", 5.0, 900.0, False, False),
                ("range_short", 5.0, 400.0, False, False)], {}),
    # A stop is a percentage of PRICE and has to survive the HOLDING PERIOD,
    # not one bar. These strategies hold ~14 days whether you look at them on
    # 15m or 4H candles, so the sensible stop is the SAME at both -- which is
    # why --stop-scale now defaults to 1.0 rather than 1/sqrt(bar ratio).
    "stops": ([("sl_percent_long", 0.01, 6.0, False, False),
               ("limit_percent_long", 0.01, 6.0, False, False),
               ("r_ratio_long", 0.5, 6.0, False, False),
               ("sl_percent_short", 0.01, 6.0, False, False),
               ("limit_percent_short", 0.01, 6.0, False, False),
               ("r_ratio_short", 0.5, 6.0, False, False)], {}),
}
ORDER = ["sma", "rsi", "squeeze", "bands", "stops", "ladder"]

#: Ladder rungs in three measurement systems. The DOLLAR ranges above are
#: calibrated to gold and DO NOT TRANSFER: 5-900 spans 0.17%-30% of a $3,000
#: gold price but only 0.03%-4.5% of a 20,000 index, so searching them on
#: NAS100 explores a different economic region than the one they were designed
#: for and every rung becomes trivially reachable.
#:
#: This is the same scale-dependence that produced the copper divisor error,
#: the global `volume < 10` cut, and the dollar-denominated stop parameters.
#: `strategy.py` already implements percent and ATR rungs (QUIRK 8); this just
#: lets the trainer search them.
#:
#: Percent bounds mirror the dollar ones as a fraction of gold's price, so a
#: `--ladder-mode percent` run on gold is comparable to the dollar run; ATR
#: bounds divide by gold's median ATR(14) of 8.59.
LADDER_SPECS = {
    "dollars": GROUPS["ladder"][0],
    "percent": [("mark_up_pct", 0.1, 30.0, False, False),
                ("lock_profit_up_pct", 0.1, 30.0, False, False),
                ("range_long_pct", 0.1, 15.0, False, False),
                ("mark_down_pct", 0.1, 30.0, False, False),
                ("lock_profit_down_pct", 0.1, 30.0, False, False),
                ("range_short_pct", 0.1, 15.0, False, False)],
    "atr": [("mark_up_atr", 0.5, 105.0, False, False),
            ("lock_profit_up_atr", 0.5, 105.0, False, False),
            ("range_long_atr", 0.5, 47.0, False, False),
            ("mark_down_atr", 0.5, 105.0, False, False),
            ("lock_profit_down_atr", 0.5, 105.0, False, False),
            ("range_short_atr", 0.5, 47.0, False, False)],
}


def set_ladder_mode(mode: str) -> None:
    """Point the ladder group at the chosen measurement system."""
    GROUPS["ladder"] = (LADDER_SPECS[mode], {"ladder_mode": mode})

FILTERS = [
    ("ADX trend", {"use_adx_filter": True, "use_adx_filter_short": True},
     [("adx_len", 2, 150, True, True), ("adx_smooth", 1, 200, True, True),
      ("adx_threshold", 1.0, 60.0, False, False),
      ("adx_len_short", 2, 200, True, True),
      ("adx_smooth_short", 1, 150, True, True),
      ("adx_threshold_short", 1.0, 60.0, False, False)]),
    ("volatility gate",
     {"use_volatility_filter": True, "use_volatility_filter_short": True},
     [("atr_long", 2, 200, True, True), ("vol_long", 5, 400, True, True),
      ("atr_short", 2, 300, True, True), ("vol_short", 5, 400, True, True)]),
    ("FRED real yield",
     {"use_macro_filter": True, "rate_filter_mode": "replace"},
     [("rate_sma_days", 2, 500, True, False)]),   # already in DAYS, never scale
]

#: Search ceiling. NOT capped at Pine's 5000-bar max_bars_back, because a long
#: lookback can be expressed on a higher timeframe instead: 6067 M5 bars is 21
#: days, which is ~126 H4 bars via request.security -- same horizon, a fraction
#: of the bars, comfortably inside the limit. Capping the search at 5000 would
#: discard genuinely better configs to work around a limit that has a
#: workaround. emit_pine() flags anything needing it. Set --max-bars-back 5000
#: if you want the search confined to what plain Pine can run directly.
MAX_LEN = 25_000
_DF = _RATES = _SCALE = _STOPSCALE = None
_MAXLEN = MAX_LEN
#: remembered so worker processes can rebuild state -- see _pool_init
_ARGS: tuple = ()


def _init(csv=None, start=None, scale=None, stop_scale=None, end=None):
    global _DF, _RATES, _SCALE, _STOPSCALE, _ARGS
    if scale is not None:
        _SCALE, _STOPSCALE = scale, stop_scale
        _ARGS = (csv, start, scale, stop_scale, end)
    if _DF is None and csv:
        d = _normalise(_read_csv(csv))
        if start:
            d = d[start:]
        # `end` exists so recent data can be HELD OUT. Without it the trainer
        # could only ever run to the last bar in the file, which silently
        # consumed the holdout: a 4H run to 2026-08 put 188% of its 228% total
        # into 2024-2026 at PF 14.96 on 39 trades, while returning PF 1.00 over
        # the seven years of 2013-2019 it could not lean on.
        if end:
            d = d[:end]
        if d.empty:
            raise SystemExit(
                f"\n  {csv} has NO ROWS"
                + (f" on or after {start}" if start else "")
                + (f" on or before {end}" if end else "")
                + ".\n  Check the fetch completed: the file should have "
                  "millions of rows for M1.\n  Run without --start/--end to "
                  "see its actual date range.")
        _DF = d
    if _RATES is None and os.path.exists("dfii10.csv"):
        _RATES = fetch_fred.load_daily_series("dfii10.csv")
    return _DF


def _pool_init(args) -> None:
    """Rebuild module state inside each worker.

    macOS (and Windows) SPAWN worker processes rather than forking them, so
    module-level globals like _DF are NOT inherited -- the child re-imports the
    module and gets None. On Linux fork made this work by accident. Every Pool
    must therefore pass this initialiser, or the workers crash with
    'NoneType' object is not subscriptable.
    """
    _init(*args)


def _fits_pine(cand: dict) -> bool:
    """Reject configs TradingView cannot execute.

    ta.dmi(len, smooth) needs len + smooth bars of history, and Pine's
    max_bars_back tops out at 5000. Checking here keeps the optimiser inside
    the feasible set instead of returning a winner that cannot be traded.
    """
    for a, b in (("adx_len", "adx_smooth"), ("adx_len_short", "adx_smooth_short")):
        if a in cand or b in cand:
            if cand.get(a, 0) + cand.get(b, 0) > _MAXLEN:
                return False
    return all(v <= _MAXLEN for k, v in cand.items()
               if isinstance(v, int) and "length" in k or k.startswith(("bb_period", "kc_length", "atr_", "vol_")))


def scaled(spec: list) -> list:
    """Apply the timeframe multiplier to length-type ranges."""
    out = []
    for name, lo, hi, is_int, scales in spec:
        if scales:
            hi = min(int(round(hi * _SCALE)), _MAXLEN)
            lo = max(int(lo), 1)
        elif "percent" in name and _STOPSCALE != 1.0:
            lo, hi = lo * _STOPSCALE, hi * _STOPSCALE
        out.append((name, lo, hi, is_int))
    return out


def evaluate(cfg: dict, slippage: float = 0.0) -> dict:
    res = run_strategy(_DF, Params(**cfg),
                       BrokerConfig(CAPITAL, 1.0, slippage_points=slippage),
                       rates=_RATES)
    m = compute_metrics(res.equity, res.trades, CAPITAL)
    t = res.trades
    ret = (t["pnl"] / (t["entry_price"] * t["qty"])) if len(t) else pd.Series(dtype=float)
    dd = abs(m["max_drawdown_pct"])
    return {"net": 100 * (res.equity.iloc[-1] / CAPITAL - 1),
            "trades": m["trades"], "winrate": m["win_rate_pct"],
            "pf": m["profit_factor"], "cagr": m["cagr_pct"],
            "sharpe": m["sharpe"], "maxdd": m["max_drawdown_pct"],
            # CAGR per unit of drawdown. Unlike net/cagr this is NOT a
            # monotonic transform of profit -- it will pick a different config.
            "calmar": (m["cagr_pct"] / dd) if dd > 1e-9 else np.nan,
            "avg_trade": 100 * float(ret.mean()) if len(ret) else np.nan}


def _sample(rng, name, lo, hi, is_int):
    """Draw one parameter -- LOG-uniform for lengths, uniform for everything else.

    Widening the length ranges to 150 (2400 after the M15 x16 scaling) made
    uniform sampling actively harmful: every working value sits between 3 and
    96, so only ~4% of uniform draws land in the region that matters and the
    rest test 1000-bar averages nobody wants. Log-uniform spends equal effort
    per octave -- as many draws in 3-30 as in 300-2400 -- which is how a
    lookback length should be searched, because the difference between 10 and
    20 bars is meaningful and the difference between 1010 and 1020 is not.

    Thresholds, multipliers and percentages stay uniform: their scale is
    already natural and some (long_val, short_val) straddle zero, where a log
    is undefined.
    """
    if is_int and lo >= 1 and hi / max(lo, 1) > 50:
        v = int(round(np.exp(rng.uniform(np.log(lo), np.log(hi)))))
        return min(max(v, int(lo)), int(hi))
    return int(rng.integers(lo, hi + 1)) if is_int else float(rng.uniform(lo, hi))


#: Arguments that change how a run EXECUTES but not what it PRODUCES. Anything
#: not listed here is assumed to affect the answer and goes into the tag hash.
#: Erring this way is deliberate: a spurious extra directory costs disk, a
#: missing one costs a wrong conclusion.
TAG_IGNORED = {
    "workers", "report", "fresh", "verbose", "self_test",
    # Execution control in train_staged.py, not result-affecting:
    #   redo   -- whether to recompute a stage already done
    #   only   -- WHICH stage to run this invocation
    #   stages -- the sequence, when running several
    # `only` and `stages` must be ignored or the piece-by-piece workflow
    # breaks: `--only sma` and `--only rsi` are meant to accumulate in ONE
    # directory, and hashing them would send each to its own. What was
    # actually run, and in what order, is recorded in state.json["order"]
    # instead -- which is the honest place for it, since the order emerges
    # from how the run was driven rather than from a flag.
    "redo", "only", "stages",
}


def settings_fingerprint(args, extra: dict | None = None) -> tuple[str, dict]:
    """8-char hash over every result-affecting input, plus the search space.

    Six separate times in this project a checkpoint key omitted an argument
    that changed the answer -- --samples, --train-years, --skip-retrain,
    --base, --min-trade-frac and --seed -- and each time a run silently
    inherited months computed under different settings. Twice that would have
    manufactured the exact conclusion being tested ("results are consistent
    across window lengths", "re-fitting makes no difference"), straight from
    a stale cache.

    A hand-maintained list of tag components will keep failing, because the
    failure mode is forgetting to update it. This derives the key from the
    whole argparse namespace instead, so a NEW ARGUMENT IS COVERED THE MOMENT
    IT EXISTS, with no second step to forget.

    GROUPS / FILTERS / ORDER are hashed too. They are not arguments, but
    widening the length ranges and the stop box changed what the search could
    reach without changing a single flag -- a behaviour change invisible to
    any argument-based key.
    """
    d = {k: v for k, v in sorted(vars(args).items()) if k not in TAG_IGNORED}
    if extra:
        d.update(extra)
    d["_space"] = repr(sorted((g, sorted(s), sorted(f.items()))
                              for g, (s, f) in GROUPS.items()))
    d["_filters"] = repr([(n, sorted(f.items()), sorted(s)) for n, f, s in FILTERS])
    d["_order"] = repr(ORDER)
    blob = json.dumps(d, sort_keys=True, default=str)
    return hashlib.sha1(blob.encode()).hexdigest()[:8], d


def guard_settings(out_dir: str, settings: dict) -> None:
    """Write the settings beside the results; refuse to resume a mismatch.

    Belt and braces behind the hash. The hash prevents collisions; this makes
    every results directory self-describing, so what produced it can be read
    off disk months later rather than reconstructed from a filename.
    """
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, "args.json")
    if os.path.exists(p):
        old = json.load(open(p))
        diff = {k: (old.get(k), settings.get(k)) for k in set(old) | set(settings)
                if str(old.get(k)) != str(settings.get(k))}
        if diff:
            lines = "\n".join(f"    {k}: {a!r} -> {b!r}" for k, (a, b) in diff.items())
            raise SystemExit(
                f"\n{out_dir} was produced by DIFFERENT settings:\n{lines}\n"
                "  Resuming would mix results from two different questions.\n"
                "  Delete the directory, or change a setting so the tag differs.")
    else:
        json.dump(settings, open(p, "w"), indent=2, default=str)


def trade_floor(base_trades: int, frac: float, n_bars: int, tf: str,
                min_abs: int = 30) -> int:
    """Minimum trade count a candidate must clear on the TRAINING window.

    WHY THE OLD 0.25 WAS WRONG. The floor exists to stop the optimiser gaming
    the objective with a handful of lucky trades. At 0.25 x baseline it also
    permitted a FOUR-FOLD drop in activity, which for a strategy already
    trading ~10 times a year means a qualifying config need only trade 2.6
    times a year. Measured consequence on the 10-year rolling run: the frozen
    config was flat in 7% of test months, the re-fitted one in 27%, and the
    search's apparent inferiority was substantially "it picked configs that
    sit out" rather than "it picked bad entries".

    The floor CANNOT be applied to the test month -- that would be lookahead.
    So it is applied as a comparable trade RATE on the training window: clear
    `frac` of the baseline's trades-per-year and you are as active as the
    thing you are trying to beat.
    """
    years = max(n_bars * TF_MINUTES[tf] / (365.25 * 24 * 60), 1e-9)
    by_rate = frac * base_trades            # same window, so rate == count
    return int(max(min_abs, round(by_rate)))


def _trial(args):
    seed, cur, fixed, spec, floor, objective, slip = args
    rng = np.random.default_rng(seed)
    cand = {n: _sample(rng, n, lo, hi, i) for n, lo, hi, i in spec}
    # Optimising at ZERO cost gives the search no reason to prefer fewer,
    # larger trades. On M5 that produced 18,598 trades with a 1.4bp edge
    # against a 3bp round-trip spread -- a real gross edge that is entirely
    # consumed by execution. Scoring at the spread you will actually pay makes
    # trade count part of the objective instead of an afterthought.
    if not _fits_pine(cand):
        return cand, {"net": -1e9, "trades": 0, "winrate": 0.0, "pf": 0.0,
                      "cagr": 0.0, "sharpe": 0.0, "maxdd": 0.0,
                      "avg_trade": 0.0}, -np.inf
    r = evaluate({**cur, **fixed, **cand}, slippage=slip)
    if r["trades"] < floor:
        return cand, r, -np.inf
    v = r[objective]
    return cand, r, (v if np.isfinite(v) else -np.inf)


def search(cur, fixed, spec, floor, samples, seed, workers, objective, slip=0.0):
    rng = np.random.default_rng(seed)
    tasks = [(int(rng.integers(0, 2**31)), cur, fixed, spec, floor, objective,
              slip) for _ in range(samples)]
    with mp.Pool(workers, initializer=_pool_init, initargs=(_ARGS,)) as pool:
        got = pool.map(_trial, tasks, chunksize=4)
    return max(got, key=lambda x: x[2])


_TF = "H4"


def emit_pine(cfg: dict) -> str:
    m = [("RSIlengthL", "rsi_length_long"), ("RSIlengthS", "rsi_length_short"),
         ("RSIoverSold", "rsi_oversold"), ("RSIoverBought", "rsi_overbought"),
         ("LSMAlengthL", "lsma_length_long"), ("LSMAlengthS", "lsma_length_short"),
         ("SSMAlengthL", "ssma_length_long"), ("SSMAlengthS", "ssma_length_short"),
         ("adx_len", "adx_len"), ("adx_smooth", "adx_smooth"),
         ("adxVar", "adx_threshold"), ("adx_lenS", "adx_len_short"),
         ("adx_smoothS", "adx_smooth_short"), ("adxVarS", "adx_threshold_short"),
         ("atr_longL", "atr_long"), ("Vol_longL", "vol_long"),
         ("atr_longS", "atr_short"), ("Vol_longS", "vol_short"),
         ("rate_sma_len", "rate_sma_days"),
         ("lengthL", "bb_length_l"), ("lengthS", "bb_length_s"),
         ("lengthKCL", "kc_length_l"), ("lengthKCS", "kc_length_s"),
         ("multKC", "kc_mult"), ("longVal", "long_val"), ("shortVal", "short_val"),
         ("BBlengthL", "bb_period_long"), ("BBmultL", "bb_stdev_long"),
         ("BBlengthS", "bb_period_short"), ("BBmultS", "bb_stdev_short"),
         ("SL_percent_basedL", "sl_percent_long"),
         ("L_percent_basedL", "limit_percent_long"), ("r_ratioL", "r_ratio_long"),
         ("SL_percent_basedS", "sl_percent_short"),
         ("L_percent_basedS", "limit_percent_short"), ("r_ratioS", "r_ratio_short")]

    # The ladder rungs MUST follow ladder_mode. Emitting the dollar keys
    # unconditionally printed markUp=10000 (the "disabled" sentinel) for every
    # percent-mode run, while the config being scored actually had
    # mark_up_pct=5.76 and friends -- so the Pine shown was a DIFFERENT
    # strategy from the one in the results table. Same failure the 4H run had,
    # in a new place: the numbers were right, the report was not.
    mode = cfg.get("ladder_mode", "dollars")
    suffix = {"dollars": "", "percent": "_pct", "atr": "_atr"}[mode]
    tag = {"dollars": "", "percent": "_pct", "atr": "_atr"}[mode]
    m += [(f"markUp{tag}", f"mark_up{suffix}"),
          (f"lockProfitUp{tag}", f"lock_profit_up{suffix}"),
          (f"rangeL{tag}", f"range_long{suffix}"),
          (f"markDown{tag}", f"mark_down{suffix}"),
          (f"lockProfitDown{tag}", f"lock_profit_down{suffix}"),
          (f"rangeS{tag}", f"range_short{suffix}")]

    lines = []
    if mode != "dollars":
        lines.append(f"// LADDER MODE = {mode.upper()}: rungs below are "
                     + ("PERCENTAGES OF ENTRY PRICE"
                        if mode == "percent" else "MULTIPLES OF ATR")
                     + ", not dollars.")
        lines.append("// The stock Pine script uses DOLLAR rungs -- it needs the "
                     "scale-free variant")
        lines.append("// or these values will be read as absolute points and "
                     "the ladder will fire instantly.")
    for pine, key in m:
        if key not in cfg:
            continue
        v = cfg[key]
        if isinstance(v, bool):
            continue
        if isinstance(v, float) and not float(v).is_integer():
            lines.append(f'{pine:<18}= input.float({v:.4g}, "{pine}")')
        else:
            lines.append(f'{pine:<18}= input.int({int(v)}, "{pine}")')
    on = []
    if cfg.get("use_adx_filter"):
        on.append("trend_is_active")
    if cfg.get("use_adx_filter_short"):
        on.append("trend_is_activeS")
    if cfg.get("use_volatility_filter"):
        on.append("volatility_gateL")
    if cfg.get("use_volatility_filter_short"):
        on.append("volatility_gateS")
    if cfg.get("use_macro_filter"):
        on.append("rateGateLong")
    if cfg.get("use_sma_trigger_short"):
        on.append("(SSMAS < SSMAL)")
    # Anything past Pine's 5000-bar ceiling needs the request.security form.
    # ONLY length-type parameters are bar counts. markUp / lockProfit / range
    # are DOLLARS -- 10000 there means "ladder disabled", not 10000 bars, and
    # flagging it as a max_bars_back problem is nonsense.
    LENGTHS = {"adx_len", "adx_smooth", "adx_len_short", "adx_smooth_short",
               "atr_long", "vol_long", "atr_short", "vol_short",
               "lsma_length_long", "lsma_length_short",
               "ssma_length_long", "ssma_length_short",
               "rsi_length_long", "rsi_length_short",
               "bb_length_l", "bb_length_s", "kc_length_l", "kc_length_s",
               "bb_period_long", "bb_period_short"}
    long_ones = [(p, k, cfg[k]) for p, k in m
                 if k in LENGTHS and k in cfg
                 and isinstance(cfg[k], (int, float))
                 and not isinstance(cfg[k], bool) and cfg[k] > 5000]
    pairs = [("adx_len", "adx_smooth", "long"), ("adx_len_short", "adx_smooth_short", "short")]
    for a, b, side in pairs:
        if cfg.get(a, 0) + cfg.get(b, 0) > 5000 and not any(k == a for _, k, _ in long_ones):
            long_ones.append((a, a, cfg.get(a, 0)))
    if long_ones:
        lines.append("")
        lines.append("// EXCEEDS PINE'S 5000-BAR max_bars_back -- use request.security")
        lines.append("// on a higher timeframe for the same horizon:")
        for pine, key, v in long_ones:
            mins = float(v) * TF_MINUTES[_TF]
            for htf, hm in (("60", 60), ("240", 240), ("D", 1440)):
                n_bars = mins / hm
                if n_bars <= 4000:
                    lines.append(f'//   {pine} = {v:g} bars = {mins/1440:.1f} days'
                                 f'  ->  {n_bars:.0f} bars on the "{htf}" timeframe')
                    break
    lines.append("")
    lines.append("// filters to UNCOMMENT in longSignal / shortSignal:")
    lines.append("//   " + (", ".join(on) if on else "none -- leave all commented out"))
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--tf", required=True, choices=sorted(TF_MINUTES))
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None,
                    help="last date to TRAIN on, e.g. 2023-12-31. Anything "
                         "after it is held out. Without this the search runs "
                         "to the end of the file and will happily locate its "
                         "edge in the most recent window, which is exactly "
                         "the data you wanted to test on.")
    ap.add_argument("--samples", type=int, default=400)
    ap.add_argument("--passes", type=int, default=2)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 1))
    ap.add_argument("--trigger-tolerance", type=int, default=None,
                    help="hold trigger_tolerance FIXED at this value for the "
                         "whole search. Changing it changes the strategy -- "
                         "entries fire far more often at 3 than at 0 -- so the "
                         "selective parameters must be re-fitted for it. "
                         "Comparing tolerance levels using parameters tuned at "
                         "tolerance 0 measures the mismatch, not the idea.")
    ap.add_argument("--min-trade-frac", type=float, default=0.6,
                    help="a candidate must take at least this FRACTION of the "
                         "baseline's trades on the training window. Was "
                         "hardcoded at 0.25, which let activity fall 4x and "
                         "filled the rolling test with configs that sit out "
                         "whole months. 0.6 keeps candidates comparably active.")
    ap.add_argument("--stop-scale", type=float, default=None,
                    help="multiplier on stop%% ranges. Default 1.0 -- the range "
                         "is used as written (0.01-6.00%%). Pass a smaller "
                         "value only if you deliberately want tighter stops "
                         "than the working configs use.")
    ap.add_argument("--length-scale", type=float, default=1.0,
                    help="extra multiplier on LENGTH ranges, on top of the "
                         "timeframe conversion. The GROUPS ranges are 1-60 "
                         "in 4H-bar equivalents, i.e. 4 hours to 10 days, so "
                         "on Daily bars they collapse to 1-10 days. This "
                         "project measured trend as sign-consistent at 3-12 "
                         "MONTHS and inconsistent at 8 days, so a Daily run "
                         "left at the default searches only the horizon "
                         "already known not to work. --length-scale 25 "
                         "reaches ~250 daily bars (a year).")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--objective", default="net",
                    choices=["net", "cagr", "calmar", "sharpe", "pf", "avg_trade"],
                    help="what the GROUP search maximises. NOTE: net and cagr "
                         "rank identically over a fixed window (cagr is a "
                         "monotonic transform of net), so they return the same "
                         "config. calmar and sharpe genuinely differ -- they "
                         "trade return against drawdown and volatility.")
    ap.add_argument("--filter-objective", default="pf",
                    choices=["net", "cagr", "calmar", "sharpe", "pf", "avg_trade"],
                    help="what the FILTER ladder maximises (default pf)")
    ap.add_argument("--max-bars-back", type=int, default=MAX_LEN,
                    help="search ceiling on lookback length. Default is well "
                         "past Pine's 5000-bar limit because long lookbacks can "
                         "be run via request.security on a higher timeframe; "
                         "pass 5000 to confine the search to plain Pine.")
    ap.add_argument("--slippage", type=float, default=0.0,
                    help="spread in price points applied DURING the search, "
                         "not just in the final table. Use the spread you will "
                         "actually pay (gold CFD ~0.25) so trade count becomes "
                         "part of the objective.")
    ap.add_argument("--ladder-mode", default="dollars",
                    choices=sorted(LADDER_SPECS),
                    help="how profit-ladder rungs are measured. 'dollars' is "
                         "the Pine original and is calibrated to gold prices; "
                         "use 'percent' or 'atr' on any other instrument, or "
                         "the rung ranges mean something different than they "
                         "did on gold.")
    ap.add_argument("--base", help="config to start the search from. Defaults "
                                   "to the 4H stripped config, which is a poor "
                                   "starting point for a 15m gold run -- point "
                                   "this at the config you actually want to "
                                   "improve on. Its name is added to the output "
                                   "filenames so a --base run cannot overwrite "
                                   "an earlier one.")
    ap.add_argument("--allow-shorts", default=None, choices=["true", "false"],
                    help="force shorts on or off for the whole search. Set "
                         "false to optimise the LONG-ONLY variant, which is the "
                         "only version that prices sensibly (an ETF pays no "
                         "financing; a CFD at rf+2.5%% is worse than cash).")
    ap.add_argument("--fresh", action="store_true",
                    help="ignore any saved state and start over")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    # --base and the date window go in the tag. Without them a run starting
    # from a different config, or over a different window, would overwrite the
    # previous `_trained.json` and its resume state -- so a fresh search could
    # silently inherit checkpoints from a search that asked a different question.
    # Human-readable stem so a directory can be recognised at a glance, plus a
    # hash over EVERY result-affecting argument and the search space itself.
    # The readable part is for you; the hash is what makes the key correct.
    fp, settings = settings_fingerprint(a)
    tag = (f"{os.path.basename(a.csv).replace('.csv','')}_{a.tf}"
           + (f"_b{os.path.basename(a.base).replace('.json','')}" if a.base else "")
           + (f"_{a.start[:7]}" if a.start else "")
           + (f"_to{a.end[:7]}" if a.end else "")
           + ("_longonly" if a.allow_shorts == "false" else "")
           + (f"_tol{a.trigger_tolerance}" if a.trigger_tolerance is not None else "")
           + (f"_seed{a.seed}" if a.seed else "")
           + f"_{fp}")
    out = f"results/train_{tag}"
    guard_settings(out, settings)
    state_path = f"{out}/state.json"

    global _MAXLEN, _TF, BASE_CFG
    _MAXLEN, _TF = a.max_bars_back, a.tf
    set_ladder_mode(a.ladder_mode)
    if a.base:
        if not os.path.exists(a.base):
            raise SystemExit(f"--base {a.base} not found")
        BASE_CFG = a.base
    if a.trigger_tolerance is not None:
        for g, (spec, fixed) in GROUPS.items():
            GROUPS[g] = (spec, {**fixed, "trigger_tolerance": a.trigger_tolerance})
        for i, (nm, fx, sp) in enumerate(FILTERS):
            FILTERS[i] = (nm, {**fx, "trigger_tolerance": a.trigger_tolerance}, sp)
    if a.allow_shorts is not None:
        # Applied as a FIXED switch on every group, so no candidate anywhere in
        # the search can turn shorts back on.
        want = a.allow_shorts == "true"
        for g, (spec, fixed) in GROUPS.items():
            GROUPS[g] = (spec, {**fixed, "allow_shorts": want})
        for i, (nm, fx, sp) in enumerate(FILTERS):
            FILTERS[i] = (nm, {**fx, "allow_shorts": want}, sp)
    ratio = TF_MINUTES["H4"] / TF_MINUTES[a.tf]
    # DEFAULT NOW 1.0. It used to be 1/sqrt(bar ratio), which on M15 shrank the
    # stop range to 0.125-2.5% -- excluding the ~2.95%/6.00% stops that BOTH
    # working configs use. The premise was that faster bars need tighter stops;
    # the premise is wrong, because the stop has to survive the holding period
    # and that is ~14 days on either timeframe.
    stop_scale = a.stop_scale if a.stop_scale is not None else 1.0
    df = _init(a.csv, a.start, ratio * a.length_scale, stop_scale, a.end)

    print(f"\nTRAINING {tag}   {len(df):,} bars   "
          f"{df.index[0].date()} -> {df.index[-1].date()}")
    # Report the multiplier ACTUALLY used, not the bare timeframe ratio. The
    # NAS100 Daily run printed "x0" while genuinely searching x4.2, which is
    # the kind of mismatch that makes a correct run look broken.
    print(f"  length ranges x{ratio * a.length_scale:.3g} (4H-equivalent"
          + (f", incl. --length-scale {a.length_scale:g}" if a.length_scale != 1 else "")
          + f"), stop%% ranges x{stop_scale:.2f}")
    print(f"  {a.workers} workers, {a.samples} samples/group, {a.passes} passes")
    print("=" * 100)

    if os.path.exists(state_path) and not a.fresh:
        st = json.load(open(state_path))
        cur, done, kept = st["cur"], st["done"], st["kept"]
        print(f"  resuming from {state_path} ({len(done)} steps done)")
    else:
        cur, done, kept = json.load(open(BASE_CFG)), [], []

    base = evaluate(json.load(open(BASE_CFG)), slippage=a.slippage)
    if not done:
        print(f"  {'step':<26}{'trades':>8}{'win%':>7}{'PF':>7}{'net%':>10}"
              f"{'Sharpe':>8}{'maxDD%':>9}  status")
        print("  " + "-" * 92)
        print(f"  {'baseline (4H params)':<26}{base['trades']:>8}{base['winrate']:>7.1f}"
              f"{base['pf']:>7.2f}{base['net']:>10.1f}{base['sharpe']:>8.2f}"
              f"{base['maxdd']:>9.2f}")

    floor = trade_floor(base["trades"], a.min_trade_frac, len(df), a.tf)

    # ---- stage 1: groups, optimising net profit ----------------------------
    for p in range(1, a.passes + 1):
        for grp in ORDER:
            key = f"pass{p}:{grp}"
            if key in done:
                continue
            spec, fixed = GROUPS[grp]
            t0 = time.time()
            cand, r, score = search(cur, fixed, scaled(spec), floor, a.samples,
                                    a.seed + 1000 * p + hash(grp) % 997,
                                    a.workers, a.objective, a.slippage)
            prev = evaluate(cur, slippage=a.slippage)[a.objective]
            # score == -inf means NO candidate cleared the trade floor. max()
            # still returns one, and applying it is how a 2-trade PF=inf
            # "winner" gets adopted. Require a finite score.
            #
            # AND prev may itself be nan: a config that wipes the account has
            # negative final equity, so CAGR (and therefore calmar) is nan.
            # Every `candidate > nan` is False, so a blown-up incumbent could
            # never be improved on and the entire run reported "kept current".
            # A finite score always beats a non-finite incumbent.
            moved = np.isfinite(score) and (not np.isfinite(prev)
                                            or r[a.objective] > prev)
            if moved:
                cur = {**cur, **fixed, **cand}
            done.append(key)
            json.dump({"cur": cur, "done": done, "kept": kept},
                      open(state_path, "w"), indent=2, default=str)
            print(f"  {key:<26}{r['trades']:>8}{r['winrate']:>7.1f}{r['pf']:>7.2f}"
                  f"{r['net']:>10.1f}{r['sharpe']:>8.2f}{r['maxdd']:>9.2f}  "
                  f"{'applied' if moved else 'kept current'}  [{time.time()-t0:.0f}s]",
                  flush=True)

    # ---- stage 2: filter ladder, optimising profit factor ------------------
    prev = evaluate(cur, slippage=a.slippage)
    for name, fixed, spec in FILTERS:
        key = f"filter:{name}"
        if key in done:
            continue
        cand, r, score = search(cur, fixed, scaled(spec), floor, a.samples,
                                a.seed + hash(name) % 9973, a.workers, "pf",
                                a.slippage)
        pw, pp = prev["winrate"], prev["pf"]
        better = (np.isfinite(score)
                  and (not np.isfinite(pw) or r["winrate"] > pw)
                  and (not np.isfinite(pp) or r["pf"] > pp))
        if better:
            cur, prev = {**cur, **fixed, **cand}, r
            kept.append(name)
        done.append(key)
        json.dump({"cur": cur, "done": done, "kept": kept},
                  open(state_path, "w"), indent=2, default=str)
        print(f"  {key:<26}{r['trades']:>8}{r['winrate']:>7.1f}{r['pf']:>7.2f}"
              f"{r['net']:>10.1f}{r['sharpe']:>8.2f}{r['maxdd']:>9.2f}  "
              f"{'KEEP' if better else 'revert'}", flush=True)

    # ---- stage 3: costs ----------------------------------------------------
    print(f"\n  COST SENSITIVITY  (spread in price points, applied per fill)")
    print("  " + "-" * 92)
    # Sweep RELATIVE to the spread actually being paid. The fixed gold ladder
    # (0.00-0.50) never reached NAS100's measured 2.0-point spread, so every
    # cost table on that instrument stopped short of the real cost and looked
    # reassuringly flat. Anchoring on --slippage keeps break-even inside the
    # sweep whatever the instrument's price scale.
    base_slip = a.slippage if a.slippage > 0 else 0.25
    for slip in tuple(round(base_slip * f, 4) for f in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0)):
        r = evaluate(cur, slippage=slip)
        print(f"  {'slippage ' + format(slip, '.2f'):<26}{r['trades']:>8}"
              f"{r['winrate']:>7.1f}{r['pf']:>7.2f}{r['net']:>10.1f}"
              f"{r['sharpe']:>8.2f}{r['maxdd']:>9.2f}")

    # MUST carry the search slippage. Without it the FINAL line reported a
    # zero-cost run against a BASELINE that had costs applied (line above uses
    # slippage=a.slippage), so the summary flattered every result: the M1 run
    # printed "FINAL net 56.0%" when the config's own cost-laden number was
    # 14.4%. Same config, same window -- the 56% was simply free trading.
    final = evaluate(cur, slippage=a.slippage)
    print(f"\n  BASELINE : net {base['net']:>8.1f}%  win {base['winrate']:.1f}%  "
          f"PF {base['pf']:.2f}  Sharpe {base['sharpe']:.2f}  trades {base['trades']}")
    print(f"  FINAL    : net {final['net']:>8.1f}%  win {final['winrate']:.1f}%  "
          f"PF {final['pf']:.2f}  Sharpe {final['sharpe']:.2f}  trades {final['trades']}")
    print(f"  filters kept: {', '.join(kept) if kept else 'none'}")

    json.dump(cur, open(f"configs/{tag}_trained.json", "w"), indent=2, default=str)
    pine = emit_pine(cur)
    open(f"{out}/pine_inputs.txt", "w").write(pine)
    print(f"\n  wrote configs/{tag}_trained.json")
    print(f"  wrote {out}/pine_inputs.txt\n")
    print(pine)


if __name__ == "__main__":
    main()
