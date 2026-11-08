#!/usr/bin/env python3
"""PEAD7c -- BUG-CORRECTED re-run of PEAD3/PEAD7 (audit 2026-10-04: 32% of trades bought at the open of the day whose close
completes the EAR signal). Correction: entry = opening auction of the first day AFTER both the filing and the EAR known date.
Same events, gates, costs as PEAD7. Plus a DESCRIPTIVE holding-period curve (days 1..120). I am not a financial adviser."""
import bisect, collections as C, numpy as np
import ss_events2 as S, batch2_run as B
from pead6_run import price
RATIO = {"M": 0.64, "S": 1.06}
band, bench, bad, good = B.common(); L = B.pead1_longs(); sue = B.LOAD("sue_events.pkl")
by = C.defaultdict(list)
for t, d, rp, v in sue: by[t].append((d, v))
for t in by: by[t].sort()
thr = B.sue_threshold(sue, 0.7); ev = []
for e in L:
    Z = by.get(e["t"], []); i = bisect.bisect_left(Z, (e["ad"], -1e18))
    if i < len(Z) and Z[i][0] <= e["ad"] + 60:
        d, v = Z[i]; th = thr(int(d))
        if np.isfinite(th) and v >= th: ev.append((e["t"], max(int(d), int(e["known"]))))
ev = sorted(set(ev))
R = price([r for r in S.study(ev, band, bench, bad, good, execution="open") if r["band"] in "MS"], RATIO)
B.P(f"PEAD7c (corrected entry): {len(ev)} events -> {len(R)} M+S"); B.gates(R, B.ERAS, "PEAD7c")
B.P("\n  reported: S 2018+ " + str(B.mt([r for r in R if r["band"] == "S" and r["y"] >= 2018])))
# holding-period curve (descriptive), 120-day paths
R120 = price([r for r in S.study(ev, band, bench, bad, good, H=120, execution="open") if r["band"] in "MS"], RATIO)
P = [np.cumprod(1 + r["rpath"].astype(float)) - np.cumprod(1 + (r["rpath"] - r["path"]).astype(float)) for r in R120 if len(r["path"]) >= 120]
A = np.array([p[:120] for p in P]); cost = np.mean([r["cost"] for r in R120]); m = A.mean(0)
B.P(f"\n  holding curve (n {len(A)} full 120-day paths, mean cost {cost*100:.2f}%): day: mean cum excess | net | net per day")
for h in (1, 2, 5, 10, 20, 30, 40, 60, 80, 100, 120):
    B.P(f"    {h:3d}: {m[h-1]*100:+6.2f}% | {(m[h-1]-cost)*100:+6.2f}% | {(m[h-1]-cost)/h*100:+.4f}%")
pk = np.argmax(A, axis=1) + 1
B.P(f"  day of each trade's own peak: median {np.median(pk):.0f}, mean {pk.mean():.0f}; share peaking in days 1-5 {100*np.mean(pk<=5):.0f}%, days 116-120 {100*np.mean(pk>=116):.0f}%")
B.P(f"  mean-curve peak: day {int(np.argmax(m))+1} ({m.max()*100:+.2f}%)")
for lo, hi in ((2005, 2012), (2013, 2019), (2020, 2026)):
    Ae = np.array([p[:120] for p, r in zip(P, [r for r in R120 if len(r['path']) >= 120]) if lo <= r["y"] <= hi]); me = Ae.mean(0)
    B.P(f"    {lo}-{hi}: cum excess d20 {me[19]*100:+.2f}%  d60 {me[59]*100:+.2f}%  d120 {me[119]*100:+.2f}%  peak day {int(np.argmax(me))+1}")
open("../data/run_pead7c.log", "w").write("\n".join(B.OUT) + "\n")
