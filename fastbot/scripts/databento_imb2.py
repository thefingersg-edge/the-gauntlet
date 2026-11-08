#!/usr/bin/env python3
"""BOUNCE1 / Part B puller (PREREGISTRATION_BOUNCE1). READ-ONLY market data; places no orders. Key from ~/.databento_key.
Run on the Mac from the fastbot folder:
    python3 scripts/databento_imb2.py cost
    caffeinate -i python3 scripts/databento_imb2.py pull --go      # resumable; writes data/imb1/spy_path.csv
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import databento_costs1 as C1
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); D = os.path.join(FB, "data", "imb1")
OUT = os.path.join(D, "spy_path.csv"); LOG = os.path.join(D, "pull2.log")
CK = ["0930:30", "1550:00", "1550:15", "1550:30", "1551:00", "1552:00", "1555:00", "1558:00", "1559:59", "1600:01", "1605:00", "1615:00", "1630:00", "1650:00"]
COLS = ["date"] + ["m" + c.replace(":", "") for c in CK] + ["status"]
def days():
    return [r["date"] for r in csv.DictReader(open(os.path.join(D, "days.csv"))) if r["status"] == "ok"]
def req(c, d, a, b):
    q = c.timeseries.get_range(dataset="XNAS.ITCH", schema="bbo-1s", symbols=["SPY"], stype_in="raw_symbol", start=a, end=b).to_df()
    q = q[(q["bid_px_00"] > 0) & (q["ask_px_00"] > q["bid_px_00"])]
    m = (q["bid_px_00"] + q["ask_px_00"]) / 2; m.index = m.index.tz_convert("America/New_York"); return m
def at(m, d, ck, after=False):
    hh, mm, ss = int(ck[:2]), int(ck[2:4]), int(ck[5:]); t = dt.datetime.fromisoformat(C1.et(d, hh, mm, ss))
    s = m[m.index >= t] if after else m[m.index <= t]
    return "" if not len(s) else float(s.iloc[0] if after else s.iloc[-1])
def cost():
    db, c = C1.client(); ds = days(); sub = ds[::60]; tot = 0.0
    for d in sub:
        tot += c.metadata.get_cost(dataset="XNAS.ITCH", schema="bbo-1s", symbols=["SPY"], stype_in="raw_symbol", start=C1.et(d, 9, 30), end=C1.et(d, 9, 31))
        tot += c.metadata.get_cost(dataset="XNAS.ITCH", schema="bbo-1s", symbols=["SPY"], stype_in="raw_symbol", start=C1.et(d, 15, 49, 55), end=C1.et(d, 16, 51))
    print(f"estimated total: ${tot * len(ds) / len(sub):.2f} for {len(ds)} days")
def pull():
    if "--go" not in sys.argv: sys.exit("add --go to download (run 'cost' first)")
    db, c = C1.client(); log = open(LOG, "a")
    have = {r["date"] for r in csv.DictReader(open(OUT))} if os.path.exists(OUT) else set()
    new = not os.path.exists(OUT); f = open(OUT, "a", newline=""); w = csv.DictWriter(f, fieldnames=COLS)
    if new: w.writeheader()
    for d in days():
        if d in have: continue
        try:
            mo = req(c, d, C1.et(d, 9, 30), C1.et(d, 9, 31)); pm = req(c, d, C1.et(d, 15, 49, 55), C1.et(d, 16, 51))
            row = {"date": d, "status": "ok"}
            for ck in CK:
                src = mo if ck.startswith("0930") else pm
                row["m" + ck.replace(":", "")] = at(src, d, ck, after=ck in ("0930:30", "1600:01"))
        except Exception as ex:
            msg = str(ex)[:200].replace("\n", " ")
            if "auth" in msg.lower() or "401" in msg or "403" in msg: sys.exit(f"stopped: Databento auth/permission error -- {msg}")
            log.write(f"{d}: {type(ex).__name__}: {msg}\n"); log.flush(); print(f"{d}: {type(ex).__name__} -- will retry on the next run"); continue
        w.writerow(row); f.flush(); print(d, "ok", flush=True)
    print("done ->", OUT)
if __name__ == "__main__":
    {"cost": cost, "pull": pull}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
