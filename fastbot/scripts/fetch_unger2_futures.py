#!/usr/bin/env python3
"""
fetch_unger2_futures.py -- UNGER2 Part F (PREREGISTRATION_UNGER2.md): CME CL and GC 1-minute OHLCV from Databento.
Mechanical copy of flows/fetch_futures.py (FLOWS-15); only the symbols, dates and folder differ. READ-ONLY market data.
RUN ON THE MAC. Needs a Databento API key in $DATABENTO_API_KEY or ~/.databento_key
(never printed). Costs money: the script first asks Databento for the price and
downloads ONLY with --confirm, and only if the total is under --max-usd (default 25).
    python3 fetch_unger2_futures.py --self-test
    python3 fetch_unger2_futures.py            # prints the cost, downloads nothing
    python3 fetch_unger2_futures.py --confirm  # downloads, year by year, resumable
"""
from __future__ import annotations
import datetime as dt, hashlib, json, os, subprocess, sys, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "data", "unger2", "futures"); META = os.path.join(HERE, "..", "data", "unger2", "futures.meta.json")
API = "https://hist.databento.com/v0/"
SYMS = ["CL.v.0", "GC.v.0"]
START, END = "2010-06-07", "2026-10-01"


def key():
    k = os.environ.get("DATABENTO_API_KEY", "").strip()
    p = os.path.expanduser("~/.databento_key")
    if not k and os.path.exists(p):
        k = open(p).read().strip()
    if not k:
        raise SystemExit("STOP: no Databento key ($DATABENTO_API_KEY or ~/.databento_key)")
    return k


def call(endpoint, params, k, out=None):
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    cmd = ["curl", "-sS", "--fail", "-u", f"{k}:", "--max-time", "900", url]
    if out:
        cmd += ["-o", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{endpoint}: {r.stderr.strip()[:300]}")
    return r.stdout


def params(sym, a, b, **kw):
    return dict(dataset="GLBX.MDP3", symbols=sym, stype_in="continuous", schema="ohlcv-1m", start=a, end=b, **kw)


def years():
    y0, y1 = int(START[:4]), int(END[:4])
    for y in range(y0, y1 + 1):
        a = max(START, f"{y}-01-01"); b = min(END, f"{y + 1}-01-01")
        if a < b:
            yield y, a, b


def main(confirm: bool, max_usd: float):
    k = key()
    total = 0.0
    for s in SYMS:
        c = float(call("metadata.get_cost", params(s, START, END), k))
        print(f"  {s}: ${c:.2f}"); total += c
    print(f"TOTAL ${total:.2f} (limit ${max_usd:.2f})")
    if not confirm:
        print("Nothing downloaded. Re-run with --confirm to buy and download."); return 0
    if total > max_usd:
        raise SystemExit("STOP: cost above --max-usd")
    os.makedirs(D, exist_ok=True)
    meta = {"built_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "cost_usd": total, "files": {}}
    for s in SYMS:
        for y, a, b in years():
            p = os.path.join(D, f"{s.split('.')[0]}_{y}.csv")
            if not os.path.exists(p) or os.path.getsize(p) < 1000:
                call("timeseries.get_range", params(s, a, b, encoding="csv", pretty_px="true", pretty_ts="true",
                                                   map_symbols="true"), k, out=p)
            meta["files"][os.path.basename(p)] = dict(bytes=os.path.getsize(p),
                                                      sha256=hashlib.sha256(open(p, "rb").read()).hexdigest())
            print(f"  {os.path.basename(p)} {os.path.getsize(p):,} bytes")
    json.dump(meta, open(META, "w"), indent=1)
    return 0


def self_test():
    ys = list(years())
    ok = ys[0] == (2010, "2010-06-07", "2011-01-01") and ys[-1] == (2026, "2026-01-01", "2026-10-01")
    print(f"  {'PASS' if ok else 'FAIL'}  yearly chunks cover {START}..{END}")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    mx = float(sys.argv[sys.argv.index("--max-usd") + 1]) if "--max-usd" in sys.argv else 25.0
    sys.exit(main("--confirm" in sys.argv, mx))
