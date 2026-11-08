#!/usr/bin/env python3
"""Stage-at-a-time training with seed consensus and an inner validation split.

WHY NOT JUST USE train_tf.py

train_tf.py runs one search per group, accepts whatever it finds if the FIT
metric improved, and moves on. Two measurements from this project say that is
the wrong shape:

  1. SEED VARIANCE DOMINATES. search_robustness.py: re-rolling the random seed
     moved out-of-sample performance MORE than switching search algorithm did
     (sd 0.541 vs 0.377). The tolerance-1 seed test was worse -- four runs
     identical but for the seed gave reproducibility 48.1% to 69.9% and
     out-of-sample Sharpe 0.26 to 1.17. Taking one search's answer is taking
     one draw and calling it a finding.

  2. FIT QUALITY DOES NOT PREDICT HELD-OUT QUALITY. Correlation between the
     two across six search methods was -0.18, CI (-0.86, +0.74). Accepting a
     stage because the fit improved is accepting noise.

So this changes the ACCEPTANCE RULE rather than the search:

    K independent searches per stage, different seeds, same budget each.
    Each proposes its best candidate on the FIT slice.
    Every candidate is then scored on a VALIDATION slice it never saw.
    The stage is accepted only if a MAJORITY OF THE K SEEDS improve
    validation -- i.e. the gain is not one seed's luck. A seed that finds no
    candidate at all counts against the stage rather than dropping out of the
    vote. The accepted parameters are the best of those on validation.

A stage that only helps on one seed out of four is rejected, which is exactly
the outcome the old rule got wrong.

THE SPLIT

    [-------------- training window --------------][--- final holdout ---]
    [----- fit 70% -----][--- validation 30% ---]
                                                   never touched until the end

Validation is the LAST 30% of the training window, not a random sample: the
question is whether parameters chosen on older data work on newer data, which
is the question live trading asks.

PIECE BY PIECE

Every stage writes state.json and a per-stage record, so you can run one stage,
look at it, and continue later. --only runs a single stage; --stages sets the
order and which to include. Re-running a completed stage is a no-op unless
--redo is passed.

    python train_staged.py --csv spx500usd_oanda_m15.csv --tf M15 \
        --start 2009-01-01 --end 2022-12-31 --only sma
    python train_staged.py --csv spx500usd_oanda_m15.csv --tf M15 \
        --start 2009-01-01 --end 2022-12-31          # all stages in order
    python train_staged.py ... --report              # what has been accepted
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

CAPITAL = 6000.0


def score(df, cfg, slip, rates, objective):
    r = run_strategy(df, Params(**cfg), BrokerConfig(CAPITAL, 1.0,
                                                     slippage_points=slip),
                     rates=rates)
    m = compute_metrics(r.equity, r.trades, CAPITAL)
    dd = abs(m["max_drawdown_pct"])
    vals = {"net": 100 * (r.equity.iloc[-1] / CAPITAL - 1),
            "cagr": m["cagr_pct"], "sharpe": m["sharpe"],
            "pf": m["profit_factor"], "trades": m["trades"],
            "maxdd": m["max_drawdown_pct"],
            "calmar": (m["cagr_pct"] / dd) if dd > 1e-9 else np.nan}
    return vals, vals.get(objective, np.nan)


def set_fit_window(a, fit_df, val_df):
    """Install the FIT slice as the module's dataframe, the way workers can see.

    `_init` records its arguments in `T._ARGS`, which is what the worker-pool
    initialiser replays. Assigning `T._DF` directly works in the parent and
    leaves every spawned worker with None.

    The end bound is one second before the first VALIDATION bar, because
    `_init` slices with d[:end] and pandas date-string slicing is inclusive --
    the same off-by-one that leaked a bar per month in the rolling test.
    """
    T._DF = None
    T._init(a.csv, str(pd.Timestamp(fit_df.index[0]).date()),
            T._SCALE, T._STOPSCALE,
            (pd.Timestamp(val_df.index[0]) - pd.Timedelta(seconds=1)).isoformat())


def run_stage(name, cur, fit_df, val_df, a, rates, floor):
    """K seeded searches on `fit`, majority vote on `val`."""
    spec, fixed = T.GROUPS[name]
    cands = []
    for k in range(a.seeds):
        # The FIT window must be installed via _init, not by assigning _DF.
        # T.search spawns workers that rebuild module state from T._ARGS; a
        # hand-set _DF is invisible to them and they die on _DF = None. Same
        # bug as rolling_retrain.py had, reintroduced here.
        set_fit_window(a, fit_df, val_df)
        cand, r, sc = T.search(cur, fixed, T.scaled(spec), floor, a.samples,
                               a.seed + 1000 * k + hash(name) % 997,
                               a.workers, a.objective, a.slippage)
        if np.isfinite(sc):
            cands.append(cand)
    if not cands:
        return cur, {"accepted": False, "reason": "no candidate cleared the "
                     "trade floor on any seed", "n_seeds": a.seeds}

    base_val, base_sc = score(val_df, cur, a.slippage, rates, a.objective)
    scored = []
    for cand in cands:
        v, s = score(val_df, {**cur, **fixed, **cand}, a.slippage, rates,
                     a.objective)
        scored.append((s, v, cand))
    better = [x for x in scored if np.isfinite(x[0]) and x[0] > base_sc]
    # Majority of the seeds REQUESTED, not of the seeds that happened to
    # produce a candidate. A first version used len(cands), so if 3 of 4 seeds
    # failed to clear the trade floor the survivor faced need=1 and decided the
    # stage alone -- the exact single-draw acceptance this rule exists to stop.
    # Seeds that produce nothing are evidence against the stage, not absent
    # from the vote.
    need = a.seeds // 2 + 1
    rec = {"n_seeds": a.seeds, "n_candidates": len(cands),
           "n_improved": len(better), "need": need,
           "base_val": base_sc,
           "val_scores": [None if not np.isfinite(s) else round(s, 4)
                          for s, _, _ in scored]}
    if len(better) < need:
        miss = a.seeds - len(cands)
        rec.update(accepted=False,
                   reason=(f"only {len(better)}/{a.seeds} seeds improved "
                           f"validation, needed {need}"
                           + (f" ({miss} produced no candidate)" if miss else "")))
        return cur, rec
    best = max(better, key=lambda x: x[0])
    rec.update(accepted=True, val_before=round(base_sc, 4),
               val_after=round(best[0], 4), params=best[2],
               val_metrics={k: (None if not np.isfinite(v) else round(v, 3))
                            for k, v in best[1].items()})
    return {**cur, **fixed, **best[2]}, rec


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--tf", required=True, choices=sorted(T.TF_MINUTES))
    ap.add_argument("--start", required=True, help="training window start")
    ap.add_argument("--end", required=True, help="training window end (holdout after)")
    ap.add_argument("--val-frac", type=float, default=0.30,
                    help="last fraction of the training window used to ACCEPT "
                         "or reject a stage. Never searched on.")
    ap.add_argument("--seeds", type=int, default=4,
                    help="independent searches per stage. A stage is accepted "
                         "only if a majority improve validation.")
    ap.add_argument("--samples", type=int, default=200, help="per seed, per stage")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 1))
    ap.add_argument("--objective", default="calmar",
                    choices=["net", "cagr", "calmar", "sharpe", "pf"])
    ap.add_argument("--slippage", type=float, default=0.0)
    ap.add_argument("--ladder-mode", default="dollars", choices=sorted(T.LADDER_SPECS))
    ap.add_argument("--length-scale", type=float, default=1.0)
    ap.add_argument("--stop-scale", type=float, default=None)
    ap.add_argument("--min-trade-frac", type=float, default=0.6)
    ap.add_argument("--trigger-tolerance", type=int, default=None)
    ap.add_argument("--state-triggers", action="store_true",
                    help="use `RSI > level` / `close < band` instead of "
                         "crossovers, matching a Pine script written with "
                         "> and <. Held fixed for the whole run: a config "
                         "trained under crossovers does not transfer.")
    ap.add_argument("--base", default=None)
    ap.add_argument("--stages", default=",".join(T.ORDER))
    ap.add_argument("--only", default=None, help="run just this stage")
    ap.add_argument("--redo", action="store_true", help="re-run completed stages")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    T.set_ladder_mode(a.ladder_mode)
    T._MAXLEN, T._TF = 25_000, a.tf
    if a.base:
        T.BASE_CFG = a.base
    if a.trigger_tolerance is not None:
        for g, (s, f) in T.GROUPS.items():
            T.GROUPS[g] = (s, {**f, "trigger_tolerance": a.trigger_tolerance})
    if a.state_triggers:
        # Fixed on every group so no candidate can flip back mid-search.
        for g, (s, f) in T.GROUPS.items():
            T.GROUPS[g] = (s, {**f, "rsi_state": True, "bb_state": True,
                               "lsma_state": True, "ssma_state": True})
    ratio = T.TF_MINUTES["H4"] / T.TF_MINUTES[a.tf]
    T._SCALE = ratio * a.length_scale
    T._STOPSCALE = a.stop_scale if a.stop_scale is not None else 1.0

    fp, settings = T.settings_fingerprint(a)
    tag = (f"{os.path.basename(a.csv).replace('.csv','')}_{a.tf}_staged"
           f"_{a.start[:7]}_to{a.end[:7]}_{fp}")
    out = f"results/{tag}"
    T.guard_settings(out, settings)
    state_path = f"{out}/state.json"

    df = _normalise(_read_csv(a.csv))[a.start:a.end]
    cut = int(len(df) * (1 - a.val_frac))
    fit_df, val_df = df.iloc[:cut], df.iloc[cut:]
    rates = (fetch_fred.load_daily_series("dfii10.csv")
             if os.path.exists("dfii10.csv") else None)
    T._RATES = rates

    st = (json.load(open(state_path)) if os.path.exists(state_path)
          else {"cur": json.load(open(T.BASE_CFG)), "done": {}, "order": []})

    print(f"\nSTAGED TRAINING  {tag}")
    print(f"  fit        {fit_df.index[0].date()} .. {fit_df.index[-1].date()}"
          f"   {len(fit_df):,} bars")
    print(f"  validation {val_df.index[0].date()} .. {val_df.index[-1].date()}"
          f"   {len(val_df):,} bars   (never searched)")
    print(f"  holdout    everything after {a.end} -- untouched")
    print(f"  {a.seeds} seeds x {a.samples} samples per stage, "
          f"majority must improve validation")
    print("=" * 96)

    if a.report:
        for s in st["order"]:
            r = st["done"][s]
            flag = "ACCEPTED" if r["accepted"] else "rejected"
            print(f"  {s:<10}{flag:<10}{r.get('n_improved','-')}/"
                  f"{r.get('n_seeds','-')} seeds improved validation   "
                  + (f"{r['val_before']} -> {r['val_after']}" if r["accepted"]
                     else r.get("reason", "")))
        return

    set_fit_window(a, fit_df, val_df)
    base_fit, _ = score(fit_df, json.load(open(T.BASE_CFG)), a.slippage,
                        rates, a.objective)
    floor = T.trade_floor(base_fit["trades"], a.min_trade_frac,
                          len(fit_df), a.tf, min_abs=10)
    print(f"  baseline {base_fit['trades']} trades on fit -> floor {floor}\n")
    print(f"  {'stage':<10}{'seeds ok':>10}{'val before':>12}{'val after':>11}"
          f"{'trades':>8}{'Sharpe':>8}{'maxDD%':>9}  decision")
    print("  " + "-" * 88)

    stages = [a.only] if a.only else [s for s in a.stages.split(",") if s]
    for s in stages:
        if s not in T.GROUPS:
            raise SystemExit(f"unknown stage {s!r}; choose from {list(T.GROUPS)}")
        if s in st["done"] and not a.redo:
            r = st["done"][s]
            print(f"  {s:<10}{'(done)':>10}  "
                  + ("accepted" if r["accepted"] else "rejected") + " earlier")
            continue
        t0 = time.time()
        st["cur"], rec = run_stage(s, st["cur"], fit_df, val_df, a, rates, floor)
        st["done"][s] = rec
        st["order"] = [x for x in st["order"] if x != s] + [s]
        os.makedirs(out, exist_ok=True)
        json.dump(st, open(state_path, "w"), indent=2, default=str)
        json.dump(st["cur"], open(f"{out}/config.json", "w"), indent=2, default=str)
        if rec["accepted"]:
            m = rec["val_metrics"]
            print(f"  {s:<10}{rec['n_improved']}/{rec['n_seeds']:<8}"
                  f"{rec['val_before']:>12}{rec['val_after']:>11}"
                  f"{m['trades']:>8}{m['sharpe']:>8}{m['maxdd']:>9}  "
                  f"ACCEPTED [{time.time()-t0:.0f}s]", flush=True)
        else:
            print(f"  {s:<10}{rec.get('n_improved',0)}/{rec.get('n_seeds',0):<8}"
                  f"{'':>12}{'':>11}{'':>8}{'':>8}{'':>9}  "
                  f"rejected -- {rec['reason']} [{time.time()-t0:.0f}s]", flush=True)

    print(f"\n  state  {state_path}")
    print(f"  config {out}/config.json")
    acc = [s for s in st["order"] if st["done"][s]["accepted"]]
    print(f"  accepted so far: {', '.join(acc) if acc else 'none'}")


if __name__ == "__main__":
    main()
