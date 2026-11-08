#!/usr/bin/env python3
"""
refunding_events.py -- FLOWS-2 Step 0: the quarterly borrowing-estimate dates.

PREREGISTRATION_REFUNDING.md section 1 requires this table to be built and
frozen (sha256) BEFORE any bond price is joined to it. This script reads no
price data at all.

    python3 refunding_events.py --self-test     # offline
    python3 refunding_events.py                 # ~90 small requests, ~2 min

SOURCE
    Treasury's archive "Quarterly Refunding Financing Estimates by Calendar
    Year" links one press release per quarter. Each press release carries its
    own date. The event day T is that date: the Monday 15:00 ET release of
    marketable borrowing estimates (Wang & Zhao's event).

TWO SOURCES MUST AGREE
    The quarter -> URL list is read LIVE from the archive page and compared
    with EXPECTED below, transcribed on 2026-09-26. Any difference is printed
    and written to the metadata; the live page wins. If the archive page
    cannot be parsed at all, EXPECTED is used and that is recorded.

OUTPUT
    data/refunding_events.csv       one row per quarter, 2005-Q1 .. 2026-Q3
    data/refunding_events.meta.json sources, disagreements, flags, sha256

    P, the pre-announcement day, is the last weekday before T that is not a
    US federal holiday. The harness must still confirm P has a bond bar and
    must refuse to run on any row whose status is not OK.
"""
from __future__ import annotations

import argparse, csv, datetime as dt, hashlib, html, json, os, re, sys, time
import urllib.request
from html.parser import HTMLParser

VERSION = "1.0"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ARCHIVE = ("https://home.treasury.gov/policy-issues/financing-the-government/"
           "quarterly-refunding/quarterly-refunding-archives/"
           "quarterly-refunding-financing-estimates-by-calendar-year")
PR = "https://home.treasury.gov/news/press-releases/"
UA = "Mozilla/5.0 (research; refunding_events.py)"
PAUSE = 1.0
FIRST, LAST = (2005, 1), (2026, 3)          # 2026-Q4 not yet published
QMONTHS = {1: (1, 2), 2: (4, 5), 3: (7, 8), 4: (10, 11)}   # release month by quarter

#: transcribed from the archive page 2026-09-26; (year, quarter) -> href tail
EXPECTED = {
 (2026,3):"sb0584",(2026,2):"sb0485",(2026,1):"sb0377",
 (2025,4):"sb0300",(2025,3):"sb0209",(2025,2):"sb0115",(2025,1):"sb0007",
 (2024,4):"jy2688",(2024,3):"jy2506",(2024,2):"jy2304",(2024,1):"jy2054",
 (2023,4):"jy1851",(2023,3):"jy1662",(2023,2):"jy1453",(2023,1):"jy1231",
 (2022,4):"jy1063",(2022,3):"jy0902",(2022,2):"jy0755",(2022,1):"jy0575",
 (2021,4):"jy0452",(2021,3):"jy0302",(2021,2):"jy0158",(2021,1):"jy0011",
 (2020,4):"sm1172",(2020,3):"sm1077",(2020,2):"sm997",(2020,1):"sm893",
 (2019,4):"sm808",(2019,3):"sm743",(2019,2):"sm672",(2019,1):"sm593",
 (2018,4):"sm535",(2018,3):"sm445",(2018,2):"sm0375",(2018,1):"sm0268",
 (2017,4):"sm0197",(2017,3):"sm0138",(2017,2):"sm0068",(2017,1):"jl0718",
 (2016,4):"jl0599",(2016,3):"jl0532",(2016,2):"jl0445",(2016,1):"jl0334",
 (2015,4):"jl0245",(2015,3):"PDF:Financing%20Estimates%20August%202015.pdf",
 (2015,2):"jl10040",(2015,1):"jl9756",
 (2014,4):"jl2684",(2014,3):"jl2597",(2014,2):"jl2370",(2014,1):"jl2277",
 (2013,4):"jl2208",(2013,3):"jl2131",(2013,2):"jl1919",(2013,1):"tg1837",
 (2012,4):"tg1752",(2012,3):"tg1659",(2012,2):"tg1556",(2012,1):"tg1401",
 (2011,4):"tg1342",(2011,3):"tg1262",(2011,2):"tg1155",(2011,1):"tg1038",
 (2010,4):"tg938",(2010,3):"tg806",(2010,2):"tg682",(2010,1):"tg524",
 (2009,4):"tg341",(2009,3):"tg250",(2009,2):"tg106",(2009,1):"tg07",
 (2008,4):"hp1236",(2008,3):"hp1104",(2008,2):"hp943",(2008,1):"hp775",
 (2007,4):"hp651",(2007,3):"hp513",(2007,2):"hp373",(2007,1):"hp239",
 (2006,4):"hp146",(2006,3):"hp35",(2006,2):"js4220",(2006,1):"js3091",
 (2005,4):"js3000",(2005,3):"js2669",(2005,2):"js2414",(2005,1):"js2220",
}
PDF_BASE = "https://home.treasury.gov/system/files/221/"
MONTHS = {m: i for i, m in enumerate(
    "january february march april may june july august september october "
    "november december".split(), 1)}
