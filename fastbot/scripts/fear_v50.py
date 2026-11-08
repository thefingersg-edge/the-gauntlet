#!/usr/bin/env python3
"""PREREGISTRATION_v50 + v50.1 -- news-based fear composite vs next-day realised volatility.
Primary C = mean(z_EPU, z_GPR) from data/v50/fear_table.csv (pinned), used at date <= target-2.
G1 in-sample HAR+VIX+C (NW-HAC 5 lags, t>=2.39, b>0 in each era);
G2 expanding-window OOS from 2009-01, monthly refit, DM on squared log-RV error (t>=2.39, better in each era);
G3 short-VX1 carry overlay: flat when C in top fifth of its prior 250 values, vs always-short and a
   VIX-top-fifth control; P&L / worst drawdown (gross, as vix_daily_risk.daily_pnl).
I am not a financial adviser. This is a measurement, not a recommendation."""
import csv, datetime as dt, hashlib, math, os, sys, bisect
import numpy as np
from reactive import load

VERSION = "1.0"
PINS = {"../PREREGISTRATION_v50.md": "8560ed09ba26aad15dc3e637340203c8fc70d7fd57d57bfc10bdabfebcfda269",
        "../PREREGISTRATION_v50.1.md": "6beae2ec94ca32c5f452761eef64a2b69499d1c13d0551f7d96922f5311b6364",
        "../data/v50/fear_table.csv": "e58d9de5ea1f6e8ac9cb99fa6f7babca339b23d246d8804717c2922e40db594e",
        "../data/v50/trends_monthly.csv": "350c5f84fc7030a2d78c67b5266292d38177cafa63d16118584fc6460b520a95"}
T = 2.39; LAGS = 5
ERAS = ((2005, 2012), (2013, 2019), (2020, 2026)); OOS_ERAS = ((2009, 2012), (2013, 2019), (2020, 2026))


def nw(X, y, lags=LAGS):
    X = np.asarray(X, float); y = np.asarray(y, float)
    XtXi = np.linalg.inv(X.T @ X); b = XtXi @ X.T @ y; u = y - X @ b
    Xu = X * u[:, None]; S = Xu.T @ Xu
    for l in range(1, lags + 1):
        w = 1 - l / (lags + 1); G = Xu[l:].T @ Xu[:-l]; S += w * (G + G.T)
    V = XtXi @ S @ XtXi
    return b, np.sqrt(np.diag(V))


def nw_mean_t(d, lags=LAGS):
    b, se = nw(np.ones((len(d), 1)), d, lags); return b[0], b[0] / se[0]


def rv_days(ins):
    days = load("../data", ins); out = {}
    for d in sorted(days):
        ks = sorted(days[d]); c = np.array([days[d][k][3] for k in ks])
        out[d] = (float(np.sum(np.diff(np.log(c)) ** 2)), (days[d][ks[-1]][3] / days[d][ks[0]][0] - 1) * 1e4)
    return out


