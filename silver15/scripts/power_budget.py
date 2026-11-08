#!/usr/bin/env python3
"""Power budget for a cross-metal residual basket. RUN THIS BEFORE HYPOTHESISING.

The previous pre-registration fixed a 3-sigma threshold and a 200-trade floor
without checking they were mutually achievable. They were not: the design
yielded ~16 independent trades a year and needed ~1,400. The test was dead
before it ran, and would have invalidated a positive result just as surely as
the negative one it produced.

This tool answers, from data alone and before any hypothesis is stated:

  1. What does each candidate pair cost, relative to how far its residual moves?
  2. How many independent trades per year does each pair yield?
  3. How correlated are the pairs -- i.e. how much does a basket actually buy?
  4. Given all that, what edge is detectable? Is the test worth running at all?

If the answer to (4) is "no", that is the deliverable. Writing a
pre-registration you cannot satisfy is worse than writing none.

    python power_budget.py --data ../data_h4
"""

from __future__ import annotations

import argparse
import itertools
import os

VERSION = "1.0"

# MEASURED round-trip spreads as a fraction of price (oanda_intraday --sides,
# 2026-06 -> 2026-08). Note the spread on the minor metals: palladium's is
# 16x gold's, which may disqualify it before any signal is considered.
SPREAD_REL = {
    "xauusd": 0.62000 / 4106.06,     # 0.0151%
    "xcuusd": 0.00199 / 6.29,        # 0.0316%
    "xagusd": 0.03600 / 59.97,       # 0.0600%
    "xptusd": 2.19500 / 1634.59,     # 0.1343%
    "xpdusd": 2.96800 / 1253.83,     # 0.2367%
}
NAME = {"xagusd": "silver", "xauusd": "gold", "xptusd": "platinum",
        "xpdusd": "palladium", "xcuusd": "copper"}

# Frozen from the previous test so this is a like-for-like power estimate.
BETA_WINDOW, RESID_WINDOW, Z_WINDOW = 120, 30, 120
ENTRY_Z, MAX_HOLD, VOL_WINDOW = 2.0, 30, 14
TARGET_SD = 3.0


def load(data_dir):
    import pandas as pd
    out = {}
    for stem in SPREAD_REL:
        p = os.path.join(data_dir, f"{stem}_4h.csv")
        if not os.path.exists(p):
            print(f"  missing {p} -- skipping {NAME[stem]}")
            continue
        d = pd.read_csv(p)
        t = d.columns[0]
        d[t] = pd.to_datetime(d[t], utc=True)
        out[stem] = d.set_index(t).sort_index()["close"]
    return out


def pair_stats(a, b, sa, sb):
    """Cost, residual vol, entry count and per-trade P&L series for one pair."""
    import numpy as np, pandas as pd

    idx = a.index.intersection(b.index)
    ra = np.log(a.loc[idx]).diff()
    rb = np.log(b.loc[idx]).diff()
    beta = (ra.rolling(BETA_WINDOW).cov(rb)
            / rb.rolling(BETA_WINDOW).var().replace(0, np.nan)).clip(0.5, 4.0)
    resid = ra - beta * rb
    svol = resid.rolling(VOL_WINDOW).std()
    cum = resid.rolling(RESID_WINDOW).sum()
    z = (cum - cum.rolling(Z_WINDOW).mean()) / cum.rolling(Z_WINDOW).std()

    cost = 2 * (sa / 2 + beta.abs() * sb / 2)          # round trip, log units
    ratio = (cost / svol).replace([np.inf, -np.inf], np.nan).dropna()

    fired = (z.abs() >= ENTRY_Z).to_numpy()
    kept, last = [], -10**9
    for i in np.flatnonzero(fired):
        if i - last >= MAX_HOLD:
            kept.append(i); last = i
    years = (idx[-1] - idx[0]).days / 365.25

    return dict(n=len(kept), per_year=len(kept) / years, years=years,
                cost_ratio=float(ratio.median()), resid=resid, z=z,
                entries=idx[kept] if kept else idx[:0])


