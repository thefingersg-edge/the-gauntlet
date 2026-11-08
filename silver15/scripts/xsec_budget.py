#!/usr/bin/env python3
"""Power budget for a CROSS-SECTIONAL strategy. Run before hypothesising.

NO RETURNS ARE COMPUTED IN THIS FILE. Everything below comes from rank
persistence, turnover, spreads and volatility — never from P&L.

WHY CROSS-SECTIONAL IS A DIFFERENT ANIMAL
-----------------------------------------
Every previous test made one decision PER INSTRUMENT. A cross-sectional
strategy makes one decision per REBALANCE across the whole panel: the
positions are all driven by the same ranking, so 28 legs are one observation,
not 28. That is a ~28x cut in nominal sample before anything else happens.

Against that it has two genuine advantages:

  * the market factor is differenced away (long top, short bottom), so the
    common component that dominates directional trading is removed;
  * ranks use RELATIVE information, which is not the same information the
    time-series signals were reading.

THE THREE THINGS THAT DECIDE IT
-------------------------------
  1. How many INDEPENDENT rebalances exist, after rank persistence. A momentum
     rank barely changes between adjacent rebalances, so the nominal count is
     an upper bound.
  2. TURNOVER. Rotating a panel means trading several instruments per
     rebalance. Cost per decision can be many times a single-instrument trade.
  3. The detectability bar, which is k/sqrt(years) and does NOT depend on
     trade count -- so the question is whether cost leaves room beneath it.

    python xsec_budget.py --data ../data_universe
"""

from __future__ import annotations

import argparse
import os
import sys

VERSION = "1.0"
YEARS = 20.4
NET_BAR_2SIG = 2.0 / YEARS ** 0.5          # 0.44
MIN_PANEL = 20                              # instruments needed to rank


def main():
    import numpy as np, pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data_universe")
    ap.add_argument("--top", type=int, default=5, help="longs (and shorts)")
    a = ap.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import screen_universe as U

    print(f"xsec_budget.py v{VERSION}   NO RETURNS COMPUTED")
    s = U.load(a.data)
    idx = None
    for v in s.values():
        idx = v.index if idx is None else idx.union(v.index)
    M = pd.DataFrame({U.LABEL[k]: v.reindex(idx) for k, v in s.items()})
    spread = pd.Series({U.LABEL[k]: U.SPREAD_REL[k] for k in s})
    logM = np.log(M)
    print(f"  {M.shape[1]} instruments, {len(M):,} H4 bars, {YEARS:.1f} years")
    print(f"  detectability bar at 2 sigma: annual Sharpe {NET_BAR_2SIG:.2f}\n")

    print(f"{'rebal':>6}{'days':>6}{'rebals':>8}{'rank rho':>10}{'indep':>8}"
          f"{'turnover':>10}{'cost/rebal':>12}{'ann cost':>10}{'gross req':>11}")
    print("=" * 82)
    best = None
    for reb in (30, 60, 120, 250, 500):
        L = reb                                  # lookback = rebalance spacing
        mom = logM - logM.shift(L)
        rank = mom.rank(axis=1, pct=True)
        ok = M.notna().sum(axis=1) >= MIN_PANEL
        pts = np.flatnonzero(ok.to_numpy())
        pts = pts[::reb]
        if len(pts) < 12:
            continue
        R = rank.iloc[pts]

        # 1. rank persistence between CONSECUTIVE rebalances -> independence
        rhos = []
        for i in range(1, len(R)):
            x, y = R.iloc[i - 1], R.iloc[i]
            m = x.notna() & y.notna()
            if m.sum() >= MIN_PANEL:
                rhos.append(np.corrcoef(x[m], y[m])[0, 1])
        rho = float(np.nanmean(rhos)) if rhos else 0.0
        indep = len(R) * (1 - rho) / (1 + rho) if rho > -1 else len(R)

        # 2. turnover: how much of the book changes each rebalance
        sel = []
        for i in range(len(R)):
            r = R.iloc[i].dropna()
            if len(r) < MIN_PANEL:
                sel.append(set()); continue
            longs = set(r.nlargest(a.top).index)
            shorts = set(r.nsmallest(a.top).index)
            sel.append(longs | shorts)
        # Symmetric difference counts BOTH departures and arrivals, so it
        # double-counts the names actually traded. Divide by 2. The previous
        # version reported 110% turnover on a book where ~55% of names change,
        # which made cost twice as bad as it is -- conservative, but wrong.
        turn = np.mean([len(sel[i] ^ sel[i - 1]) / (2 * 2 * a.top)
                        for i in range(1, len(sel)) if sel[i] and sel[i - 1]])

        # 3. cost: legs traded x their spread, per rebalance, as a fraction of
        #    the gross book (2*top legs)
        avg_spread = float(spread.mean())
        cost_per_rebal = turn * 2 * a.top * avg_spread / (2 * a.top)
        rebals_per_year = len(R) / YEARS
        # portfolio vol per rebalance period: spread of a long-short book.
        # Use the cross-sectional dispersion of period returns as the scale.
        per = logM.diff(reb)
        disp = float(per.std(axis=1).median())
        cost_in_vol = cost_per_rebal / disp if disp > 0 else np.inf
        ann_cost = cost_in_vol * np.sqrt(rebals_per_year)
        gross_req = NET_BAR_2SIG + ann_cost

        print(f"{reb:>6}{reb*4/24:>6.0f}{len(R):>8}{rho:>10.3f}{indep:>8.0f}"
              f"{turn:>10.1%}{cost_per_rebal*100:>11.4f}%{ann_cost:>10.2f}"
              f"{gross_req:>11.2f}")
        if best is None or gross_req < best[0]:
            best = (gross_req, reb, indep, rho, turn, ann_cost)

    if not best:
        print("\n  no viable rebalance frequency"); return
    g, reb, indep, rho, turn, ac = best
    print(f"\n  Best: rebalance every {reb} bars ({reb*4/24:.0f} days)")
    print(f"    rank persistence {rho:.3f} -> {indep:.0f} independent rebalances")
    print(f"    turnover {turn:.0%} per rebalance, annualised cost {ac:.2f} Sharpe")
    print(f"    GROSS annual Sharpe required: {g:.2f}")
    print(f"\n  For comparison: directional needed 0.79 at 3 sigma / ~0.57 at 2.")
    print(f"  Published cross-sectional momentum on liquid futures runs ~0.3-0.6")
    print(f"  gross, and that is with far larger universes than 28.")
    if g <= 0.6:
        print(f"\n  => {g:.2f} is inside the plausible band. Worth pre-registering.")
    else:
        print(f"\n  => {g:.2f} exceeds what this family plausibly produces.")
        print(f"     A 28-instrument panel is small for cross-sectional work:")
        print(f"     the rank has few distinct states and turnover is expensive.")
    if indep < 200:
        print(f"\n  !! only {indep:.0f} independent rebalances. Even a correct")
        print(f"     result would be estimated from a very small sample.")


if __name__ == "__main__":
    main()
