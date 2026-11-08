#!/usr/bin/env python3
"""PREREGISTRATION_v57 -- does S&P breadth predict the next month beyond VIX?
A measurement (fastbot Rule 1), one run.

    python3 breadth_vix_v57.py --self-test
    python3 breadth_vix_v57.py
"""
from __future__ import annotations

import argparse, hashlib, os, sys
import numpy as np
import breadth_v56 as B, tv_series as TV

VERSION = "1.0"
DOC = "../PREREGISTRATION_v57.md"
DOC_SHA = "2ed58dfb28e41955c0e4553fc5548fe9dca31f684c616c156b9b8c8a7b127bb8"
N_ROT, SEED = 2000, 57


def resid(a, Z):
    """Residual of a on [1, Z] (Z: 2-d array of controls)."""
    X = np.column_stack([np.ones(len(a)), Z])
    return a - X @ np.linalg.lstsq(X, a, rcond=None)[0]


def multi(y, cols, lag):
    """OLS y ~ 1 + cols with NW SEs; returns (beta, t) incl. constant at [0]."""
    y = np.asarray(y, float); X = np.column_stack([np.ones(len(y))] + [np.asarray(c, float) for c in cols])
    XtXi = np.linalg.inv(X.T @ X); b = XtXi @ X.T @ y; u = y - X @ b
    g = X * u[:, None]; S = g.T @ g
    for L in range(1, lag + 1):
        w = 1 - L / (lag + 1); G = g[L:].T @ g[:-L]; S += w * (G + G.T)
    V = XtXi @ S @ XtXi
    return b, b / np.sqrt(np.diag(V))


def rotation_p(ey, ex, t_obs, n_rot=N_ROT, seed=SEED, lag=20):
    rng = np.random.default_rng(seed); n = len(ey)
    tt = np.array([B.nw_ols(ey, np.roll(ex, int(o)), lag)[1][1] for o in rng.integers(252, n - 252, n_rot)])
    return float((tt <= t_obs).mean()), float(tt.std())


def panel(h, S, s5, vix):
    F = B.fwd(S, h); ds = sorted(S); pos = {d: i for i, d in enumerate(ds)}
    ts = [t for t in sorted(F) if t >= B.START and t in s5]
    dropped = sum(1 for t in ts if t not in vix)
    ts = [t for t in ts if t in vix]
    y = np.array([F[t][0] for t in ts]); x = np.array([s5[t] / 10 for t in ts])
    v = np.log(np.array([vix[t] for t in ts])); low = (x < 2).astype(float)
    m50 = np.array([(S[t][1] / S[ds[pos[t] - 50]][1] - 1) * 1e4 if pos[t] >= 50 else np.nan for t in ts])
    return ts, y, x, v, low, m50, dropped


