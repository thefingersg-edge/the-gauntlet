#!/usr/bin/env python3
"""THE v3 pre-registered test. Spec frozen in PREREGISTRATION_v3.md.

Slow directional momentum, 28 instruments, pooled into one statistic.

One run. --data and --seeds are the only arguments; nothing here changes the
specification. If you want another flag, that impulse is what this file exists
to refuse.
"""

from __future__ import annotations

import argparse
import os
import sys

VERSION = "3.0-prereg"

# ---- FROZEN SPEC (PREREGISTRATION_v3.md) ----------------------------------
LOOKBACK = 60          # H4 bars, momentum z-score window
ENTRY_Z = 1.0          # loose on purpose; no mechanism for extremes trending more
HOLD = 60              # ~10 days; cost drag falls as ~1/hold
VOL_WINDOW = 14
SL_VOL = 2.90          # trend geometry, T/S = 3
TP_VOL = 8.71
BOOT_LO, BOOT_HI = 2.5, 97.5      # 95% CI  (2 sigma standard, per prereg)
MAX_INSTRUMENT_SHARE = 0.25
MAX_YEAR_SHARE = 0.25
# ---------------------------------------------------------------------------


def instrument_trades(price, spread_rel, mode, rng=None):
    """Slow momentum, TREND direction, asymmetric barriers, non-overlapping.

    Cost is charged once on entry and once on exit, as a fraction of price --
    NOT as a fixed dollar amount. A fixed dollar spread across 20 years is the
    error that made silver_mr.py's original config look catastrophic.
    """
    import numpy as np, pandas as pd

    idx = price.index
    p = pd.Series(np.log(price.to_numpy(float)), index=idx)
    r = p.diff()
    vol = r.rolling(VOL_WINDOW).std()
    z = (p - p.rolling(LOOKBACK).mean()) / p.rolling(LOOKBACK).std()

    zv = z.to_numpy()
    sides = np.zeros(len(idx), dtype=int)
    sides[zv >= ENTRY_Z] = 1            # TREND: follow the move, do not fade it
    sides[zv <= -ENTRY_Z] = -1
    if mode == "rev":
        sides = -sides
    elif mode == "rand":
        nz = sides != 0
        sides = sides.copy()
        sides[nz] = rng.choice([-1, 1], size=int(nz.sum()))

    lp = p.to_numpy()
    vv = vol.to_numpy()
    n, rows = len(idx), []

    kept, last = [], -10**9
    for i in np.flatnonzero(sides != 0):
        if i - last >= HOLD:
            kept.append(i); last = i

    for i in kept:
        if i + 1 >= n or not np.isfinite(vv[i]) or vv[i] <= 0:
            continue
        side = int(sides[i])
        tp, sl = TP_VOL * vv[i], SL_VOL * vv[i]
        end = min(i + 1 + HOLD, n)
        cum, outcome = 0.0, "time"
        for j in range(i + 1, end):
            step = lp[j] - lp[j - 1]
            if not np.isfinite(step):
                break
            cum += side * step
            # Record the ACTUAL level, not the barrier level. Snapping a
            # breach back to the barrier credits a loss of exactly -sl when
            # the bar in fact closed below it, and because the near stop is
            # hit ~3x more often than the far target the optimism is wildly
            # asymmetric: it manufactured +0.28 vol units per trade on a
            # DRIFTLESS random walk at zero cost. Verified by synthetic control.
            if cum <= -sl:
                outcome = "sl"; break
            if cum >= tp:
                outcome = "tp"; break
        pnl = cum - spread_rel            # round trip, fraction of price
        rows.append(dict(t=idx[i], pnl=pnl / vv[i], raw=pnl, win=int(pnl > 0),
                         outcome=outcome))
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["t", "pnl", "raw", "win", "outcome"])


