#!/usr/bin/env python3
"""Power budget for v50 -- written BEFORE any fear/attention index is fetched.
Uses only realised variance (squared 5m returns) and VIX: no predictor data."""
import csv, datetime as dt, math
import numpy as np
from reactive import load

def rv_series(ins):
    days = load("../data", ins); out = {}
    for d in sorted(days):
        ks = sorted(days[d]); c = np.array([days[d][k][3] for k in ks])
        out[d] = float(np.sum(np.diff(np.log(c)) ** 2))
    return out

vix = {dt.date.fromisoformat(r["date"]): float(r["vix"]) for r in csv.DictReader(open("../data/VIXCLS.csv")) if r["vix"] not in ("", ".")}
for ins in ("spx500usd", "nas100usd"):
    RV = rv_series(ins); ds = [d for d in sorted(RV) if d >= dt.date(2005, 1, 1)]
    lr = np.log(np.array([RV[d] for d in ds]))
    rows = []
    for i in range(22, len(ds) - 1):
        pv = [d for d in (ds[i - 1],) if d in vix]
        if not pv: continue
        rows.append((lr[i], lr[i - 1], lr[i - 5:i].mean(), lr[i - 22:i].mean(), math.log(vix[pv[0]]), ds[i].year))
    A = np.array([r[:5] for r in rows]); y = A[:, 0]; X = np.column_stack([np.ones(len(y)), A[:, 1:]])
    b = np.linalg.lstsq(X, y, rcond=None)[0]; e = y - X @ b
    r2 = 1 - e.var() / y.var(); rho = np.corrcoef(e[1:], e[:-1])[0, 1]
    n = len(e); neff = n * (1 - rho) / (1 + rho)
    # MDE for the slope on a standardised extra predictor (80% power, two-sided 5% -> 2.8 SE; t 2.24 gate -> 3.08 SE)
    mde = 3.08 * e.std() / math.sqrt(neff)
    print(f"{ins}: days {n} ({ds[22]}..{ds[-2]})  HAR+VIX R2 {r2:.3f}  resid sd {e.std():.3f} log-units  resid AR1 {rho:.2f}  n_eff {neff:.0f}")
    print(f"   MDE slope per 1 sd of predictor (t 2.24 gate, 80% power): {mde:.3f} log-units = {100*(math.exp(mde)-1):.1f}% change in next-day RV")
    print(f"   equivalent incremental R2 ~ {mde**2 / y.var():.4f}")
    for lo, hi in ((2005, 2012), (2013, 2019), (2020, 2026)):
        m = np.array([lo <= r[5] <= hi for r in rows]); ne = m.sum() * (1 - rho) / (1 + rho)
        print(f"   era {lo}-{hi}: n {m.sum()}  per-era MDE {3.08 * e[m].std() / math.sqrt(ne):.3f}")
    m = np.array([r[5] >= 2015 for r in rows]); ne = m.sum() * (1 - rho) / (1 + rho)
    print(f"   2015-2026 (GDELT window): n {m.sum()}  MDE {3.08 * e[m].std() / math.sqrt(ne):.3f}")
