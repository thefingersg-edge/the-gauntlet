#!/usr/bin/env python3
"""PRE1 harness (PREREGISTRATION_PRE1). One run. I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, math, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from imb1_run import zser, ols_hc, tmean
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); D = os.path.join(FB, "data", "imb1")
def main():
    log = os.path.join(FB, "data", "run_pre1.log")
    if os.path.exists(log): sys.exit("already run")
    OUT = []; P = lambda s="": (print(s, flush=True), OUT.append(s))
    P("pre1_run.py  PREREGISTRATION_PRE1\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    R = [r for r in csv.DictReader(open(os.path.join(D, "days.csv"))) if r["status"] == "ok" and float(r["paired_usd"] or 0) > 0]
    R.sort(key=lambda r: r["date"]); dates = [r["date"] for r in R]
    S = {r["date"]: (float(r["buy_usd"]) - float(r["sell_usd"])) / float(r["paired_usd"]) for r in R}; z = zser(dates, [S[d] for d in dates])
    M = {r["date"]: r for r in csv.DictReader(open(os.path.join(D, "spy_path.csv")))}
    ds = [d for d in sorted(z) if d in M and M[d]["m093030"] and M[d]["m155000"] and M[d]["m160001"]]
    f = lambda d, k: float(M[d][k])
    Dm = np.array([(f(d, "m155000") / f(d, "m093030") - 1) * 100 for d in ds]); Ss = np.array([S[d] for d in ds])
    Rt = {k: np.array([(f(d, k) / f(d, "m155000") - 1) * 1e4 for d in ds]) for k in ("m160001", "m155015", "m155100")}
    b1, t1 = ols_hc(Ss, Dm); g1 = b1 > 0 and t1 >= 2.0
    P(f"  days {len(ds)}; day move to 15:50 SD {Dm.std():.2f}%; corr(day move, imbalance) {np.corrcoef(Dm, Ss)[0,1]:+.3f}")
    P(f"  G1 imbalance on day move: slope {b1:+.5f} per 1% (HC t {t1:+.2f})  -> {'PASS' if g1 else 'FAIL'}")
    b2, t2 = ols_hc(Rt["m160001"], Dm); g2 = b2 > 0 and t2 >= 2.0
    P(f"  G2 15:50:00 -> 16:00:01 return on day move: {b2:+.3f} bp per 1% (HC t {t2:+.2f})  -> {'PASS' if g2 else 'FAIL'}")
    sel = np.abs(Dm) >= 1.0; pn = np.sign(Dm[sel]) * Rt["m160001"][sel] - 1.0; m, t3, n = tmean(pn); g3 = m > 0 and t3 >= 2.0
    P(f"  G3 |day move| >= 1%: {n} days; mean net {m:+.2f} bp (gross {m+1:+.2f}) t {t3:+.2f}  -> {'PASS' if g3 else 'FAIL'}")
    yrs = np.array([int(d[:4]) for d in ds])[sel]; ev = []
    for a, c, lab in ((2019, 2020, "2019-20"), (2021, 2023, "2021-23"), (2024, 2026, "2024-26")):
        v = pn[(yrs >= a) & (yrs <= c)]; ev.append((lab, v.mean() if len(v) else float("nan"), len(v)))
    g4 = all(e[1] > 0 for e in ev); P("  G4 " + "  ".join(f"{l} {v:+.2f} (n {k})" for l, v, k in ev) + f"  -> {'PASS' if g4 else 'FAIL'}")
    P("\n  reported:")
    for k, lab in (("m155015", "15:50:15"), ("m155100", "15:51:00")):
        b, t = ols_hc(Rt[k], Dm); g = np.sign(Dm[sel]) * Rt[k][sel]; P(f"    to {lab}: slope {b:+.3f} bp per 1% (t {t:+.2f}); |D|>=1% gross {g.mean():+.2f} bp")
    s2 = np.abs(Dm) >= 2.0; v = np.sign(Dm[s2]) * Rt["m160001"][s2] - 1.0
    if s2.sum() > 1: mm = tmean(v); P(f"    |day move| >= 2%: {mm[2]} days, mean net {mm[0]:+.2f} bp (t {mm[1]:+.2f})")
    P(f"\n  VERDICT PRE1 G1 {'P' if g1 else 'F'} (mechanism)  G2 {'P' if g2 else 'F'} G3 {'P' if g3 else 'F'} G4 {'P' if g4 else 'F'} -> {'PASS' if g2 and g3 and g4 else 'FAIL'}")
    open(log, "w").write("\n".join(OUT) + "\n")
if __name__ == "__main__": main()