def main():
    import numpy as np, pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data_universe")
    ap.add_argument("--seeds", type=int, default=50)
    a = ap.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import screen_universe as U

    print(f"prereg_v3_test.py v{VERSION}   spec frozen in PREREGISTRATION_v3.md")
    print(f"  momentum z over {LOOKBACK} H4 bars, |z|>={ENTRY_Z}, TREND direction")
    print(f"  barriers sl {SL_VOL} / tp {TP_VOL} vol (T/S=3), hold {HOLD} bars "
          f"(~{HOLD*4/24:.0f}d)")
    print(f"  break-even win rate ~25.6%   evidence standard: 2 sigma\n")

    s = U.load(a.data)
    print(f"  {len(s)} instruments\n")

    print(f"{'instrument':<12}{'trades':>8}{'win':>8}{'mean pnl':>11}{'sum':>9}")
    frames, per_ins = [], {}
    for k, v in sorted(s.items()):
        tr = instrument_trades(v, U.SPREAD_REL[k], "real")
        if len(tr) == 0:
            continue
        per_ins[U.LABEL[k]] = tr
        frames.append(tr.assign(ins=U.LABEL[k]))
        print(f"{U.LABEL[k]:<12}{len(tr):>8,}{tr.win.mean():>7.1%}"
              f"{tr.pnl.mean():>+11.4f}{tr.pnl.sum():>+9.1f}")

    pool = pd.concat(frames, ignore_index=True)
    print(f"\n{'='*72}\nPOOLED — the single pre-registered statistic\n{'='*72}")
    print(f"  trades                {len(pool):,}")
    print(f"  win rate              {pool.win.mean():.2%}  "
          f"(break-even ~25.6%)")
    print(f"  MEAN P&L              {pool.pnl.mean():+.4f} vol units")
    boot = np.array([np.random.default_rng(k).choice(
        pool.pnl.to_numpy(), len(pool), replace=True).mean() for k in range(1000)])
    lo, hi = float(np.percentile(boot, BOOT_LO)), float(np.percentile(boot, BOOT_HI))
    print(f"  bootstrap 95% CI      [{lo:+.4f}, {hi:+.4f}]")

    yrs = (pool.t.max() - pool.t.min()).days / 365.25
    tpy = len(pool) / yrs
    sharpe = (pool.pnl.mean() / pool.pnl.std()) * np.sqrt(tpy) if pool.pnl.std() > 0 else 0
    print(f"  implied annual Sharpe {sharpe:+.2f}   (bar for 2 sigma: ~0.44 net)")
    print(f"  outcomes              {pool.outcome.value_counts().to_dict()}")

    gp = {k: v.pnl[v.pnl > 0].sum() for k, v in per_ins.items()}
    tot = sum(gp.values())
    ins_share = max(gp.values()) / tot if tot > 0 else float("nan")
    yr = pool.assign(y=pool.t.dt.year).groupby("y").pnl.apply(lambda v: v[v > 0].sum())
    year_share = yr.max() / yr.sum() if yr.sum() > 0 else float("nan")
    print(f"  top instrument        {max(gp, key=gp.get)} = {ins_share:.1%} of gross positive")
    print(f"  top year              {yr.idxmax()} = {year_share:.1%} of gross positive")

    c1 = pool.pnl.mean() > 0 and lo > 0
    c2 = ins_share <= MAX_INSTRUMENT_SHARE and year_share <= MAX_YEAR_SHARE
    print(f"\n  1 profitable after costs (mean>0, CI lo>0)      "
          f"{'PASS' if c1 else 'FAIL'}")
    print(f"  2 not one instrument (<=25%) or year (<=25%)    "
          f"{'PASS' if c2 else 'FAIL'}")

    print(f"\n  --- diagnostic, NOT a criterion ---")
    rev = pd.concat([instrument_trades(v, U.SPREAD_REL[k], "rev")
                     for k, v in sorted(s.items())], ignore_index=True)
    wr = []
    for k in range(a.seeds):
        rng = np.random.default_rng(k)
        wr.append(pd.concat([instrument_trades(v, U.SPREAD_REL[i], "rand", rng)
                             for i, v in sorted(s.items())],
                            ignore_index=True).win.mean())
    mu, sd = float(np.mean(wr)), float(np.std(wr))
    print(f"  real {pool.win.mean():.2%}   random {mu:.2%} (sd {sd:.4f})"
          f"   reversed {rev.win.mean():.2%}")
    if sd > 0:
        print(f"  real vs random: {(pool.win.mean()-mu)/sd:+.2f} sd")

    print(f"\n{'='*72}\nVERDICT\n{'='*72}")
    if c1 and c2:
        print("  H1 SUPPORTED at 2 sigma. Slow directional momentum is")
        print("  profitable after measured costs on this universe.")
        print("  NEXT: forward-test before any capital. A 2-sigma pass is one")
        print("  in twenty by chance, and this is a widely-known effect.")
    else:
        print("  H1 REJECTED.")
        print("  Per PREREGISTRATION_v3.md this means: no edge at or above a")
        print("  gross annual Sharpe of ~0.57 on this universe and history.")
        print("  It does NOT mean no edge exists. The line ends here regardless.")


if __name__ == "__main__":
    main()
