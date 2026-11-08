#!/usr/bin/env python3
"""Brute-force every SSMAlengthL x SSMAlengthS pair, ranked by net profit.

The SSMA leg is the `(SSMAS < SSMAL)` condition on the SHORT entry. In the
current script it is commented out of shortSignal, so this grid answers: if you
switch it back on, which lengths pay best, and is the answer stable?

    SSMAL = ta.sma(close, SSMAlengthL)     <- the "L" axis
    SSMAS = ta.sma(close, SSMAlengthS)     <- the "S" axis
    condition: SSMAS < SSMAL

Note the naming is inverted from what you would expect: with L=3 and S=13 the
condition is sma(13) < sma(3), i.e. the SLOWER average below the FASTER one --
a momentum-down state. The grid covers both sides of the diagonal, so pairs
where S < L (the opposite state) are included too.

WHAT IT PRINTS

Ranked by net profit %, because that is the objective asked for. Alongside each
winner it also shows:

    neighbours  -- how many of the 8 adjacent (L,S) cells are within 20% of it.
                   A genuine setting sits in a cluster; a fitted one is an
                   island. This is the single most useful column here, because
                   a 60x60 grid contains 3,600 chances for noise to produce a
                   spectacular number.
    FIT / VAL   -- profit split 2013-2019 vs 2020-date. Fitting on the whole
                   span and reading only the total hides which half paid.

Resumable: each row of the grid is checkpointed, so it can be run in chunks.

    python grid_ssma.py --run --max-len 60
    python grid_ssma.py --report
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
SPLIT = "2020-01-01"          # fit / validation boundary, for the diagnostic only
CAPITAL = 6000.0
OUT = "results/grid_ssma"

_DF = _BASE = None


def _init() -> None:
    global _DF, _BASE
    if _DF is None:
        _DF = _normalise(_read_csv(DATA))[START:]
    if _BASE is None:
        _BASE = json.load(open(CFG))


def evaluate(overrides: dict) -> dict:
    _init()
    p = Params(**{**_BASE, **overrides})
    res = run_strategy(_DF, p, BrokerConfig(CAPITAL, 1.0))
    m = compute_metrics(res.equity, res.trades, CAPITAL)
    t = res.trades
    eq = res.equity
    net = 100 * (eq.iloc[-1] / CAPITAL - 1)
    if len(t):
        pre = t[t["entry_time"] < SPLIT]
        post = t[t["entry_time"] >= SPLIT]
        fit = float(pre["pnl"].sum()) / CAPITAL * 100
        val = float(post["pnl"].sum()) / CAPITAL * 100
    else:
        fit = val = 0.0
    return {"net": net, "trades": m["trades"],
            "shorts": int((t["direction"] == -1).sum()) if len(t) else 0,
            "cagr": m["cagr_pct"], "sharpe": m["sharpe"],
            "maxdd": m["max_drawdown_pct"], "pf": m["profit_factor"],
            "fit": fit, "val": val}


def _cell(args):
    L, S = args
    r = evaluate({"use_sma_trigger_short": True,
                  "ssma_length_long": L, "ssma_length_short": S})
    r["L"], r["S"] = L, S
    return r


def run(max_len: int, workers: int) -> None:
    _init()
    os.makedirs(OUT, exist_ok=True)
    for L in range(1, max_len + 1):
        path = f"{OUT}/row_{L:03d}.json"
        if os.path.exists(path):
            continue
        with mp.Pool(workers) as pool:
            rows = pool.map(_cell, [(L, S) for S in range(1, max_len + 1)])
        json.dump(rows, open(path, "w"))
        best = max(rows, key=lambda x: x["net"])
        print(f"  L={L:>3}  best S={best['S']:>3}  net {best['net']:>8.1f}%  "
              f"trades {best['trades']:>4}", flush=True)


def report(max_len: int, top: int) -> None:
    _init()
    rows = []
    for L in range(1, max_len + 1):
        path = f"{OUT}/row_{L:03d}.json"
        if os.path.exists(path):
            rows += json.load(open(path))
    if not rows:
        raise SystemExit("nothing computed yet -- run with --run")
    g = pd.DataFrame(rows)
    g.to_csv(f"{OUT}/grid.csv", index=False)

    base = evaluate({"use_sma_trigger_short": False})
    print(f"\nGRID: {len(g):,} combinations, 4H gold {START} to date")
    print("=" * 100)
    print(f"  BASELINE (SSMA filter OFF, your current script)")
    print(f"    net {base['net']:.1f}%   trades {base['trades']}   "
          f"CAGR {base['cagr']:.2f}%   Sharpe {base['sharpe']:.2f}   "
          f"maxDD {base['maxdd']:.2f}%   PF {base['pf']:.2f}")

    # neighbour count: how many of the 8 adjacent cells are within 20%
    piv = g.pivot(index="L", columns="S", values="net")
    def neighbours(L, S, net):
        c = 0
        for dl in (-1, 0, 1):
            for ds in (-1, 0, 1):
                if dl == 0 and ds == 0:
                    continue
                try:
                    v = piv.loc[L + dl, S + ds]
                except KeyError:
                    continue
                if np.isfinite(v) and v >= 0.8 * net:
                    c += 1
        return c

    g = g.sort_values("net", ascending=False)
    print(f"\n  TOP {top} BY NET PROFIT")
    print(f"  {'L':>4}{'S':>5}{'net%':>10}{'trades':>8}{'shorts':>8}{'CAGR%':>8}"
          f"{'Sharpe':>8}{'maxDD%':>9}{'PF':>7}{'FIT%':>9}{'VAL%':>9}{'nbrs':>6}")
    print("  " + "-" * 96)
    for _, x in g.head(top).iterrows():
        nb = neighbours(int(x["L"]), int(x["S"]), x["net"])
        flag = "" if nb >= 4 else ("   ISLAND" if nb <= 1 else "   thin")
        print(f"  {int(x['L']):>4}{int(x['S']):>5}{x['net']:>10.1f}"
              f"{int(x['trades']):>8}{int(x['shorts']):>8}{x['cagr']:>8.2f}"
              f"{x['sharpe']:>8.2f}{x['maxdd']:>9.2f}{x['pf']:>7.2f}"
              f"{x['fit']:>9.1f}{x['val']:>9.1f}{nb:>6}{flag}")

    beat = g[g["net"] > base["net"]]
    print(f"\n  combinations beating the filter-OFF baseline: "
          f"{len(beat):,} / {len(g):,}  ({100*len(beat)/len(g):.1f}%)")
    b = g.iloc[0]
    nb = neighbours(int(b["L"]), int(b["S"]), b["net"])
    print(f"  best cell L={int(b['L'])} S={int(b['S'])} has {nb}/8 neighbours "
          f"within 20% -> {'CLUSTER, plausible' if nb >= 4 else 'ISLAND, likely noise'}")
    print(f"\n  If a large share of the grid beats the baseline, the filter helps")
    print(f"  broadly and the exact lengths matter little. If only a handful do,")
    print(f"  the winners are the 3,600 lottery tickets paying out.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--max-len", type=int, default=60)
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    if a.run:
        run(a.max_len, a.workers)
    if a.report or not a.run:
        report(a.max_len, a.top)


if __name__ == "__main__":
    main()
