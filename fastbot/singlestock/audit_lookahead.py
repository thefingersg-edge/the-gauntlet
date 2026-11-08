#!/usr/bin/env python3
"""AUDIT 2026-10-04: does PEAD3/PEAD7 ever buy before the EAR signal is known? (filing on the 8-K day -> entry at the open of
day k+1, while EAR uses the close of k+1). Descriptive audit, not a test."""
import bisect, collections as C, numpy as np
import ss_events2 as S, batch2_run as B
from pead6_run import price
band, bench, bad, good = B.common(); L = B.pead1_longs(); sue = B.LOAD("sue_events.pkl")
by = C.defaultdict(list)
for t, d, rp, v in sue: by[t].append((d, v))
for t in by: by[t].sort()
thr = B.sue_threshold(sue, 0.7); meta = {}
for e in L:
    Z = by.get(e["t"], []); i = bisect.bisect_left(Z, (e["ad"], -1e18))
    if i < len(Z) and Z[i][0] <= e["ad"] + 60:
        d, v = Z[i]; th = thr(int(d))
        if np.isfinite(th) and v >= th: meta[(e["t"], int(d))] = (e["ad"], e["known"], e["entry"])
conf = [(t, d, 0) for (t, d) in meta]
R = price([r for r in S.study(conf, band, bench, bad, good, execution="open") if r["band"] in "MS"], {"M": 0.64, "S": 1.06})
for r in R:
    ad, kn, en = meta[(r["t"], r["sig"])]; r["early"] = r["entry"] <= kn; r["same"] = r["sig"] == ad
y = C.defaultdict(list)
for r in R: y[r["y"]].append(r)
print("year   n   early%  net_all  net_early  net_ok   day1-ok")
for k in sorted(y):
    a = y[k]; e = [r for r in a if r["early"]]; o = [r for r in a if not r["early"]]
    f = lambda s: 100 * np.mean([r["x"] - r["cost"] for r in s]) if s else float("nan")
    print(f"{k} {len(a):5d} {100*len(e)/len(a):6.1f} {f(a):+7.2f} {f(e):+9.2f} {f(o):+7.2f}")
E_ = [r for r in R if r["early"]]; O = [r for r in R if not r["early"]]
print("ALL: early", len(E_), "of", len(R), " net early", B.mt(E_), " net ok", B.mt(O))
for lo, hi in ((2005, 2012), (2013, 2019), (2020, 2026)): print(lo, hi, "ok-only", B.mt([r for r in O if lo <= r["y"] <= hi]))
print("2018+ ok-only", B.mt([r for r in O if r["y"] >= 2018]), " M ok", B.mt([r for r in O if r["band"] == "M"]), " S ok", B.mt([r for r in O if r["band"] == "S"]))
