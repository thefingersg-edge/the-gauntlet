#!/usr/bin/env python3
"""Power budgets for v51-v53, written BEFORE any outcome is computed.
v51: counts of BOS/CHoCH events (prices used only to LOCATE events, never their aftermath) and the
     RMS of all 16-bar (4h) mid returns (squared returns only).  v52/v53: years and daily vol only."""
import sys, math
import numpy as np
from struct15 import load15, structure_events, STEMS

stems = sys.argv[1:] or STEMS
for s in stems:
    d = load15(s); c = d["c"]; n = len(c)
    r16 = np.log(c[16:] / c[:-16]) * 1e4; rms = float(np.sqrt(np.mean(r16 ** 2)))
    yrs = (d["t"][-1] - d["t"][0]).astype("int64") / 525960
    out = [f"{s}: bars {n:,} ({str(d['t'][0])[:10]}..{str(d['t'][-1])[:10]}, {yrs:.1f}y)  4h RMS {rms:.1f} bp  median spread {np.median(d['spr']):.2f} bp"]
    for k in (2, 3, 4, 5):
        ev = structure_events(d["h"], d["l"], c, k)
        nb = sum(1 for e in ev if e[1] == "BOS"); nc = len(ev) - nb
        # MDE per trade at t 2.24, 80% power, assuming roughly independent trades (overlap ignored -> optimistic)
        out.append(f"   k={k}: BOS {nb:,}  CHoCH {nc:,}   MDE/trade BOS {3.08 * rms / math.sqrt(max(nb,1)):.2f} bp  CHoCH {3.08 * rms / math.sqrt(max(nc,1)):.2f} bp")
    print("\n".join(out), flush=True)
