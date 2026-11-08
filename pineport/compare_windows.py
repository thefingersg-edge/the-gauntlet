#!/usr/bin/env python3
"""Line up the 3y / 5y / 10y rolling-retrain runs and test them against the
criterion fixed in run_window_sweep.sh.

The point is NOT to find the best training length. It is to find out whether
the answer depends on training length at all. Three lengths agreeing that
re-fitting adds nothing is a far stronger statement than one length saying so,
because it rules out "you just picked the wrong lookback" -- which is the last
remaining way the null result could be an artefact of a choice I made.

INTERSECTED ON COMMON MONTHS. Even with matched --start dates the runs can end
up with slightly different month lists (a window that fell short of the 200-bar
minimum is skipped). Comparing means over different month sets would let the
calendar do the talking, so everything below is computed on the intersection.

    python compare_windows.py
    python compare_windows.py --tf H1
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

import numpy as np
import pandas as pd


def load(pattern: str) -> dict[float, pd.DataFrame]:
    got = {}
    for d in sorted(glob.glob(pattern)):
        f = os.path.join(d, "summary.csv")
        if not os.path.exists(f):
            continue
        m = re.search(r"_tr([\d.]+)y_", d)
        if not m:
            continue
        got[float(m.group(1))] = pd.read_csv(f).dropna(subset=["retrained"])
    return got


def report(name: str, runs: dict[float, pd.DataFrame]) -> list[bool]:
    if len(runs) < 2:
        print(f"\n{name}: only {len(runs)} run(s) found -- need at least two\n")
        return []
    common = set.intersection(*(set(r["month"]) for r in runs.values()))
    months = sorted(common)
    print(f"\n{'=' * 96}\n{name}   {len(months)} common test months   "
          f"{months[0]} .. {months[-1]}")
    print(f"{'train':<9}{'ann%':>9}{'Sharpe':>8}{'maxDD%':>9}{'%up':>7}"
          f"{'  vs frozen':>18}{'  vs random':>18}{'  vs B&H':>16}")
    print("-" * 96)
    verdicts = []
    for y in sorted(runs):
        r = runs[y][runs[y]["month"].isin(common)].sort_values("month")
        x = r["retrained"]
        eq = (1 + x).cumprod()
        yrs = len(x) / 12
        ann = 100 * (eq.iloc[-1] ** (1 / yrs) - 1) if eq.iloc[-1] > 0 else np.nan
        dd = 100 * ((eq / eq.cummax()) - 1).min()
        sh = (x.mean() / x.std()) * np.sqrt(12) if x.std() > 0 else np.nan
        cells, sig = [], {}
        for o in ("frozen", "random", "buyhold"):
            d = (r["retrained"] - r[o]).dropna()
            se = d.std(ddof=1) / np.sqrt(len(d))
            t = d.mean() / se if se > 0 else np.nan
            sig[o] = abs(t) > 2
            cells.append(f"{100*d.mean():>+7.3f}% t{t:>+5.2f}")
        print(f"{y:<9.0f}{ann:>9.2f}{sh:>8.2f}{dd:>9.1f}{100*(x>0).mean():>7.1f}"
              + "".join(f"{c:>18}" for c in cells[:2]) + f"{cells[2]:>16}")
        verdicts.append(sig["frozen"] and sig["random"])

    bh = runs[sorted(runs)[0]]
    bh = bh[bh["month"].isin(common)]["buyhold"]
    eqb = (1 + bh).cumprod()
    print(f"{'buy&hold':<9}{100*(eqb.iloc[-1]**(12/len(bh))-1):>9.2f}"
          f"{(bh.mean()/bh.std())*np.sqrt(12):>8.2f}"
          f"{100*((eqb/eqb.cummax())-1).min():>9.1f}{100*(bh>0).mean():>7.1f}")
    return verdicts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tf", default="H4")
    a = ap.parse_args()

    allv = []
    for stub, name in [("xauusd_oanda_h4", "GOLD 4H"),
                       ("nas100usd_oanda_h4", "NAS100 4H")]:
        allv += report(name, load(f"results/{stub}_{a.tf}_roll_tr*y_*"))

    print(f"\n{'=' * 96}\nVERDICT")
    if not allv:
        print("  no runs found -- run run_window_sweep.sh first")
    elif any(allv):
        print("  NOT SETTLED. At least one training length beat BOTH frozen and")
        print("  random at |t| > 2. Re-fitting may pay at that depth -- but check")
        print("  first whether a long window has simply converged on `frozen`.")
    else:
        print("  SETTLED. No training length beat both frozen and random on either")
        print("  instrument. The null result is not an artefact of the 3-year")
        print("  lookback: re-fitting adds nothing at any history depth tested.")
    print()


if __name__ == "__main__":
    main()
