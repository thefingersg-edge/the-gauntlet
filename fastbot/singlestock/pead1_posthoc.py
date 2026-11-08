#!/usr/bin/env python3
"""POST-HOC, DESCRIPTIVE ONLY (not in PREREGISTRATION_PEAD1): where does the gross drift sit, and what cost would it survive?"""
import os, pickle, numpy as np
import pead_engine as E
C = "../data/sharadar/cache"
ev = [e for f in sorted(os.listdir(C)) if f.startswith("events_") for e in pickle.load(open(os.path.join(C, f), "rb"))]
ev = E.fill_costs(E.signals(ev)); yr = lambda d: int(str(np.datetime64(int(d), "D"))[:4])
MS = [e for e in ev if e["long"] and "x60" in e and e["band"] in ("M", "S") and yr(e["entry"]) >= 2005]
mt = lambda S, f: E.clustered_mean_t([f(e) for e in S], [E.quarter(e["entry"]) for e in S])
for lab, S in (("2005-12", [e for e in MS if yr(e["entry"]) <= 2012]), ("2013-19", [e for e in MS if 2013 <= yr(e["entry"]) <= 2019]),
               ("2020-26", [e for e in MS if yr(e["entry"]) >= 2020]), ("2018-26", [e for e in MS if yr(e["entry"]) >= 2018])):
    g = mt(S, lambda e: e["x60"]); print(f"  gross {lab}: {g[0]*100:+.2f}% (t {g[1]:+.2f}, n {g[2]})   mean cost {np.mean([e['cost'] for e in S])*100:.2f}%")
for b in ("M", "S"):
    S = [e for e in MS if e["band"] == b]; g = mt(S, lambda e: e["x60"]); print(f"  gross band {b}: {g[0]*100:+.2f}% (t {g[1]:+.2f})  mean cost {np.mean([e['cost'] for e in S])*100:.2f}%")
for frac in (0.5, 0.25):
    v = mt(MS, lambda e: e["x60"] - frac * e["cost"]); v2 = mt([e for e in MS if yr(e["entry"]) >= 2018], lambda e: e["x60"] - frac * e["cost"])
    print(f"  if cost were {frac:.0%} of the estimate: net {v[0]*100:+.2f}% (t {v[1]:+.2f});  2018+ {v2[0]*100:+.2f}% (t {v2[1]:+.2f})")
q33 = np.quantile([x["cost"] for x in MS], 0.33); lo = [e for e in MS if e["cost"] <= q33]
v = mt(lo, lambda e: e["x60"] - e["cost"]); print(f"  cheapest third of trades by cost: net {v[0]*100:+.2f}% (t {v[1]:+.2f}, n {v[2]})")
