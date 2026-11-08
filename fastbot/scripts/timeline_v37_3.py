#!/usr/bin/env python3
"""PREREGISTRATION_v37.3 -- does the timeline predict direction better when
trained on the RECENT world instead of the old one?

PART A (Dave's post-COVID question)
  NEW  model: trained 2022-01-01..2024-02-29, early-stopped on 2024-03-01..2024-08-14
  OLD  model: the v37.2 LOCK (trained 2005-2012) -- unchanged
  ALL  model: trained 2005-01-01..2024-02-29, same early-stop slice (reported)
  TEST window 2024-08-15..2026-08-14: two years the NEW model never saw.
  A1  NEW test AUC above all 20 day-shift nulls (NEW recipe, shifted labels)
  A2  NEW minus OLD test AUC > 0 with a day-bootstrap 95% interval above 0
  A3  reported: NEW trades (q90/q10 of its early-stop-slice predictions), net

PART B (is "train on recent" a real effect or luck?) -- 8 rolling windows
  RECENT = the 3 years before the test window; ALL-PRIOR = 2005 up to the same
  point; both early-stopped on the last 6 months of their training span;
  test = the next 2 years.
  B   RECENT beats ALL-PRIOR in >= 6 of 8 windows AND the mean AUC gain
      across windows has t >= 2.0.

Direction-only labels (v37.1): up-first vs down-first among points where a
barrier was hit. Features: data/timeline_v37/matrix.npz (tl_build 1.1).
"""
from __future__ import annotations

import argparse, hashlib, os, pickle, sys
import numpy as np

import timeline_v37_1 as V1
from timeline_v37 import auc, simulate, cl_t, MAT, N_PERM, AUC_VOID

VERSION = "1.0"
DOC = ("PREREGISTRATION_v37.3.md", "0bb2bd25a7111a565096249a3564d33889a89d937902c0e5fd79c8a0cebefb61")
MATRIX_SHA = "6fc354b289c94cbf28b018e5f233e22d949c1f23cc6aeff3bc88aced09ce2088"
OLD_LOCK = ("../data/timeline_v37/LOCK_v37_2.pkl",
            "fb2f89ae2b8ec8b7fa53a076cf4977626cc6949dd43288ac25697ddef267f4dc")
A = dict(core=("2022-01-01", "2024-02-29"), inner=("2024-03-01", "2024-08-14"),
         test=("2024-08-15", "2026-08-14"))
WINDOWS = [(2007, 2009), (2009, 2011), (2011, 2013), (2013, 2015),
           (2015, 2017), (2017, 2019), (2019, 2021), (2021, 2023)]   # recent 3y; test next 2y
N_BOOT = 1000
B_MIN_WINS, B_T = 6, 2.0


def rng_mask(d, lo, hi):
    return (d >= lo) & (d <= hi)


