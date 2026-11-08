#!/usr/bin/env python3
"""FORWARD_v36 -- record the v36 noise-band rule on NAS100, forward only.

Run by forward_tick.sh after the v25 ledger. NON-FATAL there. RECORDS ONLY:
nothing here places an order or touches a broker account. Rules are
momentum_v36.py's noise_rows(), imported unchanged, on OANDA M5 bid/ask
pulled into ../data/v36fwd (never the historical files).

A session is written once, after it is complete (its date is before today in
New York), and never rewritten. Sessions before START are warm-up only.

    python3 forward_noiseband.py --self-test
    python3 forward_noiseband.py
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import sys
from zoneinfo import ZoneInfo

from momentum_v36 import noise_rows
from reactive import load

VERSION = "1.1"   # 1.1 (FORWARD_v36.1): also writes sessions with no trade (trades 0) and sessions that could not be evaluated (trades blank)
#: FORWARD_v36.1 -- from this session on, every complete NAS100 session gets a
#: row, so a missing day can no longer mean either "no trade" or "no data".
ZERO_START = dt.date(2026, 10, 5)
START = dt.date(2026, 9, 28)          # first forward session, FORWARD_v36 s.2
INS = "nas100usd"
DATA = "../data/v36fwd"
OUT = "../data/forward_noiseband.csv"
COLS = ["date", "trades", "gross_bp", "net_bp", "recorded_utc"]
_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)
assert not [n for n in list(globals()) if _FORBIDDEN.search(n)]


def done_dates(path):
    if not os.path.exists(path):
        return set()
    return {r["date"] for r in csv.DictReader(open(path))}


def new_rows(days, today, have):
    traded = noise_rows(days, INS)                        # the v36 rule, unchanged
    rows = [r for r in traded
            if START <= r["date"] < today and r["date"].isoformat() not in have]
    tdates = {r["date"] for r in traded}
    ds = sorted(days)
    for p, d in zip(ds, ds[1:]):                          # FORWARD_v36.1
        if d < max(START, ZERO_START) or d >= today or d in tdates or d.isoformat() in have:
            continue
        ok = "09:30" in days[d] and "15:55" in days[d] and "15:55" in days[p]
        rows.append(dict(ins=INS, date=d, n=0 if ok else "", Ng=0.0 if ok else None, Nn=0.0 if ok else None))
    return sorted(rows, key=lambda r: r["date"])


def record(data_dir, out, today):
    days = load(data_dir, INS)
    have = done_dates(out)
    rows = new_rows(days, today, have)
    fresh = not os.path.exists(out)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(out, "a", newline="") as fh:
        w = csv.writer(fh)
        if fresh:
            w.writerow(COLS)
        for r in rows:
            f = lambda x: "" if x is None else f"{x:.4f}"
            w.writerow([r["date"].isoformat(), r["n"], f(r["Ng"]), f(r["Nn"]), now])
    return rows


def self_test():
    import tempfile, shutil
    ok = True

    def check(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

    print(f"forward_noiseband.py v{VERSION} self-test (historical 5m data)\n")
    days = load("../data", INS)
    global START
    keep = START
    START = dt.date(2026, 6, 1)
    tmp = tempfile.mkdtemp()
    out = os.path.join(tmp, "f.csv")
    try:
        cut = dt.date(2026, 7, 1)
        r1 = new_rows(days, cut, set())
        check("only complete sessions before 'today' are written",
              all(START <= r["date"] < cut for r in r1) and len(r1) > 5)
        with open(out, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(COLS)
            for r in r1:
                w.writerow([r["date"].isoformat(), r["n"], r["Ng"], r["Nn"], "x"])
        r2 = new_rows(days, dt.date(2026, 8, 1), done_dates(out))
        check("PLANTED: a second run never rewrites a recorded session",
              not ({r["date"] for r in r2} & {r["date"] for r in r1}) and r2)
        check("warm-up sessions before START are never written",
              all(r["date"] >= START for r in r1 + r2))
    finally:
        START = keep
        shutil.rmtree(tmp)
    check("START is frozen at 2026-09-28", START == dt.date(2026, 9, 28))
    print("\nFORWARD_v36.1: sessions without a trade are written too")
    global ZERO_START
    kz, ks = ZERO_START, START
    START, ZERO_START = dt.date(2026, 6, 1), dt.date(2026, 6, 1)
    try:
        cut = dt.date(2026, 7, 1)
        rows = new_rows(days, cut, set())
        old = [r for r in noise_rows(days, INS) if START <= r["date"] < cut]
        check("traded sessions are exactly v1.0's (the rule is untouched)",
              [(r["date"], r["n"], r["Ng"]) for r in rows if r["n"] not in (0, "")]
              == [(r["date"], r["n"], r["Ng"]) for r in old])
        sess = [d for d in sorted(days)[1:] if START <= d < cut]
        check(f"every session in the window has exactly one row ({len(rows)} rows, {len(sess)} sessions)",
              sorted(r["date"] for r in rows) == sess)
        check("and some of them are zero-trade rows", any(r["n"] == 0 for r in rows))
        d0 = next(r["date"] for r in rows if r["n"] == 0)
        broken = {k: dict(v) for k, v in days.items()}
        broken[d0].pop("15:55", None)
        rb = {r["date"]: r for r in new_rows(broken, cut, set())}
        check("PLANTED: a session missing its 15:55 bar is written as a skip (trades blank)",
              d0 in rb and rb[d0]["n"] == "" and rb[d0]["Ng"] is None)
        ZERO_START = dt.date(2026, 10, 5)
        check("sessions before ZERO_START get no zero or skip rows (v1.0 behaviour)",
              all(r["n"] not in (0, "") for r in new_rows(days, cut, set())))
    finally:
        START, ZERO_START = ks, kz
    check("ZERO_START is frozen at 2026-10-05", ZERO_START == dt.date(2026, 10, 5))
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    here = os.path.dirname(os.path.abspath(__file__))
    today = dt.datetime.now(ZoneInfo("America/New_York")).date()
    rows = record(os.path.join(here, DATA), os.path.join(here, OUT), today)
    print(f"forward_noiseband v{VERSION}: {len(rows)} new session(s) recorded"
          + ("" if not rows else f", last {rows[-1]['date']}"))


if __name__ == "__main__":
    main()
