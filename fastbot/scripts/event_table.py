#!/usr/bin/env python3
"""STEP 1 of the event-study line -- build the table, measure nothing.

WHY THIS FILE EXISTS
--------------------
FINDINGS.md rule 4: the standard error of an annualised Sharpe goes as
1/sqrt(YEARS). Its corollary is that an EVENT study escapes that floor,
because it has N events rather than N years -- 160 FOMC meetings and ~240
CPI releases over two decades, on a span where a signal backtest cannot
tell a Sharpe of 0.8 from zero.

Event studies are the one design in this project that escapes the
resolution floor, and they have never been tried.

FINDINGS.md rule 1: measuring beats backtesting. So this file builds the
measuring stick and nothing else. It computes no return, holds no view,
and the self-test asserts by namespace inspection that no return or
position function exists in it.

THE PART THAT IS ACTUALLY HARD
------------------------------
Not the dates. The TIMES.

    FOMC statements moved from 14:15 to 14:00 ET, announced 2013-03-13
    press conferences began 2011-04-27, quarterly at first
    they became every-meeting from 2019-01-30
    and on 2011-2012 press-conference days the statement came at 12:30
      with the conference at 14:15 -- the ONLY period where the two are
      far apart, and the one most calendars get wrong

A pre-announcement window measured against the wrong release time is not
a weak test, it is a different test wearing this one's name. So every row
carries a `time_quality` of SOURCED, RULE or UNCERTAIN, the counts are
reported, and nothing here silently asserts a precision it does not have.

RUN THIS LOCALLY. It fetches from ALFRED and federalreserve.gov, both
public, no API key.

    python3 event_table.py --self-test
    python3 event_table.py --out ../data/events.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import sys
import urllib.request

VERSION = "1.9"

UA = "fastbot-event-table/1.0 (research; contact via local operator)"

#: ALFRED serves release dates as plain text with no API key. The rid is
#: VERIFIED against the page's own title rather than trusted: rid=10 and
#: rid=11 are adjacent and are CPI and the Employment Cost Index, which
#: are not the same thing and would not announce the same way.
#: v1.8 -- `rids` is a LIST of candidates, not a single number, because
#: the id for a release you have not used before is a guess. Each is
#: tried and verified against the page's own title; a wrong guess is
#: REFUSED rather than silently filling the table with another release.
#: `--find-rid TEXT` looks them up properly instead of guessing at all.
#: v1.9 -- `coverage_from` is the first year the SOURCE has, and it is a
#: stated fact that gets checked against what arrives, not derived from
#: it. A series scored from a year its source never covered reports
#: fifteen broken years and refuses to write a table that is fine; a
#: series scored from whatever turned up cannot detect a truncated fetch
#: at all. So it is asserted, and the run says so if it moves.
RELEASES = {
    "CPI": dict(rids=[10], expect="consumer price index",
                time=(8, 30), agency="BLS", coverage_from=1994),
    "NFP": dict(rids=[50], expect="employment situation",
                time=(8, 30), agency="BLS", coverage_from=1994),
    #: v1.8. Weekly, so this one release is larger than FOMC, CPI and
    #: NFP put together.
    #:
    #: The DATE is taken from ALFRED, which matters: when a federal
    #: holiday falls in the week the report moves off Thursday (usually
    #: to Wednesday), so generating Thursdays would be wrong. Only the
    #: TIME is asserted, and it carries the same RULE flag as CPI and
    #: NFP -- a stable modern convention, not a sourced document.
    #:
    #: v1.9 -- rid VERIFIED, not guessed. v1.8 shipped six candidates
    #: [180, 178, 20, 45, 205, 161] and a --find-rid that came back
    #: empty, which is the same thing as guessing with extra steps.
    #: rid=180 is confirmed twice over:
    #:   fred.stlouisfed.org/release?rid=180             title + source agency
    #:   alfred.stlouisfed.org/release/downloaddates?rid=180   same title
    #: both read "Unemployment Insurance Weekly Claims Report", source
    #: "U.S. Employment and Training Administration" -- which is also why
    #: `agency` says DOL/ETA and not BLS.
    #:
    #: `reject` exists because of ONE number: rid=469 is the STATE
    #: Unemployment Insurance Weekly Claims Report, and the national
    #: release's name is a SUBSTRING of it. Substring verification is
    #: asymmetric and cannot tell them apart -- 469 would sail through
    #: `expect` and fill the table with a different release. This is the
    #: only kind of wrong rid the name check cannot catch by itself.
    #:
    #: coverage_from=2009: ALFRED's vintage history for this release
    #: begins 2009-05-28, not 1994. The claims table is ~17 years, not
    #: ~33. Scoring it from 1994 would flag every year 1994-2008 as a
    #: parse failure and exit 2 on a table that is complete.
    "CLAIMS": dict(rids=[180],
                   expect="unemployment insurance weekly claims",
                   reject=("state unemployment insurance",),
                   time=(8, 30), agency="DOL/ETA", coverage_from=2009),
}
#: v1.1. `downloaddates?rid=N` is a LANDING PAGE, not the data. v1.0
#: fetched it, its regex found the single date printed on that page, and
#: the run reported "OK 1 dates" as a success. The file itself is
#: release_dates_N.txt. Candidates are TRIED and the one that works is
#: reported -- an endpoint that responds is a finding, one that does not
#: is also a finding, and neither is assumed.
#: v1.8 -- looking a release id UP beats guessing it. One page, no key.
ALFRED_RELEASES_INDEX = "https://alfred.stlouisfed.org/releases"

#: v1.9 -- the fetch is TWO steps, because the two things it must do
#: cannot be done by the same response.
#:
#: The landing page NAMES the release and holds no dates. The .txt file
#: holds the dates and names nothing. v1.8 tried them in one loop with
#:
#:     if not release_name_ok(...) and "release_dates" not in url:
#:
#: which says: skip verification whenever the bare .txt endpoint answers.
#: So the ONE path that needs checking hardest -- an id nobody has used
#: before, returning a file with no name in it -- was the exact path that
#: skipped the check. A rid is now verified on the landing page FIRST,
#: and a rid that fails there is never fetched for dates at all.
ALFRED_LANDING = "https://alfred.stlouisfed.org/release/downloaddates?rid={rid}"
ALFRED_DATE_FILES = [
    "https://alfred.stlouisfed.org/release/downloaddates?rid={rid}&ff=txt",
    "https://alfred.stlouisfed.org/media/files/release_dates_{rid}.txt",
]

#: How many events a complete year holds. These are facts about the
#: schedule, not tuning knobs: the FOMC holds 8 scheduled meetings a year
#: and has since 1981; BLS publishes CPI and the Employment Situation
#: monthly.
#: CLAIMS: a year holds 52 or 53 Thursdays, and a holiday shifts a
#: release rather than removing it.
EXPECTED_PER_YEAR = {"FOMC": 8, "CPI": 12, "NFP": 12, "CLAIMS": 52}
#: A year returning fewer than this is a parse failure, not a quiet year.
MIN_PER_YEAR = {"FOMC": 7, "CPI": 11, "NFP": 11, "CLAIMS": 48}
#: v1.2 -- AND a ceiling. v1.1's gate could only fail downward, so 17 FOMC
#: dates in 2015 sailed through as "not short". A gate that can only fail
#: in one direction has only been half tested. The FOMC does hold
#: unscheduled meetings (2020 had several), so the ceiling is loose --
#: but 17 is not a busy year, it is contamination.
MAX_PER_YEAR = {"FOMC": 12, "CPI": 14, "NFP": 14, "CLAIMS": 54}
#: Text near a date that means it is NOT the announcement. FOMC minutes
#: are published exactly 21 days after each meeting, and v1.1 captured
#: every one of them as if it were a meeting -- so half the table sat
#: three weeks from the event it claimed to mark.
#: Markers BEFORE a date that mean it is a release of something else.
NOT_THE_EVENT = ("minutes", "released", "transcript", "beige",
                 "projection", "longer-run")
#: v1.3 -- markers AFTER a date. The Fed's historical pages label the row
#: type to the RIGHT of the date ("March 15  Conference Call"), so a
#: before-only check missed every one. That is why 1994, 2001, 2003, 2008
#: and 2020 came back at 14-15 meetings: those are the years with the
#: most inter-meeting calls.
#:
#: "minutes" is deliberately NOT in this list. Every genuine meeting row
#: also says Minutes to its right, so filtering on it after the date
#: would delete the entire table.
NOT_THE_EVENT_AFTER = ("conference call", "notation vote",
                       "videoconference", "unscheduled")
#: Tight, because after tag-stripping the previous row's tail is close.
CONTEXT_CHARS = 20
CONTEXT_AFTER = 40
#: A 30-year release history has hundreds of dates. Anything less than
#: this means the wrong resource was fetched.
MIN_DATES_TOTAL = 100

#: ---- RELEASE TIMES, WITH SOURCES. Every one of these is a claim about
#: ---- the world and is written down so it can be checked or corrected.
#:
#: BLS releases at 08:30 ET. Stable across the whole sample.
BLS_TIME = (8, 30)
#: FOMC statement, from 2013. Announced 2013-03-13:
#:   "Committee policy statements for all regularly scheduled meetings
#:    will now be released at 2 p.m. Eastern Time."
FOMC_STATEMENT_MODERN = (14, 0)
FOMC_MODERN_FROM = dt.date(2013, 4, 1)
#: Before that, 14:15 ET on ordinary meetings.
FOMC_STATEMENT_LEGACY = (14, 15)
#: EXCEPT 2011-2012 press-conference meetings: statement 12:30, press
#: conference 14:15. This is the interval where a window anchored on
#: "the FOMC release" can be nearly two hours wrong.
FOMC_PRESSER_ERA_1 = (dt.date(2011, 4, 27), dt.date(2012, 12, 31))
FOMC_STATEMENT_PRESSER_ERA_1 = (12, 30)
#: Press conferences: began 2011-04-27 (quarterly), every meeting from
#: 2019-01-30.
PRESSER_FROM = dt.date(2011, 4, 27)
PRESSER_EVERY_MEETING_FROM = dt.date(2019, 1, 30)
FOMC_PRESSER_MODERN = (14, 30)
FOMC_PRESSER_ERA_1_TIME = (14, 15)
#: Statements themselves only begin in Feb 1994. Before that the FOMC did
#: not announce decisions, so a "pre-announcement window" has nothing to
#: anchor to and those meetings are excluded rather than guessed at.
FIRST_STATEMENT = dt.date(1994, 2, 4)

FOMC_CAL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
FOMC_HIST = ("https://www.federalreserve.gov/monetarypolicy/"
             "fomchistorical{year}.htm")

HEADER = ["event", "date", "time_et", "time_quality", "press_conference",
          "pc_quality", "source", "note"]


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def parse_release_dates(text):
    """Pull ISO dates out of ALFRED's plain-text release-date listing."""
    out = []
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        try:
            out.append(dt.date(int(m.group(1)), int(m.group(2)),
                               int(m.group(3))))
        except ValueError:
            continue
    return sorted(set(out))


TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
#: An anchor, split into its attributes and its visible content. The rid
#: must be an ATTRIBUTE and the name must be the CONTENT -- see find_rid.
ANCHOR_RE = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.I | re.S)
RID_RE = re.compile(r"rid=(\d{1,5})\b")


def page_title(text):
    """The page's own <title>, tags and entities resolved. '' if none."""
    m = TITLE_RE.search(text or "")
    return strip_tags(m.group(1)).strip() if m else ""


def find_rid(text, needle):
    """[(rid, name)] from ALFRED's releases index matching `needle`.

    Pure -- it takes the page text, so the self-test can plant one. A
    release id you have not used before is a guess, and guessing is how
    rid=10 quietly becomes the Employment Cost Index.

    v1.9. v1.8's pattern was

        rid=(\\d{1,5})[^>]*>\\s*([^<]{3,90}?)\\s*<

    which requires the name to be the IMMEDIATE text of the element
    carrying the rid. It returned nothing at all against the live index.
    Any of these defeat it, and all three are ordinary markup:

        <a href="/release?rid=180"><span>Name</span></a>   nested element
        <a href="/release?rid=180">Name &amp; More</a>     entity in name
        <a ... rid=180" data-x="..." >Name</a>             attrs after href

    A pattern that assumes a markup shape is a guess about someone
    else's HTML. This version assumes only what a release link IS: an
    anchor whose ATTRIBUTES carry the rid and whose CONTENT is the name.
    Attribute order, nesting and entities all stop mattering.

    The anchor is found first and the rid looked for inside it, which is
    not the same as finding the rid first and reading forward. Reading
    forward from a rid in a <form action="...rid=999"> walks straight
    into the NEXT release's anchor and files ITS name under 999. Passing
    needle="" returns every readable link -- the diagnostic uses it.
    """
    hits = set()
    for m in ANCHOR_RE.finditer(text or ""):
        rm = RID_RE.search(m.group(1))
        if not rm:
            continue
        name = strip_tags(m.group(2)).strip()
        if not 3 <= len(name) <= 90:
            continue
        if needle.lower() in name.lower():
            hits.add((int(rm.group(1)), name))
    return sorted(hits)


def index_diagnosis(text):
    """What was ACTUALLY fetched, when a lookup comes back empty.

    v1.8 printed "nothing matching 'unemployment insurance'" and stopped,
    which collapses three different failures into one sentence:

        the page carries no release links   -- wrong URL, redirect, or an
                                               index rendered by JavaScript
        links present, names unreadable     -- the markup is not what the
                                               parser expects
        index parsed, needle absent         -- the search term is wrong

    Only the third is the operator's fault, and it is the only one the
    message implied. A failure that cannot say which of three things
    happened is not a diagnosis, it is a shrug.
    """
    txt = text or ""
    return dict(bytes=len(txt),
                title=page_title(txt),
                rids=len(set(RID_RE.findall(txt))),
                anchors=len(re.findall(r"</a>", txt, re.I)),
                named=find_rid(txt, ""))


def release_name_ok(text, expect):
    """Does the fetched page actually describe the release we asked for?

    rid is a number and numbers are easy to get wrong. rid=10 and rid=11
    are CPI and the Employment Cost Index. A table built on the wrong one
    would look completely normal and be measuring a different event.
    """
    return expect.lower() in (text or "").lower()


def verify_release(text, spec):
    """(ok, why) -- is this rid the release we asked for? v1.9.

    Two changes on release_name_ok, both of which it gets wrong:

    1. SCOPE. release_name_ok searches the WHOLE page, so any page that
       merely links to or mentions the release passes. ALFRED's release
       pages carry sidebars and related-release links; the Employment
       Cost Index page mentioning the CPI anywhere would have been
       accepted as the CPI. The claim being checked is "this page IS
       that release", and the page's own <title> is where it says so.

    2. NEAR MISSES. Substring matching is asymmetric: a LONGER name
       containing the expected one passes. "State Unemployment Insurance
       Weekly Claims Report" (rid=469) contains "Unemployment Insurance
       Weekly Claims" whole. No amount of checking `expect` harder
       separates them, so the near miss is named explicitly in `reject`.

    Falls back to the whole text when there is no <title> -- a bare .txt
    response has none -- and says which scope it used, because "verified"
    means different things in the two cases.
    """
    title = page_title(text)
    scope, where = (title, "title") if title else ((text or ""), "page")
    low = scope.lower()
    if spec["expect"].lower() not in low:
        return False, (f"{where} does not say {spec['expect']!r}"
                       + (f" -- it says {title[:58]!r}" if title else ""))
    for bad in spec.get("reject", ()):
        if bad.lower() in low:
            return False, (f"{where} says {bad!r} -- that is a DIFFERENT "
                           f"release whose name contains this one's")
    return True, f"{where}: {title[:58] or '(no title, matched body text)'}"