def main():
    import numpy as np, pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data_h4")
    ap.add_argument("--edge", type=float, default=0.035,
                    help="edge to detect, in win-rate fraction (0.035 = 3.5pp)")
    a = ap.parse_args()

    print(f"power_budget.py v{VERSION}")
    series = load(a.data)
    print(f"  {len(series)} instruments loaded\n")

    print("MEASURED round-trip spreads (fraction of price)")
    print("=" * 72)
    for s, v in sorted(SPREAD_REL.items(), key=lambda kv: kv[1]):
        if s in series:
            print(f"  {NAME[s]:<10} {v*100:.4f}%")

    print("\nCANDIDATE PAIRS  (residual of A vs beta x B)")
    print("=" * 72)
    print(f"  {'pair':<22}{'cost/vol':>10}{'trades/yr':>11}{'total n':>9}"
          f"{'verdict':>12}")
    stats = {}
    for x, y in itertools.combinations(sorted(series), 2):
        st = pair_stats(series[x], series[y], SPREAD_REL[x], SPREAD_REL[y])
        key = f"{NAME[x]}/{NAME[y]}"
        stats[key] = st
        # A pair is only worth trading if cost is a small fraction of the
        # barrier it must reach. Above ~0.5 the cost eats a 2.0 barrier.
        v = "ok" if st["cost_ratio"] < 0.35 else (
            "marginal" if st["cost_ratio"] < 0.6 else "TOO DEAR")
        print(f"  {key:<22}{st['cost_ratio']:>10.3f}{st['per_year']:>11.1f}"
              f"{st['n']:>9,}{v:>12}")

    keep = {k: v for k, v in stats.items() if v["cost_ratio"] < 0.35}
    print(f"\n  {len(keep)} of {len(stats)} pairs are affordable.")
    if not keep:
        print("  Nothing is tradeable at these spreads. Stop here.")
        return

    print("\nHOW INDEPENDENT ARE THE AFFORDABLE PAIRS?")
    print("=" * 72)
    R = pd.DataFrame({k: v["resid"] for k, v in keep.items()}).dropna()
    C = R.corr()
    off = C.to_numpy()[~np.eye(len(C), dtype=bool)]
    rho = float(np.mean(np.abs(off)))
    print(f"  mean |correlation| between pair residuals: {rho:.3f}")
    print("  (pairs sharing a leg move together -- six pairs from four metals")
    print("   is nowhere near six independent experiments)")

    m = len(keep)
    raw = sum(v["n"] for v in keep.values())
    eff = raw / (1 + (m - 1) * rho)
    print(f"\n  raw trades across {m} pairs        {raw:,}")
    print(f"  effective independent trades    {eff:,.0f}"
          f"   (inflation factor {raw/eff:.1f}x)")

    print("\nIS THAT ENOUGH?")
    print("=" * 72)
    n0, sd0 = 165, 0.0340                        # measured, previous test
    for edge in (0.03, a.edge, 0.05, 0.07):
        need = n0 * (sd0 / (edge / TARGET_SD)) ** 2
        ok = eff >= need
        print(f"  detect {edge*100:>4.1f}pp at {TARGET_SD:.0f} sd: need "
              f"{need:>7,.0f}   have {eff:>7,.0f}   "
              f"{'ACHIEVABLE' if ok else 'not achievable'}")

    best = np.sqrt(n0 / eff) * sd0 * TARGET_SD
    print(f"\n  Smallest edge detectable at {TARGET_SD:.0f} sd with this basket:"
          f"  {best*100:.1f}pp")
    print(f"  The hedged 15m result suggested the true edge is ~3-4pp.")
    if best <= 0.04:
        print("  => A test IS worth pre-registering. Fix thresholds to match.")
    else:
        print("  => Still underpowered for a 3-4pp edge. Pre-registering a")
        print("     3-sigma test here would repeat the previous mistake.")
        print(f"     Either accept detecting only >={best*100:.1f}pp, or stop.")


if __name__ == "__main__":
    main()
