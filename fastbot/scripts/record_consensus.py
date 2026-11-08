#!/usr/bin/env python3
"""PREREGISTRATION_v55 -- append the TradingView economic-calendar consensus for
a release day to data/forward_consensus.csv. RECORDS ONLY.

The calendar can only be read from a Claude session. A scheduled session pulls
the day's US high-importance events after 08:30 ET on CPI / payrolls days,
saves the raw JSON to data/v55/raw/<YYYY-MM-DD>.json, and runs:

    python3 record_consensus.py ../data/v55/raw/2026-10-02.json
    python3 record_consensus.py --missed 2026-10-14 CPI      # a day nobody pulled
    python3 record_consensus.py --self-test

Idempotent: a (date, title) already in the file is never rewritten -- a first
print is never overwritten by a later pull. Nothing is back-filled.

v1.1 (2026-10-16, PREREGISTRATION_v55_AMENDMENT_1): the tvremix connector was
retired; pulls now come from TradingView's official MCP
(mcp-tv-get-economic-calendar), which returns {"result": [...], "status": "ok"}
instead of tvremix's {"data": {"events": [...]}}. Both shapes are read; event
fields (title, country, date, forecast, actual, previous, unit) are unchanged.
A raw file of unknown shape, or one with no US event on its day, is now an
error (exit 2) instead of silently appending nothing. Row logic is unchanged.
--pulled-utc gives the real pull time when a raw file reaches the Mac later than
it was pulled (the scheduled run could not reach the folder; Amendment 1, s.3).
Every pull time -- given or taken from the file's mtime -- must fall on the raw
file's own date, at or after 08:30 ET, or the file is refused: no back-fill.

    python3 record_consensus.py ../data/v55/raw/2026-11-06.json --pulled-utc 2026-11-06T14:07:00Z
"""
from __future__ import annotations

import argparse, csv, datetime as dt, json, os, sys
from zoneinfo import ZoneInfo

VERSION = "1.1"
OUT = "../data/forward_consensus.csv"
COLS = ["release", "date", "time_et", "title", "forecast", "actual", "previous", "unit", "status", "pulled_utc", "raw_file"]
PRIMARY = {"Non Farm Payrolls": "NFP", "Inflation Rate MoM": "CPI"}
NY = ZoneInfo("America/New_York")


class RawError(Exception):
    pass


def events_of(js):
    """tvremix: {"data": {"events": [...]}}; official TradingView MCP: {"result": [...]}."""
    if isinstance(js, dict) and isinstance(js.get("result"), list):
        return js["result"]
    if isinstance(js, dict) and isinstance(js.get("data", js).get("events"), list):
        return js.get("data", js)["events"]
    raise RawError("unrecognised raw JSON shape (no result[] or data.events[])")


