"""Single-stock pipeline (PEAD1+). Works on Sharadar bulk tables (stocks/SEP, tickers, actions, events).
Column names are mapped in COLS and checked at load; anything missing stops the run (no silent guessing).
Memory-safe: SEP is streamed once into one .npz per ticker (data/sharadar/store/), then processed per ticker.
I am not a financial adviser. This is a measurement tool, not a recommendation."""
import csv, gzip, io, os, sys, zipfile, datetime as dt, bisect
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.environ.get("SS_DATA") or os.path.join(HERE, "..", "data", "sharadar")
COLS = {"stocks": ["ticker", "date", "open", "high", "low", "close", "volume", "closeadj", "closeunadj"],
        "events": ["ticker", "date", "eventcodes"],
        "actions": ["date", "action", "ticker"],
        "tickers": ["table", "ticker", "isdelisted", "category", "exchange"]}
EARNINGS_CODE = "22"     # 8-K Item 2.02, Results of Operations and Financial Condition
BAD_DELIST = {"delisted", "regulatorydelisting", "bankruptcyliquidation", "voluntarydelisting"}
GOOD_DELIST = {"acquisitionby", "acquisitioncash", "acquisitionstock", "spacmerger", "mergerfrom", "mergerto", "spinoff"}
# Sharadar writes a generic "delisted" for EVERY delisting, so the -30% applies only when no merger/acquisition action exists for the ticker.
UNIVERSE_CATEGORIES = ("Domestic Common Stock", "Domestic Common Stock Primary Class", "Domestic Common Stock Secondary Class")
UNIVERSE_EXCHANGES = ("NYSE", "NASDAQ", "NYSEMKT")


def open_table(path):
    """CSV inside .zip / .gz / plain. Returns a text stream."""
    if path.endswith(".zip"):
        z = zipfile.ZipFile(path); name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        return io.TextIOWrapper(z.open(name), encoding="utf-8-sig", newline="")
    if path.endswith(".gz"): return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    return open(path, encoding="utf-8-sig", newline="")


def find(table, raw=None):
    raw = raw or os.path.join(DATA, "raw")
    c = [f for f in os.listdir(raw) if f.split(".")[0] == table and not f.endswith(".part")]
    if not c: sys.exit(f"no {table} file in {raw}")
    return os.path.join(raw, c[0])


def reader(path, table):
    fh = open_table(path); rd = csv.reader(fh); head = [h.strip().lower() for h in next(rd)]
    miss = [c for c in COLS[table] if c not in head]
    if miss: sys.exit(f"{table}: missing columns {miss}; header is {head}")
    return rd, {c: head.index(c) for c in head}


def d2i(s):  # 'YYYY-MM-DD' -> int days since epoch
    return (dt.date.fromisoformat(s[:10]) - dt.date(1970, 1, 1)).days


def build_store(sep_path, store=None, min_rows=60):
    """Stream SEP once -> store/<ticker>.npz (date int, o,h,l,c split-adj, closeadj, closeunadj, volume). Needs rows grouped by ticker."""
    store = store or os.path.join(DATA, "store"); os.makedirs(store, exist_ok=True)
    rd, ix = reader(sep_path, "stocks"); cur, buf, seen, n = None, [], set(), 0
    def flush():
        nonlocal n
        if cur is None or len(buf) < min_rows: return
        a = np.array(buf, dtype=np.float64); a = a[np.argsort(a[:, 0])]
        np.savez(os.path.join(store, cur.replace("/", "_") + ".npz"), d=a[:, 0].astype(np.int32),
                 o=a[:, 1].astype(np.float32), h=a[:, 2].astype(np.float32), l=a[:, 3].astype(np.float32),
                 c=a[:, 4].astype(np.float32), v=a[:, 5].astype(np.float32), ca=a[:, 6], cu=a[:, 7].astype(np.float32))
        n += 1
    k = [ix[c] for c in ("date", "open", "high", "low", "close", "volume", "closeadj", "closeunadj")]
    for r in rd:
        t = r[ix["ticker"]]
        if t != cur:
            flush()
            if t in seen: sys.exit(f"SEP not grouped by ticker ({t} reappears) -- sort it first")
            seen.add(t); cur, buf = t, []
        try: buf.append([d2i(r[k[0]])] + [float(r[j]) for j in k[1:]])
        except ValueError: continue
    flush(); return n


def load(store, t):
    z = np.load(os.path.join(store, t)); return {k: z[k] for k in z.files}


def announcements(events_path):
    rd, ix = reader(events_path, "events"); out = []
    for r in rd:
        if EARNINGS_CODE in r[ix["eventcodes"]].replace(" ", "").split("|"):
            out.append((r[ix["ticker"]], d2i(r[ix["date"]])))
    return sorted(set(out))


def delistings(actions_path):
    rd, ix = reader(actions_path, "actions"); bad, good = {}, {}
    for r in rd:
        a = r[ix["action"]].strip().lower(); t = r[ix["ticker"]]; d = d2i(r[ix["date"]])
        if a in BAD_DELIST: bad[t] = d
        elif a in GOOD_DELIST: good[t] = d
    return bad, good


def edge_spread(o, h, l, c):
    """EDGE (Ardia, Guidotti & Kroencke 2024) via the 'bidask' package; returns a fraction or nan."""
    from bidask import edge
    try:
        s = edge(np.asarray(o, float), np.asarray(h, float), np.asarray(l, float), np.asarray(c, float))
        return float(s) if s is not None and np.isfinite(s) and s > 0 else float("nan")
    except Exception:
        return float("nan")


