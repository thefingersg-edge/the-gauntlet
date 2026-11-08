#!/usr/bin/env python3
"""THE v2 pre-registered test. Spec frozen in PREREGISTRATION_v2.md.

One run. One pooled statistic. No flags that change the specification --
--data and --seeds only. If you want another knob here, that impulse is what
this file exists to refuse.
"""

from __future__ import annotations

import argparse
import itertools
import os
import sys

VERSION = "2.0-prereg"

# ---- FROZEN SPEC ----------------------------------------------------------
BETA_WINDOW, RESID_WINDOW, Z_WINDOW = 120, 30, 120

# Beta clip bounds. The old (0.5, 4.0) was inherited from silver_mr.py, where
# silver-vs-gold beta is naturally ~1.4 and the floor never bound. Applied to
# cross-metal pairs it bound 84-98% of the time -- copper/palladium's natural
# beta is 0.166, so a 0.5 floor over-hedged it by 3x and the "residual" was a
# fixed blend, not a fitted hedge. Bounds now span the observed range with
# room to spare, and binding_rate() reports how often they actually bite so
# this cannot recur unnoticed.
BETA_LO, BETA_HI = 0.0, 6.0
ENTRY_Z = 2.0
TP = SL = 3.0                 # symmetric -> break-even 0.5 + C/(2B)
MAX_HOLD = 8                  # H4 bars, ~1.3 days
VOL_WINDOW = 14
EXCLUDE = {("xpdusd", "xptusd")}          # cost/vol 0.592, excluded on cost
COST_SCREEN = 0.35

SPREAD_REL = {
    "xauusd": 0.62000 / 4106.06, "xcuusd": 0.00199 / 6.29,
    "xagusd": 0.03600 / 59.97,   "xptusd": 2.19500 / 1634.59,
    "xpdusd": 2.96800 / 1253.83,
}
NAME = {"xagusd": "silver", "xauusd": "gold", "xptusd": "platinum",
        "xpdusd": "palladium", "xcuusd": "copper"}

MAX_PAIR_SHARE, MAX_YEAR_SHARE = 0.35, 0.30
# ---------------------------------------------------------------------------


def binding_rate(a, b):
    """How often the beta clip bites for this pair. Near 1.0 means the hedge
    is a constant, i.e. not a hedge."""
    import numpy as np, pandas as pd
    idx = a.index.intersection(b.index)
    ra = pd.Series(np.log(a.loc[idx].to_numpy(float)), index=idx).diff()
    rb = pd.Series(np.log(b.loc[idx].to_numpy(float)), index=idx).diff()
    raw = (ra.rolling(BETA_WINDOW).cov(rb)
           / rb.rolling(BETA_WINDOW).var().replace(0, np.nan)).dropna()
    if not len(raw):
        return float("nan"), float("nan")
    return float(raw.median()), float(((raw <= BETA_LO) | (raw >= BETA_HI)).mean())


def load(data_dir):
    import pandas as pd
    out = {}
    for stem in SPREAD_REL:
        p = os.path.join(data_dir, f"{stem}_4h.csv")
        d = pd.read_csv(p)
        t = d.columns[0]
        d[t] = pd.to_datetime(d[t], utc=True)
        out[stem] = d.set_index(t).sort_index()["close"]
    return out


def pair_trades(a, b, sa, sb, mode, rng=None):
    """mode: 'real' | 'rev' | 'rand'.  Returns a DataFrame of trades."""
    import numpy as np, pandas as pd

    idx = a.index.intersection(b.index)
    pa, pb = a.loc[idx], b.loc[idx]
    la, lb = np.log(pa.to_numpy(float)), np.log(pb.to_numpy(float))
    ra = pd.Series(la, index=idx).diff()
    rb = pd.Series(lb, index=idx).diff()
    beta = (ra.rolling(BETA_WINDOW).cov(rb)
            / rb.rolling(BETA_WINDOW).var().replace(0, np.nan)).clip(BETA_LO, BETA_HI)
    resid = ra - beta * rb
    svol = resid.rolling(VOL_WINDOW).std()
    cum = resid.rolling(RESID_WINDOW).sum()
    z = (cum - cum.rolling(Z_WINDOW).mean()) / cum.rolling(Z_WINDOW).std()

    zv = z.to_numpy()
    sides = np.zeros(len(idx), dtype=int)
    sides[zv <= -ENTRY_Z] = 1
    sides[zv >= ENTRY_Z] = -1
    if mode == "rev":
        sides = -sides
    elif mode == "rand":
        nz = sides != 0
        sides = sides.copy()
        sides[nz] = rng.choice([-1, 1], size=int(nz.sum()))

    bv, sv = beta.to_numpy(), svol.to_numpy()
    cost_side = sa / 2 + np.abs(bv) * sb / 2

    kept, last = [], -10**9
    for i in np.flatnonzero(sides != 0):
        if i - last >= MAX_HOLD:
            kept.append(i); last = i

    n, rows = len(idx), []
    for i in kept:
        if i + 1 >= n or not np.isfinite(sv[i]) or sv[i] <= 0 \
                or not np.isfinite(bv[i]):
            continue
        side, b = int(sides[i]), bv[i]
        tp, sl = TP * sv[i], SL * sv[i]
        end = min(i + 1 + MAX_HOLD, n)
        cumr, outcome = 0.0, "time"
        for j in range(i + 1, end):
            step = (la[j] - la[j - 1]) - b * (lb[j] - lb[j - 1])
            if not np.isfinite(step):
                break
            cumr += side * step
            # Record the ACTUAL level at the breach, not the barrier level.
            # Snapping biases P&L whenever barriers are ASYMMETRIC: the
            # near barrier is hit more often, so its understatement wins.
            # Symmetric barriers happen to cancel, which is why only the
            # asymmetric engines failed the synthetic control.
            if cumr <= -sl:
                outcome = "sl"; break
            if cumr >= tp:
                outcome = "tp"; break
        pnl = cumr - 2 * cost_side[i]
        rows.append(dict(t=idx[i], pnl=pnl / sv[i], win=int(pnl > 0),
                         outcome=outcome))
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["t", "pnl", "win", "outcome"])


