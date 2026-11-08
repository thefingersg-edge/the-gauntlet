#!/usr/bin/env python3
"""PREREGISTRATION_v37 -- can the event timeline predict the trades we would
have wanted? (Dave's hindsight-label idea.)

STAGE FIT  (never reads a row dated 2020-01-01 or later)
  * LightGBM per side (LONG wanted / SHORT wanted), fitted on 2005-2012,
    rounds chosen on 2013-2014, scored on 2015-2019 (validation).
  * Permutation null: the same procedure 20x with training labels shifted
    by a random whole number of days. G1 = real validation AUC above all 20.
  * Readable patterns: single events and ordered pairs "A then B" within
    60 min / 1 day / 5 days, mined on 2005-2014, checked on 2015-2019;
    up to 5 that hold are frozen.
  * Trading thresholds frozen from validation predictions.
  Writes a LOCK (model, thresholds, patterns) and prints its sha256.

STAGE TEST (once; refuses unless --lock-sha matches the LOCK)
  * Sealed 2020-01-01 .. 2026-09-17, NET of the quoted spread.
  * G2 model trades, G3 pattern trades: net > 0, t >= 2.24, each sealed era
    > 0, and above the 95th percentile of 200 random-entry nulls.

    python3 timeline_v37.py --self-test | --stage fit | --stage test --lock-sha X
"""
from __future__ import annotations

import argparse, hashlib, json, math, os, pickle, re, sys
import numpy as np

VERSION = "1.0.1"
DOC = ("PREREGISTRATION_v37.md", "4edaacf1a6763ca3511da14c4aa67318abd7c56e2124fa4df4ba1d48215c1c53")
MAT = "../data/timeline_v37/matrix.npz"
LOCK = "../data/timeline_v37/LOCK.pkl"
TRAIN_END, INNER_START, VAL_START, SEALED_START = "2012-12-31", "2013-01-01", "2015-01-01", "2020-01-01"
SEALED_END = "2026-09-17"
N_PERM, N_RAND = 20, 200
Q_ENTRY = 0.90
HOLD_POINTS = 8                        # 2h at 15-min decision spacing
WINDOWS = {"60m": 60, "1d": 1440, "5d": 7200}
MIN_SUPPORT, MAX_PATTERNS = 300, 5
AUC_VOID = 0.65
T_GATE = 2.24
ERAS = (("2020-01-01", "2021-12-31"), ("2022-01-01", "2023-12-31"), ("2024-01-01", "2026-09-17"))
PARAMS = dict(objective="binary", learning_rate=0.03, num_leaves=15, min_data_in_leaf=200,
              feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
              verbose=-1, seed=7, num_threads=4)
_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)


def _guard():
    bad = [n for n in globals() if _FORBIDDEN.search(n)]
    if bad:
        raise SystemExit(f"namespace guard: {bad}")


def auc(y, p):
    y = np.asarray(y, bool); p = np.asarray(p, float)
    r = np.argsort(np.argsort(p)) + 1.0
    n1, n0 = y.sum(), (~y).sum()
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def day_shift(y, dates, rng):
    """Shift labels by a random whole number of trading days (keeps each
    day's internal structure and all autocorrelation, breaks the link)."""
    ud = np.unique(dates)
    k = int(rng.integers(20, len(ud) - 20))
    idx = {d: i for i, d in enumerate(ud)}
    di = np.array([idx[d] for d in dates])
    out = np.empty_like(y)
    for i, d in enumerate(ud):
        src = ud[(i + k) % len(ud)]
        a, b = np.where(di == i)[0], np.where(dates == src)[0]
        m = min(len(a), len(b))
        out[a[:m]] = y[b[:m]]
        if len(a) > m:
            out[a[m:]] = y[b[:len(a) - m]] if len(b) else 0
    return out


def fit_side(lgb, X, y, dates, core, inner):
    ds_c = lgb.Dataset(X[core], y[core])
    ds_i = lgb.Dataset(X[inner], y[inner], reference=ds_c)
    m = lgb.train(PARAMS, ds_c, num_boost_round=1500, valid_sets=[ds_i],
                  callbacks=[lgb.early_stopping(60, verbose=False)])
    return m


def presence(X, names, W):
    """(P, M): event present within W minutes, and its log-minutes-since."""
    evs = [n[3:] for n in names if n.startswith("ms_")]
    cols = [list(names).index("ms_" + e) for e in evs]
    M = X[:, cols]
    P = M < math.log1p(W)
    return evs, P, M


