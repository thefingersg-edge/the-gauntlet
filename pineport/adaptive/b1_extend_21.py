#!/usr/bin/env python3
"""Re-run the converging-trendline detector on all 21 markets.

b1_events.csv was produced with core.MARKETS, which holds 11 markets, while
b2_events.csv covers all 21. That left episode 1 claiming "twenty-one markets,
including rates and softs" for a family that contained neither.

This reuses b1_shapes.detect() unchanged, at its default parameters, and
writes b1_events_21.csv -- the original file is NOT touched, because it is the
pre-registered result and the 21-market run is a new, larger test.

Before trusting the extension it reproduces the original 11 markets bit for
bit. If that check fails the parameters differ and nothing else here is safe.
"""
import os, sys
import numpy as np
import pandas as pd

os.chdir(os.path.expanduser("~/mnt/Claude/pineport/adaptive"))
sys.path.insert(0, ".")
import core
from b1_shapes import detect, FWD

MARKETS = sorted(f[:-7] for f in os.listdir("data") if f.endswith("_d1.csv"))
ERAS = {n: (pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC"))
        for n, (a, b) in core.ERAS.items()}

out = []
for i, m in enumerate(MARKETS, 1):
    df = core.load(m)
    ev = detect(df)                       # default k=3, conv=0.7, lookback=120
    ev["market"] = m
    ev["era"] = [next((n for n, (a, b) in ERAS.items() if a <= d <= b), None)
                 for d in ev.date]
    out.append(ev)
    print(f"[{i:>2}/{len(MARKETS)}] {m:<10} {len(ev):>5} detections", flush=True)

E = pd.concat(out, ignore_index=True)
E["norm"] = E.fwd.abs() / (E.vol * np.sqrt(FWD))
E = E[["t", "date", "kind", "prior", "breakout", "fwd", "vol", "span",
       "compression", "market", "era", "norm"]]

# ---- reproduction check against the original 11-market file -----------------
old = pd.read_csv("b1_events.csv")
old_m = sorted(set(old.market))
new_sub = E[E.market.isin(old_m)].reset_index(drop=True)
ok = len(new_sub) == len(old)
detail = f"rows new={len(new_sub)} old={len(old)}"
if ok:
    for col in ("t", "kind", "prior", "market"):
        same = (new_sub[col].values == old[col].values).all()
        ok &= bool(same)
        if not same:
            detail += f" | MISMATCH in {col}"
    for col in ("fwd", "vol", "compression"):
        close = np.allclose(new_sub[col].values, old[col].values,
                            rtol=1e-9, atol=1e-12, equal_nan=True)
        ok &= bool(close)
        if not close:
            detail += f" | MISMATCH in {col}"
print()
print("REPRODUCTION CHECK:", "PASS" if ok else "FAIL", "-", detail)
if not ok:
    sys.exit("refusing to write b1_events_21.csv - detector does not reproduce "
             "the original 11-market result at these parameters")

E.to_csv("b1_events_21.csv", index=False)
print(f"wrote b1_events_21.csv  {len(E)} detections, {E.market.nunique()} markets")
print(f"  was {len(old)} detections over {len(old_m)} markets")
print(E.groupby("kind").size().to_string())
