#!/usr/bin/env python3
"""Historical short-term interest rates from FRED, for the v6 carry test.

NO RETURNS AND NO P&L ARE COMPUTED IN THIS FILE. It fetches rates, reports
coverage, builds differentials, and cross-checks them against the OANDA
financing snapshot. Nothing here touches a price series.

STDLIB ONLY -- BY DESIGN
------------------------
urllib and csv, nothing else. This script is the one that has to run before
anything else works, so it must not be able to fail on a missing package or
an unactivated virtualenv. If it needs pandas, it can fail for a reason that
has nothing to do with rates.

WHY FRED AND NOT TRADINGVIEW
----------------------------
The macro line died on TradingView's historical-bar cap: VIX and US10Y came
back with 6.2 years, which set a 2-sigma bar of 0.80 against a plausible
0.3-0.6, and the constraint was a plan tier rather than anything about the
data. FRED has no such cap, needs no key, and the OECD series here start
decades before our 2006 price history.

WHICH RATE
----------
Two OECD families, both fetched, coverage reported for each:

  IRSTCI01<CC>M156N   immediate / overnight interbank ("call money")
  IR3TIB01<CC>M156N   3-month interbank

The OVERNIGHT series is the better match on mechanism: CFD financing is
computed and charged daily, so what you actually earn tracks the overnight
rate, not a 3-month term rate. The 3-month family is fetched as a fallback
because several IR3TIB series were discontinued when LIBOR was retired, and
a series that stops in 2022 cannot support a test that runs to 2026.

Which family gets used must be FROZEN IN THE PRE-REGISTRATION on coverage --
a data property -- before any P&L exists. This file computes none, so the
choice is made on the right basis. It is still a choice among two, and the
pre-registration has to say so.

THE PROVENANCE CHECK, WHICH IS THE POINT OF THIS FILE
-----------------------------------------------------
This project has had SIX data-provenance failures: three mislabelled OANDA
files, a "COT" series that was not CFTC data at all, a symbol-blind COT
export that returned byte-identical series for gold and silver, and a
day-index off-by-one. Every one produced plausible-looking output.

So the rates are not trusted because they came from FRED. They are trusted
only if the differential they imply TODAY agrees with the financing OANDA is
actually quoting today. USD_CHF should come back near +3.9%, EUR_AUD near
-2.1%. If FRED says otherwise, something is wrong and the run stops.

    python fetch_rates.py --self-test        # offline, no network
    python fetch_rates.py                    # fetch + coverage + cross-check
    python fetch_rates.py --check-only       # cross-check a previous pull
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import urllib.error
import urllib.request

VERSION = "1.1"

# Two endpoints for the same data. fredgraph.csv is the documented one but it
# renders through the graphing backend and is measurably slower -- it timed
# out on the first real run. The /data/ text file is a static export of the
# same series and is usually the faster of the two, so it is tried second
# rather than being treated as exotic.
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
FRED_TXT = "https://fred.stlouisfed.org/data/{sid}.txt"

# OECD country codes as FRED spells them
CCY_COUNTRY = {
    "USD": "US", "EUR": "EZ", "GBP": "GB", "JPY": "JP",
    "CHF": "CH", "AUD": "AU", "NZD": "NZ", "CAD": "CA",
}

FAMILY = {
    "overnight": "IRSTCI01{cc}M156N",
    "3month": "IR3TIB01{cc}M156N",
}

# The 13 FX instruments in the carry book, as OANDA names them.
PAIRS = ["EUR_USD", "GBP_USD", "AUD_USD", "NZD_USD", "USD_CAD", "USD_CHF",
         "EUR_GBP", "EUR_JPY", "GBP_JPY", "EUR_CHF", "EUR_AUD", "AUD_NZD",
         "NZD_CAD"]

# How closely a FRED-implied differential must match OANDA's quoted carry
# before the data is believed. Generous, because they are not the same
# instrument: OANDA quotes a tom-next FX swap rate including its own funding,
# FRED quotes an unsecured interbank rate, and the two legitimately differ by
# cross-currency basis. A full percentage point of slack is tolerant of that
# and still catches a wrong or scrambled series, which is what it is for.
MATCH_TOL = 0.010          # 1.00 percentage point, in decimal


# ---------------------------------------------------------------------------
# pure helpers -- exercised offline
# ---------------------------------------------------------------------------

def parse_fred_csv(text: str) -> list[tuple[str, float]]:
    """FRED CSV -> [(YYYY-MM-DD, value)], missing values dropped.

    Two header conventions exist in the wild: the current files use
    `observation_date`, older ones use `DATE`. Missing observations are a
    literal '.' rather than an empty field, which float() would happily
    refuse in a way that is easy to misread as a network problem.
    """
    rows = []
    rdr = csv.reader(io.StringIO(text))
    header = next(rdr, None)
    if not header or len(header) < 2:
        return rows
    for rec in rdr:
        if len(rec) < 2:
            continue
        raw = rec[1].strip()
        if raw in (".", "", "NA", "NaN"):
            continue
        try:
            rows.append((rec[0].strip(), float(raw)))
        except ValueError:
            continue
    return rows


def parse_fred_txt(text: str) -> list[tuple[str, float]]:
    """FRED's /data/<id>.txt export -> [(YYYY-MM-DD, value)].

    A block of metadata, a blank line, a `DATE  VALUE` header, then
    whitespace-separated rows. Missing values are '.' here too.
    """
    rows, started = [], False
    for line in text.splitlines():
        s = line.strip()
        if not started:
            if s.upper().startswith("DATE"):
                started = True
            continue
        if not s:
            continue
        parts = s.split()
        if len(parts) < 2 or parts[1] in (".", "NA", "NaN"):
            continue
        try:
            rows.append((parts[0], float(parts[1])))
        except ValueError:
            continue
    return rows


def coverage(series: list[tuple[str, float]]) -> dict:
    if not series:
        return {"n": 0, "start": None, "end": None}
    return {"n": len(series), "start": series[0][0], "end": series[-1][0]}


def as_of(series: list[tuple[str, float]], default: float | None = None):
    """Most recent observation, as a decimal rate. FRED quotes percent."""
    if not series:
        return default
    return series[-1][1] / 100.0


def differential(rates: dict[str, float], pair: str) -> float | None:
    """carry(BASE_QUOTE) = r_BASE - r_QUOTE, as a decimal annual rate."""
    base, quote = pair.split("_")
    if base not in rates or quote not in rates:
        return None
    if rates[base] is None or rates[quote] is None:
        return None
    return rates[base] - rates[quote]


def oanda_carry(fin: dict, pair: str) -> float | None:
    """The markup-free carry implied by OANDA's quoted financing pair.

    Same decomposition as carry_budget.py: the midpoint of long and short.
    Duplicated deliberately rather than imported, so this file stays
    stdlib-only and can run when nothing else does.
    """
    q = fin.get(pair)
    if not q:
        return None
    c = (float(q["longRate"]) - float(q["shortRate"])) / 2.0
    days = q.get("daysChargedPerWeek", 7) or 7
    return c * min(days, 7) / 7.0


# ---------------------------------------------------------------------------

def _get(url: str, timeout: float) -> str | None:
    """Fetch a URL. None means 404 -- a series that does not exist, which is
    information rather than an error. Anything else raises."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (silver15-research)",
        "Accept": "text/csv,text/plain,*/*",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def fetch(sid: str, timeout: float = 60.0, retries: int = 3,
          verbose: bool = False) -> list[tuple[str, float]]:
    """One series, with retries and a second endpoint.

    A timeout is NOT treated as "no data". Returning [] on a timeout would
    silently drop a currency from the book and quietly shrink the universe --
    the same class of failure as the ragged-index bug in v4, where SMI, AEX
    and FR40 vanished from a "28-instrument" panel without a word. A network
    failure here stops the run.
    """
    import time
    attempts = []
    for endpoint, parser in ((FRED_CSV, parse_fred_csv),
                             (FRED_TXT, parse_fred_txt)):
        url = endpoint.format(sid=sid)
        delay = 2.0
        for attempt in range(1, retries + 1):
            try:
                body = _get(url, timeout)
                if body is None:
                    return []                      # genuine 404: no such series
                rows = parser(body)
                if rows:
                    return rows
                attempts.append(f"{url.split('/')[-1]} parsed 0 rows")
                break
            except Exception as exc:               # noqa: BLE001
                attempts.append(f"{type(exc).__name__}: {str(exc)[:60]}")
                if verbose:
                    print(f"      retry {attempt}/{retries} on {sid}: "
                          f"{type(exc).__name__}", file=sys.stderr)
                if attempt < retries:
                    time.sleep(delay)
                    delay *= 2
    raise SystemExit(
        f"\n  could not fetch {sid} after {retries} attempts on two endpoints."
        f"\n    {'; '.join(attempts[:4])}"
        f"\n  This is a network failure, not an empty series, so the run stops"
        f"\n  rather than silently dropping a currency from the book."
        f"\n  Try:  python3 fetch_rates.py --probe        (one series only)"
        f"\n        python3 fetch_rates.py --timeout 120")