def mine(X, names, yl, ys, rows, base_l, base_s):
    """Every single event and ordered pair within each window; returns list of
    (key, side, lift, z, support)."""
    out = []
    for wn, W in WINDOWS.items():
        evs, P, M = presence(X[rows], names, W)
        yl_, ys_ = yl[rows] == 1, ys[rows] == 1
        def score(mask, key):
            n = int(mask.sum())
            if n < MIN_SUPPORT:
                return
            for side, yy, base in (("LONG", yl_, base_l), ("SHORT", ys_, base_s)):
                rate = yy[mask].mean()
                z = (rate - base) / math.sqrt(base * (1 - base) / n)
                out.append((key, side, rate / base, z, n))
        for a in range(len(evs)):
            score(P[:, a], (wn, evs[a]))
            for b in range(len(evs)):
                if a != b:
                    score(P[:, a] & P[:, b] & (M[:, a] > M[:, b]), (wn, evs[a], evs[b]))
    return out


def pattern_mask(X, names, key):
    wn, *ev = key
    evs, P, M = presence(X, names, WINDOWS[wn])
    ix = [evs.index(e) for e in ev]
    if len(ix) == 1:
        return P[:, ix[0]]
    a, b = ix
    return P[:, a] & P[:, b] & (M[:, a] > M[:, b])


def simulate(sig, dates, net):
    """Walk decision points in time order; sig = +1/-1/0; a trade blocks the
    next HOLD_POINTS points on the same day. Returns (dates, net) of trades."""
    td, tn, block, lastd = [], [], 0, None
    for i in range(len(sig)):
        if dates[i] != lastd:
            block, lastd = 0, dates[i]
        if block > 0:
            block -= 1
            continue
        if sig[i] != 0:
            td.append(dates[i]); tn.append(net[i][0] if sig[i] > 0 else net[i][1])
            block = HOLD_POINTS
    return np.array(td), np.array(tn, float)


def cl_t(dates, x):
    if len(x) < 30:
        return float("nan"), float("nan")
    ud, inv = np.unique(dates, return_inverse=True)
    mu = x.mean()
    s = np.bincount(inv, weights=x - mu)
    G = len(ud)
    se = math.sqrt((s ** 2).sum() * G / (G - 1)) / len(x)
    return mu, (mu / se if se > 0 else float("nan"))


