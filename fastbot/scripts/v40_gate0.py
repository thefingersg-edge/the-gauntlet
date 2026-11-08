import numpy as np, os, time, sys
import tl_build2 as T2, tl_build as T1
here=os.getcwd(); t=time.time(); N=int(sys.argv[1])
rows, feats, ev = T2.build("../data", here, limit_days=N, verbose=False)
print("built", len(rows), f"{time.time()-t:.0f}s", flush=True)
names=[f"ms_{e}" for e in T1.EVENTS]+[f"n60_{e}" for e in T1.INTRADAY]+T1.STATES
X=np.array([[np.nan if f.get(n) is None else f[n] for n in names] for f in feats],dtype=np.float32)
z=dict(np.load("../data/timeline_v37/matrix.npz")); n=len(rows)
same_keys = all(z["date"][i]==r["date"].isoformat() and z["hm"][i]==r["hm"] for i,r in enumerate(rows))
Xo=z["X"][:n]; eq=np.array_equal(np.isnan(X),np.isnan(Xo)) and float(np.nanmax(np.abs(np.nan_to_num(X)-np.nan_to_num(Xo))))==0.0
lab=all(z["yl"][i]==r["yl"] and z["ys"][i]==r["ys"] and abs(z["gl"][i]-r["gl"])<1e-4 for i,r in enumerate(rows))
print("GATE 0 (tl_build2 US == tl_build 1.1):", n, "rows  keys", same_keys, " features identical", eq, " labels", lab, f"{time.time()-t:.0f}s")
