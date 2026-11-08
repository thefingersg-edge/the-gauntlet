#!/usr/bin/env python3
"""PEAD1 budget -- counts and squared returns only, over ALL announcements (no EAR signal, no means printed).
Run after the 'events' stage; before freezing PREREGISTRATION_PEAD1."""
import os, pickle, numpy as np
from collections import defaultdict
C = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "sharadar", "cache")
ev = [e for f in sorted(os.listdir(C)) if f.startswith("events_") for e in pickle.load(open(os.path.join(C, f), "rb"))]
yr = lambda d: int(str(np.datetime64(int(d), "D"))[:4])
weeks = defaultdict(set)
print(f"announcements with a 60-day outcome: {sum('x60' in e for e in ev):,} (all bands, all years)")
for b in ("L", "M", "S", "X", "MS"):
    for lo, hi in ((2005, 2012), (2013, 2019), (2020, 2026), (2018, 2026), (2005, 2026)):
        x = [e["x60"] for e in ev if (e["band"] in ("M", "S") if b == "MS" else e["band"] == b) and "x60" in e and lo <= yr(e["entry"]) <= hi]
        wk = len({int(e["entry"]) // 7 for e in ev if (e["band"] in ("M", "S") if b == "MS" else e["band"] == b) and "x60" in e and lo <= yr(e["entry"]) <= hi})
        if len(x) < 50: continue
        rms = float(np.sqrt(np.mean(np.square(x)))); n10 = len(x) / 10
        # week-clustered: effective n between n10 and the number of entry weeks
        mde_lo, mde_hi = 2.8 * rms / np.sqrt(n10), 2.8 * rms / np.sqrt(min(n10, wk))
        print(f"  {b:<2} {lo}-{hi}: announcements {len(x):7,}  top decile ~{n10:6,.0f}  entry weeks {wk:5,}  60d excess RMS {rms*100:5.1f}%  MDE {mde_lo*100:4.2f}-{mde_hi*100:4.2f}%")
spr = [e["spread"] for e in ev if e["band"] in ("M", "S") and np.isfinite(e["spread"])]
print(f"  EDGE spread M+S: median {np.median(spr)*1e4:.0f} bp, 75th pct {np.quantile(spr, .75)*1e4:.0f} bp (cost estimate, not a return)")
