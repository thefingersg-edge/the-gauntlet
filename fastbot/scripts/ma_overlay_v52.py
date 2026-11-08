#!/usr/bin/env python3
"""PREREGISTRATION_v52 -- the 200-day moving average as a risk overlay.
Flag F_t = close_t > mean(last 200 closes incl. t). Position over close t -> t+1 = F_{t-1} (one-day delay).
Costs: one full quoted spread per switch (at the executing close); financing (DGS3MO+2.5%)/360 per calendar
night while long; flat earns 0. Portfolio = equal-weight mean of the four instruments' daily net returns.
I am not a financial adviser. This is a measurement, not a recommendation."""
import csv, datetime as dt, hashlib, math, sys, bisect
import numpy as np
from daily_close import daily

VERSION = "1.0"
PINS = {"../PREREGISTRATION_v52.md": "0101fb2f68ff08ced19821d0262ce556653825c363b2b9ce21bb8b19bc30a122",
        "daily_close.py": "617eadd2fc60ae99a736e0fa8b7455e12f0c3918069f3587f4176e5b0044c88c"}
STEMS = ("spx500usd", "nas100usd", "uk100gbp", "xauusd"); END = dt.date(2026, 9, 25)
ERAS = ((2005, 2012), (2013, 2019), (2020, 2026))

def series(path, col):
    d, v = [], []
    for r in csv.DictReader(open(path)):
        try: x = float(r[col])
        except (ValueError, KeyError): continue
        d.append(dt.date.fromisoformat(r[list(r)[0]])); v.append(x)
    return d, v

RT = series("../data/DGS3MO.csv", "DGS3MO")
VX = series("../data/VIXCLS.csv", "vix")
def asof(S, day, lag=0):
    i = bisect.bisect_right(S[0], day - dt.timedelta(days=lag)) - 1
    return S[1][max(i, 0)]

class Inst:
    def __init__(self, stem):
        D = daily(stem); self.ds = [d for d in sorted(D) if d <= END]
        self.c = np.array([D[d][0] for d in self.ds]); self.sp = np.array([D[d][1] for d in self.ds]) / 1e4
        self.r = np.r_[0.0, self.c[1:] / self.c[:-1] - 1]
        nights = np.r_[0, [(b - a).days for a, b in zip(self.ds, self.ds[1:])]]
        rate = np.array([asof(RT, d) for d in self.ds])
        self.fin = np.r_[0.0, nights[1:] * (rate[:-1] + 2.5) / 100 / 360]
        self.vix = np.array([asof(VX, d) for d in self.ds])          # VIX on or before date
    def flag(self, n=200):
        f = np.full(len(self.c), np.nan); cs = np.cumsum(np.r_[0, self.c])
        m = (cs[n:] - cs[:-n]) / n; f[n - 1:] = (self.c[n - 1:] > m).astype(float); return f
    def pnl(self, pos):
        """pos[i] = exposure held over return i (close i-1 -> close i). NaN -> not started."""
        p = np.nan_to_num(pos); start = np.argmax(~np.isnan(pos))
        prev = np.r_[0.0, p[:-1]]; sw = np.abs(p - prev)
        cost = sw * np.r_[self.sp[0], self.sp[:-1]]                  # executed at the previous close
        net = p * self.r - p * self.fin - cost; net[:start] = np.nan
        return net

def delayed(f, lag):
    out = np.full(len(f), np.nan); out[lag:] = f[:-lag]; return out

def portfolio(insts, nets):
    days = sorted(set().union(*[i.ds for i in insts])); idx = {d: k for k, d in enumerate(days)}
    M = np.full((len(days), len(insts)), np.nan)
    for j, (I, n) in enumerate(zip(insts, nets)):
        for d, x in zip(I.ds, n): M[idx[d], j] = x
    live = ~np.isnan(M).all(1); started = np.maximum.accumulate(live)
    M2 = np.where(np.isnan(M), 0.0, M); cnt = (~np.isnan(np.maximum.accumulate(np.where(np.isnan(M), -np.inf, 1), axis=0)) & (np.maximum.accumulate(~np.isnan(M), axis=0))).sum(1)
    port = np.where(cnt > 0, M2.sum(1) / np.maximum(cnt, 1), np.nan)
    return np.array(days), port

