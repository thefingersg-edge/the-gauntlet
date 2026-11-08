#!/usr/bin/env python3
"""The sealed segment, every arm, on refreshed data.

SEALED WINDOW: 2026-08-29 to 2026-11-06.
Chosen because every one of the 21 daily files previously ended on or before
2026-08-28, so this window is unseen by the gate runs in RESULTS_ALL.md for
ALL markets, not just some. The ragged end dates are now gone: every file
ends 2026-11-06.
"""
import numpy as np, pandas as pd, engine, part_b
engine._cache.clear(); part_b._h1.clear()
import arm_a, arm_b, arm_c, arm_d, arm_e, arm_f

CUT = pd.Timestamp("2026-08-28", tz="UTC")
ARMS = [("A  Donchian 55/20", arm_a), ("B  path continuity", arm_b),
        ("C  ORB intraday", arm_c), ("D  v3 trend + index MR", arm_d),
        ("E  twin sleeve", arm_e), ("F  dip-buy (part A)", arm_f)]

print("SEALED SEGMENT  2026-08-29 .. 2026-11-06   (unseen by every gate run)\n")
print(f"  {'arm':<24} {'backtest/trade':>16} {'sealed/trade':>15} {'n':>5} {'ratio':>8}")
print("  " + "-" * 72)
for name, mod in ARMS:
    ts = mod.run()
    old = [t for t in ts if t.entry_date <= CUT]
    new = [t for t in ts if t.entry_date > CUT]
    bo = np.mean([t.net for t in old]) if old else np.nan
    bn = np.mean([t.net for t in new]) if new else np.nan
    ratio = (bn / bo) if (old and new and bo not in (0, np.nan)) else np.nan
    r = f"{ratio:+7.0%}" if np.isfinite(ratio) else "    n/a"
    s = f"{bn:+.4%}" if np.isfinite(bn) else " no trades"
    print(f"  {name:<24} {bo:+15.4%} {s:>15} {len(new):>5} {r:>8}")

print("\n  CAVEAT: ten weeks. ARM F's sample was already too small to conclude")
print("  from and most of these are smaller. A reading, not a result. The")
print("  registered twelve-month window is what settles it.")
