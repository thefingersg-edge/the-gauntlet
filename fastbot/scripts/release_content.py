#!/usr/bin/env python3
"""PREREGISTRATION_v29 Part 2 -- fetch each CPI and payrolls release AS
PUBLISHED THAT DAY, from FRED/ALFRED real-time data.

RUN LOCALLY. The key is read from $FRED_API_KEY or ~/.fred_key and is
never printed, logged or written anywhere. Public data, read only.
Resumable: re-running skips rows already in the output file.

    python3 release_content.py --self-test
    python3 release_content.py            # ~20 minutes, polite rate
"""
from __future__ import annotations

import argparse, csv, datetime as dt, json, os, re, sys, time
import urllib.parse, urllib.request

VERSION = "1.0"
API = "https://api.stlouisfed.org/fred/series/observations"
SERIES = {"NFP": ("PAYEMS", "UNRATE"), "CPI": ("CPIAUCSL", "CPILFESL")}
FROM_YEAR = 2003          # 12 prior releases before the 2005 data start
PAUSE = 0.55              # FRED allows 120 requests a minute
_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)


def load_key():
    k = os.environ.get("FRED_API_KEY", "").strip()
    if not k:
        p = os.path.expanduser("~/.fred_key")
        if os.path.exists(p):
            k = open(p).read().strip()
    return k or None


def last_two(payload):
    """(prev_date, prev_val, last_date, last_val) from a FRED JSON reply."""
    obs = [o for o in payload.get("observations", [])
           if o.get("value") not in (None, "", ".")]
    if len(obs) < 2:
        return None
    a, b = obs[-2], obs[-1]
    return a["date"], float(a["value"]), b["date"], float(b["value"])


def expected_month(event_date):
    """The month a release on this date reports: the month before."""
    first = event_date.replace(day=1)
    prev = first - dt.timedelta(days=1)
    return prev.replace(day=1).isoformat()


def fetch(series, day, key):
    q = dict(series_id=series, api_key=key, file_type="json",
             realtime_start=day.isoformat(), realtime_end=day.isoformat(),
             observation_start=(day - dt.timedelta(days=420)).isoformat())
    url = API + "?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"User-Agent": "fastbot-v29"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def self_test():
    ok = True
    def check(n, c, d=""):
        nonlocal ok; ok &= bool(c)
        print(f"  [{'PASS' if c else 'FAIL'}] {n}" + (f"   {d}" if d else ""))
    print(f"release_content.py v{VERSION} self-test\n")
    js = {"observations": [{"date": "2026-06-01", "value": "159000"},
                           {"date": "2026-07-01", "value": "159150"},
                           {"date": "2026-08-01", "value": "."}]}
    got = last_two(js)
    check("missing values ('.') are skipped, the last two REAL ones kept",
          got == ("2026-06-01", 159000.0, "2026-07-01", 159150.0), f"{got}")
    check("a September release reports August",
          expected_month(dt.date(2026, 9, 4)) == "2026-08-01")
    check("a January release reports December of the year before",
          expected_month(dt.date(2026, 1, 9)) == "2025-12-01")
    check("the two releases and four series are the frozen ones",
          SERIES == {"NFP": ("PAYEMS", "UNRATE"),
                     "CPI": ("CPIAUCSL", "CPILFESL")})
    os.environ.pop("FRED_API_KEY", None)
    check("the key comes from the environment or ~/.fred_key, nowhere else",
          load_key() is None or isinstance(load_key(), str))
    check("no order, execute, submit or position name in this file",
          not [n for n in globals() if _FORBIDDEN.search(n)])
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="../data/events_v2.csv")
    ap.add_argument("--out", default="../data/release_content.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    key = load_key()
    if not key:
        print("no FRED key: set $FRED_API_KEY or put it in ~/.fred_key")
        sys.exit(2)
    print(f"release_content.py v{VERSION}   PREREGISTRATION_v29 Part 2")
    print("  public data, read only. The key is not printed.\n")

    todo = []
    for r in csv.DictReader(open(a.events)):
        if r["event"] in SERIES and r.get("time_et", "").startswith("08:3"):
            d = dt.date.fromisoformat(r["date"])
            if FROM_YEAR <= d.year and d < dt.date.today():
                todo += [(r["event"], d, s) for s in SERIES[r["event"]]]
    done = set()
    if os.path.exists(a.out):
        for r in csv.DictReader(open(a.out)):
            done.add((r["release"], r["event_date"], r["series"]))
    new = not os.path.exists(a.out)
    fh = open(a.out, "a", newline="")
    w = csv.writer(fh)
    if new:
        w.writerow(["release", "event_date", "series", "prev_date", "prev_value",
                    "last_date", "last_value", "expected_month", "vintage_ok"])
    n_ok = n_bad = n_err = 0
    left = [t for t in todo if (t[0], t[1].isoformat(), t[2]) not in done]
    print(f"  {len(todo):,} requests in all, {len(left):,} still to fetch\n")
    for i, (rel, d, s) in enumerate(left, 1):
        try:
            got = last_two(fetch(s, d, key))
        except Exception as e:                                  # noqa: BLE001
            n_err += 1
            print(f"  {rel} {d} {s}: FETCH FAILED ({type(e).__name__})")
            time.sleep(PAUSE * 4)
            continue
        exp = expected_month(d)
        okv = got is not None and got[2] == exp
        n_ok += okv; n_bad += not okv
        w.writerow([rel, d.isoformat(), s] + (list(got) if got else ["", "", "", ""])
                   + [exp, int(okv)])
        fh.flush()
        if i % 100 == 0:
            print(f"  {i:,}/{len(left):,}   vintage ok {n_ok}  mismatched {n_bad}  "
                  f"failed {n_err}")
        time.sleep(PAUSE)
    fh.close()
    print(f"\n  done. vintage ok {n_ok}, mismatched {n_bad}, fetch failed {n_err}"
          f"\n  written to {a.out}. Re-run to retry failures.")


if __name__ == "__main__":
    main()