def fomc_statement_time(d, has_presser):
    """(hour, minute, quality) for an FOMC statement on date `d`.

    quality: SOURCED  the time is fixed by a published Fed announcement
             RULE     the time follows a documented convention
             UNCERTAIN the convention is known to have exceptions here
    """
    if d < FIRST_STATEMENT:
        return None, None, "UNCERTAIN"
    if d >= FOMC_MODERN_FROM:
        return FOMC_STATEMENT_MODERN[0], FOMC_STATEMENT_MODERN[1], "SOURCED"

    in_era_1 = FOMC_PRESSER_ERA_1[0] <= d <= FOMC_PRESSER_ERA_1[1]
    #: v1.7. `has_presser` may be None, meaning UNKNOWN -- and in era 1
    #: alone that is fatal to the TIME, because the flag determines it:
    #: 12:30 with a press conference, 14:15 without. 105 minutes apart.
    #:
    #: v1.5 downgraded all of 2011-2018 for this, which was far too broad
    #: (from 2013-04 the time is 14:00 whatever the flag says). v1.6 then
    #: downgraded nothing, which left 14 meetings claiming 14:15 on what
    #: is really a coin flip. This is the narrow, correct version.
    if in_era_1 and has_presser is None:
        return None, None, "UNCERTAIN"
    if has_presser and in_era_1:
        return (FOMC_STATEMENT_PRESSER_ERA_1[0],
                FOMC_STATEMENT_PRESSER_ERA_1[1], "RULE")
    return FOMC_STATEMENT_LEGACY[0], FOMC_STATEMENT_LEGACY[1], "RULE"


def has_press_conference(d, presser_dates=None):
    """Whether meeting `d` had a press conference.

    From 2019-01-30 every meeting has one, so that half needs no list. The
    2011-2018 quarterly ones DO need a list; without it they are reported
    as unknown rather than guessed, because Kurov et al. found the
    press-conference split materially changes the result.
    """
    if d >= PRESSER_EVERY_MEETING_FROM:
        return True, "SOURCED"
    if d < PRESSER_FROM:
        return False, "SOURCED"
    if presser_dates is None:
        return None, "UNCERTAIN"
    return (d in presser_dates), "RULE"


MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}
MONTH_RE = ("January|February|March|April|May|June|July|August|September|"
            "October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|"
            "Sept|Oct|Nov|Dec")
DASH = r"(?:-|–|—|&ndash;|&mdash;)"

#: v1.1. Ranges AND single days. v1.0 required a dash, so every one-day
#: meeting was silently dropped and 1994-2005 came back with two meetings
#: a year against a true eight.
#: v1.5 -- group 5 captures a year the date states for ITSELF. The 2015
#: historical page ends "Last Update: January 16, 2026"; v1.4 read
#: "January 16", took the year from the page heading, and filed it as a
#: 2015 meeting. A date carrying its own year is never the page's year,
#: and 2005 escaped the same footer only because its date happened to
#: fall on a Saturday and the weekend filter caught it by luck.
FOMC_PAT = re.compile(
    rf"({MONTH_RE})\.?\s+(\d{{1,2}})"
    rf"(?:\s*{DASH}\s*(?:({MONTH_RE})\.?\s+)?(\d{{1,2}}))?"
    rf"(?:\s*,?\s*((?:19|20)\d{{2}}))?", re.I)


TAG = re.compile(r"<[^>]+>")
ENTITY = {"&ndash;": "-", "&mdash;": "-", "&nbsp;": " ", "&amp;": "&"}
#: v1.4. The marker must sit IMMEDIATELY before the date, not merely
#: within a window. Once tags are stripped the previous row's
#: "(Released February 19, 2025)" ends only ~19 characters before the
#: next meeting's "March 18-19", so a loose window would delete real
#: meetings while claiming to remove minutes.
BEFORE_ADJACENT = re.compile(
    r"(released|revised|transcript|last update|last modified)\W{0,3}$",
    re.I)


def strip_tags(html):
    """Markup out, one space in its place.

    v1.3 failed on the modern calendar page because it puts the month and
    the day in SEPARATE elements -- '<div>January</div><div>28-29</div>'
    -- so a regex expecting 'January 28' matched nothing and 2021-2026
    came back empty from a page that lists all of them. The historical
    pages put month and day adjacent, which is why those years worked and
    hid the problem.
    """
    if not html:
        return ""
    out = TAG.sub(" ", html)
    for k, v in ENTITY.items():
        out = out.replace(k, v)
    return re.sub(r"\s+", " ", out)


def parse_fomc_dates(html, year=None):
    """Meeting dates from a Fed calendar page.

    Two things this must get right, both silent when wrong:

    1. The DECISION lands on the LAST day of a range. Taking the first
       puts every two-day meeting's window 24 hours early across the
       whole sample.
    2. A calendar page holds SEVERAL years at once. v1.0 took the first
       four-digit year on the page and applied it to every match, so
       2021-2026 came back empty. Each date is now attributed to the
       nearest preceding year heading in the document, which works for
       both the multi-year calendar and the single-year historical pages.
    """
    html = strip_tags(html)
    years = [(m.start(), int(m.group(0)))
             for m in re.finditer(r"\b(?:19|20)\d{2}\b", html)]

    def year_at(pos):
        if year is not None:
            return year
        best = None
        for p, y in years:
            if p <= pos:
                best = y
            else:
                break
        return best

    out = []
    for m in FOMC_PAT.finditer(html):
        mo1 = MONTHS.get(m.group(1).lower().rstrip("."))
        if mo1 is None:
            mo1 = MONTHS.get(_expand_month(m.group(1)))
        day2 = int(m.group(4)) if m.group(4) else int(m.group(2))
        mo2 = mo1
        if m.group(3):
            mo2 = MONTHS.get(_expand_month(m.group(3)), mo1)
        #: A date that states its own year overrides the page heading.
        y = int(m.group(5)) if m.group(5) else year_at(m.start())
        if y is None or mo2 is None:
            continue
        #: v1.2. The Fed lists the MINUTES release date beside every
        #: meeting, 21 days later, and v1.1 took both. 2015 came back
        #: with 17 dates alternating +21d, and half of them marked an
        #: event three weeks from the announcement they claimed to be.
        #: Measuring on that would have diluted any real effect toward
        #: zero and looked like a clean null on 551 observations.
        ctx = html[max(0, m.start() - CONTEXT_CHARS):m.start()]
        if BEFORE_ADJACENT.search(ctx):
            continue
        after = html[m.end():m.end() + CONTEXT_AFTER].lower()
        if any(w in after for w in NOT_THE_EVENT_AFTER):
            continue
        try:
            d = dt.date(y, mo2, day2)
        except ValueError:
            continue
        #: A weekend date is page furniture, not a meeting or a release.
        if d.weekday() >= 5:
            continue
        out.append(d)
    return sorted(set(out))


def _expand_month(tok):
    t = tok.lower().rstrip(".")
    for name in MONTHS:
        if name.startswith(t):
            return name
    return t


def build_rows(fomc_dates, releases, presser_dates=None,
               used_rids=None):
    """One row per event. No returns, no positions, no view."""
    rows = []
    for d in sorted(fomc_dates):
        pc, pcq = has_press_conference(d, presser_dates)
        #: pc may be None (unknown) -- passed through, NOT coerced
        h, mi, q = fomc_statement_time(d, pc)
        note = ""
        if q == "UNCERTAIN":
            note = ("no statement was issued before 1994-02"
                    if d < FIRST_STATEMENT else "convention has exceptions")
        #: v1.6. This USED to set q = "UNCERTAIN" here, conflating two
        #: different things: whether the RELEASE TIME is known, and
        #: whether a press conference was held.
        #:
        #: They are not the same. From 2013-04 every statement is at
        #: 14:00 regardless of press conference -- the time is SOURCED
        #: and unambiguous. Downgrading it because a COVARIATE is unknown
        #: threw away ~46 events whose window is perfectly well defined,
        #: and it did so silently, under a column named time_quality.
        #:
        #: The press-conference flag matters for Kurov's split, not for
        #: the window. It now carries its own quality.
        if pcq == "UNCERTAIN":
            note = (note + "; " if note else "") + \
                "press-conference flag unknown for 2011-2018"
        rows.append(dict(
            event="FOMC", date=d.isoformat(),
            time_et="" if h is None else f"{h:02d}:{mi:02d}",
            time_quality=q,
            press_conference="" if pc is None else ("yes" if pc else "no"),
            pc_quality=pcq,
            source="federalreserve.gov FOMC calendars", note=note))
    for name, dates in sorted(releases.items()):
        for d in dates:
            rows.append(dict(
                event=name, date=d.isoformat(),
                time_et=f"{RELEASES[name]['time'][0]:02d}:"
                        f"{RELEASES[name]['time'][1]:02d}",
                time_quality="RULE", press_conference="",
                pc_quality="",
                source=f"ALFRED release dates rid="
                       f"{(used_rids or {}).get(name, RELEASES[name]['rids'][0])}",
                note=f"{RELEASES[name]['agency']} releases at "
                     f"{RELEASES[name]['time'][0]:02d}:"
                     f"{RELEASES[name]['time'][1]:02d} ET"))
    return sorted(rows, key=lambda r: (r["date"], r["event"]))


