#!/usr/bin/env python3
"""COSTS1 step 1: draw the frozen 400-signal sample (plus an ordered reserve) BEFORE any quote is read.
Frame: PEAD3 CONFIRMED signals (frozen PEAD1 engine + PEAD3 rule), bands M and S, entry 2018-05-01 .. 2026-06-30,
excluding US half-days. Stratified 200 M / 200 S, seed 20261003. Reserve: the rest of each band in seeded random order,
used strictly in order to replace a row that has no quote data (rule in PREREGISTRATION_COSTS1.1).
Output: data/costs1/sample.csv  (run once; refuses to overwrite).
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, bisect, datetime as dt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ss_lib, ss_events2 as S, pead_engine as E
from batch2_run import pead1_longs, sue_threshold, LOAD
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(FB, "data", "costs1", "sample.csv"); SEED = 20261003; N = 200; H = 60
LO, HI = dt.date(2018, 5, 1), dt.date(2026, 6, 30)
DS = {"NASDAQ": "XNAS.ITCH", "NYSE": "XNYS.PILLAR", "NYSEMKT": "XASE.PILLAR"}

def half_day(d):
    return (d.month, d.day) in ((7, 3), (12, 24)) or (d.month == 11 and d.weekday() == 4 and 23 <= d.day <= 29)

def main():
    if os.path.exists(OUT): sys.exit("sample.csv exists -- frozen; not redrawing")
    exch = {}
    r, ix = ss_lib.reader(ss_lib.find("tickers"), "tickers")
    for row in r:
        if row[ix["table"]] == "SEP": exch[row[ix["ticker"]]] = row[ix["exchange"]]
    L = pead1_longs(); sue = LOAD("sue_events.pkl"); thr = sue_threshold(sue, 0.7)
    by = {}
    for t, d, rp, v in sue: by.setdefault(t, []).append((d, v))
    for t in by: by[t].sort()
    frame = {"M": [], "S": []}
    for e in L:
        Z = by.get(e["t"], []); i = bisect.bisect_left(Z, (e["ad"], -1e18))
        if i >= len(Z) or Z[i][0] > e["ad"] + 60: continue
        d, v = Z[i]; th = thr(int(d))
        if not (np.isfinite(th) and v >= th): continue
        f = e["t"].replace("/", "_") + ".npz"
        if not os.path.exists(os.path.join(S.STORE, f)) or exch.get(e["t"]) not in DS: continue
        z = ss_lib.load(S.STORE, f); dd = z["d"]; k = bisect.bisect_left(dd, int(d)); e0 = k + 1; x = e0 + H - 1
        if k < 60 or x >= len(dd): continue
        ed = dt.date(1970, 1, 1) + dt.timedelta(int(dd[e0])); xd = dt.date(1970, 1, 1) + dt.timedelta(int(dd[x]))
        if not (LO <= ed <= HI) or half_day(ed) or half_day(xd): continue
        c = ss_lib.edge_spread(z["o"][k-60:k], z["h"][k-60:k], z["l"][k-60:k], z["c"][k-60:k])
        frame[e["band"]].append(dict(ticker=e["t"], band=e["band"], exchange=exch[e["t"]], dataset=DS[exch[e["t"]]],
                                     filing=str(np.datetime64(int(d), "D")), entry_date=ed.isoformat(), exit_date=xd.isoformat(),
                                     edge=f"{c:.6f}" if np.isfinite(c) else "", close_prev=f"{float(z['cu'][k]):.4f}"))
    rng = np.random.default_rng(SEED); out = []
    for b in ("M", "S"):
        F = sorted(frame[b], key=lambda r: (r["entry_date"], r["ticker"])); p = rng.permutation(len(F))
        for j, q in enumerate(p): out.append(dict(F[q], order=j, role="sample" if j < N else "reserve"))
        print(f"band {b}: frame {len(F)}, sample {min(N, len(F))}, reserve {max(0, len(F) - N)}")
    cols = ["band", "order", "role", "ticker", "exchange", "dataset", "filing", "entry_date", "exit_date", "edge", "close_prev"]
    w = csv.DictWriter(open(OUT, "w", newline=""), fieldnames=cols); w.writeheader(); w.writerows(out); print("wrote", OUT)

if __name__ == "__main__": main()
