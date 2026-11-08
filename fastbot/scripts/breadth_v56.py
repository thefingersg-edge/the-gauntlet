#!/usr/bin/env python3
"""PREREGISTRATION_v56 -- does S&P breadth predict the S&P's next month?
A measurement (fastbot Rule 1), one run.

    python3 breadth_v56.py --self-test
    python3 breadth_v56.py
"""
from __future__ import annotations

import argparse, csv, datetime as dt, hashlib, math, os, sys
from zoneinfo import ZoneInfo
import numpy as np
import tv_series as TV

VERSION = "1.0"
DOC = "../PREREGISTRATION_v56.md"
DOC_SHA = "2fa66403d942a6b89c5d7cb068a5e45a7a17b2e55ae12ee0c8bcc25bf579213a"            # pinned in the freezing commit
#: the frozen snapshot of data/tv taken 2026-10-01 (data/tv itself is refreshed monthly)
TVD = "../data/tv_20261001"
TVD_MANIFEST_SHA = "b287eb00651b4cd9d43ffb4d567f681a1156dd20eecb674fa9890636d86bc9b3"
END = dt.date(2026, 9, 25)
START = dt.date(2007, 1, 2)
ERAS = ((2007, 2012), (2013, 2019), (2020, 2026))
NY, UTC = ZoneInfo("America/New_York"), dt.timezone.utc


def sessions(data_dir="../data/v24"):
    """{date: (open_mid_0930, close_mid_1545, spread_bp_0930)} from OANDA 15m bid/ask."""
    def rd(side):
        out = {}
        with open(os.path.join(data_dir, f"spx500usd_{side}_15m.csv")) as fh:
            r = csv.reader(fh); next(r)
            for row in r:
                t = dt.datetime.fromisoformat(row[0]).replace(tzinfo=UTC).astimezone(NY)
                if t.strftime("%H:%M") in ("09:30", "15:45"):
                    out[(t.date(), t.strftime("%H:%M"))] = (float(row[1]), float(row[4]))
        return out
    b, a = rd("bid"), rd("ask")
    S = {}
    for (d, hm) in b:
        if hm != "09:30" or (d, "15:45") not in b or (d, "09:30") not in a or (d, "15:45") not in a:
            continue
        o = (b[(d, "09:30")][0] + a[(d, "09:30")][0]) / 2
        c = (b[(d, "15:45")][1] + a[(d, "15:45")][1]) / 2
        sp = (a[(d, "09:30")][0] - b[(d, "09:30")][0]) / o * 1e4
        S[d] = (o, c, sp)
    return S


def fwd(S, h):
    """{t: (r_h bp, entry spread bp)}: open of t+1 -> close of t+h, mid."""
    ds = sorted(S); out = {}
    for i, t in enumerate(ds):
        if i + h >= len(ds) or ds[i + h] > END:
            continue
        o = S[ds[i + 1]][0]; c = S[ds[i + h]][1]
        out[t] = ((c / o - 1) * 1e4, S[ds[i + 1]][2])
    return out


def nw_ols(y, X, lag):
    """OLS with Newey-West (Bartlett) SEs. X without constant; returns (beta, t)."""
    y = np.asarray(y, float); X = np.column_stack([np.ones(len(y)), np.asarray(X, float)])
    XtXi = np.linalg.inv(X.T @ X); b = XtXi @ X.T @ y; u = y - X @ b
    g = X * u[:, None]; S = g.T @ g
    for L in range(1, lag + 1):
        w = 1 - L / (lag + 1); G = g[L:].T @ g[:-L]; S += w * (G + G.T)
    V = XtXi @ S @ XtXi
    return b, b / np.sqrt(np.diag(V))


def zweig(adv, dec):
    ds = sorted(d for d in set(adv) & set(dec) if adv[d] + dec[d] > 0)
    ema, em, out = None, [], []
    for d in ds:
        x = adv[d] / (adv[d] + dec[d]); ema = x if ema is None else ema + (2 / 11) * (x - ema); em.append((d, ema))
    for i in range(10, len(em)):
        if em[i][1] > 0.615 and em[i - 1][1] <= 0.615 and min(v for _, v in em[i - 10:i]) < 0.40:
            out.append(em[i][0])
    return out


def washouts(s5):
    out, armed = [], True
    for d, v in sorted(s5.items()):
        if armed and v < 10:
            out.append(d); armed = False
        elif v > 30:
            armed = True
    return out


