#!/usr/bin/env python3
"""Refresh the v41 forest's Mac-only inputs (PREREGISTRATION_v41.1).

RUN ON THE MAC -- it needs the network and the FRED key (~/.fred_key or
$FRED_API_KEY; the key is never printed). Writes ONLY to data/v41/refresh/:

    aaii_sentiment.xls      AAII weekly survey, full history
    cftc_positions.csv      CFTC TFF rows for the current and previous year
    DGS2.csv DTWEXBGS.csv GASREGW.csv   FRED, observations from 2025-01-01

Why a separate folder: fred_fetch_v31.py skips files already on disk and
sentiment_fetch.py never re-downloads the current year's CFTC zip, so running
them could never refresh anything -- and editing data/v31 or data/sentiment
in place would change the inputs closed results ran on. forward_forest.py v1.1
appends only rows dated AFTER each original file's last row, and only uses a
refreshed AAII workbook if it agrees with the original on every shared week.

Called by forward_tick.sh step 6 at most once a day (non-fatal); safe to run by hand:

    python3 refresh_v41_inputs.py
    python3 refresh_v41_inputs.py --self-test
"""
from __future__ import annotations

import argparse, csv, datetime as dt, json, os, sys, time

VERSION = "1.0"
OUT = "../data/v41/refresh"


def main():
    from sentiment_fetch import get, cftc_rows, WANT, AAII, CFTC
    from fred_fetch_v31 import call, obs
    from release_content import load_key
    os.makedirs(OUT, exist_ok=True)
    log = {"run_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "version": VERSION}
    print(f"refresh_v41_inputs.py v{VERSION}  -> {OUT}/ (nothing else is written)")
    # AAII
    try:
        blob, ctype = get(AAII)
        if blob[:1] == b"<" or "html" in ctype.lower():
            raise ValueError("got a web page, not the spreadsheet (bot check)")
        open(f"{OUT}/aaii_sentiment.xls", "wb").write(blob)
        log["aaii"] = "ok"; print("  AAII ok")
    except Exception as e:                                       # noqa: BLE001
        log["aaii"] = f"FAILED {type(e).__name__} {e}"; print(f"  AAII FAILED ({e})")
    # CFTC TFF, current and previous year, always re-downloaded
    rows = []
    y = dt.date.today().year
    for f in (f"fut_fin_txt_{y - 1}.zip", f"fut_fin_txt_{y}.zip"):
        try:
            blob, _ = get(CFTC + f)
            got = list(cftc_rows(blob))
            for r in got:
                r["report"] = "tff"
            rows += got; time.sleep(0.5)
            print(f"  CFTC {f}: {len(got)} rows")
        except Exception as e:                                   # noqa: BLE001
            log[f"cftc_{f}"] = f"FAILED {type(e).__name__}"; print(f"  CFTC {f} FAILED ({e})")
    if rows:
        keys = ["report", "instrument", "code", "name", "report_date"] + list(WANT)
        with open(f"{OUT}/cftc_positions.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys); w.writeheader()
            for r in sorted(rows, key=lambda r: (r["instrument"], r["report_date"])):
                w.writerow(r)
        log["cftc"] = len(rows)
    # FRED
    key = load_key()
    if not key:
        log["fred"] = "no key"; print("  FRED: no key ($FRED_API_KEY or ~/.fred_key)")
    else:
        for s in ("DGS2", "DTWEXBGS", "GASREGW"):
            try:
                o = obs(call(s, key, observation_start="2025-01-01"))
                with open(f"{OUT}/{s}.csv", "w", newline="") as fh:
                    w = csv.writer(fh); w.writerow(["date", "value"]); w.writerows(o)
                log[s] = f"{len(o)} obs to {o[-1][0]}"; print(f"  {s}: {len(o)} obs to {o[-1][0]}")
            except Exception as e:                               # noqa: BLE001
                log[s] = f"FAILED {type(e).__name__}"; print(f"  {s} FAILED ({type(e).__name__})")
            time.sleep(0.6)
    with open(f"{OUT}/refresh_log.jsonl", "a") as fh:
        fh.write(json.dumps(log) + "\n")
    return 0


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"refresh_v41_inputs.py v{VERSION} self-test\n")
    src = open(__file__).read()
    check("writes only under data/v41/refresh", src.count('open(f"{OUT}/') >= 4 and "../data/sentiment" not in src.split("def self_test")[0].replace('"../data/v41/refresh"', ""))
    import sentiment_fetch, fred_fetch_v31                         # noqa: F401
    check("reuses the v30/v31 parsers (cftc_rows, obs)", hasattr(sentiment_fetch, "cftc_rows") and hasattr(fred_fetch_v31, "obs"))
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else main())
