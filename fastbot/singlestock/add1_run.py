#!/usr/bin/env python3
"""ADD1 harness (PREREGISTRATION_ADD1). One run on the sealed window.  SS_STORE=~/store python3 add1_run.py
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, hashlib, pickle, datetime as dt, numpy as np
import ss_lib, ss_events2 as S, batchB_engine as B, batchB_select as Sel, pead_engine as E
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DOC = (os.path.join(FB, "PREREGISTRATION_ADD1.md"), "ca59a6f6e368594804f376b342560c7831a92be89df14b71560654862f131614")
def main():
    if hashlib.sha256(open(DOC[0], "rb").read()).hexdigest() != DOC[1]: sys.exit("doc changed")
    log = os.path.join(FB, "data", "run_add1.log")
    if os.path.exists(log): sys.exit("already run")
    OUT = []; P = lambda s="": (print(s, flush=True), OUT.append(s))
    P("add1_run.py  PREREGISTRATION_ADD1 pinned\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    C = S.CACHE; band = pickle.load(open(os.path.join(C, "band.pkl"), "rb")); bench = pickle.load(open(os.path.join(C, "bench.pkl"), "rb"))
    bad, good = ss_lib.delistings(ss_lib.find("actions")); ev = Sel.select()
    lo = (dt.date(2023, 7, 1) - dt.date(1970, 1, 1)).days; hi = 10**9
    R = B.apply_cost(B.run(ev["B1add"], 60, band, bench, bad, good, lo, hi), 0.25)
    x = [r["x"] for r in R]; m, t, n = E.clustered_mean_t(x, [r["entry"] // 30 for r in R]); g1 = m < 0 and t <= -1.645
    sc = [r["x"] + r["cost"] + 0.001 for r in R]; m2, t2, _ = E.clustered_mean_t(sc, [r["entry"] // 30 for r in R]); g2 = m2 < 0
    P(f"  events {n} (entries {min(r['entry'] for r in R)} .. ; dates as days since 1970)")
    P(f"  G1 mean excess {m*100:+.2f}%  t {t:+.2f}  -> {'PASS' if g1 else 'FAIL'}")
    P(f"  G2 short P&L after costs = {-m2*100:+.2f}% per trade (mean cost {np.mean([r['cost'] for r in R])*100:.2f}% + 0.10% borrow)  -> {'PASS' if g2 else 'FAIL'}")
    P(f"  reported: share negative {100*np.mean(np.array(x) < 0):.0f}%; median {np.median(x)*100:+.2f}%; by year " + " ".join(f"{y}:{np.mean([r['x'] for r in R if r['y']==y])*100:+.2f}%(n{sum(r['y']==y for r in R)})" for y in sorted({r['y'] for r in R})))
    P(f"\n  VERDICT ADD1 G1 {'P' if g1 else 'F'} G2 {'P' if g2 else 'F'} -> {'PASS' if g1 and g2 else 'FAIL'}")
    open(log, "w").write("\n".join(OUT) + "\n")
if __name__ == "__main__": main()
