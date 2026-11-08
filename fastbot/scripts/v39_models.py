#!/usr/bin/env python3
"""PREREGISTRATION_v39 -- which model type finds direction in the timeline?
Development comparison on SPX500 2012-2026 (all previously seen data), yearly
walk-forward with an expanding window. It PICKS a winner by a frozen rule; it
cannot confirm one (v38 indices and forward data do that).

Models (direction: up-first vs down-first among barrier hits, v37.1 labels)
  LGBM    LightGBM, v37 parameters, early-stopped on the last 6 months of train
  LOGIT   L2 logistic regression (C 0.1), median-impute + standardise
  FOREST  random forest, 300 trees, min leaf 200, sqrt features
  RULES   one decision tree, depth 3, min leaf 500 (readable)
  KNN-EV  k-nearest-neighbours (k 250) on 20 principal components of the timeline
  KNN-SH  k-nearest-neighbours (k 250) on the 24-bar z-normalised price shape
  NULL    LGBM on day-shifted training labels (the reference a model must beat)
Part M: meta-labelling -- LGBM decides which v36 noise-band trades to keep.
"""
from __future__ import annotations
import argparse, hashlib, math, os, sys, json
import numpy as np
from timeline_v37 import auc, simulate, cl_t, PARAMS
import timeline_v37_1 as V1

VERSION = "1.0"
DOC = ("PREREGISTRATION_v39.md", "f42c19b2b1f015dbd198108ccc07d8647744005f29f49550d9e359e7e2d77d93")
YEARS = list(range(2012, 2027))
MODELS = ["LGBM", "LOGIT", "FOREST", "RULES", "KNN-EV", "KNN-SH", "NULL"]
MIN_WIN_YEARS = 10
META_KEEP = 0.60


def fit_predict(name, Xtr, ytr, Xte, dtr, rng, Str=None, Ste=None):
    import lightgbm as lgb
    from sklearn.pipeline import make_pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.decomposition import PCA
    from sklearn.neighbors import NearestNeighbors
    if name in ("LGBM", "NULL"):
        y = ytr if name == "LGBM" else V1.day_shift2(ytr.astype(np.int8), dtr, rng)
        cut = np.sort(np.unique(dtr))[-126]            # ~last 6 months of trading days
        core, inner = dtr < cut, dtr >= cut
        m = lgb.train(PARAMS, lgb.Dataset(Xtr[core], y[core]), 1500,
                      valid_sets=[lgb.Dataset(Xtr[inner], y[inner])],
                      callbacks=[lgb.early_stopping(60, verbose=False)])
        return m.predict(Xte, num_iteration=m.best_iteration)
    if name == "LOGIT":
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=0.1, max_iter=2000))
    elif name == "FOREST":
        m = make_pipeline(SimpleImputer(strategy="median"),
                          RandomForestClassifier(300, min_samples_leaf=200, max_features="sqrt", n_jobs=4, random_state=7))
    elif name == "RULES":
        m = make_pipeline(SimpleImputer(strategy="median"), DecisionTreeClassifier(max_depth=3, min_samples_leaf=500, random_state=7))
    if name in ("LOGIT", "FOREST", "RULES"):
        m.fit(Xtr, ytr)
        return m.predict_proba(Xte)[:, 1]
    if name == "KNN-EV":
        pre = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), PCA(20, random_state=7))
        A, B = pre.fit_transform(Xtr), pre.transform(Xte)
    else:
        ok_tr, ok_te = np.isfinite(Str).all(1), np.isfinite(Ste).all(1)
        A, B = np.where(ok_tr[:, None], Str, 0), np.where(ok_te[:, None], Ste, 0)
    nn = NearestNeighbors(n_neighbors=250).fit(A)
    _, ix = nn.kneighbors(B)
    return ytr[ix].mean(1)


