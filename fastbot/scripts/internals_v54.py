#!/usr/bin/env python3
"""PREREGISTRATION_v54 -- do market internals (put/call, VIX/VIX3M, S&P breadth,
NYSE advance/decline) add direction information to the v37 event timeline?

FOREST (the frozen v39/v40 recipe) is trained on SPX500 ONLY, yearly
walk-forward, twice with the same seed: BASE on the 125 original features and
AUG on those plus the 20 internals features (tl_build3). Both predict US30 and
NAS100 -- markets no timeline model has been fitted or scored on -- in each
test year. The question is the paired difference AUG - BASE.

    python3 internals_v54.py --self-test
    python3 internals_v54.py --stage predict [--budget 160]   # resumable
    python3 internals_v54.py --stage test                     # once
"""
import argparse, datetime as dt, hashlib, math, os, sys, time
import numpy as np

VERSION = "1.0"
DOC = "../PREREGISTRATION_v54.md"
DOC_SHA = "fb8718bbc3355f220fdf142638a1f4e93efef86833a7322a10c302c8c98b3f10"                         # pinned in the freezing commit
D = "../data/v54"
TRAIN = "spx500usd"
TEST = ("us30usd", "nas100usd")
YEARS = range(2013, 2027)
END = "2026-08-14"                          # last date of the v37 SPX matrix
ERAS = ((2013, 2017), (2018, 2021), (2022, 2026))
N_BASE, N_BOOT = 125, 1000


def forest():
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import make_pipeline
    return make_pipeline(SimpleImputer(strategy="median"),
                         RandomForestClassifier(300, min_samples_leaf=200, max_features="sqrt", n_jobs=4, random_state=7))


def auc(y, p):
    from scipy.stats import rankdata                     # average ranks for ties (Mann-Whitney)
    y = np.asarray(y, bool); r = rankdata(p)
    n1, n0 = y.sum(), (~y).sum()
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def cl_t(dates, x):
    ud, inv = np.unique(dates, return_inverse=True); mu = x.mean()
    s = np.bincount(inv, weights=x - mu); G = len(ud)
    se = math.sqrt((s ** 2).sum() * G / (G - 1)) / len(x)
    return mu, mu / se


def load(stem):
    return dict(np.load(f"{D}/{stem}.npz"))


def stage_predict(budget):
    t0 = time.time()
    S = load(TRAIN)
    hitS = (S["yl"] == 1) | (S["ys"] == 1)
    M = {s: load(s) for s in TEST + (TRAIN,)}
    for s in M:
        assert list(M[s]["names"]) == list(S["names"]), f"{s}: feature names differ"
    pf = lambda s, k: f"{D}/pred_{k}_{s}.npy"
    P = {(s, k): (np.load(pf(s, k)) if os.path.exists(pf(s, k)) else np.full(len(M[s]["date"]), np.nan, np.float32))
         for s in M for k in ("base", "aug")}
    for Y in YEARS:
        sel = {s: (M[s]["date"] >= f"{Y}-01-01") & (M[s]["date"] <= f"{Y}-12-31") & (M[s]["date"] <= END) for s in M}
        if not any(np.isnan(P[(s, k)][sel[s]]).any() for s in M for k in ("base", "aug")):
            continue
        if time.time() - t0 > budget:
            print("paused (budget)"); return
        tr = hitS & (S["date"] < f"{Y}-01-01")
        y = (S["yl"][tr] == 1).astype(int)
        for k, cols in (("base", slice(0, N_BASE)), ("aug", slice(None))):
            m = forest().fit(S["X"][tr][:, cols], y)
            for s in M:
                if sel[s].any():
                    P[(s, k)][sel[s]] = m.predict_proba(M[s]["X"][sel[s]][:, cols])[:, 1]
                np.save(pf(s, k), P[(s, k)])
        print(f"  {Y} done ({time.time() - t0:.0f}s)", flush=True)
    print("all predictions written")


def paired_boot(Y, Pb, Pa, D_, rng, n=N_BOOT):
    ud, inv = np.unique(D_, return_inverse=True)
    groups = [np.where(inv == i)[0] for i in range(len(ud))]
    out = []
    for _ in range(n):
        ix = np.concatenate([groups[i] for i in rng.integers(0, len(ud), len(ud))])
        out.append(auc(Y[ix], Pa[ix]) - auc(Y[ix], Pb[ix]))
    return np.array(out)


