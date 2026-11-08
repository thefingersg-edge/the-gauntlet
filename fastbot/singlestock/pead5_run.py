#!/usr/bin/env python3
import os, sys, hashlib, datetime as dt, numpy as np
import ss_lib, ss_events2 as S, pead_engine as E
from batch2_run import pead1_longs, LOAD
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DOC = (os.path.join(FB, "PREREGISTRATION_PEAD5.md"), "6f84fda84659229262ec7c54e65c14c3bfeac0d29404dc2f830e92964589f44d")
SEAL = (dt.date(2023, 6, 30) - dt.date(1970, 1, 1)).days; OUT = []
def P(s=""): print(s, flush=True); OUT.append(s)
def mt(R): return E.clustered_mean_t([r["x"] - r["cost"] for r in R], [E.quarter(r["entry"]) for r in R])
def main():
    if not DOC[1] or hashlib.sha256(open(DOC[0], "rb").read()).hexdigest() != DOC[1]: sys.exit("doc not pinned/changed")
    log = os.path.join(FB, "data", "run_pead5.log")
    if os.path.exists(log): sys.exit("already run")
    P("pead5_run.py  PREREGISTRATION_PEAD5 pinned\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    band, bench = LOAD("band.pkl"), LOAD("bench.pkl"); bad, good = ss_lib.delistings(ss_lib.find("actions"))
    ev = [(e["t"], e["known"]) for e in pead1_longs()]; res = {}
    for H in (120, 90, 180):
        R = S.costs(S.study(ev, band, bench, bad, good, H=H, execution="open"), 1.0)
        main_ = [r for r in R if r["band"] in ("M", "S") and r["y"] >= 2005 and r["entry"] + int(H * 1.5) <= SEAL]
        late = [r for r in R if r["band"] in ("M", "S") and r["entry"] > SEAL]
        res[H] = (main_, late)
    main_, late = res[120]; m, t, n = mt(main_); g1 = m > 0 and t >= 2.0
    er = [mt([r for r in main_ if a <= r["y"] <= b]) for a, b in ((2005, 2012), (2013, 2017), (2018, 2023))]; g2 = all(e[0] > 0 for e in er)
    bm = {b: mt([r for r in main_ if r["band"] == b]) for b in ("M", "S")}; g3 = all(v[0] > 0 for v in bm.values())
    P(f"  G1 120d net {m*100:+.2f}% (t {t:+.2f}, n {n}); gross {np.mean([r['x'] for r in main_])*100:+.2f}%  -> {'PASS' if g1 else 'FAIL'}")
    P("  G2 eras " + "  ".join(f"{e[0]*100:+.2f}% (t {e[1]:+.2f})" for e in er) + f"  -> {'PASS' if g2 else 'FAIL'}")
    P("  G3 " + "  ".join(f"{b} {v[0]*100:+.2f}% (t {v[1]:+.2f})" for b, v in bm.items()) + f"  -> {'PASS' if g3 else 'FAIL'}")
    P("\n  reported:")
    for H in (90, 180):
        mm = mt(res[H][0]); P(f"    {H} days: net {mm[0]*100:+.2f}% (t {mm[1]:+.2f})")
    for H in (120,):
        mm = mt(res[H][1]) if res[H][1] else (np.nan, np.nan, 0); P(f"    entries after 2023-06 (not clean), 120d: net {mm[0]*100:+.2f}% (t {mm[1]:+.2f}, n {mm[2]})")
    P(f"\n  VERDICT PEAD5 G1 {'P' if g1 else 'F'} G2 {'P' if g2 else 'F'} G3 {'P' if g3 else 'F'} -> {'PASS' if g1 and g2 and g3 else 'FAIL'}")
    open(log, "w").write("\n".join(OUT) + "\n")
if __name__ == "__main__":
    main()
