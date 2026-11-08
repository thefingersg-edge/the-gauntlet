#!/usr/bin/env python3
"""The sealed segment: 2026-08-08 to 2026-11-05.

Three months of real history that no gate run saw and that ARM F was never
fitted on. ARM F part A trades exactly the three markets we extended, so it
is the only arm that can be read cleanly here.
"""
import numpy as np, pandas as pd, engine, arm_f
engine._cache.clear()
CUT = pd.Timestamp("2026-08-07", tz="UTC")

ts = arm_f.run()
old = [t for t in ts if t.entry_date <= CUT]
new = [t for t in ts if t.entry_date > CUT]

def line(lbl, s):
    if not s:
        print(f"  {lbl:<34} no trades"); return
    n = [t.net for t in s]
    w = sum(1 for x in n if x > 0)
    print(f"  {lbl:<34} {len(s):>4} trades   net/trade {np.mean(n):+.4%}   "
          f"win {w/len(s):.0%}   best {max(n):+.2%}  worst {min(n):+.2%}")

print("ARM F part A — dip-buy, the only arm whose markets are all extended\n")
line("backtest  2005-01 .. 2026-08-07", old)
line("SEALED    2026-08-08 .. 2026-11-05", new)
print()
for m in arm_f.ARM_F_MARKETS:
    line(f"  sealed: {m}", [t for t in new if t.market == m])

if new:
    print(f"\n  sealed-segment gross {np.mean([t.gross for t in new]):+.4%}   "
          f"cost {np.mean([t.cost() for t in new]):.4%}")
    eq = (1 + pd.Series([t.net for t in sorted(new, key=lambda x: x.entry_date)])).cumprod()
    print(f"  compounded on notional over the segment: {eq.iloc[-1]-1:+.2%}")
    print(f"\n  backtest mean was +0.513%/trade. Sealed segment is "
          f"{np.mean([t.net for t in new])/0.00513:.0%} of that.")
