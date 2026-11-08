#!/usr/bin/env python3
"""PREREGISTRATION_v53 -- credit spreads (BAA10Y) and the stock-bond correlation as risk overlays, judged
against what a VIX rule already does. SPX500 + NAS100, equal weight; costs/financing as v52 (ma_overlay_v52.Inst).
Position over close t -> t+1 (return index t+1) uses data dated <= t-1 (FRED one-day publication lag).
I am not a financial adviser. This is a measurement, not a recommendation."""
import csv, datetime as dt, hashlib, sys, bisect
import numpy as np
from ma_overlay_v52 import Inst, stats, portfolio, era_dd, VX

VERSION = "1.0"
PINS = {"../PREREGISTRATION_v53.md": "c8ed1d96884525cf07874e80f6cd6b925b30c30cd81094d7fcd4c9b52d11ffd8",
        "daily_close.py": "617eadd2fc60ae99a736e0fa8b7455e12f0c3918069f3587f4176e5b0044c88c",
        "../data/v53/raw/BAA10Y.csv": "1c77186b4991482fffb1c521eb7e010609d15bfb3e5b1e9e45c987d7c59558d6",
        "../data/v53/raw/DGS10.csv": "98af25bb5f90d3dbcd181dbee47b9eb48d57813d09b7b0aed299f258c9427c8d"}
START = dt.date(2006, 1, 3)

def fred(path):
    d, v = [], []
    for r in csv.reader(open(path)):
        try: x = float(r[1]); dd = dt.date.fromisoformat(r[0])
        except ValueError: continue
        d.append(dd); v.append(x)
    return d, np.array(v)

def last_idx(dates, day):          # last obs dated <= day
    return bisect.bisect_right(dates, day) - 1

