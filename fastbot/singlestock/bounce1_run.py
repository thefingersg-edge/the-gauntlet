#!/usr/bin/env python3
"""BOUNCE1 (+ BOUNCE1.1) and Part B (descriptive). One run.  python3 bounce1_run.py
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, math, datetime as dt, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from imb1_run import zser, ols_hc, tmean
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); D = os.path.join(FB, "data", "imb1")
CK = ["155015", "155030", "155100", "155200", "155500", "155800", "155959", "160001", "160500", "161500", "163000", "165000"]
def main():
    log = os.path.join(FB, "data", "run_bounce1.log")
    if os.path.exists(log): sys.exit("already run")
    OUT = []; P = lambda s="": (print(s, flush=True), OUT.append(s))
    P("bounce1_run.py  PREREGISTRATION_BOUNCE1 + BOUNCE1.1\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    R = [r for r in csv.DictReader(open(os.path.join(D, "days.csv"))) if r["status"] == "ok" and float(r["paired_usd"] or 0) > 0]
    R.sort(key=lambda r: r["date"]); dates = [r["date"] for r in R]
    S = [(float(r["buy_usd"]) - float(r["sell_usd"])) / float(r["paired_usd"]) for r in R]; z = zser(dates, S)
    M = {r["date"]: r for r in csv.DictReader(open(os.path.join(D, "spy_path.csv")))}
    pol = {r["month"]: float(r["rate_pct"]) / 100 for r in csv.DictReader(open(os.path.join(FB, "data", "policy_rates.csv"))) if r["currency"] == "USD"}
    sd = sorted(M); nxt = {sd[i]: sd[i + 1] for i in range(len(sd) - 1)}
    b, fin_side = {}, {}
    for d in z:
        if d not in M or d not in nxt: continue
        n = M[nxt[d]]; c = M[d]
        if not n["m093030"] or not c["m160001"]: continue
        b[d] = (float(n["m093030"]) / float(c["m160001"]) - 1) * 1e4
    ds = sorted(b); y = np.array([b[d] for d in ds]); x = np.array([z[d] for d in ds])
    sl, t = ols_hc(y, x); g1 = sl < 0 and t <= -2.0
    P(f"  days {len(ds)} ({ds[0]} .. {ds[-1]}); overnight SPY return SD {y.std():.1f} bp")
    P(f"  G1 slope of overnight return on z: {sl:+.3f} bp per z (HC t {t:+.2f})  -> {'PASS' if g1 else 'FAIL'}")
    def fin(d, side):
        wd = dt.date.fromisoformat(d).weekday(); days = 3 if wd == 4 else 1; r = pol.get(d[:7], 0.02)
        return days / 365 * ((r + 0.025) if side > 0 else -(r - 0.025)) * 1e4
    sel = [d for d in ds if abs(z[d]) >= 1]
    pn = {d: -math.copysign(1, z[d]) * b[d] - 1.0 - fin(d, -math.copysign(1, z[d])) for d in sel}
    pf = {d: -math.copysign(1, z[d]) * b[d] - 3.0 for d in sel}
    m, t2, n = tmean(list(pn.values())); g2 = m > 0 and t2 >= 2.0
    P(f"  G2 |z|>=1: {n} trades; mean net {m:+.2f} bp (gross {np.mean([-math.copysign(1, z[d]) * b[d] for d in sel]):+.2f}; mean financing {np.mean([fin(d, -math.copysign(1, z[d])) for d in sel]):+.2f}) t {t2:+.2f}  -> {'PASS' if g2 else 'FAIL'}")
    ev = []
    for (a, c_), lab in (((2019, 2020), "2019-20"), ((2021, 2023), "2021-23"), ((2024, 2026), "2024-26")):
        v = [pn[d] for d in sel if a <= int(d[:4]) <= c_]; ev.append((lab, np.mean(v), len(v)))
    g3 = all(e[1] > 0 for e in ev)
    P("  G3 " + "  ".join(f"{l} {v:+.2f} bp (n {k})" for l, v, k in ev) + f"  -> {'PASS' if g3 else 'FAIL'}")
    mf = tmean(list(pf.values())); P(f"  reported: original flat 3.0 bp cost version: mean net {mf[0]:+.2f} bp (t {mf[1]:+.2f})")
    P(f"\n  VERDICT BOUNCE1 G1 {'P' if g1 else 'F'} G2 {'P' if g2 else 'F'} G3 {'P' if g3 else 'F'} -> {'PASS' if g1 and g2 and g3 else 'FAIL'}")
    P("\n  PART B (DESCRIPTIVE): SPY return from the 15:50:00 midpoint to each checkpoint, regressed on z (bp per z)")
    for ck in CK:
        k_ = [d for d in z if d in M and M[d]["m155000"] and M[d]["m" + ck]]
        yy = np.array([(float(M[d]["m" + ck]) / float(M[d]["m155000"]) - 1) * 1e4 for d in k_]); xx = np.array([z[d] for d in k_])
        s_, t_ = ols_hc(yy, xx); lab = f"{ck[:2]}:{ck[2:4]}:{ck[4:]}"
        P(f"    to {lab}: slope {s_:+.3f} bp per z (HC t {t_:+.2f}), return SD {yy.std():.1f} bp, n {len(k_)}" + ("   [after-hours, thin]" if ck > "160001" else ""))
    open(log, "w").write("\n".join(OUT) + "\n")
if __name__ == "__main__": main()
