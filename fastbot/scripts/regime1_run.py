#!/usr/bin/env python3
"""REGIME1 harness (PREREGISTRATION_REGIME1.md).  python3 regime1_run.py q1 | q2
Q1: do moving-average / trend filters tell next-day or next-week direction?  Q2: do SESSION1 trades aligned with F1 beat aligned random?
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, json, glob, math, hashlib
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, HERE); os.chdir(HERE)
from daily_close import daily
from premarket_factor import regress, tstat
PIN = {os.path.join(FB, "PREREGISTRATION_REGIME1.md"): "b3a1b70b20e44ccc761132257c788c24ef6eb76e7fdf4ad281ec8dccb9d52c69"}
STEMS = ("spx500usd", "nas100usd", "uk100gbp", "xauusd"); ERAS = ((2005, 2012), (2013, 2019), (2020, 2026))
END = pd.Timestamp("2026-09-26"); T1 = 2.81


def pin():
    for f, h in PIN.items():
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} changed -- refused")


def states(stem):
    d = daily(stem); s = pd.Series({pd.Timestamp(k): v[0] for k, v in d.items()}).sort_index(); s = s[s.index < END]
    sma50, sma200 = s.rolling(50).mean(), s.rolling(200).mean()
    e20, e50 = s.ewm(span=20, adjust=False).mean(), s.ewm(span=50, adjust=False).mean()
    F = pd.DataFrame({"F1": np.where(sma200.notna(), s > sma200, np.nan),
                      "F2": np.where(sma200.notna(), sma50 > sma200, np.nan),
                      "F3": np.where(s.index >= s.index[49], e20 > e50, np.nan),     # EMA50 needs 50 days of warm-up
                      "F4": np.where(s.shift(252).notna(), s > s.shift(252), np.nan),
                      "F5": np.where(sma200.shift(20).notna(), sma200 > sma200.shift(20), np.nan)}, index=s.index)
    return s, F


NAMES = {"F1": "close > SMA200", "F2": "SMA50 > SMA200 (golden cross)", "F3": "EMA20 > EMA50", "F4": "12-month return > 0", "F5": "SMA200 rising (20d)"}


def pooled(rows):
    """rows: list of (inst_idx, date, up, r_bp). Returns b, t."""
    if len(rows) < 30: return float("nan"), float("nan")
    ii = np.array([r[0] for r in rows]); X = np.zeros((len(rows), 5)); X[np.arange(len(rows)), ii] = 1; X[:, 4] = [r[2] for r in rows]
    keep = X[:, :4].sum(0) > 0; X = np.c_[X[:, :4][:, keep], X[:, 4]]
    b, V = regress(np.array([r[3] for r in rows]), X, [r[1] for r in rows]); return b[-1], tstat(b, V, len(b) - 1)


def q1():
    pin(); L = ["REGIME1 Q1 -- does the filter tell direction?  (b = mean return in up state minus down state, bp; pooled 4 instruments, date-clustered)",
                "  I am not a financial adviser. This is a measurement, not a recommendation.", ""]
    S = {st: states(st) for st in STEMS}
    # self-test: a perfect-foresight filter must pass, a coin-flip must not
    st0, (s0, _) = "spx500usd", S["spx500usd"]; r0 = (s0.shift(-1) / s0 - 1).dropna() * 1e4
    rows = [(0, str(d)[:10], float(r0[d] > 0), r0[d]) for d in r0.index]; bp, tp = pooled(rows)
    rng = np.random.default_rng(0); rows = [(0, str(d)[:10], float(rng.random() < .5), r0[d]) for d in r0.index]; bc, tc = pooled(rows)
    L.append(f"  self-test: perfect foresight b {bp:+.1f} t {tp:+.1f};  coin flip b {bc:+.2f} t {tc:+.2f}  -> {'OK' if tp > 10 and abs(tc) < 3 else 'BROKEN'}\n")
    npass = 0
    for h in (1, 5):
        L.append(f"  horizon {h} day{'s' if h > 1 else ''}" + (" (non-overlapping)" if h > 1 else ""))
        for f in ("F1", "F2", "F3", "F4", "F5"):
            rows, per = [], {}
            for ii, st in enumerate(STEMS):
                s, F = S[st]; r = (s.shift(-h) / s - 1) * 1e4; ok = F[f].notna() & r.notna()
                idx = np.flatnonzero(ok.to_numpy())
                if h > 1: idx = idx[::h]
                for i in idx:
                    rows.append((ii, str(s.index[i])[:10], float(F[f].iloc[i]), float(r.iloc[i])))
            up = np.array([x[2] for x in rows]) == 1; rr = np.array([x[3] for x in rows])
            b, t = pooled(rows)
            eb = [pooled([x for x in rows if a <= int(x[1][:4]) <= c])[0] for a, c in ERAS]
            ib = [np.mean([x[3] for x in rows if x[0] == ii and x[2] == 1]) - np.mean([x[3] for x in rows if x[0] == ii and x[2] == 0]) for ii in range(4)]
            ok = b > 0 and t >= T1 and all(e > 0 for e in eb) and sum(x > 0 for x in ib) >= 3; npass += ok
            hit = np.mean(np.where(up, rr > 0, rr < 0)); hit_long = np.mean(rr > 0)
            L.append(f"    {f} {NAMES[f]:<31} b {b:+6.2f} (t {t:+5.2f})  eras " + " ".join(f"{e:+.1f}" for e in eb)
                     + "  inst " + " ".join(f"{x:+.1f}" for x in ib) + f"  -> {'PASS' if ok else 'FAIL'}")
            L.append(f"         up {up.mean():.0%} of days; mean up {rr[up].mean():+.2f} / down {rr[~up].mean():+.2f}; vol up {rr[up].std():.0f} / down {rr[~up].std():.0f};"
                     f" hit {hit:.1%} vs always-long {hit_long:.1%}")
        L.append("")
    L.append(f"  Q1 PASSES: {npass} of 10 (t >= {T1}, every era, >= 3 of 4 instruments)")
    open(os.path.join(FB, "data", "run_regime1_q1.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))


def lookup(F, f):
    idx = F.index.to_numpy(); val = F[f].to_numpy()
    def g(day):
        p = np.searchsorted(idx, np.datetime64(day, "ns"), side="left") - 1
        return np.nan if p < 0 else val[p]
    return g


def two_t(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or len(b) < 2: return float("nan")
    return (a.mean() - b.mean()) / math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def cl_t(r, days):
    r = np.asarray(r, float)
    if len(r) < 2: return float("nan"), float("nan")
    df = pd.DataFrame({"r": r, "d": days}); m = r.mean()
    u = df.assign(u=df["r"] - m).groupby("d")["u"].sum(); se = math.sqrt((u ** 2).sum()) / len(r)
    return m, (m / se if se > 0 else float("nan"))


def q2():
    pin(); OUTD = os.path.join(FB, "data", "session1")
    S = {st: states(st)[1] for st in STEMS}
    LK = {(st, f): lookup(S[st], f) for st in STEMS for f in ("F1", "F2")}
    def align(st, f, days, sides):
        g = LK[(st, f)]; s = np.array([g(d) for d in days], float); sd = np.asarray(sides)
        a = np.where(np.isnan(s), np.nan, np.where(s == 1, sd > 0, sd < 0).astype(float)); return a
    L = ["REGIME1 Q2 -- SESSION1 trades taken WITH the trend filter (F1 close > SMA200 primary; F2 golden cross reported)",
         "  I am not a financial adviser. This is a measurement, not a recommendation.", "",
         "  lift = (aligned - counter) for the pattern  minus  (aligned - counter) for its random partners: the part of any gain owed to the pattern", ""]
    tests = []   # (family, name, stem-list rows)
    for f_ in glob.glob(os.path.join(OUTD, "A_*.json")):
        R = json.load(open(f_)); st = R["stem"]
        for kind in ("BOS", "CHOCH"):
            rows = [x for x in R["A1"]["3"] if x[0] == kind]
            tests.append(("A 15m", f"S {kind} k=3", st, [x[5] for x in rows], [x[2] for x in rows], [x[1] for x in rows],
                          R["rand"][kind]["r"], R["rand"][kind]["dy"], R["rand"][kind]["side"], 1.0))
    for f_ in glob.glob(os.path.join(OUTD, "B_*.json")):
        _, tf, a, b, *_ = os.path.basename(f_)[:-5].split("_"); st = (a + b).lower()
        for name, parts in json.load(open(f_)).items():
            for x in parts:
                tests.append((f"B {tf}", name, st, x["r"], x["dy"], x["side"], x["rand"], x["rdy"], x["rside"], 1e4))
    G = {}
    for fam, name, st, r, dy, sd, rr, rdy, rsd, sc in tests:
        k = (fam, name); G.setdefault(k, []).append((st, np.asarray(r) * sc, dy, sd, np.asarray(rr) * sc, rdy, rsd))
    npass = ntest = 0; lifts = []
    for f in ("F1", "F2"):
        L.append(f"  ===== {f} {'(primary, gated)' if f == 'F1' else '(reported only)'} =====")
        L.append(f"    {'family':<7}{'test':<26}{'n al':>7}{'aligned':>9}{'t':>7}{'vs rnd t':>9}{'counter':>9}{'lift':>8}   eras(aligned)       verdict")
        for (fam, name), parts in sorted(G.items()):
            ra, da, rc, ya = [], [], [], []; qa, qc = [], []
            for st, r, dy, sd, rr, rdy, rsd in parts:
                if len(r):
                    al = align(st, f, dy, sd); m = al == 1; c = al == 0
                    ra += r[m].tolist(); da += list(np.asarray(dy)[m]); rc += r[c].tolist()
                if len(rr):
                    al2 = align(st, f, rdy, rsd); qa += rr[al2 == 1].tolist(); qc += rr[al2 == 0].tolist()
            if f == "F1": ntest += 1
            if len(ra) < 30:
                L.append(f"    {fam:<7}{name:<26}{len(ra):>7}   too few -> FAIL"); continue
            m, t = cl_t(ra, da); tr = two_t(ra, qa); yr = np.array([int(x[:4]) for x in da]); ra_ = np.array(ra)
            em = [ra_[(yr >= a) & (yr <= b)].mean() if ((yr >= a) & (yr <= b)).any() else float("nan") for a, b in ERAS]
            lift = (np.mean(ra) - (np.mean(rc) if rc else np.nan)) - (np.mean(qa) - np.mean(qc)) if qa and qc else float("nan")
            tb = 2.24 if fam.startswith("A") else 3.4
            ok = m > 0 and t >= tb and tr >= 2 and all(e > 0 for e in em) and len(ra) >= 200
            if f == "F1": npass += ok; lifts.append(lift)
            L.append(f"    {fam:<7}{name:<26}{len(ra):>7}{m:+9.2f}{t:+7.2f}{tr:+9.2f}{(np.mean(rc) if rc else float('nan')):+9.2f}{lift:+8.2f}   "
                     + " ".join(f"{e:+.1f}" for e in em) + f"   {('PASS' if ok else 'FAIL') if f == 'F1' else '-'}")
        L.append("")
    lf = np.array([x for x in lifts if np.isfinite(x)])
    L.append(f"  Q2 PASSES (F1): {npass} of {ntest}")
    L.append(f"  F1 lift across tests: median {np.median(lf):+.2f} bp, positive in {np.mean(lf > 0):.0%} of {len(lf)} tests   [reported]")
    open(os.path.join(FB, "data", "run_regime1_q2.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else ""
    {"q1": q1, "q2": q2}.get(a, lambda: print(__doc__))()
