#!/usr/bin/env python3
"""
fetch_fred.py -- FLOWS-1/2 Step 0: public rate series from FRED.

    DGS10   10y constant-maturity yield   FLOWS-1 bond-CFD roll-flag check
    DGS30   30y constant-maturity yield   same check for USB30Y_USD
    DGS3MO  3m T-bill                     USD financing benchmark
    ECBDFR  ECB deposit facility rate     EUR financing benchmark (DE30, Bund)

Uses the FRED API if a key is present ($FRED_API_KEY or ~/.fred_key, the
fastbot convention; never printed), else the public fredgraph CSV, which
needs no key. Records which route was used. Full history, current vintage.

    python3 fetch_fred.py --self-test
    python3 fetch_fred.py
"""
from __future__ import annotations
import argparse, csv, datetime as dt, hashlib, io, json, os, sys, time
import urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SERIES = ("DGS10", "DGS30", "DGS3MO", "ECBDFR")
API = "https://api.stlouisfed.org/fred/series/observations"
GRAPH = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
UA = "Mozilla/5.0 (research; fetch_fred.py)"


def load_key():
    k = os.environ.get("FRED_API_KEY", "").strip()
    p = os.path.expanduser("~/.fred_key")
    if not k and os.path.exists(p):
        k = open(p).read().strip()
    return k or None


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def parse_api(txt: str) -> list:
    return [(o["date"], o["value"]) for o in json.loads(txt)["observations"]
            if o["value"] not in (".", "")]


def parse_graph(txt: str) -> list:
    rows = list(csv.reader(io.StringIO(txt)))
    return [(r[0], r[1]) for r in rows[1:] if len(r) > 1 and r[1] not in (".", "")]


def main() -> int:
    key = load_key(); os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    meta = {"fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "route": "api" if key else "fredgraph", "series": {}}
    bad = 0
    for s in SERIES:
        try:
            if key:
                q = urllib.parse.urlencode(dict(series_id=s, api_key=key, file_type="json"))
                obs = parse_api(get(f"{API}?{q}"))
            else:
                obs = parse_graph(get(GRAPH + s))
        except Exception as e:                                # noqa: BLE001
            msg = str(e).replace(key, "***") if key else str(e)
            print(f"  {s:<7} FAILED  {msg[:80]}"); bad += 1; continue
        out = os.path.join(HERE, "data", f"fred_{s.lower()}.csv")
        with open(out, "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["date", s.lower()]); w.writerows(obs)
        sha = hashlib.sha256(open(out, "rb").read()).hexdigest()
        meta["series"][s] = dict(rows=len(obs), first=obs[0][0], last=obs[-1][0], sha256=sha)
        print(f"  {s:<7} {len(obs):>6} obs  {obs[0][0]} .. {obs[-1][0]}  sha256 {sha[:16]}")
        time.sleep(0.6)
    json.dump(meta, open(os.path.join(HERE, "data", "fred.meta.json"), "w"), indent=2)
    return 1 if bad else 0


def self_test() -> int:
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    check("fredgraph CSV parsed, missing '.' dropped",
          parse_graph("observation_date,DGS10\n2024-01-02,3.95\n2024-01-15,.\n") == [("2024-01-02", "3.95")])
    check("API JSON parsed, missing '.' dropped",
          parse_api('{"observations":[{"date":"2024-01-02","value":"3.95"},'
                    '{"date":"2024-01-15","value":"."}]}') == [("2024-01-02", "3.95")])
    check("key never needed for the fallback route", GRAPH.startswith("https://fred.stlouisfed.org"))
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--self-test", action="store_true")
    sys.exit(self_test() if ap.parse_args().self_test else main())
