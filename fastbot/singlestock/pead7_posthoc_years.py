#!/usr/bin/env python3
"""DESCRIPTIVE ONLY (post hoc, not a test): PEAD7 by year -- what differs before 2013? I am not a financial adviser."""
import numpy as np, collections as C
import ss_events2 as S, batch2_run as B
from pead6_run import price
band, bench, bad, good = B.common(); conf, _ = B.pead3_events(B.pead1_longs(), B.LOAD("sue_events.pkl"))
Ro = {(r["t"], r["sig"]): r for r in S.study(conf, band, bench, bad, good, execution="open") if r["band"] in "MS"}
Rc = {(r["t"], r["sig"]): r for r in S.study(conf, band, bench, bad, good, execution="close") if r["band"] in "MS"}
R = list(Ro.values()); price(R, {"M": 0.64, "S": 1.06})
by = C.defaultdict(list)
for r in R: by[r["y"]].append(r)
print("year   n    S%   gross   day1   rest   cost   net    net_M   net_S  EDGE_med")
for y in sorted(by):
    L = by[y]; d1 = [r["x"] - Rc[(r["t"], r["sig"])]["x"] for r in L if (r["t"], r["sig"]) in Rc]
    m = lambda f, s=L: 100 * np.mean([f(r) for r in s]) if s else float("nan")
    M = [r for r in L if r["band"] == "M"]; Sb = [r for r in L if r["band"] == "S"]
    print(f"{y} {len(L):5d} {100*len(Sb)/len(L):4.0f} {m(lambda r:r['x']):+6.2f} {100*np.mean(d1):+6.2f} {m(lambda r:r['x'])-100*np.mean(d1):+6.2f} {m(lambda r:r['cost']):6.2f} {m(lambda r:r['x']-r['cost']):+6.2f} {m(lambda r:r['x']-r['cost'],M):+7.2f} {m(lambda r:r['x']-r['cost'],Sb):+7.2f} {100*np.nanmedian([r['spread'] for r in L]):6.2f}")
