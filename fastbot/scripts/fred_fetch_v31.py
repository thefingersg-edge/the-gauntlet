#!/usr/bin/env python3
"""PREREGISTRATION_v31 -- fetch petrol, ADP, claims and the market
backdrop from FRED. RUN LOCALLY. The key is read from $FRED_API_KEY or
~/.fred_key and is never printed. Public data, read only. Resumable.

    python3 fred_fetch_v31.py --self-test
    python3 fred_fetch_v31.py            # ~20-25 minutes
"""
from __future__ import annotations

import argparse, csv, datetime as dt, json, os, re, sys, time
import urllib.error, urllib.parse, urllib.request

from release_content import load_key

VERSION = "1.0"
API = "https://api.stlouisfed.org/fred/series/observations"
OUT = "../data/v31"
FULL = ("GASREGW", "DGS2", "DTWEXBGS")          # market prices, current vintage
PAUSE = 0.55
_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)


def call(series, key, **q):
    q = dict(series_id=series, api_key=key, file_type="json", **q)
    url = API + "?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"User-Agent": "fastbot-v31"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def obs(js, keep=None):
    o = [(x["date"], x["value"]) for x in js.get("observations", [])
         if x.get("value") not in (None, "", ".")]
    return o if keep is None else o[-keep:]


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"fred_fetch_v31.py v{VERSION} self-test\n")
    js = {"observations": [{"date": "2020-01-04", "value": "210000"},
                           {"date": "2020-01-11", "value": "."},
                           {"date": "2020-01-18", "value": "220000"}]}
    check("missing values are skipped", obs(js) == [("2020-01-04", "210000"),
                                                    ("2020-01-18", "220000")])
    check("keep takes the LAST n", obs(js, 1) == [("2020-01-18", "220000")])
    check("three market series in full, nothing else",
          FULL == ("GASREGW", "DGS2", "DTWEXBGS"))
    check("no order, execute, submit or position name in this file",
          not [n for n in globals() if _FORBIDDEN.search(n)])
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="../data/events_v2.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    key = load_key()
    if not key:
        print("no FRED key: set $FRED_API_KEY or ~/.fred_key"); sys.exit(2)
    os.makedirs(OUT, exist_ok=True)
    print(f"fred_fetch_v31.py v{VERSION}   PREREGISTRATION_v31 -- public data,"
          f" the key is not printed\n")

    for s in FULL:
        p = f"{OUT}/{s}.csv"
        if os.path.exists(p):
            print(f"  {s:<9} already on disk"); continue
        try:
            o = obs(call(s, key, observation_start="2000-01-01"))
            with open(p, "w", newline="") as fh:
                w = csv.writer(fh); w.writerow(["date", "value"]); w.writerows(o)
            print(f"  {s:<9} {len(o):>6} observations  {o[0][0]} .. {o[-1][0]}")
        except Exception as e:                                   # noqa: BLE001
            print(f"  {s:<9} FAILED ({type(e).__name__} {getattr(e, 'code', '')})")
        time.sleep(PAUSE)

    #: vintage requests: (series, event_date, vintage_date, keep)
    todo = []
    for r in csv.DictReader(open(a.events)):
        if not r.get("time_et", "").startswith("08:3"):
            continue
        d = dt.date.fromisoformat(r["date"])
        if d.year < 2003 or d >= dt.date.today():
            continue
        if r["event"] == "NFP":
            todo.append(("NPPTTL", d, d - dt.timedelta(days=1), 2))
        elif r["event"] == "CLAIMS":
            todo.append(("ICSA", d, d - dt.timedelta(days=1), 5))   # predictor
            todo.append(("ICSA", d, d, 2))                          # the print
    p = f"{OUT}/vintages.csv"
    done = set()
    if os.path.exists(p):
        for r in csv.DictReader(open(p)):
            done.add((r["series"], r["event_date"], r["vintage_date"]))
    new = not os.path.exists(p)
    fh = open(p, "a", newline="")
    w = csv.writer(fh)
    if new:
        w.writerow(["series", "event_date", "vintage_date", "status",
                    "obs_date", "value"])
    left = [t for t in todo if (t[0], t[1].isoformat(), t[2].isoformat()) not in done]
    print(f"\n  {len(todo):,} vintage requests, {len(left):,} to fetch")
    stat = {}
    for i, (s, d, v, keep) in enumerate(left, 1):
        try:
            js = call(s, key, realtime_start=v.isoformat(), realtime_end=v.isoformat(),
                      observation_start=(v - dt.timedelta(days=500)).isoformat())
            o = obs(js, keep)
            status = "ok" if o else "empty"
        except urllib.error.HTTPError as e:
            o, status = [], f"http{e.code}"
        except Exception as e:                                   # noqa: BLE001
            o, status = [], type(e).__name__
        stat[(s, status)] = stat.get((s, status), 0) + 1
        if not o:
            w.writerow([s, d.isoformat(), v.isoformat(), status, "", ""])
        for od, val in o:
            w.writerow([s, d.isoformat(), v.isoformat(), status, od, val])
        fh.flush()
        if i % 200 == 0:
            print(f"  {i:,}/{len(left):,}   " + "  ".join(
                f"{k[0]} {k[1]} {n}" for k, n in sorted(stat.items())))
        time.sleep(PAUSE)
    fh.close()
    print("\n  done: " + "  ".join(f"{k[0]} {k[1]} {n}" for k, n in sorted(stat.items())))
    print(f"  written to {OUT}/. Paste me this output.")


if __name__ == "__main__":
    main()
