#!/usr/bin/env python3
"""
fetch_tsyfut.py -- FLOWS-17 data (PREREGISTRATION_TSYFUT.md): CME Treasury futures best bid/ask at one-minute
intervals (Databento GLBX.MDP3, schema bbo-1m), volume-ranked front contract ZN.v.0 and ZB.v.0, 2010-06-07 -> 2026-09-01.
READ-ONLY market data; places no orders.

RUN ON THE MAC. Needs a Databento key in $DATABENTO_API_KEY or ~/.databento_key (never printed). It costs money, so
the script first asks Databento for the price and downloads ONLY with --confirm, and only if the total is under --max-usd.
    python3 fetch_tsyfut.py --self-test
    python3 fetch_tsyfut.py                 # prints the cost, downloads nothing
    python3 fetch_tsyfut.py --confirm       # downloads (resumable, one request per year), then writes tsyfut.meta.json
Pattern copied from fastbot/scripts/fetch_futport1.py v1.1. Computes NO returns.
I am not a financial adviser. This is a measurement, not a recommendation.
"""
from __future__ import annotations
import datetime as dt, hashlib, json, os, subprocess, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data", "tsyfut"); META = os.path.join(D, "tsyfut.meta.json")
API = "https://hist.databento.com/v0/"
SYMS = ["ZN.v.0", "ZB.v.0"]
START, END = "2010-06-07", "2026-09-01"
SCHEMA = "bbo-1m"


def key():
    k = os.environ.get("DATABENTO_API_KEY", "").strip(); p = os.path.expanduser("~/.databento_key")
    if not k and os.path.exists(p): k = open(p).read().strip()
    if not k: raise SystemExit("STOP: no Databento key ($DATABENTO_API_KEY or ~/.databento_key)")
    return k


def call(endpoint, params, k, out=None):
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    cmd = ["curl", "-sS", "--fail", "-u", f"{k}:", "--max-time", "900", url]
    if out: cmd += ["-o", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(f"{endpoint}: {r.stderr.strip()[:300]}")
    return r.stdout


def params(sym, **kw):
    p = dict(dataset="GLBX.MDP3", symbols=sym, stype_in="continuous", schema=SCHEMA, start=START, end=END)
    p.update(kw); return p


def fname(sym): return os.path.join(D, sym.replace(".", "_") + ".csv")


def years():
    for y in range(int(START[:4]), int(END[:4]) + 1):
        a = max(START, f"{y}-01-01"); b = min(END, f"{y + 1}-01-01")
        if a < b: yield y, a, b


def fetch_chunked(sym, p, k):
    parts = []
    for y, a, b in years():
        part = p + f".{y}.part"
        if not os.path.exists(part):
            tmp = part + ".tmp"
            for attempt in range(3):
                try:
                    call("timeseries.get_range", params(sym, start=a, end=b, encoding="csv", pretty_px="true",
                                                        pretty_ts="true", map_symbols="true"), k, out=tmp)
                    os.replace(tmp, part); break
                except RuntimeError as ex:
                    print(f"    {sym} {y}: attempt {attempt + 1} failed ({str(ex)[:80]})", flush=True)
                    if os.path.exists(tmp): os.remove(tmp)
            else:
                raise SystemExit(f"STOP: {sym} {y} failed 3 times -- re-run later; finished years are kept")
        print(f"    {sym} {y} ok", flush=True)
        parts.append(part)
    with open(p + ".tmp", "w") as out:
        head = None
        for part in parts:
            with open(part) as fh:
                first = fh.readline()
                if not first: continue
                if head is None: head = first; out.write(head)
                for ln in fh:
                    if ln.strip(): out.write(ln)
    os.replace(p + ".tmp", p)
    for part in parts: os.remove(part)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def main(confirm, max_usd):
    k = key(); total = 0.0
    for s in SYMS:
        c = float(call("metadata.get_cost", params(s), k)); total += c
        print(f"  {s} {SCHEMA} {START} -> {END}: ${c:.2f}")
    print(f"TOTAL ${total:.2f} (limit ${max_usd:.2f})")
    if not confirm: print("Nothing downloaded. Re-run with --confirm to buy and download."); return 0
    if total > max_usd: raise SystemExit("STOP: cost above --max-usd")
    os.makedirs(D, exist_ok=True)
    meta = {"built_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "cost_usd": total,
            "schema": SCHEMA, "start": START, "end": END, "files": {}}
    for s in SYMS:
        p = fname(s)
        if not os.path.exists(p) or os.path.getsize(p) < 200:
            fetch_chunked(s, p, k)
        meta["files"][os.path.basename(p)] = dict(bytes=os.path.getsize(p), sha256=sha(p))
        print(f"  {os.path.basename(p)} {os.path.getsize(p):,} bytes", flush=True)
    json.dump(meta, open(META, "w"), indent=1); print("done ->", META)
    return 0


def self_test():
    ys = list(years())
    ok = (SYMS == ["ZN.v.0", "ZB.v.0"] and fname("ZN.v.0").endswith("ZN_v_0.csv") and ys[0] == (2010, "2010-06-07", "2011-01-01")
          and ys[-1] == (2026, "2026-01-01", "2026-09-01") and params("ZN.v.0")["schema"] == "bbo-1m")
    print(f"  {'PASS' if ok else 'FAIL'}  symbols, schema, file names, yearly chunks 2010-06-07 .. 2026-09-01"); return 0 if ok else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv: sys.exit(self_test())
    mx = float(sys.argv[sys.argv.index("--max-usd") + 1]) if "--max-usd" in sys.argv else 25.0
    sys.exit(main("--confirm" in sys.argv, mx))
