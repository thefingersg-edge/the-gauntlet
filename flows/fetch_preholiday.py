#!/usr/bin/env python3
"""fetch_preholiday.py -- FLOWS-10 Step 0: NYSE closures and pre-holiday days
(offline, by rule). Writes data/preholiday_events.csv. No price is read.
    python3 fetch_preholiday.py --self-test | (no args)"""
from __future__ import annotations
import csv, datetime as dt, hashlib, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from fetch_eia_calendar import _nth_weekday, _last_weekday, _observed   # noqa: E402
from refunding_events import _easter                                     # noqa: E402
OUT = os.path.join(HERE, "data", "preholiday_events.csv")
SPECIAL = {dt.date(2007, 1, 2): "Ford mourning", dt.date(2012, 10, 29): "Sandy", dt.date(2012, 10, 30): "Sandy",
           dt.date(2018, 12, 5): "Bush mourning", dt.date(2025, 1, 9): "Carter mourning"}


def nyse_holidays(y):
    h = {}
    nyd = dt.date(y, 1, 1)
    if nyd.weekday() == 6: h[nyd + dt.timedelta(days=1)] = "New Year"
    elif nyd.weekday() < 5: h[nyd] = "New Year"           # NYSE does not observe a Saturday New Year on Friday
    h[_nth_weekday(y, 1, 0, 3)] = "MLK"
    h[_nth_weekday(y, 2, 0, 3)] = "Presidents"
    h[_easter(y) - dt.timedelta(days=2)] = "Good Friday"
    h[_last_weekday(y, 5, 0)] = "Memorial"
    if y >= 2022: h[_observed(dt.date(y, 6, 19))] = "Juneteenth"
    h[_observed(dt.date(y, 7, 4))] = "Independence"
    h[_nth_weekday(y, 9, 0, 1)] = "Labor"
    h[_nth_weekday(y, 11, 3, 4)] = "Thanksgiving"
    h[_observed(dt.date(y, 12, 25))] = "Christmas"
    return h


def build():
    closed = {}
    for y in range(2004, 2028):
        closed.update(nyse_holidays(y))
    closed.update(SPECIAL)
    rows, seen = [], set()
    for d in sorted(closed):
        if not (dt.date(2005, 1, 3) <= d <= dt.date(2026, 9, 30)):
            continue
        p = d - dt.timedelta(days=1)
        while p.weekday() >= 5 or p in closed:
            p -= dt.timedelta(days=1)
        if p in seen or p < dt.date(2005, 1, 3) or p > dt.date(2026, 8, 31):
            continue
        seen.add(p)
        rows.append((p.isoformat(), d.isoformat(), closed[d]))
    return rows, closed


def main():
    rows, _ = build()
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["pre_day", "holiday", "name"]); w.writerows(rows)
    print(f"{len(rows)} pre-holiday days; sha256 {hashlib.sha256(open(OUT,'rb').read()).hexdigest()}")
    return 0


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    h = nyse_holidays(2022)
    check("2022: New Year on Sat 1 Jan not observed on Fri 31 Dec 2021", dt.date(2021, 12, 31) not in nyse_holidays(2021) and dt.date(2022, 1, 1) not in h)
    check("Good Friday 2024 = 29 Mar", dt.date(2024, 3, 29) in nyse_holidays(2024))
    check("Juneteenth 2022 observed Mon 20 Jun", dt.date(2022, 6, 20) in h)
    rows, closed = build()
    r = {x[1]: x[0] for x in rows}
    check("pre-day of Thanksgiving 2025 = Wed 26 Nov", r.get("2025-11-27") == "2025-11-26")
    check("pre-day of Memorial Day 2025 (Mon 26 May) = Fri 23 May", r.get("2025-05-26") == "2025-05-23")
    check("Sandy: one pre-day (Fri 26 Oct 2012) for the two-day closure", r.get("2012-10-29") == "2012-10-26" and "2012-10-30" not in r)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