def boot_diff(y, p_new, p_old, days, rng):
    ud, inv = np.unique(days, return_inverse=True)
    groups = [np.where(inv == i)[0] for i in range(len(ud))]
    out = []
    for _ in range(N_BOOT):
        pick = rng.integers(0, len(ud), len(ud))
        ix = np.concatenate([groups[i] for i in pick])
        out.append(auc(y[ix], p_new[ix]) - auc(y[ix], p_old[ix]))
    return np.quantile(out, [0.025, 0.975])


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"timeline_v37_3.py v{VERSION} self-test\n")
    rng = np.random.default_rng(4)
    days = np.repeat(np.arange(400), 10); y = rng.random(4000) < 0.47
    good = y + rng.normal(0, 2, 4000); bad = rng.random(4000)
    lo, hi = boot_diff(y, good, bad, days, rng)
    check("a better model's AUC gain has an interval above 0", lo > 0)
    global N_BOOT
    keep, N_BOOT, fp = N_BOOT, 200, 0
    for _ in range(60):
        yy = rng.random(4000) < 0.47
        fp += boot_diff(yy, rng.random(4000), rng.random(4000), days, rng)[0] > 0
    N_BOOT = keep
    check(f"PLANTED FAIL, 60 times: noise vs noise passes the A2 rule {fp}/60 times (must be <= 5)", fp <= 5)
    check("Part A test window starts after the NEW model's last training day",
          A["test"][0] > A["inner"][1] > A["core"][1])
    check("every Part B test window starts after its training span",
          all(f"{hi + 1}-01-01" > f"{hi}-12-31" for lo, hi in WINDOWS))
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def run(here):
    import lightgbm as lgb
    for path, want in ((os.path.join(here, "..", DOC[0]), DOC[1]), (os.path.join(here, MAT), MATRIX_SHA),
                       (os.path.join(here, OLD_LOCK[0]), OLD_LOCK[1])):
        if hashlib.sha256(open(path, "rb").read()).hexdigest() != want:
            print(f"  {os.path.basename(path)} does not match its frozen sha. Refused."); sys.exit(2)
    print("  PREREGISTRATION_v37.3, matrix.npz and the v37.2 LOCK match their frozen sha256\n")
    z = np.load(os.path.join(here, MAT)); d = z["date"]; X = z["X"]; names = list(z["names"])
    yl, ys = z["yl"] == 1, z["ys"] == 1
    hit = yl | ys; up = yl.astype(int)
    net = np.column_stack([z["gl"] - z["spread"], z["gs"] - z["spread"]])
    rng = np.random.default_rng(37)

    # ------------------------------------------------------------ PART A
    print("  PART A -- post-COVID training, test 2024-08-15 .. 2026-08-14 (never seen by the NEW model)")
    core = rng_mask(d, *A["core"]) & hit; inner = rng_mask(d, *A["inner"]) & hit
    t_all = rng_mask(d, *A["test"]); t_hit = t_all & hit
    newm = V1.fit_dir(lgb, X, up, core, inner)
    allcore = rng_mask(d, "2005-01-01", A["core"][1]) & hit
    allm = V1.fit_dir(lgb, X, up, allcore, inner)
    oldm = lgb.Booster(model_str=pickle.loads(open(os.path.join(here, OLD_LOCK[0]), "rb").read())["model"])
    pn, po, pa = (m.predict(X[t_hit]) if m is oldm else m.predict(X[t_hit], num_iteration=m.best_iteration)
                  for m in (newm, oldm, allm))
    yt = up[t_hit] == 1
    a_new, a_old, a_all = auc(yt, pn), auc(yt, po), auc(yt, pa)
    print(f"    train points (hit): NEW core {core.sum():,}  inner {inner.sum():,}   ALL core {allcore.sum():,}")
    print(f"    test hit points {t_hit.sum():,} on {len(np.unique(d[t_hit]))} days")
    null = []
    idx = np.where(core | inner)[0]
    for k in range(N_PERM):
        yp = up.astype(np.int8).copy()
        yp[idx] = V1.day_shift2(up[idx].astype(np.int8), d[idx], rng)
        mn = V1.fit_dir(lgb, X, yp, core, inner)
        null.append(auc(yt, mn.predict(X[t_hit], num_iteration=mn.best_iteration)))
    null = np.array(null)
    a1 = a_new > null.max() and a_new < AUC_VOID
    lo, hi = boot_diff(yt, pn, po, d[t_hit], rng)
    a2 = (a_new - a_old) > 0 and lo > 0
    lo3, hi3 = boot_diff(yt, pa, po, d[t_hit], rng)
    print(f"    test direction AUC   NEW (2022-24) {a_new:.4f}   OLD (2005-12) {a_old:.4f}   ALL (2005-24) {a_all:.4f}")
    print(f"    A1 NEW vs 20 day-shift nulls: null mean {null.mean():.4f} max {null.max():.4f}  -> {'PASS' if a1 else 'FAIL'}")
    print(f"    A2 NEW - OLD = {a_new - a_old:+.4f}  day-bootstrap 95% [{lo:+.4f}, {hi:+.4f}]  -> {'PASS' if a2 else 'FAIL'}")
    print(f"       (reported) ALL - OLD = {a_all - a_old:+.4f}  95% [{lo3:+.4f}, {hi3:+.4f}]")
    pin = newm.predict(X[rng_mask(d, *A["inner"])], num_iteration=newm.best_iteration)
    thr = np.quantile(pin, [0.10, 0.90])
    p_t = newm.predict(X[t_all], num_iteration=newm.best_iteration)
    sig = np.where(p_t >= thr[1], 1, np.where(p_t <= thr[0], -1, 0))
    td, tn = simulate(sig, d[t_all], net[t_all])
    mu, t = cl_t(td, tn)
    print(f"    A3 (reported) NEW model trades on the test window: {len(tn)} trades, net {mu:+.2f} bp, t {t:+.2f}")
    imp = sorted(zip(newm.feature_importance("gain"), names), reverse=True)[:10]
    print("    NEW model top features: " + ", ".join(n for _, n in imp))

    # ------------------------------------------------------------ PART B
    print("\n  PART B -- rolling eras: RECENT 3 years vs ALL PRIOR history, tested on the next 2 years")
    print(f"    {'train (recent)':<16}{'test':<12}{'n test':>8}{'RECENT':>9}{'ALL-PRIOR':>11}{'gain':>9}{'95% CI':>20}")
    gains = []
    for lo_y, hi_y in WINDOWS:
        te = rng_mask(d, f"{hi_y + 1}-01-01", f"{hi_y + 2}-12-31") & hit
        inn = rng_mask(d, f"{hi_y}-07-01", f"{hi_y}-12-31") & hit
        rc = rng_mask(d, f"{lo_y}-01-01", f"{hi_y}-06-30") & hit
        ap = rng_mask(d, "2005-01-01", f"{hi_y}-06-30") & hit
        mr = V1.fit_dir(lgb, X, up, rc, inn); ma = V1.fit_dir(lgb, X, up, ap, inn)
        pr = mr.predict(X[te], num_iteration=mr.best_iteration); pa_ = ma.predict(X[te], num_iteration=ma.best_iteration)
        y_ = up[te] == 1
        ar, aa = auc(y_, pr), auc(y_, pa_)
        l_, h_ = boot_diff(y_, pr, pa_, d[te], rng)
        gains.append(ar - aa)
        print(f"    {lo_y}-{hi_y:<11}{hi_y + 1}-{str(hi_y + 2)[2:]:<7}{te.sum():>8}{ar:>9.4f}{aa:>11.4f}{ar - aa:>+9.4f}   [{l_:+.4f}, {h_:+.4f}]")
    g = np.array(gains)
    wins = int((g > 0).sum()); tb = g.mean() / (g.std(ddof=1) / np.sqrt(len(g)))
    bpass = wins >= B_MIN_WINS and tb >= B_T
    print(f"    RECENT beats ALL-PRIOR in {wins} of {len(g)} windows; mean gain {g.mean():+.4f}, t {tb:+.2f}  -> B {'PASS' if bpass else 'FAIL'}")
    print(f"\n  VERDICTS  A1 {'PASS' if a1 else 'FAIL'}   A2 {'PASS' if a2 else 'FAIL'}   B {'PASS' if bpass else 'FAIL'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    print(f"timeline_v37_3.py v{VERSION}   PREREGISTRATION_v37.3\n")
    print("  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    run(os.path.dirname(os.path.abspath(__file__)))


if __name__ == "__main__":
    main()
