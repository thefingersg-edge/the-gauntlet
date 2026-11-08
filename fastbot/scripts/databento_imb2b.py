#!/usr/bin/env python3
"""IMB2 puller (PREREGISTRATION_IMB2). READ-ONLY market data; places no orders. Key from ~/.databento_key.
Run on the Mac from the fastbot folder:
    python3 scripts/databento_imb2b.py cost
    caffeinate -i python3 scripts/databento_imb2b.py pull --go     # resumable; writes data/imb1/imb2_msgs.csv, imb2_px.csv
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import databento_costs1 as C1
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); D = os.path.join(FB, "data", "imb1")
MSG = os.path.join(D, "imb2_msgs.csv"); PX = os.path.join(D, "imb2_px.csv"); LOG = os.path.join(D, "pull3.log")
OFF = [-500, 0, 50, 100, 250, 500, 1000, 2000, 5000, 15000, 60000]
PXCOLS = ["date", "inst"] + [f"{s}{o}" for o in OFF for s in ("b", "a")]
def members():
    M = {}
    for r in csv.DictReader(open(os.path.join(D, "members.csv"))): M.setdefault(r["date"], {})[r["dataset"]] = r["symbols"].split()
    return M
def days():
    return [r["date"] for r in csv.DictReader(open(os.path.join(D, "days.csv"))) if r["status"] == "ok"]
def t0(d): return dt.datetime.fromisoformat(C1.et(d, 15, 50))
def win(d, a_ms, b_ms):
    return (t0(d) + dt.timedelta(milliseconds=a_ms)).isoformat(), (t0(d) + dt.timedelta(milliseconds=b_ms)).isoformat()
def cost():
    db, c = C1.client(); M = members(); ds = days(); sub = ds[::60]; tot = 0.0
    for d in sub:
        a, b = win(d, -500, 5000)
        for dsn, sy in M[d].items(): tot += c.metadata.get_cost(dataset=dsn, schema="imbalance", symbols=sy, stype_in="raw_symbol", start=a, end=b)
        a, b = win(d, -500, 61000)
        tot += c.metadata.get_cost(dataset="XNAS.ITCH", schema="mbp-1", symbols=["SPY"], stype_in="raw_symbol", start=a, end=b)
        tot += c.metadata.get_cost(dataset="GLBX.MDP3", schema="mbp-1", symbols=["ES.c.0"], stype_in="continuous", start=a, end=b)
    print(f"estimated total: ${tot * len(ds) / len(sub):.2f} for {len(ds)} days")
def snap(df, d):
    out = {}
    if df is None or not len(df): return out
    df = df[(df["bid_px_00"] > 0) & (df["ask_px_00"] > df["bid_px_00"])]; idx = df.index.tz_convert("America/New_York")
    for o in OFF:
        t = t0(d) + dt.timedelta(milliseconds=o); s = df[idx <= t]
        if len(s): out[f"b{o}"], out[f"a{o}"] = float(s["bid_px_00"].iloc[-1]), float(s["ask_px_00"].iloc[-1])
    return out
def pull():
    if "--go" not in sys.argv: sys.exit("add --go to download (run 'cost' first)")
    db, c = C1.client(); M = members(); log = open(LOG, "a")
    empty = lambda p: not os.path.exists(p) or os.path.getsize(p) == 0
    have = {r["date"] for r in csv.DictReader(open(PX))} if not empty(PX) else set()
    nm, npx = empty(MSG), empty(PX)
    fm = open(MSG, "a", newline=""); wm = csv.writer(fm); fp = open(PX, "a", newline=""); wp = csv.DictWriter(fp, fieldnames=PXCOLS)
    if nm: wm.writerow(["date", "venue", "symbol", "ms", "side", "imb_qty", "paired_qty", "ref_price"])
    if npx: wp.writeheader()
    for d in days():
        if d in have: continue
        try:
            rows = []
            for dsn, sy in M[d].items():
                a, b = win(d, -500, 5000)
                df = c.timeseries.get_range(dataset=dsn, schema="imbalance", symbols=sy, stype_in="raw_symbol", start=a, end=b).to_df()
                if len(df):
                    if "ts_recv" not in df.columns: df = df.reset_index()      # to_df() puts ts_recv in the index
                    df = df.sort_values("ts_recv"); df = df[df["ts_recv"] >= t0(d)].groupby("symbol", as_index=False).first()
                    for _, r in df.iterrows():
                        ms = (r["ts_recv"].tz_convert("America/New_York") - t0(d)).total_seconds() * 1000
                        rows.append([d, dsn[:4], r["symbol"], round(ms, 3), r["side"], float(r["total_imbalance_qty"]), float(r["paired_qty"]), float(r["ref_price"])])
            a, b = win(d, -500, 61000)
            sp = snap(c.timeseries.get_range(dataset="XNAS.ITCH", schema="mbp-1", symbols=["SPY"], stype_in="raw_symbol", start=a, end=b).to_df(), d)
            es = snap(c.timeseries.get_range(dataset="GLBX.MDP3", schema="mbp-1", symbols=["ES.c.0"], stype_in="continuous", start=a, end=b).to_df(), d)
        except Exception as ex:
            msg = str(ex)[:200].replace("\n", " ")
            if "auth" in msg.lower() or "401" in msg or "403" in msg: sys.exit(f"stopped: Databento auth/permission error -- {msg}")
            log.write(f"{d}: {type(ex).__name__}: {msg}\n"); log.flush(); print(f"{d}: {type(ex).__name__} -- will retry on the next run"); continue
        wm.writerows(rows); wp.writerow(dict(date=d, inst="SPY", **sp)); wp.writerow(dict(date=d, inst="ES", **es)); fm.flush(); fp.flush()
        print(d, "msgs", len(rows), "spy", len(sp) // 2, "es", len(es) // 2, flush=True)
    print("done")
if __name__ == "__main__":
    {"cost": cost, "pull": pull}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
