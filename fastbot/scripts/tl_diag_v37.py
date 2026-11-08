"""DIAGNOSTIC of the VOIDED v37 fit (validation only; the sealed rows are never loaded).
Question: is AUC 0.70 leakage, or is the label mixing 'a big move happens' with 'which way'?"""
import pickle, numpy as np, lightgbm as lgb
from timeline_v37 import auc, SEALED_START, VAL_START
z = np.load("../data/timeline_v37/matrix.npz"); d = z["date"]; keep = d < SEALED_START
X, yl, ys, names = z["X"][keep], z["yl"][keep], z["ys"][keep], list(z["names"]); d = d[keep]
val = d >= VAL_START
L = pickle.load(open("../data/timeline_v37/LOCK.pkl", "rb"))
pl = lgb.Booster(model_str=L["models"]["LONG"]).predict(X[val]); ps = lgb.Booster(model_str=L["models"]["SHORT"]).predict(X[val])
vl, vs = yl[val] == 1, ys[val] == 1
hit = vl | vs
print(f"validation: long AUC {auc(vl, pl):.3f}  short AUC {auc(vs, ps):.3f}")
print(f"  corr(p_long, p_short) = {np.corrcoef(pl, ps)[0,1]:+.3f}   (a direction model would be NEGATIVE)")
print(f"  p_long predicting 'ANY barrier hit' AUC {auc(hit, pl):.3f};  p_short: {auc(hit, ps):.3f}")
print(f"  p_long predicting the SHORT label   AUC {auc(vs, pl):.3f}   (direction would give < 0.5)")
print(f"  DIRECTION among points where a barrier was hit (n {hit.sum()}):")
print(f"    AUC of p_long - p_short for 'up first' {auc(vl[hit], (pl - ps)[hit]):.3f}")
print(f"    AUC of p_long alone                   {auc(vl[hit], pl[hit]):.3f}")
for n in ("rv_ratio", "sigma2h_bp", "vix_chg5", "vx_ratio"):
    x = X[val][:, names.index(n)]; ok = ~np.isnan(x)
    print(f"  {n:<11} alone: AUC for any-hit {auc(hit[ok], x[ok]):.3f}   for up-first|hit {auc(vl[hit & ok], x[hit & ok]):.3f}")
