"""v41: NAS100 v37 timeline (US session) from the historical 5m files -- for thresholds only."""
import numpy as np, os, time
import tl_build2 as T2, tl_build as T1
from reactive import load
t = time.time()
days = load("../data", "nas100usd")
rows, feats, ev = T2.build("../data", os.getcwd(), days=days, verbose=False)
names = [f"ms_{e}" for e in T1.EVENTS] + [f"n60_{e}" for e in T1.INTRADAY] + T1.STATES
X = np.array([[np.nan if f.get(n) is None else f[n] for n in names] for f in feats], dtype=np.float32)
np.savez_compressed("../data/v41/nas100_hist.npz", X=X, names=np.array(names),
    date=np.array([r["date"].isoformat() for r in rows]), hm=np.array([r["hm"] for r in rows]))
print(len(rows), "rows", f"{time.time()-t:.0f}s")
