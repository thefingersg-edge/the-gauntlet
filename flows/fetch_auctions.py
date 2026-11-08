#!/usr/bin/env python3
"""
fetch_auctions.py -- FLOWS-11 Step 0: Treasury note/bond auctions 2005-01..2026-08
from the TreasuryDirect securities API. RUN ON THE MAC. Reads no price.
Keeps Notes and Bonds with term >= 5 years; drops TIPS and FRNs; records closing time.
    python3 fetch_auctions.py --self-test | (no args)
"""
from __future__ import annotations
import csv, datetime as dt, hashlib, json, os, re, sys, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fetch_ecb as FE    # noqa: E402
OUT = os.path.join(HERE, "data", "auction_events.csv"); META = OUT.replace(".csv", ".meta.json")
BASE = "https://www.treasurydirect.gov/TA_WS/securities/search?"


def years_of(term: str) -> float:
    """'10-Year', '9-Year 10-Month', '29-Year 11-Month' -> years."""
    y = re.search(r"(\d+)-Year", term or ""); m = re.search(r"(\d+)-Month", term or "")
    return (int(y.group(1)) if y else 0) + (int(m.group(1)) / 12 if m else 0)


def keep(r) -> bool:
    return (r.get("securityType") in ("Note", "Bond") and str(r.get("tips", "No")) != "Yes"
            and str(r.get("floatingRate", "No")) != "Yes" and years_of(r.get("securityTerm", "")) >= 4.5)


def fetch():
    rows = []
    for typ in ("Note", "Bond"):
        for y in range(2005, 2027):
            q = urllib.parse.urlencode(dict(format="json", type=typ, dateFieldName="auctionDate",
                                            startDate=f"01/01/{y}", endDate=f"12/31/{y}", pagesize=500))
            js = json.loads(FE.get(BASE + q))
            rows += js if isinstance(js, list) else js.get("securityList", [])
    return rows


def main():
    raw = fetch()
    out = {}
    for r in raw:
        if not keep(r):
            continue
        d = (r.get("auctionDate") or "")[:10]
        if not ("2005-01-01" <= d <= "2026-08-31"):
            continue
        out[(d, r.get("cusip"))] = (d, r.get("securityType"), r.get("securityTerm"), round(years_of(r.get("securityTerm")), 2),
                                    r.get("closingTimeCompetitive", ""), r.get("reopening", ""), r.get("cusip"))
    rows = sorted(out.values())
    per = {}
    for r in rows:
        per[r[0][:4]] = per.get(r[0][:4], 0) + 1
    print("auctions per year:", per)
    bad = {y: c for y, c in per.items() if not (15 <= c <= 80) and y != "2026"}
    if len(per) < 22 or bad:
        raise SystemExit(f"STOP: implausible auction counts {bad} / years {len(per)}. Nothing written.")
    ct = {}
    for r in rows:
        ct[r[4]] = ct.get(r[4], 0) + 1
    print("closing times:", ct)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["date", "type", "term", "years", "close_competitive", "reopening", "cusip"]); w.writerows(rows)
    s = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
    json.dump(dict(built_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), per_year=per,
                   closing_times=ct, n=len(rows), sha256=s), open(META, "w"), indent=1)
    print(f"{len(rows)} auctions; wrote {os.path.relpath(OUT, HERE)} sha256 {s}")
    return 0


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    check("term parse", years_of("9-Year 10-Month") == 9 + 10 / 12 and years_of("30-Year") == 30)
    check("keep a 10y note", keep({"securityType": "Note", "securityTerm": "10-Year", "tips": "No", "floatingRate": "No"}))
    check("drop TIPS, FRN, 3y", not keep({"securityType": "Note", "securityTerm": "10-Year", "tips": "Yes"})
          and not keep({"securityType": "Note", "securityTerm": "2-Year", "floatingRate": "Yes"})
          and not keep({"securityType": "Note", "securityTerm": "3-Year"}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
