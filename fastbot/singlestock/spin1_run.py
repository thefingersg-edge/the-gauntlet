#!/usr/bin/env python3
"""SPIN1 harness (PREREGISTRATION_SPIN1). One run.  SS_STORE=~/store python3 spin1_run.py
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, io, subprocess, hashlib, pickle, bisect, datetime as dt, numpy as np
import ss_lib, ss_events2 as S, pead_engine as E
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); DOC = (os.path.join(FB, "PREREGISTRATION_SPIN1.md"), "81bb0b715127a40d3c0cc68d589922bbda24d0ca76e027d777a245b70aad59e0")
D0 = dt.date(1970, 1, 1); day = lambda s: (dt.date.fromisoformat(s) - D0).days
def outcome(t, sd, H, band, bench, bad, good):
    f = t.replace("/", "_") + ".npz"
    if not os.path.exists(os.path.join(S.STORE, f)): return None
    z = ss_lib.load(S.STORE, f); d = z["d"]; ca = z["ca"]; cu = z["cu"]; n = len(d)
    k = bisect.bisect_left(d, sd) + 1                                  # 2nd trading day on/after the action date
    if k >= n - 1: return None
    x = k + H; delist = 0.0
    if x >= n:
        if t in bad and t not in good: delist = -0.30
        x = n - 1
    g = (1 + delist) * ca[x] / ca[k] - 1
    bb = [np.mean([bench.get((int(d[j]), b), 0.0) for b in ("L", "M", "S")]) for j in range(k + 1, x + 1)]
    return dict(t=t, entry=int(d[k]), exit=int(d[x]), y=int(str(np.datetime64(int(d[k]), "D"))[:4]), g=float(g),
                x=float(g - (np.prod([1 + v for v in bb]) - 1)), cost=0.005 + 2 * 0.0035 / max(float(cu[k]), 0.01), days=int(x - k))
def main():
    if not DOC[1] or hashlib.sha256(open(DOC[0], "rb").read()).hexdigest() != DOC[1]: sys.exit("doc not pinned/changed")
    log = os.path.join(FB, "data", "run_spin1.log")
    if os.path.exists(log): sys.exit("already run")
    OUT = []; P = lambda s="": (print(s, flush=True), OUT.append(s))
    P("spin1_run.py  PREREGISTRATION_SPIN1 pinned\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    C = S.CACHE; band = pickle.load(open(os.path.join(C, "band.pkl"), "rb")); bench = pickle.load(open(os.path.join(C, "bench.pkl"), "rb"))
    bad, good = ss_lib.delistings(ss_lib.find("actions"))
    rows = list(csv.DictReader(io.StringIO(subprocess.run(["unzip", "-p", ss_lib.find("actions")], capture_output=True, text=True).stdout)))
    ev = sorted({(r["ticker"], day(r["date"]), r["contraticker"]) for r in rows if r["action"] == "spunofffrom"})
    def run(H, who=0):
        R = []
        for t, sd, par in ev:
            o = outcome(par if who else t, sd, H, band, bench, bad, good)
            if o: R.append(o)
        return R
    R = run(250); lo, hi = day("2013-01-01"), day("2025-09-30")
    M = [r for r in R if lo <= r["entry"] <= hi]; net = lambda L: [r["x"] - r["cost"] for r in L]
    m, t, n = E.clustered_mean_t(net(M), [E.quarter(r["entry"]) for r in M]); g1 = m > 0 and t >= 2.0
    e1 = [r for r in M if r["y"] <= 2019]; e2 = [r for r in M if r["y"] >= 2020]; g2 = np.mean(net(e1)) > 0 and np.mean(net(e2)) > 0
    P(f"  events {len(ev)} spunofffrom rows -> {len(R)} with prices; primary window n {n}")
    P(f"  G1 2013-01..2025-09 mean net excess {m*100:+.2f}%  t {t:+.2f}  (gross excess {np.mean([r['x'] for r in M])*100:+.2f}%)  -> {'PASS' if g1 else 'FAIL'}")
    P(f"  G2 2013-19 {np.mean(net(e1))*100:+.2f}% (n {len(e1)})   2020-25 {np.mean(net(e2))*100:+.2f}% (n {len(e2)})  -> {'PASS' if g2 else 'FAIL'}")
    P("\n  reported:")
    for a, b in ((1998, 2004), (2005, 2012)):
        L = [r for r in R if a <= r["y"] <= b]
        if L: mm = E.clustered_mean_t(net(L), [E.quarter(r["entry"]) for r in L]); P(f"    {a}-{b}: net {mm[0]*100:+.2f}% (t {mm[1]:+.2f}, n {mm[2]})")
    P(f"    primary: median net {np.median(net(M))*100:+.2f}%, share positive {100*np.mean(np.array(net(M))>0):.0f}%")
    R6 = [r for r in run(125) if lo <= r["entry"] <= hi]; mm = E.clustered_mean_t(net(R6), [E.quarter(r["entry"]) for r in R6]); P(f"    125-day hold: net {mm[0]*100:+.2f}% (t {mm[1]:+.2f})")
    RP = [r for r in run(250, 1) if lo <= r["entry"] <= hi]
    if RP: mm = E.clustered_mean_t(net(RP), [E.quarter(r["entry"]) for r in RP]); P(f"    parents, 250 days: net {mm[0]*100:+.2f}% (t {mm[1]:+.2f}, n {mm[2]})")
    P(f"\n  VERDICT SPIN1 G1 {'P' if g1 else 'F'} G2 {'P' if g2 else 'F'} -> {'PASS' if g1 and g2 else 'FAIL'}")
    open(log, "w").write("\n".join(OUT) + "\n")
if __name__ == "__main__": main()
