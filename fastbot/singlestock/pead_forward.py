#!/usr/bin/env python3
"""FORWARD_PEAD3 recorder (paper only -- nothing is ever traded by this script).
After each data refresh (sharadar_pull.py --refresh -> data/sharadar_fwd_YYYYMMDD/raw, then the PEAD1 pipeline stages with
SS_DATA pointing at that folder), run:
    SS_DATA=<refresh root> SS_STORE=<store> python3 pead_forward.py record   # add new signals filed on/after START
    SS_DATA=<refresh root> SS_STORE=<store> python3 pead_forward.py mark     # close rows whose 60 trading days have passed
Ledger: data/pead3_forward.csv (append-only; a row is never edited except to fill its exit fields once).
Signals use the FROZEN PEAD1 engine and the FROZEN PEAD3 confirmation rule; secondary flags record the PEAD4 late-entry
'not confirmed' group and the S band, so all three designs are tracked forward from the same start.
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, pickle, bisect, datetime as dt
import numpy as np
import ss_lib, ss_events2 as S, pead_engine as E
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LEDGER = os.path.join(FB, "data", "pead3_forward.csv"); START = (dt.date(2026, 10, 5) - dt.date(1970, 1, 1)).days; H = 60
COLS = ["ticker", "band", "announce_8k", "filing", "group", "ear", "sue", "entry_date", "entry_px", "exit_date", "exit_px", "excess", "edge_cost", "net", "status", "recorded", "net_pead7", "day1", "anchor"]

def rows():
    return list(csv.DictReader(open(LEDGER))) if os.path.exists(LEDGER) else []

def record():
    C = S.CACHE; ev = [e for f in sorted(os.listdir(C)) if f.startswith("events_") for e in pickle.load(open(os.path.join(C, f), "rb"))]
    ev = E.signals(ev); longs = [e for e in ev if e["long"] and e["band"] in ("M", "S")]
    arq = S.fundamentals_arq(ss_lib.universe()); sue = S.sue_events(arq)
    from batch2_run import sue_threshold
    thr = sue_threshold(sue, 0.7); by = {}
    for t, d, rp, v in sue: by.setdefault(t, []).append((d, v))
    for t in by: by[t].sort()
    have = {(r["ticker"], r["filing"]) for r in rows()}; new = []
    for e in longs:
        Z = by.get(e["t"], []); i = bisect.bisect_left(Z, (e["ad"], -1e18))
        if i >= len(Z) or Z[i][0] > e["ad"] + 60 or Z[i][0] < START: continue
        d, v = Z[i]; th = thr(int(d)); fd = str(np.datetime64(int(d), "D"))
        if (e["t"], fd) in have or not np.isfinite(th): continue
        new.append({"ticker": e["t"], "band": e["band"], "announce_8k": str(np.datetime64(int(e["ad"]), "D")), "filing": fd,
                    "anchor": str(np.datetime64(int(max(d, e["known"])), "D")),   # AUDIT 2026-10-04: never enter before the EAR is known
                    "group": "CONFIRMED" if v >= th else "not_confirmed", "ear": f"{e['ear']:.4f}", "sue": f"{v:.3f}",
                    "status": "open", "recorded": dt.date.today().isoformat()})
    w = csv.DictWriter(open(LEDGER, "a", newline=""), fieldnames=COLS)
    if not os.path.exists(LEDGER) or os.path.getsize(LEDGER) == 0: w.writeheader()
    for r in new: w.writerow(r)
    print(f"record: {len(new)} new signals (confirmed {sum(r['group']=='CONFIRMED' for r in new)})")

def mark():
    band = pickle.load(open(os.path.join(S.CACHE, "band.pkl"), "rb")); bench = pickle.load(open(os.path.join(S.CACHE, "bench.pkl"), "rb"))
    R = rows(); n = 0
    for r in R:
        if r["status"] != "open": continue
        f = r["ticker"].replace("/", "_") + ".npz"
        if not os.path.exists(os.path.join(S.STORE, f)): continue
        z = ss_lib.load(S.STORE, f); d = z["d"]; k = bisect.bisect_left(d, ss_lib.d2i(r.get("anchor") or r["filing"])); e0 = k + 1; x = e0 + H - 1
        if x >= len(d): continue
        adj = z["ca"][e0] / z["c"][e0]; px0 = z["o"][e0] * adj; g = z["ca"][x] / px0 - 1
        b = band.get((f, int(E.month_of(d[k]))), r["band"]); bb = [bench.get((int(d[j]), b), 0.0) for j in range(e0, x + 1)]
        ex = g - (np.prod([1 + v for v in bb]) - 1); c = ss_lib.edge_spread(z["o"][k-60:k], z["h"][k-60:k], z["l"][k-60:k], z["c"][k-60:k])
        sp = c if np.isfinite(c) else 0.01; cm = 2 * 0.0035 / float(z["cu"][k]); c = sp + cm
        n7 = ex - ({"M": 0.64, "S": 1.06}.get(r["band"], 1.0) * sp + cm)          # PEAD7 measured-cost net (FORWARD_PEAD3.1)
        d1 = z["ca"][e0] / px0 - 1                                                  # open-auction -> close on day one (raw)
        r.update(entry_date=str(np.datetime64(int(d[e0]), "D")), entry_px=f"{px0:.4f}", exit_date=str(np.datetime64(int(d[x]), "D")),
                 exit_px=f"{z['ca'][x]:.4f}", excess=f"{ex:.5f}", edge_cost=f"{c:.5f}", net=f"{ex - c:.5f}", net_pead7=f"{n7:.5f}", day1=f"{d1:.5f}", status="closed"); n += 1
    w = csv.DictWriter(open(LEDGER, "w", newline=""), fieldnames=COLS); w.writeheader(); w.writerows(R); print(f"mark: closed {n}")

if __name__ == "__main__":
    {"record": record, "mark": mark}[sys.argv[1]]()
