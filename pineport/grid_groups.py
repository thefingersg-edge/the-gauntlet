#!/usr/bin/env python3
"""Sequential group optimisation: tune a whole group jointly, apply it, move on.

Groups are defined by what actually interacts. A Bollinger period means nothing
without its stdev; a squeeze needs its BB lengths, KC lengths, multiplier AND
the momentum thresholds together, because changing one shifts what the others
should be. Tuning them one pair at a time (as grid_all.py does) finds each
parameter's best against the others' CURRENT values, which is why stacking
those winners gained almost nothing.

    sma       LSMAlengthL/S + SSMAlengthL/S        4 params
    rsi       RSIlengthL/S + overSold/overBought   4 params
    squeeze   BB lengths + KC lengths + multKC
              + longVal + shortVal                 7 params
    bands     BBlengthL/multL + BBlengthS/multS    4 params
    stops     SL/Limit/RR for long and short       6 params

METHOD

Exhaustive grids are impossible past two dimensions (the squeeze group is 15^7
= 170 million combinations), so each group gets a dense random search over its
own ranges. With enough draws this converges on the same answer a grid would
reach, and unlike a grid it spends no budget on axes that do not matter.

The winner of each group is APPLIED before the next group is searched, so every
later group is tuned against the improved configuration rather than the
original. Passes repeat until nothing improves.

WHAT TO WATCH

    order dependence -- greedy sequential search depends on the order groups
        are visited. Pass 2 re-searches every group against the pass-1 result;
        if the config keeps moving, the surface is flat and the "optimum" is
        arbitrary.
    FIT / VAL -- net profit 2013-2019 vs 2020-date. A configuration earning
        everything in one half is fitted to that half.
    trades -- if the count collapses as groups are applied, the search is
        buying its gains by trading less, which will not survive costs.

    python grid_groups.py --run --samples 600
    python grid_groups.py --report
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
OUT = "results/grid_groups"

#: group -> list of (param, lo, hi, is_int); plus any fixed overrides
GROUPS: dict[str, tuple[list, dict]] = {
    "sma": ([("lsma_length_long", 1, 60, True),
             ("lsma_length_short", 1, 60, True),
             ("ssma_length_long", 1, 60, True),
             ("ssma_length_short", 1, 60, True)],
            {"use_sma_trigger_short": True}),
    "rsi": ([("rsi_length_long", 2, 40, True),
             ("rsi_oversold", 15.0, 75.0, False),
             ("rsi_length_short", 2, 40, True),
             ("rsi_overbought", 15.0, 75.0, False)], {}),
    "squeeze": ([("bb_length_l", 1, 40, True),
                 ("bb_length_s", 1, 40, True),
                 ("kc_length_l", 2, 50, True),
                 ("kc_length_s", 2, 50, True),
                 ("kc_mult", 1.0, 4.0, False),
                 ("long_val", -120.0, 60.0, False),
                 ("short_val", -60.0, 120.0, False)], {}),
    "bands": ([("bb_period_long", 2, 80, True),
               ("bb_stdev_long", 0.1, 3.5, False),
               ("bb_period_short", 2, 80, True),
               ("bb_stdev_short", 0.1, 3.5, False)], {}),
    "stops": ([("sl_percent_long", 0.5, 10.0, False),
               ("limit_percent_long", 0.5, 10.0, False),
               ("r_ratio_long", 0.5, 6.0, False),
               ("sl_percent_short", 0.5, 10.0, False),
               ("limit_percent_short", 0.5, 10.0, False),
               ("r_ratio_short", 0.5, 6.0, False)], {}),
}
ORDER = ["sma", "rsi", "squeeze", "bands", "stops"]

_DF = _CUR = None


def _init(cur: dict | None = None) -> None:
    global _DF, _CUR
    if _DF is None:
        _DF = _normalise(_read_csv(DATA))[START:]
    if cur is not None:
        _CUR = cur


def evaluate(cfg: dict) -> dict:
    _init()
    res = run_strategy(_DF, Params(**cfg), BrokerConfig(CAPITAL, 1.0))
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


def sample(spec: list, rng) -> dict:
    out = {}
    for name, lo, hi, is_int in spec:
        out[name] = (int(rng.integers(lo, hi + 1)) if is_int
                     else float(rng.uniform(lo, hi)))
    return out


def _trial(args):
    seed, grp, cur = args
    _init()
    spec, fixed = GROUPS[grp]
    rng = np.random.default_rng(seed)
    cand = sample(spec, rng)
    r = evaluate({**cur, **fixed, **cand})
    return cand, r


def search_group(grp: str, cur: dict, samples: int, seed: int,
                 workers: int) -> tuple[dict, dict]:
    spec, fixed = GROUPS[grp]
    rng = np.random.default_rng(seed)
    tasks = [(int(rng.integers(0, 2**31)), grp, cur) for _ in range(samples)]
    with mp.Pool(workers) as pool:
        got = pool.map(_trial, tasks, chunksize=8)
    # Keep the current setting in the running: a group that cannot beat where
    # it already is should not be moved.
    base = evaluate({**cur, **fixed})
    best_cand, best = {}, base
    for cand, r in got:
        if r["net"] > best["net"]:
            best_cand, best = cand, r
    return {**fixed, **best_cand}, best


def run(samples: int, passes: int, seed: int, workers: int) -> None:
    _init()
    os.makedirs(OUT, exist_ok=True)
    state_path = f"{OUT}/state.json"
    if os.path.exists(state_path):
        st = json.load(open(state_path))
        cur, log = st["cur"], st["log"]
    else:
        cur, log = json.load(open(CFG)), []

    start = evaluate(cur)
    if not log:
        print(f"  {'start':<26}{start['net']:>9.1f}%{start['trades']:>8} trades"
              f"{start['sharpe']:>8.2f}")
        log.append({"step": "start", **start})

    done = {(e["step"]) for e in log}
    for p in range(1, passes + 1):
        for grp in ORDER:
            key = f"pass{p}:{grp}"
            if key in done:
                continue
            winner, r = search_group(grp, cur, samples,
                                     seed + 1000 * p + hash(grp) % 997, workers)
            prev = evaluate(cur)["net"]
            moved = r["net"] > prev + 1e-9
            if moved:
                cur = {**cur, **winner}
            log.append({"step": key, "moved": bool(moved),
                        "params": {k: v for k, v in winner.items()
                                   if not isinstance(v, bool)}, **r})
            json.dump({"cur": cur, "log": log}, open(state_path, "w"),
                      indent=2, default=str)
            print(f"  {key:<26}{r['net']:>9.1f}%{r['trades']:>8} trades"
                  f"{r['sharpe']:>8.2f}   {'applied' if moved else 'kept current'}",
                  flush=True)
    json.dump(cur, open(f"{OUT}/best_config.json", "w"), indent=2, default=str)


def report() -> None:
    _init()
    st = json.load(open(f"{OUT}/state.json"))
    cur, log = st["cur"], st["log"]
    base = json.load(open(CFG))
    print("\nSEQUENTIAL GROUP OPTIMISATION -- 4H gold "
          f"{START} to date")
    print("=" * 100)
    print(f"  {'step':<26}{'net%':>10}{'trades':>8}{'Sharpe':>8}{'maxDD%':>9}"
          f"{'FIT%':>8}{'VAL%':>9}  status")
    print("  " + "-" * 96)
    for e in log:
        status = "" if e["step"] == "start" else (
            "applied" if e.get("moved") else "kept current")
        print(f"  {e['step']:<26}{e['net']:>10.1f}{e['trades']:>8}"
              f"{e['sharpe']:>8.2f}{e['maxdd']:>9.2f}{e['fit']:>8.1f}"
              f"{e['val']:>9.1f}  {status}")

    b, f = evaluate(cur), evaluate(base)
    print(f"\n  START : net {f['net']:.1f}%  Sharpe {f['sharpe']:.2f}  "
          f"maxDD {f['maxdd']:.2f}%  trades {f['trades']}")
    print(f"  FINAL : net {b['net']:.1f}%  Sharpe {b['sharpe']:.2f}  "
          f"maxDD {b['maxdd']:.2f}%  trades {b['trades']}")
    print("\n  CHANGED PARAMETERS")
    for k in sorted(cur):
        if k in base and cur[k] != base[k]:
            a, c = base[k], cur[k]
            fa = f"{a:.3f}" if isinstance(a, float) else str(a)
            fc = f"{c:.3f}" if isinstance(c, float) else str(c)
            print(f"    {k:<26}{fa:>12}  ->  {fc:>12}")
    moved = sum(1 for e in log if e.get("moved"))
    print(f"\n  groups that moved: {moved} of {len(log)-1}")
    print(f"  wrote {OUT}/best_config.json")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--samples", type=int, default=600)
    ap.add_argument("--passes", type=int, default=2)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    if a.run:
        run(a.samples, a.passes, a.seed, a.workers)
    if a.report or not a.run:
        report()


if __name__ == "__main__":
    main()
