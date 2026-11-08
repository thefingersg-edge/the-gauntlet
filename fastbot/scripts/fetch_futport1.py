#!/usr/bin/env python3
"""
fetch_futport1.py -- FUTPORT1 data (PREREGISTRATION_FUTPORT1.md): CME daily bars from Databento, continuous calendar front and
second (ROOT.c.0, ROOT.c.1) for 29 roots, 2010-06-06 -> 2026-10-01. READ-ONLY market data; places no orders.
RUN ON THE MAC. Needs a Databento key in $DATABENTO_API_KEY or ~/.databento_key (never printed). It costs money, so the script first
asks Databento for the price and downloads ONLY with --confirm, and only if the total is under --max-usd (default 25).
    python3 fetch_futport1.py --self-test
    python3 fetch_futport1.py                # prints the cost, downloads nothing
    python3 fetch_futport1.py --confirm      # downloads one file per symbol (resumable), then writes futport1.meta.json
Pattern copied from flows/fetch_futures.py (FLOWS-15). v1.1: per-year requests with retries (a 15-minute server timeout on ZC).
I am not a financial adviser. This is a measurement, not a recommendation.
"""
from __future__ import annotations
import datetime as dt, hashlib, json, os, subprocess, sys, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "data", "futport1"); META = os.path.join(D, "futport1.meta.json")
API = "https://hist.databento.com/v0/"
ROOTS = ["ES", "NQ", "YM", "RTY", "ZT", "ZF", "ZN", "ZB", "6E", "6J", "6B", "6A", "6C", "6S",
         "GC", "SI", "HG", "PL", "CL", "NG", "HO", "RB", "ZC", "ZS", "ZW", "ZL", "ZM", "LE", "HE"]
SYMS = [f"{r}.c.{k}" for r in ROOTS for k in (0, 1)]
START, END = "2010-06-06", "2026-10-01"


def key():
    k = os.environ.get("DATABENTO_API_KEY", "").strip(); p = os.path.expanduser("~/.databento_key")
    if not k and os.path.exists(p): k = open(p).read().strip()
    if not k: raise SystemExit("STOP: no Databento key ($DATABENTO_API_KEY or ~/.databento_key)")
    return k


def call(endpoint, params, k, out=None):
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    cmd = ["curl", "-sS", "--fail", "-u", f"{k}:", "--max-time", "600", url]
    if out: cmd += ["-o", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(f"{endpoint}: {r.stderr.strip()[:300]}")
    return r.stdout


def params(sym, **kw):
    return dict(dataset="GLBX.MDP3", symbols=sym, stype_in="continuous", schema="ohlcv-1d", start=START, end=END, **kw)


def fname(sym): return os.path.join(D, sym.replace(".", "_") + ".csv")


def years():
    for y in range(int(START[:4]), int(END[:4]) + 1):
        a = max(START, f"{y}-01-01"); b = min(END, f"{y + 1}-01-01")
        if a < b: yield y, a, b


def fetch_chunked(sym, p, k):
    """v1.1 (mechanical, 2026-10-12): one request per calendar year, each to its own part file, so a slow server reply costs one year,
    not the whole symbol. A part is only kept if curl finished. Parts are joined (one header) into the final file at the end."""
    parts = []
    for y, a, b in years():
        part = p + f".{y}.part"
        if not os.path.exists(part):
            tmp = part + ".tmp"
            for attempt in range(3):
                try:
                    call("timeseries.get_range", dict(params(sym, encoding="csv", pretty_px="true", pretty_ts="true", map_symbols="true"), start=a, end=b), k, out=tmp)
                    os.replace(tmp, part); break
                except RuntimeError as ex:
                    print(f"    {sym} {y}: attempt {attempt + 1} failed ({str(ex)[:80]})", flush=True)
                    if os.path.exists(tmp): os.remove(tmp)
            else:
                raise SystemExit(f"STOP: {sym} {y} failed 3 times -- re-run later; finished parts are kept")
        parts.append(part)
    with open(p + ".tmp", "w") as out:
        head = None
        for part in parts:
            lines = open(part).read().splitlines()
            if not lines: continue
            if head is None: head = lines[0]; out.write(head + "\n")
            for ln in lines[1:]:
                if ln: out.write(ln + "\n")
    os.replace(p + ".tmp", p)
    for part in parts: os.remove(part)


def main(confirm, max_usd):
    k = key(); total = 0.0
    for s in SYMS:
        c = float(call("metadata.get_cost", params(s), k)); total += c
    print(f"{len(SYMS)} symbols, TOTAL ${total:.2f} (limit ${max_usd:.2f})")
    if not confirm: print("Nothing downloaded. Re-run with --confirm to buy and download."); return 0
    if total > max_usd: raise SystemExit("STOP: cost above --max-usd")
    os.makedirs(D, exist_ok=True)
    meta = {"built_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "cost_usd": total, "files": {}}
    for s in SYMS:
        p = fname(s)
        if not os.path.exists(p) or os.path.getsize(p) < 200:
            fetch_chunked(s, p, k)
        meta["files"][os.path.basename(p)] = dict(bytes=os.path.getsize(p), sha256=hashlib.sha256(open(p, "rb").read()).hexdigest())
        print(f"  {os.path.basename(p)} {os.path.getsize(p):,} bytes", flush=True)
    json.dump(meta, open(META, "w"), indent=1); print("done ->", META)
    return 0


def self_test():
    ok = len(ROOTS) == 29 and len(set(ROOTS)) == 29 and len(SYMS) == 58 and fname("6E.c.0").endswith("6E_c_0.csv")
    print(f"  {'PASS' if ok else 'FAIL'}  29 roots, 58 symbols, file names"); return 0 if ok else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv: sys.exit(self_test())
    mx = float(sys.argv[sys.argv.index("--max-usd") + 1]) if "--max-usd" in sys.argv else 25.0
    sys.exit(main("--confirm" in sys.argv, mx))
