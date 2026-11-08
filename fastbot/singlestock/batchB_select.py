"""Batch B signal selection (point-in-time) -> dict ticker -> [(signal_day, label)], plus H and cluster unit per test."""
import os, pickle
import numpy as np
from collections import defaultdict
import ss_events2 as S
C = S.CACHE
SPECS = {"B1": dict(H=60, unit=91), "B2": dict(H=9, unit=91), "B3": dict(H=5, unit=7), "B4": dict(H=21, unit=30)}

def select():
    cp = os.path.join(C, 'batchB_events.pkl')
    if os.path.exists(cp): return pickle.load(open(cp, 'rb'))
    ev = _select(); pickle.dump({k: dict(v) for k, v in ev.items()}, open(cp, 'wb')); return pickle.load(open(cp, 'rb'))

def _select():
    add, rem, pred = pickle.load(open(os.path.join(C, "batchB_b1b2.pkl"), "rb")); wk, mo = pickle.load(open(os.path.join(C, "batchB_b3b4.pkl"), "rb"))
    ev = {k: defaultdict(list) for k in SPECS}
    for t, d in rem: ev["B1"][t].append((d, "deleted"))
    ev["B1add"] = defaultdict(list)
    for t, d in add: ev["B1add"][t].append((d, "added"))
    for t, p, d0 in pred: ev["B2"][t].append((p - 14, "pre"))
    byw = defaultdict(list)
    for t, d, r, b in wk: byw[d // 7].append((r, t, d))
    for w, L in byw.items():
        if len(L) < 100: continue
        q = np.quantile([x[0] for x in L], 0.1)
        for r, t, d in L:
            if r <= q: ev["B3"][t].append((d, "loser"))
    bym = defaultdict(list)
    for t, d, r, b in mo: bym[d // 30].append((r, t, d))
    for m, L in bym.items():
        if len(L) < 100: continue
        q = np.quantile([x[0] for x in L], 0.9)
        for r, t, d in L:
            if r >= q: ev["B4"][t].append((d, "winner"))
    return ev
