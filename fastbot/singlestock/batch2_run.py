#!/usr/bin/env python3
"""Harness for PEAD2 / PEAD3 / INSIDER1 / STRAT1 (each pre-registered and frozen 2026-10-03). Each test runs ONCE.
    SS_STORE=~/store python3 batch2_run.py pead2|pead3|insider1|strat1
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, pickle, hashlib, math, bisect
import numpy as np
from collections import defaultdict
import ss_lib, pead_engine as E, ss_events2 as S

PINS = {"pead2": ("../PREREGISTRATION_PEAD2.md", "c55ca77ca89556754f3bda358f95d92d92155be59fd6bcf39a021b428a3386e0"),
        "pead3": ("../PREREGISTRATION_PEAD3.md", "23419e48198a09522c7fbc8d59697e3056764f3ba35ffc7c9c418974de6154f5"),
        "insider1": ("../PREREGISTRATION_INSIDER1.md", "9a3c50c55dcd512e7fcee32446c91f0f720e41632a1733d7b386a905720faac9"),
        "strat1": ("../PREREGISTRATION_STRAT1.md", "e1f3bdddd308ac0fd5a4b8814265f774fe89e4e02753979ae528fff75012205d")}
CODE = {"ss_events2.py": "cf4bfa27d54c2a557f0759b6875eb52f88aef96b2eeba67c1c2e95e5d244fc13", "strat1_engine.py": "9b8dccf1e1a751219dae2360ccb306a2bc107932bdfb919951cfa94110d7a2f3", "pead_engine.py": "a9a48da76af824c69879aa0c1f8e89bd3de1740ac6e558ac8ad6ba560523d300"}
C = S.CACHE; LOAD = lambda n: pickle.load(open(os.path.join(C, n), "rb"))
OUT = []
_orig_study = S.study
def _cached_study(events, band, bench, bad, good, H=60, execution="open", known_lag=0):
    """memoise S.study on disk so a test can be prepared in several short calls; computes outcomes but PRINTS nothing."""
    import hashlib as _h
    key = _h.sha256(repr((sorted(map(tuple, [e[:2] for e in events]))[:50], len(events), H, execution, known_lag)).encode()).hexdigest()[:16]
    p = os.path.join(C, f"study_{key}.pkl")
    if os.path.exists(p): return pickle.load(open(p, "rb"))
    r = _orig_study(events, band, bench, bad, good, H=H, execution=execution, known_lag=known_lag)
    pickle.dump(r, open(p, "wb")); return r
S.study = _cached_study
def P(s=""): print(s, flush=True); OUT.append(s)

def check(test):
    log = os.path.join(S.D, "..", f"run_{test}.log")
    if os.path.exists(log): sys.exit(f"{test} already run once -- see {log}")
    f, h = PINS[test]
    if hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} changed -- refused")
    for f, h in CODE.items():
        if not h or hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} not pinned or changed -- refused")
    P(f"batch2_run.py {test}   pre-registration and code pins match\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    return log

def common():
    band, bench = LOAD("band.pkl"), LOAD("bench.pkl"); bad, good = ss_lib.delistings(ss_lib.find("actions"))
    return band, bench, bad, good

def pead1_longs():
    ev = [e for part in [LOAD(f) for f in sorted(os.listdir(C)) if f.startswith("events_")] for e in part]
    ev = E.signals(ev); yr = lambda d: int(str(np.datetime64(int(d), "D"))[:4])
    return [e for e in ev if e["long"] and e["band"] in ("M", "S") and yr(e["entry"]) >= 2005]

def mt(recs): return E.clustered_mean_t([r["x"] - r["cost"] for r in recs], [E.quarter(r["entry"]) for r in recs])

def calendar_sharpe(recs, lo_year=2018):
    daily = defaultdict(list)
    for r in recs:
        p = r["path"].astype(float).copy()
        if len(p) == 0: continue
        p[0] -= r["cost"]
        for dd, v in zip(r["dates"], p): daily[int(dd)].append(v)
    ds = sorted(d for d in daily if int(str(np.datetime64(d, "D"))[:4]) >= lo_year)
    x = np.array([np.mean(daily[d]) for d in ds])
    return (x.mean() / x.std() * math.sqrt(252) if len(x) > 50 and x.std() > 0 else float("nan")), len(x)

def gates(recs, eras, label=""):
    MS = [r for r in recs if r["band"] in ("M", "S")]
    m, t, n = mt(MS); g1 = m > 0 and t >= 2.0
    P(f"  G1 M+S net excess {m*100:+.2f}%  t {t:+.2f}  n {n}   (gross {np.mean([r['x'] for r in MS])*100:+.2f}%, mean cost {np.mean([r['cost'] for r in MS])*100:.2f}%)  -> {'PASS' if g1 else 'FAIL'}")
    es = [mt([r for r in MS if lo <= r["y"] <= hi]) for lo, hi in eras]; rc = mt([r for r in MS if r["y"] >= 2018])
    g2 = all(e[0] > 0 for e in es) and rc[0] > 0 and rc[1] >= 2.0
    P("  G2 eras " + "  ".join(f"{lo}-{hi % 100:02d} {e[0]*100:+.2f}% (t {e[1]:+.2f}, n {e[2]})" for (lo, hi), e in zip(eras, es)) + f"   2018-26 {rc[0]*100:+.2f}% (t {rc[1]:+.2f}, n {rc[2]})  -> {'PASS' if g2 else 'FAIL'}")
    bm = {b: mt([r for r in MS if r["band"] == b]) for b in ("M", "S")}; g3 = all(v[0] > 0 for v in bm.values())
    P("  G3 " + "  ".join(f"{b} {v[0]*100:+.2f}% (t {v[1]:+.2f}, n {v[2]})" for b, v in bm.items()) + f"  -> {'PASS' if g3 else 'FAIL'}")
    sh, nd = calendar_sharpe(MS); g5 = sh >= 0.5
    P(f"  G5 calendar-time excess Sharpe 2018+ {sh:+.2f} ({nd} days)  -> {'PASS' if g5 else 'FAIL'}")
    v = all((g1, g2, g3, g5)); P(f"\n  VERDICT {label} G1 {'P' if g1 else 'F'} G2 {'P' if g2 else 'F'} G3 {'P' if g3 else 'F'} G5 {'P' if g5 else 'F'} -> {'PASS' if v else 'FAIL'}")
    return v

ERAS = ((2005, 2012), (2013, 2019), (2020, 2026)); ERAS_I = ((2008, 2012), (2013, 2019), (2020, 2026))

def sue_threshold(sue, q):
    s = sorted((d, v) for _, d, _, v in sue); ds = [d for d, _ in s]; vs = [v for _, v in s]
    from functools import lru_cache
    @lru_cache(maxsize=None)
    def thr(day):          # memoised per day (identical values; speed only)
        lo, hi = bisect.bisect_left(ds, day - 91), bisect.bisect_left(ds, day)
        return float(np.quantile(vs[lo:hi], q)) if hi - lo >= 200 else np.nan
    return thr

def pead3_events(longs, sue):
    by = defaultdict(list)
    for t, d, rp, v in sue: by[t].append((d, v))
    for t in by: by[t].sort()
    thr = sue_threshold(sue, 0.7); out, unconf = [], []
    for e in longs:
        L = by.get(e["t"], []); i = bisect.bisect_left(L, (e["ad"], -1e18))
        if i < len(L) and L[i][0] <= e["ad"] + 60:
            d, v = L[i]; th = thr(int(d))
            (out if np.isfinite(th) and v >= th else unconf).append((e["t"], d, v))
    return out, unconf

def main():
    test = sys.argv[1] if len(sys.argv) > 1 else ""
    if test not in PINS: print(__doc__); return
    log = check(test); band, bench, bad, good = common()
    if test == "pead2":
        L = pead1_longs(); ev = [(e["t"], e["known"]) for e in L]
        R = S.study(ev, band, bench, bad, good, execution="close")
        P(f"  events: {len(L)} PEAD1 longs -> {len(R)} with a closing-auction outcome")
        S.costs(R, 0.25); gates(R, ERAS, "PEAD2")
        P("\n  reported: cost sensitivity (M+S)")
        for frac in (0.0, 0.5, 1.0):
            S.costs(R, frac); a = mt(R); b = mt([r for r in R if r["y"] >= 2018])
            P(f"    {frac:.0%} of EDGE: net {a[0]*100:+.2f}% (t {a[1]:+.2f});  2018+ {b[0]*100:+.2f}% (t {b[1]:+.2f})")
    elif test == "pead3":
        L = pead1_longs(); sue = LOAD("sue_events.pkl"); conf, unconf = pead3_events(L, sue)
        P(f"  PEAD1 longs {len(L)}: SUE-confirmed {len(conf)}, not confirmed {len(unconf)}, no SUE filing within 60d {len(L)-len(conf)-len(unconf)}")
        R = S.study(conf, band, bench, bad, good, execution="open"); S.costs(R, 1.0); gates(R, ERAS, "PEAD3")
        P("\n  reported:")
        Ra = S.study(conf, band, bench, bad, good, execution="close"); S.costs(Ra, 0.25); a = mt([r for r in Ra if r["band"] in "MS"]); b = mt([r for r in Ra if r["band"] in "MS" and r["y"] >= 2018])
        P(f"    closing auction, 25% cost: net {a[0]*100:+.2f}% (t {a[1]:+.2f});  2018+ {b[0]*100:+.2f}% (t {b[1]:+.2f})")
        Ru = S.study(unconf, band, bench, bad, good, execution="open"); S.costs(Ru, 1.0); u = [r for r in Ru if r["band"] in "MS"]
        P(f"    EAR long NOT confirmed by SUE: gross {np.mean([r['x'] for r in u])*100:+.2f}%  net {mt(u)[0]*100:+.2f}% (n {len(u)})")
        thr = sue_threshold(sue, 0.9); top = [(t, d, v) for t, d, rp, v in sue if d >= 12784 and np.isfinite(thr(int(d))) and v >= thr(int(d))]   # 2005+
        Rs = S.study(top, band, bench, bad, good, execution="open"); S.costs(Rs, 1.0); s_ = [r for r in Rs if r["band"] in "MS"]
        g = E.clustered_mean_t([r["x"] for r in s_], [E.quarter(r["entry"]) for r in s_])
        P(f"    SUE alone, top decile: gross {g[0]*100:+.2f}% (t {g[1]:+.2f})  net {mt(s_)[0]*100:+.2f}% (n {len(s_)})")
    elif test == "insider1":
        ev = LOAD("insider_clusters.pkl"); R = S.study(ev, band, bench, bad, good, execution="open"); S.costs(R, 1.0)
        gates(R, ERAS_I, "INSIDER1")
        P("\n  reported:")
        Lb = [r for r in R if r["band"] == "L"]; P(f"    L band: net {mt(Lb)[0]*100:+.2f}% (t {mt(Lb)[1]:+.2f}, n {len(Lb)})")
        Ra = S.study(ev, band, bench, bad, good, execution="close"); S.costs(Ra, 0.25); a = mt([r for r in Ra if r["band"] in "MS"]); b = mt([r for r in Ra if r["band"] in "MS" and r["y"] >= 2018])
        P(f"    closing auction, 25% cost: net {a[0]*100:+.2f}% (t {a[1]:+.2f});  2018+ {b[0]*100:+.2f}% (t {b[1]:+.2f})")
        R20 = S.study(ev, band, bench, bad, good, H=20, execution="open"); S.costs(R20, 1.0); P(f"    20-day hold: net {mt([r for r in R20 if r['band'] in 'MS'])[0]*100:+.2f}%")
        buys = LOAD("insider_buys.pkl"); cl = {(t, d) for t, d in ev}; singles = []
        for t, rows in buys.items():
            last = -10**9
            for d, o, v in rows:
                if (t, d) not in cl and v >= 50000 and d - last >= 60: singles.append((t, d)); last = d
        Rs = S.study(singles, band, bench, bad, good, execution="open"); S.costs(Rs, 1.0); s_ = [r for r in Rs if r["band"] in "MS"]
        P(f"    single-insider buys >= $50k (not clusters): gross {np.mean([r['x'] for r in s_])*100:+.2f}%  net {mt(s_)[0]*100:+.2f}% (t {mt(s_)[1]:+.2f}, n {len(s_)})")
    elif test == "strat1":
        import strat1_engine as ST
        ST.run(P, band, bench, bad, good)
    open(log, "w").write("\n".join(OUT) + "\n")

if __name__ == "__main__":
    main()
