#!/usr/bin/env python3
"""COSTS2 verdict (PREREGISTRATION_COSTS2). Read-only.  SS_STORE=~/store python3 costs2_verdict.py
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, csv, bisect, numpy as np
import ss_lib, ss_events2 as S
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); D = os.path.join(FB, "data", "costs1")
m1 = {(r["band"], r["order"]): r for r in csv.DictReader(open(os.path.join(D, "measures.csv"))) if r["status"] == "ok"}
rng = np.random.default_rng(20261004)
def ci(x):
    x = np.asarray(x, float); b = [np.median(rng.choice(x, len(x))) for _ in range(2000)]
    return np.median(x), np.quantile(b, .05), np.quantile(b, .95)
def show(lab, x, pct=True):
    m, lo, hi = ci(x); f = (lambda v: f"{100*v:+.3f}%") if pct else (lambda v: f"{v:.2f}")
    print(f"  {lab:<44} median {f(m)}  90% CI [{f(lo)}, {f(hi)}]  n {len(x)}"); return m
rows = []
for r in csv.DictReader(open(os.path.join(D, "measures2.csv"))):
    a = m1[(r["band"], r["order"])]; f = r["ticker"].replace("/", "_") + ".npz"
    z = ss_lib.load(S.STORE, f); d = z["d"]; k = bisect.bisect_left(d, ss_lib.d2i(r["entry_date"]))
    if k >= len(d) or d[k] != ss_lib.d2i(r["entry_date"]): continue
    u = z["cu"][k] / z["c"][k]; osh, csh = z["o"][k] * u, z["cu"][k]
    op, cl, mid = float(r["official_open"]), float(r["official_close"]), float(r["first_mid"])
    if not all(np.isfinite([op, cl, mid])): continue   # 2 rows: Databento opening-price stat present but undefined (nan)
    rows.append(dict(band=r["band"], fid=abs(osh - op) / op, fid_s=(osh - op) / op, oc=abs(op - mid) / mid, oc_s=(op - mid) / mid,
                     d1_off=cl / op - 1, d1_sh=csh / osh - 1, rt=abs(op - mid) / mid + float(a["exit_auction"]), edge=float(a["edge"])))
print(f"COSTS2 verdict -- {len(rows)} rows matched to the Sharadar store\nI am not a financial adviser. This is a measurement, not a recommendation.\n")
for lab, R in (("ALL", rows), ("M", [r for r in rows if r["band"] == "M"]), ("S", [r for r in rows if r["band"] == "S"])):
    print(lab)
    fa = show("1 |Sharadar open - official open|", [r["fid"] for r in R])
    show("  signed (Sharadar - official)", [r["fid_s"] for r in R])
    show("2 opening auction vs first mid (one way)", [r["oc"] for r in R])
    show("  signed (official open - mid)", [r["oc_s"] for r in R])
    print(f"  {'3 day one mean: official open->close':<44} {100*np.mean([r['d1_off'] for r in R]):+.3f}%   Sharadar {100*np.mean([r['d1_sh'] for r in R]):+.3f}%")
    show("  round trip open auction + exit auction", [r["rt"] for r in R])
    rb = show("  round trip / EDGE", [r["rt"] / r["edge"] for r in R if r["edge"] > 0], False)
    if lab == "ALL": A, B = fa <= 0.001, rb <= 0.5
print(f"\nRULE A (median |Sharadar - official open| <= 0.10%): {'PASS -- Sharadar open is the auction price' if A else 'FAIL -- open-entry backtests used an untradeable price'}")
print(f"RULE B (round trip / EDGE <= 0.50): {'PASS -- opening-auction entry accepted' if B else 'FAIL'}")