def run_models(here, out_rows):
    z = np.load(os.path.join(here, "../data/timeline_v37/matrix.npz")); sh = np.load(os.path.join(here, "../data/v39/shapes.npz"))
    d, X = z["date"], z["X"]; S = sh["s24"]
    hit = (z["yl"] == 1) | (z["ys"] == 1); up = (z["yl"] == 1).astype(int)
    net = np.column_stack([z["gl"] - z["spread"], z["gs"] - z["spread"]])
    rng = np.random.default_rng(39)
    prev_pred = {}
    res = {m: {} for m in MODELS}
    for Y in YEARS:
        tr = hit & (d < f"{Y}-01-01"); te_all = (d >= f"{Y}-01-01") & (d <= f"{Y}-12-31") & (d <= "2026-09-17")
        te = te_all & hit
        if te.sum() < 200:
            continue
        for mname in MODELS:
            p_all = fit_predict(mname, X[tr], up[tr], X[te_all], d[tr], rng, S[tr], S[te_all])
            hit_te = hit[te_all]
            a = auc(up[te_all][hit_te] == 1, p_all[hit_te])
            net_bp = float("nan"); ntr = 0
            if mname in prev_pred:
                lo, hi = np.quantile(prev_pred[mname], [0.10, 0.90])
                sig = np.where(p_all >= hi, 1, np.where(p_all <= lo, -1, 0))
                td, tn = simulate(sig, d[te_all], net[te_all])
                if len(tn):
                    net_bp, ntr = float(tn.mean()), len(tn)
                    res[mname].setdefault("trades", []).append((td, tn))
            prev_pred[mname] = p_all
            res[mname][Y] = (a, net_bp, ntr)
            out_rows.append(dict(model=mname, year=Y, auc=a, net_bp=net_bp, trades=ntr))
            print(f"    {Y} {mname:<7} AUC {a:.4f}  trades {ntr:>4}  net {net_bp:+.2f}", flush=True)
    return res


def run_meta(here):
    import lightgbm as lgb
    z = np.load(os.path.join(here, "../data/timeline_v37/matrix.npz")); m = np.load(os.path.join(here, "../data/v39/meta.npz"))
    X = z["X"][m["row"]]
    side = m["side"].astype(float)[:, None]
    Xm = np.hstack([X, side])                       # the model knows the trade's side
    d, g, n = m["date"], m["gross"], m["net"]
    y = (g > 0).astype(int)
    keep_all, base_all, dd_all = [], [], []
    prev = None
    for Y in YEARS:
        tr = d < f"{Y}-01-01"; te = (d >= f"{Y}-01-01") & (d <= f"{Y}-12-31")
        if te.sum() < 30 or tr.sum() < 500:
            continue
        cut = np.sort(np.unique(d[tr]))[-126]
        core, inner = tr & (d < cut), tr & (d >= cut)
        mdl = lgb.train(PARAMS, lgb.Dataset(Xm[core], y[core]), 1500, valid_sets=[lgb.Dataset(Xm[inner], y[inner])],
                        callbacks=[lgb.early_stopping(60, verbose=False)])
        p = mdl.predict(Xm[te], num_iteration=mdl.best_iteration)
        if prev is not None:
            thr = np.quantile(prev, 1 - META_KEEP)
            k = p >= thr
            keep_all.append(np.where(k, n[te], np.nan)); base_all.append(n[te]); dd_all.append(d[te])
            print(f"    {Y} meta: trades {te.sum():>4}  kept {k.sum():>4}  all net {n[te].mean():+.2f}  kept net {n[te][k].mean():+.2f}"
                  f"  AUC(win) {auc(y[te] == 1, p):.3f}", flush=True)
        prev = p
    kept = np.concatenate(keep_all); base = np.concatenate(base_all); dd = np.concatenate(dd_all)
    return kept, base, dd


