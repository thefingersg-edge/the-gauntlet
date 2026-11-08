#!/usr/bin/env python3
"""Switch each commented-out filter on, OPTIMISE its own parameters, keep what helps.

Difference from the first version: each filter is no longer tested at whatever
values happened to be sitting in the commented-out line. Its own parameters are
searched first, so a filter fails only if it cannot help at ANY setting -- not
because it was left badly tuned.

SEARCH OBJECTIVE

Profit factor, subject to a trade-count floor. PF is the right target for a
selection question because it rewards both winning more often and losing less
when wrong, which is what a filter is for. The floor matters: without it the
optimiser's best move is a filter that takes twelve trades.

    floor = 40% of the baseline trade count

ACCEPTANCE RULE, FIXED BEFORE RUNNING

A filter is KEPT if its best version improves BOTH:

    win rate      -- % of trades closing profitable
    profit factor -- gross win / gross loss

Net profit is reported but does NOT decide. A filter trading less often and
winning more often is doing its job even if the total falls.

Order, each applied on top of whatever was kept:

    1. ADX        adx_len/smooth/threshold, long and short      6 params
    2. VOL GATE   atr and averaging length, long and short      4 params
    3. FRED       rate_sma_days                                 1 param

    python filter_ladder.py --optimise --samples 400
    python filter_ladder.py --optimise --base configs/grid_groups_best.json
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
import fetch_fred                                   # noqa: E402

DATA = "xauusd_oanda_h4.csv"
START = "2013-01-01"
CAPITAL = 6000.0
OUT = "results/filter_ladder_wide"

#: name -> (fixed switches, [(param, lo, hi, is_int)])
STEPS = [
    # WIDENED. The first pass put every vol-gate optimum against the top of its
    # range (atr_long=40 of 40, atr_short=76 of 80, vol_long=74 of 90), which
    # means the search wanted to keep going and the ceiling was the answer, not
    # the data. Ranges roughly quadrupled; ADX and FRED widened to match.
    ("1. ADX trend",
     {"use_adx_filter": True, "use_adx_filter_short": True},
     [("adx_len", 2, 150, True), ("adx_smooth", 1, 200, True),
      ("adx_threshold", 1.0, 60.0, False),
      ("adx_len_short", 2, 200, True), ("adx_smooth_short", 1, 150, True),
      ("adx_threshold_short", 1.0, 60.0, False)]),
    ("2. volatility gate",
     {"use_volatility_filter": True, "use_volatility_filter_short": True},
     [("atr_long", 2, 200, True), ("vol_long", 5, 400, True),
      ("atr_short", 2, 300, True), ("vol_short", 5, 400, True)]),
    ("3. FRED real yield",
     {"use_macro_filter": True, "rate_filter_mode": "replace"},
     [("rate_sma_days", 2, 500, True)]),
]

_DF = _RATES = None


def _init() -> None:
    global _DF, _RATES
    if _DF is None:
        _DF = _normalise(_read_csv(DATA))[START:]
    if _RATES is None and os.path.exists("dfii10.csv"):
        _RATES = fetch_fred.load_daily_series("dfii10.csv")


def evaluate(cfg: dict) -> dict:
    _init()
    res = run_strategy(_DF, Params(**cfg), BrokerConfig(CAPITAL, 1.0),
                       rates=_RATES)
    m = compute_metrics(res.equity, res.trades, CAPITAL)
    t = res.trades
    wins = int((t["pnl"] > 0).sum()) if len(t) else 0
    ret = (t["pnl"] / (t["entry_price"] * t["qty"])) if len(t) else pd.Series(dtype=float)
    return {"net": 100 * (res.equity.iloc[-1] / CAPITAL - 1),
            "trades": m["trades"], "wins": wins,
            "winrate": m["win_rate_pct"], "pf": m["profit_factor"],
            "avg_trade": 100 * float(ret.mean()) if len(ret) else np.nan,
            "sharpe": m["sharpe"], "maxdd": m["max_drawdown_pct"]}


def _trial(args):
    seed, cur, fixed, spec, floor = args
    _init()
    rng = np.random.default_rng(seed)
    cand = {n: (int(rng.integers(lo, hi + 1)) if i else float(rng.uniform(lo, hi)))
            for n, lo, hi, i in spec}
    r = evaluate({**cur, **fixed, **cand})
    if r["trades"] < floor or not np.isfinite(r["pf"]):
        return cand, r, -np.inf
    return cand, r, r["pf"]


def optimise_step(cur: dict, fixed: dict, spec: list, floor: int,
                  samples: int, seed: int, workers: int):
    rng = np.random.default_rng(seed)
    tasks = [(int(rng.integers(0, 2**31)), cur, fixed, spec, floor)
             for _ in range(samples)]
    with mp.Pool(workers) as pool:
        got = pool.map(_trial, tasks, chunksize=8)
    best = max(got, key=lambda x: x[2])
    return best[0], best[1], best[2]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="configs/gold_4h_stripped.json")
    ap.add_argument("--optimise", action="store_true")
    ap.add_argument("--samples", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()

    _init()
    os.makedirs(OUT, exist_ok=True)
    tag = os.path.basename(a.base).replace(".json", "")
    state_path = f"{OUT}/{tag}_state.json"
    if os.path.exists(state_path):
        st = json.load(open(state_path))
        cur, done, kept = st["cur"], st["done"], st["kept"]
    else:
        cur, done, kept = json.load(open(a.base)), [], []

    base = evaluate(json.load(open(a.base)))
    prev = evaluate(cur)
    floor = int(0.4 * base["trades"])

    if not done:
        print(f"\nFILTER LADDER (each filter's parameters optimised) -- 4H gold {START}+")
        print(f"  base: {tag}   search: PF, floor {floor} trades   "
              f"keep rule: win% AND PF must both improve")
        print("=" * 108)
        print(f"  {'step':<24}{'trades':>8}{'wins':>7}{'win%':>8}{'PF':>7}"
              f"{'avg trade%':>12}{'net%':>9}{'Sharpe':>8}{'maxDD%':>9}  decision")
        print("  " + "-" * 104)
        print(f"  {'0. baseline (all off)':<24}{base['trades']:>8}{base['wins']:>7}"
              f"{base['winrate']:>8.1f}{base['pf']:>7.2f}{base['avg_trade']:>12.3f}"
              f"{base['net']:>9.1f}{base['sharpe']:>8.2f}{base['maxdd']:>9.2f}")

    for name, fixed, spec in STEPS:
        if name in done:
            continue
        cand, r, score = optimise_step(cur, fixed, spec, floor, a.samples,
                                       a.seed + hash(name) % 9973, a.workers)
        better = (r["winrate"] > prev["winrate"]) and (r["pf"] > prev["pf"])
        if better:
            cur = {**cur, **fixed, **cand}
            prev = r
            kept.append(name)
            note = "KEEP"
        else:
            why = []
            if r["winrate"] <= prev["winrate"]:
                why.append(f"win% {r['winrate']:.1f}<={prev['winrate']:.1f}")
            if r["pf"] <= prev["pf"]:
                why.append(f"PF {r['pf']:.2f}<={prev['pf']:.2f}")
            note = "revert (" + ", ".join(why) + ")"
        done.append(name)
        json.dump({"cur": cur, "done": done, "kept": kept},
                  open(state_path, "w"), indent=2, default=str)
        print(f"  {name:<24}{r['trades']:>8}{r['wins']:>7}{r['winrate']:>8.1f}"
              f"{r['pf']:>7.2f}{r['avg_trade']:>12.3f}{r['net']:>9.1f}"
              f"{r['sharpe']:>8.2f}{r['maxdd']:>9.2f}  {note}", flush=True)
        print(f"      best params: "
              + ", ".join(f"{k}="
                          + (f"{v:.2f}" if isinstance(v, float) else str(v))
                          for k, v in cand.items()))

    if len(done) == len(STEPS):
        print()
        print(f"  KEPT: {', '.join(kept) if kept else 'none -- all reverted'}")
        print(f"  FINAL vs BASELINE")
        print(f"    win rate      {base['winrate']:>7.1f}%  ->  {prev['winrate']:>7.1f}%")
        print(f"    profit factor {base['pf']:>7.2f}   ->  {prev['pf']:>7.2f}")
        print(f"    avg trade     {base['avg_trade']:>7.3f}%  ->  {prev['avg_trade']:>7.3f}%")
        print(f"    trades        {base['trades']:>7}   ->  {prev['trades']:>7}")
        print(f"    net profit    {base['net']:>7.1f}%  ->  {prev['net']:>7.1f}%")
        out = f"configs/{tag}_filtered.json"
        json.dump(cur, open(out, "w"), indent=2, default=str)
        print(f"\n  wrote {out}")


if __name__ == "__main__":
    main()
