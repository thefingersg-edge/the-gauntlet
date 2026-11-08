#!/usr/bin/env python3
"""POST-HOC, descriptive only (not in PREREGISTRATION_v52): is the 200-day MA's drawdown cut better than
random timing with the same time in market? Same 500-draw circular-shift null as G2, recording max DD."""
import numpy as np
from ma_overlay_v52 import Inst, delayed, stats, portfolio, STEMS
I = [Inst(s) for s in STEMS]; F = [i.flag(200) for i in I]
def run(idx, seed=52):
    rng = np.random.default_rng(seed); dd, sh = [], []
    for _ in range(500):
        nets = []
        for k in idx:
            f = F[k]; v = ~np.isnan(f); fv = f[v]; off = int(rng.integers(250, len(fv) - 250)); g = f.copy(); g[v] = np.roll(fv, off)
            nets.append(I[k].pnl(delayed(g, 2)))
        s = stats(*portfolio([I[k] for k in idx], nets)); dd.append(s["dd"]); sh.append(s["sh"])
    real = stats(*portfolio([I[k] for k in idx], [I[k].pnl(delayed(F[k], 2)) for k in idx]))
    dd = np.array(dd); sh = np.array(sh)
    return real, np.mean(dd <= real["dd"]), np.median(dd), np.mean(sh >= real["sh"]), np.median(sh)
for lab, idx in (("4-instrument portfolio", [0, 1, 2, 3]), ("SPX+NAS", [0, 1])):
    real, p_dd, med_dd, p_sh, med_sh = run(idx)
    print(f"{lab}: real DD {real['dd']*100:.1f}% vs null median {med_dd*100:.1f}% (share of nulls with a DEEPER DD: {p_dd:.0%});"
          f"  real Sharpe {real['sh']:+.3f} vs null median {med_sh:+.3f} (share of nulls >= real: {p_sh:.0%})")
