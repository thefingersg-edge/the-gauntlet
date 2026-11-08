#!/usr/bin/env python3
"""PEAD6 harness (PREREGISTRATION_PEAD6). One run.  SS_STORE=~/store python3 pead6_run.py
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, hashlib, numpy as np
import ss_lib, ss_events2 as S, pead_engine as E
import batch2_run as B
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DOC = (os.path.join(FB, "PREREGISTRATION_PEAD6.md"), "48272fdd4f01c87b18f17ae8c73c3ab1d66cbff1b9fa19526c9d0bb6ce455ce3")
def price(R, ratio):
    med = {}
    for b in ("M", "S"):
        v = [r["spread"] for r in R if r["band"] == b and np.isfinite(r["spread"])]; med[b] = float(np.median(v)) if v else 0.01
    for r in R:
        sp = r["spread"] if np.isfinite(r["spread"]) else med.get(r["band"], 0.01)
        r["cost"] = ratio.get(r["band"], 1.0) * sp + (r["comm"] if np.isfinite(r["comm"]) else 0)
    return R
def main():
    if not DOC[1] or hashlib.sha256(open(DOC[0], "rb").read()).hexdigest() != DOC[1]: sys.exit("doc not pinned/changed")
    log = os.path.join(FB, "data", "run_pead6.log")
    if os.path.exists(log): sys.exit("already run")
    P = B.P; P("pead6_run.py  PREREGISTRATION_PEAD6 pinned\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    band, bench, bad, good = B.common()
    L = B.pead1_longs(); sue = B.LOAD("sue_events.pkl"); conf, _ = B.pead3_events(L, sue)
    R = [r for r in S.study(conf, band, bench, bad, good, execution="close") if r["band"] in ("M", "S")]
    P(f"  events: {len(conf)} SUE-confirmed -> {len(R)} M+S with a closing-auction outcome")
    price(R, {"M": 0.11, "S": 0.25}); B.gates(R, B.ERAS, "PEAD6")
    P("\n  reported:")
    price(R, {"M": 0.10, "S": 0.20}); a = B.mt(R); P(f"    1 point ratios (M 0.10, S 0.20): net {a[0]*100:+.2f}% (t {a[1]:+.2f})")
    R120 = [r for r in S.study(conf, band, bench, bad, good, H=120, execution="close") if r["band"] in ("M", "S")]
    price(R120, {"M": 0.11, "S": 0.25}); a = B.mt(R120); b = B.mt([r for r in R120 if r["y"] >= 2018])
    P(f"    2 120-day hold, auction: net {a[0]*100:+.2f}% (t {a[1]:+.2f}, n {a[2]});  2018+ {b[0]*100:+.2f}% (t {b[1]:+.2f})")
    Ro = [r for r in S.study(conf, band, bench, bad, good, execution="open") if r["band"] in ("M", "S")]
    price(Ro, {"M": 1.12, "S": 1.94}); a = B.mt(Ro); b = B.mt([r for r in Ro if r["y"] >= 2018])
    P(f"    3 PEAD3 open entry at measured quoted open cost: net {a[0]*100:+.2f}% (t {a[1]:+.2f});  2018+ {b[0]*100:+.2f}% (t {b[1]:+.2f})")
    price(R, {"M": 0.11, "S": 0.25}); a = B.mt([r for r in R if r["band"] == "S" and r["y"] >= 2018])
    P(f"    4 S band 2018+, auction: net {a[0]*100:+.2f}% (t {a[1]:+.2f}, n {a[2]})")
    open(log, "w").write("\n".join(B.OUT) + "\n")
if __name__ == "__main__":
    main()
