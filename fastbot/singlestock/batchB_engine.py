"""Fast per-ticker event study for Batch B (and reusable): closing-auction execution, rolling EDGE spread, band-excess.
Signal known at the close of day k (first trading day >= signal day); buy at the close of k+1; sell at the close of k+1+H.
Cost model 'auction' = 25% of EDGE(60d before k) + 2 x $0.0035 / price; 'full' = 100% EDGE + commission.
Delisting inside the hold: last close, -30% if a non-merger delisting (as PEAD1).
I am not a financial adviser. This is a measurement tool, not a recommendation."""
import os, bisect, pickle
import numpy as np, pandas as pd
from collections import defaultdict
import ss_lib, pead_engine as E, ss_events2 as S
from bidask import edge_rolling
EDGE_DIR = os.path.join(os.path.expanduser("~"), "edge_cache")

def edge_series(f, z):
    os.makedirs(EDGE_DIR, exist_ok=True); p = os.path.join(EDGE_DIR, f)
    if os.path.exists(p): return np.load(p)["s"]
    df = pd.DataFrame({"open": z["o"], "high": z["h"], "low": z["l"], "close": z["c"]}).astype(float)
    s = edge_rolling(df, window=60).to_numpy(dtype=float); np.savez(p, s=s); return s

def run(events, H, band, bench, bad, good, lo_day, hi_day):
    """events: dict ticker -> list of (signal_day, label). Keeps trades with entry >= lo_day and exit <= hi_day."""
    out = []
    for t, evs in events.items():
        f = t.replace("/", "_") + ".npz"
        if not os.path.exists(os.path.join(S.STORE, f)): continue
        z = ss_lib.load(S.STORE, f); d = z["d"]; ca = z["ca"]; cu = z["cu"]; n = len(d); sp = None
        for sd, lab in evs:
            k = bisect.bisect_left(d, sd)
            if k < 61 or k + 2 >= n: continue
            e0 = k + 1; x = e0 + H; delist = 0.0
            if x >= n:
                if t in bad and t not in good: delist = -0.30
                x = n - 1
                if x <= e0: continue
            if d[e0] < lo_day or d[x] > hi_day: continue
            b = band.get((f, int(E.month_of(d[k]))))
            if b is None: continue
            if sp is None: sp = edge_series(f, z)
            s = sp[k - 1] if np.isfinite(sp[k - 1]) and sp[k - 1] > 0 else np.nan
            g = (1 + delist) * ca[x] / ca[e0] - 1
            bb = [bench.get((int(d[j]), b), 0.0) for j in range(e0 + 1, x + 1)]
            out.append(dict(t=t, band=b, lab=lab, entry=int(d[e0]), y=int(str(np.datetime64(int(d[e0]), "D"))[:4]),
                            x=float(g - (np.prod([1 + v for v in bb]) - 1)), spread=s, comm=2 * 0.0035 / float(cu[k]) if cu[k] > 0 else 0.0))
    return out

def apply_cost(recs, frac):
    med = defaultdict(list)
    for r in recs:
        if np.isfinite(r["spread"]): med[r["band"]].append(r["spread"])
    m = {b: float(np.median(v)) for b, v in med.items()}
    for r in recs: r["cost"] = frac * (r["spread"] if np.isfinite(r["spread"]) else m.get(r["band"], 0.01)) + r["comm"]
    return recs
