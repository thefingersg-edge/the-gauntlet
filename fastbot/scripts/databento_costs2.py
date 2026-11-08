#!/usr/bin/env python3
"""COSTS2 puller (PREREGISTRATION_COSTS2): official opening-auction price for the 400 COSTS1 rows. READ-ONLY data; no orders.
Run on the Mac from the fastbot folder:   python3 scripts/databento_costs2.py cost      then      python3 scripts/databento_costs2.py pull --go
Writes data/costs1/measures2.csv (resumable). The key is read from ~/.databento_key and never printed.
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import databento_costs1 as C1
OUT = os.path.join(C1.D, "measures2.csv"); COLS = ["band", "order", "ticker", "dataset", "entry_date", "official_open", "src_open", "first_mid", "official_close"]

def rows():
    return [r for r in csv.DictReader(open(C1.MEAS)) if r["status"] == "ok"]

def cost():
    db, c = C1.client(); R = rows(); sub = R[::20]; tot = 0.0
    for r in sub:
        tot += c.metadata.get_cost(dataset=r["dataset"], schema="statistics", symbols=[r["ticker"]], stype_in="raw_symbol",
                                   start=C1.et(r["entry_date"], 9, 25), end=C1.et(r["entry_date"], 9, 45))
    print(f"estimated cost for {len(R)} rows: ${tot * len(R) / len(sub):.2f}")

def stat(df, db, name):
    if df is None or not len(df): return None
    s = df[df["stat_type"].astype(int) == int(getattr(db.StatType, name))]
    return float(s["price"].iloc[-1]) if len(s) else None

def pull():
    if "--go" not in sys.argv: sys.exit("add --go to download")
    db, c = C1.client(); done = {(r["band"], r["order"]): r for r in csv.DictReader(open(OUT))} if os.path.exists(OUT) else {}
    for r in rows():
        k = (r["band"], r["order"])
        if k in done: continue
        day = r["entry_date"]; o = {x: r.get(x, "") for x in COLS}
        try:
            st = C1.fetch(c, r, day, "statistics", C1.et(day, 9, 25), C1.et(day, 9, 45), "openstats")
            op = stat(st, db, "OPENING_PRICE"); src = "stat_open"
            if op is None:
                tr = C1.fetch(c, r, day, "trades", C1.et(day, 9, 30), C1.et(day, 9, 30, 5), "opentrades")
                if tr is not None and len(tr): op, src = float(tr.loc[tr["size"].idxmax(), "price"]), "trade_cross"
            q = C1.mid_spread(C1.fetch(c, r, day, *C1.requests(r, day)[0], "open"))
            cl = stat(C1.fetch(c, r, day, *C1.requests(r, day)[2], "stats"), db, "CLOSE_PRICE")
            o.update(official_open=op if op else "", src_open=src if op else "", first_mid=float(q[0].iloc[0]) if q else "", official_close=cl or "")
        except Exception as ex:
            if "auth" in str(ex).lower() or "401" in str(ex) or "403" in str(ex): sys.exit(f"stopped: Databento auth/permission error -- {str(ex)[:200]}")
            o["src_open"] = f"error:{type(ex).__name__}"
        done[k] = o
        w = csv.DictWriter(open(OUT, "w", newline=""), fieldnames=COLS); w.writeheader(); w.writerows(done.values())
        print(f"{r['band']} #{r['order']:>4} {r['ticker']:<6} open {o['official_open'] or '-'} ({o['src_open']})", flush=True)
    print("done ->", OUT)

if __name__ == "__main__":
    {"cost": cost, "pull": pull}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
