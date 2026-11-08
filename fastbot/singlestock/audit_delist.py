#!/usr/bin/env python3
"""DESCRIPTIVE sensitivity (assumptions audit 2026-10-07): the -30% delisting-for-cause rule. Re-runs ss_events2.study with
the penalty at 0%, -30%, -60%, -100% on PEAD1 longs (M+S, entry k+2, 60d) and the corrected PEAD7c events. Verdicts unchanged."""
import inspect, bisect, collections as Cc, numpy as np
import ss_events2 as S, batch2_run as B, pead_engine as E
from pead6_run import price
assert 'delist = -0.30' in inspect.getsource(B._orig_study)
src = inspect.getsource(B._orig_study).replace("delist = -0.30", "delist = PEN")
ns = dict(S.__dict__); exec(src, ns); study = ns["study"]
band, bench, bad, good = B.common(); L = B.pead1_longs(); sue = B.LOAD("sue_events.pkl")
by = Cc.defaultdict(list)
for t, d, rp, v in sue: by[t].append((d, v))
for t in by: by[t].sort()
thr = B.sue_threshold(sue, 0.7); ev7 = []
for e in L:
    Z = by.get(e["t"], []); i = bisect.bisect_left(Z, (e["ad"], -1e18))
    if i < len(Z) and Z[i][0] <= e["ad"] + 60:
        d, v = Z[i]; th = thr(int(d))
        if np.isfinite(th) and v >= th: ev7.append((e["t"], max(int(d), int(e["known"]))))
ev7 = sorted(set(ev7)); ev1 = [(e["t"], e["known"]) for e in L]
for pen in (0.0, -0.30, -0.60, -1.00):
    ns["PEN"] = pen
    R1 = [r for r in study(ev1, band, bench, bad, good, execution="open") if r["band"] in "MS"]; S.costs(R1, 1.0)
    R7 = price([r for r in study(ev7, band, bench, bad, good, execution="open") if r["band"] in "MS"], {"M": 0.64, "S": 1.06})
    a = B.mt(R1); b = B.mt(R7)
    print(f"penalty {pen:+.0%}:  PEAD1 net {a[0]*100:+.2f}% (t {a[1]:+.2f})   PEAD7c net {b[0]*100:+.2f}% (t {b[1]:+.2f})")
