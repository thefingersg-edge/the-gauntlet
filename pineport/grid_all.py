#!/usr/bin/env python3
"""Brute-force every ACTIVE parameter pair in the 4H script, ranked by net profit.

One 2-D grid per logical group, because the parameters in a group interact with
each other far more than across groups (a Bollinger period means nothing without
its stdev). Groups covered -- only those actually wired into longSignal /
shortSignal in the current script; ADX, the volatility gates, the FRED filter
and the ladder are all commented out there and are skipped.

    lsma        LSMAlengthL x LSMAlengthS      (LSMAS > LSMAL, long entry)
    ssma        SSMAlengthL x SSMAlengthS      (SSMAS < SSMAL, short entry)
    rsi_long    RSIlengthL  x RSIoverSold
    rsi_short   RSIlengthS  x RSIoverBought
    bb_long     BBlengthL   x BBmultL          (long entry band)
    bb_short    BBlengthS   x BBmultS          (short entry band)
    kc          lengthKCL   x lengthKCS        (squeeze channel)
    sqz_bb      lengthL     x lengthS          (squeeze bands)
    vals        longVal     x shortVal         (squeeze momentum thresholds)
    stop_long   SL%L        x Limit%L
    stop_short  SL%S        x Limit%S

READ THE CLUSTER COLUMN, NOT JUST THE WINNER

Eleven groups at ~324 cells each is ~3,500 chances for noise to produce a
flattering number. Two guards are printed for every group:

    nbrs   how many of the 8 adjacent cells are within 20% of the winner.
           A real setting sits in a cluster (>=4); an isolated peak (<=1) is
           an island and will not reproduce.
    FIT / VAL   net profit split 2013-2019 vs 2020-date. A winner that earns
           everything in one half is a period-specific fit, not a setting.

AND DO NOT STACK ALL THE WINNERS. Each group's best is conditional on every
other group sitting at its CURRENT value. Applying all eleven at once is a
different configuration that none of these grids tested -- use --stack to
actually measure it rather than assuming it adds up.

    python grid_all.py --run
    python grid_all.py --report
    python grid_all.py --stack
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

from broker import BrokerConfig                     # noqa: E402
from data import _normalise, _read_csv              # noqa: E402
from metrics import compute_metrics                 # noqa: E402
from strategy import Params, run_strategy           # noqa: E402

DATA = "xauusd_oanda_h4.csv"
CFG = "configs/gold_4h_stripped.json"
START = "2013-01-01"
SPLIT = "2020-01-01"
CAPITAL = 6000.0
OUT = "results/grid_all"


def ints(lo, hi, n):
    return sorted(set(np.linspace(lo, hi, n).round().astype(int).tolist()))


def floats(lo, hi, n):
    return [round(float(x), 3) for x in np.linspace(lo, hi, n)]


#: group -> (param_a, values_a, param_b, values_b, extra_overrides)
GROUPS: dict[str, tuple] = {
    "lsma":       ("lsma_length_long", ints(1, 40, 18),
                   "lsma_length_short", ints(1, 40, 18), {}),
    "ssma":       ("ssma_length_long", ints(1, 40, 18),
                   "ssma_length_short", ints(1, 40, 18),
                   {"use_sma_trigger_short": True}),
    "rsi_long":   ("rsi_length_long", ints(2, 30, 18),
                   "rsi_oversold", floats(20, 70, 18), {}),
    "rsi_short":  ("rsi_length_short", ints(2, 30, 18),
                   "rsi_overbought", floats(20, 70, 18), {}),
    "bb_long":    ("bb_period_long", ints(2, 60, 18),
                   "bb_stdev_long", floats(0.1, 3.0, 18), {}),
    "bb_short":   ("bb_period_short", ints(2, 60, 18),
                   "bb_stdev_short", floats(0.1, 3.0, 18), {}),
    "kc":         ("kc_length_l", ints(2, 40, 18),
                   "kc_length_s", ints(2, 40, 18), {}),
    "sqz_bb":     ("bb_length_l", ints(1, 30, 18),
                   "bb_length_s", ints(1, 30, 18), {}),
    "vals":       ("long_val", floats(-100, 50, 18),
                   "short_val", floats(-50, 100, 18), {}),
    "stop_long":  ("sl_percent_long", floats(0.5, 8.0, 18),
                   "limit_percent_long", floats(0.5, 8.0, 18), {}),
    "stop_short": ("sl_percent_short", floats(0.5, 8.0, 18),
                   "limit_percent_short", floats(0.5, 8.0, 18), {}),
}

_DF = _BASE = None


def _init() -> None:
    global _DF, _BASE
    if _DF is None:
        _DF = _normalise(_read_csv(DATA))[START:]
    if _BASE is None:
        _BASE = json.load(open(CFG))


def evaluate(overrides: dict) -> dict:
    _init()
    res = run_strategy(_DF, Params(**{**_BASE, **overrides}),
                       BrokerConfig(CAPITAL, 1.0))
    m = compute_metrics(res.equity, res.trades, CAPITAL)
    t, eq = res.trades, res.equity
    if len(t):
        fit = float(t[t["entry_time"] < SPLIT]["pnl"].sum()) / CAPITAL * 100
        val = float(t[t["entry_time"] >= SPLIT]["pnl"].sum()) / CAPITAL * 100
    else:
        fit = val = 0.0
    return {"net": 100 * (eq.iloc[-1] / CAPITAL - 1), "trades": m["trades"],
            "cagr": m["cagr_pct"], "sharpe": m["sharpe"],
            "maxdd": m["max_drawdown_pct"], "pf": m["profit_factor"],
            "fit": fit, "val": val}


def _cell(args):
    grp, a, av, b, bv = args
    pa, _, pb, _, extra = GROUPS[grp]
    r = evaluate({**extra, pa: av, pb: bv})
    r["a"], r["b"] = av, bv
    return r


def run(groups: list[str], workers: int) -> None:
    _init()
    os.makedirs(OUT, exist_ok=True)
    for grp in groups:
        path = f"{OUT}/{grp}.json"
        if os.path.exists(path):
            print(f"  {grp:<12} done, skipping")
            continue
        pa, avs, pb, bvs, _ = GROUPS[grp]
        tasks = [(grp, pa, av, pb, bv) for av in avs for bv in bvs]
        with mp.Pool(workers) as pool:
            rows = pool.map(_cell, tasks, chunksize=8)
        json.dump({"param_a": pa, "param_b": pb, "rows": rows}, open(path, "w"))
        best = max(rows, key=lambda x: x["net"])
        print(f"  {grp:<12} {len(rows):>4} cells   best {pa}={best['a']} "
              f"{pb}={best['b']}   net {best['net']:.1f}%", flush=True)


def _nbrs(rows, pa_vals, pb_vals, best) -> int:
    piv = {(r["a"], r["b"]): r["net"] for r in rows}
    ia, ib = pa_vals.index(best["a"]), pb_vals.index(best["b"])
    c = 0
    for da in (-1, 0, 1):
        for db in (-1, 0, 1):
            if da == 0 and db == 0:
                continue
            if 0 <= ia + da < len(pa_vals) and 0 <= ib + db < len(pb_vals):
                v = piv.get((pa_vals[ia + da], pb_vals[ib + db]))
                if v is not None and v >= 0.8 * best["net"]:
                    c += 1
    return c


def report() -> None:
    _init()
    base = evaluate({})
    print(f"\nALL ACTIVE PARAMETER GROUPS -- 4H gold {START} to date")
    print("=" * 104)
    print(f"  CURRENT SCRIPT: net {base['net']:.1f}%   trades {base['trades']}   "
          f"CAGR {base['cagr']:.2f}%   Sharpe {base['sharpe']:.2f}   "
          f"maxDD {base['maxdd']:.2f}%   PF {base['pf']:.2f}")
    print()
    print(f"  {'group':<12}{'best A':>14}{'best B':>14}{'net%':>9}{'gain':>8}"
          f"{'trades':>8}{'Sharpe':>8}{'maxDD%':>9}{'FIT%':>8}{'VAL%':>9}{'nbrs':>6}")
    print("  " + "-" * 100)
    out = {}
    for grp in GROUPS:
        path = f"{OUT}/{grp}.json"
        if not os.path.exists(path):
            print(f"  {grp:<12}  not run yet")
            continue
        d = json.load(open(path))
        rows = d["rows"]
        pa, avs, pb, bvs, _ = GROUPS[grp]
        best = max(rows, key=lambda x: x["net"])
        nb = _nbrs(rows, avs, bvs, best)
        flag = "" if nb >= 4 else ("  ISLAND" if nb <= 1 else "  thin")
        out[grp] = (pa, best["a"], pb, best["b"], best, nb)
        print(f"  {grp:<12}{str(best['a']):>14}{str(best['b']):>14}"
              f"{best['net']:>9.1f}{best['net']-base['net']:>+8.1f}"
              f"{best['trades']:>8}{best['sharpe']:>8.2f}{best['maxdd']:>9.2f}"
              f"{best['fit']:>8.1f}{best['val']:>9.1f}{nb:>6}{flag}")
    json.dump({k: {"param_a": v[0], "best_a": v[1], "param_b": v[2],
                   "best_b": v[3], "nbrs": v[5]} for k, v in out.items()},
              open(f"{OUT}/winners.json", "w"), indent=2, default=str)
    print(f"\n  wrote {OUT}/winners.json")
    print("  Each 'gain' is that group tuned ALONE, everything else left as-is.")
    print("  They do not add up -- run --stack to measure the combination.")


def stack() -> None:
    _init()
    w = json.load(open(f"{OUT}/winners.json"))
    base = evaluate({})
    print("\nSTACKING THE WINNERS -- do the gains survive together?")
    print("=" * 96)
    print(f"  {'configuration':<44}{'net%':>10}{'trades':>8}{'Sharpe':>8}"
          f"{'maxDD%':>9}{'FIT%':>8}{'VAL%':>9}")
    print("  " + "-" * 92)
    print(f"  {'current script':<44}{base['net']:>10.1f}{base['trades']:>8}"
          f"{base['sharpe']:>8.2f}{base['maxdd']:>9.2f}{base['fit']:>8.1f}{base['val']:>9.1f}")
    ov: dict = {}
    for grp, v in w.items():
        ov[v["param_a"]] = v["best_a"]
        ov[v["param_b"]] = v["best_b"]
        if grp == "ssma":
            ov["use_sma_trigger_short"] = True
        r = evaluate(ov)
        print(f"  {'+ ' + grp:<44}{r['net']:>10.1f}{r['trades']:>8}"
              f"{r['sharpe']:>8.2f}{r['maxdd']:>9.2f}{r['fit']:>8.1f}{r['val']:>9.1f}")
    print()
    print("  If the stacked total lands far below the sum of the individual")
    print("  gains, the groups interact and the per-group winners were each")
    print("  fitted against the others' ORIGINAL values.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--stack", action="store_true")
    ap.add_argument("--groups", default=None, help="comma list, default all")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    groups = ([g.strip() for g in a.groups.split(",")] if a.groups
              else list(GROUPS))
    if a.run:
        run(groups, a.workers)
    if a.report:
        report()
    if a.stack:
        stack()
    if not (a.run or a.report or a.stack):
        report()


if __name__ == "__main__":
    main()
