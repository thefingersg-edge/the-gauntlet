#!/usr/bin/env python3
"""PREREGISTRATION_v37.1 -- the timeline test, asking about DIRECTION only.

v37 (1.0.1) was VOIDED by its own rule (validation AUC 0.70 >= 0.65). The
diagnostic (tl_diag_v37.py, validation only) showed the models were
predicting whether ANY barrier is hit (AUC 0.75, realised-vol ratio alone
0.74), not which way: p_long and p_short correlate +0.74. Here one model per
point predicts UP-FIRST vs DOWN-FIRST, trained and scored only on points
where a barrier was hit. Everything else is v37: data, features, split,
parameters, nulls, gates, the LOCK-then-TEST protocol.

    python3 timeline_v37_1.py --self-test | --stage fit | --stage test --lock-sha X
"""
from __future__ import annotations

import argparse, hashlib, math, os, pickle, sys
import numpy as np

import timeline_v37 as B
from timeline_v37 import (auc, day_shift, simulate, cl_t, presence, pattern_mask, WINDOWS,
                          MIN_SUPPORT, MAX_PATTERNS, N_PERM, N_RAND, AUC_VOID, T_GATE, ERAS,
                          TRAIN_END, INNER_START, VAL_START, SEALED_START, SEALED_END, MAT)

VERSION = "1.1.1"   # 1.1 crashed in the null loop (uneven day sizes) before printing any AUC
DOC = ("PREREGISTRATION_v37.1.md", "421264a370f955c8f482d7c4fec6cd4f2670d800d7f699926d439a6d3262091f")
LOCK = "../data/timeline_v37/LOCK_v37_1.pkl"
Q_HI, Q_LO = 0.90, 0.10


def day_shift2(y, dates, rng):
    """v37 day_shift, but days of unequal size are filled by cycling the
    source day's labels (1.1 crashed here on hit-point subsets)."""
    ud = np.unique(dates)
    k = int(rng.integers(20, len(ud) - 20))
    pos = {dd: np.where(dates == dd)[0] for dd in ud}
    out = np.empty_like(y)
    for i, dd in enumerate(ud):
        a, b = pos[dd], pos[ud[(i + k) % len(ud)]]
        out[a] = y[b[np.arange(len(a)) % len(b)]]
    return out


def fit_dir(lgb, X, y, core, inner):
    ds_c = lgb.Dataset(X[core], y[core]); ds_i = lgb.Dataset(X[inner], y[inner], reference=ds_c)
    return lgb.train(B.PARAMS, ds_c, num_boost_round=1500, valid_sets=[ds_i],
                     callbacks=[lgb.early_stopping(60, verbose=False)])


