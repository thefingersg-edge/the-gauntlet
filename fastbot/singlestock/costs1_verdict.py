#!/usr/bin/env python3
"""COSTS1 verdict from data/costs1/measures.csv (PREREGISTRATION_COSTS1 + COSTS1.1). Read-only.
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, csv, numpy as np
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
R = [r for r in csv.DictReader(open(os.path.join(FB, "data", "costs1", "measures.csv"))) if r["status"] == "ok"]
rng = np.random.default_rng(20261003)
def med_ci(x):
    x = np.asarray(x, float); b = [np.median(rng.choice(x, len(x))) for _ in range(2000)]
    return np.median(x), np.quantile(b, 0.05), np.quantile(b, 0.95)
def show(name, x, pct=True):
    m, lo, hi = med_ci(x); f = (lambda v: f"{100*v:.3f}%") if pct else (lambda v: f"{v:.2f}")
    print(f"  {name:<34} median {f(m)}  90% CI [{f(lo)}, {f(hi)}]  n {len(x)}"); return m, lo, hi
print(f"COSTS1 route 1 verdict -- {len(R)} usable rows (M {sum(r['band']=='M' for r in R)}, S {sum(r['band']=='S' for r in R)})")
print("I am not a financial adviser. This is a measurement, not a recommendation.\n")
for lab, sub in (("ALL", R), ("M", [r for r in R if r["band"] == "M"]), ("S", [r for r in R if r["band"] == "S"])):
    print(lab)
    E = [r for r in sub if r["edge"] and float(r["edge"]) > 0]
    show("EDGE estimate (round trip)", [float(r["edge"]) for r in E])
    show("1 open quoted spread (round trip)", [float(r["open_spread"]) for r in sub])
    show("2 closing auction (round trip)", [float(r["auction_rt"]) for r in sub])
    show("   open / EDGE", [float(r["open_spread"]) / float(r["edge"]) for r in E], False)
    m = show("   auction / EDGE", [float(r["auction_rt"]) / float(r["edge"]) for r in E], False)
    if lab == "ALL": verdict = "ACCEPT auction model" if m[0] <= 0.50 else "KEEP full EDGE"
print(f"\nDECISION (median auction/EDGE <= 0.50): {verdict}")
