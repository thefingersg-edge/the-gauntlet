#!/usr/bin/env python3
"""
fetch_earnings.py -- FLOWS-9 Step 0. RUN ON THE MAC. Reads no price.
1. Universe: for each year y, the ten registrants with the largest
   dei:EntityPublicFloat at instant CY(y-1)Q2I (SEC XBRL frames API); applies
   to events from 1 April y to 31 March y+1. First year = first frame with >= 500 filers.
2. Events: each universe firm's 8-K filings with Item 2.02, with EDGAR acceptanceDateTime.
SEC requires a descriptive User-Agent with a contact: set $SEC_USER_AGENT or put one
line in ~/.sec_user_agent, e.g.  "Dave research you@example.com". It is sent only to sec.gov.
The acceptance-hour histogram is printed so the time zone reading can be checked
(earnings 8-Ks cluster just after 16:00 and before 09:30 ET) before the table is used.
    python3 fetch_earnings.py --self-test | (no args)
"""
from __future__ import annotations
import csv, datetime as dt, hashlib, json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
UNI = os.path.join(HERE, "data", "earnings_universe.csv")
EVT = os.path.join(HERE, "data", "earnings_events.csv")
META = os.path.join(HERE, "data", "earnings.meta.json")
FRAMES = "https://data.sec.gov/api/xbrl/frames/dei/EntityPublicFloat/USD/CY{y}Q2I.json"
SUBS = "https://data.sec.gov/submissions/{name}"
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()


def ua():
    u = os.environ.get("SEC_USER_AGENT", "").strip()
    p = os.path.expanduser("~/.sec_user_agent")
    if not u and os.path.exists(p):
        u = open(p).read().strip()
    if not u or "@" not in u:
        raise SystemExit("STOP: set SEC_USER_AGENT or ~/.sec_user_agent to 'Name contact@email' (SEC fair-access rule)")
    return u


def get_json(url, agent):
    time.sleep(0.15)                                           # SEC limit: 10 requests/second
    out = subprocess.run(["curl", "-sS", "--fail", "-L", "--compressed", "-A", agent, "--max-time", "60", url],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"{url}: {out.stderr.strip()[:200]}")
    return json.loads(out.stdout)


def top10(frame: dict):
    rows = sorted(frame.get("data", []), key=lambda r: -float(r.get("val", 0)))
    seen, out = set(), []
    for r in rows:
        if r["cik"] in seen:
            continue
        seen.add(r["cik"]); out.append(r)
        if len(out) == 10:
            break
    return out


def item202(block: dict):
    """(accession, filingDate, acceptanceDateTime) for 8-K rows whose items include 2.02."""
    out = []
    n = len(block.get("form", []))
    for i in range(n):
        if block["form"][i] in ("8-K", "8-K/A") and "2.02" in str(block.get("items", [""] * n)[i]).split(","):
            out.append((block["accessionNumber"][i], block["filingDate"][i], block["acceptanceDateTime"][i], block["form"][i]))
    return out


CAP = 5e12            # amendment A1


def screened_top10(fr: dict, prev: dict):
    """Amendment A1: value <= $5e12 and within x3 of the same CIK's previous-year value."""
    pv = {r["cik"]: float(r["val"]) for r in prev.get("data", [])}
    ok = [r for r in fr.get("data", []) if float(r["val"]) <= CAP and r["cik"] in pv and pv[r["cik"]] > 0
          and 1 / 3 <= float(r["val"]) / pv[r["cik"]] <= 3]
    return top10({"data": ok})


def main():
    agent = ua()
    uni, frames, raw_top = [], {}, {}
    fdir = os.path.join(HERE, "data", "earnings_frames"); os.makedirs(fdir, exist_ok=True)
    for y in range(2008, 2026):
        try:
            fr = get_json(FRAMES.format(y=y), agent)
        except Exception as e:
            print(f"  frame CY{y}Q2I: {e}"); continue
        json.dump(fr, open(os.path.join(fdir, f"CY{y}Q2I.json"), "w"))
        n = len(fr.get("data", []))
        print(f"  frame CY{y}Q2I: {n} filers")
        if n < 500:
            continue
        frames[y] = fr
        raw_top[y + 1] = [r.get("entityName", "") for r in top10(fr)]
        if y - 1 not in frames:
            continue
        for rank, r in enumerate(screened_top10(fr, frames[y - 1]), 1):
            uni.append((y + 1, rank, r["cik"], r.get("entityName", ""), r["val"]))
        print(f"    universe {y + 1}: " + "; ".join(u[3][:22] for u in uni[-10:]))
    if not uni:
        raise SystemExit("STOP: no usable frame")
    with open(UNI, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["year_from_april", "rank", "cik", "name", "public_float_usd"]); w.writerows(uni)
    events, hours = [], {}
    for cik in sorted({u[2] for u in uni}):
        js = get_json(SUBS.format(name=f"CIK{int(cik):010d}.json"), agent)
        rows = item202(js["filings"]["recent"])
        for fl in js["filings"].get("files", []):
            rows += item202(get_json(SUBS.format(name=fl["name"]), agent))
        for acc, fdate, acct, form in rows:
            events.append((cik, js.get("name", ""), acc, form, fdate, acct))
            h = acct[11:13]; hours[h] = hours.get(h, 0) + 1
    events.sort(key=lambda r: r[5])
    with open(EVT, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["cik", "name", "accession", "form", "filing_date", "acceptance_raw"]); w.writerows(events)
    print("acceptance hour (as written by EDGAR) histogram:", dict(sorted(hours.items())))
    json.dump(dict(built_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), amendment="A1",
                   unscreened_top10=raw_top, universe_rows=len(uni), events=len(events), hour_hist=hours,
                   universe_sha256=sha(UNI), events_sha256=sha(EVT)), open(META, "w"), indent=1)
    print(f"universe {len(uni)} rows ({UNI}); events {len(events)} ({EVT})")
    return 0


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    fr = {"data": [{"cik": i % 12, "val": 100 - i, "entityName": str(i)} for i in range(30)]}
    t = top10(fr)
    check("top10 is unique by CIK and ordered by float", len(t) == 10 and len({r["cik"] for r in t}) == 10 and t[0]["val"] == 100)
    blk = {"form": ["8-K", "10-Q", "8-K", "8-K/A"], "items": ["2.02,9.01", "", "5.02", "2.02"],
           "accessionNumber": list("abcd"), "filingDate": ["2024-01-01"] * 4, "acceptanceDateTime": ["2024-01-01T16:31:00.000Z"] * 4}
    check("Item 2.02 8-Ks selected (and not 5.02 or 10-Q)", [r[0] for r in item202(blk)] == ["a", "d"])
    cur = {"data": [{"cik": 1, "val": 3e16}, {"cik": 2, "val": 2e11}, {"cik": 3, "val": 1e11}, {"cik": 4, "val": 9e11}]}
    prv = {"data": [{"cik": 1, "val": 3e10}, {"cik": 2, "val": 1.5e11}, {"cik": 4, "val": 1e9}]}
    check("A1 screen drops the x1000 error, the x900 jump and the firm with no prior year",
          [r["cik"] for r in screened_top10(cur, prv)] == [2])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
