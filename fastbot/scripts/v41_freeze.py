"""v41: train the frozen model M (v39 FOREST recipe) on SPX hit points dated
before 2026-01-01, and derive each instrument's thresholds from M's
out-of-sample predictions on 2026-01-01..2026-08-14. Writes data/v41/."""
import numpy as np, pickle, hashlib, json
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
import sklearn
S = dict(np.load("../data/timeline_v37/matrix.npz")); N = dict(np.load("../data/v41/nas100_hist.npz"))
assert list(S["names"]) == list(N["names"])
hit = (S["yl"] == 1) | (S["ys"] == 1); tr = hit & (S["date"] < "2026-01-01")
M = make_pipeline(SimpleImputer(strategy="median"),
                  RandomForestClassifier(300, min_samples_leaf=200, max_features="sqrt", n_jobs=4, random_state=7))
M.fit(S["X"][tr], (S["yl"][tr] == 1).astype(int))
blob = pickle.dumps(M); open("../data/v41/forest_v41.pkl", "wb").write(blob)
thr = {}
for nm, Z in (("SPX500_USD", S), ("NAS100_USD", N)):
    sel = (Z["date"] >= "2026-01-01") & (Z["date"] <= "2026-08-14")
    p = M.predict_proba(Z["X"][sel])[:, 1]
    thr[nm] = dict(lo=float(np.quantile(p, 0.10)), hi=float(np.quantile(p, 0.90)), n=int(sel.sum()))
check = M.predict_proba(S["X"][:2000])[:, 1]
out = dict(sklearn=sklearn.__version__, train_rows=int(tr.sum()), thresholds=thr,
           model_sha256=hashlib.sha256(blob).hexdigest(),
           check_pred_sha256=hashlib.sha256(np.round(check, 10).tobytes()).hexdigest(),
           matrix_sha256="6fc354b289c94cbf28b018e5f233e22d949c1f23cc6aeff3bc88aced09ce2088")
json.dump(out, open("../data/v41/freeze_v41.json", "w"), indent=1)
print(json.dumps(out, indent=1))
