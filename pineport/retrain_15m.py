#!/usr/bin/env python3
"""Parallel walk-forward retrain of the 15m strategy.

DESIGN CONSTRAINTS, all forced by the data rather than chosen:

* 243 trades over the 2006-2023 training window. The usual minimum is 10
  observations per fitted parameter, so the honest budget is ~6 parameters, not
  the 57 the script exposes. The search space below is deliberately small; a
  wider one would fit noise faster, not better.

* 2024-2026 IS NOT TOUCHED by this script. It is loaded only by --holdout,
  which refuses to run until a walk-forward result exists. Every number printed
  during the search is out-of-sample within 2006-2023.

* Two nulls, because "the optimiser found something" is the claim under test:
    baseline  -- the untouched starting config over the same test windows
    random    -- parameters drawn at random with no optimisation at all
  If the search cannot beat random draws out of sample, it is fitting noise.

* Objective is Calmar with a trade-count floor. Without the floor the
  optimiser's best move is to take three lucky trades.

SPEED
  One full-window run is ~13s single-core; a fold is ~2-4s. Trials inside a
  fold are independent, so they parallelise cleanly across cores. The dataframe
  is a module global and workers are forked, so it is shared copy-on-write
  rather than pickled per task.

    python retrain_15m.py --walkforward --trials 80
    python retrain_15m.py --holdout
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
from null_test import run_null                      # noqa: E402
from strategy import Params, run_strategy           # noqa: E402

DATA = "xauusd_oanda_m15.csv"
BASE_CFG = "configs/gold_15m_scalefree.json"
RESULTS = "results/retrain_15m"

TRAIN_START, TRAIN_END = "2006-01-01", "2023-12-31"
HOLDOUT_START = "2024-01-01"          # sealed until --holdout

CAPITAL = 6000.0
MIN_TRADES_PER_YEAR = 3.0

#: Six parameters. See the docstring for why it is not more.
SPACE: list[tuple[str, float, float, bool]] = [
    ("bb_period_long",     20,   140,  True),    # BBlengthL   (now 94)
    ("bb_stdev_long",      0.6,  2.6,  False),   # BBmultL     (now 1.13)
    ("sl_percent_long",    1.5,  6.0,  False),   # SL long     (now 2.94)
    ("limit_percent_long", 1.5,  8.0,  False),   # Limit long  (now 3.14)
    ("rsi_oversold",       40.0, 65.0, False),   # RSIoverSold (now 54)
    ("lsma_length_long",   10,   90,   True),    # LSMAlengthL (now 49)
]

_DF: pd.DataFrame | None = None
_BASE: dict | None = None


def _init() -> None:
    global _DF, _BASE
    if _DF is None:
        _DF = _normalise(_read_csv(DATA))
    if _BASE is None:
        _BASE = json.load(open(BASE_CFG))


def evaluate(window: pd.DataFrame, overrides: dict) -> dict:
    cfg = BrokerConfig(CAPITAL, 1.0)
    res = run_strategy(window, Params(**{**_BASE, **overrides}), cfg)
    m = compute_metrics(res.equity, res.trades, CAPITAL)
    m["years"] = (window.index[-1] - window.index[0]).days / 365.25
    return m


def objective(m: dict) -> float:
    n, yrs = m.get("trades", 0), m.get("years", 1e-9)
    if n < MIN_TRADES_PER_YEAR * yrs or n < 8:
        return -np.inf
    c = m.get("calmar", np.nan)
    return float(c) if c is not None and np.isfinite(c) else -np.inf


def sample(rng: np.random.Generator) -> dict:
    return {n: (int(rng.integers(lo, hi + 1)) if i else float(rng.uniform(lo, hi)))
            for n, lo, hi, i in SPACE}


def _trial(args):
    """One in-sample evaluation. Runs in a worker process."""
    seed, i0, i1 = args
    _init()
    rng = np.random.default_rng(seed)
    cand = sample(rng)
    return cand, objective(evaluate(_DF.iloc[i0:i1], cand))


def make_folds(df: pd.DataFrame, train_years: float = 6.0,
               test_years: float = 2.0) -> list[tuple]:
    """Rolling folds. Parameters are chosen on train, scored on the NEXT block."""
    out, start = [], df.index[0]
    while True:
        tr_end = start + pd.DateOffset(years=int(train_years))
        te_end = tr_end + pd.DateOffset(years=int(test_years))
        if te_end > df.index[-1]:
            break
        out.append((df.index.searchsorted(start), df.index.searchsorted(tr_end),
                    df.index.searchsorted(te_end)))
        start = start + pd.DateOffset(years=int(test_years))
    return out


def run_one_fold(k: int, trials: int, seed: int, workers: int) -> None:
    """Run a single fold and checkpoint it.

    Deliberately one fold per invocation: the sandbox reaps long background
    jobs, and losing 20 minutes of search to a silent kill is worse than the
    small overhead of reloading the data each time. Re-running a completed
    fold is a no-op, so this is safe to call in a loop.
    """
    _init()
    os.makedirs(RESULTS, exist_ok=True)
    out = f"{RESULTS}/fold_{k}.json"
    if os.path.exists(out):
        print(f"fold {k}: already done, skipping")
        return

    train = _DF[TRAIN_START:TRAIN_END]
    folds = make_folds(train)
    if k >= len(folds):
        print(f"fold {k}: out of range (only {len(folds)} folds)")
        return
    base_i = _DF.index.searchsorted(train.index[0])
    i0, i1, i2 = (x + base_i for x in folds[k])

    # Per-fold seed so each fold searches independently but reproducibly.
    rng = np.random.default_rng(seed + 1000 * k)
    seeds = [(int(rng.integers(0, 2**31)), i0, i1) for _ in range(trials)]
    with mp.Pool(workers) as pool:
        got = pool.map(_trial, seeds, chunksize=4)
    best, best_s = max(got, key=lambda x: x[1])
    if not np.isfinite(best_s):
        print(f"fold {k}: no candidate cleared the trade floor")
        return

    test = _DF.iloc[i1:i2]
    m = evaluate(test, best)
    row = {"fold": k, "is": best_s, "oos": objective(m),
           "base": objective(evaluate(test, {})),
           "rand": float(np.median([objective(evaluate(test, sample(rng)))
                                    for _ in range(10)])),
           "trades": m["trades"],
           "train_start": str(_DF.index[i0].date()),
           "test_start": str(test.index[0].date()),
           "test_end": str(test.index[-1].date()), **best}
    json.dump(row, open(out, "w"), indent=2)
    print(f"fold {k}  {row['train_start']} | test {row['test_start']}->{row['test_end']}"
          f"   IS {row['is']:>6.2f}   OOS {row['oos']:>6.2f}"
          f"   base {row['base']:>6.2f}   rand {row['rand']:>6.2f}"
          f"   trades {row['trades']}")


def summarise() -> None:
    _init()
    fs = sorted(f for f in os.listdir(RESULTS) if f.startswith("fold_"))
    if not fs:
        raise SystemExit("no folds yet -- run --fold 0 .. --fold 4 first")
    rows = [json.load(open(f"{RESULTS}/{f}")) for f in fs]
    r = pd.DataFrame(rows).sort_values("fold")
    r.to_csv(f"{RESULTS}/folds.csv", index=False)
    print(f"{'fold':<6}{'test window':<26}{'IS':>7}{'OOS':>8}{'base':>8}"
          f"{'rand':>8}{'trades':>8}")
    print("-" * 74)
    for _, x in r.iterrows():
        print(f"{int(x['fold']):<6}{x['test_start']+' '+x['test_end']:<26}"
              f"{x['is']:>7.2f}{x['oos']:>8.2f}{x['base']:>8.2f}"
              f"{x['rand']:>8.2f}{int(x['trades']):>8}")

    _summary_stats(r)


def _summary_stats(r: pd.DataFrame) -> None:
    beat_base = int((r["oos"] > r["base"]).sum())
    beat_rand = int((r["oos"] > r["rand"]).sum())
    n = len(r)
    print("\nOUT-OF-SAMPLE SCOREBOARD")
    print("=" * 100)
    print(f"  optimised beat the BASELINE in : {beat_base}/{n} folds")
    print(f"  optimised beat RANDOM params in: {beat_rand}/{n} folds")
    print(f"  median in-sample Calmar        : {r['is'].median():.2f}")
    print(f"  median out-of-sample Calmar    : {r['oos'].median():.2f}")
    print(f"  IS/OOS gap (overfitting signal): {r['is'].median() - r['oos'].median():+.2f}")
    print()
    print("  PARAMETER STABILITY -- a parameter that matters converges across folds")
    print(f"  {'parameter':<22}{'median':>10}{'min':>10}{'max':>10}{'spread':>10}")
    stable = {}
    for nme, lo, hi, _ in SPACE:
        v = r[nme]
        spread = (v.max() - v.min()) / (hi - lo)
        stable[nme] = float(v.median())
        flag = "  converged" if spread < 0.4 else ("  scattered" if spread > 0.7 else "")
        print(f"  {nme:<22}{v.median():>10.2f}{v.min():>10.2f}{v.max():>10.2f}"
              f"{spread:>9.0%}{flag}")

    json.dump({**_BASE, **stable}, open(f"{RESULTS}/selected.json", "w"), indent=2)
    print(f"\n  wrote {RESULTS}/selected.json  (median of per-fold choices)")
    if beat_rand <= n / 2:
        print("\n  VERDICT: the search did not beat random parameters out of sample.")
        print("  That is a result: keep the baseline, do not adopt these values.")
    else:
        print(f"\n  VERDICT: beat random in {beat_rand}/{n}. Now run --holdout ONCE.")


def holdout() -> None:
    _init()
    sel_path = f"{RESULTS}/selected.json"
    if not os.path.exists(sel_path):
        raise SystemExit("run --walkforward first; the holdout stays sealed until then")
    sel = json.load(open(sel_path))
    hold = _DF[HOLDOUT_START:]
    cfg = BrokerConfig(CAPITAL, 1.0)
    print(f"HOLDOUT {hold.index[0].date()} -> {hold.index[-1].date()}   "
          "(first and only look)")
    print("=" * 92)
    print(f"{'config':<14}{'trades':>8}{'CAGR%':>9}{'Sharpe':>8}{'maxDD%':>9}"
          f"{'PF':>7}{'Calmar':>8}{'vs random':>11}")
    print("-" * 92)
    for lab, c in [("baseline", _BASE), ("retrained", sel)]:
        p = Params(**c)
        res = run_strategy(hold, p, cfg)
        m = compute_metrics(res.equity, res.trades, CAPITAL)
        try:
            pc = run_null(hold, p, cfg, 600, 0)["percentile"]
        except SystemExit:
            pc = float("nan")
        print(f"{lab:<14}{m['trades']:>8}{m['cagr_pct']:>9.2f}{m['sharpe']:>8.2f}"
              f"{m['max_drawdown_pct']:>9.2f}{m['profit_factor']:>7.2f}"
              f"{m.get('calmar', float('nan')):>8.2f}{pc:>11.1f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fold", type=int, default=None, help="run one fold and checkpoint")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--holdout", action="store_true")
    ap.add_argument("--trials", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    if a.fold is not None:
        run_one_fold(a.fold, a.trials, a.seed, a.workers)
    elif a.summary:
        summarise()
    elif a.holdout:
        holdout()
    else:
        raise SystemExit("pass --walkforward or --holdout")


if __name__ == "__main__":
    main()
