#!/usr/bin/env python3
"""
fetch_ecb.py -- FLOWS-5 Step 0: scheduled ECB monetary policy decision dates.
RUN ON THE MAC (needs www.ecb.europa.eu; the Cowork VM's proxy refuses it).

Implements PREREGISTRATION_ECBDRIFT.md section 1. Reads no price.

For each year 2005..2026 it tries the ECB's static listing fragments, in
order, and keeps the first that yields decisions:
    /press/govcdec/mopo/{y}/html/index_include.en.html
    /press/pr/date/{y}/html/index_include.en.html
A decision is a link whose text reads "Monetary policy decision(s)". Its
date comes from the press-release file name (ecb.mpYYMMDD / prYYMMDD), or
failing that the nearest isoDate attribute. Raw pages are kept in
data/ecb_raw/ (gitignored) so every date can be audited.

Checks (a failure STOPS, nothing is written):
  2005-2014  10-13 decisions a year     2015-2025  exactly 8
  2026       no more than 8
Non-Thursday dates are LISTED for review, not dropped (section 1).
Unscheduled decisions named in section 1 are removed and listed.

    python3 fetch_ecb.py --self-test          # offline
    python3 fetch_ecb.py                      # network
    python3 fetch_ecb.py --from-dir DIR       # parse saved pages DIR/{year}.html
"""
from __future__ import annotations
import csv, datetime as dt, hashlib, html as H, json, os, re, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "ecb_events.csv")
META = OUT.replace(".csv", ".meta.json")
RAW = os.path.join(HERE, "data", "ecb_raw")
YEARS = range(2005, 2027)
END = dt.date(2026, 8, 31)
BASE = "https://www.ecb.europa.eu"
CANDIDATES = ["/press/govcdec/mopo/{y}/html/index_include.en.html",
              "/press/pr/date/{y}/html/index_include.en.html"]
UA = "Mozilla/5.0 (Macintosh) flows-research/1.0"
#: section 1: not scheduled monetary policy meetings
UNSCHEDULED = {dt.date(2008, 10, 8): "coordinated emergency cut",
               dt.date(2020, 3, 18): "evening PEPP announcement",
               dt.date(2022, 6, 15): "ad hoc meeting"}
NEW_TIME_FROM = dt.date(2022, 7, 1)          # 14:15 from the July 2022 meeting

A_RE = re.compile(r'<a\b([^>]*)>(.*?)</a>', re.I | re.S)
HREF_RE = re.compile(r'href="([^"]+)"', re.I)
CODE_RE = re.compile(r'(?:ecb\.)?(?:mp|pr)(\d{2})(\d{2})(\d{2})(?![\d])')
ISO_RE = re.compile(r'isoDate="(\d{4}-\d{2}-\d{2})"')
TITLE_RE = re.compile(r'monetary\s+policy\s+decisions?\b', re.I)


def text_of(s):
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def parse(page: str, year: int):
    """[(date, href)] for 'Monetary policy decisions' links in one year's page."""
    out = {}
    for m in A_RE.finditer(page):
        attrs, body = m.group(1), m.group(2)
        if not TITLE_RE.search(text_of(body)):
            continue
        hm = HREF_RE.search(attrs)
        href = hm.group(1) if hm else ""
        d = None
        cm = CODE_RE.search(href.rsplit("/", 1)[-1])
        if cm:
            try:
                d = dt.date(2000 + int(cm.group(1)), int(cm.group(2)), int(cm.group(3)))
            except ValueError:
                d = None
        if d is None:
            isos = ISO_RE.findall(page[:m.start()])
            if isos:
                d = dt.date.fromisoformat(isos[-1])
        if d is not None and d.year == year:
            out.setdefault(d, href)
    return sorted(out.items())


def get(url):
    """urllib with certifi's CA bundle if installed; if the TLS chain still
    cannot be verified (seen on the Mac venv, 2026-09-27), fall back to the
    system curl, which verifies against the macOS keychain. Verification is
    never switched off."""
    import ssl, subprocess
    ctx = None
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
    out = subprocess.run(["curl", "-sS", "--fail", "-L", "-A", UA, "--max-time", "30", url],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"curl: {out.stderr.strip()}")
    return out.stdout


