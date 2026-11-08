#!/usr/bin/env python3
"""
fetch_eia_calendar.py -- FLOWS-6 Step 0: the EIA storage-report calendar.

OFFLINE and deterministic: no network, no price. Implements
PREREGISTRATION_NATGAS.md section 1 exactly:

  * report day = the Thursday of each Monday-Friday week, 10:30 ET
  * a week containing a US federal holiday (observed) on any weekday is
    EXCLUDED ENTIRELY -- from the event group and the control group
  * special federal closures are treated the same way
  * weeks inside the 2013, 2018-19 and 2025 shutdowns are excluded

Writes flows/data/eia_events.csv with one row per Monday of every week
2005-01-03 .. 2026-08-31: week_monday, report_day (the Thursday, or blank),
status (REPORT | EXCLUDED), reason.

    python3 fetch_eia_calendar.py --self-test
    python3 fetch_eia_calendar.py            # writes the table, prints its sha256

Also provides federal_holidays(), used by fetch_announce.py (ISM rule).
Plain python3, no pandas.
"""
from __future__ import annotations
import csv, datetime as dt, hashlib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "eia_events.csv")
START, END = dt.date(2005, 1, 3), dt.date(2026, 8, 31)

#: section 1: one-off federal closures (national days of mourning, Sandy)
SPECIAL_CLOSURES = [dt.date(2007, 1, 2), dt.date(2012, 10, 29), dt.date(2012, 10, 30),
                    dt.date(2018, 12, 5), dt.date(2025, 1, 9)]
#: section 1: federal shutdowns, inclusive
SHUTDOWNS = [(dt.date(2013, 10, 1), dt.date(2013, 10, 16)),
             (dt.date(2018, 12, 22), dt.date(2019, 1, 25)),
             (dt.date(2025, 10, 1), dt.date(2025, 11, 12))]


def _nth_weekday(y, m, wd, n):
    d = dt.date(y, m, 1)
    d += dt.timedelta(days=(wd - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def _last_weekday(y, m, wd):
    d = dt.date(y, m + 1, 1) - dt.timedelta(days=1) if m < 12 else dt.date(y, 12, 31)
    return d - dt.timedelta(days=(d.weekday() - wd) % 7)


def _observed(d):
    return d - dt.timedelta(days=1) if d.weekday() == 5 else (
        d + dt.timedelta(days=1) if d.weekday() == 6 else d)


def federal_holidays(y: int) -> set:
    """US federal holidays, observed dates, that fall in calendar year y
    (a Saturday New Year's Day observed on 31 Dec lands in y-1's set too,
    because the function is evaluated for y+1 as well by callers)."""
    h = set()
    for yy in (y, y + 1):
        s = {_observed(dt.date(yy, 1, 1)), _nth_weekday(yy, 1, 0, 3), _nth_weekday(yy, 2, 0, 3),
             _last_weekday(yy, 5, 0), _observed(dt.date(yy, 7, 4)), _nth_weekday(yy, 9, 0, 1),
             _nth_weekday(yy, 10, 0, 2), _observed(dt.date(yy, 11, 11)), _nth_weekday(yy, 11, 3, 4),
             _observed(dt.date(yy, 12, 25))}
        if yy >= 2021:
            s.add(_observed(dt.date(yy, 6, 19)))   # Juneteenth: first observed Fri 2021-06-18
        h |= {d for d in s if d.year == y}
    return h


def build():
    hol = set()
    for y in range(START.year - 1, END.year + 2):
        hol |= federal_holidays(y)
    closed = hol | set(SPECIAL_CLOSURES)
    rows = []
    mon = START - dt.timedelta(days=START.weekday())
    while mon <= END:
        week = [mon + dt.timedelta(days=i) for i in range(5)]
        thu = week[3]
        why = []
        hs = [d for d in week if d in closed]
        if hs:
            why.append("holiday " + " ".join(d.isoformat() for d in hs))
        if any(a <= d <= b for d in week for a, b in SHUTDOWNS):
            why.append("shutdown")
        if thu > END or thu < START:
            why.append("outside sample")
        if why:
            rows.append((mon.isoformat(), "", "EXCLUDED", "; ".join(why)))
        else:
            rows.append((mon.isoformat(), thu.isoformat(), "REPORT", ""))
        mon += dt.timedelta(days=7)
    return rows


def main() -> int:
    rows = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["week_monday", "report_day", "status", "reason"])
        w.writerows(rows)
    n = sum(r[2] == "REPORT" for r in rows)
    per = {}
    for r in rows:
        if r[2] == "REPORT":
            per[r[1][:4]] = per.get(r[1][:4], 0) + 1
    print(f"weeks {len(rows)}   report days {n}   excluded {len(rows) - n}")
    print("per year: " + " ".join(f"{y}:{c}" for y, c in sorted(per.items())))
    # 2025 loses six shutdown weeks and 2026 is a part year; every other year
    # must hold 38-50. NOTE: the pre-registration expected ~1,030 report days;
    # excluding Monday-holiday weeks too (as section 1 says: "any weekday")
    # leaves ~900. Recorded as a deviation from the estimate, not the rule.
    lo = {"2025": 30, "2026": 20}
    bad = {y: c for y, c in per.items() if not (lo.get(y, 38) <= c <= 50)}
    if bad:
        print(f"STOP: implausible yearly counts {bad}")
        return 1
    print(f"wrote {os.path.relpath(OUT, HERE)}  sha256 {hashlib.sha256(open(OUT, 'rb').read()).hexdigest()}")
    return 0


def self_test() -> int:
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    check("Thanksgiving 2025 is 27 Nov", dt.date(2025, 11, 27) in federal_holidays(2025))
    check("Juneteenth 2021 observed Fri 18 Jun", dt.date(2021, 6, 18) in federal_holidays(2021))
    check("no Juneteenth in 2020", dt.date(2020, 6, 19) not in federal_holidays(2020))
    check("New Year 2022 (Sat) observed Fri 31 Dec 2021", dt.date(2021, 12, 31) in federal_holidays(2021))
    check("July 4 2026 (Sat) observed Fri 3 Jul", dt.date(2026, 7, 3) in federal_holidays(2026))
    rows = {r[0]: r for r in build()}
    check("Thanksgiving week 2025 excluded", rows["2025-11-24"][2] == "EXCLUDED")
    check("Labor Day week 2025 excluded (Monday holiday)", rows["2025-09-01"][2] == "EXCLUDED")
    check("ordinary week 2025-09-08 -> report Thu 2025-09-11",
          rows["2025-09-08"][1:3] == ("2025-09-11", "REPORT"))
    check("Carter mourning week 2025-01-06 excluded", rows["2025-01-06"][2] == "EXCLUDED")
    check("2013 shutdown week excluded", rows["2013-10-07"][2] == "EXCLUDED")
    check("every report day is a Thursday",
          all(dt.date.fromisoformat(r[1]).weekday() == 3 for r in rows.values() if r[2] == "REPORT"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