DATE_TEXT = re.compile(r"\b(January|February|March|April|May|June|July|August|"
                       r"September|October|November|December)\s+(\d{1,2}),\s+(\d{4})")
DATE_ATTR = re.compile(r'datetime="(\d{4})-(\d{2})-(\d{2})')
QLINK = re.compile(r"^\s*(1st|2nd|3rd|4th)\s+Quarter", re.I)


def url_of(tail: str) -> str:
    return PDF_BASE + tail[4:] if tail.startswith("PDF:") else PR + tail


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


class ArchiveParser(HTMLParser):
    """Year headings followed by '1st Quarter'.. links, in document order."""
    def __init__(self):
        super().__init__(); self.year = None; self.href = None
        self.text = ""; self.links = {}
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href"); self.text = ""
    def handle_data(self, data):
        m = re.fullmatch(r"\s*((?:19|20)\d{2})\s*", data)
        if m and self.href is None:
            self.year = int(m.group(1))
        if self.href is not None:
            self.text += data
    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            m = QLINK.match(self.text.replace("​", ""))
            if m and self.year:
                q = "1st 2nd 3rd 4th".split().index(m.group(1).lower()) + 1
                self.links.setdefault((self.year, q), self.href)
            self.href = None


def parse_archive(page: str) -> dict:
    p = ArchiveParser(); p.feed(page)
    out = {}
    for k, href in p.links.items():
        href = html.unescape(href)
        if "/news/press-releases/" in href:
            out[k] = href.rstrip("/").rsplit("/", 1)[-1]
        elif href.lower().endswith(".pdf"):
            out[k] = "PDF:" + href.rsplit("/", 1)[-1]
    return out


def page_dates(page: str):
    """(headline date, metadata date). Treasury prints the release date under
    the headline, before any date quoted in the body (checked on sb0584,
    2026-08-03, and js2220, 2005-01-31)."""
    m = DATE_TEXT.search(re.sub(r"<[^>]+>", " ", page))
    text = (dt.date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2)))
            if m else None)
    m = DATE_ATTR.search(page)
    attr = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
    return text, attr


def release_date(page: str):
    text, attr = page_dates(page)
    return text or attr


def title_of(page: str) -> str:
    m = re.search(r"<title>(.*?)</title>", page, re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(m.group(1))).strip() if m else ""


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


