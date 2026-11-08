#!/usr/bin/env python3
"""v39 CHECK 1 (descriptive, gates nothing) -- is the random forest's 0.555 a
plateau or a spike? Same data, labels and yearly walk-forward as v39 Part A;
only min_samples_leaf and max_depth vary. The frozen v39 FOREST
(leaf 200, depth unlimited) is NOT changed by anything printed here.
Also saves that frozen config's out-of-sample predictions for the exit review."""
import csv, os, numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from timeline_v37 import auc

LEAVES, DEPTHS, YEARS = (50, 100, 200, 500), (6, 10, None), range(2012, 2027)
z = np.load("../data/timeline_v37/matrix.npz"); d, X = z["date"], z["X"]
hit = (z["yl"] == 1) | (z["ys"] == 1); up = (z["yl"] == 1).astype(int)
import time, sys
T0, BUDGET = time.time(), float(sys.argv[1]) if len(sys.argv) > 1 else 1e9
PC, PP = "../data/v39/plateau.csv", "../data/v39/forest_oos_pred.npy"
done = set()
if os.path.exists(PC):
    done = {(r["leaf"], r["depth"] or "None", r["year"]) for r in csv.DictReader(open(PC))}
pred = np.load(PP) if os.path.exists(PP) else np.full(len(d), np.nan, np.float32)
new = not os.path.exists(PC)
out = open(PC, "a", newline=""); w = csv.writer(out)
if new: w.writerow(["leaf", "depth", "year", "auc"])
for leaf in LEAVES:
    for depth in DEPTHS:
        aucs = []
        for Y in YEARS:
            if (str(leaf), str(depth), str(Y)) in done:
                continue
            if time.time() - T0 > BUDGET:
                np.save(PP, pred); print("paused", flush=True); sys.exit(0)
            tr = hit & (d < f"{Y}-01-01"); te_all = (d >= f"{Y}-01-01") & (d <= f"{Y}-12-31") & (d <= "2026-09-17")
            m = make_pipeline(SimpleImputer(strategy="median"),
                              RandomForestClassifier(300, min_samples_leaf=leaf, max_depth=depth, max_features="sqrt", n_jobs=4, random_state=7))
            m.fit(X[tr], up[tr])
            p = m.predict_proba(X[te_all])[:, 1]
            h = hit[te_all]; a = auc(up[te_all][h] == 1, p[h]); aucs.append(a)
            w.writerow([leaf, str(depth), Y, f"{a:.5f}"]); out.flush()
            if leaf == 200 and depth is None:
                pred[te_all] = p; np.save(PP, pred)
        if not aucs:
            continue
        a = np.array(aucs)
        print(f"leaf {leaf:>3} depth {str(depth):>4}: mean AUC {a.mean():.4f}  years>0.5 {(a > 0.5).sum()}/15  min {a.min():.3f}", flush=True)
np.save(PP, pred)
print("done")
