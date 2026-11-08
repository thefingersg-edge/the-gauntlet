"""v54 Step 0: build the tl_build3 timeline (125 base + 20 internals features, from the frozen data/tv_20261001) for
SPX500, US30 and NAS100 in the US cash session. Writes data/v54/<stem>.npz.
No model is fitted and no signed return is computed here.
Gate 0 (SPX only): the 125 base columns and labels must equal data/timeline_v37/matrix.npz
exactly on every shared (date, bar) key.

    python3 v54_build.py spx500usd | us30usd | nas100usd
"""
import os, sys, time
import numpy as np
import tl_build3 as T3
from reactive import load

TVD = "../data/tv_20261001"   # the frozen 2026-10-01 pull (MANIFEST sha pinned in PREREGISTRATION_v54)
stem = sys.argv[1]
t0 = time.time()
os.makedirs("../data/v54", exist_ok=True)
days = load("../data", stem)
rows, feats, ev = T3.build("../data", os.getcwd(), days=days, tv_dir=TVD)
M = T3.to_matrix(rows, feats)
np.savez_compressed(f"../data/v54/{stem}.npz", **M)
print(stem, len(days), "sessions", len(rows), "decision points", M["X"].shape[1], "features", f"{time.time() - t0:.0f}s", flush=True)
if stem == "spx500usd":
    S = dict(np.load("../data/timeline_v37/matrix.npz"))
    key = {(d, h): i for i, (d, h) in enumerate(zip(S["date"], S["hm"]))}
    idx = [(i, key[(d, h)]) for i, (d, h) in enumerate(zip(M["date"], M["hm"])) if (d, h) in key]
    a, b = np.array([i for i, _ in idx]), np.array([j for _, j in idx])
    base = M["X"][a][:, :125]
    same_x = np.array_equal(np.nan_to_num(base, nan=-9e9), np.nan_to_num(S["X"][b], nan=-9e9))
    same_y = all(np.array_equal(M[k][a], S[k][b]) for k in ("yl", "ys", "gl", "gs", "b_bp", "spread"))
    same_n = list(M["names"][:125]) == list(S["names"])
    print(f"GATE 0: {len(idx):,} of {len(S['date']):,} v37 rows matched; names {same_n}; 125 base features identical {same_x}; labels identical {same_y}"
          f" -> {'PASS' if (same_x and same_y and same_n and len(idx) == len(S['date'])) else 'FAIL'}")