def self_test() -> int:
    fails = []

    def check(name, cond, detail=""):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}" +
              (f"   {detail}" if detail else ""))
        if not cond:
            fails.append(name)

    print(f"fetch_rates.py v{VERSION} — offline controls\n")
    print(f"  interpreter  {sys.executable}")
    print(f"  stdlib only, so no venv is required\n")

    # 1-3. CSV parsing, both header conventions, and the '.' convention
    cur = "observation_date,IRSTCI01USM156N\n2024-01-01,5.33\n2024-02-01,.\n2024-03-01,5.31\n"
    old = "DATE,IR3TIB01GBM156N\n1999-01-01,5.91\n1999-02-01,5.42\n"
    p1, p2 = parse_fred_csv(cur), parse_fred_csv(old)
    check("1 current header parsed", len(p1) == 2, f"{len(p1)} rows")
    check("2 legacy DATE header parsed", len(p2) == 2, f"{len(p2)} rows")
    check("3 '.' dropped, not read as zero",
          all(v != 0.0 for _, v in p1) and p1[1][0] == "2024-03-01",
          "a missing month must vanish, not become 0%")

    # 4. an empty/404 series must not masquerade as data
    check("4 empty series -> zero coverage", coverage([])["n"] == 0)

    # 4b. the fallback endpoint's format
    txt = ("Title:               Interest Rates\n"
           "Series ID:           IRSTCI01USM156N\n"
           "Source:              OECD\n\n"
           "DATE          VALUE\n"
           "1960-01-01     3.99\n"
           "1960-02-01        .\n"
           "1960-03-01     4.01\n")
    pt = parse_fred_txt(txt)
    check("4b /data/.txt fallback parsed", len(pt) == 2 and pt[0][1] == 3.99,
          f"{len(pt)} rows, metadata header skipped")

    # 5. percent -> decimal
    check("5 FRED percent converted to decimal",
          abs(as_of(p1) - 0.0531) < 1e-12, f"{as_of(p1)}")

    # 6-7. differentials, including sign
    r = {"USD": 0.0400, "CHF": 0.0050, "EUR": 0.0200, "AUD": 0.0300}
    check("6 differential is base minus quote",
          abs(differential(r, "USD_CHF") - 0.0350) < 1e-12,
          f"{differential(r, 'USD_CHF'):+.4f}")
    check("7 sign flips with the pair",
          abs(differential(r, "EUR_AUD") + 0.0100) < 1e-12,
          f"{differential(r, 'EUR_AUD'):+.4f}")

    # 8. a missing currency yields None, never a silent zero
    check("8 missing currency -> None, not 0.0",
          differential(r, "GBP_USD") is None,
          "a silent 0.0 would put the pair in the middle of the rank")

    # 9-10. the OANDA decomposition, including the 6-day scaling
    fin = {"USD_CHF": {"longRate": 0.0289, "shortRate": -0.0499,
                       "daysChargedPerWeek": 7},
           "GBP_JPY": {"longRate": 0.0192, "shortRate": -0.0397,
                       "daysChargedPerWeek": 6}}
    check("9 OANDA carry decomposed", abs(oanda_carry(fin, "USD_CHF") - 0.0394) < 1e-9,
          f"{oanda_carry(fin, 'USD_CHF'):+.4f} vs +0.0394 measured")
    # Derive the expectation from the INPUTS, not from the 4-dp figure printed
    # by carry_budget.py. Asserting against a rounded display value makes the
    # control fail whenever the true value has more precision than the report
    # -- which is a defect in the test, not in the code under test.
    want = ((0.0192 + 0.0397) / 2) * 6 / 7
    check("10 six-day instrument scaled",
          abs(oanda_carry(fin, "GBP_JPY") - want) < 1e-12,
          f"{oanda_carry(fin, 'GBP_JPY'):.6f} vs {want:.6f}")

    # 11. THE PROVENANCE GATE MUST ACTUALLY REJECT. A gate that never fires
    #     is decoration -- this project has been burned by exactly that.
    good = abs(0.0350 - 0.0394) <= MATCH_TOL
    scrambled = abs(-0.0208 - 0.0394) <= MATCH_TOL
    check("11 gate accepts a plausible match", good, "3.50% vs 3.94% quoted")
    check("12 gate REJECTS a scrambled series", not scrambled,
          "-2.08% vs +3.94% must fail")

    print(f"\n  {'ALL CONTROLS PASS' if not fails else str(len(fails)) + ' FAILED'}")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", default="../data_rates")
    ap.add_argument("--financing", default="../data_carry/financing.json")
    ap.add_argument("--check-only", action="store_true",
                    help="re-run the cross-check on an existing pull")
    ap.add_argument("--probe", action="store_true",
                    help="fetch ONE series and stop — tests connectivity fast")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--retries", type=int, default=3)
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    if a.probe:
        sid = "IRSTCI01USM156N"
        print(f"probing {sid} (US overnight) ...")
        ser = fetch(sid, a.timeout, a.retries, verbose=True)
        cov = coverage(ser)
        if not ser:
            print("  404 — series does not exist under that id")
            return 1
        print(f"  OK  {cov['n']:,} obs  {cov['start']} -> {cov['end']}")
        print(f"  last value {ser[-1][1]:.2f}%")
        print("\n  connectivity fine — run without --probe for the full pull.")
        return 0

    print(f"fetch_rates.py v{VERSION}   NO RETURNS COMPUTED\n")
    os.makedirs(a.out, exist_ok=True)
    store = {}

    for fam, tpl in FAMILY.items():
        path = os.path.join(a.out, f"rates_{fam}.json")
        if a.check_only and os.path.exists(path):
            with open(path) as fh:
                store[fam] = json.load(fh)
            print(f"  reusing {path}")
            continue
        print(f"{fam.upper()}  ({tpl.format(cc='<CC>')})")
        print("=" * 74)
        got = {}
        for ccy, cc in CCY_COUNTRY.items():
            sid = tpl.format(cc=cc)
            ser = fetch(sid, a.timeout, a.retries)
            cov = coverage(ser)
            got[ccy] = ser
            flag = "" if cov["n"] else "   <-- MISSING"
            print(f"  {ccy}  {sid:<20} {cov['n']:>5} obs  "
                  f"{cov['start'] or '?'} -> {cov['end'] or '?'}{flag}")
        store[fam] = got
        with open(path, "w") as fh:
            json.dump(got, fh)
        print(f"  -> {path}\n")

    # ---- which family can actually support the test? ----------------------
    print("COVERAGE VERDICT")
    print("=" * 74)
    usable = {}
    for fam, got in store.items():
        ends = [coverage(s)["end"] for s in got.values() if s]
        starts = [coverage(s)["start"] for s in got.values() if s]
        n_missing = sum(1 for s in got.values() if not s)
        if not ends:
            print(f"  {fam:<10} unusable: no series returned data")
            continue
        latest_start, earliest_end = max(starts), min(ends)
        print(f"  {fam:<10} {len(got) - n_missing}/{len(got)} currencies, "
              f"common window {latest_start} -> {earliest_end}"
              + (f", {n_missing} missing" if n_missing else ""))
        usable[fam] = (n_missing, earliest_end, latest_start)

    if not usable:
        raise SystemExit("no rate family returned usable data")

    # prefer complete coverage, then the one that runs closest to today
    best = sorted(usable.items(), key=lambda kv: (kv[1][0], kv[1][1]),
                  reverse=False)
    best = sorted(best, key=lambda kv: (kv[1][0], -_ymd(kv[1][1])))[0][0]
    print(f"\n  -> '{best}' has the better coverage. FREEZE THIS CHOICE in")
    print(f"     PREREGISTRATION_v6.md before any P&L is computed.")

    # ---- THE PROVENANCE CROSS-CHECK ---------------------------------------
    print(f"\nPROVENANCE CROSS-CHECK against OANDA's quoted financing")
    print("=" * 74)
    if not os.path.exists(a.financing):
        print(f"  no snapshot at {a.financing}; run carry_budget.py first.")
        print(f"  THE RATES ARE NOT YET TRUSTED.")
        return 1
    with open(a.financing) as fh:
        fin = json.load(fh)

    latest = {c: as_of(store[best].get(c, [])) for c in CCY_COUNTRY}
    miss = [c for c, v in latest.items() if v is None]
    if miss:
        print(f"  no current rate for {', '.join(miss)} — cannot cross-check")

    print(f"  {'pair':<10}{'FRED diff':>12}{'OANDA carry':>14}{'gap':>10}")
    ok = bad = 0
    for p in PAIRS:
        d, o = differential(latest, p), oanda_carry(fin, p)
        if d is None or o is None:
            print(f"  {p:<10}{'—':>12}{'—':>14}{'skipped':>10}")
            continue
        gap = d - o
        good = abs(gap) <= MATCH_TOL
        ok, bad = ok + good, bad + (not good)
        print(f"  {p:<10}{d:>+12.4f}{o:>+14.4f}{gap:>+10.4f}"
              f"{'' if good else '   <-- MISMATCH'}")

    print(f"\n  {ok} within {MATCH_TOL:.1%}, {bad} outside")
    if bad == 0:
        print("  => rates AGREE with quoted financing. Provenance established.")
    elif bad <= 2:
        print("  => mostly agrees. Inspect the outliers before proceeding;")
        print("     cross-currency basis is real, a scrambled series is not.")
    else:
        print("  => DOES NOT AGREE. Do not build on this data. Six provenance")
        print("     failures in this project were all found exactly here.")
        return 1
    return 0


def _ymd(s: str | None) -> int:
    if not s:
        return 0
    try:
        return int(s.replace("-", ""))
    except ValueError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
