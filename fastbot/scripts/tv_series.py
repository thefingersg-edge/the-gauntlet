#!/usr/bin/env python3
"""tv_series -- daily index / futures series pulled through the TradingView
connector (tvremix MCP, get_ohlcv 1D), written to data/tv/ and read back with
the moment each value was KNOWN.

WHY THIS EXISTS (2026-10-01)
----------------------------
* The v41 forest's VIX and VIX-futures inputs were Dave's TradingView exports
  and a FRED download. They stopped on 2026-08-18 / 2026-08-31, and a stale file
  does not show up as a missing feature: the "minutes since the last VIX drop"
  feature silently counts from the last drop IN THE FILE (two drops, 11 and 17
  Sep, were missing).
* The same connector serves series this programme has never had: put/call,
  VIX3M, S&P breadth, NYSE advance/decline (PREREGISTRATION_v54, v56).

THE CONNECTOR CAN ONLY BE CALLED FROM A CLAUDE SESSION, not from launchd.
A session pulls each symbol (count 5000), the JSON lands in a file, and
convert() turns it into data/tv/<NAME>.csv plus a MANIFEST.json entry.

TIMESTAMPS -- checked against the existing files on 2026-10-01
--------------------------------------------------------------
* CFE futures (VX1!, VX2!): TradingView stamps the daily bar at the session
  OPEN, 17:00 Chicago on the PREVIOUS calendar day. The trading date is the
  Chicago date + 1 when the stamp hour >= 16 (tl_build 1.1's rule). Identical
  to Dave's exports on 4,969 of 4,969 overlapping bars except the export's last
  row, which was exported mid-session (18.2 vs settled 18.1906).
* Indices (VIX at 03:15 ET; everything else at 09:30 ET): trading date = the
  New York date of the stamp. VIX matches FRED VIXCLS on 4,969 of 4,978 days;
  SKEW matches Cboe's file on 4,974 of 4,991.
* A value is AVAILABLE at AVAIL[name] (ET, same trading date): 16:15 for the
  Cboe vol indices and VX (as tl_build), 18:00 for breadth and put/call (a
  deliberately late stamp; decisions only happen 09:40-13:45, so any stamp
  between the close and the next open is equivalent).
* PARTIAL BARS: convert() drops any bar whose availability stamp is later than
  the pull time. That is the bug that put 18.2 into Dave's VX export.
* VINTAGE CHECK (1.1): when <NAME>.csv already exists, every trade date in both
  the file and the new pull must carry the same close (relative 1e-9), or
  convert() refuses and writes nothing. A refresh adds days and keeps every older
  stored row (so a short monthly pull never shrinks the file); it may never rewrite one.
  Frozen snapshots (data/tv_YYYYMMDD) are what tests read; data/tv is the live
  copy the v41 recorder appends from.
* VINTAGE PINS (1.2): <out_dir>/VINTAGE_PINS.json lists {NAME: {date: {"keep": x, "revised": y}}}.
  A mismatch is tolerated only when the stored close is exactly `keep` AND the new pull
  says exactly `revised`; the stored row is then written unchanged. Any other mismatch,
  including a further revision of a pinned date, still refuses.

    python3 tv_series.py --self-test
    python3 tv_series.py --convert <raw.json> --pulled-utc 2026-10-01T21:55:00Z [--source "..."]
"""
from __future__ import annotations

import argparse, csv, datetime as dt, hashlib, json, os, sys
from zoneinfo import ZoneInfo

VERSION = "1.3"   # 1.3 (2026-10-16): --source names the connector in MANIFEST.json (the official TradingView MCP
# returns the same {symbol, bars[{t,o,h,l,c}]} shape, so convert() is unchanged);
# 1.2 (2026-10-16): data/tv/VINTAGE_PINS.json keeps a stored row Dave chose over a named revision;
# 1.1 (2026-10-02): convert() refuses a pull that disagrees with rows already on disk
NY, CH = ZoneInfo("America/New_York"), ZoneInfo("America/Chicago")
HERE = os.path.dirname(os.path.abspath(__file__))
TV_DIR = os.path.join(HERE, "../data/tv")

#            name      TradingView symbol  kind    available (ET)
SPECS = {"VIX":    ("CBOE:VIX",   "index", "16:15"),
         "VX1":    ("CBOE:VX1!",  "cfe",   "16:15"),
         "VX2":    ("CBOE:VX2!",  "cfe",   "16:15"),
         "SKEW":   ("CBOE:SKEW",  "index", "16:15"),
         "VIX3M":  ("CBOE:VIX3M", "index", "16:15"),
         "GVZ":    ("CBOE:GVZ",   "index", "16:15"),
         "PCC":    ("USI:PCC",    "index", "18:00"),
         "S5FI":   ("INDEX:S5FI", "index", "18:00"),
         "S5TH":   ("INDEX:S5TH", "index", "18:00"),
         "ADD":    ("USI:ADD",    "index", "18:00"),
         "ADV":    ("USI:ADV",    "index", "18:00"),
         "DECL":   ("USI:DECL",   "index", "18:00")}
