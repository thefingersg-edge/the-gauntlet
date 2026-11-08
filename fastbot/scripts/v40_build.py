"""v40: build the v37 timeline (tl_build2, US-identical by Gate 0) for each
unseen index in its own cash session. Writes data/v40/<stem>.npz."""
import sys, os, time, numpy as np
import tl_build2 as T2, tl_build as T1, noise_v38 as N
stem = sys.argv[1]; here = os.getcwd(); t = time.time()
tz, o, c = N.SESS[stem]
days = N.load("../data/v38", stem)
rows, feats, ev = T2.build("../data", here, days=days, sess=T2.Session(tz, o, c), verbose=False)
names = [f"ms_{e}" for e in T1.EVENTS] + [f"n60_{e}" for e in T1.INTRADAY] + T1.STATES
X = np.array([[np.nan if f.get(n) is None else f[n] for n in names] for f in feats], dtype=np.float32)
np.savez_compressed(f"../data/v40/{stem}.npz", X=X, names=np.array(names),
    date=np.array([r["date"].isoformat() for r in rows]), hm=np.array([r["hm"] for r in rows]),
    yl=np.array([r["yl"] for r in rows], np.int8), ys=np.array([r["ys"] for r in rows], np.int8),
    gl=np.array([r["gl"] for r in rows], np.float32), gs=np.array([r["gs"] for r in rows], np.float32),
    b_bp=np.array([r["b_bp"] for r in rows], np.float32), spread=np.array([r["spread"] for r in rows], np.float32))
print(stem, len(days), "sessions", len(rows), "decision points", len(ev), "events", f"{time.time()-t:.0f}s")
