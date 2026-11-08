#!/usr/bin/env python3
"""PEAD7 harness (PREREGISTRATION_PEAD7). One run.  SS_STORE=~/store python3 pead7_run.py
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, hashlib
import ss_events2 as S
import batch2_run as B
from pead6_run import price
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DOC = (os.path.join(FB, "PREREGISTRATION_PEAD7.md"), "101b6b1152a07bd163b4db9368f0a2695e14eca599b1e0ef14b9cdb8702f84ab")
def main():
    if not DOC[1] or hashlib.sha256(open(DOC[0], "rb").read()).hexdigest() != DOC[1]: sys.exit("doc not pinned/changed")
    log = os.path.join(FB, "data", "run_pead7.log")
    if os.path.exists(log): sys.exit("already run")
    P = B.P; P("pead7_run.py  PREREGISTRATION_PEAD7 pinned\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    band, bench, bad, good = B.common()
    conf, _ = B.pead3_events(B.pead1_longs(), B.LOAD("sue_events.pkl"))
    R = [r for r in S.study(conf, band, bench, bad, good, execution="open") if r["band"] in ("M", "S")]
    P(f"  events: {len(conf)} SUE-confirmed -> {len(R)} M+S with an outcome")
    price(R, {"M": 0.64, "S": 1.06}); B.gates(R, B.ERAS, "PEAD7")
    P("\n  reported:")
    price(R, {"M": 0.56, "S": 0.89}); a = B.mt(R); P(f"    1 point ratios (M 0.56, S 0.89): net {a[0]*100:+.2f}% (t {a[1]:+.2f})")
    R120 = [r for r in S.study(conf, band, bench, bad, good, H=120, execution="open") if r["band"] in ("M", "S")]
    price(R120, {"M": 0.64, "S": 1.06}); a = B.mt(R120); b = B.mt([r for r in R120 if r["y"] >= 2018])
    P(f"    2 120-day hold, open-auction entry: net {a[0]*100:+.2f}% (t {a[1]:+.2f}, n {a[2]});  2018+ {b[0]*100:+.2f}% (t {b[1]:+.2f})")
    price(R, {"M": 0.64, "S": 1.06}); a = B.mt([r for r in R if r["band"] == "S" and r["y"] >= 2018])
    P(f"    3 S band 2018+: net {a[0]*100:+.2f}% (t {a[1]:+.2f}, n {a[2]})")
    open(log, "w").write("\n".join(B.OUT) + "\n")
if __name__ == "__main__":
    main()