def self_test():
    ok = True
    def check(n, c, d=""):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}" + (f"   {d}" if d else ""))
    print(f"timeline_v37.py v{VERSION} self-test\n")
    rng = np.random.default_rng(1)
    y = rng.random(5000) < 0.3
    p = y + rng.normal(0, 1, 5000)
    check("AUC of an informative score > 0.6", auc(y, p) > 0.6, f"{auc(y, p):.3f}")
    check("PLANTED FAIL: AUC of noise ~ 0.5", abs(auc(y, rng.random(5000)) - 0.5) < 0.03)
    dates = np.repeat(np.arange(500), 10)
    ys = day_shift(y.astype(np.int8), dates, rng)
    check("day shift keeps the base rate", abs(ys.mean() - y.mean()) < 0.01)
    check("day shift breaks the alignment", abs(auc(ys, p) - 0.5) < 0.05, f"{auc(ys, p):.3f}")
    sig = np.zeros(40, int); sig[0] = 1; sig[3] = -1; sig[20] = -1
    d2 = np.array([0] * 20 + [1] * 20)
    net = np.ones((40, 2)); net[:, 1] = -1
    td, tn = simulate(sig, d2, net)
    check("a trade blocks the next 8 points; a new day unblocks", len(tn) == 2 and tn[0] == 1 and tn[1] == -1)
    x = rng.normal(0, 30, 3000); dd = np.repeat(np.arange(1000), 3)
    check("PLANTED FAIL: clustered t of noise < gate", abs(cl_t(dd, x)[1]) < T_GATE)
    check("clustered t finds a +3 bp edge on 3000", cl_t(dd, x + 3)[1] > T_GATE)
    check("split dates are ordered and sealed starts 2020",
          TRAIN_END < INNER_START < VAL_START < SEALED_START == "2020-01-01")
    check("namespace guard", not [n for n in globals() if _FORBIDDEN.search(n)])
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def stage_fit(here):
    import lightgbm as lgb
    z = np.load(os.path.join(here, MAT), allow_pickle=False)
    d_all = z["date"]
    keep = d_all < SEALED_START                 # the sealed rows never leave disk
    X, names = z["X"][keep], list(z["names"])
    d, yl, ys = d_all[keep], z["yl"][keep], z["ys"][keep]
    assert max(d) < SEALED_START      # 1.0.1: numpy max fails on str dates (crashed before any fit)
    core, inner, val = d <= TRAIN_END, (d >= INNER_START) & (d < VAL_START), d >= VAL_START
    trn = core | inner
    print(f"  rows: core {core.sum():,}  inner {inner.sum():,}  validation {val.sum():,}"
          f"  (sealed rows loaded: 0)")
    res, models, rounds = {}, {}, {}
    for side, y in (("LONG", yl == 1), ("SHORT", ys == 1)):
        m = fit_side(lgb, X, y.astype(int), d, core, inner)
        rounds[side] = m.best_iteration
        pv = m.predict(X[val], num_iteration=m.best_iteration)
        a = auc(y[val], pv)
        rng = np.random.default_rng(11 if side == "LONG" else 12)
        null = []
        for k in range(N_PERM):
            yp = y.astype(np.int8).copy()
            yp[trn] = day_shift(y[trn].astype(np.int8), d[trn], rng)
            mn = fit_side(lgb, X, yp, d, core, inner)
            null.append(auc(y[val], mn.predict(X[val], num_iteration=mn.best_iteration)))
        null = np.array(null)
        g1 = a > null.max() and a < AUC_VOID
        res[side] = dict(auc=a, null_max=float(null.max()), null_mean=float(null.mean()), g1=bool(g1))
        models[side] = m
        print(f"  {side:<5} validation AUC {a:.4f}  null (20 day-shifts) mean {null.mean():.4f} max {null.max():.4f}"
              f"  rounds {m.best_iteration}   G1 {'PASS' if g1 else 'FAIL'}"
              + ("   VOID: AUC above 0.65 is presumed leakage" if a >= AUC_VOID else ""))
    pl = models["LONG"].predict(X[val], num_iteration=rounds["LONG"])
    ps = models["SHORT"].predict(X[val], num_iteration=rounds["SHORT"])
    thr = dict(long=float(np.quantile(pl, Q_ENTRY)), short=float(np.quantile(ps, Q_ENTRY)))
    # validation trading, reported only (gross: spreads 2015-19 were real, so net too)
    net_val = np.column_stack([z["gl"][keep][val] - z["spread"][keep][val],
                               z["gs"][keep][val] - z["spread"][keep][val]])
    sig = np.where((pl >= thr["long"]) & (pl > ps), 1, np.where((ps >= thr["short"]) & (ps > pl), -1, 0))
    td, tn = simulate(sig, d[val], net_val)
    mu, t = cl_t(td, tn)
    print(f"  validation trading (reported): {len(tn)} trades, net {mu:+.2f} bp/trade, t {t:+.2f}")
    imp = sorted(zip(models["LONG"].feature_importance("gain") + models["SHORT"].feature_importance("gain"), names), reverse=True)[:15]
    print("  top features by gain (long+short):  " + ", ".join(n for _, n in imp))

    # ---- patterns
    base_l, base_s = (yl[trn] == 1).mean(), (ys[trn] == 1).mean()
    cand = mine(X, names, yl, ys, trn, base_l, base_s)
    cand.sort(key=lambda r: -r[3])
    top = cand[:40]
    print(f"\n  patterns mined on 2005-2014: {len(cand):,} scored; top 40 by z go to validation")
    vl, vs_ = (yl[val] == 1), (ys[val] == 1)
    held = []
    for key, side, lift, zt, n in top:
        mk = pattern_mask(X[val], names, key)
        nv = int(mk.sum())
        if nv < 50:
            continue
        yy, base = (vl, vl.mean()) if side == "LONG" else (vs_, vs_.mean())
        rate = yy[mk].mean()
        zv = (rate - base) / math.sqrt(base * (1 - base) / nv)
        if zv >= 2.0:
            held.append((key, side, lift, zt, n, rate / base, zv, nv))
    held.sort(key=lambda r: -r[6])
    frozen = held[:MAX_PATTERNS]
    for key, side, lift, zt, n, lv, zv, nv in top[:10] if False else frozen:
        pass
    print(f"  {len(held)} of the top 40 held on validation (z >= 2); frozen: {len(frozen)}")
    for key, side, lift, zt, n, lv, zv, nv in frozen:
        print(f"    {side:<5} {' then '.join(key[1:]):<44} within {key[0]:<4}  train lift {lift:.2f} (n {n})  val lift {lv:.2f} z {zv:+.2f} (n {nv})")
    print("  top 10 mined (before validation), for the record:")
    for key, side, lift, zt, n in top[:10]:
        print(f"    {side:<5} {' then '.join(key[1:]):<44} within {key[0]:<4}  lift {lift:.2f}  z {zt:+.1f}  n {n}")
    lock = dict(version=VERSION, rounds=rounds, thr=thr, res=res, names=names,
                patterns=[(list(k), s) for k, s, *_ in frozen],
                models={s: m.model_to_string(num_iteration=rounds[s]) for s, m in models.items()})
    blob = pickle.dumps(lock)
    open(os.path.join(here, LOCK), "wb").write(blob)
    sha = hashlib.sha256(blob).hexdigest()
    print(f"\n  G1 (information): LONG {'PASS' if res['LONG']['g1'] else 'FAIL'}   SHORT {'PASS' if res['SHORT']['g1'] else 'FAIL'}")
    print(f"  LOCK written, sha256 {sha}")


