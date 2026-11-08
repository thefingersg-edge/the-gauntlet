#!/usr/bin/env python3
"""THE v4 pre-registered test. Spec frozen in PREREGISTRATION_v4.md.

Cross-sectional momentum: long top 5, short bottom 5, rebalanced every 120 H4
bars on non-overlapping lookbacks. One pooled statistic.

--data and --seeds only. Nothing here changes the specification.
"""

from __future__ import annotations

import argparse
import os
import sys

VERSION = "4.0-prereg"

# ---- FROZEN SPEC ----------------------------------------------------------
LOOKBACK = 120        # H4 bars (~20 days); equals REBAL so windows never overlap
REBAL = 120
TOP = 5               # longs, and shorts
MIN_PANEL = 20        # instruments required to form a rank
VOL_WINDOW = 60       # for per-leg vol scaling
MAX_INSTRUMENT_SHARE = 0.25
MAX_YEAR_SHARE = 0.25
# ---------------------------------------------------------------------------


def build(data_dir):
    import numpy as np, pandas as pd
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import screen_universe as U
    s = U.load(data_dir)
    idx = None
    for v in s.values():
        idx = v.index if idx is None else idx.union(v.index)
    M = pd.DataFrame({U.LABEL[k]: v.reindex(idx) for k, v in s.items()}).sort_index()
    spread = pd.Series({U.LABEL[k]: U.SPREAD_REL[k] for k in s})
    return M, spread


def run(M, spread, mode="real", rng=None, charge_cost=True):
    """One row per rebalance. Returns the portfolio's net log return."""
    import numpy as np, pandas as pd

    L = np.log(M)
    # Compute momentum and vol on EACH INSTRUMENT'S OWN BARS, then align.
    # Doing it on the ragged union index means shift(120) spans 120 UNION
    # rows -- not 120 of that instrument's bars -- and rolling(60) needs 60
    # consecutive non-NaN rows. Instruments with different sessions (SMI,
    # AEX, FR40) then had NO valid vol at all and were silently excluded:
    # a "28-instrument" panel that was really ~18, almost all FX, from 2013.
    mom = pd.DataFrame(index=L.index, columns=L.columns, dtype=float)
    vol = pd.DataFrame(index=L.index, columns=L.columns, dtype=float)
    for c in L.columns:
        own = L[c].dropna()
        if len(own) < LOOKBACK + VOL_WINDOW + 2:
            continue
        mom[c] = (own - own.shift(LOOKBACK)).reindex(L.index).ffill()
        vol[c] = own.diff().rolling(VOL_WINDOW).std().reindex(L.index).ffill()
    ok = M.notna().sum(axis=1) >= MIN_PANEL
    pts = np.flatnonzero(ok.to_numpy())[::REBAL]

    rows, prev = [], {}
    for a in range(len(pts) - 1):
        i, j = pts[a], pts[a + 1]
        m = mom.iloc[i].dropna()
        v = vol.iloc[i]
        m = m[[c for c in m.index if np.isfinite(v.get(c, np.nan)) and v.get(c, 0) > 0]]
        if len(m) < MIN_PANEL:
            continue

        if mode == "rand":
            order = pd.Series(rng.permutation(len(m)), index=m.index)
        elif mode == "rev":
            order = -m.rank()
        else:
            order = m.rank()

        longs = list(order.nlargest(TOP).index)
        shorts = list(order.nsmallest(TOP).index)

        # forward log return over the holding period, per leg
        fwd = (L.iloc[j] - L.iloc[i])
        # vol-scale each leg to equal risk, then equal-weight the two sides
        w = {}
        for c in longs:
            w[c] = w.get(c, 0.0) + (1.0 / TOP) / v[c]
        for c in shorts:
            w[c] = w.get(c, 0.0) - (1.0 / TOP) / v[c]
        # normalise so gross risk is 1 unit, making rebalances comparable
        gross = sum(abs(x) for x in w.values())
        if gross <= 0:
            continue
        w = {c: x / gross for c, x in w.items()}

        ret = sum(w[c] * fwd[c] for c in w if np.isfinite(fwd.get(c, np.nan)))

        # cost: charge the CHANGE in each position, on the legs that moved
        cost = 0.0
        if charge_cost:
            keys = set(w) | set(prev)
            for c in keys:
                d = abs(w.get(c, 0.0) - prev.get(c, 0.0))
                cost += d * spread.get(c, 0.0)
        prev = w

        rows.append(dict(t=M.index[i], ret=ret, net=ret - cost, cost=cost,
                         n_panel=len(m),
                         longs=",".join(longs), shorts=",".join(shorts)))
    return pd.DataFrame(rows)