def run():
    got = hashlib.sha256(open(DOC, "rb").read()).hexdigest()
    if got != DOC_SHA:
        sys.exit(f"{DOC} changed since frozen ({got[:12]}). Refused.")
    got = hashlib.sha256(open(os.path.join(B.TVD, "MANIFEST.json"), "rb").read()).hexdigest()
    if got != B.TVD_MANIFEST_SHA:
        sys.exit(f"{B.TVD}/MANIFEST.json changed since frozen ({got[:12]}). Refused.")
    print(f"breadth_vix_v57.py v{VERSION}\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    S = B.sessions(); s5 = dict(TV.read("S5FI", B.TVD)); vix = dict(TV.read("VIX", B.TVD))
    ts, y, x, v, low, m50, dropped = panel(20, S, s5, vix)
    print(f"  h=20  n {len(y):,} (dropped for missing VIX: {dropped}), low-breadth days {int(low.sum())}")
    b1, t1 = multi(y, [x, v], 20)
    print(f"  G1 model r20 ~ x + lnVIX : x {b1[1]:+.2f} bp per 10pp (NW t {t1[1]:+.2f}); lnVIX {b1[2]:+.1f} bp (NW t {t1[2]:+.2f})")
    Z = v[:, None]; ex, ey = resid(x, Z), resid(y, Z)
    bf, tf = B.nw_ols(ey, ex, 20)
    p, sd = rotation_p(ey, ex, tf[1])
    print(f"  G2 FWL partial t {tf[1]:+.2f} (slope {bf[1]:+.2f}, equals G1's x coefficient); rotation p {p:.3f}, null sd {sd:.2f}")
    b3, t3 = multi(y, [low, v], 20)
    print(f"  G3 model r20 ~ low + lnVIX: low {b3[1]:+.1f} bp (NW t {t3[1]:+.2f}); lnVIX {b3[2]:+.1f} bp (NW t {t3[2]:+.2f})")
    g1 = b1[1] < 0 and t1[1] <= -2.0
    g2 = p <= 0.05
    g3 = b3[1] > 0 and t3[1] >= 2.0
    print(f"\n  G1 breadth slope beyond VIX, t <= -2 : {'PASS' if g1 else 'FAIL'}")
    print(f"  G2 rotation null p <= 0.05          : {'PASS' if g2 else 'FAIL'}")
    print(f"  G3 low-breadth premium beyond VIX   : {'PASS' if g3 else 'FAIL'}")
    print(f"\n  VERDICT: {'BREADTH ADDS BEYOND VIX' if (g1 and g2 and g3) else 'NOT SHOWN BEYOND VIX'}\n")
    # reported
    print(f"  reported  corr(S5FI, lnVIX) {np.corrcoef(x, v)[0, 1]:+.3f}")
    bv, tv = multi(y, [v], 20)
    print(f"  reported  VIX only: r20 ~ lnVIX {bv[1]:+.1f} bp per unit ln (NW t {tv[1]:+.2f})")
    V = np.exp(v)
    q = lambda a: " / ".join(f"{z:.1f}" for z in np.percentile(a, [25, 50, 75]))
    print(f"  reported  VIX quartiles  low-breadth: {q(V[low == 1])}   rest: {q(V[low == 0])}")
    hi = V >= 25
    bh, th = B.nw_ols(y[hi], low[hi], 20)
    print(f"  reported  within VIX>=25 (n {hi.sum()}, low-breadth {int(low[hi].sum())}): low minus rest {bh[1]:+.1f} bp (NW t {th[1]:+.2f})"
          "  [NW on a non-contiguous subset: indicative only]")
    ok = np.isfinite(m50)
    bm, tm = multi(y[ok], [x[ok], v[ok], m50[ok]], 20)
    print(f"  reported  r20 ~ x + lnVIX + 50d return: x {bm[1]:+.2f} (t {tm[1]:+.2f}), lnVIX {bm[2]:+.1f} (t {tm[2]:+.2f}), m50 {bm[3]:+.4f} (t {tm[3]:+.2f})")
    ts5, y5, x5, v5, low5, _, _ = panel(5, S, s5, vix)
    a, ta = multi(y5, [x5, v5], 5); c, tc = multi(y5, [low5, v5], 5)
    print(f"  reported  h=5: x beyond VIX {a[1]:+.2f} (NW t {ta[1]:+.2f}); low beyond VIX {c[1]:+.1f} (NW t {tc[1]:+.2f})")


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"breadth_vix_v57.py v{VERSION} self-test\n")
    rng = np.random.default_rng(3); n = 5000
    v = rng.normal(size=n); x = -0.8 * v + 0.6 * rng.normal(size=n)
    y = 5 * v + rng.normal(size=n) * 3                                   # only VIX matters
    b, t = multi(y, [x, v], 5)
    check("PLANTED: y driven by VIX only -> breadth coefficient ~0 beyond VIX", abs(t[1]) < 3 and abs(b[2] - 5) < 0.3)
    y2 = 5 * v - 4 * x + rng.normal(size=n) * 3                          # breadth adds
    b2, t2 = multi(y2, [x, v], 5)
    check("PLANTED: breadth adds -> coefficient ~ -4, t << -2", abs(b2[1] + 4) < 0.3 and t2[1] < -10)
    ex, ey = resid(x, v[:, None]), resid(y2, v[:, None])
    bf, _ = B.nw_ols(ey, ex, 5)
    check("Frisch-Waugh partial slope equals the multiple-regression coefficient", abs(bf[1] - b2[1]) < 1e-8)
    bm, _ = multi(y2, [x], 0); bo, _ = B.nw_ols(y2, x, 0)
    check("multi() with one regressor equals breadth_v56.nw_ols", np.allclose(bm, bo))
    p, _ = rotation_p(rng.normal(size=1500), rng.normal(size=1500), -3.0, n_rot=200, lag=5)
    check("rotation p of a t of -3 on pure noise is small", p < 0.05)
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else run())
