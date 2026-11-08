#!/usr/bin/env python3
"""PREREGISTRATION_v48 -- gold into Chinese New Year and Diwali. DESCRIPTIVE ONLY (MDE ~194 bp).
Fixed before the run:
 * Event table data/v48/events_v48.csv pinned by sha (frozen before any price join).
 * Daily close = close of the 16:45 New York 15m bar (the 17:00 NY roll), weekdays with that bar.
 * Window: close 15 trading days before the event day E -> close of E, where E = event date
   or the last trading day before it. Events whose window starts before the data are dropped.
 * Reference: all remaining trading days between/around event windows, tiled into
   non-overlapping 15-day blocks (leftover dropped).
 * Cost = spread at the entry close (ask_c/bid_c - 1) + (DGS3MO + 2.5%)/365 per calendar night.
 * t = two-sample (event vs reference), clustered by year for events (one per type per year).
I am not a financial adviser. This is a measurement, not a recommendation."""
import csv, datetime as dt, hashlib, sys, bisect
from zoneinfo import ZoneInfo
import numpy as np
from premarket_factor import regress, tstat

VERSION = "1.0"
DOC = ("PREREGISTRATION_v48.md", "2ad9b46b4083e2161a79e534aef48a241e781039b4ad4917eb8fe10eb917f287")
EVT = ("data/v48/events_v48.csv", "b7640992bfbff8d1b64717d09ceca6a730ae995641794c656ecf858e8ef1ccd9")
NY = ZoneInfo("America/New_York"); W = 15


def closes():
    b, a = {}, {}
    for fn, dst in (("../data/v24/xauusd_bid_15m.csv", b), ("../data/v24/xauusd_ask_15m.csv", a)):
        for r in csv.reader(open(fn)):
            if r[0] != "time": dst[r[0]] = float(r[4])
    out = {}
    for k, v in b.items():
        if k not in a: continue
        t = dt.datetime.fromisoformat(k).replace(tzinfo=dt.timezone.utc).astimezone(NY)
        if t.strftime("%H:%M") == "16:45" and t.weekday() < 5:
            out[t.date()] = ((v + a[k]) / 2, (a[k] / v - 1) * 1e4)
    return out


def main():
    for f, h in (("../" + DOC[0], DOC[1]), ("../" + EVT[0], EVT[1])):
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} changed -- refused")
    print(f"gold_season_v48.py v{VERSION}   PREREGISTRATION_v48 (sha {DOC[1][:8]}…) and event table (sha {EVT[1][:8]}…) match\n"
          "  DESCRIPTIVE ONLY -- MDE ~194 bp; no PASS/FAIL is claimed.\n"
          "  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    C = closes(); ses = sorted(C); px = [C[d][0] for d in ses]; sp = [C[d][1] for d in ses]
    RT = ([], [])
    for r in csv.DictReader(open("../data/DGS3MO.csv")):
        try: v = float(r["DGS3MO"])
        except ValueError: continue
        RT[0].append(dt.date.fromisoformat(r["observation_date"])); RT[1].append(v)
    def fin(i, j):
        k = bisect.bisect_right(RT[0], ses[i]) - 1
        return (ses[j] - ses[i]).days * (RT[1][max(k, 0)] + 2.5) / 100 / 365 * 1e4
    def ret(i, j): return (px[j] / px[i] - 1) * 1e4
    ev = []
    for r in csv.DictReader(open("../" + EVT[0])):
        d = dt.date.fromisoformat(r["date"])
        j = bisect.bisect_right(ses, d) - 1
        if j < W or d > ses[-1]: 
            print(f"    dropped {r['event']} {r['year']} (outside data)"); continue
        i = j - W
        ev.append(dict(e=r["event"], y=int(r["year"]), i=i, j=j, g=ret(i, j), net=ret(i, j) - sp[i] - fin(i, j)))
    used = set()
    for x in ev: used |= set(range(x["i"], x["j"] + 1))
    ref = []; i = 0
    while i + W < len(ses):
        blk = set(range(i, i + W + 1))
        if blk & used: i += 1; continue
        ref.append(dict(y=ses[i].year, g=ret(i, i + W), net=ret(i, i + W) - sp[i] - fin(i, i + W))); i += W
    rg = np.array([r["g"] for r in ref])
    print(f"  data {ses[0]}..{ses[-1]}   events used {len(ev)}   reference 15-day blocks {len(ref)}")
    print(f"  reference: gross {rg.mean():+.1f} bp  sd {rg.std(ddof=1):.0f}  net {np.mean([r['net'] for r in ref]):+.1f}\n")
    for lab, sel in (("CNY", ["CNY"]), ("DIWALI", ["DIWALI"]), ("both", ["CNY", "DIWALI"])):
        E = [x for x in ev if x["e"] in sel]
        y = np.array([x["g"] for x in E] + list(rg)); X = np.column_stack([np.ones(len(y)), [1.0] * len(E) + [0.0] * len(ref)])
        cl = [f"E{x['y']}" for x in E] + [f"R{k}" for k in range(len(ref))]
        b, V = regress(y, X, cl)
        g = np.array([x["g"] for x in E]); n = np.array([x["net"] for x in E])
        print(f"  {lab:<6} n {len(E):2d}  window gross {g.mean():+6.1f} bp  net {n.mean():+6.1f}  up {np.mean(g > 0):.0%}"
              f"   minus reference {b[1]:+6.1f} bp  t {tstat(b, V, 1):+.2f}")
    print("\n  per event (gross bp):")
    for e in ("CNY", "DIWALI"):
        print("   " + e + ": " + "  ".join(f"{x['y'] % 100:02d}:{x['g']:+.0f}" for x in ev if x["e"] == e))
    for lo, hi in ((2006, 2012), (2013, 2019), (2020, 2026)):
        g = [x["g"] for x in ev if lo <= x["y"] <= hi]
        print(f"   era {lo}-{hi % 100:02d}: both events gross {np.mean(g):+.1f} bp (n {len(g)})  reference {np.mean([r['g'] for r in ref if lo <= r['y'] <= hi]):+.1f}")
    print("\n  VERDICT  DESCRIPTIVE (no gate, by pre-registration)")


if __name__ == "__main__":
    main()
