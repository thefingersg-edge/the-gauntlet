#!/usr/bin/env python3
"""Batch B event lists (no returns after the signal are computed here).
B1 S&P 500 additions / deletions (Sharadar sp500 'added'/'removed', effective date)
B2 predicted earnings dates: same-quarter 8-K Item 2.02 date one year earlier + 364 days
B3 weekly losers: per week-end, prior 5-day return of each M/S stock (ranked in the harness)
B4 12-1 momentum: per month-end, return from t-252 to t-21 of each M/S stock (ranked in the harness)
    SS_STORE=~/store python3 batchB_build.py b1b2 | b3b4"""
import os, sys, pickle, bisect
import numpy as np
from collections import defaultdict
import ss_lib, ss_events2 as S, pead_engine as E
C = S.CACHE

def b1b2():
    rd, ix = S.stream("sp500"); add, rem = [], []
    for r in rd:
        a = r[ix["action"]]
        if a in ("added", "removed"):
            (add if a == "added" else rem).append((r[ix["ticker"]], ss_lib.d2i(r[ix["date"]])))
    ann = ss_lib.announcements(ss_lib.find("events")); by = defaultdict(list)
    for t, d in ann: by[t].append(d)
    pred = []
    for t, ds in by.items():
        ds = sorted(set(ds))
        for d in ds:
            p = d + 364
            # skip if the company already announced in the 50 days before the predicted date (it moved earlier)
            pred.append((t, p, d))
    pickle.dump((add, rem, pred), open(os.path.join(C, "batchB_b1b2.pkl"), "wb"))
    print("B1 added", len(add), "removed", len(rem), "  B2 predicted dates", len(pred))

def b3b4():
    band = pickle.load(open(os.path.join(C, "band.pkl"), "rb")); wk, mo = [], []
    for f in sorted(os.listdir(S.STORE)):
        z = ss_lib.load(S.STORE, f); d = z["d"]; ca = z["ca"]; cu = z["cu"]; n = len(d)
        if n < 260: continue
        wkday = (d + 3) % 7                      # 0 = Monday (1970-01-01 was a Thursday)
        last_of_week = np.r_[np.diff(d // 7 * 0 + ((d + 3) // 7)) != 0, True]
        mon = E.month_of(d); last_of_month = np.r_[np.diff(mon) != 0, True]
        for i in np.nonzero(last_of_week)[0]:
            if i < 5 or i >= n - 1: continue
            b = band.get((f, int(mon[i])))
            if b in ("M", "S") and cu[i] >= 5: wk.append((f[:-4], int(d[i]), float(ca[i] / ca[i - 5] - 1), b))
        for i in np.nonzero(last_of_month)[0]:
            if i < 252 or i >= n - 1: continue
            b = band.get((f, int(mon[i])))
            if b in ("M", "S") and cu[i] >= 5: mo.append((f[:-4], int(d[i]), float(ca[i - 21] / ca[i - 252] - 1), b))
    pickle.dump((wk, mo), open(os.path.join(C, "batchB_b3b4.pkl"), "wb")); print("B3 week rows", len(wk), "  B4 month rows", len(mo))

if __name__ == "__main__":
    {"b1b2": b1b2, "b3b4": b3b4}[sys.argv[1]]()
