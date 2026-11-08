#!/usr/bin/env python3
"""COSTS1 route 1 -- Databento quote puller + per-row measures (PREREGISTRATION_COSTS1 + COSTS1.1).
READ-ONLY market data. Places no orders. The key is read from ~/.databento_key and never printed.

Run on the Mac from the fastbot folder (needs:  pip3 install databento):
    python3 scripts/databento_costs1.py check        # dataset date ranges, no charge
    python3 scripts/databento_costs1.py cost         # price estimate from Databento's free cost endpoint, no download
    python3 scripts/databento_costs1.py pull --go    # download + measures -> data/costs1/measures.csv (resumable)
Then tell Claude; the verdict step (medians, bootstrap, decision rule) runs from measures.csv.
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, json, datetime as dt
from zoneinfo import ZoneInfo
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
D = os.path.join(FB, "data", "costs1"); RAW = os.path.join(D, "raw"); SAMPLE = os.path.join(D, "sample.csv")
MEAS = os.path.join(D, "measures.csv"); NY = ZoneInfo("America/New_York"); N_PER_BAND = 200
COLS = ["band", "order", "role", "ticker", "dataset", "entry_date", "exit_date", "edge", "status",
        "open_spread", "entry_auction", "exit_auction", "auction_rt", "src_entry_close", "src_exit_close"]

def client():
    import databento as db
    kp = os.path.expanduser("~/.databento_key")
    if not os.path.exists(kp): sys.exit("put your Databento API key in ~/.databento_key (one line), then chmod 600 it")
    key = open(kp).read().strip()
    if not key.startswith("db-"): sys.exit("~/.databento_key is empty or not a Databento key (should start 'db-'); copy the key again and rewrite the file")
    return db, db.Historical(key)

def et(day, hh, mm, ss=0):
    y, m, d = map(int, day.split("-")); return dt.datetime(y, m, d, hh, mm, ss, tzinfo=NY).isoformat()

def requests(r, day):
    sym = r["ticker"]; ds = r["dataset"]
    return [("bbo-1s", et(day, 9, 30), et(day, 9, 31)), ("bbo-1s", et(day, 15, 59), et(day, 16, 0)),
            ("statistics", et(day, 15, 55), et(day, 17, 0))]

def load_sample():
    S = list(csv.DictReader(open(SAMPLE)))
    for r in S: r["order"] = int(r["order"])
    return sorted(S, key=lambda r: (r["band"], r["order"]))

def check():
    db, c = client()
    for ds in ("XNAS.ITCH", "XNYS.PILLAR", "XASE.PILLAR"): print(ds, c.metadata.get_dataset_range(dataset=ds))

def cost():
    db, c = client(); S = [r for r in load_sample() if r["role"] == "sample"]; sub = S[::20]; tot = 0.0
    for r in sub:
        for day in (r["entry_date"], r["exit_date"]):
            for sch, a, b in requests(r, day):
                try: tot += c.metadata.get_cost(dataset=r["dataset"], schema=sch, symbols=[r["ticker"]], stype_in="raw_symbol", start=a, end=b)
                except Exception as ex: print("  cost skip", r["ticker"], day, sch, type(ex).__name__)
    print(f"estimated cost for the 400-row sample: ${tot * len(S) / len(sub):.2f} (from {len(sub)} rows; replacements add a little)")

def fetch(c, r, day, sch, a, b, tag):
    p = os.path.join(RAW, f"{r['ticker'].replace('/', '_')}_{day}_{tag}.dbn.zst")
    if not os.path.exists(p):
        st = c.timeseries.get_range(dataset=r["dataset"], schema=sch, symbols=[r["ticker"]], stype_in="raw_symbol", start=a, end=b)
        st.to_file(p)
    import databento as db
    return db.DBNStore.from_file(p).to_df()

def mid_spread(df):
    if df is None or len(df) == 0: return None
    df = df[(df["bid_px_00"] > 0) & (df["ask_px_00"] > df["bid_px_00"])]
    if len(df) == 0: return None
    m = (df["bid_px_00"] + df["ask_px_00"]) / 2; return m, (df["ask_px_00"] - df["bid_px_00"]) / m

def day_measures(db, c, r, day, want_open):
    out = {}
    q = requests(r, day)
    if want_open:
        x = mid_spread(fetch(c, r, day, *q[0], "open"))
        out["open_spread"] = float(x[1].median()) if x else None
    x = mid_spread(fetch(c, r, day, *q[1], "preclose"))
    mid = float(x[0].iloc[-1]) if x else None
    st = fetch(c, r, day, *q[2], "stats"); close, src = None, ""
    if st is not None and len(st):
        s = st[st["stat_type"].astype(int) == int(db.StatType.CLOSE_PRICE)]
        if len(s): close, src = float(s["price"].iloc[-1]), "stat_close"
    if close is None:   # fallback: largest print in the first 10 s after 16:00 (the closing cross)
        tr = fetch(c, r, day, "trades", et(day, 16, 0), et(day, 16, 0, 10), "trades")
        if tr is not None and len(tr): close, src = float(tr.loc[tr["size"].idxmax(), "price"]), "trade_cross"
    out["auction"] = abs(close - mid) / mid if (close and mid) else None; out["src"] = src
    return out

def pull():
    if "--go" not in sys.argv: sys.exit("add --go to download (run 'cost' first to see the price)")
    db, c = client(); os.makedirs(RAW, exist_ok=True)
    import traceback
    LOG = open(os.path.join(D, "pull.log"), "a"); LOG.write(f"--- pull {dt.datetime.now().isoformat()}\n")
    rng = {}
    for ds in ("XNAS.ITCH", "XNYS.PILLAR", "XASE.PILLAR"):
        try: rng[ds] = c.metadata.get_dataset_range(dataset=ds); LOG.write(f"range {ds} {rng[ds]}\n")
        except Exception as ex:   # dataset not available on this account -> its rows count as missing (replaced from reserve)
            rng[ds] = None; LOG.write(f"range {ds} FAILED {type(ex).__name__}: {str(ex)[:300]}\n"); print(f"note: {ds} unavailable ({type(ex).__name__})")
    LOG.flush()
    if all(v is None for v in rng.values()): sys.exit("Databento refused every dataset (see data/costs1/pull.log) -- nothing pulled, sample untouched")
    done = {(r["band"], int(r["order"])): r for r in csv.DictReader(open(MEAS))} if os.path.exists(MEAS) else {}
    S = load_sample()
    for band in ("M", "S"):
        rows = [r for r in S if r["band"] == band]; good = sum(1 for k, v in done.items() if k[0] == band and v["status"] == "ok")
        for r in rows:
            if good >= N_PER_BAND: break
            k = (band, r["order"])
            if k in done: continue
            o = {c_: r.get(c_, "") for c_ in COLS}; o["status"] = "missing"
            try:
                if rng[r["dataset"]] is None: raise LookupError("dataset unavailable")
                start = str(rng[r["dataset"]].get("start", ""))[:10]
                if start and r["entry_date"] < start: raise ValueError("before dataset start")
                a = day_measures(db, c, r, r["entry_date"], True); b = day_measures(db, c, r, r["exit_date"], False)
                o.update(open_spread=a["open_spread"], entry_auction=a["auction"], exit_auction=b["auction"],
                         src_entry_close=a["src"], src_exit_close=b["src"])
                if None not in (a["open_spread"], a["auction"], b["auction"]):
                    o["status"] = "ok"; o["auction_rt"] = a["auction"] + b["auction"]; good += 1
            except Exception as ex:
                if "auth" in str(ex).lower() or "401" in str(ex) or "403" in str(ex):
                    sys.exit(f"stopped: Databento auth/permission error -- {str(ex)[:200]}")   # never burn the reserve on an account problem
                o["status"] = f"missing:{type(ex).__name__}"
                LOG.write(f"{band} #{r['order']} {r['ticker']} {r['dataset']} {r['entry_date']}: {type(ex).__name__}: {str(ex)[:300]}\n"); LOG.flush()
            done[k] = o
            w = csv.DictWriter(open(MEAS, "w", newline=""), fieldnames=COLS); w.writeheader()
            w.writerows(sorted(done.values(), key=lambda v: (v["band"], int(v["order"]))))
            print(f"{band} #{r['order']:>4} {r['ticker']:<6} {o['status']}  (ok {good}/{N_PER_BAND})", flush=True)
    print("done ->", MEAS)

if __name__ == "__main__":
    {"check": check, "cost": cost, "pull": pull}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