def main(from_dir=None) -> int:
    os.makedirs(RAW, exist_ok=True)
    got, src = {}, {}
    for y in YEARS:
        found = []
        if from_dir:
            p = os.path.join(from_dir, f"{y}.html")
            if os.path.exists(p):
                found = parse(open(p, encoding="utf-8", errors="replace").read(), y)
                src[y] = p
        else:
            for tmpl in CANDIDATES:
                url = BASE + tmpl.format(y=y)
                try:
                    page = get(url)
                except Exception as e:
                    print(f"  {y} {tmpl.split('/')[2]}: {e}")
                    continue
                open(os.path.join(RAW, f"{y}_{tmpl.split('/')[2]}.html"), "w").write(page)
                found = parse(page, y)
                if found:
                    src[y] = url
                    break
                print(f"  {y} {url}: page fetched, no decisions parsed")
            time.sleep(0.5)
        got[y] = found
        print(f"  {y}: {len(found):2d} decisions  {src.get(y, 'NO SOURCE')}")
    rows, dropped = [], []
    for y, lst in got.items():
        for d, href in lst:
            if d > END:
                continue
            if d in UNSCHEDULED:
                dropped.append((d, UNSCHEDULED[d])); continue
            rows.append((d, href))
    per = {}
    for d, _ in rows:
        per[d.year] = per.get(d.year, 0) + 1
    bad = {}
    for y in YEARS:
        c = per.get(y, 0)
        okc = (10 <= c <= 13) if y <= 2014 else (c == 8 if y <= 2025 else c <= 8)
        if not okc:
            bad[y] = c
    if bad:
        print(f"\nSTOP: implausible yearly counts {bad}. Nothing written.")
        print("  Inspect data/ecb_raw/, or save each year's ECB listing as DIR/{year}.html")
        print("  and re-run with --from-dir DIR.")
        return 1
    rows.sort()
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "time_cet", "scheduled", "source_url", "note"])
        for d, href in rows:
            note = "" if d.weekday() == 3 else f"not a Thursday ({d:%A}) -- review"
            w.writerow([d.isoformat(), "14:15" if d >= NEW_TIME_FROM else "13:45", 1,
                        href if href.startswith("http") else BASE + href, note])
    nonthu = [d for d, _ in rows if d.weekday() != 3]
    meta = dict(built_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                sources={str(k): v for k, v in src.items()}, per_year=per,
                dropped_unscheduled=[f"{d} {why}" for d, why in dropped],
                not_thursday=[str(d) for d in nonthu],
                sha256=hashlib.sha256(open(OUT, "rb").read()).hexdigest())
    json.dump(meta, open(META, "w"), indent=1)
    print(f"\n{len(rows)} scheduled decisions; dropped as unscheduled: {meta['dropped_unscheduled']}")
    print(f"not a Thursday (review): {meta['not_thursday']}")
    print(f"wrote {os.path.relpath(OUT, HERE)} sha256 {meta['sha256']}")
    return 0


def self_test() -> int:
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    page = '''<dl><dt isoDate="2024-12-12"><div class="date">12 December 2024</div></dt>
      <dd><div class="title"><a href="/press/pr/date/2024/html/ecb.mp241212~abc.en.html">Monetary policy decisions</a></div></dd>
      <dt isoDate="2024-12-12"></dt><dd><a href="/press/pr/date/2024/html/ecb.is241212~x.en.html">Monetary policy statement</a></dd>
      <dt isoDate="2024-10-17"></dt><dd><a href="/press/pr/date/2024/html/ecb.mp241017~d.en.html"><span>Monetary policy
      decisions</span></a></dd>
      <dt isoDate="2005-03-03"></dt><dd><a href="/press/pr/date/2005/html/pr050303.en.html">Monetary policy decisions</a></dd>
      <dt isoDate="2024-06-06"></dt><dd><a href="/x/no-code.html">Monetary policy decisions</a></dd></dl>'''
    p = parse(page, 2024)
    check("finds decisions by title, dates from file names",
          [d for d, _ in p] == [dt.date(2024, 6, 6), dt.date(2024, 10, 17), dt.date(2024, 12, 12)])
    check("statement link is not a decision", all("is24" not in h for _, h in p))
    check("old-style prYYMMDD file name", [d for d, _ in parse(page, 2005)] == [dt.date(2005, 3, 3)])
    check("isoDate fallback when the file name has no date", (dt.date(2024, 6, 6), "/x/no-code.html") in p)
    check("unscheduled list holds 2008-10-08", dt.date(2008, 10, 8) in UNSCHEDULED)
    return 0 if ok else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    fd = sys.argv[sys.argv.index("--from-dir") + 1] if "--from-dir" in sys.argv else None
    sys.exit(main(fd))
