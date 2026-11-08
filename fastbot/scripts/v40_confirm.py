#!/usr/bin/env python3
"""PREREGISTRATION_v40 -- confirmation of the v39 winner on markets no model
has seen. FOREST (frozen v39 config) trained ONLY on SPX500, yearly
walk-forward (train on SPX years < Y), predicts direction on UK100 DE30 EU50
JP225 AU200 in year Y, each on its own v37 timeline (tl_build2, Gate 0).
  --stage predict   resumable; writes data/v40/pred_<stem>.npy
  --stage test      the gates (once)
"""
import argparse, hashlib, os, sys, time, datetime as dt, math
import numpy as np

VERSION = "1.0"
DOC = ("PREREGISTRATION_v40.md", "19b050601244fbffefb4ff8b2cb623a0d8af27935eb104f7211b4500e72e996d")
STEMS = ("uk100gbp", "de30eur", "eu50eur", "jp225usd", "au200aud")
YEARS = range(2012, 2027)
ERAS = ((2013, 2017), (2018, 2021), (2022, 2026))
T_GATE, T_REPL, N_BOOT = 2.24, 1.64, 1000


def forest():
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import make_pipeline
    return make_pipeline(SimpleImputer(strategy="median"),
                         RandomForestClassifier(300, min_samples_leaf=200, max_features="sqrt", n_jobs=4, random_state=7))


def auc(y, p):
    y = np.asarray(y, bool); r = np.argsort(np.argsort(p)) + 1.0
    n1, n0 = y.sum(), (~y).sum()
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def cl_t(dates, x):
    ud, inv = np.unique(dates, return_inverse=True); mu = x.mean()
    s = np.bincount(inv, weights=x - mu); G = len(ud)
    se = math.sqrt((s ** 2).sum() * G / (G - 1)) / len(x)
    return mu, mu / se


def stage_predict(budget):
    t0 = time.time()
    S = dict(np.load("../data/timeline_v37/matrix.npz"))
    hitS = (S["yl"] == 1) | (S["ys"] == 1)
    M = {s: dict(np.load(f"../data/v40/{s}.npz")) for s in STEMS}
    for s in STEMS:
        assert list(M[s]["names"]) == list(S["names"]), "feature names differ"
    P = {s: (np.load(f"../data/v40/pred_{s}.npy") if os.path.exists(f"../data/v40/pred_{s}.npy")
             else np.full(len(M[s]["date"]), np.nan, np.float32)) for s in STEMS}
    for Y in YEARS:
        todo = [s for s in STEMS if np.isnan(P[s][(M[s]["date"] >= f"{Y}-01-01") & (M[s]["date"] <= f"{Y}-12-31")]).any()]
        if not todo:
            continue
        if time.time() - t0 > budget:
            print("paused"); return
        tr = hitS & (S["date"] < f"{Y}-01-01")
        m = forest().fit(S["X"][tr], (S["yl"][tr] == 1).astype(int))
        for s in todo:
            sel = (M[s]["date"] >= f"{Y}-01-01") & (M[s]["date"] <= f"{Y}-12-31")
            if sel.any():
                P[s][sel] = m.predict_proba(M[s]["X"][sel])[:, 1]
            np.save(f"../data/v40/pred_{s}.npy", P[s])
        print(f"  {Y} done ({time.time() - t0:.0f}s)", flush=True)
    print("all predictions written")


def paths_for(stem, dates, hms):
    import noise_v38 as N
    days = N.load("../data/v38", stem)
    tz, want, _ = N.plan(stem); last = want[-1]
    out = {}
    for i, (d, h) in enumerate(zip(dates, hms)):
        bars = days.get(dt.date.fromisoformat(d))
        if not bars or last not in bars:
            continue
        ks = sorted(bars); j = ks.index(h)
        after = [bars[k] for k in ks[j + 1:]]
        if len(after) < 24:
            continue
        e = after[0][0]
        out[i] = np.array([((b[1] / e - 1) * 1e4, (b[2] / e - 1) * 1e4, (b[3] / e - 1) * 1e4) for b in after], np.float32)
    return out


def run_exit(p, b, side, kind):
    """E1: fixed 2h (24 bars), stop 1 sigma.  E2: to the close, stop 1 sigma trailing
    the best price at max(0.3, 1 - 0.5*mfe) sigma, never below break-even after +0.5 sigma.
    A bar's low is checked against the stop BEFORE its high moves the trail."""
    best, stop = 0.0, -b
    seq = p[:24] if kind == "E1" else p
    for hi, lo, c in seq:
        fav, adv = (hi, lo) if side > 0 else (-lo, -hi)
        if adv <= stop:
            return stop
        if kind == "E2":
            best = max(best, fav); m = best / b
            dist = max(0.3, 1.0 - 0.5 * m)
            if m >= 0.5:
                dist = min(m, dist)
            stop = max(stop, best - dist * b)
    return side * seq[-1][2]


