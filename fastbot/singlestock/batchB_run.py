#!/usr/bin/env python3
"""BATCHB harness.  python3 batchB_run.py main  (once)  |  python3 batchB_run.py sealed B?  (survivors only, once)"""
import os, sys, pickle, hashlib, datetime as dt
import numpy as np
from collections import defaultdict
import ss_lib, ss_events2 as S, batchB_engine as B, batchB_select as Sel, pead_engine as E
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PINS = {os.path.join(FB, "PREREGISTRATION_BATCHB.md"): "b2c39827fd9d53dd6d0d0fae0963691fe04c2205387053ccc277ec37eb35627c", "batchB_engine.py": "a02360b27a7e6f33a76983de7002e9478a93445f9e96d04ef5cad7641a191fc9", "batchB_select.py": "b75648889a990d0cbba1079e51ffb278026f72779ad69b8557b228584599c476"}
C = S.CACHE; T = 2.50; OUT = []
def P(s=""): print(s, flush=True); OUT.append(s)

def ct(recs, unit):
    return E.clustered_mean_t([r["x"] - r["cost"] for r in recs], [r["entry"] // unit for r in recs])

def evaluate(k, R, sealed=False):
    unit = Sel.SPECS[k]["unit"]; B.apply_cost(R, 0.25); MS = R if k == "B1" else [r for r in R if r["band"] in ("M", "S")]
    m, t, n = ct(MS, unit)
    if sealed:
        ok = m > 0 and t >= 1.0; P(f"  {k} SEALED 2023-07 -> 2026-09: net {m*100:+.2f}% (t {t:+.2f}, n {n})  -> {'CONFIRMED' if ok else 'NOT CONFIRMED'}"); return ok
    g = np.mean([r["x"] for r in MS]); g1 = m > 0 and t >= T
    er = [ct([r for r in MS if a <= r["y"] <= b], unit) for a, b in ((2005, 2012), (2013, 2017), (2018, 2023))]; g2 = all(e[0] > 0 for e in er)
    if k == "B1": g3 = True; bands = "n/a"
    else:
        bm = {b: ct([r for r in MS if r["band"] == b], unit) for b in ("M", "S")}; g3 = all(v[0] > 0 for v in bm.values())
        bands = "  ".join(f"{b} {v[0]*100:+.2f}% (t {v[1]:+.2f})" for b, v in bm.items())
    B.apply_cost(R, 0.5); m50 = ct(MS, unit)[0]; g4 = m50 > 0; B.apply_cost(R, 0.25)
    ok = g1 and g2 and g3 and g4
    P(f"  {k}: n {n:,}  gross {g*100:+.3f}%  net(25%) {m*100:+.3f}% (t {t:+.2f})  G1 {'P' if g1 else 'F'}")
    P(f"      eras " + "  ".join(f"{e[0]*100:+.3f}% (t {e[1]:+.2f})" for e in er) + f"  G2 {'P' if g2 else 'F'}   |  bands {bands}  G3 {'P' if g3 else 'F'}   |  net at 50% {m50*100:+.3f}%  G4 {'P' if g4 else 'F'}   -> {'PASS' if ok else 'FAIL'}")
    return ok

def main():
    for f, h in PINS.items():
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} changed or not pinned -- refused")
    mode = sys.argv[1]; log = os.path.join(FB, "data", "run_batchB.log")
    if mode == "main":
        if os.path.exists(log): sys.exit("main already run")
        P("batchB_run.py main  (entries 2005-01 .. exits 2023-06-30)  pins match\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
        res = {}
        for k in ("B1", "B2", "B3", "B4"):
            R = pickle.load(open(os.path.join(C, f"batchB_{k}_main.pkl"), "rb")); res[k] = evaluate(k, R)
        P("\n  reported:")
        for k in ("B2", "B3", "B4"):
            R = [r for r in pickle.load(open(os.path.join(C, f"batchB_{k}_main.pkl"), "rb")) if r["band"] in ("M", "S")]
            for frac in (0.0, 1.0):
                B.apply_cost(R, frac); m, t, _ = ct(R, Sel.SPECS[k]["unit"]); P(f"    {k} at {frac:.0%} of EDGE: net {m*100:+.3f}% (t {t:+.2f})")
        band = pickle.load(open(os.path.join(C, "band.pkl"), "rb")); bench = pickle.load(open(os.path.join(C, "bench.pkl"), "rb")); bad, good = ss_lib.delistings(ss_lib.find("actions"))
        ev = Sel.select(); lo = (dt.date(2005, 1, 1) - dt.date(1970, 1, 1)).days; hi = (dt.date(2023, 6, 30) - dt.date(1970, 1, 1)).days
        A = B.apply_cost(B.run(ev["B1add"], 60, band, bench, bad, good, lo, hi), 0.25); m, t, n = ct(A, 91)
        P(f"    B1 additions (60d): net {m*100:+.2f}% (t {t:+.2f}, n {n})")
        P("\n  VERDICTS  " + "   ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in res.items()))
        open(log, "w").write("\n".join(OUT) + "\n")
    elif mode == "sealed":
        k = sys.argv[2]; txt = open(log).read()
        if f"{k} PASS" not in txt.split("VERDICTS")[-1]: sys.exit(f"{k} did not pass -- no sealed run")
        slog = os.path.join(FB, "data", f"run_batchB_sealed_{k}.log")
        if os.path.exists(slog): sys.exit("sealed already run")
        band = pickle.load(open(os.path.join(C, "band.pkl"), "rb")); bench = pickle.load(open(os.path.join(C, "bench.pkl"), "rb")); bad, good = ss_lib.delistings(ss_lib.find("actions"))
        ev = Sel.select(); lo = (dt.date(2023, 7, 1) - dt.date(1970, 1, 1)).days; hi = (dt.date(2026, 9, 30) - dt.date(1970, 1, 1)).days
        R = [r for r in B.run(ev[k], Sel.SPECS[k]["H"], band, bench, bad, good, lo, hi) if k == "B1" or r["band"] in ("M", "S")]
        evaluate(k, R, sealed=True); open(slog, "w").write("\n".join(OUT) + "\n")

if __name__ == "__main__":
    main()
