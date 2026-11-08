#!/usr/bin/env python3
"""BREADTH2 harness (PREREGISTRATION_BREADTH2). One run.  SS_STORE=~/store python3 breadth2_run.py
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, hashlib, csv, io, subprocess, datetime as dt, numpy as np
import ss_lib, ss_events2 as S
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); SC = os.path.join(FB, "scripts"); sys.path.insert(0, SC)
DOC = (os.path.join(FB, "PREREGISTRATION_BREADTH2.md"), "6d3f68969ef1f685e570144c42b6c83a19da2959b1d5d87d1f0bfa1c987597da")
H = 20; D0 = dt.date(1970, 1, 1)
def day(s): return (dt.date.fromisoformat(s) - D0).days
def todate(i): return D0 + dt.timedelta(int(i))

def membership_rows():
    raw = subprocess.run(["unzip", "-p", ss_lib.find("sp500")], capture_output=True, text=True).stdout
    return list(csv.DictReader(io.StringIO(raw)))

def build():
    rows = membership_rows(); snaps, evs = {}, []
    for r in rows:
        if r["action"] == "historical": snaps.setdefault(day(r["date"]), set()).add(r["ticker"])
        elif r["action"] in ("added", "removed"): evs.append((day(r["date"]), r["action"], r["ticker"]))
    first = min(snaps); evs = sorted(e for e in evs if e[0] > first)
    tick = sorted(set().union(*snaps.values()) | {e[2] for e in evs})
    have = [t for t in tick if os.path.exists(os.path.join(S.STORE, t.replace("/", "_") + ".npz"))]
    # trading days: union of member price dates from the first snapshot
    Z = {}; days = set()
    for t in have:
        z = ss_lib.load(S.STORE, t.replace("/", "_") + ".npz"); Z[t] = z; days.update(int(x) for x in z["d"] if x >= first - 90)
    T = np.array(sorted(days)); idx = {d: i for i, d in enumerate(T)}; N = len(have); col = {t: j for j, t in enumerate(have)}
    CA = np.full((len(T), N), np.nan); OA = np.full((len(T), N), np.nan)
    for t, z in Z.items():
        j = col[t]; d = z["d"]; m = d >= first - 90; ii = [idx[int(x)] for x in d[m]]
        CA[ii, j] = z["ca"][m]; adj = np.where(z["c"][m] > 0, z["ca"][m] / z["c"][m], np.nan); OA[ii, j] = z["o"][m] * adj
    # 50-day SMA on each column's own valid closes
    ABOVE = np.full(CA.shape, np.nan)
    for j in range(N):
        v = np.where(np.isfinite(CA[:, j]))[0]
        if len(v) < 51: continue
        x = CA[v, j]; cs = np.cumsum(np.r_[0, x]); sma = (cs[50:] - cs[:-50]) / 50          # sma[k] = mean x[k..k+49]
        ABOVE[v[49:], j] = (x[49:] > sma).astype(float)
    # point-in-time membership
    items = sorted([(d, 0, "e", a, t) for d, a, t in evs] + [(d, 1, "s", None, s) for d, s in snaps.items()], key=lambda q: (q[0], q[1]))
    cur = set(); k = 0; B, R, COV, DT = [], [], [], []
    for i, d in enumerate(T):
        while k < len(items) and items[k][0] <= d:
            it = items[k]
            if it[2] == "s": cur = set(snaps[it[0]])
            elif it[3] == "added": cur.add(it[4])
            else: cur.discard(it[4])
            k += 1
        if d < first or not cur or i + H >= len(T): continue
        js = [col[t] for t in cur if t in col]; cov = len(js) / len(cur)
        a = ABOVE[i, js]; ok = np.isfinite(a)
        if cov < 0.90 or ok.mean() < 0.90: continue
        o1 = OA[i + 1, js]; ce = CA[i + H, js]
        last = np.array([CA[i + 1:i + H + 1, j][np.isfinite(CA[i + 1:i + H + 1, j])][-1] if np.isfinite(CA[i + 1:i + H + 1, j]).any() else np.nan for j in js])
        ce = np.where(np.isfinite(ce), ce, last); r = ce / o1 - 1; r = r[np.isfinite(r)]
        o5 = CA[min(i + 5, len(T) - 1), js] / o1 - 1
        B.append(100 * a[ok].mean()); R.append(1e4 * r.mean()); COV.append(cov); DT.append(int(d))
        R5.append(1e4 * np.nanmean(o5))
    return np.array(DT), np.array(B), np.array(R), np.array(COV), np.array(R5)

R5 = []
def main():
    if hashlib.sha256(open(DOC[0], "rb").read()).hexdigest() != DOC[1]: sys.exit("doc changed")
    log = os.path.join(FB, "data", "run_breadth2.log")
    if os.path.exists(log): sys.exit("already run")
    from breadth_v56 import nw_ols
    OUT = []; P = lambda s="": (print(s, flush=True), OUT.append(s))
    P("breadth2_run.py  PREREGISTRATION_BREADTH2 pinned\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    DT, Bt, Rt, COV, R5a = build(); dts = [todate(x) for x in DT]
    np.savez(os.path.join(FB, "data", "breadth2_series.npz"), d=DT, b=Bt, r=Rt, cov=COV, r5=R5a)
    P(f"  days {len(DT)} ({dts[0]} .. {dts[-1]}), median member coverage {100*np.median(COV):.1f}%")
    def reg(m, lag=H, y=Rt):
        b, t = nw_ols(y[m], Bt[m] / 10, lag); return b[1], t[1], int(m.sum())
    yr = np.array([d.year for d in dts]); dd = np.array(dts)
    m1 = (dd >= dt.date(1998, 5, 1)) & (dd <= dt.date(2006, 12, 29)); m2 = (dd >= dt.date(2007, 1, 2)) & (dd <= dt.date(2026, 8, 31))
    b1, t1, n1 = reg(m1); b2, t2, n2 = reg(m2)
    allm = dd <= dt.date(2026, 8, 31); low = (Bt < 20).astype(float)
    bl, tl = nw_ols(Rt[allm], low[allm], H)
    g1s = b1 < 0; g1c = g1s and t1 <= -1.645; g2 = b2 < 0 and t2 <= -2.0; g3 = bl[1] > 0 and tl[1] >= 2.0
    P(f"  G1 1998-05..2006-12  slope {b1:+.2f} bp per 10pp (NW t {t1:+.2f}, n {n1})  sign {'neg' if g1s else 'POS'}; {'confirmed out of sample' if g1c else 'not confirmed (t > -1.645)'}")
    P(f"  G2 2007..2026-08     slope {b2:+.2f} bp per 10pp (NW t {t2:+.2f}, n {n2})  -> {'PASS' if g2 else 'FAIL'}")
    P(f"  G3 B<20 minus rest   {bl[1]:+.1f} bp (NW t {tl[1]:+.2f}; low days {int(low[allm].sum())})  -> {'PASS' if g3 else 'FAIL'}")
    v = g2 and g3 and g1s
    P("\n  reported:")
    for lo, hi in ((1998, 2006), (2007, 2012), (2013, 2019), (2020, 2026)):
        m = allm & (yr >= lo) & (yr <= hi); b, t, n = reg(m); P(f"    era {lo}-{hi}: slope {b:+.2f} (t {t:+.2f}, n {n})")
    b5, t5, n5 = reg(allm, 5, R5a); P(f"    h=5 whole period: slope {b5:+.2f} (t {t5:+.2f})")
    try:
        import tv_series as TV
        s5 = dict(TV.read("S5FI", os.path.join(SC, "../data/tv_20261001"))); pair = [(Bt[i], s5[dts[i]]) for i in range(len(dts)) if dts[i] in s5]
        P(f"    corr with TradingView S5FI: {np.corrcoef(*zip(*pair))[0,1]:.3f} (n {len(pair)}); mean PIT {np.mean([p[0] for p in pair]):.1f} vs TV {np.mean([p[1] for p in pair]):.1f}")
        from breadth_v56 import sessions, fwd
        F = fwd(sessions(os.path.join(SC, "../data/v24")), H); ii = [i for i in range(len(dts)) if dts[i] in F and dts[i] >= dt.date(2007, 1, 2)]
        b, t = nw_ols(np.array([F[dts[i]][0] for i in ii]), Bt[ii] / 10, H); P(f"    OANDA SPX500 target 2007+: slope {b[1]:+.2f} (t {t[1]:+.2f}, n {len(ii)})")
    except Exception as ex: P(f"    TV/OANDA cross-checks failed: {type(ex).__name__}: {ex}")
    P(f"\n  VERDICT BREADTH2 G1 sign {'neg' if g1s else 'pos'}{' (confirmed)' if g1c else ''}  G2 {'P' if g2 else 'F'}  G3 {'P' if g3 else 'F'} -> {'PASS' if v else 'FAIL'}")
    open(log, "w").write("\n".join(OUT) + "\n")
if __name__ == "__main__": main()