def stats(days, x):
    m = ~np.isnan(x); x = x[m]; d = days[m]
    eq = np.cumprod(1 + x); dd = (eq / np.maximum.accumulate(eq) - 1).min()
    yrs = (d[-1] - d[0]).days / 365.25; cagr = eq[-1] ** (1 / yrs) - 1
    sh = x.mean() / x.std() * math.sqrt(252)
    return dict(sh=sh, dd=dd, cagr=cagr, cal=cagr / abs(dd))

def era_dd(days, x):
    out = []
    for lo, hi in ERAS:
        m = np.array([lo <= d.year <= hi for d in days]) & ~np.isnan(x)
        eq = np.cumprod(1 + x[m]); out.append((eq / np.maximum.accumulate(eq) - 1).min())
    return out

def main():
    for f, h in PINS.items():
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} changed -- refused")
    print(f"ma_overlay_v52.py v{VERSION}   PREREGISTRATION_v52 (0101fb2f…) and daily_close.py (617eadd2…) match\n"
          "  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    I = [Inst(s) for s in STEMS]
    F = [i.flag(200) for i in I]
    common_start = [np.argmax(~np.isnan(f)) + 2 for f in F]
    def bh(i, k):
        p = np.full(len(i.c), np.nan); p[common_start[k]:] = 1.0; return p
    ovl = [i.pnl(delayed(f, 2)) for i, f in zip(I, F)]          # F_{t-1} held over close t -> t+1 = return index t+1
    bhn = [i.pnl(bh(i, k)) for k, i in enumerate(I)]
    days, PO = portfolio(I, ovl); _, PB = portfolio(I, bhn)
    # self-test: a perfect-foresight flag must beat the null; a constant-1 flag must equal B&H
    pf = [np.r_[(i.r[1:] > 0).astype(float), 0.0] for i in I]
    perfect = [i.pnl(np.where(np.isnan(delayed(f, 2)), np.nan, np.r_[np.nan, p[:-1]])) for i, f, p in zip(I, F, pf)]
    ones = [i.pnl(np.where(np.isnan(delayed(f, 2)), np.nan, 1.0)) for i, f in zip(I, F)]
    st_ok = stats(*portfolio(I, perfect))["sh"] > 3 and abs(stats(*portfolio(I, ones))["sh"] - stats(days, PB)["sh"]) < 0.02
    print(f"  self-test: perfect-foresight flag Sharpe >> 0 and always-on flag == buy-and-hold: {'OK' if st_ok else 'BROKEN'}")
    if not st_ok: sys.exit("self-test broken -- no verdict")
    so, sb = stats(days, PO), stats(days, PB); eo, eb = era_dd(days, PO), era_dd(days, PB)
    print(f"\n  portfolio ({days[~np.isnan(PO)][0]}..{days[-1]}):")
    print(f"    buy & hold  Sharpe {sb['sh']:+.3f}  CAGR {sb['cagr']*100:+.2f}%  max DD {sb['dd']*100:6.1f}%  Calmar {sb['cal']:.3f}   era DD " + " ".join(f"{x*100:.1f}%" for x in eb))
    print(f"    200-day MA  Sharpe {so['sh']:+.3f}  CAGR {so['cagr']*100:+.2f}%  max DD {so['dd']*100:6.1f}%  Calmar {so['cal']:.3f}   era DD " + " ".join(f"{x*100:.1f}%" for x in eo))
    g1 = so["dd"] >= 0.75 * sb["dd"] and all(a >= b for a, b in zip(eo, eb))
    print(f"  G1 drawdown: overlay {so['dd']*100:.1f}% vs 0.75 x B&H {0.75*sb['dd']*100:.1f}%; each era lower: {all(a >= b for a, b in zip(eo, eb))}  -> {'PASS' if g1 else 'FAIL'}")
    rng = np.random.default_rng(52); null = []
    for _ in range(500):
        nets = []
        for i, f in zip(I, F):
            v = ~np.isnan(f); fv = f[v]; off = int(rng.integers(250, len(fv) - 250))
            g = f.copy(); g[v] = np.roll(fv, off); nets.append(i.pnl(delayed(g, 2)))
        null.append(stats(*portfolio(I, nets))["sh"])
    q95 = np.quantile(null, 0.95); g2 = so["sh"] > q95
    print(f"  G2 timing: overlay Sharpe {so['sh']:+.3f} vs circular-shift null 95th pct {q95:+.3f} (null median {np.median(null):+.3f})  -> {'PASS' if g2 else 'FAIL'}")
    g3 = so["sh"] >= sb["sh"] - 0.05 and so["cal"] > sb["cal"]
    print(f"  G3 return-to-risk: Sharpe {so['sh']:+.3f} vs B&H {sb['sh']:+.3f} (-0.05 allowed); Calmar {so['cal']:.3f} vs {sb['cal']:.3f}  -> {'PASS' if g3 else 'FAIL'}")
    # G4: on top of implied-vol sizing (SPX, NAS)
    def ivpos(i, k, flag=None):
        e = np.minimum(1.5, 15.0 / np.r_[np.nan, i.vix[:-1]])          # VIX dated <= t-1 for the position over t -> t+1
        e = np.r_[np.nan, e[:-1]]
        e[:common_start[k]] = np.nan
        if flag is not None: e = e * delayed(flag, 2)
        return e
    base = [I[k].pnl(ivpos(I[k], k)) for k in (0, 1)]; withf = [I[k].pnl(ivpos(I[k], k, F[k])) for k in (0, 1)]
    d2, PB2 = portfolio(I[:2], base); _, PW2 = portfolio(I[:2], withf)
    s_b2, s_w2 = stats(d2, PB2), stats(d2, PW2)
    g4 = s_w2["cal"] > s_b2["cal"] and s_w2["sh"] >= s_b2["sh"] - 0.05
    print(f"  G4 on top of IV sizing (SPX+NAS): base Sharpe {s_b2['sh']:+.3f} DD {s_b2['dd']*100:.1f}% Calmar {s_b2['cal']:.3f}  ->  +MA Sharpe {s_w2['sh']:+.3f} DD {s_w2['dd']*100:.1f}% Calmar {s_w2['cal']:.3f}   -> {'PASS' if g4 else 'FAIL'}")
    print("\n  reported (no gates):")
    for k, s in enumerate(STEMS):
        a, b = stats(np.array(I[k].ds), ovl[k]), stats(np.array(I[k].ds), bhn[k])
        f = delayed(F[k], 2); tim = np.nanmean(f); sw = int(np.nansum(np.abs(np.diff(f[~np.isnan(f)]))))
        print(f"    {s:<9} B&H Sharpe {b['sh']:+.3f} DD {b['dd']*100:6.1f}%  |  MA Sharpe {a['sh']:+.3f} DD {a['dd']*100:6.1f}%  in market {tim:.0%}  switches {sw}")
    F100 = [i.flag(100) for i in I]; o100 = [i.pnl(np.where(np.isnan(delayed(f2, 2)), np.nan, delayed(f1, 2))) for i, f1, f2 in zip(I, F100, F)]
    s100 = stats(*portfolio(I, o100)); print(f"    100-day MA portfolio: Sharpe {s100['sh']:+.3f} DD {s100['dd']*100:.1f}% Calmar {s100['cal']:.3f}")
    same = [i.pnl(np.where(np.isnan(delayed(f, 2)), np.nan, delayed(f, 1))) for i, f in zip(I, F)]
    ss = stats(*portfolio(I, same)); print(f"    same-day execution (no delay): Sharpe {ss['sh']:+.3f} DD {ss['dd']*100:.1f}% Calmar {ss['cal']:.3f}")
    def vixflag(i):
        v = i.vix; f = np.full(len(v), np.nan)
        for t in range(250, len(v)): f[t] = 0.0 if v[t] > np.quantile(v[t - 250:t], 0.8) else 1.0
        return f
    vr = [I[k].pnl(np.where(np.isnan(delayed(F[k], 2)), np.nan, delayed(vixflag(I[k]), 1))) for k in (0, 1)]
    ma2 = [ovl[0], ovl[1]]; bh2 = [bhn[0], bhn[1]]
    for lab, nets in (("B&H", bh2), ("200-day MA", ma2), ("VIX rule (v50)", vr)):
        s = stats(*portfolio(I[:2], nets)); print(f"    SPX+NAS {lab:<15} Sharpe {s['sh']:+.3f} DD {s['dd']*100:6.1f}% Calmar {s['cal']:.3f}")
    print(f"\n  VERDICTS  G1 {'PASS' if g1 else 'FAIL'}   G2 {'PASS' if g2 else 'FAIL'}   G3 {'PASS' if g3 else 'FAIL'}   ->"
          f" {'USEFUL RISK OVERLAY' if g1 and g2 and g3 else 'NOT USEFUL'}   |  G4 {'PASS (adds to vol sizing)' if g4 else 'FAIL (does not add to vol sizing)'}")

if __name__ == "__main__":
    main()