def stage_test():
    rng = np.random.default_rng(54)
    Ys, Pbs, Pas, Ds, per = [], [], [], [], {}
    print("  AUC on hit points, 2013-01-01 .. 2026-08-14 (train: SPX only, yearly walk-forward)\n")
    for s in TEST + (TRAIN,):
        M = load(s)
        Pb, Pa = np.load(f"{D}/pred_base_{s}.npy"), np.load(f"{D}/pred_aug_{s}.npy")
        hit = (M["yl"] == 1) | (M["ys"] == 1)
        g = hit & (M["date"] >= "2013-01-01") & (M["date"] <= END) & np.isfinite(Pb) & np.isfinite(Pa)
        y = M["yl"][g] == 1
        ab, aa = auc(y, Pb[g]), auc(y, Pa[g])
        tag = "  (SPX: the training market, walk-forward; descriptive)" if s == TRAIN else ""
        print(f"    {s:<10} n {g.sum():>6,}  BASE {ab:.4f}  AUG {aa:.4f}  diff {aa - ab:+.4f}{tag}")
        if s in TEST:
            Ys.append(y); Pbs.append(Pb[g]); Pas.append(Pa[g]); Ds.append(M["date"][g])
            per[s] = aa - ab
    Y, Pb, Pa, Dd = np.concatenate(Ys), np.concatenate(Pbs), np.concatenate(Pas), np.concatenate(Ds)
    d0 = auc(Y, Pa) - auc(Y, Pb)
    bt = paired_boot(Y, Pb, Pa, Dd, rng)
    lo = float(np.quantile(bt, 0.025))
    print(f"\n    POOLED US30+NAS100  BASE {auc(Y, Pb):.4f}  AUG {auc(Y, Pa):.4f}  diff {d0:+.4f}"
          f"  day-bootstrap 95% CI [{lo:+.4f}, {float(np.quantile(bt, 0.975)):+.4f}]")
    yrs = np.array([int(x[:4]) for x in Dd])
    eras = []
    for a, b in ERAS:
        m = (yrs >= a) & (yrs <= b)
        eras.append(auc(Y[m], Pa[m]) - auc(Y[m], Pb[m]))
    print("    eras (AUG - BASE): " + "   ".join(f"{a}-{b} {e:+.4f}" for (a, b), e in zip(ERAS, eras)))
    g1 = lo > 0
    g2 = all(v > 0 for v in per.values()) and all(e > 0 for e in eras)
    print(f"\n  G1  pooled diff, day-bootstrap 95% lower bound > 0          : {'PASS' if g1 else 'FAIL'} ({lo:+.4f})")
    print(f"  G2  diff > 0 on each market AND in each era                : {'PASS' if g2 else 'FAIL'}"
          f"  (US30 {per['us30usd']:+.4f}, NAS100 {per['nas100usd']:+.4f})")
    print(f"\n  VERDICT: {'PASS' if (g1 and g2) else 'FAIL'}")
    # reported, gating nothing: BASE alone on two more unseen markets (a v40-style check)
    bb = []
    ud, inv = np.unique(Dd, return_inverse=True); groups = [np.where(inv == i)[0] for i in range(len(ud))]
    for _ in range(N_BOOT):
        ix = np.concatenate([groups[i] for i in rng.integers(0, len(ud), len(ud))]); bb.append(auc(Y[ix], Pb[ix]))
    print(f"\n  reported  BASE pooled AUC on US30+NAS100 {auc(Y, Pb):.4f}, day-bootstrap 95% lower {np.quantile(bb, 0.025):.4f}"
          f"  (v40 found 0.512 on five non-US markets)")
    try:
        S = load(TRAIN); hitS = (S["yl"] == 1) | (S["ys"] == 1)
        tr = hitS & (S["date"] < "2026-01-01")
        m = forest().fit(S["X"][tr], (S["yl"][tr] == 1).astype(int))
        imp = m[-1].feature_importances_; names = list(S["names"])
        order = np.argsort(-imp)
        rank = {names[i]: r + 1 for r, i in enumerate(order)}
        newn = names[N_BASE:]
        print("  reported  AUG importance rank of the 20 new features (of 145): " +
              ", ".join(f"{n} {rank[n]}" for n in sorted(newn, key=lambda n: rank[n])))
        print(f"            their share of total importance {imp[N_BASE:].sum():.3f} (equal share would be {20 / 145:.3f})")
    except Exception as e:                                           # noqa: BLE001
        print(f"  reported  importance: not computed ({e})")


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"internals_v54.py v{VERSION} self-test\n")
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 5000).astype(bool)
    p = rng.normal(size=5000) + 0.5 * y
    check("auc of a planted signal is well above 0.5 and auc of noise is near 0.5",
          auc(y, p) > 0.6 and abs(auc(y, rng.normal(size=5000)) - 0.5) < 0.03)
    check("auc handles ties like the rank-sum definition", abs(auc(np.array([1, 0, 1, 0], bool), np.array([1, 1, 0, 0.])) - 0.5) < 1e-12)
    dates = np.array([f"2020-01-{1 + i % 28:02d}" for i in range(5000)])
    bt = paired_boot(y, p, p, dates, rng, 50)
    check("PLANTED: identical BASE and AUG give a paired difference of exactly 0", np.all(bt == 0))
    pa = p + 0.4 * (y - 0.5)
    bt = paired_boot(y, p, pa, dates, rng, 200)
    check("PLANTED: a genuinely better AUG gives a bootstrap lower bound > 0", np.quantile(bt, 0.025) > 0)
    check("the base block is the first 125 columns, matching tl_build3", N_BASE == 125)
    try:
        import tl_build3 as T3
        check("tl_build3 NAMES = 125 base + 20 new", len(T3.NAMES) == 145 and T3.NAMES[:125] == T3.BASE_NAMES)
    except ImportError:
        check("tl_build3 importable", False)
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["predict", "test"]); ap.add_argument("--budget", type=float, default=160)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    got = hashlib.sha256(open(DOC, "rb").read()).hexdigest()
    if got != DOC_SHA:
        print(f"{DOC} changed since frozen ({got[:12]}). Refused."); sys.exit(2)
    print(f"internals_v54.py v{VERSION}  stage {a.stage}\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    stage_predict(a.budget) if a.stage == "predict" else stage_test()


if __name__ == "__main__":
    main()