def run():
    got = hashlib.sha256(open(DOC, "rb").read()).hexdigest()
    if got != DOC_SHA:
        sys.exit(f"{DOC} changed since frozen ({got[:12]}). Refused.")
    got = hashlib.sha256(open(os.path.join(TVD, "MANIFEST.json"), "rb").read()).hexdigest()
    if got != TVD_MANIFEST_SHA:
        sys.exit(f"{TVD}/MANIFEST.json changed since frozen ({got[:12]}). Refused.")
    print(f"breadth_v56.py v{VERSION}\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    S = sessions()
    s5 = dict(TV.read("S5FI", TVD)); s2 = dict(TV.read("S5TH", TVD)); add = TV.read("ADD", TVD)
    av = [x for _, x in add]
    addz = {add[i][0]: (av[i] - np.mean(av[i - 252:i])) / np.std(av[i - 252:i]) for i in range(252, len(add)) if np.std(av[i - 252:i]) > 0}
    res = {}
    for h in (20, 5):
        F = fwd(S, h)
        ts = [t for t in sorted(F) if t >= START and t in s5]
        y = np.array([F[t][0] for t in ts]); x = np.array([s5[t] / 10 for t in ts]); sp = np.array([F[t][1] for t in ts])
        b, t = nw_ols(y, x, h)
        low = np.array([s5[t_] < 20 for t_ in ts], float)
        bd, td_ = nw_ols(y, low, h)
        eras = []
        for lo, hi in ERAS:
            m = np.array([lo <= q.year <= hi for q in ts])
            be, te = nw_ols(y[m], x[m], h); eras.append((be[1], te[1], m.sum()))
        res[h] = dict(n=len(ts), b=b[1], t=t[1], bd=bd[1], td=td_[1], low_mean=y[low == 1].mean(), all_mean=y.mean(),
                      n_low=int(low.sum()), spread=float(np.median(sp)), eras=eras, ts=ts, y=y)
        print(f"  h={h:<2} n {len(ts):,}  slope per 10pp S5FI {b[1]:+.2f} bp (NW t {t[1]:+.2f})   "
              f"low-breadth (S5FI<20, n {int(low.sum())}) minus rest {bd[1]:+.1f} bp (NW t {td_[1]:+.2f});"
              f" low mean {y[low == 1].mean():+.1f} bp, all {y.mean():+.1f} bp, median entry spread {np.median(sp):.2f} bp")
        print("        eras: " + "   ".join(f"{lo}-{hi}: {be:+.2f} (t {te:+.2f}, n {n})" for (lo, hi), (be, te, n) in zip(ERAS, eras)))
    r = res[20]
    g1 = r["b"] < 0 and r["t"] <= -2.0
    g2 = all(be < 0 for be, _, _ in r["eras"])
    g3 = r["bd"] > 0 and r["td"] >= 2.0 and (r["low_mean"] - r["spread"]) > 0
    print(f"\n  G1 slope < 0, t <= -2      : {'PASS' if g1 else 'FAIL'}")
    print(f"  G2 slope < 0 in every era  : {'PASS' if g2 else 'FAIL'}")
    print(f"  G3 low-breadth premium     : {'PASS' if g3 else 'FAIL'}")
    print(f"\n  VERDICT: {'PASS' if (g1 and g2 and g3) else 'FAIL'}\n")
    # reported
    F20 = fwd(S, 20)
    ts = [t for t in sorted(F20) if t >= START and t in s2]
    b, t = nw_ols([F20[q][0] for q in ts], [s2[q] / 10 for q in ts], 20)
    print(f"  reported  S5TH slope per 10pp {b[1]:+.2f} bp (NW t {t[1]:+.2f}), n {len(ts):,}")
    ts = [t for t in sorted(F20) if t >= START and t in addz]
    b, t = nw_ols([F20[q][0] for q in ts], [addz[q] for q in ts], 20)
    print(f"  reported  ADD z slope {b[1]:+.2f} bp per z (NW t {t[1]:+.2f}), n {len(ts):,}")
    F60 = fwd(S, 60)
    zt = [d for d in zweig(dict(TV.read("ADV", TVD)), dict(TV.read("DECL", TVD))) if START <= d]
    print(f"  reported  Zweig thrusts ({len(zt)}): " + "; ".join(
        f"{d} r20 {F20[d][0]:+.0f}" + (f" r60 {F60[d][0]:+.0f}" if d in F60 else "") if d in F20 else f"{d} (no r20 yet)" for d in zt))
    wo = [d for d in washouts(s5) if d >= START]
    print(f"  reported  first washouts S5FI<10 ({len(wo)}): " + "; ".join(
        f"{d} r20 {F20[d][0]:+.0f}" if d in F20 else f"{d} (no r20 yet)" for d in wo))
    print(f"  reported  unconditional r20 mean {np.mean([F20[q][0] for q in F20 if q >= START]):+.1f} bp")


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"breadth_v56.py v{VERSION} self-test\n")
    rng = np.random.default_rng(1)
    x = rng.normal(size=4000); y = -3 * x + rng.normal(size=4000) * 10
    b, t = nw_ols(y, x, 5)
    check("NW OLS recovers a planted slope of -3", abs(b[1] + 3) < 0.5 and t[1] < -10)
    e = rng.normal(size=4000); y2 = np.convolve(e, np.ones(20), "same")
    _, t0 = nw_ols(y2, rng.normal(size=4000), 0); _, t20 = nw_ols(y2, np.convolve(rng.normal(size=4000), np.ones(20), "same"), 20)
    check("NW t on overlapping noise stays modest (|t| < 3.5)", abs(t20[1]) < 3.5)
    S = {dt.date(2020, 1, 1) + dt.timedelta(days=i): (100.0 + i, 100.5 + i, 1.0) for i in range(30)}
    F = fwd(S, 5)
    t0_ = min(S)
    check("forward return starts at the NEXT session's open (never the signal day)",
          abs(F[t0_][0] - ((S[t0_ + dt.timedelta(days=5)][1] / S[t0_ + dt.timedelta(days=1)][0] - 1) * 1e4)) < 1e-9)
    check("washouts re-arm only above 30", washouts({dt.date(2020, 1, i): v for i, v in enumerate([50, 9, 8, 25, 9, 31, 9], 1)}) == [dt.date(2020, 1, 2), dt.date(2020, 1, 7)])
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else run())
