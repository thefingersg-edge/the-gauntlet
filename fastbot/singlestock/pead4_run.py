#!/usr/bin/env python3
import os, sys, pickle, hashlib, bisect, datetime as dt
import numpy as np
import ss_lib, ss_events2 as S, pead_engine as E
from batch2_run import pead1_longs, sue_threshold, LOAD
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DOC = (os.path.join(FB, "PREREGISTRATION_PEAD4.md"), "d79d7c1a1ddf13535b4bdbc195a093f0beca71053b3570a01a018bde2f97ac96")
OUT = []
def P(s=""): print(s, flush=True); OUT.append(s)
SEAL = (dt.date(2023, 6, 30) - dt.date(1970, 1, 1)).days

def main():
    if not DOC[1] or hashlib.sha256(open(DOC[0], "rb").read()).hexdigest() != DOC[1]: sys.exit("doc not pinned/changed")
    log = os.path.join(FB, "data", "run_pead4.log")
    if os.path.exists(log): sys.exit("already run")
    P("pead4_run.py  PREREGISTRATION_PEAD4 pinned\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    band, bench = LOAD("band.pkl"), LOAD("bench.pkl"); bad, good = ss_lib.delistings(ss_lib.find("actions"))
    L = pead1_longs(); sue = LOAD("sue_events.pkl"); by = {}
    for t, d, rp, v in sue: by.setdefault(t, []).append((d, v))
    for t in by: by[t].sort()
    thr = sue_threshold(sue, 0.7); ev = []
    for e in L:
        Z = by.get(e["t"], []); i = bisect.bisect_left(Z, (e["ad"], -1e18))
        if i < len(Z) and Z[i][0] <= e["ad"] + 60:
            d, v = Z[i]; th = thr(int(d))
            if np.isfinite(th): ev.append((e["t"], d, "C" if v >= th else "U", e["ad"], e["known"]))
    R = S.costs(S.study([(t, d, g) for t, d, g, a, k in ev], band, bench, bad, good, execution="open"), 1.0)
    for r in R: r["net"] = r["x"] - r["cost"]; r["g_"] = r["extra"][0]
    main_ = [r for r in R if r["band"] in ("M", "S") and r["y"] >= 2005 and r["entry"] + 90 <= SEAL]
    # H4a: difference regression
    y = np.array([r["net"] for r in main_]); dmy = np.array([1.0 if r["g_"] == "C" else 0.0 for r in main_]); cl = [E.quarter(r["entry"]) for r in main_]
    def diff(sub):
        yy = np.array([r["net"] for r in sub]); dd = np.array([1.0 if r["g_"] == "C" else 0.0 for r in sub]); cc = [E.quarter(r["entry"]) for r in sub]
        X = np.column_stack([np.ones(len(yy)), dd]); b = np.linalg.lstsq(X, yy, rcond=None)[0]; u = yy - X @ b
        from collections import defaultdict
        G = defaultdict(lambda: np.zeros(2))
        for xi, ui, ci in zip(X, u, cc): G[ci] += xi * ui
        XtXi = np.linalg.inv(X.T @ X); M = sum(np.outer(g, g) for g in G.values()); V = XtXi @ M @ XtXi
        return b[1], b[1] / np.sqrt(V[1, 1]), len(sub)
    b, t, n = diff(main_); er = [diff([r for r in main_ if a <= r["y"] <= c]) for a, c in ((2005, 2012), (2013, 2017), (2018, 2023))]
    h4a = b > 0 and t >= 2.24 and all(e[0] > 0 for e in er)
    for g in ("C", "U"):
        s_ = [r for r in main_ if r["g_"] == g]; m = E.clustered_mean_t([r["net"] for r in s_], [E.quarter(r["entry"]) for r in s_]); P(f"  {'confirmed' if g == 'C' else 'not confirmed'}: net {m[0]*100:+.2f}% (t {m[1]:+.2f}, n {m[2]})")
    P(f"  H4a confirmed minus not: {b*100:+.2f}%  t {t:+.2f}  n {n}   eras " + " ".join(f"{e[0]*100:+.2f}(t {e[1]:+.2f})" for e in er) + f"  -> {'PASS' if h4a else 'FAIL'}")
    # H4b: early window from PEAD1 entry (open k+2) to close of filing day
    early = []
    for t_, d, g, ad, known in ev:
        f = t_.replace("/", "_") + ".npz"; z = ss_lib.load(S.STORE, f); dd = z["d"]; ca = z["ca"]; o = z["o"]; c = z["c"]
        k1 = bisect.bisect_left(dd, known); e0 = k1 + 1; fi = bisect.bisect_left(dd, d)
        if e0 >= len(dd) or fi >= len(dd) or fi <= e0: continue
        b_ = band.get((f, int(E.month_of(dd[k1]))))
        if b_ not in ("M", "S") or dd[fi] > SEAL or dd[e0] < 12784: continue
        px0 = o[e0] * ca[e0] / c[e0]; gr = ca[fi] / px0 - 1
        bb = [bench.get((int(dd[j]), b_), 0.0) for j in range(e0, fi + 1)]
        early.append((gr - (np.prod([1 + v for v in bb]) - 1), E.quarter(dd[e0]), g))
    m = E.clustered_mean_t([x for x, _, _ in early], [q for _, q, _ in early]); h4b = m[0] < 0 and m[1] <= -2.24
    P(f"  H4b early window (PEAD1 entry -> filing day): {m[0]*100:+.2f}%  t {m[1]:+.2f}  n {m[2]}  -> {'PASS' if h4b else 'FAIL'}")
    for g in ("C", "U"):
        xs = [x for x, _, gg in early if gg == g]; P(f"    early window, {'confirmed' if g == 'C' else 'not confirmed'}: {np.mean(xs)*100:+.2f}% (n {len(xs)})")
    late = [r for r in R if r["band"] in ("M", "S") and r["entry"] > SEAL]
    for g in ("C", "U"):
        s_ = [r for r in late if r["g_"] == g]
        if s_: P(f"    reported, entries after 2023-06 ({'confirmed' if g == 'C' else 'not'}): net {np.mean([r['net'] for r in s_])*100:+.2f}% (n {len(s_)})")
    P(f"\n  VERDICTS  H4a {'PASS' if h4a else 'FAIL'}   H4b {'PASS' if h4b else 'FAIL'}")
    open(log, "w").write("\n".join(OUT) + "\n")

if __name__ == "__main__":
    main()
