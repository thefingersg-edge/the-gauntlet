#!/usr/bin/env python3
"""GRAN1 inputs: daily market-level series built from single-stock data (point-in-time). No index returns are read here.
  ins_ratio30  purchases / (purchases + sales) by officers/directors, distinct (ticker, owner, filing date), filings in the prior 30 days
  ear_L28      mean EAR of L-band (top-500 dollar volume) results announcements whose EAR was known in the prior 28 days; n_L28 = count
  disp_L       cross-sectional SD of daily returns across L-band stocks (that day)
Writes data/sharadar/cache/gran_daily.csv
    SS_STORE=~/store python3 gran_build.py insiders | disp | ear | write"""
import os, sys, csv, pickle, bisect
import numpy as np
from collections import defaultdict
import ss_lib, ss_events2 as S, pead_engine as E
C = S.CACHE

def insiders():
    rd, ix = S.stream("insiders"); U = ss_lib.universe(); seen = set(); buy = defaultdict(int); sell = defaultdict(int)
    for r in rd:
        if r[ix["formtype"]].strip() != "4": continue
        code = r[ix["transactioncode"]].strip()
        if code not in ("P", "S"): continue
        if r[ix["isofficer"]] != "Y" and r[ix["isdirector"]] != "Y": continue
        t = r[ix["ticker"]]
        if t.replace("/", "_") + ".npz" not in U: continue
        try: d = ss_lib.d2i(r[ix["date"]])
        except ValueError: continue
        k = (t, r[ix["ownername"]].strip().upper(), d, code)
        if k in seen: continue
        seen.add(k); (buy if code == "P" else sell)[d] += 1
    pickle.dump((dict(buy), dict(sell)), open(os.path.join(C, "gran_ins.pkl"), "wb")); print("insiders: days", len(buy), len(sell))

def disp():
    band = pickle.load(open(os.path.join(C, "band.pkl"), "rb")); d0, nd = 10000, 12000
    s1 = np.zeros(nd); s2 = np.zeros(nd); n = np.zeros(nd)
    for f in sorted(os.listdir(S.STORE)):
        z = ss_lib.load(S.STORE, f); d = z["d"]; ca = z["ca"]
        if len(d) < 2: continue
        r = ca[1:] / ca[:-1] - 1; dd = d[1:]; mo = E.month_of(dd)
        isL = np.array([band.get((f, int(m))) == "L" for m in mo]); ok = isL & np.isfinite(r) & (np.abs(r) < 1) & (np.diff(d) <= 5)
        np.add.at(s1, dd[ok] - d0, r[ok]); np.add.at(s2, dd[ok] - d0, r[ok] ** 2); np.add.at(n, dd[ok] - d0, 1)
    pickle.dump((d0, s1, s2, n), open(os.path.join(C, "gran_disp.pkl"), "wb")); print("disp: days with >=100 L stocks", int((n >= 100).sum()))

def ear():
    ev = [e for f in sorted(os.listdir(C)) if f.startswith("events_") for e in pickle.load(open(os.path.join(C, f), "rb"))]
    L = sorted((e["known"], e["ear"]) for e in ev if e["band"] == "L")
    pickle.dump(L, open(os.path.join(C, "gran_ear.pkl"), "wb")); print("L-band announcements", len(L))

def write():
    buy, sell = pickle.load(open(os.path.join(C, "gran_ins.pkl"), "rb")); d0, s1, s2, n = pickle.load(open(os.path.join(C, "gran_disp.pkl"), "rb"))
    L = pickle.load(open(os.path.join(C, "gran_ear.pkl"), "rb")); kd = [k for k, _ in L]; ev = [e for _, e in L]
    days = [d0 + i for i in range(len(n)) if n[i] >= 100]
    with open(os.path.join(C, "gran_daily.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["day", "date", "ins_ratio30", "n_ins30", "ear_L28", "n_L28", "disp_L", "n_L"])
        for d in days:
            b = sum(buy.get(x, 0) for x in range(d - 29, d + 1)); s = sum(sell.get(x, 0) for x in range(d - 29, d + 1))
            lo, hi = bisect.bisect_left(kd, d - 27), bisect.bisect_right(kd, d)
            i = d - d0; m = s1[i] / n[i]; sd = np.sqrt(max(s2[i] / n[i] - m * m, 0))
            w.writerow([d, str(np.datetime64(d, "D")), f"{b/(b+s):.5f}" if b + s >= 50 else "", b + s,
                        f"{np.mean(ev[lo:hi]):.6f}" if hi - lo >= 20 else "", hi - lo, f"{sd:.6f}", int(n[i])])
    print("gran_daily.csv rows", len(days))

if __name__ == "__main__":
    {"insiders": insiders, "disp": disp, "ear": ear, "write": write}[sys.argv[1]]()