def _easter(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25; g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mo = (h + l - 7 * m + 114) // 31
    return dt.date(y, mo, (h + l - 7 * m + 114) % 31 + 1)


def bond_holidays(y):
    """US bond-market full closures: federal holidays plus Good Friday.
    No pandas, so this runs under the Mac's plain python3."""
    h = {_observed(dt.date(y, 1, 1)), _nth_weekday(y, 1, 0, 3), _nth_weekday(y, 2, 0, 3),
         _last_weekday(y, 5, 0), _observed(dt.date(y, 7, 4)), _nth_weekday(y, 9, 0, 1),
         _nth_weekday(y, 10, 0, 2), _observed(dt.date(y, 11, 11)), _nth_weekday(y, 11, 3, 4),
         _observed(dt.date(y, 12, 25)), _easter(y) - dt.timedelta(days=2)}
    if y >= 2022:
        h.add(_observed(dt.date(y, 6, 19)))
    return h


def pre_day(t: dt.date) -> dt.date:
    hol = bond_holidays(t.year) | bond_holidays(t.year - 1)
    d = t - dt.timedelta(days=1)
    while d.weekday() >= 5 or d in hol:
        d -= dt.timedelta(days=1)
    return d


def fomc_before(t: dt.date, fomc: list, n_bdays: int = 5) -> bool:
    lo = t - dt.timedelta(days=9)          # ~5 business days, generous
    return any(lo <= f < t for f in fomc)


def load_fomc() -> list:
    p = os.path.join(ROOT, "fastbot", "data", "events.csv")
    out = []
    for r in csv.DictReader(open(p)):
        if r["event"] == "FOMC":
            out.append(dt.date.fromisoformat(r["date"]))
    return out


def quarters():
    y, q = FIRST
    while (y, q) <= LAST:
        yield (y, q)
        q += 1
        if q == 5:
            y, q = y + 1, 1


def status_of(q: int, t, title: str, is_pdf: bool) -> str:
    if t is None:
        return "NO_DATE"
    if t.month not in QMONTHS[q]:
        return "MONTH_UNEXPECTED"
    if not is_pdf and "borrow" not in title.lower() and "financ" not in title.lower():
        return "TITLE_UNEXPECTED"
    return "OK"


def main() -> int:
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    print(f"refunding_events.py v{VERSION} -- reads NO price data")
    meta = {"version": VERSION, "archive": ARCHIVE,
            "fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    try:
        live = parse_archive(fetch(ARCHIVE))
    except Exception as e:                                   # noqa: BLE001
        live = {}; meta["archive_error"] = str(e)[:200]
    if len(live) < 40:
        print(f"  archive parse gave {len(live)} quarters -- using EXPECTED list")
        meta["source"] = "EXPECTED (archive unparseable)"
        links = dict(EXPECTED)
    else:
        meta["source"] = "live archive, checked against EXPECTED"
        links = {k: live.get(k) or EXPECTED.get(k) for k in quarters()}
    diffs = {f"{y}-Q{q}": {"live": live.get((y, q)), "expected": EXPECTED.get((y, q))}
             for (y, q) in quarters() if live and live.get((y, q)) != EXPECTED.get((y, q))}
    meta["disagreements"] = diffs
    for k, v in diffs.items():
        print(f"  DISAGREE {k}: live {v['live']}  expected {v['expected']}")

    fomc = load_fomc()
    rows = []
    for (y, q) in quarters():
        tail = links.get((y, q))
        if not tail:
            rows.append(dict(quarter=f"{y}-Q{q}", url="", T="", T_weekday="", T_page_metadata="",
                             P="", P_weekday="", fomc_in_prior_week="",
                             title="", status="NO_LINK")); continue
        url = url_of(tail); is_pdf = tail.startswith("PDF:")
        t, title, ta = None, "", None
        if is_pdf:
            m = re.search(r"(January|February|March|April|May|June|July|"
                          r"August|September|October|November|December)", tail)
            title = "PDF " + tail[4:]
        else:
            try:
                page = fetch(url); t = release_date(page); title = title_of(page)
                td, ta = page_dates(page)
            except Exception as e:                           # noqa: BLE001
                title = f"FETCH ERROR {str(e)[:60]}"
            time.sleep(PAUSE)
        st = "PDF_NEEDS_DATE" if is_pdf else status_of(q, t, title, is_pdf)
        p = pre_day(t) if t else None
        rows.append(dict(
            quarter=f"{y}-Q{q}", url=url,
            T=t.isoformat() if t else "", T_weekday=t.strftime("%a") if t else "",
            T_page_metadata=ta.isoformat() if ta else "",
            P=p.isoformat() if p else "", P_weekday=p.strftime("%a") if p else "",
            fomc_in_prior_week=(fomc_before(t, fomc) if t else ""),
            title=title[:90], status=st))
        print(f"  {y}-Q{q}  T={rows[-1]['T']:<10} {rows[-1]['T_weekday']:<3}  "
              f"P={rows[-1]['P']:<10} {rows[-1]['P_weekday']:<3}  {st}")

    out = os.path.join(HERE, "data", "refunding_events.csv")
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    sha = hashlib.sha256(open(out, "rb").read()).hexdigest()
    bad = [r for r in rows if r["status"] != "OK"]
    non_monday = [r["quarter"] for r in rows if r["T_weekday"] and r["T_weekday"] != "Mon"]
    meta.update(csv=os.path.relpath(out, ROOT), sha256=sha, rows=len(rows),
                not_ok={r["quarter"]: r["status"] for r in bad},
                non_monday_releases=non_monday)
    json.dump(meta, open(os.path.join(HERE, "data", "refunding_events.meta.json"), "w"), indent=2)
    print(f"\n  {len(rows)} quarters -> {os.path.relpath(out, ROOT)}")
    print(f"  sha256 {sha}")
    print(f"  not OK: {len(bad)}  {[r['quarter']+':'+r['status'] for r in bad]}")
    print(f"  releases not on a Monday: {non_monday or 'none'}")
    if bad:
        print("\n  Rows not OK must be resolved BY HAND from the linked document,\n"
              "  before any price is joined. Edit the CSV, re-hash, and record why.")
    return 0 if not bad else 2


def self_test() -> int:
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    sample = ('<h3>2025</h3><ul><li><a href="https://home.treasury.gov/news/'
              'press-releases/sb0300">4th Quarter</a></li><li><a href="/news/'
              'press-releases/sb0209">3rd Quarter</a></li></ul><h3>2015</h3>'
              '<a href="/system/files/221/Financing%20Estimates%20August%202015.pdf">'
              '3rd Quarter</a>')
    got = parse_archive(sample)
    check("archive: year + quarter -> press-release id", got.get((2025, 4)) == "sb0300")
    check("archive: relative href handled", got.get((2025, 3)) == "sb0209")
    check("archive: PDF quarter kept as PDF", got.get((2015, 3), "").startswith("PDF:"))
    check("metadata date used only when there is no headline date",
          release_date('<time datetime="2025-07-28T15:00:00Z">') == dt.date(2025, 7, 28))
    check("headline date wins over a later body date",
          release_date("<h1>Treasury</h1><p>January 31, 2005</p><p>November 1, 2004</p>") == dt.date(2005, 1, 31))
    check("conflict detectable",
          page_dates('<p>August 3, 2026</p><time datetime="2026-07-30T00:00">') ==
          (dt.date(2026, 8, 3), dt.date(2026, 7, 30)))
    check("date from body text",
          release_date("<p>Treasury</p><span>November 3, 2025</span>") == dt.date(2025, 11, 3))
    check("P skips the weekend (Mon -> Fri)", pre_day(dt.date(2025, 11, 3)) == dt.date(2025, 10, 31))
    check("P skips a holiday (Tue after Memorial Day -> Fri)",
          pre_day(dt.date(2024, 5, 28)) == dt.date(2024, 5, 24))
    check("Good Friday is a bond holiday (2024-03-29)", dt.date(2024, 3, 29) in bond_holidays(2024))
    check("Thanksgiving 2025 is 27 Nov", dt.date(2025, 11, 27) in bond_holidays(2025))
    check("EXPECTED covers every quarter 2005-Q1..2026-Q3",
          all(k in EXPECTED for k in quarters()) and len(EXPECTED) == len(list(quarters())))
    check("status: wrong month flagged", status_of(3, dt.date(2020, 3, 2), "Borrowing", False) == "MONTH_UNEXPECTED")
    check("status: good row OK", status_of(4, dt.date(2025, 11, 3), "Treasury Announces Marketable Borrowing Estimates", False) == "OK")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else main())
