#!/usr/bin/env python3
"""ARM B's own pre-registered kill conditions, from run1_armB.md.

It committed to these before any data was run. Honouring that commitment.
"""
import numpy as np, pandas as pd, engine, arm_b
from engine import _mean

def edge(ts):
    g = engine.g6_matched_control(ts)
    return g["edge_vs_control"], g["coverage"], len(ts)

print("KILL TEST 1 — the mirror test")
print("  'Run the same rules with the filter reversed: trades taken only when")
print("   ID >= +0.10 (trends built from a few jumps). The theory says these")
print("   should do worse than their matched control. If the reversed trades'")
print("   edge is equal to or above the strategy's edge, the filter is doing")
print("   nothing, and any profit is plain momentum.'\n")

arm_b.MIRROR = False
main = arm_b.run()
arm_b.MIRROR = True
mir = arm_b.run()
arm_b.MIRROR = False

e_main, c_main, n_main = edge(main)
e_mir, c_mir, n_mir = edge(mir)
print(f"  smooth-trend  (ID <= -0.10): edge vs control {e_main:+.5f}  "
      f"net/trade {_mean([t.net for t in main]):+.4%}  n={n_main}")
print(f"  jump-built    (ID >= +0.10): edge vs control {e_mir:+.5f}  "
      f"net/trade {_mean([t.net for t in mir]):+.4%}  n={n_mir}")
verdict = "FILTER DOES NOTHING — abandon, per its own rule" if e_mir >= e_main \
          else "filter survives the mirror test"
print(f"\n  VERDICT: {verdict}")

print("\nKILL TEST 2 — the monotone gradient")
print("  'Split all would-be trend trades into terciles of ID. Edge versus")
print("   control must rise from the highest-ID tercile to the lowest.'\n")
rows = []
for lo, hi, name in ((-1.01, -0.10, "low ID  (smoothest)"),
                     (-0.10, 0.05, "mid ID"),
                     (0.05, 1.01, "high ID (jumpiest)")):
    arm_b.MIRROR = False
    orig = arm_b.P["theta"]
    # take trades whose ID falls in the band by filtering after the fact
    ts = []
    for m in engine.MARKETS:
        import numpy as _np
        df = engine.load(m)
        c = df["close"]; lr = _np.log(c).diff()
        R = _np.log(c / c.shift(60)); d = _np.sign(R)
        ID = (d * ((lr < 0).rolling(60).sum() - (lr > 0).rolling(60).sum()) / 60)
        arm_b.P["theta"] = hi
        for t in arm_b.run_market(m):
            v = ID.get(t.entry_date - pd.Timedelta(days=0), np.nan)
            ts.append((t, v))
    arm_b.P["theta"] = orig
    sel = [t for t, v in ts if np.isfinite(v) and lo < v <= hi]
    if len(sel) < 50:
        rows.append((name, len(sel), np.nan)); continue
    e, _, _ = edge(sel)
    rows.append((name, len(sel), e))
for name, n, e in rows:
    print(f"  {name:<22} n={n:>5}  edge vs control {e:+.5f}" if np.isfinite(e)
          else f"  {name:<22} n={n:>5}  (too few)")