def self_test():
    ok = True
    def check(n, c, dtl=""):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n} {dtl}")
    print(f"v39_models.py v{VERSION} self-test\n")
    rng = np.random.default_rng(1)
    n = 6000
    X = rng.normal(0, 1, (n, 30)).astype(np.float32)
    y = (X[:, 0] + X[:, 1] * X[:, 2] + rng.normal(0, 1.5, n) > 0).astype(int)
    import datetime as _dt
    d = np.array([(_dt.date(2010, 1, 1) + _dt.timedelta(days=i // 3)).isoformat() for i in range(n)])
    S = rng.normal(0, 1, (n, 24)).astype(np.float32); S[:, 0] += 2 * (y - 0.5)
    tr, te = np.arange(n) < 4500, np.arange(n) >= 4500
    for m in ["LGBM", "LOGIT", "FOREST", "RULES", "KNN-EV", "KNN-SH"]:
        p = fit_predict(m, X[tr], y[tr], X[te], d[tr], rng, S[tr], S[te])
        check(f"{m} finds a planted signal", auc(y[te] == 1, p) > 0.6, f"AUC {auc(y[te] == 1, p):.3f}")
    p = fit_predict("NULL", X[tr], y[tr], X[te], d[tr], rng)
    check("PLANTED FAIL: the NULL model (day-shifted labels) does not", auc(y[te] == 1, p) < 0.56, f"AUC {auc(y[te] == 1, p):.3f}")
    yr = rng.integers(0, 2, n)
    p = fit_predict("FOREST", X[tr], yr[tr], X[te], d[tr], rng)
    check("PLANTED FAIL: a forest on random labels scores ~0.5", abs(auc(yr[te] == 1, p) - 0.5) < 0.05, f"AUC {auc(yr[te] == 1, p):.3f}")
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--part", choices=["models", "meta", "all"], default="all")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    here = os.path.dirname(os.path.abspath(__file__))
    print(f"v39_models.py v{VERSION}   PREREGISTRATION_v39\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    got = hashlib.sha256(open(os.path.join(here, "..", DOC[0]), "rb").read()).hexdigest()
    if got != DOC[1]:
        print("  PREREGISTRATION_v39.md changed since frozen. Refused."); sys.exit(2)
    if a.part in ("models", "all"):
        rows = []
        res = run_models(here, rows)
        import csv
        with open(os.path.join(here, "../data/v39/model_years.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        print("\n  SUMMARY 2012-2026 (direction AUC by year; trades from 2013, net of spread)")
        null = np.array([res["NULL"][Y][0] for Y in YEARS if Y in res["NULL"]])
        ref = null.mean() + 2 * null.std(ddof=1) / math.sqrt(len(null))
        best = None
        for mname in MODELS:
            aucs = np.array([res[mname][Y][0] for Y in YEARS if Y in res[mname]])
            wins = int((aucs > 0.5).sum())
            tr = res[mname].get("trades", [])
            if tr:
                td = np.concatenate([t[0] for t in tr]); tn = np.concatenate([t[1] for t in tr]); mu, t = cl_t(td, tn)
            else:
                mu, t, tn = float("nan"), float("nan"), []
            elig = mname != "NULL" and wins >= MIN_WIN_YEARS and aucs.mean() > ref
            print(f"    {mname:<7} mean AUC {aucs.mean():.4f}  years > 0.5: {wins:>2}/{len(aucs)}  trades {len(tn):>5} net {mu:+.2f} bp t {t:+.2f}"
                  f"   {'ELIGIBLE' if elig else ''}")
            if elig and (best is None or aucs.mean() > best[1]):
                best = (mname, aucs.mean())
        print(f"    NULL reference: mean + 2 SE = {ref:.4f}")
        print(f"\n  WINNER (frozen rule): {best[0] if best else 'NONE -- no model is eligible'}")
    if a.part in ("meta", "all"):
        print("\n  PART M -- meta-labelling the v36 noise-band trades (keep the top 60% by predicted win chance)")
        kept, base, dd = run_meta(here)
        k = ~np.isnan(kept)
        mu_b, t_b = cl_t(dd, base); mu_k, t_k = cl_t(dd[k], kept[k])
        # paired: per-trade difference between the filtered book (0 for dropped trades) and trading everything
        pd_ = np.where(k, 0.0, -base)                  # dropping a trade changes P&L by -its net
        mu_d, t_d = cl_t(dd, pd_)
        print(f"    all trades   {len(base):>5}  net {mu_b:+.2f} bp/trade  t {t_b:+.2f}")
        print(f"    kept trades  {k.sum():>5}  net {mu_k:+.2f} bp/trade  t {t_k:+.2f}")
        print(f"    value of the filter (P&L gained by dropping trades, per trade offered) {mu_d:+.2f} bp  t {t_d:+.2f}"
              f"   -> M {'PASS' if (mu_d > 0 and t_d >= 2.0 and mu_k > 0 and t_k >= 2.0) else 'FAIL'}")


if __name__ == "__main__":
    main()
