#!/usr/bin/env python3
"""IMB1 analysis (PREREGISTRATION_IMB1). One run, from data/imb1/days.csv + symbols.csv (Databento pull, 2026-10-04..06).
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, hashlib, math, collections as C, numpy as np
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); D = os.path.join(FB, "data", "imb1")
DOC = (os.path.join(FB, "PREREGISTRATION_IMB1.md"), None)
def ols_hc(y, x):
    X = np.column_stack([np.ones(len(x)), x]); XtXi = np.linalg.inv(X.T @ X); b = XtXi @ X.T @ y; u = y - X @ b
    V = XtXi @ (X.T * u**2) @ X @ XtXi; return b[1], b[1] / math.sqrt(V[1, 1])
def zser(dates, S):
    z = {}
    for i in range(250, len(dates)):
        w = np.array(S[i - 250:i]); sd = w.std(ddof=1)
        if sd > 0: z[dates[i]] = (S[i] - w.mean()) / sd
    return z
def tmean(a): a = np.asarray(a, float); return a.mean(), a.mean() / (a.std(ddof=1) / math.sqrt(len(a))), len(a)
def main():
    log = os.path.join(D, "..", "run_imb1.log")
    if os.path.exists(log): sys.exit("already run")
    OUT = []; P = lambda s="": (print(s, flush=True), OUT.append(s))
    P("imb1_run.py  PREREGISTRATION_IMB1 sha " + hashlib.sha256(open(DOC[0], "rb").read()).hexdigest()[:12] + "\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    R = [r for r in csv.DictReader(open(os.path.join(D, "days.csv"))) if r["status"] == "ok" and float(r["paired_usd"] or 0) > 0]
    R.sort(key=lambda r: r["date"]); dates = [r["date"] for r in R]
    S = [(float(r["buy_usd"]) - float(r["sell_usd"])) / float(r["paired_usd"]) for r in R]
    ret = {r["date"]: (float(r["spy_mid_1600"]) / float(r["spy_mid_1551"]) - 1) * 1e4 for r in R}
    nmem = {r["date"]: int(r["n_nas"] or 0) + int(r["n_nys"] or 0) for r in R}
    z = zser(dates, S); ds = sorted(z); y = np.array([ret[d] for d in ds]); x = np.array([z[d] for d in ds])
    b, t = ols_hc(y, x); g1 = b > 0 and t >= 2.0
    P(f"  days {len(R)} ok; with z (after 250-day warm-up) {len(ds)}: {ds[0]} .. {ds[-1]}; 9-min SPY return SD {y.std():.1f} bp")
    P(f"  G1 slope {b:+.3f} bp per z (HC t {t:+.2f})  -> {'PASS' if g1 else 'FAIL'}")
    sel = [d for d in ds if abs(z[d]) >= 1]; pnl = {d: math.copysign(1, z[d]) * ret[d] - 1.0 for d in sel}
    m, t2, n = tmean(list(pnl.values())); g2 = m > 0 and t2 >= 2.0
    P(f"  G2 |z|>=1 trades: {n}; mean net {m:+.2f} bp (gross {m+1:+.2f}) t {t2:+.2f}  -> {'PASS' if g2 else 'FAIL'}")
    per = [((2019, 2020), "2019-20"), ((2021, 2023), "2021-23"), ((2024, 2026), "2024-26")]; ev = []
    for (a, c), lab in per:
        v = [pnl[d] for d in sel if a <= int(d[:4]) <= c]; ev.append((lab, np.mean(v) if v else float('nan'), len(v)))
    g3 = all(e[1] > 0 for e in ev)
    P("  G3 " + "  ".join(f"{l} {m_:+.2f} bp (n {k})" for l, m_, k in ev) + f"  -> {'PASS' if g3 else 'FAIL'}")
    P("\n  reported:")
    sel2 = [d for d in ds if abs(z[d]) >= 2]
    if sel2: mm = tmean([math.copysign(1, z[d]) * ret[d] - 1.0 for d in sel2]); P(f"    |z|>=2: n {mm[2]}, mean net {mm[0]:+.2f} bp (t {mm[1]:+.2f})")
    V = C.defaultdict(lambda: [0.0, 0.0])
    for r in csv.DictReader(open(os.path.join(D, "symbols.csv"))):
        k = (r["date"], r["venue"]); v = float(r["imb_qty"]) * float(r["ref_price"]); sg = 1 if r["side"] == "B" else (-1 if r["side"] == "A" else 0)
        V[k][0] += sg * v; V[k][1] += float(r["paired_qty"]) * float(r["ref_price"])
    for ven in ("XNAS", "XNYS"):
        dd = [d for d in dates if V[(d, ven)][1] > 0]; zz = zser(dd, [V[(d, ven)][0] / V[(d, ven)][1] for d in dd]); k_ = sorted(zz)
        bb, tt = ols_hc(np.array([ret[d] for d in k_]), np.array([zz[d] for d in k_])); P(f"    {ven}-only signal: slope {bb:+.3f} (t {tt:+.2f}, n {len(k_)})")
    few = [d for d in ds if nmem[d] < 400]; P(f"    days with < 400 members reporting: {len(few)}")
    P("    15:51 -> 15:55 split: not available (only the 15:51 and 15:59:59 SPY midpoints were pulled)")
    for (a, c), lab in per:
        k_ = [d for d in ds if a <= int(d[:4]) <= c]; bb, tt = ols_hc(np.array([ret[d] for d in k_]), np.array([z[d] for d in k_])); P(f"    slope {lab}: {bb:+.3f} (t {tt:+.2f})")
    P(f"\n  VERDICT IMB1 G1 {'P' if g1 else 'F'} G2 {'P' if g2 else 'F'} G3 {'P' if g3 else 'F'} -> {'PASS' if g1 and g2 and g3 else 'FAIL'}")
    open(log, "w").write("\n".join(OUT) + "\n")
if __name__ == "__main__": main()