def coverage_report(event, dates, from_year, to_year):
    """Per-year counts against the known schedule.

    v1.0 had no such check and printed a 46%-complete FOMC series and a
    0.3%-complete CPI series as success. **A table builder that cannot
    tell a complete table from a broken one is not a measuring stick**,
    and every earlier failure in this project was of exactly this shape:
    passing for a reason unrelated to the thing being tested.

    Returns (rows, n_short, complete) where rows is [(year, n, ok)].
    """
    lo = MIN_PER_YEAR.get(event, 1)
    hi = MAX_PER_YEAR.get(event, 10 ** 6)
    by = {}
    for d in dates:
        by[d.year] = by.get(d.year, 0) + 1
    #: The current year is partial by definition and must not be scored
    #: against a full year's schedule -- v1.1 flagged 2026 as short in
    #: August, which is noise in the one place the report must be quiet.
    partial = dt.date.today().year
    #: v1.9 -- the year a series BEGINS needs handling too. ALFRED's
    #: claims history starts 2009-05-28, so 2009 holds ~31 releases
    #: against a 52-a-year schedule and v1.8 would call that a parse
    #: failure -- fifteen of them, since it also scored 1994-2008.
    #:
    #: The first attempt EXEMPTED that year, and it broke a test written
    #: for v1.0's original failure: one CPI date in a year stopped
    #: counting as incomplete, because a lone date makes its own year
    #: look like a partial start. An exemption is a gate that cannot
    #: fire, and this project has shipped enough of those.
    #:
    #: So the boundary year is still SCORED, against a schedule pro-rated
    #: to the part of the year the series actually covers. 2009 from
    #: 28 May is 60% of a year, so 48 becomes 28 -- and a 2009 holding
    #: three releases still fails. Only applied when the series spans
    #: more than one year; for a single-year series the year IS the
    #: series and there is no boundary to allow for.
    first = min(dates) if dates else None
    multi = bool(dates) and max(dates).year > first.year
    out, bad = [], 0
    for y in range(from_year, to_year + 1):
        n = by.get(y, 0)
        #: the current year is unfinished in the WORLD, not in the data,
        #: so no amount of pro-rating fixes it -- v1.1 flagged 2026 as
        #: short in August, which is noise in the one place the report
        #: must be quiet.
        if y == partial:
            out.append((y, n, True))
            continue
        lo_y = lo
        if multi and y == first.year and first.month > 1:
            frac = ((dt.date(y, 12, 31) - first).days + 1) / 365.25
            lo_y = max(1, int(lo * frac))
        ok = lo_y <= n <= hi
        if not ok:
            bad += 1
        out.append((y, n, ok))
    return out, bad, bad == 0


def enough_dates(dates, minimum=MIN_DATES_TOTAL):
    """Did the fetch return a date LIST, or a page that mentions a date?"""
    return len(dates) >= minimum