def build_store_resumable(csv_path, store, state_path, budget_s=150, min_rows=60, allow=None):
    """Like build_store, but on a plain (unzipped) CSV with byte-offset checkpoints, so it can run in short calls.
    Returns True when the whole file has been processed."""
    import json, time
    os.makedirs(store, exist_ok=True); t0 = time.time()
    st = json.load(open(state_path)) if os.path.exists(state_path) else {"offset": None, "done": False, "n": 0, "seen": []}
    seen = set(st.get("seen", []))
    if st["done"]: return True
    fh = open(csv_path, "rb"); head = fh.readline().decode("utf-8-sig").strip().lower().split(",")
    miss = [c for c in COLS["stocks"] if c not in head]
    if miss: sys.exit(f"stocks: missing columns {miss}")
    ix = {c: head.index(c) for c in head}; k = [ix[c] for c in ("date", "open", "high", "low", "close", "volume", "closeadj", "closeunadj")]
    if st["offset"]: fh.seek(st["offset"])
    cur, buf, start = None, [], fh.tell()
    def flush():
        if cur is None or len(buf) < min_rows: return
        a = np.array(buf, dtype=np.float64); a = a[np.argsort(a[:, 0])]
        np.savez(os.path.join(store, cur.replace("/", "_") + ".npz"), d=a[:, 0].astype(np.int32),
                 o=a[:, 1].astype(np.float32), h=a[:, 2].astype(np.float32), l=a[:, 3].astype(np.float32),
                 c=a[:, 4].astype(np.float32), v=a[:, 5].astype(np.float32), ca=a[:, 6], cu=a[:, 7].astype(np.float32))
        st["n"] += 1
    def save(offset, done=False):
        st.update(offset=offset, done=done, seen=sorted(seen)); json.dump(st, open(state_path, "w"))
    keep = True
    while True:
        pos = fh.tell(); line = fh.readline()
        if not line:
            if keep: flush()
            save(pos, True); return True
        r = line.decode("utf-8").rstrip("\r\n").split(",")
        t = r[ix["ticker"]]
        if t != cur:
            if keep: flush()
            if time.time() - t0 > budget_s:                       # checkpoint at a ticker boundary
                save(pos); return False
            if t in seen: sys.exit(f"SEP not grouped by ticker: {t} reappears at byte {pos}")
            seen.add(t); cur, buf = t, []
            keep = allow is None or (t.replace("/", "_") + ".npz") in allow
        if not keep: continue
        try: buf.append([d2i(r[k[0]])] + [float(r[j]) for j in k[1:]])
        except (ValueError, IndexError): continue


def universe(tickers_path=None):
    """Tickers in the SEP table that are US domestic common stock on NYSE / NASDAQ / NYSE American (delisted ones included).
    Returns None if there is no tickers file (synthetic tests)."""
    try: tickers_path = tickers_path or find("tickers")
    except SystemExit: return None
    rd, ix = reader(tickers_path, "tickers"); out = set()
    for r in rd:
        if r[ix["table"]] == "SEP" and r[ix["category"]] in UNIVERSE_CATEGORIES and r[ix["exchange"]] in UNIVERSE_EXCHANGES:
            out.add(r[ix["ticker"]].replace("/", "_") + ".npz")
    return out


def bucketize_resumable(csv_path, outdir, state_path, allow, budget_s=150, nb=64):
    """SEP is NOT grouped by ticker. Pass 1: stream it once and append each allowed row to one of nb bucket files by
    hash(ticker). Byte-offset checkpoints after flushing; duplicates from an interrupted checkpoint are removed in pass 2."""
    import json, time, zlib
    os.makedirs(outdir, exist_ok=True); t0 = time.time()
    st = json.load(open(state_path)) if os.path.exists(state_path) else {"offset": None, "done": False, "rows": 0}
    if st["done"]: return True
    fh = open(csv_path, "rb"); head = fh.readline()
    if st["offset"]: fh.seek(st["offset"])
    outs = [open(os.path.join(outdir, f"b{i:02d}.csv"), "ab") for i in range(nb)]
    allow_b = {a[:-4].replace("_", "/").encode() for a in allow} | {a[:-4].encode() for a in allow}
    n = 0
    while True:
        line = fh.readline()
        if not line:
            for o in outs: o.close()
            st.update(done=True, offset=fh.tell(), rows=st["rows"] + n); json.dump(st, open(state_path, "w")); return True
        t = line[:line.index(b",")]
        if t in allow_b:
            outs[zlib.crc32(t) % nb].write(line); n += 1
        if n and n % 500000 == 0 and time.time() - t0 > budget_s:
            for o in outs: o.flush(); o.close()
            st.update(offset=fh.tell(), rows=st["rows"] + n); json.dump(st, open(state_path, "w")); return False


def store_from_bucket(bucket_path, store, header, min_rows=60):
    import pandas as pd
    df = pd.read_csv(bucket_path, header=None, names=header)
    df = df.drop_duplicates(["ticker", "date"]); df["d"] = (pd.to_datetime(df["date"]) - pd.Timestamp("1970-01-01")).dt.days
    n = 0
    for t, g in df.groupby("ticker", sort=False):
        if len(g) < min_rows: continue
        g = g.sort_values("d")
        np.savez(os.path.join(store, str(t).replace("/", "_") + ".npz"), d=g["d"].to_numpy(np.int32),
                 o=g["open"].to_numpy(np.float32), h=g["high"].to_numpy(np.float32), l=g["low"].to_numpy(np.float32),
                 c=g["close"].to_numpy(np.float32), v=g["volume"].to_numpy(np.float32), ca=g["closeadj"].to_numpy(np.float64),
                 cu=g["closeunadj"].to_numpy(np.float32))
        n += 1
    return n
