#!/usr/bin/env python3
"""Score each separately-trained trigger_tolerance against the criterion fixed
in run_tolerance_study.sh.

Each config here was fitted WITH its own tolerance held constant, so this is a
like-for-like comparison. The earlier sweep -- tolerance applied to parameters
tuned at 0 -- is not comparable and should not be cited alongside it.

Three things are reported per level, because they can disagree:

    in-sample        what the training window says (always the best number)
    out-of-sample    2006-2012 and 2024-2026, neither seen during fitting
    reproducibility  share of trades common to OANDA and Dukascopy

The gate that motivated the whole exercise is the third one: at tolerance 0 it
came back at 46.7%, meaning fewer than half the trades survive a change of
data vendor. A level only counts as a win if it fixes that WITHOUT giving up
the out-of-sample performance -- otherwise it has bought reproducibility by
removing the thing being reproduced.

    python compare_tolerance.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from broker import BrokerConfig                     # noqa: E402
from data import _normalise, _read_csv              # noqa: E402
from feed_compare import align, match_trades        # noqa: E402
from metrics import compute_metrics                 # noqa: E402
from strategy import Params, run_strategy           # noqa: E402
import fetch_fred                                   # noqa: E402

TRAIN = ("2013-01-01", "2023-12-31")
OOS = [("2006-2012", "2006-01-01", "2012-12-31"),
       ("2024-2026", "2024-01-01", "2026-12-31")]
SLIP = 0.25
CAPITAL = 6000.0
MIN_REPRO = 60.0
MIN_SHARPE = 0.8


def main() -> None:
    rates = (fetch_fred.load_daily_series("dfii10.csv")
             if os.path.exists("dfii10.csv") else None)
    oa = _normalise(_read_csv("xauusd_oanda_m15.csv"))
    dk_path = "xauusd_dk_m15_fixed.csv"
    dk = _normalise(_read_csv(dk_path)) if os.path.exists(dk_path) else None
    if dk is None:
        print(f"  {dk_path} missing -- reproducibility column will be blank")
    bc = BrokerConfig(CAPITAL, 1.0, slippage_points=SLIP)

    found = []
    for p in sorted(glob.glob("configs/*_tol*_trained.json")):
        m = re.search(r"_tol(\d+)_trained", p)
        if m:
            found.append((int(m.group(1)), p))
    if not found:
        raise SystemExit("no *_tol*_trained.json configs -- run "
                         "run_tolerance_study.sh first")

    print(f"\nTRIGGER TOLERANCE, each level SEPARATELY TRAINED on "
          f"{TRAIN[0]}..{TRAIN[1]}")
    print(f"criterion fixed in advance: reproducibility >= {MIN_REPRO:.0f}% "
          f"AND OOS Sharpe >= {MIN_SHARPE} on BOTH unseen windows")
    print("=" * 100)
    hdr = f"{'tol':>4}{'IS trades':>11}{'IS Sharpe':>11}"
    for nm, _, _ in OOS:
        hdr += f"{nm + ' Sh':>14}"
    print(hdr + f"{'repro':>9}   verdict")
    print("-" * 100)

    for tol, path in sorted(found):
        cfg = json.load(open(path))
        cfg["trigger_tolerance"] = tol          # belt and braces
        seg = oa[TRAIN[0]:TRAIN[1]]
        r = run_strategy(seg, Params(**cfg), bc, rates=rates)
        mi = compute_metrics(r.equity, r.trades, CAPITAL)

        oos_sh = []
        for nm, s, e in OOS:
            rr = run_strategy(oa[s:e], Params(**cfg), bc, rates=rates)
            oos_sh.append(compute_metrics(rr.equity, rr.trades, CAPITAL)["sharpe"])

        repro = np.nan
        if dk is not None:
            A, B, _ = align(dk, oa)
            ra = run_strategy(A, Params(**cfg), bc, rates=rates)
            rb = run_strategy(B, Params(**cfg), bc, rates=rates)
            mm = match_trades(ra.trades, rb.trades)
            repro = mm["pct"] if isinstance(mm, dict) and "pct" in mm else mm

        ok = (np.isfinite(repro) and repro >= MIN_REPRO
              and all(np.isfinite(s) and s >= MIN_SHARPE for s in oos_sh))
        line = f"{tol:>4}{mi['trades']:>11}{mi['sharpe']:>11.2f}"
        for s in oos_sh:
            line += f"{s:>14.2f}"
        print(line + f"{repro:>8.1f}%   {'WIN' if ok else 'no'}")

    print("\nIf no level wins, the conclusion is that the edge and the")
    print("fragility are the same property: the strategy earns what it earns")
    print("BECAUSE four rare conditions must align exactly, and loosening that")
    print("enough to reproduce across vendors removes the edge itself.")


if __name__ == "__main__":
    main()
