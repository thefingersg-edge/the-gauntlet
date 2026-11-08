#!/usr/bin/env python3
"""PREREGISTRATION_GRAN1 harness.  python3 gran1_run.py main   (once)  |  python3 gran1_run.py sealed H1|H2|H3 (only if main passed it)
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, math, bisect, hashlib, datetime as dt
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, os.path.join(FB, "scripts"))
DOC = (os.path.join(FB, "PREREGISTRATION_GRAN1.md"), "67e1d50da7008d4b2397118eb1b7b0f587ba8479cfb47140c424cc5c136893fb")
TAB = (os.path.join(FB, "data", "sharadar", "cache", "gran_daily.csv"), "6377d9b212bc828463648d0b68c9ffcb3a354d11295ea7fb45629fc53e33b0fa")
SEAL = dt.date(2023, 7, 1); END = dt.date(2026, 9, 30); T = 2.39
OUT = []
def P(s=""): print(s, flush=True); OUT.append(s)

def nw(X, y, lags):
    X = np.asarray(X, float); y = np.asarray(y, float); XtXi = np.linalg.inv(X.T @ X); b = XtXi @ X.T @ y; u = y - X @ b
    Xu = X * u[:, None]; S = Xu.T @ Xu
    for l in range(1, lags + 1):
        w = 1 - l / (lags + 1); G = Xu[l:].T @ Xu[:-l]; S += w * (G + G.T)
    return b, np.sqrt(np.diag(XtXi @ S @ XtXi))

def gran():
    rows = list(csv.DictReader(open(TAB[0]))); g = {}
    for r in rows: g[dt.date.fromisoformat(r["date"])] = r
    return g

def zseries(g, col, window=500):
    ds = sorted(d for d in g if g[d][col]); v = np.array([float(g[d][col]) for d in ds]); z = {}
    for i in range(window, len(ds)):
        w = v[i - window:i]; z[ds[i]] = (v[i] - w.mean()) / w.std() if w.std() > 0 else np.nan
    return z

def asof(z, day):
    ks = asof.cache.setdefault(id(z), sorted(z)); i = bisect.bisect_right(ks, day) - 1
    return z[ks[i]] if i >= 0 and (day - ks[i]).days <= 7 else np.nan
asof.cache = {}

def r20_rows(stem, z, lo, hi, H=20):
    from daily_close import daily
    D = daily(stem); ds = sorted(D); c = np.array([D[d][0] for d in ds]); out = []
    for i in range(len(ds) - H):
        d = ds[i]
        if not (lo <= d < hi) or ds[i + H] > hi + dt.timedelta(days=40): continue
        if ds[i + H] >= hi and hi == SEAL: continue                       # target must end before the seal
        s = asof(z, d - dt.timedelta(days=1))
        if np.isfinite(s): out.append((d, s, math.log(c[i + H] / c[i]) * 1e4))
    return out

def reg(rows, lags=20):
    X = np.column_stack([np.ones(len(rows)), [r[1] for r in rows]]); b, se = nw(X, [r[2] for r in rows], lags); return b[1], b[1] / se[1], len(rows)

def h12(name, col, eras, lo, two_sided, stem="spx500usd", hi=SEAL, H=20):
    z = zseries(gran(), col); rows = r20_rows(stem, z, lo, hi, H); b, t, n = reg(rows, max(H, 5))
    er = [reg([r for r in rows if a <= r[0].year <= e], max(H, 5)) for a, e in eras]
    sgn = np.sign(b); ok_t = (abs(t) >= T) if two_sided else (b > 0 and t >= T)
    ok = ok_t and all(np.sign(x[0]) == sgn for x in er) and (two_sided or sgn > 0)
    return b, t, n, er, ok, rows

def rv_rows(stem, lo, hi):
    from reactive import load
    days = load(os.path.join(FB, "data"), stem); ds = sorted(d for d in days if d >= dt.date(2004, 6, 1)); RV = {}
    for d in ds:
        ks = sorted(days[d]); c = np.array([days[d][k][3] for k in ks]); RV[d] = float(np.sum(np.diff(np.log(c)) ** 2))
    vix = {}
    for r in csv.DictReader(open(os.path.join(FB, "data", "VIXCLS.csv"))):
        try: vix[dt.date.fromisoformat(r["date"])] = float(r["vix"])
        except ValueError: pass
    vd = sorted(vix); g = gran(); gd = sorted(d for d in g if g[d]["disp_L"]); gl = {d: math.log(float(g[d]["disp_L"])) for d in gd if float(g[d]["disp_L"]) > 0}
    lr = np.log(np.array([RV[d] for d in ds])); out = []
    for i in range(22, len(ds)):
        T_ = ds[i]
        if not (lo <= T_ < hi): continue
        j = bisect.bisect_left(vd, T_) - 1
        if j < 0: continue
        k = bisect.bisect_right(gd, ds[i - 2])                                  # disp dated <= t-1 where target day is t+1
        w = [gl[d] for d in gd[max(0, k - 5):k] if d in gl]
        if len(w) < 5: continue
        out.append(dict(d=T_, y=lr[i], h1=lr[i - 1], h5=lr[i - 5:i].mean(), h22=lr[i - 22:i].mean(), lv=math.log(vix[vd[j]]), ds=float(np.mean(w))))
    return out

def h3(stem="spx500usd", lo=dt.date(2005, 1, 1), hi=SEAL):
    R = rv_rows(stem, lo, hi)
    def fit(rs):
        X = np.column_stack([np.ones(len(rs)), [r["h1"] for r in rs], [r["h5"] for r in rs], [r["h22"] for r in rs], [r["lv"] for r in rs], [r["ds"] for r in rs]])
        b, se = nw(X, [r["y"] for r in rs], 5); return b[5], b[5] / se[5], len(rs), np.std([r["ds"] for r in rs])
    b, t, n, sd = fit(R); er = [fit([r for r in R if a <= r["d"].year <= e]) for a, e in ((2005, 2012), (2013, 2017), (2018, 2023))]
    f = lambda r, c: [1, r["h1"], r["h5"], r["h22"], r["lv"]] + ([r["ds"]] if c else [])
    d_ = []; months = sorted({(r["d"].year, r["d"].month) for r in R if r["d"].year >= 2010})
    for (y, m) in months:
        ms = dt.date(y, m, 1); tr = [r for r in R if r["d"] < ms]; te = [r for r in R if r["d"].year == y and r["d"].month == m]
        Y = np.array([r["y"] for r in tr])
        b0 = np.linalg.lstsq(np.array([f(r, 0) for r in tr]), Y, rcond=None)[0]; b1 = np.linalg.lstsq(np.array([f(r, 1) for r in tr]), Y, rcond=None)[0]
        for r in te: d_.append((r["y"] - np.dot(b0, f(r, 0))) ** 2 - (r["y"] - np.dot(b1, f(r, 1))) ** 2)
    d_ = np.array(d_); bm, sem = nw(np.ones((len(d_), 1)), d_, 5); dm = bm[0] / sem[0]
    ok = b > 0 and t >= T and all(e[0] > 0 for e in er) and dm >= 2.0
    return b, t, n, sd, er, dm, ok

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    for f, h in (DOC, TAB):
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} changed -- refused")
    log = os.path.join(FB, "data", "run_gran1.log")
    if mode == "main":
        if os.path.exists(log): sys.exit("main already run once")
        P("gran1_run.py main   PREREGISTRATION_GRAN1 and gran_daily.csv match;  sample ends 2023-06-30 (sealed after)\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
        b, t, n, er, ok1, rows1 = h12("H1", "ins_ratio30", ((2008, 2012), (2013, 2017), (2018, 2023)), dt.date(2008, 1, 1), False)
        P(f"  H1 insiders (ratio z) -> SPX 20d: slope {b:+.1f} bp/sd  NW t {t:+.2f}  n {n}   eras " + " ".join(f"{e[0]:+.1f}(t {e[1]:+.2f})" for e in er) + f"  -> {'PASS' if ok1 else 'FAIL'}")
        b, t, n, er, ok2, rows2 = h12("H2", "ear_L28", ((2005, 2012), (2013, 2017), (2018, 2023)), dt.date(2005, 1, 1), True)
        P(f"  H2 large-cap earnings reaction (z) -> SPX 20d: slope {b:+.1f} bp/sd  NW t {t:+.2f}  n {n}   eras " + " ".join(f"{e[0]:+.1f}(t {e[1]:+.2f})" for e in er) + f"  -> {'PASS' if ok2 else 'FAIL'}")
        b, t, n, sd, er, dm, ok3 = h3()
        P(f"  H3 dispersion -> next-day SPX RV beyond HAR+VIX: b {b:+.4f}  NW t {t:+.2f}  n {n}  ({100*(math.exp(b*sd)-1):+.1f}% RV per sd)   eras " + " ".join(f"{e[0]:+.4f}(t {e[1]:+.2f})" for e in er) + f"   OOS DM t {dm:+.2f}  -> {'PASS' if ok3 else 'FAIL'}")
        P("\n  reported (not gated):")
        for nm, col, lo, two in (("H1", "ins_ratio30", dt.date(2008, 1, 1), False), ("H2", "ear_L28", dt.date(2005, 1, 1), True)):
            bb, tt, nn, ee, _, _ = h12(nm, col, ((2005, 2012), (2013, 2017), (2018, 2023)), lo, two, stem="nas100usd")
            P(f"    {nm} on NAS100: slope {bb:+.1f} bp/sd  t {tt:+.2f}")
        bb, tt, nn, ee, _, _ = h12("H1", "ins_ratio30", ((2008, 2012), (2013, 2017), (2018, 2023)), dt.date(2008, 1, 1), False, H=60)
        P(f"    H1 at 60 days: slope {bb:+.1f} bp/sd  t {tt:+.2f}")
        b3 = h3("nas100usd"); P(f"    H3 on NAS100: b {b3[0]:+.4f} t {b3[1]:+.2f}  DM t {b3[5]:+.2f}")
        for nm, rows in (("H1", rows1), ("H2", rows2)):
            fav = [r for r in rows if (r[1] > 0)]; P(f"    {nm} timing (signal > 0): mean 20d SPX {np.mean([r[2] for r in fav]):+.0f} bp on {len(fav)} days vs all days {np.mean([r[2] for r in rows]):+.0f} bp")
        P(f"\n  VERDICTS  H1 {'PASS' if ok1 else 'FAIL'}   H2 {'PASS' if ok2 else 'FAIL'}   H3 {'PASS' if ok3 else 'FAIL'}   (passes go to ONE sealed run each)")
        open(log, "w").write("\n".join(OUT) + "\n")
    elif mode == "sealed":
        H = sys.argv[2]; main_log = open(log).read() if os.path.exists(log) else ""
        if f"{H} PASS" not in main_log.split("VERDICTS")[-1]: sys.exit(f"{H} did not pass main -- no sealed run")
        slog = os.path.join(FB, "data", f"run_gran1_sealed_{H}.log")
        if os.path.exists(slog): sys.exit("sealed run already done")
        P(f"gran1_run.py sealed {H}: 2023-07-01 -> 2026-09-30, pass = same sign and t >= 1.0")
        if H == "H3":
            b, t, n, sd, er, dm, _ = h3(lo=SEAL, hi=END); ok = b > 0 and t >= 1.0; P(f"  b {b:+.4f}  t {t:+.2f}  n {n}  -> {'CONFIRMED' if ok else 'NOT CONFIRMED'}")
        else:
            col = {"H1": "ins_ratio30", "H2": "ear_L28"}[H]; z = zseries(gran(), col); rows = r20_rows("spx500usd", z, SEAL, END); b, t, n = reg(rows)
            ok = t >= 1.0 if H == "H1" else abs(t) >= 1.0; P(f"  slope {b:+.1f} bp/sd  t {t:+.2f}  n {n}  -> {'CONFIRMED' if ok else 'NOT CONFIRMED'}  (sign must match main)")
        open(slog, "w").write("\n".join(OUT) + "\n")

if __name__ == "__main__":
    main()