BY_SYMBOL = {v[0]: k for k, v in SPECS.items()}


def trade_date(t: int, kind: str) -> dt.date:
    if kind == "cfe":
        c = dt.datetime.fromtimestamp(t, CH)
        return c.date() + (dt.timedelta(days=1) if c.hour >= 16 else dt.timedelta(0))
    return dt.datetime.fromtimestamp(t, NY).date()


def avail(name: str, d: dt.date) -> dt.datetime:
    """ET-naive datetime at which the value for trading date d is known."""
    hm = SPECS[name][2]
    return dt.datetime.combine(d, dt.time(int(hm[:2]), int(hm[3:])))


SOURCE_DEFAULT = "tvremix MCP get_ohlcv interval=1D count=5000"


def convert(raw_path: str, pulled_utc: str, out_dir: str = TV_DIR, source: str = SOURCE_DEFAULT) -> str:
    d = json.load(open(raw_path))
    sym = d["symbol"]
    name = BY_SYMBOL[sym]
    kind = SPECS[name][1]
    pulled = dt.datetime.fromisoformat(pulled_utc.replace("Z", "+00:00")).astimezone(NY).replace(tzinfo=None)
    rows, dropped = [], []
    for b in sorted(d["bars"], key=lambda b: b["t"]):
        td = trade_date(b["t"], kind)
        if td.weekday() >= 5:
            raise SystemExit(f"{sym}: bar {b['t']} maps to a weekend date {td}")
        if avail(name, td) > pulled:
            dropped.append(td.isoformat()); continue
        rows.append([b["t"], b["o"], b["h"], b["l"], b["c"]])
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}.csv")
    if os.path.exists(path):
        have = {trade_date(int(r["time"]), kind): float(r["close"]) for r in csv.DictReader(open(path))}
        same = lambda a, b: abs(a - b) <= 1e-9 * max(1.0, abs(b))
        pins_p = os.path.join(out_dir, "VINTAGE_PINS.json")
        pins = (json.load(open(pins_p)) if os.path.exists(pins_p) else {}).get(name, {})
        stored = {trade_date(int(r["time"]), kind): [int(r["time"]), float(r["open"]), float(r["high"]),
                  float(r["low"]), float(r["close"])] for r in csv.DictReader(open(path))}
        pinned = []
        for i, r in enumerate(rows):
            d, c = trade_date(r[0], kind), r[4]
            p = pins.get(d.isoformat())
            if p and d in have and same(have[d], p["keep"]) and same(c, p["revised"]):
                rows[i] = stored[d]; pinned.append(d.isoformat())
        bad = [(d.isoformat(), have[d], c) for d, c in ((trade_date(r[0], kind), r[4]) for r in rows)
               if d in have and not same(have[d], c)]
        if pinned:
            print(f"  {name}: kept stored row(s) per VINTAGE_PINS.json: {pinned}")
        if bad:
            raise SystemExit(f"{sym}: VINTAGE CHANGED on {len(bad)} date(s), e.g. {bad[:3]} -- nothing written")
        if rows and trade_date(rows[-1][0], kind) < max(have):
            raise SystemExit(f"{sym}: the pull ends {trade_date(rows[-1][0], kind)}, before the file ({max(have)}) -- nothing written")
        # keep every stored row older than the pull's first session (a short pull must not shrink the file)
        first = trade_date(rows[0][0], kind) if rows else None
        older = [[int(r["time"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])]
                 for r in csv.DictReader(open(path)) if first is None or trade_date(int(r["time"]), kind) < first]
        rows = older + rows
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["time", "open", "high", "low", "close"]); w.writerows(rows)
    man_p = os.path.join(out_dir, "MANIFEST.json")
    man = json.load(open(man_p)) if os.path.exists(man_p) else {}
    man[name] = {"symbol": sym, "kind": kind, "available_et": SPECS[name][2], "rows": len(rows),
                 "first": trade_date(rows[0][0], kind).isoformat(), "last": trade_date(rows[-1][0], kind).isoformat(),
                 "dropped_partial": dropped, "pulled_utc": pulled_utc,
                 "source": source,
                 "raw_sha256": hashlib.sha256(open(raw_path, "rb").read()).hexdigest(),
                 "csv_sha256": hashlib.sha256(open(path, "rb").read()).hexdigest(),
                 "tv_series_version": VERSION}
    json.dump(man, open(man_p, "w"), indent=1, sort_keys=True)
    print(f"  {name:<6} {sym:<12} {len(rows):>5} rows {man[name]['first']} -> {man[name]['last']}"
          + (f"   dropped partial: {dropped}" if dropped else ""))
    return path