def mine_dir(X, names, up, rows, base):
    out = []
    for wn, W in WINDOWS.items():
        evs, P, M = presence(X[rows], names, W)
        u = up[rows]
        def score(mask, key):
            n = int(mask.sum())
            if n < MIN_SUPPORT:
                return
            rate = u[mask].mean()
            z = (rate - base) / math.sqrt(base * (1 - base) / n)
            out.append((key, "LONG" if z > 0 else "SHORT", rate, z, n))
        for a in range(len(evs)):
            score(P[:, a], (wn, evs[a]))
            for b in range(len(evs)):
                if a != b:
                    score(P[:, a] & P[:, b] & (M[:, a] > M[:, b]), (wn, evs[a], evs[b]))
    return out


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"timeline_v37_1.py v{VERSION} self-test\n")
    rng = np.random.default_rng(3)
    names = ["ms_a", "ms_b", "x"]
    n = 4000
    X = np.full((n, 3), math.log1p(86400), np.float32)
    X[:2000, 0] = math.log1p(30)                    # event a recent on first half
    up = np.zeros(n, bool); up[:2000] = rng.random(2000) < 0.7; up[2000:] = rng.random(2000) < 0.4
    got = mine_dir(X, names, up, np.ones(n, bool), up.mean())
    best = max(got, key=lambda r: abs(r[3]))
    check("a planted 'a -> up' pattern is mined as LONG", best[0][1:] == ("a",) and best[1] == "LONG")
    upr = rng.random(n) < 0.5
    got2 = mine_dir(X, names, upr, np.ones(n, bool), upr.mean())
    check("PLANTED FAIL: with random direction no pattern reaches |z| 4",
          max(abs(r[3]) for r in got2) < 4)
    dts = np.repeat(np.arange(300), rng.integers(1, 9, 300))
    yy = (rng.random(len(dts)) < 0.47).astype(np.int8)
    sh = day_shift2(yy, dts, rng)
    check("day_shift2 handles unequal day sizes and keeps the base rate", len(sh) == len(yy) and abs(sh.mean() - yy.mean()) < 0.05)
    check("thresholds are symmetric deciles", Q_HI == 0.90 and Q_LO == 0.10)
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def stage_fit(here):
    import lightgbm as lgb
    z = np.load(os.path.join(here, MAT)); d_all = z["date"]; keep = d_all < SEALED_START
    X, names, d = z["X"][keep], list(z["names"]), d_all[keep]
    assert max(d) < SEALED_START
    yl, ys = z["yl"][keep] == 1, z["ys"][keep] == 1
    hit = yl | ys; up = yl
    core = (d <= TRAIN_END) & hit; inner = (d >= INNER_START) & (d < VAL_START) & hit
    val_all = d >= VAL_START; val = val_all & hit; trn = (d < VAL_START) & hit
    print(f"  hit points: core {core.sum():,}  inner {inner.sum():,}  validation {val.sum():,}"
          f"  (up-first share train {up[trn].mean():.3f}, val {up[val].mean():.3f}; sealed rows loaded: 0)")
    m = fit_dir(lgb, X, up.astype(int), core, inner)
    pv = m.predict(X[val], num_iteration=m.best_iteration)
    a = auc(up[val], pv)
    rng = np.random.default_rng(21)
    null = []
    idx_trn = np.where(trn)[0]
    for k in range(N_PERM):
        yp = up.astype(np.int8).copy()
        yp[idx_trn] = day_shift2(up[idx_trn].astype(np.int8), d[idx_trn], rng)
        mn = fit_dir(lgb, X, yp, core, inner)
        null.append(auc(up[val], mn.predict(X[val], num_iteration=mn.best_iteration)))
    null = np.array(null)
    g1 = a > null.max() and a < AUC_VOID
    print(f"  DIRECTION validation AUC {a:.4f}  null (20 day-shifts) mean {null.mean():.4f} max {null.max():.4f}"
          f"  rounds {m.best_iteration}   G1 {'PASS' if g1 else 'FAIL'}"
          + ("   VOID (>= 0.65)" if a >= AUC_VOID else ""))
    p_all = m.predict(X[val_all], num_iteration=m.best_iteration)
    thr = dict(hi=float(np.quantile(p_all, Q_HI)), lo=float(np.quantile(p_all, Q_LO)))
    net_val = np.column_stack([z["gl"][keep][val_all] - z["spread"][keep][val_all],
                               z["gs"][keep][val_all] - z["spread"][keep][val_all]])
    sig = np.where(p_all >= thr["hi"], 1, np.where(p_all <= thr["lo"], -1, 0))
    td, tn = simulate(sig, d[val_all], net_val)
    mu, t = cl_t(td, tn)
    print(f"  validation trading (reported): {len(tn)} trades, net {mu:+.2f} bp/trade, t {t:+.2f}, win share {np.mean(tn > 0):.3f}")
    imp = sorted(zip(m.feature_importance("gain"), names), reverse=True)[:15]
    print("  top features by gain: " + ", ".join(n for _, n in imp))
    base = up[trn].mean()
    cand = mine_dir(X, names, up, trn, base)
    cand.sort(key=lambda r: -abs(r[3]))
    top = cand[:40]
    held = []
    uv = up[val]; bv = uv.mean()
    for key, side, rate, zt, n in top:
        mk = pattern_mask(X[val], names, key)
        nv = int(mk.sum())
        if nv < 50:
            continue
        zv = (uv[mk].mean() - bv) / math.sqrt(bv * (1 - bv) / nv)
        if (zv >= 2.0 and side == "LONG") or (zv <= -2.0 and side == "SHORT"):
            held.append((key, side, rate, zt, n, uv[mk].mean(), zv, nv))
    held.sort(key=lambda r: -abs(r[6]))
    frozen = held[:MAX_PATTERNS]
    print(f"\n  patterns: {len(cand):,} scored on 2005-2014 (base up-first {base:.3f}); top 40 by |z| checked on 2015-2019;"
          f" {len(held)} held; frozen {len(frozen)}")
    for key, side, rate, zt, n, rv, zv, nv in frozen:
        print(f"    {side:<5} {' then '.join(key[1:]):<42} within {key[0]:<4} up-first train {rate:.3f} (z {zt:+.1f}, n {n})"
              f"  val {rv:.3f} (z {zv:+.1f}, n {nv})")
    print("  top 10 mined, for the record:")
    for key, side, rate, zt, n in top[:10]:
        print(f"    {side:<5} {' then '.join(key[1:]):<42} within {key[0]:<4} up-first {rate:.3f}  z {zt:+.1f}  n {n}")
    lock = dict(version=VERSION, thr=thr, auc=a, null=null.tolist(), g1=bool(g1), names=names,
                patterns=[(list(k), s) for k, s, *_ in frozen],
                model=m.model_to_string(num_iteration=m.best_iteration))
    blob = pickle.dumps(lock)
    open(os.path.join(here, LOCK), "wb").write(blob)
    print(f"\n  G1 (direction information): {'PASS' if g1 else 'FAIL'}")
    print(f"  LOCK written, sha256 {hashlib.sha256(blob).hexdigest()}")