def rows_from(raw_path, pulled_utc=None):
    js = json.load(open(raw_path))
    events = events_of(js)
    day = dt.date.fromisoformat(os.path.basename(raw_path)[:10])
    pulled_utc = pulled_utc or dt.datetime.fromtimestamp(os.path.getmtime(raw_path), dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        pt = dt.datetime.fromisoformat(pulled_utc.replace("Z", "+00:00"))
    except ValueError:
        raise RawError(f"bad pull time {pulled_utc!r} (want e.g. 2026-11-06T14:07:00Z)")
    if pt.tzinfo is None:
        raise RawError(f"pull time {pulled_utc!r} has no time zone (end it with Z)")
    pt_et = pt.astimezone(NY)
    if pt_et.date() != day or (pt_et.hour, pt_et.minute) < (8, 30):
        raise RawError(f"pull time {pulled_utc} ({pt_et:%Y-%m-%d %H:%M} ET) is not on {day} at or after 08:30 ET; "
                       "a late-arriving file needs --pulled-utc with its real release-day pull time")
    out = []
    for e in events:
        if e.get("country") != "US":
            continue
        t = dt.datetime.fromisoformat(e["date"].replace("Z", "+00:00")).astimezone(NY)
        if t.date() != day:
            continue
        f, a = e.get("forecast"), e.get("actual")
        status = "ok" if (f is not None and a is not None) else ("no_actual" if a is None else "no_forecast")
        out.append([PRIMARY.get(e["title"], "other"), day.isoformat(), t.strftime("%H:%M"), e["title"],
                    "" if f is None else f, "" if a is None else a, "" if e.get("previous") is None else e["previous"],
                    e.get("unit") or "", status, pulled_utc, os.path.basename(raw_path)])
    if not out:
        raise RawError(f"no US event dated {day} in {os.path.basename(raw_path)}")
    return out


def append(rows, out=OUT):
    have = set()
    if os.path.exists(out):
        have = {(r["date"], r["title"]) for r in csv.DictReader(open(out))}
    new = [r for r in rows if (r[1], r[3]) not in have]
    fresh = not os.path.exists(out)
    with open(out, "a", newline="") as fh:
        w = csv.writer(fh)
        if fresh: w.writerow(COLS)
        w.writerows(new)
    return new


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"record_consensus.py v{VERSION} self-test\n")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        raw = os.path.join(td, "2026-10-02.json")
        json.dump({"success": True, "data": {"events": [
            {"title": "Non Farm Payrolls", "country": "US", "date": "2026-10-02T12:30:00.000Z", "actual": 120, "forecast": 90, "previous": 162, "unit": None},
            {"title": "Unemployment Rate", "country": "US", "date": "2026-10-02T12:30:00.000Z", "actual": 4.1, "forecast": 4.1, "previous": 4.1, "unit": "%"},
            {"title": "ISM Services PMI", "country": "US", "date": "2026-10-05T14:00:00.000Z", "actual": None, "forecast": None, "previous": 55.4, "unit": None}]}}, open(raw, "w"))
        r = rows_from(raw, "2026-10-02T13:50:00Z")
        check("only that day's US events are taken (the 5 Oct event is not)", len(r) == 2)
        check("payrolls is tagged NFP at 08:30 ET with forecast and actual", r[0][:3] == ["NFP", "2026-10-02", "08:30"] and r[0][4:6] == [90, 120] and r[0][8] == "ok")
        out = os.path.join(td, "fc.csv")
        n1 = append(r, out)
        r2 = [list(x) for x in r]; r2[0][5] = 999          # a later, revised pull
        n2 = append(r2, out)
        got = list(csv.DictReader(open(out)))
        check("PLANTED: a later pull never overwrites a first print", len(n1) == 2 and n2 == [] and got[0]["actual"] == "120")
        miss = [["CPI", "2026-10-14", "08:30", "Inflation Rate MoM", "", "", "", "", "missed", "", ""]]
        append(miss, out)
        check("a missed day is recorded as missed, with no values", list(csv.DictReader(open(out)))[-1]["status"] == "missed")
        # v1.1: official TradingView MCP shape
        raw2 = os.path.join(td, "2026-11-10.json")
        json.dump({"status": "ok", "result": [
            {"title": "Inflation Rate MoM", "indicator": "Inflation Rate Mom", "country": "US", "date": "2026-11-10T13:30:00.000Z", "actual": 0.3, "actualRaw": 0.3, "forecast": 0.2, "forecastRaw": 0.2, "previous": 0.6, "importance": 1},
            {"title": "Core Inflation Rate MoM", "country": "US", "date": "2026-11-10T13:30:00.000Z", "actual": None, "forecast": 0.3, "previous": 0.3, "importance": 1},
            {"title": "PPI MoM", "country": "US", "date": "2026-11-13T13:30:00.000Z", "actual": None, "forecast": None, "previous": 1.3, "importance": 1}]}, open(raw2, "w"))
        r3 = rows_from(raw2, "2026-11-10T14:00:00Z")
        check("v1.1: official-MCP result[] shape is read, only that day's events", len(r3) == 2)
        check("v1.1: CPI tagged at 08:30 ET (EST) with forecast and actual", r3[0][:4] == ["CPI", "2026-11-10", "08:30", "Inflation Rate MoM"] and r3[0][4:6] == [0.2, 0.3] and r3[0][8] == "ok")
        check("v1.1: a missing actual is no_actual", r3[1][8] == "no_actual")
        bad = os.path.join(td, "2026-11-11.json")
        json.dump({"status": "ok", "items": []}, open(bad, "w"))
        try: rows_from(bad); raised = False
        except RawError: raised = True
        check("v1.1: an unknown JSON shape is an error, not zero rows", raised)
        empty = os.path.join(td, "2026-11-12.json")
        json.dump({"status": "ok", "result": []}, open(empty, "w"))
        try: rows_from(empty); raised = False
        except RawError: raised = True
        check("v1.1: no US event on the day is an error, not zero rows", raised)
        r4 = rows_from(raw2, "2026-11-10T14:07:00Z")
        check("v1.1: an explicit release-day pull time is used as given", r4[0][9] == "2026-11-10T14:07:00Z")
        for bad_t, why in [("2026-11-12T15:00:00Z", "on a later day"), ("2026-11-10T13:00:00Z", "before 08:30 ET"), ("2026-11-10 14:07", "with no time zone")]:
            try: rows_from(raw2, bad_t); raised = False
            except RawError: raised = True
            check(f"v1.1: a pull time {why} is refused (no back-fill)", raised)
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("raw", nargs="*")
    ap.add_argument("--missed", nargs=2, metavar=("DATE", "RELEASE"))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--pulled-utc", metavar="ISO", help="real release-day pull time, e.g. 2026-11-06T14:07:00Z (one raw file only)")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    if a.missed:
        d, rel = a.missed
        title = {v: k for k, v in PRIMARY.items()}[rel]
        new = append([[rel, d, "08:30", title, "", "", "", "", "missed", "", ""]])
        print(f"recorded missed {rel} {d}" if new else "already recorded")
    if a.pulled_utc and len(a.raw) != 1:
        print("ERROR: --pulled-utc takes exactly one raw file", file=sys.stderr)
        sys.exit(2)
    for p in a.raw:
        try:
            rows = rows_from(p, a.pulled_utc)
        except RawError as err:
            print(f"ERROR {os.path.basename(p)}: {err}", file=sys.stderr)
            sys.exit(2)
        new = append(rows)
        print(f"{os.path.basename(p)}: {len(new)} new row(s): " + ", ".join(f"{r[0]}/{r[3]} {r[8]}" for r in new))
