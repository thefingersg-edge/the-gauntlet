#!/usr/bin/env python3
"""FORWARD_C1 recorder (paper only). Daily: exposure = min(1.5, 15/VIX_prev) x (prev close > 200-day mean), for SPX500 and NAS100.
History of closes: daily_close.py (to 2026-09-30) + data/v36fwd 5m bars (pulled daily by forward_tick on the Mac), close of the
15:55 New York bar. VIX: data/VIXCLS.csv -- if the latest VIX is more than 5 days old the row is written with vix_stale=1 and the
200-day rule alone (exposure 1 or 0) so the record never invents a number.
    python3 c1_forward.py       # appends any new days since the last ledger row (from 2026-10-05)
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, csv, math, bisect, datetime as dt
from zoneinfo import ZoneInfo
import numpy as np
from daily_close import daily
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "..", "data")
LEDGER = os.path.join(D, "c1_forward.csv"); START = dt.date(2026, 10, 5); NY = ZoneInfo("America/New_York")
COLS = ["date", "ins", "close", "ma200", "vix_used", "vix_stale", "exposure", "ret_bh", "ret_c1"]

def fwd_closes(stem):
    b, a = {}, {}
    for fn, dst in ((f"{stem}_bid_5m.csv", b), (f"{stem}_ask_5m.csv", a)):
        p = os.path.join(D, "v36fwd", fn)
        if os.path.exists(p):
            for r in csv.reader(open(p)):
                if r[0] != "time": dst[r[0]] = float(r[4])
    out = {}
    for k in b:
        if k in a:
            t = dt.datetime.fromisoformat(k).replace(tzinfo=dt.timezone.utc).astimezone(NY)
            if t.strftime("%H:%M") == "15:55" and t.weekday() < 5: out[t.date()] = (b[k] + a[k]) / 2
    return out

def main():
    vix = {}
    for r in csv.DictReader(open(os.path.join(D, "VIXCLS.csv"))):
        try: vix[dt.date.fromisoformat(r["date"])] = float(r["vix"])
        except ValueError: pass
    vd = sorted(vix)
    have = {(r["date"], r["ins"]) for r in csv.DictReader(open(LEDGER))} if os.path.exists(LEDGER) else set()
    new = []
    for stem in ("spx500usd", "nas100usd"):
        C = {d: v[0] for d, v in daily(stem).items()}; C.update(fwd_closes(stem)); ds = sorted(C); c = np.array([C[d] for d in ds])
        for i in range(201, len(ds)):
            d = ds[i]
            if d < START or (d.isoformat(), stem) in have: continue
            ma = c[i - 200:i].mean(); flag = 1.0 if c[i - 1] > ma else 0.0
            j = bisect.bisect_left(vd, d) - 1; stale = j < 0 or (d - vd[j]).days > 5
            e = flag if stale else min(1.5, 15.0 / vix[vd[j]]) * flag
            r_ = c[i] / c[i - 1] - 1
            new.append({"date": d.isoformat(), "ins": stem, "close": f"{c[i]:.2f}", "ma200": f"{ma:.2f}", "vix_used": "" if stale else vix[vd[j]],
                        "vix_stale": int(stale), "exposure": f"{e:.3f}", "ret_bh": f"{r_:.6f}", "ret_c1": f"{e * r_:.6f}"})
    w = csv.DictWriter(open(LEDGER, "a", newline=""), fieldnames=COLS)
    if not os.path.exists(LEDGER) or os.path.getsize(LEDGER) == 0: w.writeheader()
    for r in sorted(new, key=lambda x: (x["date"], x["ins"])): w.writerow(r)
    print(f"c1_forward: {len(new)} new rows")

if __name__ == "__main__":
    main()
