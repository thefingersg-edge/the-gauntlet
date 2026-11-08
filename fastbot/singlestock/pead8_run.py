#!/usr/bin/env python3
"""PEAD8 harness (PREREGISTRATION_PEAD8). One run.  SS_STORE=~/store python3 pead8_run.py
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, hashlib, math, collections as C, numpy as np
import ss_events2 as S, pead_engine as E, batch2_run as B
from pead6_run import price
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DOC = (os.path.join(FB, "PREREGISTRATION_PEAD8.md"), "b458213e47ec3ca8474d26d1a84d89973f590b6243c98bf4dd3a79eaf185f2b9")
ERAS = ((2005, 2012), (2013, 2019), (2020, 2026)); RATIO = {"M": 0.64, "S": 1.06}

def exit_day(r, rule):
    """index j of the last held daily return (0-based) under the rule; None = held to the record's end."""
    rp = r["rpath"].astype(float); n = len(rp); px = np.cumprod(1 + rp); peak = 1.0
    for j in range(n - 1):
        peak = max(peak, px[j]); trig = False
        if rule == "V2": trig = px[j] <= peak * 0.85
        elif rule == "V3": trig = px[j] >= 1.25
        elif rule == "V4":
            g = 0.20 if peak < 1.10 else (0.12 if peak < 1.25 else 0.07); trig = px[j] <= peak * (1 - g)
        if trig: return j + 1                                  # sell in the NEXT day's closing auction
    return None

def truncate(r, j):
    """copy of record r held through daily return j (inclusive)."""
    q = dict(r); rp = r["rpath"][: j + 1].astype(float); pa = r["path"][: j + 1].astype(float); bb = rp - pa
    q["g"] = float(np.prod(1 + rp) - 1); q["x"] = float(q["g"] - (np.prod(1 + bb) - 1))
    q["rpath"], q["path"], q["dates"] = r["rpath"][: j + 1], r["path"][: j + 1], r["dates"][: j + 1]; q["exited"] = True
    return q

def per_day(R):
    by = C.defaultdict(lambda: [0.0, 0])
    for r in R: k = E.quarter(r["entry"]); by[k][0] += r["x"] - r["cost"]; by[k][1] += max(1, len(r["path"]))
    return {k: v[0] / v[1] for k, v in by.items()}

def main():
    if not DOC[1] or hashlib.sha256(open(DOC[0], "rb").read()).hexdigest() != DOC[1]: sys.exit("doc not pinned/changed")
    log = os.path.join(FB, "data", "run_pead8.log")
    if os.path.exists(log): sys.exit("already run")
    P = B.P; P("pead8_run.py  PREREGISTRATION_PEAD8 pinned\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    band, bench, bad, good = B.common(); conf, _ = B.pead3_events(B.pead1_longs(), B.LOAD("sue_events.pkl"))
    base = price([r for r in S.study(conf, band, bench, bad, good, execution="open") if r["band"] in "MS"], RATIO)
    long_ = price([r for r in S.study(conf, band, bench, bad, good, H=120, execution="open") if r["band"] in "MS"], RATIO)
    keyb = {(r["t"], r["sig"]) for r in base}; long_ = [r for r in long_ if (r["t"], r["sig"]) in keyb]
    keyl = {(r["t"], r["sig"]) for r in long_}; base = [r for r in base if (r["t"], r["sig"]) in keyl]
    pb = per_day(base); sb = B.calendar_sharpe(base)[0]
    P(f"  baseline PEAD7 60d: n {len(base)}  net/trade {np.mean([r['x']-r['cost'] for r in base])*100:+.2f}%  per position-day {100*np.mean(list(pb.values())):+.4f}%  Sharpe18+ {sb:.2f}\n")
    for v in ("V1", "V2", "V3", "V4"):
        R = []
        for r in long_:
            j = None if v == "V1" else exit_day(r, v)
            R.append(truncate(r, j) if j is not None else dict(r, exited=False))
        pv = per_day(R); ks = sorted(set(pv) & set(pb)); d = np.array([pv[k] - pb[k] for k in ks])
        t = d.mean() / (d.std(ddof=1) / math.sqrt(len(d))); g1 = d.mean() > 0 and t >= 2.5
        era = []
        for lo, hi in ERAS:
            Re = [r for r in R if lo <= r["y"] <= hi]; Be = [r for r in base if lo <= r["y"] <= hi]
            era.append(sum(r["x"] - r["cost"] for r in Re) / sum(max(1, len(r["path"])) for r in Re) - sum(r["x"] - r["cost"] for r in Be) / sum(max(1, len(r["path"])) for r in Be))
        g2 = all(e > 0 for e in era); sv = B.calendar_sharpe(R)[0]; g3 = sv >= sb
        yrs = C.defaultdict(list)
        for r in R: yrs[r["y"]].append(r["x"] - r["cost"])
        worst = min(yrs, key=lambda y: np.mean(yrs[y]))
        P(f"  {v}: per position-day diff {d.mean()*100:+.4f}% (t {t:+.2f}, {len(d)} quarters) -> G1 {'PASS' if g1 else 'FAIL'};  eras " + " ".join(f"{e*100:+.4f}%" for e in era) + f" -> G2 {'PASS' if g2 else 'FAIL'};  Sharpe18+ {sv:.2f} vs {sb:.2f} -> G3 {'PASS' if g3 else 'FAIL'}")
        P(f"      reported: net/trade {np.mean([r['x']-r['cost'] for r in R])*100:+.2f}%  avg days {np.mean([len(r['path']) for r in R]):.0f}  exited by rule {100*np.mean([r['exited'] for r in R]):.0f}%  worst year {worst} {np.mean(yrs[worst])*100:+.2f}%")
        P(f"      VERDICT {v}: {'PASS' if g1 and g2 and g3 else 'FAIL'}\n")
    open(log, "w").write("\n".join(B.OUT) + "\n")
if __name__ == "__main__":
    main()
