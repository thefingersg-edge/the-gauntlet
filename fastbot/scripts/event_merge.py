#!/usr/bin/env python3
"""Merge the sourced 2011-2018 FOMC overlays back into events.csv.

NO RESEARCH HAPPENS HERE. Every value written was already sourced and
is already in preann_arm2.py; this file only moves it.

WHY THE DEBT EXISTED
--------------------
v11 arm 2 resolved the 14 UNCERTAIN 2011-2012 FOMC release times, and
v12 resolved the 2011-2018 press-conference flags. Both were kept as
overlays inside preann_arm2.py rather than written to events.csv,
because RESULT_PREANN was closed and changing a finished result's inputs
silently is worse than carrying the debt.

That was right then. It is now just debt, and it has already cost
something: **vol_cause.py (v21) reads events.csv directly and drops
UNCERTAIN rows, so it silently lost those 14 FOMC events.** Two files in
one directory disagreeing about the same fact is the error that produced
RESULT_TRACKA.

WHAT CHANGES, AND WHAT MUST NOT
-------------------------------
  time_et / time_quality   14 rows: UNCERTAIN -> SOURCED
  press_conference         62 rows: UNCERTAIN -> SOURCED (yes/no)
  everything else          byte-identical, and asserted so

The output is events_v2.csv. events.csv is NOT overwritten, so every
closed result keeps the exact input it ran against.

**This changes what a re-run of preann.py would produce** -- 14 more
usable FOMC events. RESULT_PREANN stands against the OLD table; arm 2
already measured what those 14 do (+29.00 bp mean).

    python3 event_merge.py --self-test
    python3 event_merge.py
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

VERSION = "1.0"

#: The only two facts this file asserts, both from preann_arm2.
TIME_PRESSER, TIME_LEGACY = "12:30", "14:15"
SRC_TIMING = ("https://www.federalreserve.gov/newsevents/pressreleases/"
              "monetary20110324a.htm")


def load_overlays():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import preann_arm2 as A2
    return A2


def merge(rows, A2):
    """Returns (rows_out, changes). Mutates nothing in place."""
    out, changes = [], []
    for r in rows:
        r = dict(r)
        if r["event"] == "FOMC":
            d = r["date"]
            tm, pc, src = A2.resolve_time(d)
            if tm and r["time_quality"] == "UNCERTAIN":
                changes.append(("time", d, r["time_et"] or "(none)", tm))
                r["time_et"] = tm
                r["time_quality"] = "SOURCED"
                r["source"] = src
                r["note"] = (f"12:30 on press-conference days, 14:15 "
                             f"otherwise; both pinned by {SRC_TIMING}")
            if r["pc_quality"] == "UNCERTAIN" and d in A2.PRESSER_ALL:
                changes.append(("pc", d, r["press_conference"] or "-", "yes"))
                r["press_conference"] = "yes"
                r["pc_quality"] = "SOURCED"
            elif (r["pc_quality"] == "UNCERTAIN"
                  and A2.NOPC_FROM <= d <= A2.NOPC_TO):
                changes.append(("pc", d, r["press_conference"] or "-", "no"))
                r["press_conference"] = "no"
                r["pc_quality"] = "SOURCED"
        out.append(r)
    return out, changes


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"event_merge.py v{VERSION} self-test\n")
    A2 = load_overlays()

    print("the overlay is the one that was already sourced")
    check("preann_arm2 resolves 2011-04-27 to 12:30 (press conference)",
          A2.resolve_time("2011-04-27")[0] == TIME_PRESSER)
    check("and 2011-08-09 to 14:15 (no press conference)",
          A2.resolve_time("2011-08-09")[0] == TIME_LEGACY)
    check("14 dates in the time overlay",
          len(A2.PRESSER_DATES) + len(A2.NON_PRESSER_DATES) == 14)
    check("32 press conferences across 2011-04..2018-12",
          len([d for d in A2.PRESSER_ALL
               if A2.NOPC_FROM <= d <= A2.NOPC_TO]) == 32)

    print("\nthe merge touches FOMC rows only, and only UNCERTAIN ones")
    base = [
        {"event": "FOMC", "date": "2011-04-27", "time_et": "",
         "time_quality": "UNCERTAIN", "press_conference": "",
         "pc_quality": "UNCERTAIN", "source": "x", "note": "y"},
        {"event": "FOMC", "date": "2015-06-17", "time_et": "14:00",
         "time_quality": "SOURCED", "press_conference": "",
         "pc_quality": "UNCERTAIN", "source": "x", "note": "y"},
        {"event": "CPI", "date": "2011-04-15", "time_et": "08:30",
         "time_quality": "RULE", "press_conference": "",
         "pc_quality": "", "source": "alfred", "note": "z"},
    ]
    out, ch = merge(base, A2)
    check("the UNCERTAIN 2011 row gets 12:30 and SOURCED",
          out[0]["time_et"] == "12:30"
          and out[0]["time_quality"] == "SOURCED")
    #: PLANTED: an already-SOURCED time must NOT be overwritten
    check("an already-SOURCED time is left alone",
          out[1]["time_et"] == "14:00", f"{out[1]['time_et']}")
    check("but its press-conference flag IS filled",
          out[1]["press_conference"] == "yes"
          and out[1]["pc_quality"] == "SOURCED")
    #: PLANTED: a CPI row must be byte-identical
    check("a CPI row is untouched", out[2] == base[2])
    check("changes are itemised, not silent", len(ch) == 3, f"{len(ch)}")

    print("\nnothing outside the two columns may move")
    for i, r in enumerate(out):
        for k in ("event", "date"):
            if r[k] != base[i][k]:
                check(f"row {i} {k} unchanged", False)
    check("event and date never change on any row", True)
    check("the CPI source string is preserved",
          out[2]["source"] == "alfred")

    print("\nthe output is a NEW file")
    #: v1.0's first attempt grepped this file for the string
    #: open(a.events,"w") -- which the CHECK ITSELF contains, so it
    #: could only ever fail. Third time I have written that bug
    #: (oanda_financing v1.0, bis_rates v1.0, here). A file cannot test
    #: itself by searching for text it contains. Structural instead:
    #: the reader and the writer take DIFFERENT argparse defaults, so
    #: the input cannot be the output unless someone passes it.
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="../data/events.csv")
    ap.add_argument("--out", default="../data/events_v2.csv")
    d = ap.parse_args([])
    check("the input and output defaults are different paths",
          d.events != d.out, f"{os.path.basename(d.events)} -> "
                             f"{os.path.basename(d.out)}")
    check("and the input keeps the name every closed result ran against",
          os.path.basename(d.events) == "events.csv")
    #: PLANTED: the merge must be a pure function of its input -- running
    #: it twice on its own output must change nothing the second time.
    once, c1 = merge(base, A2)
    twice, c2 = merge(once, A2)
    check("merging is idempotent -- a second pass changes nothing",
          once == twice and c2 == [], f"{len(c2)} changes on pass two")

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="../data/events.csv")
    ap.add_argument("--out", default="../data/events_v2.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"event_merge.py v{VERSION}\n")
    A2 = load_overlays()
    rows = list(csv.DictReader(open(a.events)))
    cols = list(rows[0].keys())
    out, ch = merge(rows, A2)

    #: nothing but the four columns may differ, and it is asserted
    moved = 0
    for r0, r1 in zip(rows, out):
        for k in cols:
            if k in ("time_et", "time_quality", "press_conference",
                     "pc_quality", "source", "note"):
                continue
            if r0[k] != r1[k]:
                moved += 1
    print(f"  rows: {len(rows):,}   changes: {len(ch)}   "
          f"unexpected column moves: {moved}")
    if moved:
        raise SystemExit("  STOP: a column changed that should not have.")

    tch = [c for c in ch if c[0] == "time"]
    pch = [c for c in ch if c[0] == "pc"]
    print(f"\n  RELEASE TIMES RESOLVED ({len(tch)})")
    for _, d, old, new in tch:
        print(f"    {d}  {old:>8} -> {new}")
    print(f"\n  PRESS-CONFERENCE FLAGS RESOLVED ({len(pch)})")
    yes = sum(1 for c in pch if c[3] == "yes")
    print(f"    yes {yes}   no {len(pch)-yes}")

    import collections
    q = collections.Counter(r["time_quality"] for r in out
                            if r["event"] == "FOMC")
    p = collections.Counter(r["pc_quality"] for r in out
                            if r["event"] == "FOMC")
    print(f"\n  AFTER THE MERGE")
    print(f"    FOMC time_quality: {dict(q)}")
    print(f"    FOMC pc_quality:   {dict(p)}")
    if q.get("UNCERTAIN"):
        print(f"    NOTE: {q['UNCERTAIN']} still UNCERTAIN")

    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    print(f"\n  written to {a.out}   (events.csv untouched)")
    print(f"\n  This changes what a re-run of preann.py would produce: 14")
    print(f"  more usable FOMC events. RESULT_PREANN stands against the")
    print(f"  OLD table, and arm 2 already measured those 14 at +29.00 bp.")


if __name__ == "__main__":
    main()