def main():
    for f, h in PINS.items():
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} changed -- refused")
    print(f"credit_v53.py v{VERSION}   PREREGISTRATION_v53 (c8ed1d96…), daily_close.py, BAA10Y (1c77186b…), DGS10 (98af25bb…) match\n"
          "  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    I = [Inst("spx500usd"), Inst("nas100usd")]
    bd, bv = fred("../data/v53/raw/BAA10Y.csv"); yd, yv = fred("../data/v53/raw/DGS10.csv")
    # credit: D20 and its trailing-250 80th pct
    D20 = np.full(len(bv), np.nan); D20[20:] = bv[20:] - bv[:-20]
    c_off = np.zeros(len(bv), bool)
    for m in range(270, len(bv)): c_off[m] = D20[m] > np.quantile(D20[m - 250:m], 0.8)
    z_off = np.zeros(len(bv), bool)
    for m in range(250, len(bv)):
        w = bv[m - 250:m]; z_off[m] = (bv[m] - w.mean()) / w.std() > 1.0
    vd, vv = VX[0], np.array(VX[1]); v_off = np.zeros(len(vv), bool)
    for m in range(250, len(vv)): v_off[m] = vv[m] > np.quantile(vv[m - 250:m], 0.8)
    # stock-bond correlation on SPX dates: bond return on SPX day d = -(y(d) - y(prev SPX day)), y as-of d
    S = I[0]; sd = S.ds; sr = np.r_[0.0, np.log(S.c[1:] / S.c[:-1])]
    def rho_series(Yd, Yv):
        y = np.array([Yv[max(last_idx(Yd, d), 0)] for d in sd]); br = np.r_[0.0, -(y[1:] - y[:-1])]
        rho = np.full(len(sd), np.nan)
        for t in range(64, len(sd)):
            a, b = sr[t - 63:t], br[t - 63:t]                       # returns dated <= t-1
            if a.std() > 0 and b.std() > 0: rho[t] = np.corrcoef(a, b)[0, 1]
        return dict(zip(sd, rho))
    RHO = rho_series(yd, yv)

    def pos_from(inst, rule):
        """rule(day_t) -> 1 (in) / 0 (risk-off) / None, using data dated <= t-1. pos[i] = rule(ds[i-1])."""
        p = np.full(len(inst.ds), np.nan)
        for i in range(1, len(inst.ds)):
            t = inst.ds[i - 1]
            if t < START: continue
            v = rule(t)
            if v is not None: p[i] = v
        return p
    def credit_rule(off):
        def f(t):
            m = last_idx(bd, t - dt.timedelta(days=1)); return None if m < 270 else (0.0 if off[m] else 1.0)
        return f
    def vix_rule(t):
        m = last_idx(vd, t - dt.timedelta(days=1)); return None if m < 250 else (0.0 if v_off[m] else 1.0)
    def corr_rule(R):
        def f(t):
            k = bisect.bisect_left(sd, t); k = min(k, len(sd) - 1)
            if sd[k] != t: k = max(k - 1, 0)
            r = R[sd[k]]; return None if np.isnan(r) else (0.0 if r > 0 else 1.0)
        return f
    rules = {"B&H": lambda t: 1.0, "VIX": vix_rule, "CREDIT": credit_rule(c_off), "CORR": corr_rule(RHO)}
    P = {k: [pos_from(i, r) for i in I] for k, r in rules.items()}
    # align all strategies to the same start: first return where every rule is defined
    for j in range(2):
        st = max(int(np.argmax(~np.isnan(P[k][j]))) for k in P)
        for k in P: P[k][j][:st] = np.nan
    OR = lambda a, b: [np.where(np.isnan(x) | np.isnan(y), np.nan, np.minimum(x, y)) for x, y in zip(a, b)]
    P["CREDIT|VIX"] = OR(P["CREDIT"], P["VIX"]); P["CORR|VIX"] = OR(P["CORR"], P["VIX"])
    R = {k: portfolio(I, [i.pnl(p) for i, p in zip(I, ps)]) for k, ps in P.items()}
    ST = {k: stats(*v) for k, v in R.items()}; ED = {k: era_dd(*v) for k, v in R.items()}
    # self-test
    ones_ok = abs(ST["B&H"]["sh"] - stats(*portfolio(I, [i.pnl(np.where(np.isnan(p), np.nan, 1.0)) for i, p in zip(I, P["CREDIT"])]))["sh"]) < 1e-9
    pf = [np.where(np.isnan(p), np.nan, (i.r > 0).astype(float)) for i, p in zip(I, P["CREDIT"])]
    pf_ok = stats(*portfolio(I, [i.pnl(p) for i, p in zip(I, pf)]))["sh"] > 3
    print(f"  self-test: always-on == B&H, perfect foresight >> 0: {'OK' if ones_ok and pf_ok else 'BROKEN'}")
    if not (ones_ok and pf_ok): sys.exit("self-test broken -- no verdict")
    d0 = R["B&H"][0][~np.isnan(R["B&H"][1])][0]
    print(f"\n  SPX+NAS equal weight, {d0}..2026-09-25, net of spread and financing")
    for k in ("B&H", "VIX", "CREDIT", "CREDIT|VIX", "CORR", "CORR|VIX"):
        s = ST[k]; tim = np.nanmean(np.r_[P[k][0], P[k][1]])
        print(f"    {k:<11} Sharpe {s['sh']:+.3f}  CAGR {s['cagr']*100:+.2f}%  max DD {s['dd']*100:6.1f}%  Calmar {s['cal']:.3f}  in market {tim:.0%}"
              f"   era DD " + " ".join(f"{x*100:.1f}%" for x in ED[k]))
    rng = np.random.default_rng(53); verdict = {}
    for k in ("CREDIT", "CORR"):
        g1 = ST[k]["dd"] >= 0.75 * ST["B&H"]["dd"] and all(a >= b for a, b in zip(ED[k], ED["B&H"]))
        null = []
        for _ in range(500):
            ps = []
            for p in P[k]:
                v = ~np.isnan(p); q = p.copy(); q[v] = np.roll(p[v], int(rng.integers(250, v.sum() - 250))); ps.append(q)
            null.append(stats(*portfolio(I, [i.pnl(q) for i, q in zip(I, ps)]))["sh"])
        q975 = np.quantile(null, 0.975); g2 = ST[k]["sh"] > q975
        c = k + "|VIX"; g3 = ST[c]["cal"] > ST["VIX"]["cal"] and ST[c]["sh"] >= ST["VIX"]["sh"] - 0.05
        verdict[k] = (g1, g2, g3)
        print(f"\n  {k}: G1 DD {ST[k]['dd']*100:.1f}% vs 0.75xB&H {0.75*ST['B&H']['dd']*100:.1f}%, eras lower {all(a >= b for a, b in zip(ED[k], ED['B&H']))}  -> {'PASS' if g1 else 'FAIL'}")
        print(f"     G2 Sharpe {ST[k]['sh']:+.3f} vs null 97.5th {q975:+.3f} (median {np.median(null):+.3f})  -> {'PASS' if g2 else 'FAIL'}")
        print(f"     G3 {c} Calmar {ST[c]['cal']:.3f} vs VIX {ST['VIX']['cal']:.3f}; Sharpe {ST[c]['sh']:+.3f} vs {ST['VIX']['sh']:+.3f}  -> {'PASS' if g3 else 'FAIL'}")
        print(f"     {k}: {'USEFUL' if all(verdict[k]) else 'NOT USEFUL'}")
    print("\n  reported (no gates):")
    Pz = [pos_from(i, credit_rule(z_off)) for i in I]
    for j in range(2): Pz[j][:int(np.argmax(~np.isnan(P['B&H'][j])))] = np.nan
    s = stats(*portfolio(I, [i.pnl(p) for i, p in zip(I, Pz)])); print(f"    credit LEVEL (z>1): Sharpe {s['sh']:+.3f} DD {s['dd']*100:.1f}% Calmar {s['cal']:.3f}")
    d2 = []
    for r in csv.DictReader(open("../data/v31/DGS2.csv")):
        try: d2.append((dt.date.fromisoformat(r[list(r)[0]]), float(r[list(r)[1]])))
        except ValueError: pass
    R2 = rho_series([a for a, _ in d2], np.array([b for _, b in d2]))
    P2 = [pos_from(i, corr_rule(R2)) for i in I]
    for j in range(2): P2[j][:int(np.argmax(~np.isnan(P['B&H'][j])))] = np.nan
    s = stats(*portfolio(I, [i.pnl(p) for i, p in zip(I, P2)])); print(f"    correlation with 2y yield: Sharpe {s['sh']:+.3f} DD {s['dd']*100:.1f}% Calmar {s['cal']:.3f}")
    for j, nm in enumerate(("SPX500", "NAS100")):
        line = "    " + nm + ": " + "  ".join(f"{k} {stats(np.array(I[j].ds), I[j].pnl(P[k][j]))['sh']:+.3f}/{stats(np.array(I[j].ds), I[j].pnl(P[k][j]))['dd']*100:.0f}%" for k in ("B&H", "VIX", "CREDIT", "CORR"))
        print(line + "   (Sharpe/maxDD)")
    rho_yr = {}
    for d, r in RHO.items():
        if not np.isnan(r) and d >= START: rho_yr.setdefault(d.year, []).append(r > 0)
    print("    share of days with rho > 0 by year: " + " ".join(f"{y % 100:02d}:{np.mean(v):.0%}" for y, v in sorted(rho_yr.items())))
    U = Inst("uk100gbp"); pu = pos_from(U, credit_rule(c_off)); pb = pos_from(U, lambda t: 1.0)
    pb[:int(np.argmax(~np.isnan(pu)))] = np.nan
    a, b = stats(np.array(U.ds), U.pnl(pu)), stats(np.array(U.ds), U.pnl(pb))
    print(f"    UK100 with US credit: Sharpe {a['sh']:+.3f} DD {a['dd']*100:.1f}%  vs B&H {b['sh']:+.3f} DD {b['dd']*100:.1f}%")
    print("    HY OAS: FRED history starts 2023-10-02 -> not computable as specified")
    print(f"\n  VERDICTS  CREDIT {'USEFUL' if all(verdict['CREDIT']) else 'NOT USEFUL'} (G1 {'P' if verdict['CREDIT'][0] else 'F'} G2 {'P' if verdict['CREDIT'][1] else 'F'} G3 {'P' if verdict['CREDIT'][2] else 'F'})"
          f"   CORR {'USEFUL' if all(verdict['CORR']) else 'NOT USEFUL'} (G1 {'P' if verdict['CORR'][0] else 'F'} G2 {'P' if verdict['CORR'][1] else 'F'} G3 {'P' if verdict['CORR'][2] else 'F'})")

if __name__ == "__main__":
    main()
