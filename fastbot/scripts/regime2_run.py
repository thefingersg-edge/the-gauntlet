#!/usr/bin/env python3
"""REGIME2 harness (PREREGISTRATION_REGIME2.md).  python3 regime2_run.py q1 | q2 | q3
ADX(14) trend strength: Q1 direction on trending days; Q2 regime-matched SESSION1 trades (daily ADX); Q3 15m-ADX structure.
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, json, glob, hashlib
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, HERE); os.chdir(HERE)
from regime1_run import pooled, two_t, cl_t, ERAS, STEMS
from session1_run import session_mask
from structure_v51 import data
PIN = {os.path.join(FB, "PREREGISTRATION_REGIME2.md"): "885697581f4e4ecb7091519e28b90de548e2d194ac7553816ab80213a8047842"}
T1 = 2.64; OUTD = os.path.join(FB, "data", "session1")
CONT = {"BOS", "marubozu", "three_soldiers", "wide_range", "gap_bar", "opening_range", "three_bar_pull", "inside_bar", "nr7"}
REV = {"CHOCH", "pin_bar", "hammer", "engulfing", "harami", "morning_star", "key_reversal", "reversal_bar", "two_bar_rev",
       "three_bar_rev", "doji", "outside_bar", "exhaustion"}


def pin():
    for f, h in PIN.items():
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} changed -- refused")


def adx(h, l, c, n=14):
    h, l, c = (pd.Series(np.asarray(x, float)) for x in (h, l, c))
    up, dn = h.diff(), -l.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    rma = lambda s: pd.Series(s).ewm(alpha=1 / n, adjust=False).mean()
    atr = rma(tr); pdi = 100 * rma(pdm) / atr; mdi = 100 * rma(mdm) / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi); a = rma(dx.fillna(0))
    a.iloc[:50] = np.nan
    return a.to_numpy(), np.where(pdi > mdi, 1, -1)


def self_test():
    rng = np.random.default_rng(1); n = 3000
    tr_ = np.cumsum(1 + rng.normal(0, 1, n)) + 1000; rw = np.cumsum(rng.normal(0, 1, n)) + 1000
    def hlc(x): return x + abs(rng.normal(0, .5, n)), x - abs(rng.normal(0, .5, n)), x
    at, _ = adx(*hlc(tr_)); ar, _ = adx(*hlc(rw))
    h, l, c = hlc(rw); a1, _ = adx(h, l, c); a2, _ = adx(h[:2000], l[:2000], c[:2000])
    ok = np.nanmedian(at) > 40 and 15 <= np.nanmedian(ar) <= 30 and np.allclose(a1[50:2000], a2[50:], equal_nan=True)
    print(f"  self-test: trend ADX median {np.nanmedian(at):.0f}, random walk {np.nanmedian(ar):.0f}, causal {np.allclose(a1[50:2000], a2[50:])} -> {'OK' if ok else 'BROKEN'}")
    if not ok: sys.exit("self-test broken -- no verdict")


def daily_bars(stem):
    d = data(stem); ins, last, day = session_mask(stem, d["t"])
    df = pd.DataFrame({"day": day[ins], "h": d["h"][ins], "l": d["l"][ins], "c": d["c"][ins]})
    g = df.groupby("day"); D = pd.DataFrame({"n": g.size(), "h": g["h"].max(), "l": g["l"].min(), "c": g["c"].last()})
    D = D[D["n"] >= 0.8 * D["n"].mode().iloc[0]]; D.index = pd.to_datetime(D.index)
    a, di = adx(D["h"], D["l"], D["c"]); D["adx"] = a; D["di"] = di
    D["sma"] = D["c"].rolling(200).mean()
    hi, lo = D["h"].rolling(20).max().shift(1), D["l"].rolling(20).min().shift(1)
    brk = pd.Series(np.where(D["c"] > hi, 1.0, np.where(D["c"] < lo, -1.0, np.nan)), index=D.index).ffill()
    D["D1"] = (D["di"] == 1).astype(float); D["D2"] = np.where(D["sma"].notna(), (D["c"] > D["sma"]).astype(float), np.nan)
    D["D3"] = np.where(brk.notna(), (brk == 1).astype(float), np.nan)
    return D


def q1():
    pin(); self_test(); S = {st: daily_bars(st) for st in STEMS}
    L = ["REGIME2 Q1 -- does direction work on TRENDING days (ADX >= 25)?  b = up-state minus down-state mean return, bp",
         "  I am not a financial adviser. This is a measurement, not a recommendation.", ""]
    for st in STEMS:
        D = S[st]; L.append(f"  {st}: {len(D):,} days; TREND {np.mean(D['adx'] >= 25):.0%}  RANGE {np.mean(D['adx'] < 20):.0%}  (of days with ADX)")
    names = {"D1": "+DI > -DI", "D2": "close > SMA200", "D3": "20-day breakout state"}; npass = 0
    for h in (1, 5):
        L.append(f"\n  horizon {h} day{'s (non-overlapping)' if h > 1 else ''}")
        for f in ("D1", "D2", "D3"):
            out = {}
            for reg, cond in (("TREND", lambda a: a >= 25), ("RANGE", lambda a: a < 20)):
                rows = []
                for ii, st in enumerate(STEMS):
                    D = S[st]; r = (D["c"].shift(-h) / D["c"] - 1) * 1e4
                    ok = (cond(D["adx"]) & D[f].notna() & r.notna() & D["adx"].notna()).to_numpy(); idx = np.flatnonzero(ok)
                    if h > 1: idx = idx[::h]
                    rows += [(ii, str(D.index[i])[:10], float(D[f].iloc[i]), float(r.iloc[i])) for i in idx]
                out[reg] = rows
            rows = out["TREND"]; b, t = pooled(rows)
            eb = [pooled([x for x in rows if a <= int(x[1][:4]) <= c])[0] for a, c in ERAS]
            ib = []
            for ii in range(4):
                u = [x[3] for x in rows if x[0] == ii and x[2] == 1]; d_ = [x[3] for x in rows if x[0] == ii and x[2] == 0]
                ib.append(np.mean(u) - np.mean(d_) if u and d_ else np.nan)
            ok = b > 0 and t >= T1 and all(e > 0 for e in eb) and sum(x > 0 for x in ib) >= 3; npass += ok
            br, tr_ = pooled(out["RANGE"]); rr = np.array([x[3] for x in rows]); rg = np.array([x[3] for x in out["RANGE"]])
            L.append(f"    {f} {names[f]:<22} TREND b {b:+7.2f} (t {t:+5.2f}, n {len(rows):,})  eras " + " ".join(f"{e:+.1f}" for e in eb)
                     + "  inst " + " ".join(f"{x:+.1f}" for x in ib) + f"  -> {'PASS' if ok else 'FAIL'}")
            L.append(f"         RANGE b {br:+7.2f} (t {tr_:+5.2f}, n {len(rg):,});  TREND-RANGE {b - br:+.2f};  vol TREND {rr.std():.0f} / RANGE {rg.std():.0f}   [reported]")
    L.append(f"\n  Q1 PASSES: {npass} of 6 (t >= {T1}, every era, >= 3 of 4 instruments)")
    open(os.path.join(FB, "data", "run_regime2_q1.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))


def look(D):
    idx = D.index.to_numpy(); A = D["adx"].to_numpy(); DI = D["di"].to_numpy()
    def g(days):
        p = np.searchsorted(idx, np.array(days, dtype="datetime64[ns]"), side="left") - 1
        a = np.where(p >= 0, A[np.clip(p, 0, None)], np.nan); di = np.where(p >= 0, DI[np.clip(p, 0, None)], 0); return a, di
    return g


def keep_masks(cls, a, di, side):
    side = np.asarray(side)
    if cls == "C": return (a >= 25) & (di == side), (a < 20)
    return (a < 20), (a >= 25)


def verdict_rows(L, fam, name, ra, da, rc, qa, qc):
    if len(ra) < 30: L.append(f"    {fam:<7}{name:<26}{len(ra):>7}   too few -> FAIL"); return False
    m, t = cl_t(ra, da); tr = two_t(ra, qa); yr = np.array([int(x[:4]) for x in da]); ra_ = np.array(ra)
    em = [ra_[(yr >= a) & (yr <= b)].mean() if ((yr >= a) & (yr <= b)).any() else float("nan") for a, b in ERAS]
    lift = (np.mean(ra) - np.mean(rc)) - (np.mean(qa) - np.mean(qc)) if len(rc) and len(qa) and len(qc) else float("nan")
    tb = 2.24 if fam.startswith("A") else 3.4
    ok = m > 0 and t >= tb and tr >= 2 and all(e > 0 for e in em) and len(ra) >= 200
    L.append(f"    {fam:<7}{name:<26}{len(ra):>7}{m:+9.2f}{t:+7.2f}{tr:+9.2f}{(np.mean(rc) if len(rc) else float('nan')):+9.2f}{lift:+8.2f}   "
             + " ".join(f"{e:+.1f}" for e in em) + f"   {'PASS' if ok else 'FAIL'}")
    return ok, lift


def q2():
    pin(); self_test(); LK = {st: look(daily_bars(st)) for st in STEMS}
    L = ["REGIME2 Q2 -- right setup in the right regime (daily ADX at previous close)",
         "  continuation: kept if ADX >= 25 AND trade side = DI direction;  reversal: kept if ADX < 20",
         "  'wrong' = continuation in RANGE / reversal in TREND;  lift = (right - wrong) pattern minus (right - wrong) random partners",
         "  I am not a financial adviser. This is a measurement, not a recommendation.", "",
         f"    {'family':<7}{'test':<26}{'n':>7}{'right':>9}{'t':>7}{'vs rnd t':>9}{'wrong':>9}{'lift':>8}   eras(right)        verdict"]
    G = {}
    for f_ in glob.glob(os.path.join(OUTD, "A_*.json")):
        R = json.load(open(f_)); st = R["stem"]
        for kind in ("BOS", "CHOCH"):
            rows = [x for x in R["A1"]["3"] if x[0] == kind]
            G.setdefault(("A 15m", f"S {kind} k=3", kind), []).append((st, np.array([x[5] for x in rows]), [x[2] for x in rows], [x[1] for x in rows],
                np.array(R["rand"][kind]["r"]), R["rand"][kind]["dy"], R["rand"][kind]["side"]))
    for f_ in glob.glob(os.path.join(OUTD, "B_*.json")):
        _, tf, a, b, *_ = os.path.basename(f_)[:-5].split("_"); st = (a + b).lower()
        for name, parts in json.load(open(f_)).items():
            base = name.split()[1]
            for x in parts:
                G.setdefault((f"B {tf}", name, base), []).append((st, np.array(x["r"]) * 1e4, x["dy"], x["side"], np.array(x["rand"]) * 1e4, x["rdy"], x["rside"]))
    npass = 0; lifts = {"C": [], "R": []}
    for (fam, name, base), parts in sorted(G.items()):
        cls = "C" if base in CONT else "R"; ra, da, rc, qa, qc = [], [], [], [], []
        for st, r, dy, sd, rr, rdy, rsd in parts:
            if len(r):
                a, di = LK[st](dy); k, w = keep_masks(cls, a, di, sd); ra += r[k].tolist(); da += list(np.asarray(dy)[k]); rc += r[w].tolist()
            if len(rr):
                a, di = LK[st](rdy); k, w = keep_masks(cls, a, di, rsd); qa += rr[k].tolist(); qc += rr[w].tolist()
        res = verdict_rows(L, fam, f"{name} [{cls}]", ra, da, rc, qa, qc)
        if res: npass += res[0]; lifts[cls].append(res[1])
    L.append(f"\n  Q2 PASSES: {npass} of {len(G)}")
    for c, nm in (("C", "continuation"), ("R", "reversal")):
        lf = np.array([x for x in lifts[c] if np.isfinite(x)])
        L.append(f"  regime lift, {nm}: median {np.median(lf):+.2f} bp, positive in {np.mean(lf > 0):.0%} of {len(lf)} tests   [reported]")
    open(os.path.join(FB, "data", "run_regime2_q2.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))


def q3():
    pin(); self_test()
    L = ["REGIME2 Q3 -- 15m structure with 15m ADX at the signal bar (BOS: ADX >= 25 and DI direction; CHoCH: ADX < 20)",
         "  I am not a financial adviser. This is a measurement, not a recommendation.", "",
         f"    {'family':<7}{'test':<26}{'n':>7}{'right':>9}{'t':>7}{'vs rnd t':>9}{'wrong':>9}{'lift':>8}   eras(right)        verdict"]
    acc = {"BOS": [[], [], [], [], []], "CHOCH": [[], [], [], [], []]}; NDRAW = 20; npass = 0
    for st in STEMS:
        R = json.load(open(os.path.join(OUTD, f"A_{st}.json"))); d = data(st); ins, last, day = session_mask(st, d["t"])
        a15, di15 = adx(d["h"], d["l"], d["c"]); A = np.flatnonzero(ins); rng = np.random.default_rng(0)
        for kind in ("BOS", "CHOCH"):   # regenerate SESSION1 random partners exactly (same rng sequence) to get their bars
            rows = [x for x in R["A1"]["3"] if x[0] == kind]; sides = np.array([x[1] for x in rows])
            pa = rng.choice(A, size=(len(sides), NDRAW)); pb = np.minimum(pa + 15, last[pa])
            g = (sides[:, None] * (d["c"][pb] / d["o"][pa] - 1) * 1e4 - d["spr"][pa]).ravel()
            if not np.allclose(g, R["rand"][kind]["r"]): sys.exit(f"random partners not reproduced for {st} {kind}")
            cls = "C" if kind == "BOS" else "R"
            ja = np.array([x[7] for x in rows]) - 1; k, w = keep_masks(cls, a15[ja], di15[ja], sides)
            net = np.array([x[5] for x in rows]); dy = np.array([x[2] for x in rows])
            pr = pa.ravel() - 1; ps = np.repeat(sides, NDRAW); kr, wr = keep_masks(cls, a15[pr], di15[pr], ps)
            A_ = acc[kind]; A_[0] += net[k].tolist(); A_[1] += dy[k].tolist(); A_[2] += net[w].tolist(); A_[3] += g[kr].tolist(); A_[4] += g[wr].tolist()
    L.insert(3, "  random partners reproduced exactly from SESSION1's seed: OK")
    for kind in ("BOS", "CHOCH"):
        res = verdict_rows(L, "A 15m", f"S {kind} k=3 (15m ADX)", *acc[kind]); npass += bool(res and res[0])
    L.append(f"\n  Q3 PASSES: {npass} of 2")
    open(os.path.join(FB, "data", "run_regime2_q3.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else ""
    {"q1": q1, "q2": q2, "q3": q3}.get(a, lambda: print(__doc__))()
