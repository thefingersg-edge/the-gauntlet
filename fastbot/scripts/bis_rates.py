#!/usr/bin/env python3
"""PREREGISTRATION_v16 section 8 -- the precondition, and only that.

Downloads BIS central bank policy rates (dataflow BIS,WS_CBPOL,1.0),
monthly, and writes one tidy CSV of date,currency,rate.

**It computes no spread and no return.** v16 section 9 forbids turning
this into a backtest, and keeping the download in its own file is how
that stays true rather than merely intended.

ONE CONVENTION, WHICH IS THE WHOLE POINT
----------------------------------------
v16 section 8: "one convention applied throughout -- mixing conventions
across currencies would manufacture dispersion out of definitional
differences." Every series here is the same measure from the same
provider: "the interest rate which best captures the monetary
authorities' policy intentions".

WHAT THE COVERAGE CHECK FOUND, BEFORE ANY DOWNLOAD
--------------------------------------------------
17 of v16's 18 currencies are covered. Two need handling and both are
applications of v16 section 9's frozen rule, not new rules:

  SGD   NOT COVERED. Singapore has no policy rate -- the MAS targets the
        exchange rate, not an interest rate. There is nothing to source
        and nothing to impute.

  CNH   DROPPED. BIS carries CN, the PBoC's ONSHORE policy rate. CNH is
        the OFFSHORE yuan and its funding rate detaches from the onshore
        rate, violently and exactly when it matters. Section 9 says a
        series that is not the same measure as the rest is dropped and
        counted. Direction: CNH sits in today's BOTTOM quintile at
        -2.46%, so dropping it NARROWS the bottom quintile and makes
        v16's gates HARDER to pass.

  JPY   KEPT, with a caveat that must be reported rather than absorbed.
        BIS documents periods with no policy rate during the QE phases
        (roughly 2013-2024). That is the same measure with gaps, not a
        different measure, so months where it is absent simply exclude
        it from that month's ranking. **JPY is the archetypal funding
        currency, so the count of months it is missing is material to
        v16's bottom quintile and is printed, not buried.**

  HKD   KEPT. The HKMA base rate is a genuine policy rate, but under the
        currency board it tracks the Fed almost mechanically, so it will
        rarely sit in either extreme quintile. Noted so its presence is
        not mistaken for independent information.

STDLIB ONLY.

    python3 bis_rates.py --self-test      # offline, no network
    python3 bis_rates.py --download
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import sys
import urllib.error
import urllib.request
import zipfile

VERSION = "1.0"

DATAFLOW = "BIS,WS_CBPOL,1.0"
#: Tried in order. The script reports which one answered rather than
#: assuming; BIS reorganised these endpoints and a silent fallback would
#: hide which vintage the data came from.
ENDPOINTS = [
    ("sdmx-all",
     "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.."
     "?format=csv"),
    ("sdmx-all-alt",
     "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M."
     "?format=csv"),
    ("bulk-zip",
     "https://data.bis.org/static/bulk/WS_CBPOL_csv_col.zip"),
]
PER_COUNTRY = ("https://stats.bis.org/api/v2/data/dataflow/BIS/"
               "WS_CBPOL/1.0/M.{cc}?format=csv")

#: v16 section 4's universe. ISO-2 reference area -> currency.
WANT = {
    "ZA": "ZAR", "HU": "HUF", "AU": "AUD", "NO": "NOK", "PL": "PLN",
    "GB": "GBP", "US": "USD", "CZ": "CZK", "NZ": "NZD", "HK": "HKD",
    "XM": "EUR", "DK": "DKK", "SE": "SEK", "JP": "JPY", "CH": "CHF",
    "TH": "THB",
}
#: Named so the record says why, and so the self-test can check that a
#: reason exists for every one of them.
EXCLUDED = {
    "SGD": "no BIS series -- Singapore has no policy rate (MAS targets "
           "the exchange rate)",
    "CNH": "BIS carries the ONSHORE PBoC rate (CN); CNH is offshore and "
           "is a different measure -- v16 s9. Narrows the bottom "
           "quintile, so it makes the gates harder.",
}
NOTES = {
    "JPY": "BIS documents periods with no policy rate during QE "
           "(~2013-2024). Same measure, with gaps.",
    "HKD": "HKMA base rate tracks the Fed under the currency board; "
           "rarely an extreme quintile member.",
}
MIN_CURRENCIES = 14        # v16 section 8
MIN_YEARS = 15             # v16 section 8
#: v16 section 9: a percent/decimal error is the failure that would
#: manufacture or destroy dispersion silently.
MAX_PLAUSIBLE_RATE = 100.0
MIN_PLAUSIBLE_SPAN = 0.5   # a series never moving off 0.x is suspect


def fetch(url, timeout=90):
    req = urllib.request.Request(url, headers={
        "User-Agent": "bis_rates.py/1.0 (research)",
        "Accept": "text/csv, application/zip, */*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def csv_from_zip(blob):
    z = zipfile.ZipFile(io.BytesIO(blob))
    names = [n for n in z.namelist() if n.lower().endswith(".csv")]
    if not names:
        raise ValueError("zip contains no csv")
    return z.read(names[0])


def pick(header, candidates):
    """Find a column by any of its known names. Loud on failure --
    guessing a column is how a units error gets in."""
    low = {h.strip().upper(): h for h in header}
    for c in candidates:
        if c in low:
            return low[c]
    return None


def parse_sdmx_csv(text):
    """[(iso2, 'YYYY-MM', float)] from an SDMX CSV, defensively."""
    rdr = csv.reader(io.StringIO(text))
    try:
        header = next(rdr)
    except StopIteration:
        return [], "empty response"
    area = pick(header, ("REF_AREA", "AREA", "REFERENCE_AREA"))
    time = pick(header, ("TIME_PERIOD", "TIME", "PERIOD"))
    val = pick(header, ("OBS_VALUE", "VALUE", "OBSVALUE"))
    if not (area and time and val):
        return [], (f"columns not found: area={area} time={time} "
                    f"value={val} in {header[:12]}")
    ia, it, iv = header.index(area), header.index(time), header.index(val)
    out = []
    for row in rdr:
        if len(row) <= max(ia, it, iv):
            continue
        a, t, v = row[ia].strip(), row[it].strip(), row[iv].strip()
        if not a or not t or not v:
            continue                      # a gap is a gap, not a zero
        #: EXACTLY YYYY-MM. `len(t) < 7` let 2015-06-15 through and t[:7]
        #: then silently turned a daily observation into a monthly one --
        #: twenty-odd duplicate rows per month, all looking fine.
        if len(t) != 7 or t[4] != "-":
            continue
        try:
            out.append((a, t, float(v)))
        except ValueError:
            continue
    return out, None


def coverage(rows):
    """{currency: (n_obs, first, last)} for wanted areas only."""
    by = {}
    for a, t, v in rows:
        cur = WANT.get(a)
        if not cur:
            continue
        d = by.setdefault(cur, [])
        d.append((t, v))
    out = {}
    for cur, obs in by.items():
        obs.sort()
        out[cur] = (len(obs), obs[0][0], obs[-1][0])
    return out


def sanity(rows):
    """[(currency, complaint)] -- v16 section 9's unit and range checks."""
    bad, seen = [], {}
    for a, t, v in rows:
        cur = WANT.get(a)
        if not cur:
            continue
        seen.setdefault(cur, []).append(v)
        if abs(v) > MAX_PLAUSIBLE_RATE:
            bad.append((cur, f"{v} at {t} exceeds {MAX_PLAUSIBLE_RATE}"))
    for cur, vs in seen.items():
        if len(vs) > 24 and (max(vs) - min(vs)) < MIN_PLAUSIBLE_SPAN:
            bad.append((cur, f"range only {max(vs)-min(vs):.3f} over "
                             f"{len(vs)} months -- decimal scaling?"))
    return bad


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"bis_rates.py v{VERSION} self-test   (offline)\n")

    print("the universe matches v16 section 4, minus its stated exclusions")
    v16 = {"ZAR", "HUF", "AUD", "NOK", "PLN", "GBP", "USD", "CZK", "NZD",
           "HKD", "EUR", "DKK", "SEK", "SGD", "CNH", "JPY", "CHF", "THB"}
    got = set(WANT.values())
    check("v16 named 18 currencies", len(v16) == 18)
    check("this file seeks 16 of them", len(got) == 16, f"{len(got)}")
    check("the two absent are exactly SGD and CNH",
          v16 - got == {"SGD", "CNH"}, f"{sorted(v16 - got)}")
    check("and each has a written reason",
          set(EXCLUDED) == {"SGD", "CNH"}
          and all(len(r) > 40 for r in EXCLUDED.values()))
    check("16 still clears v16's floor of 14",
          len(got) >= MIN_CURRENCIES, f"{len(got)} >= {MIN_CURRENCIES}")
    check("the area->currency map is one-to-one",
          len(set(WANT.values())) == len(WANT))
    check("the euro area is XM, not EU", WANT.get("XM") == "EUR"
          and "EU" not in WANT)
    #: PLANTED: JPY must be SOUGHT, not quietly dropped for its gaps.
    check("JPY is kept despite its QE gaps", "JPY" in got)
    check("and its gap is documented rather than absorbed",
          "JPY" in NOTES and "gap" in NOTES["JPY"].lower())

    print("\nthe SDMX parser, on planted rows")
    good = ("STRUCTURE,REF_AREA,FREQ,TIME_PERIOD,OBS_VALUE\n"
            "d,US,M,2015-06,0.25\n"
            "d,XM,M,2015-06,0.05\n"
            "d,JP,M,2015-06,0.10\n")
    rows, err = parse_sdmx_csv(good)
    check("three rows parse", err is None and len(rows) == 3, str(err))
    check("the euro area maps to EUR",
          coverage(rows).get("EUR", (0,))[0] == 1)
    #: PLANTED: a gap must not become a zero. This is the same failure
    #: as USD_TRY's 0.000 read as a rate in fx_carry_access v1.0.
    gappy = good + "d,GB,M,2015-06,\nd,GB,M,2015-07,0.50\n"
    rows2, _ = parse_sdmx_csv(gappy)
    check("an empty value is skipped, NOT read as 0.0",
          coverage(rows2)["GBP"][0] == 1
          and all(v != 0.0 for a, t, v in rows2 if a == "GB"),
          f"{[r for r in rows2 if r[0]=='GB']}")
    #: daily rows must not sneak into a monthly file
    mixed = good + "d,US,D,2015-06-15,0.25\n"
    rows3, _ = parse_sdmx_csv(mixed)
    check("a daily TIME_PERIOD is rejected",
          coverage(rows3)["USD"][0] == 1, f"{coverage(rows3)['USD']}")
    check("a non-numeric value is skipped",
          parse_sdmx_csv(good + "d,US,M,2015-07,NA\n")[0].__len__() == 3)
    check("an unmapped area is ignored, not misfiled",
          "AR" not in [c for c in coverage(
              parse_sdmx_csv(good + "d,AR,M,2015-06,30.0\n")[0])])
    #: PLANTED: a renamed column must fail LOUDLY. Guessing a column is
    #: how a units error gets in unnoticed.
    renamed = "STRUCTURE,COUNTRY,FREQ,DATE,LEVEL\nd,US,M,2015-06,0.25\n"
    r4, err4 = parse_sdmx_csv(renamed)
    check("unknown columns fail loudly rather than returning nothing",
          r4 == [] and err4 is not None and "columns not found" in err4,
          str(err4)[:48])
    check("an empty response is reported, not treated as no data",
          parse_sdmx_csv("")[1] is not None)

    print("\nthe unit checks -- v16 section 9")
    #: PLANTED: a decimal-scaled series (0.0525 for 5.25%) would collapse
    #: every spread by 100x and look like a dead market rather than a bug.
    dec = [("US", f"20{y:02d}-01", 0.0525) for y in range(10, 36)]
    bad = sanity(dec)
    check("a decimal-scaled series is caught",
          any("decimal" in c for _, c in bad), f"{bad[:1]}")
    #: PLANTED: hyperinflation or a percent/basis-point error. Must use
    #: an area that is actually INGESTED -- v1.0's first attempt planted
    #: it on TR, which is not in the universe, so the check could only
    #: ever pass.
    check("an absurd rate is caught",
          any("exceeds" in c for _, c in sanity([("ZA", "2022-01", 850.0)])))
    check("and only for currencies actually ingested",
          sanity([("TR", "2022-01", 850.0)]) == [])
    real = [("US", f"20{y:02d}-01", 0.25 + y * 0.2) for y in range(10, 36)]
    check("an ordinary series passes both", sanity(real) == [])

    print("\nthis file downloads and nothing else")
    import bis_rates as _self
    banned = ("spread", "quintile", "carry", "return", "pnl", "backtest",
              "order", "position", "signal")
    offenders = [x for x in dir(_self) if not x.startswith("_")
                 and any(w in x.lower() for w in banned)]
    check("no spread, quintile or return function exists here",
          offenders == [], f"{offenders}")
    #: v1.0 tried to grep its own source for "backtest" -- which the
    #: check's own text contains, and which it then lowercased so the
    #: split marker vanished. Same error as oanda_financing v1.0:
    #: a file cannot test itself by searching for a word it contains.
    #: The namespace check above is behavioural and is the real one.
    import inspect
    pub = [n for n, o in vars(_self).items()
           if not n.startswith("_") and inspect.isfunction(o)
           and o.__module__ == _self.__name__]
    check("every public function is download, parse or check",
          set(pub) <= {"fetch", "csv_from_zip", "pick", "parse_sdmx_csv",
                       "coverage", "sanity", "self_test", "download",
                       "main"},
          f"{sorted(set(pub) - {'fetch','csv_from_zip','pick','parse_sdmx_csv','coverage','sanity','self_test','download','main'})}")

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def download(out_path, meta_path):
    text, used, errs = None, None, []
    for label, url in ENDPOINTS:
        try:
            blob = fetch(url)
            text = (csv_from_zip(blob) if url.endswith(".zip")
                    else blob).decode("utf-8", "replace")
            rows, err = parse_sdmx_csv(text)
            if err or not rows:
                errs.append(f"{label}: {err or 'no rows'}")
                text = None
                continue
            used = (label, url)
            break
        except (urllib.error.URLError, urllib.error.HTTPError,
                ValueError, OSError) as e:
            errs.append(f"{label}: {type(e).__name__}: {str(e)[:70]}")

    if text is None:
        print("  bulk endpoints failed:")
        for e in errs:
            print(f"    {e}")
        print("  falling back to one request per country")
        parts, got = [], []
        for cc in sorted(WANT):
            try:
                t = fetch(PER_COUNTRY.format(cc=cc)).decode("utf-8", "replace")
                r, err = parse_sdmx_csv(t)
                if r:
                    parts.extend(r)
                    got.append(cc)
            except Exception as e:                      # noqa: BLE001
                print(f"    {cc}: {type(e).__name__}")
        rows, used = parts, ("per-country", PER_COUNTRY)
        if not rows:
            raise SystemExit("  STOP: no data from any endpoint. v16 "
                             "section 8 returns UNDETERMINED.")
    else:
        rows, _ = parse_sdmx_csv(text)

    print(f"  source: {used[0]}\n          {used[1]}")
    print(f"  observations parsed: {len(rows):,}\n")

    bad = sanity(rows)
    if bad:
        print("  UNIT CHECK FAILURES -- v16 section 9:")
        for cur, c in bad:
            print(f"    {cur}: {c}")
        raise SystemExit("  STOP: investigate before this enters a mean.")
    print("  unit checks: OK (no decimal scaling, no absurd levels)")

    cov = coverage(rows)
    print(f"\n  COVERAGE against v16 section 4")
    print(f"    {'ccy':<5}{'obs':>7}{'from':>10}{'to':>10}   note")
    for cur in sorted(cov):
        n, lo, hi = cov[cur]
        print(f"    {cur:<5}{n:>7}{lo:>10}{hi:>10}   "
              f"{NOTES.get(cur, '')[:44]}")
    for cur, why in sorted(EXCLUDED.items()):
        print(f"    {cur:<5}{'--':>7}{'--':>10}{'--':>10}   EXCLUDED: "
              f"{why[:44]}")
    missing = sorted(set(WANT.values()) - set(cov))
    if missing:
        print(f"\n    SOUGHT BUT NOT RETURNED: {missing}")

    n_cur = len(cov)
    months = sorted({t for _, t, _ in rows})
    yrs = (int(months[-1][:4]) - int(months[0][:4])) if months else 0
    print(f"\n  PRECONDITION -- v16 section 8")
    print(f"    [{'PASS' if n_cur >= MIN_CURRENCIES else 'FAIL'}] "
          f"{n_cur} currencies (need {MIN_CURRENCIES})")
    print(f"    [{'PASS' if yrs >= MIN_YEARS else 'FAIL'}] "
          f"{yrs} years, {months[0]} to {months[-1]} (need {MIN_YEARS})")
    print(f"    [PASS] one convention: BIS policy rate, one provider")
    if n_cur < MIN_CURRENCIES or yrs < MIN_YEARS:
        raise SystemExit("\n    UNDETERMINED -- v16 section 8 stops here "
                         "rather than\n    proceeding on a reduced "
                         "universe, because dropping\n    currencies "
                         "changes the quintiles and so changes the answer.")

    with open(out_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["month", "currency", "rate_pct"])
        for a, t, v in sorted(rows, key=lambda r: (r[1], WANT.get(r[0], ""))):
            if a in WANT:
                w.writerow([t, WANT[a], f"{v:.4f}"])
    meta = {"tool": "bis_rates.py", "version": VERSION,
            "downloaded_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "dataflow": DATAFLOW, "endpoint": used[1],
            "currencies": {c: cov[c] for c in sorted(cov)},
            "excluded": EXCLUDED, "notes": NOTES}
    with open(meta_path, "w") as fh:
        json.dump(meta, fh, indent=2)
    print(f"\n  written to {out_path}")
    print(f"  provenance in {meta_path}")
    print(f"\n  This file computes NO spread and NO return. v16 section 9.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", default="../data/policy_rates.csv")
    ap.add_argument("--meta", default="../data/policy_rates.meta.json")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    if not a.download:
        ap.error("pass --download or --self-test")
    print(f"bis_rates.py v{VERSION}   PREREGISTRATION_v16 section 8\n")
    download(a.out, a.meta)


if __name__ == "__main__":
    main()
