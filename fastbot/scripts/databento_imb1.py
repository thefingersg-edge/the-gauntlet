#!/usr/bin/env python3
"""IMB1 puller (PREREGISTRATION_IMB1). READ-ONLY market data, places no orders. Key from ~/.databento_key (never printed).
Run on the Mac from the fastbot folder (pip3 install databento):
    python3 scripts/databento_imb1.py cost          # price estimate (Databento's free cost endpoint), no download
    python3 scripts/databento_imb1.py pull --go     # resumable; writes data/imb1/days.csv and data/imb1/symbols.csv
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import databento_costs1 as C1
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); D = os.path.join(FB, "data", "imb1")
MEM = os.path.join(D, "members.csv"); DAYS = os.path.join(D, "days.csv"); SYMS = os.path.join(D, "symbols.csv"); LOG = os.path.join(D, "pull.log")
DCOLS = ["date", "n_nas", "n_nys", "buy_usd", "sell_usd", "paired_usd", "spy_mid_1551", "spy_mid_1600", "status"]
def members():
    M = {}
    for r in csv.DictReader(open(MEM)): M.setdefault(r["date"], {})[r["dataset"]] = r["symbols"].split()
    return M
def cost():
    db, c = C1.client(); M = members(); ds = sorted(M)[::60]; tot = 0.0
    for d in ds:
        for dsn, sy in M[d].items():
            tot += c.metadata.get_cost(dataset=dsn, schema="imbalance", symbols=sy, stype_in="raw_symbol", start=C1.et(d, 15, 50), end=C1.et(d, 15, 50, 20))
        tot += c.metadata.get_cost(dataset="XNAS.ITCH", schema="bbo-1s", symbols=["SPY"], stype_in="raw_symbol", start=C1.et(d, 15, 50, 55), end=C1.et(d, 16, 0))
    print(f"estimated total: ${tot * len(M) / len(ds):.2f} for {len(M)} days")
def first_msgs(df):
    if df is None or not len(df): return []
    df = df.sort_values("ts_recv").groupby("symbol", as_index=False).first(); out = []
    for _, r in df.iterrows():
        sgn = 1 if r["side"] == "B" else (-1 if r["side"] == "A" else 0)
        out.append((r["symbol"], r["side"], float(r["total_imbalance_qty"]), float(r["paired_qty"]), float(r["ref_price"]), sgn))
    return out
def pull():
    if "--go" not in sys.argv: sys.exit("add --go to download (run 'cost' first)")
    db, c = C1.client(); M = members(); log = open(LOG, "a")
    done = {r["date"] for r in csv.DictReader(open(DAYS))} if os.path.exists(DAYS) else set()
    newd = not os.path.exists(DAYS); newsy = not os.path.exists(SYMS)
    fd = open(DAYS, "a", newline=""); wd = csv.DictWriter(fd, fieldnames=DCOLS); fs = open(SYMS, "a", newline=""); ws = csv.writer(fs)
    if newd: wd.writeheader()
    if newsy: ws.writerow(["date", "venue", "symbol", "side", "imb_qty", "paired_qty", "ref_price"])
    for d in sorted(M):
        if d in done: continue
        row = {"date": d, "status": "ok"}; buy = sell = paired = 0.0
        try:
            for dsn, sy in M[d].items():
                st = c.timeseries.get_range(dataset=dsn, schema="imbalance", symbols=sy, stype_in="raw_symbol", start=C1.et(d, 15, 50), end=C1.et(d, 15, 50, 20))
                F = first_msgs(st.to_df()); row["n_nas" if dsn == "XNAS.ITCH" else "n_nys"] = len(F)
                for s, side, iq, pq, rp, sg in F:
                    v = iq * rp; buy += v if sg > 0 else 0.0; sell += v if sg < 0 else 0.0; paired += pq * rp
                    ws.writerow([d, dsn[:4], s, side, iq, pq, rp])
            q = c.timeseries.get_range(dataset="XNAS.ITCH", schema="bbo-1s", symbols=["SPY"], stype_in="raw_symbol", start=C1.et(d, 15, 50, 55), end=C1.et(d, 16, 0)).to_df()
            q = q[(q["bid_px_00"] > 0) & (q["ask_px_00"] > q["bid_px_00"])]; mid = (q["bid_px_00"] + q["ask_px_00"]) / 2
            t = q.index.tz_convert("America/New_York")
            a = mid[t >= dt.datetime.fromisoformat(C1.et(d, 15, 51))]; b = mid[t <= dt.datetime.fromisoformat(C1.et(d, 15, 59, 59))]
            row.update(buy_usd=buy, sell_usd=sell, paired_usd=paired, spy_mid_1551=float(a.iloc[0]) if len(a) else "", spy_mid_1600=float(b.iloc[-1]) if len(b) else "")
            if not (row.get("n_nas") or row.get("n_nys")): row["status"] = "no_messages"   # holidays / half days
        except Exception as ex:
            if "auth" in str(ex).lower() or "401" in str(ex) or "403" in str(ex): sys.exit(f"stopped: Databento auth/permission error -- {str(ex)[:200]}")
            msg = str(ex)[:200].replace("\n", " "); log.write(f"{d}: {type(ex).__name__}: {msg}\n"); log.flush()
            if "resolved" in msg or "422" in msg: row["status"] = "no_symbols"
            else: print(f"{d}: {type(ex).__name__} -- will retry on the next run"); continue
        wd.writerow(row); fd.flush(); fs.flush(); print(f"{d} {row['status']} nas {row.get('n_nas',0)} nys {row.get('n_nys',0)}", flush=True)
    print("done ->", DAYS)
if __name__ == "__main__":
    {"cost": cost, "pull": pull}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