def main():
    import numpy as np, pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data_h4")
    ap.add_argument("--seeds", type=int, default=50)
    a = ap.parse_args()

    print(f"prereg_v2_test.py v{VERSION}   spec frozen in PREREGISTRATION_v2.md")
    print(f"  entry |z|>={ENTRY_Z}   barriers +/-{TP}   hold {MAX_HOLD} H4 bars"
          f"   hedged, non-overlapping, POOLED")
    s = load(a.data)
    print(f"  {len(s)} metals, {min(len(v) for v in s.values()):,}"
          f"-{max(len(v) for v in s.values()):,} H4 bars each\n")

    pairs = [(x, y) for x, y in itertools.combinations(sorted(s), 2)
             if (x, y) not in EXCLUDE and (y, x) not in EXCLUDE]
    print(f"{'pair':<22}{'trades':>8}{'win':>8}{'mean pnl':>11}{'sum pnl':>10}")
    per_pair, frames = {}, []
    for x, y in pairs:
        tr = pair_trades(s[x], s[y], SPREAD_REL[x], SPREAD_REL[y], "real")
        key = f"{NAME[x]}/{NAME[y]}"
        per_pair[key] = tr
        tr = tr.assign(pair=key)
        frames.append(tr)
        print(f"{key:<22}{len(tr):>8,}{tr.win.mean():>7.1%}"
              f"{tr.pnl.mean():>+11.4f}{tr.pnl.sum():>+10.1f}")

    pool = pd.concat(frames, ignore_index=True)
    print(f"\n{'='*72}\nPOOLED — the single pre-registered statistic\n{'='*72}")
    print(f"  trades              {len(pool):,}")
    print(f"  win rate            {pool.win.mean():.2%}")
    print(f"  break-even win rate ~54.3% (barriers 3.0, measured cost)")
    print(f"  MEAN P&L            {pool.pnl.mean():+.4f} spread-vol units")

    boot = np.array([np.random.default_rng(k).choice(
        pool.pnl.to_numpy(), len(pool), replace=True).mean()
        for k in range(1000)])
    lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
    print(f"  bootstrap 95% CI    [{lo:+.4f}, {hi:+.4f}]")

    gp = {k: v.pnl[v.pnl > 0].sum() for k, v in per_pair.items()}
    tot = sum(gp.values())
    pair_share = max(gp.values()) / tot if tot > 0 else float("nan")
    top_pair = max(gp, key=gp.get)
    yr = pool.assign(y=pool.t.dt.year).groupby("y").pnl.apply(
        lambda v: v[v > 0].sum())
    year_share = yr.max() / yr.sum() if yr.sum() > 0 else float("nan")

    print(f"  top pair            {top_pair} = {pair_share:.1%} of gross positive")
    print(f"  top year            {yr.idxmax()} = {year_share:.1%} of gross positive")

    c1 = pool.pnl.mean() > 0 and lo > 0
    c2 = pair_share <= MAX_PAIR_SHARE and year_share <= MAX_YEAR_SHARE
    print(f"\n  1 profitable after costs (mean>0, CI lo>0)   {'PASS' if c1 else 'FAIL'}")
    print(f"  2 not one pair (<={MAX_PAIR_SHARE:.0%}) or year (<={MAX_YEAR_SHARE:.0%})"
          f"      {'PASS' if c2 else 'FAIL'}")

    # Diagnostic only -- explicitly NOT a success criterion.
    print(f"\n  --- diagnostic (not a criterion): direction ---")
    rev = pd.concat([pair_trades(s[x], s[y], SPREAD_REL[x], SPREAD_REL[y], "rev")
                     for x, y in pairs], ignore_index=True)
    wr = []
    for k in range(a.seeds):
        rng = np.random.default_rng(k)
        wr.append(pd.concat(
            [pair_trades(s[x], s[y], SPREAD_REL[x], SPREAD_REL[y], "rand", rng)
             for x, y in pairs], ignore_index=True).win.mean())
    mu, sd = float(np.mean(wr)), float(np.std(wr))
    print(f"  real {pool.win.mean():.2%}   random {mu:.2%} (sd {sd:.4f})"
          f"   reversed {rev.win.mean():.2%}")
    print(f"  real vs random: {(pool.win.mean()-mu)/sd:+.2f} sd")

    print(f"\n{'='*72}\nVERDICT\n{'='*72}")
    if c1 and c2:
        print("  H1 SUPPORTED. The basket is profitable after measured costs.")
        print("  Next: forward-test before any capital. Do not add a meta-model yet.")
    else:
        print("  H1 REJECTED.")
        print("  Power was adequate (1,277 effective vs 914 required), so this")
        print("  is INFORMATIVE, not inconclusive: the cross-metal residual")
        print("  does not pay retail spreads. Per the prereg, the line ends here.")


if __name__ == "__main__":
    main()
