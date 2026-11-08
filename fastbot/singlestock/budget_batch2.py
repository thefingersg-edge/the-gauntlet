#!/usr/bin/env python3
"""Budgets for PEAD2 / PEAD3 / INSIDER1 / STRAT1 -- counts and squared returns only (no means printed)."""
import os, pickle, numpy as np
from collections import Counter
import ss_events2 as S
C = S.CACHE; L = lambda n: pickle.load(open(os.path.join(C, n), "rb"))
band, bench = L("band.pkl"), L("bench.pkl")
import ss_lib; bad, good = ss_lib.delistings(ss_lib.find("actions"))
def rep(name, recs):
    for lo, hi in ((2005, 2012), (2013, 2019), (2020, 2026), (2018, 2026)):
        x = [r["x"] for r in recs if r["band"] in ("M", "S") and lo <= r["y"] <= hi]
        if len(x) > 30:
            rms = float(np.sqrt(np.mean(np.square(x)))); wk = len({r["entry"] // 91 for r in recs if r["band"] in ("M", "S") and lo <= r["y"] <= hi})
            print(f"  {name} {lo}-{hi}: n {len(x):6,}  quarters {wk:3d}  60d excess RMS {rms*100:5.1f}%  MDE {2.8*rms/np.sqrt(len(x))*100:4.2f}% (event) .. {2.8*rms/np.sqrt(min(len(x), 4*wk))*100:4.2f}% (clustered guess)")
ins = L("insider_clusters.pkl")
recs = S.study(ins, band, bench, bad, good); pickle.dump(recs, open(os.path.join(C, "insider_recs.pkl"), "wb"))
print("INSIDER1 clusters with an outcome:", len(recs), " bands", dict(Counter(r["band"] for r in recs)))
rep("INSIDER1", recs)
sue = L("sue_events.pkl"); print("PEAD3: SUE events", len(sue), " by year", dict(sorted(Counter(int(str(np.datetime64(d, 'D'))[:4]) for _, d, _, _ in sue).items())))