def stage_test(here, lock_sha):
    import lightgbm as lgb
    blob = open(os.path.join(here, LOCK), "rb").read()
    if hashlib.sha256(blob).hexdigest() != lock_sha:
        print("  LOCK does not match --lock-sha. Refused."); sys.exit(2)
    L = pickle.loads(blob)
    z = np.load(os.path.join(here, MAT)); d = z["date"]
    sel = (d >= SEALED_START) & (d <= SEALED_END)
    X, dd = z["X"][sel], d[sel]
    net = np.column_stack([z["gl"][sel] - z["spread"][sel], z["gs"][sel] - z["spread"][sel]])
    yl, ys = z["yl"][sel] == 1, z["ys"][sel] == 1
    hit = yl | ys
    p = lgb.Booster(model_str=L["model"]).predict(X)
    print(f"  sealed: {sel.sum():,} points on {len(np.unique(dd))} days; direction AUC on hit points {auc(yl[hit], p[hit]):.4f} (reported)")
    sig_m = np.where(p >= L["thr"]["hi"], 1, np.where(p <= L["thr"]["lo"], -1, 0))
    sig_p = np.zeros(len(dd), int)
    for key, side in L["patterns"]:
        sig_p += np.where(pattern_mask(X, L["names"], tuple(key)), 1 if side == "LONG" else -1, 0)
    sig_p = np.sign(sig_p)
    rng = np.random.default_rng(99)
    out = {}
    for nm, sig in (("G2 model", sig_m), ("G3 patterns", sig_p)):
        td, tn = simulate(sig, dd, net)
        if len(tn) < 30:
            print(f"\n  {nm}: {len(tn)} trades -- too few; FAIL"); out[nm] = "FAIL"; continue
        mu, t = cl_t(td, tn)
        eras = [tn[(td >= lo) & (td <= hi)].mean() for lo, hi in ERAS]
        rate = (sig != 0).mean()
        rnd = [simulate(np.where(rng.random(len(dd)) < rate, rng.choice([-1, 1], len(dd)), 0), dd, net)[1].mean()
               for _ in range(N_RAND)]
        p95 = float(np.quantile(rnd, 0.95))
        ok = mu > 0 and t >= T_GATE and all(e > 0 for e in eras) and mu > p95
        out[nm] = "PASS" if ok else "FAIL"
        print(f"\n  {nm}: {len(tn)} trades  net {mu:+.2f} bp/trade  t {t:+.2f}  win share {np.mean(tn > 0):.3f}")
        print("    by era  " + "   ".join(f"{lo[:4]}-{hi[:4]} {e:+.2f}" for (lo, hi), e in zip(ERAS, eras))
              + f"   random-entry 95th pct {p95:+.2f}   -> {out[nm]}")
    print("\n  VERDICTS  " + "   ".join(f"{k}: {v}" for k, v in out.items()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--stage", choices=["fit", "test"])
    ap.add_argument("--lock-sha")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    here = os.path.dirname(os.path.abspath(__file__))
    print(f"timeline_v37_1.py v{VERSION}   PREREGISTRATION_v37.1   stage {a.stage}\n")
    print("  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    for doc, want in (B.DOC, DOC):
        got = hashlib.sha256(open(os.path.join(here, "..", doc), "rb").read()).hexdigest()
        if got != want:
            print(f"  {doc} changed since frozen. Refused."); sys.exit(2)
        print(f"  {doc} sha256 {got[:16]}... matches")
    print()
    stage_fit(here) if a.stage == "fit" else stage_test(here, a.lock_sha)


if __name__ == "__main__":
    main()