def quality_report(rows):
    out = {}
    for r in rows:
        k = (r["event"], r["time_quality"])
        out[k] = out.get(k, 0) + 1
    return out


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"event_table.py v{VERSION} self-test\n")

    print("the FOMC statement time follows the published changes")
    check("2026 is 14:00, SOURCED",
          fomc_statement_time(dt.date(2026, 9, 16), True)[:3]
          == (14, 0, "SOURCED"))
    check("2010 is 14:15",
          fomc_statement_time(dt.date(2010, 6, 23), False)[:2] == (14, 15))
    #: PLANTED: the 2011-2012 press-conference days. A window anchored on
    #: 14:15 here is nearly two hours off, and this is the case that
    #: catches it.
    check("a 2011 PRESS-CONFERENCE day is 12:30, not 14:15",
          fomc_statement_time(dt.date(2011, 6, 22), True)[:2] == (12, 30),
          "the statement came early; the conference was at 14:15")
    check("a 2011 NON-conference day is still 14:15",
          fomc_statement_time(dt.date(2011, 8, 9), False)[:2] == (14, 15))
    check("and by 2013 the two-hour gap is gone",
          fomc_statement_time(dt.date(2013, 6, 19), True)[:2] == (14, 0))
    #: the boundary, both sides of the announced change
    check("2013-03-20 is still legacy",
          fomc_statement_time(dt.date(2013, 3, 20), False)[:2] == (14, 15))
    check("2013-05-01 is modern",
          fomc_statement_time(dt.date(2013, 5, 1), False)[:2] == (14, 0))
    #: PLANTED: before Feb 1994 the FOMC issued no statement at all, so
    #: there is nothing for a pre-announcement window to anchor to
    h, m, q = fomc_statement_time(dt.date(1993, 5, 18), False)
    check("a 1993 meeting has NO time and is UNCERTAIN",
          h is None and q == "UNCERTAIN")

    print("\nthe press-conference flag is never guessed")
    check("2026 is yes, SOURCED",
          has_press_conference(dt.date(2026, 9, 16)) == (True, "SOURCED"))
    check("2005 is no, SOURCED",
          has_press_conference(dt.date(2005, 6, 30)) == (False, "SOURCED"))
    #: PLANTED: 2011-2018 was QUARTERLY. Without the list this must come
    #: back unknown -- assuming yes or no would silently mislabel roughly
    #: three quarters of those meetings either way.
    check("2015 without a list is UNKNOWN, not a guess",
          has_press_conference(dt.date(2015, 6, 17)) == (None, "UNCERTAIN"))
    check("2015 WITH a list resolves",
          has_press_conference(dt.date(2015, 6, 17),
                               {dt.date(2015, 6, 17)}) == (True, "RULE"))

    print("\na meeting's decision lands on the LAST day of the range")
    #: PLANTED: taking the first day would put every two-day meeting's
    #: window 24 hours early, across the entire sample.
    d = parse_fomc_dates("January 30-31, 2018 meeting", 2018)
    check("'January 30-31' gives the 31st, not the 30th",
          d == [dt.date(2018, 1, 31)], f"{d}")
    d2 = parse_fomc_dates("October 31-November 1, 2017", 2017)
    check("a range crossing a month end gives November 1",
          d2 == [dt.date(2017, 11, 1)], f"{d2}")
    d3 = parse_fomc_dates("September 16&ndash;17", 2025)
    check("an HTML en-dash entity parses too",
          d3 == [dt.date(2025, 9, 17)], f"{d3}")

    print("\nv1.1 -- SINGLE-DAY meetings are not dropped")
    #: PLANTED: v1.0's regex required a dash, so every one-day meeting
    #: vanished and 1994-2005 returned 2 meetings a year against a true 8.
    one = parse_fomc_dates("March 22, 2005 meeting", 2005)
    check("'March 22' alone is captured", one == [dt.date(2005, 3, 22)],
          f"{one}")
    mixed = parse_fomc_dates("June 29-30 and August 9 and December 13",
                             2005)
    check("a page mixing ranges and single days gets all three",
          mixed == [dt.date(2005, 6, 30), dt.date(2005, 8, 9),
                    dt.date(2005, 12, 13)], f"{mixed}")
    check("abbreviated months parse",
          parse_fomc_dates("Sept. 17", 2025) == [dt.date(2025, 9, 17)])

    print("\nv1.1 -- a multi-year page attributes each date to ITS year")
    #: PLANTED: v1.0 took the first four-digit year on the page and
    #: applied it to everything, which emptied 2021-2026.
    page = ("2025 FOMC Meetings January 29 March 19 "
            "2026 FOMC Meetings January 28 March 18")
    multi = parse_fomc_dates(page, None)
    check("dates under the 2026 heading get 2026, not 2025",
          dt.date(2026, 1, 28) in multi and dt.date(2025, 1, 29) in multi,
          f"{multi}")
    check("and no date is attributed to both years", len(multi) == 4)

    print("\nv1.1 -- coverage is checked against the known schedule")
    full = [dt.date(2020, m, 1) for m in range(1, 13)]
    _, short, complete = coverage_report("CPI", full, 2020, 2020)
    check("12 CPI dates in a year is complete", complete and short == 0)
    #: PLANTED: this is the exact v1.0 failure -- one date reported as OK
    _, short2, complete2 = coverage_report("CPI", [dt.date(2020, 8, 12)],
                                           2020, 2020)
    check("ONE CPI date in a year is INCOMPLETE, not a pass",
          not complete2 and short2 == 1)
    _, _, c3 = coverage_report("FOMC", [dt.date(2000, m, 1)
                                        for m in (1, 6)], 2000, 2000)
    check("2 FOMC meetings in a year is INCOMPLETE (true count is 8)",
          not c3)
    check("a 30-year release list must have >= 100 dates",
          enough_dates([dt.date(2000, 1, 1)] * 150)
          and not enough_dates([dt.date(2020, 8, 12)]),
          "one date is a landing page, not a file")

    print("\nv1.2 -- the MINUTES date is not the announcement")
    #: PLANTED: this is what v1.1 shipped. The Fed lists minutes beside
    #: every meeting, 21 days later, and 2015 came back with 17 dates
    #: alternating +21d. Half the table marked the wrong event.
    page = ('<td>January 27-28</td><td><a>Statement</a></td>'
            '<td><a>Minutes</a> (Released February 18, 2015)</td>')
    got = parse_fomc_dates(page, 2015)
    check("the meeting is captured", dt.date(2015, 1, 28) in got, f"{got}")
    check("and the MINUTES date is not", dt.date(2015, 2, 18) not in got,
          "21 days later -- v1.1 took it as a meeting")
    check("exactly one date survives", len(got) == 1)
    check("a 'transcript released' date is dropped too",
          parse_fomc_dates("Transcript released January 5", 2015) == [])
    #: PLANTED: a weekend date is page furniture. 2005-05-28 was a
    #: Saturday and v1.1 put it in the table.
    check("a Saturday is dropped",
          parse_fomc_dates("May 28", 2005) == [],
          "2005-05-28 was a Saturday and v1.1 kept it")
    check("but an ordinary weekday meeting survives",
          parse_fomc_dates("May 3", 2005) == [dt.date(2005, 5, 3)])

    print("\nv1.5 -- a date that states its own year keeps it")
    #: PLANTED: the literal footer of fomchistorical2015.htm. v1.4 read
    #: "January 16", took 2015 from the page, and filed a page-update
    #: stamp as an FOMC meeting -- one stray in most historical years.
    foot = parse_fomc_dates("Last Update: January 16, 2026", 2015)
    check("the footer stamp is NOT filed under the page's year",
          dt.date(2015, 1, 16) not in foot, f"{foot}")
    check("it is either dropped or dated 2026, never 2015",
          foot == [] or foot == [dt.date(2026, 1, 16)], f"{foot}")
    #: PLANTED: 2005's identical footer escaped v1.4 only because its
    #: date fell on a Saturday. Luck is not a filter.
    check("a stray whose date is a WEEKDAY is caught too, not by luck",
          dt.date(2015, 1, 16) not in
          parse_fomc_dates("Last Update: January 16, 2026", 2015),
          "2015-01-16 was a Friday and v1.4 kept it")
    check("an ordinary meeting with no stated year still uses the page",
          parse_fomc_dates("<div>March</div><div>17-18</div>", 2015)
          == [dt.date(2015, 3, 18)])
    check("and one WITH a stated year uses that",
          parse_fomc_dates("December 15-16, 2015", 2099)
          == [dt.date(2015, 12, 16)])

    print("\nv1.4 -- the modern page splits the month from the day")
    #: PLANTED: the ACTUAL structure of fomccalendars.htm. v1.3's regex
    #: needed 'January 28' adjacent; this page puts them in separate
    #: elements, so 2021-2026 came back empty from a page that lists
    #: every one of those years. The historical pages DO put them
    #: adjacent, which is exactly why the older years worked and hid it.
    real_row = ('<div class="fomc-meeting__month"><strong>January</strong>'
                '</div><div class="fomc-meeting__date">28-29</div>'
                '<div>Statement: PDF HTML Press Conference</div>'
                '<div>Minutes: PDF HTML (Released February 19, 2025)</div>')
    got = parse_fomc_dates(real_row, 2025)
    check("the meeting parses through the markup",
          dt.date(2025, 1, 29) in got, f"{got}")
    check("and the minutes release does NOT",
          dt.date(2025, 2, 19) not in got)
    check("exactly one date", len(got) == 1)
    #: PLANTED: the tight window matters. With tags stripped, the previous
    #: row's "(Released February 19, 2025)" ends ~19 chars before the next
    #: meeting -- a loose window would delete REAL meetings.
    two_rows = ('<div>January</div><div>28-29</div>'
                '<div>Minutes: (Released February 19, 2025)</div>'
                '<div>March</div><div>18-19</div><div>Statement</div>')
    got2 = parse_fomc_dates(two_rows, 2025)
    check("the meeting AFTER a minutes line survives",
          dt.date(2025, 3, 19) in got2,
          "a loose before-window would have eaten it")
    check("and both meetings are present, minutes absent",
          got2 == [dt.date(2025, 1, 29), dt.date(2025, 3, 19)], f"{got2}")
    check("strip_tags leaves the year heading readable",
          "2025 FOMC Meetings" in
          strip_tags("<h4>2025 <span>FOMC</span> Meetings</h4>"))

    print("\nv1.3 -- the row LABEL sits to the right of the date")
    #: PLANTED: the Fed's historical pages put the row type AFTER the
    #: date. v1.2 only looked before it, so every inter-meeting call was
    #: counted as a meeting -- which is why 1994, 2001, 2003, 2008 and
    #: 2020 came back at 14-15 against a true 8 plus a handful.
    page2 = ("<td>March 15</td><td>Conference Call</td>"
             "<td>May 3</td><td>Meeting - Statement</td>")
    got2 = parse_fomc_dates(page2, 2001)
    check("the conference call is dropped",
          dt.date(2001, 3, 15) not in got2, f"{got2}")
    check("and the meeting beside it survives",
          got2 == [dt.date(2001, 5, 3)])
    #: PLANTED: 'minutes' must NOT be an after-marker. Every real meeting
    #: row says Minutes to its right, so filtering on it there would
    #: delete the entire table rather than clean it.
    real = parse_fomc_dates("<td>January 28</td><td>Statement | Minutes</td>",
                            2015)
    check("a meeting followed by 'Minutes' is KEPT",
          real == [dt.date(2015, 1, 28)],
          "filtering 'minutes' after the date would empty the table")
    check("a notation vote is dropped",
          parse_fomc_dates("<td>June 4</td><td>Notation Vote</td>",
                           2019) == [])

    print("\nv1.2 -- coverage fails UPWARD as well as downward")
    #: PLANTED: v1.1's gate could only fail on too FEW. 17 FOMC dates in
    #: a year passed as "not short" while being 2x the true schedule.
    seventeen = [dt.date(2015, 1, 1) + dt.timedelta(days=21 * i)
                 for i in range(17)]
    _, bad, complete = coverage_report("FOMC", seventeen, 2015, 2015)
    check("17 FOMC dates in a year is a FAILURE, not a busy year",
          not complete and bad == 1, f"{len(seventeen)} dates")
    eight = [dt.date(2015, m, 15) for m in (1, 3, 4, 6, 7, 9, 10, 12)]
    check("8 is fine", coverage_report("FOMC", eight, 2015, 2015)[2])
    ten = eight + [dt.date(2015, 3, 16), dt.date(2015, 3, 17)]
    check("10 is fine too -- unscheduled meetings are real",
          coverage_report("FOMC", ten, 2015, 2015)[2])
    check("the CURRENT year is never scored against a full schedule",
          coverage_report("CPI", [dt.date(dt.date.today().year, 1, 1)],
                          dt.date.today().year, dt.date.today().year)[2],
          "August is not a short year, it is an unfinished one")

    print("\nthe release id is verified, not trusted")
    #: PLANTED: rid 10 and 11 are CPI and the Employment Cost Index. A
    #: table built on the wrong one would look entirely normal.
    check("a page describing the Employment Cost Index FAILS the CPI check",
          not release_name_ok("Employment Cost Index release dates",
                              RELEASES["CPI"]["expect"]))
    check("a page describing the CPI passes",
          release_name_ok("Consumer Price Index release dates",
                          RELEASES["CPI"]["expect"]))
    check("an empty page fails, rather than passing by default",
          not release_name_ok("", RELEASES["NFP"]["expect"]))

    print("\ndate parsing")
    txt = "1996-10-29\n2001-01-31\nnot a date\n2026-07-31\n1996-10-29\n"
    got = parse_release_dates(txt)
    check("three unique dates, sorted, duplicates dropped",
          got == [dt.date(1996, 10, 29), dt.date(2001, 1, 31),
                  dt.date(2026, 7, 31)], f"{got}")
    check("an impossible date is skipped, not clamped",
          parse_release_dates("2020-02-31") == [])

    print("\nrows carry their own quality")
    rows = build_rows([dt.date(2015, 6, 17), dt.date(2026, 9, 16)],
                      {"CPI": [dt.date(2026, 8, 12)]})
    q = quality_report(rows)
    #: v1.6: the 2015 meeting's TIME is sourced (14:00 since 2013-04);
    #: only its press-conference flag is unknown, and that is a covariate
    #: rather than a property of the window.
    check("the 2015 meeting's TIME is SOURCED, not UNCERTAIN",
          q.get(("FOMC", "SOURCED")) == 2, f"{q}")
    check("but its press-conference flag is marked UNCERTAIN",
          [r for r in rows if r["date"] == "2015-06-17"][0]["pc_quality"]
          == "UNCERTAIN")
    check("and the note still says so",
          "press-conference" in
          [r for r in rows if r["date"] == "2015-06-17"][0]["note"])
    check("every row has every column",
          all(set(r) == set(HEADER) for r in rows))
    check("rows are sorted by date", [r["date"] for r in rows]
          == sorted(r["date"] for r in rows))

    print("\nv1.8 -- claims, and looking ids up instead of guessing")
    check("every release carries a LIST of candidate ids",
          all(isinstance(v["rids"], list) and v["rids"]
              for v in RELEASES.values()))
    check("every release carries its own time and agency",
          all("time" in v and "agency" in v for v in RELEASES.values()))
    check("CLAIMS is 08:30 ET and attributed to DOL/ETA, not BLS",
          RELEASES["CLAIMS"]["time"] == (8, 30)
          and RELEASES["CLAIMS"]["agency"] == "DOL/ETA")
    check("every release has all three coverage gates set",
          all(ev in EXPECTED_PER_YEAR and ev in MIN_PER_YEAR
              and ev in MAX_PER_YEAR for ev in RELEASES))
    check("a weekly release expects ~52 and is gated 48-54",
          EXPECTED_PER_YEAR["CLAIMS"] == 52
          and (MIN_PER_YEAR["CLAIMS"], MAX_PER_YEAR["CLAIMS"]) == (48, 54))
    #: PLANTED: the finder must match on NAME, not on the number.
    idx = ('<a href="/release?rid=10">Consumer Price Index</a>'
           '<a href="/release?rid=180">Unemployment Insurance Weekly '
           'Claims</a><a href="/release?rid=46">Producer Price Index</a>')
    got = find_rid(idx, "unemployment insurance weekly claims")
    check("the finder pulls the right id from an index page",
          got == [(180, "Unemployment Insurance Weekly Claims")], f"{got}")
    check("it matches on the NAME, so a wrong number cannot slip in",
          find_rid(idx, "producer price") == [(46, "Producer Price Index")])
    check("and returns nothing rather than a guess when absent",
          find_rid(idx, "gross domestic product") == [])
    #: PLANTED: a CLAIMS row must say DOL/ETA, not BLS -- v1.7 hardcoded
    #: "BLS releases at 08:30 ET" into every non-FOMC row.
    cr = [r for r in build_rows([], {"CLAIMS": [dt.date(2020, 1, 2)]},
                                used_rids={"CLAIMS": 180})]
    check("a CLAIMS row is attributed to DOL/ETA and carries its rid",
          cr and "DOL/ETA" in cr[0]["note"] and "180" in cr[0]["source"],
          f"{cr[0]['note'] if cr else None}")

    print("\nv1.9 -- the finder reads LINKS, not one shape of markup")
    #: PLANTED, all three. Each is ordinary release-index markup and
    #: v1.8's pattern -- rid=(\d{1,5})[^>]*>\s*([^<]{3,90}?)\s*< --
    #: returns [] for every one, because it needs the name to be the
    #: immediate text of the element carrying the rid. That is a guess
    #: about someone else's HTML, and against the live index it returned
    #: nothing at all while reporting only "nothing matching".
    nested = ('<a href="/release?rid=180" class="release-link">'
              '<span>Unemployment Insurance Weekly Claims Report</span></a>')
    check("a name inside a NESTED element is read",
          find_rid(nested, "unemployment insurance weekly claims")
          == [(180, "Unemployment Insurance Weekly Claims Report")],
          f"{find_rid(nested, 'unemployment')}")
    ent = '<a href="/release?rid=46">Producer Price Index &amp; Parts</a>'
    check("an HTML entity inside a name is resolved",
          find_rid(ent, "index & parts")
          == [(46, "Producer Price Index & Parts")],
          f"{find_rid(ent, 'index & parts')}")
    attrs = ('<a href="/release?rid=10&amp;soid=1" data-track="rel" '
             'id="release-link-10">Consumer Price Index</a>')
    check("attributes AFTER the href do not hide the name",
          find_rid(attrs, "consumer price") == [(10, "Consumer Price Index")],
          f"{find_rid(attrs, 'consumer')}")
    #: PLANTED: the reason the finder locates the ANCHOR first and looks
    #: for the rid inside it, rather than finding the rid and reading
    #: forward. Reading forward from a rid in a form action walks into
    #: the NEXT release's anchor and files its name under the wrong id.
    notlink = ('<form action="/release?rid=999"></form>'
               '<a href="/release?rid=10">Consumer Price Index</a>')
    check("a rid that is not a LINK is never reported",
          find_rid(notlink, "consumer price") == [(10, "Consumer Price Index")],
          f"{find_rid(notlink, 'consumer price')}")
    check("needle='' returns every readable link, for the diagnostic",
          len(find_rid(idx, "")) == 3, f"{len(find_rid(idx, ''))}")

    print("\nv1.9 -- an empty lookup says WHICH failure it was")
    #: PLANTED: v1.8 printed "nothing matching X" for three unrelated
    #: failures. A message that cannot tell them apart sent the operator
    #: looking for a better search term when the page had no links at all.
    d_none = index_diagnosis("<html><title>Login</title><body>x</body></html>")
    check("a page with no release links reports rids=0",
          d_none["rids"] == 0 and d_none["named"] == [], f"{d_none['rids']}")
    d_unread = index_diagnosis('<div data-href="/release?rid=180">'
                               'Unemployment Insurance</div>')
    check("ids present but names unreadable is a DIFFERENT diagnosis",
          d_unread["rids"] == 1 and d_unread["named"] == [],
          f"rids={d_unread['rids']} named={d_unread['named']}")
    d_ok = index_diagnosis(idx)
    check("a parsed index reports the names it read",
          d_ok["rids"] == 3 and len(d_ok["named"]) == 3, f"{d_ok['named']}")
    check("and the diagnosis reads the page's own title",
          index_diagnosis("<title>ALFRED Releases</title>")["title"]
          == "ALFRED Releases")

    print("\nv1.9 -- verification is scoped to the TITLE, and names nest")
    #: PLANTED: release_name_ok searches the WHOLE page, so a page that
    #: merely LINKS to the CPI passes the CPI check. This is the exact
    #: shape of the failure the old docstring warned about -- rid=10 vs
    #: rid=11 -- and the old check could not catch it.
    eci = ('<title>Employment Cost Index - Release Dates</title>'
           '<body>Related: <a href="/release?rid=10">Consumer Price Index'
           '</a></body>')
    check("the OLD whole-page check passes the ECI page as the CPI",
          release_name_ok(eci, RELEASES["CPI"]["expect"]),
          "this is the bug, asserted so it cannot be quietly fixed away")
    okv, whyv = verify_release(eci, RELEASES["CPI"])
    check("the title-scoped check REFUSES it", not okv, whyv)
    good = ('<title>Consumer Price Index - Release Dates | ALFRED</title>'
            '<body>...</body>')
    check("and passes the real CPI page",
          verify_release(good, RELEASES["CPI"])[0])
    #: PLANTED: rid=469 is the STATE claims release, and the national
    #: release's whole name is a SUBSTRING of it. No amount of checking
    #: `expect` harder separates them -- this is what `reject` is for.
    state = ('<title>State Unemployment Insurance Weekly Claims Report '
             '- Release Dates</title>')
    check("the state release SATISFIES the expected name by substring",
          release_name_ok(state, RELEASES["CLAIMS"]["expect"]),
          "substring matching is asymmetric and cannot see the difference")
    oks, whys = verify_release(state, RELEASES["CLAIMS"])
    check("but `reject` refuses it", not oks, whys[:70])
    nat = ('<title>Unemployment Insurance Weekly Claims Report - Release '
           'Dates | ALFRED | St. Louis Fed</title>')
    check("and the NATIONAL release still passes",
          verify_release(nat, RELEASES["CLAIMS"])[0])
    #: a bare .txt response has no <title>; it must fall back, and say so
    okt, whyt = verify_release("Consumer Price Index\n1994-01-12\n",
                               RELEASES["CPI"])
    check("with no <title> it falls back to the body and SAYS so",
          okt and whyt.startswith("page"), whyt[:50])
    check("an empty response fails rather than passing by default",
          not verify_release("", RELEASES["CPI"])[0])

    print("\nv1.9 -- a series is scored over the span its SOURCE covers")
    #: PLANTED: ALFRED's claims history starts 2009-05-28. Scored from
    #: 1994 that is fifteen empty years, `incomplete`, and EXIT 2 on a
    #: table that is whole. This is the check that stops the run
    #: condemning itself for data nobody ever published.
    claims09 = []
    d0 = dt.date(2009, 5, 28)
    while d0 <= dt.date(2010, 12, 30):
        claims09.append(d0)
        d0 += dt.timedelta(days=7)
    _, bad94, _ = coverage_report("CLAIMS", claims09, 1994, 2010)
    check("scored from 1994 the claims series looks broken",
          bad94 >= 15, f"{bad94} bad years -- the v1.8 behaviour")
    _, bad09, ok09 = coverage_report("CLAIMS", claims09, 2009, 2010)
    check("scored from 2009 it is complete", ok09 and bad09 == 0,
          f"{bad09} bad years")
    #: PLANTED: the boundary year is PRO-RATED, not exempted. 2009 from
    #: 28 May is ~60% of a year, so the floor drops 48 -> 28 and the ~31
    #: real releases pass -- but a 2009 holding three still fails. The
    #: first version of this exempted the year outright and silently
    #: broke the v1.0 test below; an exemption is a gate that cannot fire.
    thin09 = [d for d in claims09 if d.year == 2010 or d.month == 5]
    _, badt, okt9 = coverage_report("CLAIMS", thin09, 2009, 2010)
    check("a boundary year that is genuinely EMPTY still fails",
          not okt9 and badt == 1,
          f"{sum(1 for d in thin09 if d.year == 2009)} dates in 2009 "
          f"vs a pro-rated floor of 28")
    #: PLANTED: the year AFTER the boundary is scored in full, so a real
    #: hole in it is caught rather than absorbed by the allowance.
    holed = [d for d in claims09 if not (d.year == 2010 and d.month <= 6)]
    _, badh, okh = coverage_report("CLAIMS", holed, 2009, 2010)
    check("a hole in the FIRST FULL year is still caught",
          not okh and badh == 1, f"{badh} bad years")
    #: PLANTED: a series starting in JANUARY is not partial and keeps its
    #: first year scored -- the allowance must not become a free pass.
    jan = [dt.date(2015, m, 15) for m in range(1, 13)]
    check("a January start keeps its first year scored",
          coverage_report("CPI", jan, 2015, 2015)[2]
          and not coverage_report("CPI", jan[:4], 2015, 2015)[2],
          "12 passes, 4 fails -- the year is scored either way")
    #: PLANTED: the v1.0 failure itself, restated here because the first
    #: attempt at the boundary allowance broke it 90 lines away.
    check("and ONE date in a year is STILL incomplete, as in v1.1",
          not coverage_report("CPI", [dt.date(2020, 8, 12)], 2020, 2020)[2],
          "a lone date must not read as a partial start")
    check("every release records where its source's coverage begins",
          all("coverage_from" in v for v in RELEASES.values()))
    check("and claims is recorded as 2009, not 1994",
          RELEASES["CLAIMS"]["coverage_from"] == 2009
          and RELEASES["CPI"]["coverage_from"] == 1994)

    print("\nthis file measures NOTHING (FINDINGS rule 1)")
    import event_table as _self
    banned = ("return", "pnl", "position", "signal", "backtest", "sharpe",
              "trade")
    def scan():
        return [x for x in dir(_self) if not x.startswith("_")
                and any(w in x.lower() for w in banned)]
    check("no return or position function exists", scan() == [], f"{scan()}")
    setattr(_self, "compute_returns", lambda: None)
    fired = scan() == ["compute_returns"]
    delattr(_self, "compute_returns")
    check("and the detector demonstrably FIRES", fired and scan() == [])

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../data/events.csv")
    ap.add_argument("--from-year", type=int, default=1994)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--find-rid", default=None,
                    help="look a release id up in ALFRED's index")
    a = ap.parse_args()
    if a.find_rid:
        print(f"event_table.py v{VERSION}   rid lookup\n")
        try:
            txt = get(ALFRED_RELEASES_INDEX)
        except Exception as exc:                              # noqa: BLE001
            raise SystemExit(f"  could not reach the index: {exc}")
        hits = find_rid(txt, a.find_rid)
        if not hits:
            #: v1.9. "nothing matching X" is not a diagnosis. Say which
            #: of the three possible failures this actually was.
            d = index_diagnosis(txt)
            print(f"  nothing matching {a.find_rid!r}\n")
            print(f"  WHAT WAS ACTUALLY FETCHED")
            print(f"    url          {ALFRED_RELEASES_INDEX}")
            print(f"    title        {d['title'][:64] or '(none)'}")
            print(f"    bytes        {d['bytes']:,}")
            print(f"    rid= seen    {d['rids']}")
            print(f"    </a> seen    {d['anchors']}")
            print(f"    readable     {len(d['named'])} release link(s)")
            for rid, nm in d["named"][:6]:
                print(f"                 rid={rid:<6}{nm[:58]}")
            print()
            if d["rids"] == 0:
                raise SystemExit(
                    "  The page carries NO release links at all. That is\n"
                    "  not a bad search term -- it is the wrong page: a\n"
                    "  redirect, a login wall, or an index this parser\n"
                    "  cannot see because it is drawn by JavaScript.")
            if not d["named"]:
                raise SystemExit(
                    f"  {d['rids']} release ids are present but NONE of\n"
                    "  their names could be read, so the markup is not\n"
                    "  <a ...>Name</a>. Paste the bytes above into the\n"
                    "  self-test as a planted case and widen the parser\n"
                    "  against the REAL markup -- not against a guess.")
            raise SystemExit(
                f"  The index parsed: {len(d['named'])} release names were\n"
                f"  read. {a.find_rid!r} is not one of them. Try a shorter\n"
                "  fragment -- and do NOT reach for a rid from memory,\n"
                "  which is the failure this command exists to prevent.")
        for rid, name in hits:
            print(f"    rid={rid:<6}{name}")
        if len(hits) > 1:
            print(f"\n  MORE THAN ONE MATCH. Names nest: 'State "
                  f"Unemployment Insurance Weekly Claims Report' CONTAINS\n"
                  f"  'Unemployment Insurance Weekly Claims Report', and "
                  f"no substring check can separate them. Pick the one\n"
                  f"  you mean and name the other in that release's "
                  f"`reject`.")
        print(f"\n  put it in RELEASES; the fetch verifies it against "
              f"the page's own title before taking a single date.")
        sys.exit(0)
    if a.self_test:
        sys.exit(self_test())

    print(f"event_table.py v{VERSION}   STEP 1 -- BUILD THE TABLE\n")
    print("  Public sources only. No API key. This file measures nothing.\n")

    this_year = dt.date.today().year
    releases, used_rids, series_from = {}, {}, {}
    for name, spec in sorted(RELEASES.items()):
        got_ds, used_rid = None, None
        for rid in spec["rids"]:
            #: STEP 1 -- the rid must NAME the release, on the one page
            #: that says what it is. A rid that fails here is never
            #: fetched for dates at all, which is the whole point: v1.8
            #: waved the check through for exactly the endpoint that
            #: returns a nameless file of numbers.
            try:
                land = get(ALFRED_LANDING.format(rid=rid))
            except Exception as exc:                          # noqa: BLE001
                print(f"  {name:<5} rid={rid:<6}landing page FAIL "
                      f"{str(exc)[:40]}")
                continue
            okay, why = verify_release(land, spec)
            if not okay:
                print(f"  {name:<5} rid={rid:<6}REFUSED -- {why}")
                continue
            print(f"  {name:<5} rid={rid:<6}VERIFIED   {why}")
            #: STEP 2 -- the dates, from an endpoint that serves the list
            #: rather than a page that describes it.
            for tmpl in ALFRED_DATE_FILES:
                url = tmpl.format(rid=rid)
                try:
                    txt = get(url)
                except Exception as exc:                      # noqa: BLE001
                    print(f"  {'':<5} {url.split('/')[-1][:46]:<48}"
                          f"FAIL {str(exc)[:24]}")
                    continue
                ds = parse_release_dates(txt)
                state = "OK" if enough_dates(ds) else \
                    f"only {len(ds)} date(s) -- a PAGE, not the file"
                print(f"  {'':<5} {url.split('/')[-1][:46]:<48}{state}")
                if enough_dates(ds):
                    got_ds, used_rid = ds, rid
                    break
            if got_ds is None:
                print(f"  {'':<5} the landing page itself holds "
                      f"{len(parse_release_dates(land))} date(s) -- "
                      f"a range, not the list")
            else:
                break
        if got_ds is None:
            print(f"  {name:<5} NO VERIFIED rid RETURNED A DATE LIST "
                  f"(tried {spec['rids']}).")
            print(f"  {'':<5} look the id up rather than guessing another:")
            print(f"  {'':<5}   python3 event_table.py --find-rid "
                  f"{' '.join(spec['expect'].split()[:2])!r}\n")
            continue
        used_rids[name] = used_rid
        kept = [d for d in got_ds if d.year >= a.from_year]
        if not kept:
            print(f"  {name:<5} verified, but no date lands on or after "
                  f"{a.from_year}.\n")
            continue
        releases[name] = kept
        #: v1.9 -- where the series ACTUALLY starts, against where it is
        #: RECORDED as starting. Scoring from whatever turned up would be
        #: a gate that adapts to its input, and a gate that adapts cannot
        #: fail; scoring from a fixed 1994 reports fifteen broken years
        #: for a release ALFRED only covers from 2009. So: score from the
        #: real start, and print loudly when it is not the recorded one.
        want = max(a.from_year, spec["coverage_from"])
        series_from[name] = kept[0].year
        flag = "" if kept[0].year == want else (
            f"\n  {'':<5} ^ RECORDED AS STARTING {want}. The source's "
            f"coverage has MOVED -- update coverage_from, and do not "
            f"assume the rest of the series is unaffected.")
        print(f"  {name:<5} -> {len(kept)} dates "
              f"{kept[0]} -> {kept[-1]}{flag}\n")

    #: v1.3. v1.2 used the calendar page for every year within 5 of now
    #: and the historical page for the rest -- and the calendar page does
    #: not carry 2021-2025, so those years came back EMPTY while the run
    #: reported nothing wrong. Both sources are now tried for every year
    #: and the results unioned: a page that has the year is a finding, a
    #: page that does not is also a finding, and neither is assumed.
    fomc = set()
    cal_html = None
    try:
        cal_html = get(FOMC_CAL)
    except Exception as exc:                                  # noqa: BLE001
        print(f"  FOMC calendar page FAIL {str(exc)[:40]}")
    cal_dates = parse_fomc_dates(cal_html, None) if cal_html else []
    for y in range(a.from_year, this_year + 2):
        got = {d for d in cal_dates if d.year == y}
        src = "cal" if got else ""
        try:
            hist = get(FOMC_HIST.format(year=y))
            h = {d for d in parse_fomc_dates(hist, y) if d.year == y}
            if h:
                got |= h
                src = (src + "+hist") if src else "hist"
        except Exception:                                     # noqa: BLE001
            pass
        if got:
            fomc.update(got)
        elif y <= this_year:
            print(f"  FOMC {y}  NO DATES from either source")
    print(f"  FOMC total: {len(fomc)} meetings "
          f"{min(fomc) if fomc else '-'} -> {max(fomc) if fomc else '-'}")

    print(f"\n  COVERAGE -- against the known schedule, not against hope")
    incomplete = []
    for ev, ds in [("FOMC", sorted(fomc))] + sorted(releases.items()):
        #: v1.9 -- each series is scored over the span its SOURCE covers.
        #: Claims begins 2009 and FOMC begins 1994; one denominator for
        #: both would report claims at 49% complete and refuse to write
        #: a table that is whole.
        f0 = series_from.get(ev, a.from_year)
        cov, short, complete = coverage_report(ev, ds, f0, this_year)
        exp = EXPECTED_PER_YEAR[ev] * (this_year - f0 + 1)
        print(f"    {ev:<6}{len(ds):>5} of ~{exp:<5} expected  "
              f"{f0}-{this_year}  {len(ds)/exp*100:>5.0f}%   "
              f"{short} bad year(s) (want {MIN_PER_YEAR[ev]}-{MAX_PER_YEAR[ev]})")
        if not complete:
            incomplete.append(ev)
            bad = [f"{y}:{n}" for y, n, okk in cov if not okk][:14]
            print(f"           short years: {' '.join(bad)}"
                  + (" ..." if short > 14 else ""))
    if incomplete:
        print(f"\n    INCOMPLETE: {', '.join(incomplete)}. v1.0 printed a")
        print("    46%-complete FOMC series and a 0.3%-complete CPI series")
        print("    as success because it had no such check. The table is")
        print("    still written, marked, and MUST NOT be measured on.")

    rows = build_rows(sorted(fomc), releases,
                      used_rids=used_rids)
    q = quality_report(rows)
    print(f"\n  TIME QUALITY -- what this table is entitled to claim")
    for (ev, qual), n in sorted(q.items()):
        print(f"    {ev:<6}{qual:<11}{n:>5}")
    unc = sum(n for (_, qual), n in q.items() if qual == "UNCERTAIN")
    if unc:
        print(f"\n    {unc} row(s) UNCERTAIN -- the 2011-04 to 2012-12 "
              f"meetings, where")
        print("    the press-conference flag DETERMINES the release time "
              "(12:30 with,")
        print("    14:15 without) and that flag is unknown. Excluded from "
              "any primary")
        print("    result rather than assumed either way.")
    else:
        print("\n    No UNCERTAIN rows.")
    pcu = sum(1 for r in rows if r.get("pc_quality") == "UNCERTAIN")
    if pcu:
        print(f"    {pcu} row(s) have an unknown press-conference FLAG "
              f"(2011-2018).")
        print("    That is a covariate for Kurov's split, not a property "
              "of the window.")

    p = os.path.expanduser(a.out)
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)
    print(f"\n  {len(rows)} rows written to {a.out}")
    if incomplete:
        print(f"\n  EXIT 2 -- the table is incomplete and nothing should")
        print("  be measured on it until the coverage above is clean.")
        sys.exit(2)
    print("\n  NEXT: a pre-registration fixing the windows and the")
    print("  conditioning variable, written BEFORE any price is joined to")
    print("  this table. Not this file.")
    sys.exit(0)


if __name__ == "__main__":
    main()
