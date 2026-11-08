#!/usr/bin/env python3
"""SESSION1 harness (PREREGISTRATION_SESSION1.md). Cash-session-only re-run of v51 (Part A) and TF1 30m/1h (Part B).
Chunked by design (VM 175 s limit):
    python3 session1_run.py A <stem>                  stems: spx500usd nas100usd uk100gbp xauusd
    python3 session1_run.py B <30m|1h> <INST> <P|S> [iofN]
    python3 session1_run.py verdict
Trade-level output (with random partners) goes to data/session1/ for REGIME1.
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, json, math, glob, hashlib
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
os.chdir(HERE)
PIN = {os.path.join(FB, "PREREGISTRATION_SESSION1.md"): "11bb4e0a1ea101d9c840f4b8bd3e9a802ca6761592664fa41a44efb8619d416a"}
OUTD = os.path.join(FB, "data", "session1")
ERAS = ((2005, 2012), (2013, 2019), (2020, 2026))
SES = {"spx500usd": ("America/New_York", 570, 960), "nas100usd": ("America/New_York", 570, 960),
       "uk100gbp": ("Europe/London", 480, 990), "xauusd": ("America/New_York", 510, 810)}
KS = (2, 3, 4, 5); TA = 2.24; TB = 3.4; NDRAW = 20


def pin():
    for f, h in PIN.items():
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} changed -- refused")


def cl_t(r, days):
    r = np.asarray(r, float)
    if len(r) < 2: return float("nan"), float("nan")
    df = pd.DataFrame({"r": r, "d": days}); m = r.mean()
    u = df.assign(u=df["r"] - m).groupby("d")["u"].sum(); se = math.sqrt((u ** 2).sum()) / len(r)
    return m, (m / se if se > 0 else float("nan"))


def two_t(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or len(b) < 2: return float("nan")
    return (a.mean() - b.mean()) / math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


# ---------------------------------------------------------------- Part A
def session_mask(stem, t):
    tz, op, clo = SES[stem]
    L = pd.DatetimeIndex(t.astype("datetime64[ns]")).tz_localize("UTC").tz_convert(tz)
    mins = L.hour.to_numpy() * 60 + L.minute.to_numpy()
    ins = (mins >= op) & (mins + 15 <= clo) & (L.weekday.to_numpy() < 5)
    day = L.strftime("%Y-%m-%d").to_numpy()
    last = np.full(len(t), -1)
    idx = np.flatnonzero(ins)
    if len(idx):
        dd = day[idx]; brk = np.r_[np.flatnonzero(dd[1:] != dd[:-1]), len(idx) - 1]
        start = 0
        for e in brk:
            last[idx[start:e + 1]] = idx[e]; start = e + 1
    return ins, last, day


def runA(stem):
    from structure_v51 import data
    from struct15 import structure_events
    out = os.path.join(OUTD, f"A_{stem}.json")
    if os.path.exists(out): sys.exit(f"A {stem} already run")
    d = data(stem); n = len(d["c"]); o, c, spr = d["o"], d["c"], d["spr"]
    ins, last, day = session_mask(stem, d["t"]); yr = np.array([int(x[:4]) for x in day])
    # self-test: SPX/NAS normal day = 26 bars, gold 20, UK 34
    cnt = pd.Series(day[ins]).value_counts(); mode = int(cnt.mode().iloc[0])
    want = {"spx500usd": 26, "nas100usd": 26, "uk100gbp": 34, "xauusd": 20}[stem]
    if mode != want: sys.exit(f"self-test: modal session bars {mode} != {want}")
    # in-session drift by year (every in-session bar as entry, same exit rule)
    A = np.flatnonzero(ins); B = np.minimum(A + 15, last[A])
    dr = (c[B] / o[A] - 1) * 1e4; mu = {int(y): float(dr[yr[A] == y].mean()) for y in np.unique(yr[A])}
    rng = np.random.default_rng(0); res = {"stem": stem, "A1": {}, "A2": {}, "rand": {}}
    for k in KS:
        rows = []
        for j, kind, s in structure_events(d["h"], d["l"], c, k):
            a = j + 1
            if a >= n or not ins[a]: continue
            b = min(j + 16, last[a]); g = s * (c[b] / o[a] - 1) * 1e4
            rows.append((kind, int(s), day[a], int(yr[a]), g, g - spr[a], g - s * mu.get(int(yr[a]), 0.0), int(a), int(b)))
        assert all(ins[r[7]] and ins[r[8]] and day[r[7]] == day[r[8]] for r in rows), "trade outside session"
        res["A1"][k] = rows
        if k == 3:  # G5 random partners: same direction, random in-session entry, same exit rule
            for kind in ("BOS", "CHOCH"):
                sides = np.array([r[1] for r in rows if r[0] == kind])
                if not len(sides): continue
                pa = rng.choice(A, size=(len(sides), NDRAW)); pb = np.minimum(pa + 15, last[pa])
                g = sides[:, None] * (c[pb] / o[pa] - 1) * 1e4 - spr[pa]
                res["rand"][kind] = dict(r=g.ravel().tolist(), dy=day[pa].ravel().tolist(),
                                         side=np.repeat(sides, NDRAW).tolist())
    # A2 (reported): events on the in-session-only series
    sub = np.flatnonzero(ins)
    for j, kind, s in structure_events(d["h"][sub], d["l"][sub], c[sub], 3):
        if j + 1 >= len(sub): continue
        a = sub[j + 1]; b = min(sub[min(j + 16, len(sub) - 1)], last[a])
        g = s * (c[b] / o[a] - 1) * 1e4 - spr[a]
        res["A2"].setdefault(kind, []).append((day[a], g))
    os.makedirs(OUTD, exist_ok=True); json.dump(res, open(out, "w"))
    print(f"  A {stem}: {n:,} bars, {ins.sum():,} in session; k=3 trades {len(res['A1'][3]):,}  wrote {out}")


# ---------------------------------------------------------------- Part B
HOLD = {"30m": 6, "1h": 3}


def runB(tf, inst, part, grp=None):
    import tf1_run as T, engine as E, patterns as PT
    from struct15 import structure_events
    E.H_HOLD = HOLD[tf]
    tag = "_".join(x for x in ("B", tf, inst, part, grp) if x)
    out = os.path.join(OUTD, f"{tag}.json")
    if os.path.exists(out): sys.exit(f"{tag} already run")
    D = T.load(inst, tf); n = len(D["C"]); H = HOLD[tf]
    ins = (D["hour"] >= E.SESSION[0]) & (D["hour"] < E.SESSION[1])
    runner = lambda m, s: PT.trades(D, m, s)
    res = {}
    if part == "P":
        P, _ = PT.detect(D); names = sorted(P)
        if grp:
            gi, gn = map(int, grp.split("of")); names = [nm for i_, nm in enumerate(names) if i_ * gn // len(names) == gi]
        for name in names:
            bull, bear = P[name]
            for side, mask in ((1, bull), (-1, bear)):
                tr = runner(mask, side)
                assert all(ins[j] and ins[k] and D["day"][j] == D["day"][k] for j, k, _, _ in tr)
                r, yr, dy = T.pat_pnl(D, tr, "1m")     # "1m" path = no financing (flat by the close)
                rr, rd, rs = [], [], []
                if mask.any():
                    for s_ in range(NDRAW):
                        a_, _, d_ = T.pat_pnl(D, T.matched_random(D, mask, side, tf, 1000 + s_, runner), "1m")
                        rr += a_.tolist(); rd += d_.tolist(); rs += [side] * len(a_)
                res[f"P {name} {'long' if side > 0 else 'short'}"] = [dict(r=r.tolist(), yr=yr.tolist(), dy=dy.tolist(),
                    side=[side] * len(r), rand=rr, rdy=rd, rside=rs)]
    else:
        def ok(a, b): return b < n and ins[a] and ins[b] and D["day"][a] == D["day"][b]
        for kind in ("BOS", "CHOCH"):
            rows = []
            for k_ in KS:
                for j, kd, s in structure_events(D["H"], D["L"], D["C"], k_):
                    a, b = j + 1, j + H
                    if kd != kind or not ok(a, b): continue
                    g = s * (D["C"][b] / D["O"][a] - 1) - D["spread"][a]
                    rows.append((k_, g, int(D["year"][a]), str(D["day"][a])[:10], int(s), a))
            rr, rd, rs = [], [], []
            for s_ in (1, -1):
                cm = np.zeros(n, bool)
                for x in rows:
                    if x[4] == s_ and x[5] - 1 >= 0: cm[x[5] - 1] = True
                if not cm.any(): continue
                for sd in range(NDRAW):
                    m = T.matched_random(D, cm, s_, tf, 5000 + sd, lambda mm, ss: np.flatnonzero(mm))
                    for i in m:
                        a, b = i + 1, i + H
                        if not ok(a, b): continue
                        rr.append(s_ * (D["C"][b] / D["O"][a] - 1) - D["spread"][a]); rd.append(str(D["day"][a])[:10]); rs.append(s_)
            res[f"S {kind}"] = [dict(r=[x[1] for x in rows], k=[x[0] for x in rows], yr=[x[2] for x in rows], dy=[x[3] for x in rows],
                                     side=[x[4] for x in rows], rand=rr, rdy=rd, rside=rs)]
    os.makedirs(OUTD, exist_ok=True); json.dump(res, open(out, "w")); print(f"  {tag}: {n:,} bars  wrote {out}")


# ---------------------------------------------------------------- verdict
def tf1_24h(tf):
    res = {}
    for f in glob.glob(os.path.join(FB, "data", "tf1", f"tf1_{tf}*.json")):
        b = os.path.basename(f)
        if not (b == f"tf1_{tf}.json" or b.startswith(f"tf1_{tf}_")): continue
        for k, v in json.load(open(f)).items(): res.setdefault(k, []).extend(np.array(x["r"]) for x in v)
    return {k: np.concatenate(v).mean() * 1e4 for k, v in res.items() if sum(len(x) for x in v)}


def verdict():
    pin(); L = ["SESSION1 verdict (PREREGISTRATION_SESSION1.md sha 11bb4e0a…)",
                "  I am not a financial adviser. This is a measurement, not a recommendation.", ""]
    # Part A
    F = sorted(glob.glob(os.path.join(OUTD, "A_*.json")))
    if len(F) < 4: L.append(f"  Part A: only {len(F)} of 4 instruments run")
    else:
        R = [json.load(open(f)) for f in F]; L.append("  PART A  v51 BOS/CHoCH, 15m, cash session only (bp; net = after one spread)")
        anyA = False
        for S in ("CHOCH", "BOS"):
            g1 = g2 = True
            for k in KS:
                rows = [x for Rr in R for x in Rr["A1"][str(k)] if x[0] == S]
                dy = [x[2] for x in rows]; mn, tn = cl_t([x[5] for x in rows], dy); mg, tg = cl_t([x[4] for x in rows], dy)
                me, te = cl_t([x[6] for x in rows], dy); g1 &= (mn > 0 and tn >= TA); g2 &= me > 0
                L.append(f"    {S:<5} k={k}: n {len(rows):6,}  gross {mg:+6.2f} (t {tg:+5.2f})  net {mn:+6.2f} (t {tn:+6.2f})  excess {me:+6.2f}")
            r3 = [x for Rr in R for x in Rr["A1"]["3"] if x[0] == S]
            er = [cl_t([x[5] for x in r3 if a <= x[3] <= b], [x[2] for x in r3 if a <= x[3] <= b]) for a, b in ERAS]
            g3 = all(e[0] > 0 for e in er)
            ins_ = [(Rr["stem"], cl_t([x[5] for x in Rr["A1"]["3"] if x[0] == S], [x[2] for x in Rr["A1"]["3"] if x[0] == S])) for Rr in R]
            g4 = sum(e[1][0] > 0 for e in ins_) >= 3
            rnd = np.concatenate([np.array(Rr["rand"][S]["r"]) for Rr in R if S in Rr["rand"]])
            net3 = [x[5] for x in r3]; t5 = two_t(net3, rnd); g5 = np.mean(net3) > rnd.mean() and t5 >= 2
            L.append("      eras k=3 net: " + "  ".join(f"{a}-{b % 100:02d} {e[0]:+.2f} (t {e[1]:+.2f})" for (a, b), e in zip(ERAS, er)))
            L.append("      instruments k=3 net: " + "  ".join(f"{s[:6]} {e[0]:+.2f}" for s, e in ins_))
            L.append(f"      random in-session entries (same side): net {rnd.mean():+.2f};  structure minus random {np.mean(net3) - rnd.mean():+.2f} (t {t5:+.2f})")
            a2 = [x for Rr in R for x in Rr["A2"].get(S, [])]; m2, t2 = cl_t([x[1] for x in a2], [x[0] for x in a2])
            L.append(f"      A2 (events on session-only bars), k=3 net {m2:+.2f} (t {t2:+.2f}, n {len(a2):,})   [reported]")
            v = all((g1, g2, g3, g4, g5)); anyA |= v
            L.append(f"    {S}: G1 {'PASS' if g1 else 'FAIL'}  G2 {'PASS' if g2 else 'FAIL'}  G3 {'PASS' if g3 else 'FAIL'}  G4 {'PASS' if g4 else 'FAIL'}  G5 {'PASS' if g5 else 'FAIL'}  -> {'PASS' if v else 'FAIL'}")
        L.append("    24-hour v51 for comparison (k=3 net): CHoCH -2.75 (t -12.6)   BOS -2.62 (t -8.6)\n")
    # Part B
    npass = 0; ntest = 0
    for tf in ("30m", "1h"):
        res = {}
        for f in glob.glob(os.path.join(OUTD, f"B_{tf}_*.json")):
            for k, v in json.load(open(f)).items(): res.setdefault(k, []).extend(v)
        if not res: L.append(f"  PART B {tf}: NOT RUN"); continue
        old = tf1_24h(tf)
        L.append(f"  PART B  TF1 {tf}, cash session 09-16 NY, 3h hold (bp)\n    {'test':<26}{'n':>7}{'mean':>8}{'t':>7}{'vs rnd t':>9}   eras            verdict   24h mean")
        for name, parts in sorted(res.items()):
            r = np.concatenate([np.array(x["r"]) for x in parts]); yr = np.concatenate([np.array(x["yr"]) for x in parts])
            dy = np.concatenate([np.array(x["dy"]) for x in parts]); rand = np.concatenate([np.array(x["rand"]) for x in parts]); ntest += 1
            if len(r) < 2: L.append(f"    {name:<26}{len(r):>7}  -> FAIL (too few)"); continue
            m, t = cl_t(r, dy); tr = two_t(r, rand)
            em = [r[(yr >= a) & (yr <= b)].mean() if ((yr >= a) & (yr <= b)).any() else float("nan") for a, b in ERAS]
            kok = True
            if name.startswith("S "):
                k = np.concatenate([np.array(x["k"]) for x in parts]); kok = all(np.sign(r[k == kk].mean()) == np.sign(m) for kk in KS if (k == kk).any())
            ok = m > 0 and t >= TB and tr >= 2.0 and all(e > 0 for e in em) and len(r) >= 200 and kok; npass += ok
            L.append(f"    {name:<26}{len(r):>7}{m*1e4:+8.2f}{t:+7.2f}{tr:+9.2f}   " + " ".join(f"{e*1e4:+.1f}" for e in em)
                     + f"   {'PASS' if ok else 'FAIL'}   {old.get(name, float('nan')):+.2f}")
    L.append(f"\n  PART B PASSES: {npass} of {ntest} (t >= {TB}, beat random t >= 2, every era > 0, n >= 200)")
    open(os.path.join(FB, "data", "run_session1_verdict.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    pin(); a = sys.argv[1:] or [""]
    if a[0] == "A": runA(a[1])
    elif a[0] == "B": runB(a[1], a[2], a[3], a[4] if len(a) > 4 else None)
    elif a[0] == "verdict": verdict()
    else: print(__doc__)