def stage_test():
    rng = np.random.default_rng(40)
    allY, allP, allD, per = [], [], [], {}
    trades = {"E1": [], "E2": []}
    ctrl = {"E1": [], "E2": []}
    for s in STEMS:
        M = dict(np.load(f"../data/v40/{s}.npz")); P = np.load(f"../data/v40/pred_{s}.npy")
        d, hms, b, sp = M["date"], M["hm"], M["b_bp"], M["spread"]
        hit = (M["yl"] == 1) | (M["ys"] == 1); g = (d >= "2013-01-01") & np.isfinite(P)
        per[s] = auc(M["yl"][hit & g] == 1, P[hit & g])
        allY.append(M["yl"][hit & g] == 1); allP.append(P[hit & g]); allD.append(d[hit & g])
        yrs = np.array([int(x[:4]) for x in d]); sig = np.zeros(len(d), int)
        for Y in range(2013, 2027):
            prev, cur = (yrs == Y - 1) & np.isfinite(P), (yrs == Y) & np.isfinite(P)
            if prev.sum() < 100 or not cur.any():
                continue
            lo, hi = np.quantile(P[prev], [0.10, 0.90])
            sig[cur] = np.where(P[cur] >= hi, 1, np.where(P[cur] <= lo, -1, 0))
        paths = paths_for(s, d, hms)
        lastd = None
        for i in np.where((yrs >= 2013) & (sp > 0))[0]:
            if d[i] == lastd or sig[i] == 0 or i not in paths:
                continue
            lastd = d[i]
            for k in ("E1", "E2"):
                trades[k].append((s, d[i], run_exit(paths[i], b[i], sig[i], k) - sp[i]))
        cand = [i for i in np.where((yrs >= 2013) & (sp > 0))[0] if i in paths]
        for i in rng.choice(cand, min(3000, len(cand)), replace=False):
            for k in ("E1", "E2"):
                ctrl[k] += [(s, run_exit(paths[i], b[i], side, k) - sp[i]) for side in (1, -1)]
    Y, Pp, D = np.concatenate(allY), np.concatenate(allP), np.concatenate(allD)
    a = auc(Y, Pp)
    ud, inv = np.unique(D, return_inverse=True); groups = [np.where(inv == i)[0] for i in range(len(ud))]
    boots = []
    for _ in range(N_BOOT):
        ix = np.concatenate([groups[i] for i in rng.integers(0, len(ud), len(ud))])
        boots.append(auc(Y[ix], Pp[ix]))
    lo = float(np.quantile(boots, 0.025))
    g1 = lo > 0.5 and sum(v > 0.5 for v in per.values()) >= 4
    print("  G1 DIRECTION (hit points, 2013-2026, five unseen markets)")
    for s, v in per.items():
        print(f"    {s:<9} AUC {v:.4f}")
    print(f"    POOLED   AUC {a:.4f}  day-bootstrap 95% lower {lo:.4f}  -> G1 {'PASS' if g1 else 'FAIL'}")
    out = {"G1": g1}
    for k, name in (("E1", "G2 fixed 2h, stop 1σ"), ("E2", "G3 to close, tightening + break-even")):
        dd = np.array([t[1] for t in trades[k]]); x = np.array([t[2] for t in trades[k]])
        mu, t = cl_t(dd, x)
        eras = [x[np.array([lo_ <= int(q[:4]) <= hi_ for q in dd])].mean() for lo_, hi_ in ERAS]
        mx = np.array([int(q[:4]) not in (2020, 2021) for q in dd]); mux, tx = cl_t(dd[mx], x[mx])
        ok = mu > 0 and t >= T_GATE and all(e > 0 for e in eras) and mux > 0 and tx >= T_REPL
        out[k] = ok
        c = np.array([v for _, v in ctrl[k]])
        print(f"\n  {name}: {len(x)} trades  NET {mu:+.2f} bp/trade  t {t:+.2f}  win {np.mean(x > 0) * 100:.1f}%"
              f"   eras " + " ".join(f"{e:+.2f}" for e in eras) + f"   ex-2020/21 {mux:+.2f} (t {tx:+.2f})"
              f"   control {c.mean():+.2f}  signal adds {mu - c.mean():+.2f}  -> {'PASS' if ok else 'FAIL'}")
        for s in STEMS:
            xs = np.array([t_[2] for t_ in trades[k] if t_[0] == s]); cs = np.array([v for s_, v in ctrl[k] if s_ == s])
            print(f"      {s:<9} n {len(xs):>5}  net {xs.mean():+.2f}  control {cs.mean():+.2f}  adds {xs.mean() - cs.mean():+.2f}")
    print("\n  VERDICTS  " + "   ".join(f"{k}: {'PASS' if v else 'FAIL'}" for k, v in (("G1", out["G1"]), ("G2", out["E1"]), ("G3", out["E2"]))))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", choices=["predict", "test"]); ap.add_argument("--budget", type=float, default=160)
    a = ap.parse_args()
    got = hashlib.sha256(open("../PREREGISTRATION_v40.md", "rb").read()).hexdigest()
    if got != DOC[1]:
        print("PREREGISTRATION_v40.md changed since frozen. Refused."); sys.exit(2)
    print(f"v40_confirm.py v{VERSION}  stage {a.stage}\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    stage_predict(a.budget) if a.stage == "predict" else stage_test()


if __name__ == "__main__":
    main()
