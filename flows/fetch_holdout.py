#!/usr/bin/env python3
"""
fetch_holdout.py -- FLOWS-7 Step 0 (Part H). RUN ON THE MAC.

Builds, before any price is read by a harness:
  data/holdout_events.csv     CPI/NFP/FOMC (events.csv), GDP (GDPC1 vintages,
                              amendment-A1 method), ISM (rule), 1994-01..2004-12
  data/fred_nasdaqcom_hold.csv  FRED NASDAQCOM daily close 1993-12-01..2004-12-31 (PRIMARY)
  data/spx_stooq_hold.csv       S&P 500 daily close from stooq, if it answers (SECONDARY)
  data/holdout.meta.json        sources, counts, sha256s
Plain python3; the FRED key is read as fetch_fred.py reads it and never printed.

    python3 fetch_holdout.py --self-test
    python3 fetch_holdout.py
"""
from __future__ import annotations
import csv, datetime as dt, hashlib, io, json, os, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch_announce as FA        # noqa: E402
import fetch_ecb as FE             # noqa: E402  (verified-TLS get with curl fallback)
from fetch_fred import load_key    # noqa: E402

D = os.path.join(HERE, "data")
EV = os.path.join(D, "holdout_events.csv")
NQ = os.path.join(D, "fred_nasdaqcom_hold.csv")
SP = os.path.join(D, "spx_stooq_hold.csv")
META = os.path.join(D, "holdout.meta.json")
H0, H1 = dt.date(1994, 1, 1), dt.date(2004, 12, 31)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()


def events(key) -> dict:
    FA.START, FA.END = H0, H1
    rows = FA.from_events()
    rid53, _, _ = FA.gdp_dates()
    q = urllib.parse.urlencode(dict(series_id="GDPC1", api_key=key, file_type="json",
                                    realtime_start=H0.isoformat(), realtime_end=H1.isoformat(), limit=10000))
    js = json.loads(FE.get("https://api.stlouisfed.org/fred/series/vintagedates?" + q))
    gdp = [d for d in sorted({dt.date.fromisoformat(x) for x in js.get("vintage_dates", [])}) if H0 <= d <= H1]
    miss = [d for d in gdp if d not in set(rid53)]
    per = {}
    for d in gdp:
        per[d.year] = per.get(d.year, 0) + 1
    print("GDP per year:", per)
    if miss or any(not (10 <= c <= 13) for c in per.values()) or len(per) != 11:
        raise SystemExit(f"STOP: GDP dates fail the A1 checks (not in rid53: {miss}; per year {per})")
    rows += [("GDP", d, "08:30", "FRED", "GDPC1 vintage date (A1 method), within ALFRED rid=53") for d in gdp]
    rows += [("ISM", d, "10:00", "RULE", "first US business day of the month") for d in FA.ism_dates()]
    rows.sort(key=lambda r: (r[1], r[0]))
    with open(EV, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["event", "date", "time_et", "quality", "source"])
        for e, d, t, qq, s in rows:
            w.writerow([e, d.isoformat(), t, qq, s])
    cnt = {}
    for r in rows:
        cnt[r[0]] = cnt.get(r[0], 0) + 1
    print("event counts:", cnt)
    return dict(counts=cnt, gdp_per_year=per, sha256=sha(EV))


def nasdaq(key) -> dict:
    q = urllib.parse.urlencode(dict(series_id="NASDAQCOM", api_key=key, file_type="json",
                                    observation_start="1993-12-01", observation_end=H1.isoformat()))
    js = json.loads(FE.get("https://api.stlouisfed.org/fred/series/observations?" + q))
    obs = [(o["date"], o["value"]) for o in js["observations"] if o["value"] not in (".", "")]
    with open(NQ, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["date", "close"]); w.writerows(obs)
    print(f"NASDAQCOM: {len(obs)} closes {obs[0][0]} .. {obs[-1][0]}")
    if len(obs) < 2700:
        raise SystemExit("STOP: NASDAQCOM too short")
    return dict(n=len(obs), first=obs[0][0], last=obs[-1][0], sha256=sha(NQ))


def stooq() -> dict:
    try:
        txt = FE.get("https://stooq.com/q/d/l/?s=%5Espx&d1=19931201&d2=20041231&i=d")
        rows = list(csv.DictReader(io.StringIO(txt)))
        obs = [(r["Date"], r["Close"]) for r in rows if r.get("Close")]
        if len(obs) < 2700:
            raise ValueError(f"only {len(obs)} rows: {txt[:80]!r}")
    except Exception as e:
        print(f"stooq ^spx not available ({e}) -- secondary series skipped, as registered")
        return dict(status=f"unavailable: {e}")
    with open(SP, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["date", "close"]); w.writerows(obs)
    print(f"stooq ^spx: {len(obs)} closes {obs[0][0]} .. {obs[-1][0]}")
    return dict(status="ok", n=len(obs), sha256=sha(SP))


def main() -> int:
    key = load_key()
    if not key:
        raise SystemExit("STOP: needs the FRED key ($FRED_API_KEY or ~/.fred_key)")
    if os.path.exists(EV) and os.environ.get("REBUILD") != "1":
        print("holdout_events.csv exists -- not rebuilt"); ev = dict(sha256=sha(EV))
    else:
        ev = events(key)
    meta = dict(built_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                events=ev, nasdaqcom=nasdaq(key), stooq_spx=stooq())
    json.dump(meta, open(META, "w"), indent=1)
    print("holdout_events.csv sha256", meta["events"]["sha256"])
    return 0


def self_test() -> int:
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    FA.START, FA.END = H0, H1
    ism = FA.ism_dates()
    check("ISM rule covers 1994-2004 (132 months)", len(ism) == 132 and ism[0] == dt.date(1994, 1, 3))
    ev = FA.from_events()
    yrs = {r[1].year for r in ev}
    check("events.csv gives CPI/NFP/FOMC in every holdout year", yrs == set(range(1994, 2005)))
    check("no holdout event after 2004", max(r[1] for r in ev) <= H1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