def main():
    for f, h in PINS.items():
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} changed -- refused")
    print(f"fear_v50.py v{VERSION}   PREREGISTRATION_v50 (8560ed09…) + v50.1 (6beae2ec…), fear table (e58d9de5…) all match\n"
          "  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    F = {}
    for r in csv.DictReader(open("../data/v50/fear_table.csv")):
        F[dt.date.fromisoformat(r["date"])] = {k: (float(r[k]) if r[k] else None) for k in ("z_EPU", "z_GPR", "z_TPU", "C", "C3")}
    fd = sorted(F)
    def fear(target, key, lag=2):
        i = bisect.bisect_right(fd, target - dt.timedelta(days=lag)) - 1
        if i < 0 or (target - fd[i]).days > lag + 5: return None
        return F[fd[i]][key]
    vix = {dt.date.fromisoformat(r["date"]): float(r["vix"]) for r in csv.DictReader(open("../data/VIXCLS.csv")) if r["vix"] not in ("", ".")}
    vd = sorted(vix)
    def vix_prev(t):
        i = bisect.bisect_left(vd, t) - 1
        return vix[vd[i]] if i >= 0 and (t - vd[i]).days <= 5 else None

    def rows_for(ins):
        RV = rv_days(ins); ds = [d for d in sorted(RV) if d >= dt.date(2005, 1, 1)]
        lr = np.log(np.array([RV[d][0] for d in ds])); out = []
        for i in range(22, len(ds)):
            t = ds[i]; v = vix_prev(t)
            if v is None: continue
            r = dict(d=t, y=lr[i], h1=lr[i - 1], h5=lr[i - 5:i].mean(), h22=lr[i - 22:i].mean(), lv=math.log(v),
                     ret=RV[t][1], y5=lr[i:i + 5].mean() if i + 5 <= len(ds) else None)
            for k in ("C", "C3", "z_EPU", "z_GPR", "z_TPU"):
                r[k] = fear(t, k); r[k + "_1"] = fear(t, k, lag=1)
            out.append(r)
        return out

    def fit(rs, key="C", target="y"):
        rs = [r for r in rs if r[key] is not None and r[target] is not None]
        X = np.column_stack([np.ones(len(rs)), [r["h1"] for r in rs], [r["h5"] for r in rs], [r["h22"] for r in rs],
                             [r["lv"] for r in rs], [r[key] for r in rs]])
        b, se = nw(X, [r[target] for r in rs]); return b[5], b[5] / se[5], len(rs), np.std([r[key] for r in rs])

    def g1(rs, key="C"):
        b, t, n, sdC = fit(rs, key); eras = [fit([r for r in rs if lo <= r["d"].year <= hi], key) for lo, hi in ERAS]
        return dict(b=b, t=t, n=n, sd=sdC, eras=eras, ok=b > 0 and t >= T and all(e[0] > 0 for e in eras))

    def g2(rs, key="C"):
        rs = [r for r in rs if r[key] is not None]
        feats = lambda r, c: [1, r["h1"], r["h5"], r["h22"], r["lv"]] + ([r[key]] if c else [])
        d, ds = [], []
        y0 = 2009; months = sorted({(r["d"].year, r["d"].month) for r in rs if r["d"].year >= y0})
        for (y, m) in months:
            ms = dt.date(y, m, 1); tr = [r for r in rs if r["d"] < ms]; te = [r for r in rs if r["d"].year == y and r["d"].month == m]
            if not te: continue
            Y = np.array([r["y"] for r in tr])
            b0 = np.linalg.lstsq(np.array([feats(r, 0) for r in tr]), Y, rcond=None)[0]
            b1 = np.linalg.lstsq(np.array([feats(r, 1) for r in tr]), Y, rcond=None)[0]
            for r in te:
                e0 = r["y"] - np.dot(b0, feats(r, 0)); e1 = r["y"] - np.dot(b1, feats(r, 1))
                d.append(e0 ** 2 - e1 ** 2); ds.append(r["d"])
        d = np.array(d); m, t = nw_mean_t(d)
        er = [d[[lo <= x.year <= hi for x in ds]].mean() for lo, hi in OOS_ERAS]
        base = np.mean([x for x in d])  # loss difference
        return dict(m=m, t=t, n=len(d), eras=er, ok=m > 0 and t >= T and all(e > 0 for e in er))

    SPX = rows_for("spx500usd"); NAS = rows_for("nas100usd")
    s = [r for r in SPX if r["C"] is not None]
    print(f"  SPX500 rows {len(SPX)} ({SPX[0]['d']}..{SPX[-1]['d']}); with C {len(s)}   sd(C) {np.std([r['C'] for r in s]):.3f}")

    # self-test on G1
    import copy
    sdC = np.std([r["C"] for r in s])
    P = copy.deepcopy(SPX); M = copy.deepcopy(SPX)
    for r in P:
        if r["C"] is not None: r["y"] += 0.10 * r["C"] / sdC
    for r in M:
        if r["C"] is not None: r["y"] -= 0.10 * r["C"] / sdC
    st = g1(P)["t"] > g1(SPX)["t"] + 3 and g1(M)["b"] < g1(SPX)["b"]
    stp = g1(P); stm = g1(M)
    ok = stp["t"] >= T and not stm["ok"] and st
    print(f"  self-test: planted +10% RV per sd -> t {stp['t']:+.1f}; planted -10% -> {'FAIL' if not stm['ok'] else 'PASS'}: {'OK' if ok else 'BROKEN'}")
    if not ok: sys.exit("self-test broken -- no verdict")

    G1 = g1(SPX)
    pct = lambda b, sd: 100 * (math.exp(b * sd) - 1)
    print(f"\n  G1 in-sample HAR+VIX+C: b {G1['b']:+.4f}  NW t {G1['t']:+.2f}  n {G1['n']}  (= {pct(G1['b'], G1['sd']):+.1f}% next-day RV per 1 sd of C)")
    print("     eras " + "   ".join(f"{lo}-{hi % 100:02d} b {e[0]:+.4f} t {e[1]:+.2f}" for (lo, hi), e in zip(ERAS, G1["eras"]))
          + f"   -> {'PASS' if G1['ok'] else 'FAIL'}")
    G2 = g2(SPX)
    print(f"  G2 OOS 2009+: mean loss gain {G2['m']:+.5f} (sq. log-RV)  DM t {G2['t']:+.2f}  n {G2['n']}   eras "
          + " ".join(f"{e:+.5f}" for e in G2["eras"]) + f"   -> {'PASS' if G2['ok'] else 'FAIL'}")

    # G3
    import pandas as pd
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import vix_curve_budget as VC, vix_daily_risk as VD
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        vx1 = VC.load_csv("../data/CBOE_DLY_VX1!, 1D_1f2b8.csv", "VX1"); vx2 = VC.load_csv("../data/CBOE_DLY_VX2!, 1D_7782c.csv", "VX2")
    i = vx1.index.intersection(vx2.index); vx1, vx2 = vx1.loc[i].sort_index(), vx2.loc[i].sort_index()
    exps = VD.vx_expiries(i[0], i[-1]); rows_, best, second, clean = VD.scan_offsets(vx1, vx2, exps)
    if not clean: sys.exit("VX roll not identified -- no G3")
    rolls = VD.roll_days(vx1.index, exps, best["offset"]); pnl, _ = VD.daily_pnl(vx1, vx2, rolls)
    pnl = pnl[pnl.index >= pd.Timestamp("2006-01-01")]
    Cs = [(d, F[d]["C"]) for d in fd if F[d]["C"] is not None]; Cd = [d for d, _ in Cs]; Cv = np.array([v for _, v in Cs])
    vv = np.array([vix[d] for d in vd])
    def fear_flat(t):
        j = bisect.bisect_right(Cd, t - dt.timedelta(days=2)) - 1
        return j >= 250 and Cv[j] > np.quantile(Cv[j - 250:j], 0.8)
    def vix_flat(t):
        j = bisect.bisect_left(vd, t) - 1
        return j >= 250 and vv[j] > np.quantile(vv[j - 250:j], 0.8)
    def stats(mask, cost=0.0):
        p = pnl.to_numpy() * (~mask); sw = np.abs(np.diff(np.r_[0, (~mask).astype(int)])).sum()
        cum = np.cumsum(p) - 0; peak = np.maximum.accumulate(np.r_[0, cum])[1:]; dd = (cum - peak).min()
        tot = p.sum() - cost * sw
        return tot, dd, tot / abs(dd), 1 - mask.mean(), sw
    dts = [x.date() for x in pnl.index]
    mb = np.zeros(len(dts), bool); mf = np.array([fear_flat(t) for t in dts]); mc = np.array([vix_flat(t) for t in dts])
    B, Fz, Cc = stats(mb), stats(mf), stats(mc)
    G3 = Fz[2] > B[2] and Fz[2] > Cc[2] and Fz[1] > Cc[1]
    print(f"\n  G3 short VX1 {dts[0]}..{dts[-1]} (roll offset {best['offset']}), vol points, gross:")
    for lab, S in (("always short", B), ("fear rule (C top fifth)", Fz), ("VIX control (VIX top fifth)", Cc)):
        print(f"     {lab:<28} total {S[0]:+8.1f}  worst DD {S[1]:8.1f}  total/|DD| {S[2]:5.2f}  in market {S[3]:.0%}  switches {S[4]}")
    print(f"     -> {'PASS' if G3 else 'FAIL'}")
    Fz1, Cc1 = stats(mf, 0.05), stats(mc, 0.05)
    print(f"     reported, 1 tick (0.05) per switch: fear total/|DD| {Fz1[2]:.2f}   VIX control {Cc1[2]:.2f}")
    both = mf | mc; Bt = stats(both)
    print(f"     reported, flat when EITHER fires: total {Bt[0]:+.1f}  DD {Bt[1]:.1f}  total/|DD| {Bt[2]:.2f}  in market {Bt[3]:.0%}")
    for lo, hi in ((2006, 2012), (2013, 2019), (2020, 2026)):
        m = np.array([lo <= t.year <= hi for t in dts]); pp = pnl.to_numpy()[m]
        print(f"     era {lo}-{hi}: always {pp.sum():+7.1f}   fear {(pp * ~mf[m]).sum():+7.1f}   VIX-ctl {(pp * ~mc[m]).sum():+7.1f}")

    # reported
    print("\n  reported (no gates):")
    for k in ("z_EPU", "z_GPR"):
        g = g1(SPX, k); print(f"    component {k:<6} b {g['b']:+.4f}  t {g['t']:+.2f}  ({pct(g['b'], g['sd']):+.1f}% per sd)  eras " + " ".join(f"{e[0]:+.4f}" for e in g["eras"]))
    g = fit(SPX, "C3"); print(f"    C3 (with TPU, from 2016) b {g[0]:+.4f}  t {g[1]:+.2f}  n {g[2]}  ({pct(g[0], g[3]):+.1f}% per sd)")
    g = fit(SPX, "z_TPU"); print(f"    TPU alone (2016+)       b {g[0]:+.4f}  t {g[1]:+.2f}  n {g[2]}")
    g = fit(SPX, "C_1"); print(f"    t-1 timing              b {g[0]:+.4f}  t {g[1]:+.2f}  ({pct(g[0], g[3]):+.1f}% per sd)")
    g = fit(SPX, "C", "y5"); print(f"    5-day RV horizon        b {g[0]:+.4f}  t {g[1]:+.2f}  ({pct(g[0], g[3]):+.1f}% per sd)")
    gN = g1(NAS); print(f"    NAS100                  b {gN['b']:+.4f}  t {gN['t']:+.2f}  ({pct(gN['b'], gN['sd']):+.1f}% per sd)  eras " + " ".join(f"{e[0]:+.4f}" for e in gN["eras"]))
    g2N = g2(NAS); print(f"    NAS100 OOS              DM t {g2N['t']:+.2f}  eras " + " ".join(f"{e:+.5f}" for e in g2N["eras"]))
    rr = [r for r in s]; b, se = nw(np.column_stack([np.ones(len(rr)), [r["C"] for r in rr]]), [r["ret"] for r in rr])
    print(f"    direction: SPX RTH return on C  b {b[1]:+.3f} bp per unit  t {b[1] / se[1]:+.2f}")
    # HAR alone vs no VIX, for context
    b0, se0 = nw(np.column_stack([np.ones(len(s)), [r["C"] for r in s]]), [r["y"] for r in s])
    print(f"    C alone (no HAR/VIX)    b {b0[1]:+.4f}  t {b0[1] / se0[1]:+.2f}   -- how much is already in VIX")
    # trends monthly
    TR = {r["month"]: r for r in csv.DictReader(open("../data/v50/trends_monthly.csv"))}
    mrv = {}
    for r in SPX: mrv.setdefault(f"{r['d'].year:04d}-{r['d'].month:02d}", []).append(r["y"])
    ms = sorted(mrv)
    for k in ("crash", "recession"):
        xs, ys, cs = [], [], []
        for a, b_ in zip(ms, ms[1:]):
            if a in TR and TR[a][k]:
                xs.append(math.log(float(TR[a][k]) + 1)); ys.append(np.mean(mrv[b_])); cs.append(np.mean(mrv[a]))
        X = np.column_stack([np.ones(len(xs)), cs, xs]); bb, ss = nw(X, ys, 3)
        print(f"    Google Trends UK '{k}' (monthly, next-month RV | this month's RV): b {bb[2]:+.3f}  t {bb[2] / ss[2]:+.2f}  n {len(xs)}")
    print(f"\n  VERDICTS  G1 {'PASS' if G1['ok'] else 'FAIL'}   G2 {'PASS' if G2['ok'] else 'FAIL'}   G3 {'PASS' if G3 else 'FAIL'}"
          f"   -> {'USEFUL' if G1['ok'] and G2['ok'] and G3 else ('REAL, NOT YET USABLE' if G1['ok'] and G2['ok'] else 'NOT USEFUL')}")


if __name__ == "__main__":
    main()
