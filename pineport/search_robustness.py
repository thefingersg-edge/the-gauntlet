#!/usr/bin/env python3
"""Is the greedy sequential search the problem, or is the strategy?

THE QUESTION THIS ANSWERS

`train_tf.py` optimises one group at a time, each conditioned on the groups
already fixed: sma, then rsi, then squeeze, then bands, then stops, then
ladder. That is greedy. It is order-dependent, it cannot escape a local
optimum, and two passes only partly help. A reasonable worry is that the whole
project has been walking down one arbitrary corridor.

THE TRAP IN THAT WORRY

The obvious test -- "does a better search find a better in-sample result?" --
answers the wrong question. A better search will ALWAYS find a better in-sample
result; that is what "better search" means. If in-sample quality is bought by
fitting noise, a better optimiser buys more noise.

So this measures the thing that actually matters:

    ACROSS SEARCH METHODS, DOES BETTER IN-SAMPLE PREDICT BETTER OUT-OF-SAMPLE?

    strong positive correlation  -> the search IS the constraint. Better
                                    optimisation yields genuinely better
                                    strategies and is worth building.
    flat or negative             -> the search is NOT the constraint. Every
                                    method finds a different way to fit the
                                    same training window, and none of them
                                    generalises. The strategy is the problem.

VARIANTS COMPARED, all on identical data and identical budget:

    greedy seed 0/1/2   same algorithm, different random draws
    greedy reversed     ORDER reversed -- tests order-dependence directly
    greedy shuffled     a third order
    joint               NO grouping: every parameter sampled at once, same
                        total number of evaluations. Higher-dimensional and
                        less efficient per sample, but structurally unbiased.

Six points is few, so this reports the correlation AND the raw table; a
correlation from six points is a hint, not a proof. The raw spread is often
more informative than the coefficient.

    python search_robustness.py --samples 150
    python search_robustness.py --samples 400 --workers 7
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import train_tf as T                                  # noqa: E402
from broker import BrokerConfig                       # noqa: E402
from data import _normalise, _read_csv                # noqa: E402
from metrics import compute_metrics                   # noqa: E402
from strategy import Params, run_strategy             # noqa: E402
import fetch_fred                                     # noqa: E402

CSV = "xauusd_oanda_h4.csv"
TRAIN = ("2009-04-01", "2023-08-31")
OOS = [("2006-03 .. 2009-03", "2006-01-01", "2009-03-31"),
       ("2023-09 .. 2026-08", "2023-09-01", "2026-12-31")]
CAPITAL = 6000.0
OUT = "results/search_robustness"


def oos_eval(cfg: dict, s: str, e: str, slip: float) -> dict:
    """Score a config on a window it was never trained on."""
    df = _normalise(_read_csv(CSV))[s:e]
    rates = (fetch_fred.load_daily_series("dfii10.csv")
             if os.path.exists("dfii10.csv") else None)
    r = run_strategy(df, Params(**cfg),
                     BrokerConfig(CAPITAL, 1.0, slippage_points=slip), rates=rates)
    m = compute_metrics(r.equity, r.trades, CAPITAL)
    return {"trades": m["trades"], "pf": m["profit_factor"],
            "sharpe": m["sharpe"], "cagr": m["cagr_pct"],
            "net": 100 * (r.equity.iloc[-1] / CAPITAL - 1),
            "maxdd": m["max_drawdown_pct"]}


def run_greedy(order: list, seed: int, samples: int, workers: int,
               floor: int, obj: str, slip: float) -> dict:
    cur = json.load(open(T.BASE_CFG))
    for g in order:
        spec, fixed = T.GROUPS[g]
        cand, r, score = T.search(cur, fixed, T.scaled(spec), floor, samples,
                                  seed + hash(g) % 9973, workers, obj, slip)
        prev = T.evaluate(cur, slippage=slip)[obj]
        if np.isfinite(score) and (not np.isfinite(prev) or r[obj] > prev):
            cur = {**cur, **fixed, **cand}
    return cur


def run_joint(seed: int, samples: int, workers: int, floor: int,
              obj: str, slip: float) -> dict:
    """Every parameter at once, same total evaluation budget.

    Pooling the specs means `fixed` switches from all groups apply together,
    which is the point: no group is conditioned on another's result.
    """
    spec, fixed = [], {}
    for g in T.ORDER:
        s, f = T.GROUPS[g]
        spec.extend(s)
        fixed.update(f)
    cur = json.load(open(T.BASE_CFG))
    budget = samples * len(T.ORDER)
    cand, r, score = T.search(cur, fixed, T.scaled(spec), floor, budget,
                              seed, workers, obj, slip)
    return {**cur, **fixed, **cand} if np.isfinite(score) else cur


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--samples", type=int, default=150)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 1))
    ap.add_argument("--slippage", type=float, default=0.25)
    ap.add_argument("--objective", default="calmar")
    a = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    T._MAXLEN, T._TF = 25_000, "H4"
    df = T._init(CSV, TRAIN[0], 1.0, 1.0, TRAIN[1])
    base = T.evaluate(json.load(open(T.BASE_CFG)), slippage=a.slippage)
    floor = T.trade_floor(base["trades"], 0.6, len(df), "H4", min_abs=30)

    print(f"\nSEARCH ROBUSTNESS   {len(df):,} bars   "
          f"{df.index[0].date()} -> {df.index[-1].date()}")
    print(f"  objective {a.objective}, slippage {a.slippage}, floor {floor} trades, "
          f"{a.samples} samples/group, {a.workers} workers")
    print("=" * 112)

    rev = list(reversed(T.ORDER))
    shuf = ["stops", "bands", "sma", "ladder", "squeeze", "rsi"]
    VARIANTS = [
        ("greedy seed 0", lambda: run_greedy(T.ORDER, 0, a.samples, a.workers, floor, a.objective, a.slippage)),
        ("greedy seed 1", lambda: run_greedy(T.ORDER, 1, a.samples, a.workers, floor, a.objective, a.slippage)),
        ("greedy seed 2", lambda: run_greedy(T.ORDER, 2, a.samples, a.workers, floor, a.objective, a.slippage)),
        ("greedy reversed", lambda: run_greedy(rev, 0, a.samples, a.workers, floor, a.objective, a.slippage)),
        ("greedy shuffled", lambda: run_greedy(shuf, 0, a.samples, a.workers, floor, a.objective, a.slippage)),
        ("joint (no groups)", lambda: run_joint(0, a.samples, a.workers, floor, a.objective, a.slippage)),
    ]

    hdr = f"  {'variant':<20}{'IS trades':>10}{'IS PF':>8}{'IS Sharpe':>10}{'IS net%':>9}"
    for nm, _, _ in OOS:
        hdr += f"{nm.split(' ')[0][:7] + ' PF':>12}"
    print(hdr + f"{'time':>8}")
    print("  " + "-" * 108)

    # Checkpoint key MUST include the settings, not just the variant name. An
    # earlier version keyed on name alone and silently resumed a 120-sample
    # result into a 150-sample run -- which is worse than no checkpoint at all,
    # because comparing search METHODS is only meaningful at equal budget, and
    # the mismatch is invisible in the output table.
    fp, settings = T.settings_fingerprint(a, extra={"_floor": floor,
                                                    "_train": TRAIN})
    stamp = (f"s{a.samples}_o{a.objective}_sl{a.slippage:g}"
             f"_f{floor}_{TRAIN[0]}_{TRAIN[1]}_{fp}")
    T.guard_settings(OUT, settings)

    rows = []
    for name, fn in VARIANTS:
        slug = name.replace(" ", "_").replace("(", "").replace(")", "")
        path = f"{OUT}/{slug}__{stamp}.json"
        t0 = time.time()
        if os.path.exists(path):
            rec = json.load(open(path))
        else:
            cfg = fn()
            ins = T.evaluate(cfg, slippage=a.slippage)
            rec = {"name": name, "cfg": cfg,
                   "is_pf": ins["pf"], "is_sharpe": ins["sharpe"],
                   "is_net": ins["net"], "is_trades": ins["trades"],
                   "oos": [oos_eval(cfg, s, e, a.slippage) for _, s, e in OOS]}
            json.dump(rec, open(path, "w"), indent=2, default=str)
        line = (f"  {name:<20}{rec['is_trades']:>10}{rec['is_pf']:>8.2f}"
                f"{rec['is_sharpe']:>10.2f}{rec['is_net']:>9.1f}")
        for o in rec["oos"]:
            line += f"{o['pf']:>12.2f}"
        print(line + f"{time.time() - t0:>7.0f}s", flush=True)
        rows.append(rec)

    r = pd.DataFrame([{"name": x["name"], "is_pf": x["is_pf"],
                       "is_sharpe": x["is_sharpe"],
                       **{f"oos{i}_pf": x["oos"][i]["pf"] for i in range(len(OOS))},
                       **{f"oos{i}_sharpe": x["oos"][i]["sharpe"] for i in range(len(OOS))}}
                      for x in rows])
    r["oos_mean_pf"] = r[[f"oos{i}_pf" for i in range(len(OOS))]].mean(axis=1)
    r.to_csv(f"{OUT}/summary.csv", index=False)

    print("\n  DOES BETTER IN-SAMPLE PREDICT BETTER OUT-OF-SAMPLE?")
    print("  " + "=" * 108)
    print(f"  in-sample PF spread : {r['is_pf'].min():.2f} to {r['is_pf'].max():.2f}")
    print(f"  OOS mean PF spread  : {r['oos_mean_pf'].min():.2f} to {r['oos_mean_pf'].max():.2f}")
    if r["is_pf"].std() > 1e-9 and r["oos_mean_pf"].std() > 1e-9:
        c = r["is_pf"].corr(r["oos_mean_pf"])
        n = len(r)
        # A correlation from six points is almost uninformative, so report the
        # interval rather than the point estimate. An earlier version of this
        # branched on the SIGN of c and called -0.18 "actively harmful"; with
        # n=6 that CI spans roughly -0.86 to +0.74, so the sign carries no
        # information at all. Claiming a direction from it would be exactly the
        # over-reading this whole script exists to catch.
        lo = hi = np.nan
        if n > 3 and abs(c) < 1:
            z, se = np.arctanh(c), 1 / np.sqrt(n - 3)
            lo, hi = np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)
        print(f"  correlation(IS PF, OOS PF) over {n} search methods = {c:+.2f}"
              + (f"   95% CI ({lo:+.2f}, {hi:+.2f})" if np.isfinite(lo) else ""))

        # The primary evidence, because it needs no correlation at all: if
        # re-running the SAME algorithm with a different random seed moves the
        # out-of-sample result as much as switching algorithm does, then the
        # search method is not what determines the outcome -- the draw is.
        seeds = r[r["name"].str.startswith("greedy seed")]["oos_mean_pf"]
        sd_seed = seeds.std(ddof=1) if len(seeds) > 2 else np.nan
        sd_all = r["oos_mean_pf"].std(ddof=1)
        if np.isfinite(sd_seed):
            print(f"  OOS spread from SEED ALONE (same algorithm) : "
                  f"sd {sd_seed:.3f}  [{seeds.min():.2f} to {seeds.max():.2f}]")
            print(f"  OOS spread across ALL {n} METHODS            : "
                  f"sd {sd_all:.3f}")
            print(f"    ratio {sd_seed / sd_all:.2f}x")

        decisive = np.isfinite(lo) and (lo > 0 or hi < 0)
        if decisive and c > 0:
            v = ("SEARCH IS THE CONSTRAINT. Better optimisation carries over; "
                 "building a stronger optimiser is worth it.")
        elif decisive:
            v = ("BETTER IN-SAMPLE FITS GENERALISE WORSE -- and the interval "
                 "excludes zero, so this is a real inversion. Stop optimising.")
        elif np.isfinite(sd_seed) and sd_seed >= sd_all:
            v = ("SEARCH IS NOT THE CONSTRAINT. The random seed moves the "
                 "out-of-sample result as much as the search METHOD does, so "
                 "outcome is dominated by which draw the search happened to "
                 "land on. A better optimiser would not have helped.")
        else:
            v = ("INCONCLUSIVE at this sample size. The correlation interval "
                 "includes zero and the seed spread does not dominate; add "
                 "variants or folds before concluding anything.")
        print(f"\n  VERDICT: {v}")
    best_is = r.loc[r["is_pf"].idxmax()]
    best_oos = r.loc[r["oos_mean_pf"].idxmax()]
    print(f"\n  best in-sample : {best_is['name']:<20} IS PF {best_is['is_pf']:.2f}"
          f"  ->  OOS PF {best_is['oos_mean_pf']:.2f}")
    print(f"  best OOS       : {best_oos['name']:<20} IS PF {best_oos['is_pf']:.2f}"
          f"  ->  OOS PF {best_oos['oos_mean_pf']:.2f}")
    print(f"\n  wrote {OUT}/summary.csv\n")


if __name__ == "__main__":
    main()
