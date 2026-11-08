#!/usr/bin/env python3
"""Score a trained config on the holdout windows of
PREREGISTRATION_SPX500_timeframes.md and apply its five kill conditions.

The registration fixed the windows and the conditions before any arm ran. This
script implements them literally so the verdict is arithmetic rather than
judgement, and so an arm cannot be talked past a condition it failed.

    python score_holdouts.py --results results/spx500usd_oanda_h4_H4_staged_...
    python score_holdouts.py --results <dir> --csv spx500usd_oanda_h4.csv --tf H4

WINDOWS (registration section 3)

    2005-01 .. 2008-12   holdout (pre)   -- contains the 2008 crash
    2009-01 .. 2018-10   fit             -- not scored here
    2018-10 .. 2022-12   validation      -- not scored here
    2023-01 .. 2026-08   holdout (post)

KILL CONDITIONS (registration section 5) -- an arm fails if ANY fires:

    1. Sharpe < 0.8 on either holdout, at the measured spread
    2. fewer than 30 trades in either holdout (then it is not a measurement)
    3. max drawdown worse than buy-and-hold on 2005-2008
    4. the 2005-2008 result does not survive 1.00/fill
    5. break-even spread below 0.25 points

An arm PASSES only if all five clear on BOTH holdout windows.

Note on condition 4: 2005-2011 OANDA spreads are backfilled at bid == ask, so
the real 2008 spread is unknown and certainly wider than today's 0.25. Scoring
the pre-holdout at 1.00 as well is the registration's guard against passing only
at a spread that did not exist at the time.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np                                   # noqa: E402
import pandas as pd                                  # noqa: E402

from broker import BrokerConfig                      # noqa: E402
from data import _normalise, _read_csv               # noqa: E402
from metrics import compute_metrics                  # noqa: E402
from strategy import Params, run_strategy            # noqa: E402

PRE = ("2005-01-01", "2008-12-31")
POST = ("2023-01-01", "2026-08-14")
MEASURED_SPREAD = 0.25          # half the measured 0.50 median, per registration
STRESS_SPREAD = 1.00            # the pre-holdout stress, registration section 4
SHARPE_BAR = 0.8
MIN_TRADES = 30


def params_from(cfg: dict) -> Params:
    return Params(**{k: v for k, v in cfg.items()
                     if k in Params.__dataclass_fields__})


def score(df: pd.DataFrame, p: Params, slippage: float) -> dict:
    r = run_strategy(df, p, BrokerConfig(100000.0, 1.0,
                                         slippage_points=slippage))
    m = compute_metrics(r.equity, r.trades, 100000.0)
    m["net_pct"] = 100.0 * (r.equity.iloc[-1] / 100000.0 - 1.0)
    # compute_metrics returns max_drawdown in CURRENCY (see metrics.py) -- a
    # detail that already produced one wrong table in this tree, so it is
    # converted explicitly here rather than printed raw.
    m["dd_pct"] = 100.0 * m["max_drawdown"] / 100000.0
    return m


def buy_and_hold(df: pd.DataFrame) -> dict:
    """Condition 3's benchmark. A strategy that does not protect in a crash has
    no reason to exist over simply holding the index."""
    c = df["close"]
    eq = 100000.0 * c / c.iloc[0]
    peak = eq.cummax()
    return {"net_pct": 100.0 * (eq.iloc[-1] / 100000.0 - 1.0),
            "dd_pct": 100.0 * float((eq - peak).min()) / 100000.0}


def breakeven_spread(df: pd.DataFrame, p: Params,
                     hi: float = 3.0, tol: float = 0.005) -> float:
    """Largest per-fill spread at which the window is still not a loss.

    Bisection on net return. Returns 0.0 if the window loses money even gross,
    which makes condition 5 fire on its own terms.
    """
    if score(df, p, 0.0)["net_pct"] <= 0:
        return 0.0
    lo = 0.0
    if score(df, p, hi)["net_pct"] > 0:
        return hi                      # survives anything we would plausibly pay
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if score(df, p, mid)["net_pct"] > 0:
            lo = mid
        else:
            hi = mid
    return lo


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True,
                    help="a train_staged.py output dir containing config.json")
    ap.add_argument("--csv", default=None, help="inferred from args.json if absent")
    ap.add_argument("--tf", default=None, help="label only")
    ap.add_argument("--base", default=None,
                    help="also score this untrained base, for context. Training "
                         "that accepted no stage returns the base unchanged, and "
                         "saying so is more honest than reporting it as trained.")
    a = ap.parse_args()

    cfg = json.load(open(os.path.join(a.results, "config.json")))
    args_path = os.path.join(a.results, "args.json")
    saved = json.load(open(args_path)) if os.path.exists(args_path) else {}
    csv = a.csv or saved.get("csv")
    tf = a.tf or saved.get("tf") or "?"
    if not csv or not os.path.exists(csv):
        sys.exit(f"cannot find the CSV ({csv!r}); pass --csv")

    # How many stages did training actually accept? An arm that accepted none is
    # the untrained base, and must be labelled that way.
    st_path = os.path.join(a.results, "state.json")
    acc = []
    if os.path.exists(st_path):
        st = json.load(open(st_path))
        acc = [k for k, v in st.get("done", {}).items() if v.get("accepted")]

    full = _normalise(_read_csv(csv))
    p = params_from(cfg)

    print(f"\n{'='*78}")
    print(f"HOLDOUT SCORING -- SPX500 {tf}")
    print(f"  registration PREREGISTRATION_SPX500_timeframes.md")
    print(f"  config  {a.results}")
    print(f"  data    {os.path.basename(csv)}  {len(full):,} bars  "
          f"{full.index[0].date()} -> {full.index[-1].date()}")
    print(f"  stages accepted in training: "
          f"{', '.join(acc) if acc else 'NONE -- this is the untrained base'}")
    print(f"{'='*78}")

    rows = []
    for label, (s, e), extra in (("pre  2005-2008", PRE, STRESS_SPREAD),
                                 ("post 2023-2026", POST, None)):
        d = full[s:e]
        if d.empty:
            print(f"\n{label}: NO DATA in window -- arm cannot be judged here")
            rows.append({"label": label, "empty": True})
            continue
        m = score(d, p, MEASURED_SPREAD)
        row = {"label": label, "bars": len(d), "empty": False, **m}
        if extra is not None:
            row["stress"] = score(d, p, extra)
        row["bh"] = buy_and_hold(d)
        row["be"] = breakeven_spread(d, p)
        rows.append(row)

    print(f"\n{'window':<16}{'bars':>9}{'trades':>8}{'Sharpe':>8}{'net%':>8}"
          f"{'maxDD%':>9}{'B&H dd%':>9}{'break-even':>12}")
    print("-" * 79)
    for r in rows:
        if r["empty"]:
            print(f"{r['label']:<16}{'-- no data --':>50}")
            continue
        print(f"{r['label']:<16}{r['bars']:>9,}{r['trades']:>8}{r['sharpe']:>8.2f}"
              f"{r['net_pct']:>8.1f}{r['dd_pct']:>9.1f}{r['bh']['dd_pct']:>9.1f}"
              f"{r['be']:>12.3f}")
        if "stress" in r:
            s = r["stress"]
            print(f"{'  at 1.00/fill':<16}{'':>9}{s['trades']:>8}{s['sharpe']:>8.2f}"
                  f"{s['net_pct']:>8.1f}{s['dd_pct']:>9.1f}")

    # ---- kill conditions, applied literally --------------------------------
    print(f"\n{'KILL CONDITIONS':<58}{'verdict':>10}")
    print("-" * 70)
    fails: list[str] = []

    def verdict(n: int, text: str, failed: bool, note: str = "") -> None:
        tag = "FAIL" if failed else "pass"
        if failed:
            fails.append(f"{n}")
        print(f"  {n}. {text:<54}{tag:>10}")
        if note:
            print(f"       {note}")

    live = [r for r in rows if not r["empty"]]

    bad_sharpe = [r for r in live if r["sharpe"] < SHARPE_BAR]
    verdict(1, f"Sharpe >= {SHARPE_BAR} on both holdouts", bool(bad_sharpe),
            "; ".join(f"{r['label'].strip()} = {r['sharpe']:.2f}"
                      for r in bad_sharpe))

    thin = [r for r in live if r["trades"] < MIN_TRADES]
    verdict(2, f">= {MIN_TRADES} trades in each holdout", bool(thin),
            "; ".join(f"{r['label'].strip()} = {r['trades']}" for r in thin))

    pre = next((r for r in live if r["label"].startswith("pre")), None)
    if pre:
        # dd_pct is negative; "worse" means a larger magnitude loss
        worse = pre["dd_pct"] < pre["bh"]["dd_pct"]
        verdict(3, "2005-2008 drawdown no worse than buy-and-hold", worse,
                f"strategy {pre['dd_pct']:.1f}% vs B&H {pre['bh']['dd_pct']:.1f}%")
        st = pre["stress"]
        bad = st["sharpe"] < SHARPE_BAR or st["net_pct"] <= 0
        verdict(4, "2005-2008 survives 1.00/fill", bad,
                f"Sharpe {st['sharpe']:.2f}, net {st['net_pct']:.1f}%")
    else:
        verdict(3, "2005-2008 drawdown vs buy-and-hold", True, "no data")
        verdict(4, "2005-2008 survives 1.00/fill", True, "no data")

    low_be = [r for r in live if r["be"] < MEASURED_SPREAD]
    verdict(5, f"break-even spread >= {MEASURED_SPREAD} points", bool(low_be),
            "; ".join(f"{r['label'].strip()} = {r['be']:.3f}" for r in low_be))

    print(f"\n{'='*78}")
    if fails:
        print(f"ARM FAILS -- conditions {', '.join(fails)} fired.")
        print("Per the registration, the live strategy at this timeframe should stop.")
        if not acc:
            print("Note: training accepted NO stage, so this is the untrained base.")
            print("The structure, not a parameter choice, is what failed here.")
    else:
        print("ARM PASSES all five conditions on both holdouts.")
        print("Per registration section 6, this means the STRUCTURE is worth running")
        print("with the RETRAINED values -- it is NOT evidence the live config works,")
        print("since the live values were fitted on the full history.")
    print(f"{'='*78}\n")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