def main():
    import numpy as np, pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data_universe")
    ap.add_argument("--seeds", type=int, default=200)
    a = ap.parse_args()

    print(f"prereg_v4_test.py v{VERSION}   spec frozen in PREREGISTRATION_v4.md")
    print(f"  {LOOKBACK}-bar momentum rank, long top {TOP} / short bottom {TOP},")
    print(f"  rebalance every {REBAL} bars (~{REBAL*4/24:.0f}d), non-overlapping")
    print(f"  vol-scaled legs, measured spreads, 2 sigma\n")

    M, spread = build(a.data)
    r = run(M, spread, "real")
    print(f"  {M.shape[1]} instruments   {len(r)} rebalances   "
          f"{r.t.min().date()} -> {r.t.max().date()}")

    yrs = (r.t.max() - r.t.min()).days / 365.25
    rpy = len(r) / yrs
    mu, sd = r.net.mean(), r.net.std()
    sharpe = (mu / sd) * np.sqrt(rpy) if sd > 0 else 0.0

    print(f"\n{'='*72}\nPOOLED — the single pre-registered statistic\n{'='*72}")
    print(f"  mean gross per rebalance   {r.ret.mean():+.5f}")
    print(f"  mean cost  per rebalance   {r.cost.mean():+.5f}")
    print(f"  MEAN NET   per rebalance   {mu:+.5f}")
    boot = np.array([np.random.default_rng(k).choice(r.net.to_numpy(),
                     len(r), replace=True).mean() for k in range(1000)])
    lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
    print(f"  bootstrap 95% CI           [{lo:+.5f}, {hi:+.5f}]")
    print(f"  implied annual Sharpe      {sharpe:+.2f}   (bar: 0.44)")
    print(f"  positive rebalances        {(r.net>0).mean():.1%}")

    # concentration
    import collections
    contrib = collections.defaultdict(float)
    for _, row in r.iterrows():
        if row.net <= 0:
            continue
        for c in str(row.longs).split(",") + str(row.shorts).split(","):
            contrib[c] += row.net / (2 * TOP)
    tot = sum(contrib.values())
    ins_share = max(contrib.values()) / tot if tot > 0 else float("nan")
    top_ins = max(contrib, key=contrib.get) if contrib else "n/a"
    yr = r.assign(y=r.t.dt.year).groupby("y").net.apply(lambda v: v[v > 0].sum())
    year_share = yr.max() / yr.sum() if yr.sum() > 0 else float("nan")
    print(f"  top instrument             {top_ins} = {ins_share:.1%}")
    print(f"  top year                   {yr.idxmax()} = {year_share:.1%}")

    c1 = mu > 0 and lo > 0
    c2 = ins_share <= MAX_INSTRUMENT_SHARE and year_share <= MAX_YEAR_SHARE
    print(f"\n  1 profitable after costs (mean>0, CI lo>0)      "
          f"{'PASS' if c1 else 'FAIL'}")
    print(f"  2 not one instrument (<=25%) or year (<=25%)    "
          f"{'PASS' if c2 else 'FAIL'}")

    print(f"\n  --- diagnostic, NOT a criterion ---")
    rev = run(M, spread, "rev")
    rnd = [run(M, spread, "rand", np.random.default_rng(k)) for k in range(a.seeds)]
    rm = float(np.mean([x.net.mean() for x in rnd]))
    rs = float(np.std([x.net.mean() for x in rnd]))
    print(f"  real {mu:+.5f}   random {rm:+.5f} (sd {rs:.5f})   "
          f"reversed {rev.net.mean():+.5f}")
    if rs > 0:
        print(f"  real vs random: {(mu-rm)/rs:+.2f} sd")

    print(f"\n{'='*72}\nVERDICT\n{'='*72}")
    if c1 and c2:
        print("  H1 SUPPORTED at 2 sigma.")
        print("  Before ANY capital: re-run audit.py, then forward-test.")
        print("  A 2-sigma pass is 1-in-20 by chance and momentum is the most")
        print("  published anomaly in finance -- this is not a discovery.")
    else:
        print("  H1 REJECTED.")
        print("  Per PREREGISTRATION_v4.md: no cross-sectional edge at or above")
        print("  a gross annual Sharpe of ~0.46 on this universe. The line ends.")


if __name__ == "__main__":
    main()