def stage_test(here, lock_sha):
    import lightgbm as lgb
    blob = open(os.path.join(here, LOCK), "rb").read()
    if hashlib.sha256(blob).hexdigest() != lock_sha:
        print("  LOCK does not match --lock-sha. Refused."); sys.exit(2)
    lock = pickle.loads(blob)
    z = np.load(os.path.join(here, MAT), allow_pickle=False)
    d = z["date"]
    sel = (d >= SEALED_START) & (d <= SEALED_END)
    X, dd = z["X"][sel], d[sel]
    net = np.column_stack([z["gl"][sel] - z["spread"][sel], z["gs"][sel] - z["spread"][sel]])
    print(f"  sealed rows {sel.sum():,} on {len(np.unique(dd))} days, 2020-01-01 .. {dd.max()}")
    ml = lgb.Booster(model_str=lock["models"]["LONG"]); ms = lgb.Booster(model_str=lock["models"]["SHORT"])
    pl, ps = ml.predict(X), ms.predict(X)
    print(f"  sealed AUC (reported): LONG {auc(z['yl'][sel] == 1, pl):.4f}   SHORT {auc(z['ys'][sel] == 1, ps):.4f}")
    thr = lock["thr"]
    sig_m = np.where((pl >= thr["long"]) & (pl > ps), 1, np.where((ps >= thr["short"]) & (ps > pl), -1, 0))
    sig_p = np.zeros(len(dd), int)
    for key, side in lock["patterns"]:
        mk = pattern_mask(X, lock["names"], tuple(key))
        sig_p += np.where(mk, 1 if side == "LONG" else -1, 0)
    sig_p = np.sign(sig_p)
    rng = np.random.default_rng(99)
    verdicts = {}
    for nm, sig in (("G2 model", sig_m), ("G3 patterns", sig_p)):
        td, tn = simulate(sig, dd, net)
        if len(tn) < 30:
            print(f"\n  {nm}: {len(tn)} trades -- too few; FAIL"); verdicts[nm] = "FAIL"; continue
        mu, t = cl_t(td, tn)
        eras = []
        for lo, hi in ERAS:
            m = (td >= lo) & (td <= hi)
            eras.append(tn[m].mean() if m.sum() else float("nan"))
        rnd = []
        rate = (sig != 0).mean()
        for _ in range(N_RAND):
            rs = np.where(rng.random(len(dd)) < rate, rng.choice([-1, 1], len(dd)), 0)
            rnd.append(simulate(rs, dd, net)[1].mean())
        p95 = float(np.quantile(rnd, 0.95))
        ok = mu > 0 and t >= T_GATE and all(e > 0 for e in eras) and mu > p95
        verdicts[nm] = "PASS" if ok else "FAIL"
        print(f"\n  {nm}: {len(tn)} trades  net {mu:+.2f} bp/trade  t {t:+.2f}  win share {np.mean(tn > 0):.3f}")
        print("    by era  " + "   ".join(f"{lo[:4]}-{hi[:4]} {e:+.2f}" for (lo, hi), e in zip(ERAS, eras))
              + f"   random-entry null 95th pct {p95:+.2f}   -> {verdicts[nm]}")
    print("\n  VERDICTS  " + "   ".join(f"{k}: {v}" for k, v in verdicts.items()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--stage", choices=["fit", "test"])
    ap.add_argument("--lock-sha")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    here = os.path.dirname(os.path.abspath(__file__))
    print(f"timeline_v37.py v{VERSION}   PREREGISTRATION_v37   stage {a.stage}\n")
    print("  I am not a financial adviser. This is a measurement, not a")
    print("  recommendation to take a position.\n")
    got = hashlib.sha256(open(os.path.join(here, "..", DOC[0]), "rb").read()).hexdigest()
    if got != DOC[1]:
        print(f"  {DOC[0]} changed since frozen ({got[:12]}). Refused."); sys.exit(2)
    print(f"  {DOC[0]} sha256 {got[:16]}... matches\n")
    if a.stage == "fit":
        stage_fit(here)
    elif a.stage == "test":
        stage_test(here, a.lock_sha)


_guard()

if __name__ == "__main__":
    main()
