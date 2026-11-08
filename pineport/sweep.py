#!/usr/bin/env python3
"""Fast per-parameter sweeps -- what the Chrome-extension optimiser does, in seconds.

For each parameter it walks a range of values and reports the whole profile,
not just the winner. Three things make it fast:

  1. Indicators are cached. Roughly 45% of a run is indicator computation, and
     parameters that only touch the exit/stop logic do not change them, so they
     are computed once and reused across the sweep.
  2. Values are evaluated in parallel across cores.
  3. One run per value covers both the fit and validation periods -- metrics are
     computed on sub-slices of the same trade list rather than re-running.

WHY IT REPORTS MORE THAN TOTAL PROFIT

Optimising each parameter on total profit over the whole history is the fastest
way to overfit, and this project has already measured that happening: in the
walk-forward retrain, `bb_stdev_long` tripled returns in one window while
slightly REDUCING them across 17.8 years. A profit-only sweep would have picked
it and called it an improvement.

So every row shows FIT (2006-2019) and VAL (2020-2023) side by side, and the
summary flags when the profit-maximising value differs from the validation-
maximising one. 2024-2026 is never touched here -- it stays sealed for a final
check, and stops being a holdout the moment you tune against it.

PLATEAU vs SPIKE is the other thing to read. A parameter whose best value sits
on a broad plateau is a real setting; one that spikes at a single value and
falls away either side is noise you will not see again live.

    python sweep.py --param bb_stdev_long --points 25
    python sweep.py --all --points 15
    python sweep.py --list
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from broker import BrokerConfig                                  # noqa: E402
from data import _normalise, _read_csv                           # noqa: E402
from metrics import compute_metrics                              # noqa: E402
from strategy import Params, run_strategy, compute_indicators    # noqa: E402

DATA = "xauusd_oanda_m15.csv"
BASE_CFG = "configs/gold_15m_scalefree.json"
OUT = "results/sweeps"
CAPITAL = 6000.0

SWEEP_START, SWEEP_END = "2006-01-01", "2023-12-31"
FIT_END = "2019-12-31"          # fit / validation split inside the sweep window
VAL_START = "2020-01-01"
# 2024-2026 is deliberately absent. Do not add it.

#: name -> (low, high, is_int). Ranges are wide enough to show the shape of the
#: curve, not just the neighbourhood of the current value.
RANGES: dict[str, tuple] = {
    # --- entry band
    "bb_period_long":     (10, 160, True),
    "bb_stdev_long":      (0.5, 3.0, False),
    "bb_period_short":    (3, 60, True),
    "bb_stdev_short":     (0.5, 3.0, False),
    # --- oscillators / trend state
    "rsi_length_long":    (2, 40, True),
    "rsi_oversold":       (35.0, 70.0, False),
    "rsi_length_short":   (2, 40, True),
    "rsi_overbought":     (20.0, 55.0, False),
    "lsma_length_long":   (5, 120, True),
    "ssma_length_long":   (3, 60, True),
    # --- squeeze
    "bb_length_l":        (3, 40, True),
    "bb_length_s":        (3, 40, True),
    "kc_length_l":        (4, 60, True),
    "kc_length_s":        (4, 60, True),
    "kc_mult":            (1.0, 4.5, False),
    # --- adx (short side only; long ADX is off)
    "adx_len_short":      (5, 60, True),
    "adx_smooth_short":   (1, 40, True),
    "adx_threshold_short": (15.0, 50.0, False),
    # --- exits / stops  (loop-only: indicators cached, ~2x faster)
    "sl_percent_long":    (1.0, 8.0, False),
    "limit_percent_long": (1.0, 10.0, False),
    "r_ratio_long":       (1.0, 6.0, False),
    "sl_percent_short":   (1.0, 10.0, False),
    "limit_percent_short": (1.0, 10.0, False),
    "r_ratio_short":      (1.0, 6.0, False),
    "flex_up":            (0.85, 1.0, False),
    "gap_up":             (0.97, 1.0, False),
    # --- ladder, now scale-free
    "mark_up_pct":        (2.0, 25.0, False),
    "lock_profit_up_pct": (2.0, 25.0, False),
    "range_long_pct":     (1.0, 12.0, False),
    "mark_down_pct":      (2.0, 20.0, False),
    "range_short_pct":    (1.0, 12.0, False),
}

#: Parameters that do NOT feed compute_indicators, so the indicator frame can be
#: computed once and reused across every value. Everything else rebuilds it.
LOOP_ONLY = {
    "sl_percent_long", "limit_percent_long", "r_ratio_long",
    "sl_percent_short", "limit_percent_short", "r_ratio_short",
    "flex_up", "flex_down", "gap_up", "gap_down",
    "trace_line_up", "trace_line_down", "profit_line_up", "profit_line_down",
    "mark_up_pct", "lock_profit_up_pct", "range_long_pct",
    "mark_down_pct", "lock_profit_down_pct", "range_short_pct",
    "risk_percent", "size_divisor",
}

_DF = _BASE = _IND = None


def _init(cached_for: str | None = None) -> None:
    global _DF, _BASE, _IND
    if _DF is None:
        _DF = _normalise(_read_csv(DATA))[SWEEP_START:SWEEP_END]
    if _BASE is None:
        _BASE = json.load(open(BASE_CFG))
    if cached_for and _IND is None:
        _IND = compute_indicators(_DF, Params(**_BASE))


def _metrics(trades, equity, lo, hi) -> dict:
    """Metrics over a date sub-slice of one run, so a value needs only one run."""
    t = trades[(trades["entry_time"] >= lo) & (trades["entry_time"] <= hi)]
    eq = equity[lo:hi]
    if len(t) < 3 or len(eq) < 2:
        return {"trades": len(t), "profit": np.nan, "calmar": np.nan, "pf": np.nan}
    m = compute_metrics(eq, t, CAPITAL)
    ret = (t["pnl"] / (t["entry_price"] * t["qty"])).clip(lower=-0.99)
    return {"trades": len(t),
            "profit": float(np.expm1(np.log1p(ret).sum()) * 100),
            "calmar": m.get("calmar", np.nan),
            "pf": m.get("profit_factor", np.nan)}


def _one(args):
    name, value, use_cache = args
    _init(name if use_cache else None)
    p = Params(**{**_BASE, name: value})
    res = run_strategy(_DF, p, BrokerConfig(CAPITAL, 1.0),
                       indicators=_IND if use_cache else None)
    fit = _metrics(res.trades, res.equity, SWEEP_START, FIT_END)
    val = _metrics(res.trades, res.equity, VAL_START, SWEEP_END)
    return {"value": value,
            "fit_trades": fit["trades"], "fit_profit": fit["profit"],
            "fit_calmar": fit["calmar"],
            "val_trades": val["trades"], "val_profit": val["profit"],
            "val_calmar": val["calmar"], "val_pf": val["pf"]}


def sweep(name: str, points: int, workers: int) -> pd.DataFrame:
    if name not in RANGES:
        raise SystemExit(f"unknown parameter {name!r}; try --list")
    lo, hi, is_int = RANGES[name]
    vals = (sorted(set(np.linspace(lo, hi, points).round().astype(int).tolist()))
            if is_int else np.linspace(lo, hi, points).tolist())
    cache = name in LOOP_ONLY

    _init(name if cache else None)
    cur = _BASE.get(name)
    print(f"\n{name}   current {cur}   range {lo}-{hi}   {len(vals)} points"
          f"   {'indicators cached' if cache else 'indicators rebuilt'}")
    print("=" * 92)

    with mp.Pool(workers) as pool:
        rows = pool.map(_one, [(name, v, cache) for v in vals])
    r = pd.DataFrame(rows)

    print(f"{'value':>10}{'FIT 2006-19':>26}{'VAL 2020-23':>28}")
    print(f"{'':>10}{'trades':>8}{'profit%':>10}{'calmar':>8}"
          f"{'trades':>10}{'profit%':>10}{'calmar':>8}{'PF':>8}")
    print("-" * 92)
    bf = r["fit_profit"].idxmax() if r["fit_profit"].notna().any() else None
    bv = r["val_profit"].idxmax() if r["val_profit"].notna().any() else None
    for i, x in r.iterrows():
        mark = ""
        if i == bf:
            mark += "  <- best FIT"
        if i == bv:
            mark += "  <- best VAL"
        if cur is not None and abs(float(x["value"]) - float(cur)) < 1e-9:
            mark += "  (current)"
        print(f"{x['value']:>10.3f}{x['fit_trades']:>8.0f}{x['fit_profit']:>10.1f}"
              f"{x['fit_calmar']:>8.2f}{x['val_trades']:>10.0f}"
              f"{x['val_profit']:>10.1f}{x['val_calmar']:>8.2f}{x['val_pf']:>8.2f}{mark}")

    if bf is not None and bv is not None:
        vf, vv = r.loc[bf, "value"], r.loc[bv, "value"]
        print()
        if abs(float(vf) - float(vv)) > 1e-9:
            print(f"  DISAGREEMENT: best on fit profit = {vf:.3f}, "
                  f"best on validation = {vv:.3f}")
            print("  Optimising total profit alone would have picked the first.")
        else:
            print(f"  fit and validation agree on {vf:.3f}")
        # plateau test: how much of the range is within 10% of the best VAL profit
        best = r.loc[bv, "val_profit"]
        if np.isfinite(best) and best > 0:
            near = (r["val_profit"] >= 0.9 * best).sum()
            frac = near / len(r)
            shape = ("PLATEAU -- robust" if frac >= 0.3 else
                     "SPIKE -- likely noise" if frac <= 0.12 else "narrow")
            print(f"  {near}/{len(r)} values within 10% of the best validation "
                  f"profit  ->  {shape}")
    os.makedirs(OUT, exist_ok=True)
    r.to_csv(f"{OUT}/{name}.csv", index=False)
    return r


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--param")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--points", type=int, default=15)
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()

    if a.list:
        print(f"{len(RANGES)} sweepable parameters "
              f"({len(set(RANGES) & LOOP_ONLY)} with cached indicators, ~2x faster)\n")
        for k, (lo, hi, i) in RANGES.items():
            print(f"  {k:<24}{lo:>8} - {hi:<8}"
                  f"{'  [cached]' if k in LOOP_ONLY else ''}")
        return
    if a.param:
        sweep(a.param, a.points, a.workers)
    elif a.all:
        for k in RANGES:
            try:
                sweep(k, a.points, a.workers)
            except Exception as exc:
                print(f"  {k}: FAILED {exc}")
    else:
        raise SystemExit("pass --param NAME, --all, or --list")


if __name__ == "__main__":
    main()
