#!/usr/bin/env python3
"""
fetch_announce.py -- FLOWS-4 Step 0: the announcement table. RUN ON THE MAC
(needs alfred.stlouisfed.org; the Cowork VM's proxy refuses it).

Implements PREREGISTRATION_ANNOUNCE.md section 1:
  CPI, NFP, FOMC  copied from fastbot/data/events.csv (sha256 recorded)
  GDP             every release date of ALFRED rid=53, the rid VERIFIED on
                  ALFRED's own landing page as "Gross Domestic Product"
                  before any date is read (event_table.py v1.9 discipline)
  ISM             RULE: first US business day of each month, 10:00 ET

Reads no price. Writes flows/data/announce_events.csv and
flows/data/announce_events.meta.json. Plain python3, no pandas.

    python3 fetch_announce.py --self-test     # offline
    python3 fetch_announce.py                 # network: ALFRED only
"""
from __future__ import annotations
import csv, datetime as dt, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "fastbot", "scripts"))
import event_table as et                       # noqa: E402  (stdlib only)
from fetch_eia_calendar import federal_holidays  # noqa: E402

EVENTS = os.path.join(ROOT, "fastbot", "data", "events.csv")
OUT = os.path.join(HERE, "data", "announce_events.csv")
META = OUT.replace(".csv", ".meta.json")
START, END = dt.date(2005, 1, 1), dt.date(2026, 8, 31)
GDP_RID, GDP_NAME = 53, "gross domestic product"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def ism_dates():
    out = []
    hol = set()
    for y in range(START.year, END.year + 1):
        hol |= federal_holidays(y)
    for y in range(START.year, END.year + 1):
        for m in range(1, 13):
            d = dt.date(y, m, 1)
            while d.weekday() >= 5 or d in hol:
                d += dt.timedelta(days=1)
            if START <= d <= END:
                out.append(d)
    return out


def from_events():
    rows = []
    for r in csv.DictReader(open(EVENTS)):
        if r["event"] in ("CPI", "NFP", "FOMC"):
            d = dt.date.fromisoformat(r["date"])
            if START <= d <= END:
                rows.append((r["event"], d, r["time_et"], r.get("time_quality", ""),
                             "fastbot/data/events.csv: " + r.get("source", "")))
    return rows


def gdp_dates():
    landing = et.get(et.ALFRED_LANDING.format(rid=GDP_RID))
    title = et.page_title(landing)
    if GDP_NAME not in title.lower() and GDP_NAME not in et.strip_tags(landing).lower()[:4000]:
        raise SystemExit(f"STOP: rid={GDP_RID} landing page is {title!r}, not GDP. Nothing read.")
    last = None
    for tmpl in et.ALFRED_DATE_FILES:
        url = tmpl.format(rid=GDP_RID)
        try:
            ds = et.parse_release_dates(et.get(url))
        except Exception as e:                       # a failed endpoint is a finding
            print(f"  {url}: {e}"); last = e; continue
        if len(ds) >= et.MIN_DATES_TOTAL:
            print(f"  GDP dates from {url}: {len(ds)} in all")
            return [d for d in ds if START <= d <= END], url, title
        print(f"  {url}: only {len(ds)} dates")
    raise SystemExit(f"STOP: no ALFRED endpoint returned GDP dates ({last})")


def gdpc1_vintages():
    """Amendment A1: GDP days = vintage dates of GDPC1 (FRED API; key from
    $FRED_API_KEY or ~/.fred_key, as fetch_fred.py -- never printed)."""
    sys.path.insert(0, HERE)
    import urllib.parse
    from fetch_fred import load_key
    key = load_key()
    if not key:
        raise SystemExit("STOP: amendment A1 needs a FRED API key ($FRED_API_KEY or ~/.fred_key)")
    q = urllib.parse.urlencode(dict(series_id="GDPC1", api_key=key, file_type="json",
                                    realtime_start=START.isoformat(), realtime_end=END.isoformat(),
                                    limit=10000))
    js = json.loads(et.get("https://api.stlouisfed.org/fred/series/vintagedates?" + q))
    ds = sorted({dt.date.fromisoformat(x) for x in js.get("vintage_dates", [])})
    return [d for d in ds if START <= d <= END]


def main() -> int:
    rows = from_events()
    rid53, url, title = gdp_dates()
    gdp = gdpc1_vintages()
    missing = [d for d in gdp if d not in set(rid53)]
    if missing:
        print(f"STOP: GDPC1 vintages that are not rid=53 release dates: {missing}")
        return 1
    dropped = [d for d in rid53 if d not in set(gdp)]
    print(f"  A1: {len(gdp)} GDPC1 vintage dates kept; {len(dropped)} other rid=53 dates dropped")
    per = {}
    for d in gdp:
        per[d.year] = per.get(d.year, 0) + 1
    print("GDP per year: " + " ".join(f"{y}:{c}" for y, c in sorted(per.items())))
    odd = {y: c for y, c in per.items() if y < 2026 and not (10 <= c <= 13)}
    low = {y: c for y, c in per.items() if y < 2026 and c < 11}
    if low:
        print(f"  low years (allowed only for shutdowns, listed): {low}")
    if odd:
        print(f"STOP: implausible GDP yearly counts {odd}")
        return 1
    notwk = [d for d in gdp if d.weekday() >= 5]
    if notwk:
        print(f"STOP: GDP dates on a weekend: {notwk}")
        return 1
    rows += [("GDP", d, "08:30", "FRED", "GDPC1 vintage date (amendment A1), within ALFRED rid=53") for d in gdp]
    rows += [("ISM", d, "10:00", "RULE", "first US business day of the month") for d in ism_dates()]
    rows.sort(key=lambda r: (r[1], r[0]))
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event", "date", "time_et", "quality", "source"])
        for e, d, t, q, s in rows:
            w.writerow([e, d.isoformat(), t, q, s])
    cnt = {}
    for r in rows:
        cnt[r[0]] = cnt.get(r[0], 0) + 1
    meta = dict(built_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                events_csv_sha256=sha(EVENTS), gdp_url=url, gdp_title=title,
                counts=cnt, gdp_per_year=per, gdp_source="FRED GDPC1 vintagedates (amendment A1)",
                rid53_dropped=[d.isoformat() for d in dropped], sha256=sha(OUT))
    json.dump(meta, open(META, "w"), indent=1)
    print("counts:", cnt)
    print(f"wrote {os.path.relpath(OUT, HERE)} sha256 {meta['sha256']}")
    return 0


def self_test() -> int:
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    ism = ism_dates()
    check("ISM Jan 2025 = Thu 2 Jan (1 Jan holiday)", dt.date(2025, 1, 2) in ism)
    check("ISM Sep 2025 = Tue 2 Sep (Labor Day)", dt.date(2025, 9, 2) in ism)
    check("ISM Mar 2025 = Mon 3 Mar (1st is Saturday)", dt.date(2025, 3, 3) in ism)
    check("one ISM date per month", len(ism) == len({(d.year, d.month) for d in ism}) == 12 * 21 + 8)
    ev = from_events()
    check("events.csv supplies CPI, NFP and FOMC", {r[0] for r in ev} == {"CPI", "NFP", "FOMC"})
    check("parse_release_dates reads ISO dates", et.parse_release_dates("x 2025-01-30 y 2025-02-27")
          == [dt.date(2025, 1, 30), dt.date(2025, 2, 27)])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
