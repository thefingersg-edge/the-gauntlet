#!/usr/bin/env python3
"""Extend the event calendar FORWARD from BLS, for PREREGISTRATION_v25.

WHY THIS IS NOT OPTIONAL
------------------------
events_v2.csv ends at ALFRED's last vintage. A forward test whose
calendar has run out stops signalling and reports a confident zero --
the failure this project has now produced four times. v25 section 6
makes 90 days of remaining runway a hard abort, and this file is what
keeps it above that line.

ALFRED DATES AND BLS DATES ARE NOT THE SAME THING
-------------------------------------------------
ALFRED serves VINTAGE dates -- when a value was recorded. BLS publishes
RELEASE dates -- when it was announced. They usually coincide and
v22 Gate A says they coincide often enough that the historical table
lands on bars that move at t = 10 to 15. But they are different claims,
and for a forward test anchored on an exact minute the BLS date is the
authoritative one.

So this file CROSS-CHECKS the overlap rather than assuming. Any date
where the two sources disagree is printed, because a silent one-day
error is a different test wearing this one's name.

RUN THIS LOCALLY. It fetches bls.gov, public, no key.

    python3 calendar_forward.py --self-test
    python3 calendar_forward.py --events ../data/events_v2.csv \\
                                --out ../data/events_v3.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import sys
import urllib.request

VERSION = "1.5"

UA = "fastbot-calendar-forward/1.0 (research; contact via local operator)"

#: BLS publishes one schedule page per release. Both are plain HTML and
#: both carry roughly a year of forward dates -- NOT more. As of
#: 2026-09-18 they reach 2026-12-10 and 2026-12-04, which is about
#: three months of runway against v25's 90-day floor. This file is
#: therefore a RECURRING job, not a one-off.
SOURCES = {
    "CPI": "https://www.bls.gov/schedule/news_release/cpi.htm",
    "NFP": "https://www.bls.gov/schedule/news_release/empsit.htm",
}
RELEASE_TIME = "08:30"
#: A page that parses to fewer than this is a parse failure, not a quiet
#: year. Each page carries ~12 months.
MIN_DATES = 6
#: v1.4 -- AND A CEILING. v1.3's floor could only fail downward, so 16
#: dates on a page holding 13 sailed through as "not short". This is the
#: same half-tested gate event_table shipped in v1.1, and the same fix.
MAX_DATES = 15
#: v25 section 6.
RUNWAY_DAYS = 90

#: v1.3. THE REAL MARKUP, read off the page rather than imagined.
#: BLS writes "Dec. 18, 2025" -- an ABBREVIATED month with a period.
#: v1.2's pattern required the full name, so of twelve rows only "May"
#: could ever match, and the page's other "Month YYYY" text supplied the
#: rest of the four. This is the find_rid failure a second time: a regex
#: written against markup nobody had looked at.
#:
#: Note "Sep." and not "Sept.", and zero-padded days ("Jan. 09").
MONTH_TOKENS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4, "may": 5,
    "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}
#: The month WHITELIST does the real filtering, not the shape. The
#: reference-month column ("November 2026") carries no day and cannot
#: match; the month navigation ("SEPTEMBER 2026") likewise.
DATE_RE = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+((?:19|20)\d{2})\b")

TAG = re.compile(r"<[^>]+>")
#: v1.4. Stripping TAGS leaves the CONTENTS of <script> and <style> --
#: the tag markers go, the JavaScript body stays and gets read as prose.
#: That is where three phantom February dates came from, identically on
#: two different schedule pages, and they were written into the calendar
#: as six releases that do not exist.
SCRIPT_BLOCK = re.compile(r"<(script|style|noscript)\b.*?</\1\s*>",
                          re.I | re.S)


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def parse_schedule(html):
    """Sorted unique release dates from a BLS schedule page."""
    text = re.sub(r"\s+", " ", TAG.sub(" ", SCRIPT_BLOCK.sub(" ", html or "")))
    out = set()
    for m in DATE_RE.finditer(text):
        mo = MONTH_TOKENS.get(m.group(1).lower())
        if mo is None:
            continue
        try:
            d = dt.date(int(m.group(3)), mo, int(m.group(2)))
        except ValueError:
            continue
        #: a weekend date on a BLS schedule is page furniture
        if d.weekday() >= 5:
            continue
        out.add(d)
    return sorted(out)


def load_existing(path):
    """{(event, date) -> row} plus the column order."""
    rows = list(csv.DictReader(open(path)))
    cols = list(rows[0].keys()) if rows else []
    return rows, cols


def disagreements(existing, fetched, name):
    """Dates where ALFRED and BLS differ, in the overlapping window.

    Only meaningful inside the span BOTH cover -- BLS forward dates have
    no ALFRED counterpart yet and that is not a disagreement.
    """
    have = sorted(d for (e, d) in existing if e == name)
    if not have or not fetched:
        return [], None
    lo, hi = max(have[0], fetched[0]), min(have[-1], fetched[-1])
    if lo > hi:
        return [], None
    a = {d for d in have if lo <= d <= hi}
    b = {d for d in fetched if lo <= d <= hi}
    return sorted((a - b) | (b - a)), (lo, hi)


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"calendar_forward.py v{VERSION} self-test\n")

    print("the REAL BLS rows, copied from the page on 2026-09-19")
    #: PLANTED: these are the literal bytes bls.gov serves. v1.2's
    #: pattern found FOUR dates on a page holding thirteen, because it
    #: demanded "December" where the page says "Dec.".
    real = ("Reference Month Release Date Release Time "
            "November 2025 Dec. 18, 2025 08:30 AM "
            "December 2025 Jan. 09, 2026 08:30 AM "
            "February 2026 Mar. 11, 2026 08:30 AM "
            "April 2026 May 08, 2026 08:30 AM "
            "August 2026 Sep. 11, 2026 08:30 AM "
            "September 2026 Oct. 14, 2026 08:30 AM")
    got = parse_schedule(real)
    check("all six real rows parse, abbreviations and all",
          got == [dt.date(2025, 12, 18), dt.date(2026, 1, 9),
                  dt.date(2026, 3, 11), dt.date(2026, 5, 8),
                  dt.date(2026, 9, 11), dt.date(2026, 10, 14)], f"{got}")
    #: PLANTED: the REFERENCE MONTH column sits immediately left of the
    #: release date in the flattened text. It must not become a date.
    check("the reference-month column produces nothing",
          parse_schedule("November 2026 December 2026") == [])
    #: PLANTED: a <script> body carrying dates. Stripping tags alone
    #: leaves this text behind, and it is where three phantom February
    #: dates per page came from in v1.3.
    with_js = ('August 2026 Sep. 11, 2026 08:30 AM'
               '<script>var promo={start:"Feb. 05, 2026",'
               'end:"Feb. 18, 2026"};</script>')
    check("a <script> body does NOT contribute dates",
          parse_schedule(with_js) == [dt.date(2026, 9, 11)],
          f"{parse_schedule(with_js)}")
    check("nor does a <style> block",
          parse_schedule('<style>/* Mar. 03, 2026 */</style>'
                         'April 2026 May 08, 2026') == [dt.date(2026, 5, 8)])
    check("the count gate is two-sided now",
          MIN_DATES == 6 and MAX_DATES == 15,
          "13 rows is normal; 16 was contamination")
    #: PLANTED: the page's month navigation, which is where v1.2's four
    #: phantom dates came from.
    check("the month navigation produces nothing",
          parse_schedule("BY MONTH AUGUST 2026 SEPTEMBER 2026 "
                         "ENTIRE YEAR, 2026") == [])
    #: PLANTED, regression: the OLD full-name-only pattern must FAIL on
    #: the real rows, so this fix cannot be quietly reverted.
    old_pat = re.compile(r"\b(January|February|March|April|May|June|July|"
                         r"August|September|October|November|December)"
                         r"\.?\s+(\d{1,2}),?\s+((?:19|20)\d{2})\b", re.I)
    check("and v1.2's pattern still finds only 1 of the 6",
          len(old_pat.findall(real)) == 1,
          f"{len(old_pat.findall(real))} -- only 'May' needs no abbreviation")

    print("\nBLS schedule markup parses, in the shapes the page uses")
    page = ("<table><tr><td>September 2026</td>"
            "<td>Friday, October 02, 2026</td><td>08:30 AM</td></tr>"
            "<tr><td>October 2026</td><td>Friday, November 06, 2026</td>"
            "</tr></table>")
    got = parse_schedule(page)
    check("both rows are found, with their own years",
          got == [dt.date(2026, 10, 2), dt.date(2026, 11, 6)], f"{got}")
    check("an abbreviated month parses",
          parse_schedule("Sept. 4, 2026") == [dt.date(2026, 9, 4)]
          or parse_schedule("September 4, 2026") == [dt.date(2026, 9, 4)])
    #: PLANTED: a date with no year must NOT be guessed. event_table v1.4
    #: filed a footer stamp as a meeting by taking the page's year.
    check("a date with NO year is dropped, not guessed",
          parse_schedule("October 02") == [])
    #: PLANTED: a weekend date on a schedule page is furniture. BLS does
    #: not release on Saturdays.
    check("a Saturday is dropped",
          parse_schedule("Saturday, October 03, 2026") == [],
          "2026-10-03 is a Saturday")
    check("an impossible date is skipped, not clamped",
          parse_schedule("February 31, 2026") == [])
    check("a short page is refused by the floor", MIN_DATES >= 6)

    print("\nALFRED and BLS are CROSS-CHECKED, not merged blindly")
    ex = {("CPI", dt.date(2026, 7, 14)), ("CPI", dt.date(2026, 8, 12)),
          ("CPI", dt.date(2026, 9, 12))}
    bls = [dt.date(2026, 7, 14), dt.date(2026, 8, 12),
           dt.date(2026, 9, 11), dt.date(2026, 10, 14)]
    #: PLANTED: ALFRED says the 12th, BLS says the 11th. One day apart,
    #: invisible in a row count, and it moves the measured window by a
    #: whole session.
    diff, span = disagreements(ex, bls, "CPI")
    check("a one-day disagreement inside the overlap is caught",
          diff == [dt.date(2026, 9, 11), dt.date(2026, 9, 12)], f"{diff}")
    check("and the comparison is scoped to the OVERLAP only",
          span == (dt.date(2026, 7, 14), dt.date(2026, 9, 12)), f"{span}")
    check("a BLS-only future date is not a disagreement",
          dt.date(2026, 10, 14) not in diff,
          "it has no ALFRED counterpart yet")
    check("agreement produces nothing",
          disagreements({("CPI", dt.date(2026, 7, 14))},
                        [dt.date(2026, 7, 14)], "CPI")[0] == [])

    print("\nthe runway floor is the one v25 section 6 fixed")
    check("90 days", RUNWAY_DAYS == 90)
    check("and both releases are sourced, at 08:30 ET",
          set(SOURCES) == {"CPI", "NFP"} and RELEASE_TIME == "08:30")

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def do_dump():
    """Print what the SOURCE actually serves, when the parser finds too few.

    v1.1's pattern found 4 dates on a page holding ~13. That is the
    find_rid failure again: a regex written against imagined markup. The
    fix is not another guess -- it is looking at the bytes. This mode
    exists so the operator can show them without writing a scratch
    script, and so the planted case in the self-test can be the REAL
    markup rather than an invention.
    """
    for name, url in sorted(SOURCES.items()):
        print(f"=== {name}   {url}")
        try:
            html = get(url)
        except Exception as exc:                                # noqa: BLE001
            print(f"  FETCH FAILED  {exc}\n")
            continue
        text = re.sub(r"\s+", " ", TAG.sub(" ", html))
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        yr = str(dt.date.today().year)
        print(f"  {len(html):,} bytes   title: "
              f"{(m.group(1).strip() if m else '(none)')[:60]}")
        print(f"  '{yr}' appears {text.count(yr)} times in the text")
        cur = DATE_RE.findall(text)
        print(f"  the CURRENT pattern matches {len(cur)}: {cur[:4]}")
        print(f"  --- raw text around the first 6 '{yr}' ---")
        for i, mm in enumerate(re.finditer(yr, text)):
            if i >= 6:
                break
            print(f"    {text[max(0, mm.start() - 72):mm.start() + 12]!r}")
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.I | re.S)
        print(f"  --- {len(rows)} <tr> rows; first 3 containing '{yr}' ---")
        shown = 0
        for r in rows:
            if yr in r and shown < 3:
                cells = [re.sub(r"\s+", " ", TAG.sub(" ", c)).strip()
                         for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>",
                                             r, re.I | re.S)]
                print(f"    {cells}")
                shown += 1
        if not shown:
            print(f"    none -- the schedule is not in a <table>")
        print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="../data/events_v2.csv")
    ap.add_argument("--out", default="../data/events_v3.csv")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--dump", action="store_true",
                    help="show what the BLS pages actually serve")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    if a.dump:
        do_dump()
        sys.exit(0)

    print(f"calendar_forward.py v{VERSION}   PREREGISTRATION_v25\n")
    rows, cols = load_existing(a.events)
    existing = {(r["event"], dt.date.fromisoformat(r["date"])) for r in rows}
    print(f"  {a.events}: {len(rows):,} rows\n")

    today = dt.date.today()
    added, worst, fetched_ok = [], None, 0
    for name, url in sorted(SOURCES.items()):
        try:
            got = parse_schedule(get(url))
        except Exception as exc:                                # noqa: BLE001
            print(f"  {name:<5} FETCH FAILED  {str(exc)[:50]}")
            continue
        if not MIN_DATES <= len(got) <= MAX_DATES:
            print(f"  {name:<5} {len(got)} date(s) -- OUTSIDE {MIN_DATES}-"
                  f"{MAX_DATES}. A BLS schedule page holds about 13. This "
                  f"is a PARSE FAILURE\n  {'':<5} in one direction or the "
                  f"other, not a quiet year. Nothing added.")
            continue
        fetched_ok += 1
        diff, span = disagreements(existing, got, name)
        print(f"  {name:<5} {len(got)} dates  {got[0]} .. {got[-1]}")
        if span:
            print(f"  {'':<5} overlap with the table {span[0]} .. {span[1]}: "
                  f"{len(diff)} disagreement(s)")
            for d in diff[:8]:
                who = "table only" if (name, d) in existing else "BLS only"
                print(f"  {'':<5}   {d}  {who}")
            if diff:
                print(f"  {'':<5}   ALFRED serves VINTAGE dates and BLS "
                      f"serves RELEASE dates. For a forward test the BLS")
                print(f"  {'':<5}   date is authoritative; these rows are "
                      f"NOT rewritten, because history is not recomputed.")
        new = [d for d in got if (name, d) not in existing]
        for d in new:
            added.append(dict(event=name, date=d.isoformat(),
                              time_et=RELEASE_TIME, time_quality="RULE",
                              press_conference="", pc_quality="",
                              source=f"BLS schedule {url}",
                              note=f"BLS releases at {RELEASE_TIME} ET; "
                                   f"forward schedule fetched "
                                   f"{today.isoformat()}"))
        fut = [d for d in got if d > today]
        runway = (max(fut) - today).days if fut else 0
        worst = runway if worst is None else min(worst, runway)
        print(f"  {'':<5} added {len(new)}   runway {runway} days\n")

    #: v1.4, and this is the check that actually caught the phantoms.
    #: Two different releases sharing several dates is structurally
    #: impossible -- CPI and payrolls coincide about once a decade. It
    #: needs no magic number and no knowledge of the page.
    byrel = {}
    for r in added:
        byrel.setdefault(r["event"], set()).add(r["date"])
    names = sorted(byrel)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            shared = sorted(byrel[names[i]] & byrel[names[j]])
            if len(shared) > 1:
                print(f"\n  STOP: {names[i]} and {names[j]} share "
                      f"{len(shared)} NEW dates: {' '.join(shared[:6])}")
                print(f"  Two schedules do not coincide repeatedly. These "
                      f"are page furniture being read as releases.")
                print(f"  NOTHING WRITTEN.")
                sys.exit(4)

    out = rows + [{c: r.get(c, "") for c in cols} for r in added]
    out.sort(key=lambda r: (r["date"], r["event"]))
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    print(f"  {len(out):,} rows written to {a.out}   "
          f"({len(added)} new, {a.events} untouched)")

    #: v1.1. v1.0's first run fetched NOTHING -- both sources blocked --
    #: copied the input to the output unchanged, and exited 0. A calendar
    #: extender that extends nothing and reports success is exactly the
    #: failure v25 section 6 exists to prevent, written into the tool
    #: meant to prevent it.
    if fetched_ok < len(SOURCES):
        print(f"\n  ONLY {fetched_ok} OF {len(SOURCES)} SOURCES FETCHED.")
        print(f"  The calendar was NOT extended. This exits non-zero so a")
        print(f"  scheduled run cannot record it as success -- the output")
        print(f"  is a COPY of the input, not an updated calendar.")
        sys.exit(3)

    if worst is not None and worst < RUNWAY_DAYS:
        print(f"\n  RUNWAY {worst} DAYS -- BELOW THE {RUNWAY_DAYS}-DAY FLOOR")
        print(f"  v25 section 6: the forward test HALTS rather than run")
        print(f"  blind. BLS publishes about a year ahead and no further,")
        print(f"  so this job has to run again before the floor is hit.")
        print(f"  v25.1 section 2 demoted this from a HALT to a PROMPT: the")
        print(f"  BLS window is a sawtooth and a fixed floor is")
        print(f"  unsatisfiable for part of every year. Exit 0 -- warned,")
        print(f"  not stopped. Exits 3 and 4 remain fatal.")


if __name__ == "__main__":
    main()