def read(name: str, tv_dir: str = TV_DIR, lo=None, hi=None):
    """[(trade_date, close)] sorted, optionally clipped to [lo, hi]."""
    kind = SPECS[name][1]
    out = []
    for r in csv.DictReader(open(os.path.join(tv_dir, f"{name}.csv"))):
        out.append((trade_date(int(r["time"]), kind), float(r["close"])))
    out.sort()
    if lo: out = [x for x in out if x[1] is not None and x[0] >= lo]
    if hi: out = [x for x in out if x[0] <= hi]
    return out


def last_date(name: str, tv_dir: str = TV_DIR):
    return read(name, tv_dir)[-1][0]


# ------------------------------------------------------------------ tests
def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"tv_series.py v{VERSION} self-test\n")
    # 17:00 Chicago on Sunday 2026-08-16 is the session of Monday 2026-08-17
    t = int(dt.datetime(2026, 8, 16, 17, 0, tzinfo=CH).timestamp())
    check("a CFE bar stamped 17:00 Chicago Sunday is Monday's session", trade_date(t, "cfe") == dt.date(2026, 8, 17))
    t2 = int(dt.datetime(2026, 9, 30, 9, 30, tzinfo=NY).timestamp())
    check("an index bar stamped 09:30 ET is that day's session", trade_date(t2, "index") == dt.date(2026, 9, 30))
    check("no series becomes available before the 16:00 ET close",
          all(avail(n, dt.date(2026, 9, 30)) >= dt.datetime(2026, 9, 30, 16, 0) for n in SPECS))
    # planted partial bar: pulled at 15:00 ET, today's bar must be dropped
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        raw = os.path.join(td, "x.json")
        t3 = int(dt.datetime(2026, 9, 29, 9, 30, tzinfo=NY).timestamp())
        json.dump({"symbol": "CBOE:SKEW", "bars": [{"t": t3, "o": 1, "h": 1, "l": 1, "c": 140.0},
                                                    {"t": t2, "o": 1, "h": 1, "l": 1, "c": 999.0}]}, open(raw, "w"))
        convert(raw, "2026-09-30T19:00:00Z", td)          # 15:00 ET on the 30th
        got = read("SKEW", td)
        check("PLANTED: a bar pulled before its session closed is dropped", got == [(dt.date(2026, 9, 29), 140.0)])
        json.dump({"symbol": "CBOE:SKEW", "bars": [{"t": t3, "o": 1, "h": 1, "l": 1, "c": 141.0}]}, open(raw, "w"))
        try:
            convert(raw, "2026-09-30T19:00:00Z", td); refused = False
        except SystemExit:
            refused = True
        check("PLANTED: a re-pull that rewrites a stored close is refused (1.1)", refused and read("SKEW", td) == [(dt.date(2026, 9, 29), 140.0)])
        t4 = int(dt.datetime(2026, 10, 1, 9, 30, tzinfo=NY).timestamp())
        json.dump({"symbol": "CBOE:SKEW", "bars": [{"t": t4, "o": 1, "h": 1, "l": 1, "c": 142.0}]}, open(raw, "w"))
        convert(raw, "2026-10-02T06:00:00Z", td)
        check("PLANTED: a short later pull appends and keeps the older stored rows", read("SKEW", td) == [(dt.date(2026, 9, 29), 140.0), (dt.date(2026, 10, 1), 142.0)])
    if os.path.exists(os.path.join(TV_DIR, "MANIFEST.json")):
        man = json.load(open(os.path.join(TV_DIR, "MANIFEST.json")))
        for n, m in sorted(man.items()):
            sha = hashlib.sha256(open(os.path.join(TV_DIR, f"{n}.csv"), "rb").read()).hexdigest()
            check(f"data/tv/{n}.csv matches its manifest sha", sha == m["csv_sha256"])
            ds = [d for d, _ in read(n)]
            check(f"data/tv/{n}.csv: no weekend dates, no duplicates", all(d.weekday() < 5 for d in ds) and len(ds) == len(set(ds)))
        old = os.path.join(HERE, "../data/CBOE_DLY_VX1!, 1D_1f2b8.csv")
        if os.path.exists(old) and "VX1" in man:
            ex = {}
            for r in list(csv.reader(open(old)))[1:]:
                ex[trade_date(int(r[0]), "cfe")] = float(r[4])
            tv = dict(read("VX1"))
            ks = sorted(set(ex) & set(tv))[:-1]          # the export's last row was partial
            check(f"VX1 matches Dave's export on {len(ks)} overlapping sessions (last export row excluded)",
                  len(ks) > 4000 and all(abs(ex[k] - tv[k]) < 1e-9 for k in ks))
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--convert", nargs="*")
    ap.add_argument("--pulled-utc")
    ap.add_argument("--out-dir", default=TV_DIR)
    ap.add_argument("--source", default=SOURCE_DEFAULT, help='e.g. "TradingView official MCP mcp-tv-get-ohlcv interval=1D count=300"')
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    for p in a.convert or []:
        convert(p, a.pulled_utc, a.out_dir, a.source)
