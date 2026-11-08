"""
fetch_cot.py — CFTC Commitments of Traders, legacy futures-only.

Free, weekly, back to 1986. Socrata endpoint, no API key needed for modest
volumes. Run from your own Terminal like fetch_fred.py / fetch_oanda.py —
the sandboxed shell has no egress.

    .venv/bin/python fetch_cot.py --renames        # the Feb-2022 rename cohort
    .venv/bin/python fetch_cot.py --names          # every contract name + span
    .venv/bin/python fetch_cot.py --probe          # check the whole mapping
    .venv/bin/python fetch_cot.py --list gold      # find one exact CFTC name
    .venv/bin/python fetch_cot.py                  # fetch all mapped markets
    .venv/bin/python fetch_cot.py xauusd eurusd    # fetch a subset

Writes adaptive/cot/<market>.csv with columns:
    report_date, comm_long, comm_short, oi, market_name

CFTC contract names have changed over the years ("BRITISH POUND STERLING"
became "BRITISH POUND"), so matching is by prefix and every alias is tried in
order. --list is there so a mismatch gets found and fixed rather than
silently returning an empty series — that is the failure mode that produced
787 rows of credit-spread data earlier in this project.
"""
from __future__ import annotations
import sys, os, json, time, urllib.parse, urllib.request

BASE = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
OUT  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adaptive", "cot")
PAGE = 50000

# our market -> CFTC market_and_exchange_names prefixes, newest naming first
# Our market -> the FULL contract lineage, newest name first.
#
# Resolved from --names 2026-09-03. CFTC renames rather than backfilling, so
# each market is a chain of names across three rename generations: IMM -> CME
# around 2000-08, a second pass 2003-12, and a large standardisation on
# 2022-02-08. Order matters: on a date collision the FIRST alias listed wins,
# so the most recent naming is authoritative through any transition overlap.
#
# Prefixes are exact and include the exchange, because keyword matching is
# actively dangerous here:
#   'WHEAT'  also matches WHEAT - KANSAS CITY BOARD OF TRADE, which has the
#            identical 1269 weeks over the identical span as the CBOT contract
#   'GOLD'   also matches GOLDMAN-SACHS COMMODITY INDEX
#   'COPPER' also matches MICRO COPPER
MAP: dict[str, list[str]] = {
    "xauusd":    ["GOLD - COMMODITY EXCHANGE INC."],
    "xagusd":    ["SILVER - COMMODITY EXCHANGE INC."],
    "xptusd":    ["PLATINUM - NEW YORK MERCANTILE EXCHANGE"],
    "xcuusd":    ["COPPER- #1 - COMMODITY EXCHANGE INC.",
                  "COPPER-GRADE #1 - COMMODITY EXCHANGE INC.",
                  "COPPER - COMMODITY EXCHANGE INC."],
    "cornusd":   ["CORN - CHICAGO BOARD OF TRADE"],
    # CBOT soft red winter only. NOT Kansas City (HRW) or Minneapolis (spring).
    "wheatusd":  ["WHEAT-SRW - CHICAGO BOARD OF TRADE",
                  "WHEAT - CHICAGO BOARD OF TRADE"],
    # one stem covers all seven exchange renames; excludes No. 12 and No. 14
    "sugarusd":  ["SUGAR NO. 11 - "],
    "spx500usd": ["E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE",
                  "E-MINI S&P 500 STOCK INDEX - CHICAGO MERCANTILE EXCHANGE",
                  "E-MINI S&P 500 STOCK INDEX - INTERNATIONAL MONETARY MARKET"],
    "nas100usd": ["NASDAQ MINI - CHICAGO MERCANTILE EXCHANGE",
                  "NASDAQ-100 STOCK INDEX (MINI) - CHICAGO MERCANTILE EXCHANGE",
                  "NASDAQ-100 STOCK INDEX (MINI) - INTERNATIONAL MONETARY MARKET",
                  "E-MINI NASDAQ 100 STOCK INDEX - INTERNATIONAL MONETARY MARKET"],
    "eurusd":    ["EURO FX - CHICAGO MERCANTILE EXCHANGE",
                  "EURO FX - INTERNATIONAL MONETARY MARKET"],
    "gbpusd":    ["BRITISH POUND - CHICAGO MERCANTILE EXCHANGE",
                  "BRITISH POUND STERLING - CHICAGO MERCANTILE EXCHANGE",
                  "POUND STERLING - CHICAGO MERCANTILE EXCHANGE",
                  "POUND STERLING - INTERNATIONAL MONETARY MARKET",
                  "BRITISH POUND STERLING- NEW - INTERNATIONAL MONETARY MARKET",
                  "BRITISH POUND STERLING - INTERNATIONAL MONETARY MARKET"],
    "audusd":    ["AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
                  "AUSTRALIAN DOLLARS - CHICAGO MERCANTILE EXCHANGE",
                  "AUSTRALIAN DOLLARS - INTERNATIONAL MONETARY MARKET"],
    "usdjpy":    ["JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",
                  "JAPANESE YEN - INTERNATIONAL MONETARY MARKET"],
    "usdcad":    ["CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
                  "CANADIAN DOLLAR - INTERNATIONAL MONETARY MARKET"],
    # Successors found via --renames: the Feb-2022 names share no word with
    # their predecessors, so no keyword search could have reached them.
    # NAT GAS NYME, not NAT GAS ICE LD1 / NAT GAS ICE PEN (ICE, different).
    "natgasusd": ["NAT GAS NYME - NEW YORK MERCANTILE EXCHANGE",
                  "NATURAL GAS - NEW YORK MERCANTILE EXCHANGE"],
    # UST 10Y NOTE, NOT "ULTRA UST 10Y" — the Ultra 10-Year is a separate
    # contract with a different deliverable basket, and it sits immediately
    # adjacent in the rename cohort.
    "usb10yusd": ["UST 10Y NOTE - CHICAGO BOARD OF TRADE",
                  "10-YEAR U.S. TREASURY NOTES - CHICAGO BOARD OF TRADE",
                  "6.5-10 YEAR U.S. TREASURY NOTE - CHICAGO BOARD OF TRADE"],
}

UNRESOLVED: set[str] = set()      # all 16 lineages closed 2026-09-03

# Broad keyword per market, for --names. CFTC renamed a batch of contracts in
# Feb 2022 (BRITISH POUND STERLING -> BRITISH POUND, and others), which
# truncates any hardcoded prefix. --names finds the real lineage.
DISCOVER = {
    "xauusd":"GOLD", "xagusd":"SILVER", "xcuusd":"COPPER", "xptusd":"PLATINUM",
    "cornusd":"CORN", "wheatusd":"WHEAT", "sugarusd":"SUGAR",
    "natgasusd":"NATURAL GAS", "spx500usd":"S&P 500", "nas100usd":"NASDAQ",
    "usb10yusd":"TREASURY NOTE", "eurusd":"EURO FX", "gbpusd":"POUND",
    "audusd":"AUSTRALIAN", "usdjpy":"JAPANESE YEN", "usdcad":"CANADIAN DOLLAR",
}

# CME quotes JPY/USD and CAD/USD; our CFDs are USD/JPY and USD/CAD.
# The consumer of these files must flip the sign for these two.
SIGN_FLIP = {"usdjpy", "usdcad"}

FIELDS = ("report_date_as_yyyy_mm_dd,market_and_exchange_names,"
          "comm_positions_long_all,comm_positions_short_all,open_interest_all")


def get(params: dict) -> list[dict]:
    # NOTE: '%' must NOT be in `safe`. SoQL `like` wildcards are literal '%'
    # characters and have to reach the server as %25; leaving them raw makes
    # the URL invalid and Socrata answers 400. That was the original bug here.
    url = BASE + "?" + urllib.parse.urlencode(params, safe="$,()'*")
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:500]
        raise RuntimeError(
            f"HTTP {e.code} from Socrata\n  url:  {url}\n  body: {body}") from None


def list_names(keyword: str) -> None:
    """Distinct contract names, with how many weeks each one has.

    Tries the aggregated form first; falls back to client-side dedupe if this
    Socrata deployment rejects $group, so a name mismatch never costs two
    round trips to diagnose.
    """
    where = ("true" if not keyword else
             f"upper(market_and_exchange_names) like upper('%{keyword}%')")
    try:
        rows = get({"$select": "market_and_exchange_names, count(*) AS n",
                    "$where": where, "$group": "market_and_exchange_names",
                    "$order": "market_and_exchange_names", "$limit": 5000})
        out = [(r["market_and_exchange_names"], int(float(r["n"]))) for r in rows]
    except RuntimeError as e:
        print(f"  [$group rejected, falling back to raw dedupe]\n  {e}\n")
        rows = get({"$select": "market_and_exchange_names",
                    "$where": where, "$limit": 50000})
        seen = {}
        for r in rows:
            seen[r["market_and_exchange_names"]] = seen.get(r["market_and_exchange_names"], 0) + 1
        out = sorted(seen.items())

    for name, n in sorted(out):
        print(f"  {n:6d} weeks   {name}")
    print(f"{len(out)} distinct names matching {keyword!r}")


def probe() -> None:
    """Check every entry in MAP resolves, without writing anything.

    Run this once before the real fetch. CFTC renames contracts, and a stale
    prefix returns an empty series rather than an error -- the failure mode
    that produced 787 rows of credit-spread data earlier in this project.
    """
    bad = []
    for mkt in sorted(MAP):
        hit = None
        for prefix in MAP[mkt]:
            try:
                r = get({"$select": "market_and_exchange_names, count(*) AS n",
                         "$where": f"starts_with(market_and_exchange_names, '{prefix}')",
                         "$group": "market_and_exchange_names", "$limit": 20})
            except RuntimeError as e:
                print(f"  {mkt:10s} ERROR {e}"); r = []
            if r:
                hit = (prefix, sum(int(float(x["n"])) for x in r), len(r))
                break
        if hit:
            flag = "  *** under 500 weeks" if hit[1] < 500 else ""
            print(f"  {mkt:10s} OK  {hit[1]:5d} weeks over {hit[2]} name variant(s)"
                  f"   <- {hit[0]}{flag}")
        else:
            bad.append(mkt)
            print(f"  {mkt:10s} NO MATCH  tried {MAP[mkt]}")
        time.sleep(0.2)
    print(f"\n{len(MAP)-len(bad)}/{len(MAP)} mapped."
          + (f"  Fix with --list: {' '.join(bad)}" if bad else "  Ready to fetch."))


def _rows_for(prefix: str) -> list[dict]:
    rows, off = [], 0
    while True:
        page = get({"$select": FIELDS,
                    "$where": f"starts_with(market_and_exchange_names, '{prefix}')",
                    "$order": "report_date_as_yyyy_mm_dd",
                    "$limit": PAGE, "$offset": off})
        rows += page
        if len(page) < PAGE:
            return rows
        off += PAGE
        time.sleep(0.3)


def names_for(mkt: str) -> None:
    """Every contract name matching this market's keyword, with its span.

    Existence of a match is not enough -- a renamed contract leaves the old
    name alive with a truncated span, which is exactly how gbpusd came back
    as 238 weeks and four others stopped at 2022-02-01.
    """
    kw = DISCOVER[mkt]
    rows = get({"$select": ("market_and_exchange_names, count(*) AS n, "
                            "min(report_date_as_yyyy_mm_dd) AS a, "
                            "max(report_date_as_yyyy_mm_dd) AS b"),
                "$where": f"upper(market_and_exchange_names) like upper('%{kw}%')",
                "$group": "market_and_exchange_names",
                "$order": "market_and_exchange_names", "$limit": 500})
    print(f"\n{mkt}  (keyword {kw!r}) — {len(rows)} name(s)")
    for r in sorted(rows, key=lambda x: x["a"]):
        print(f"   {int(float(r['n'])):5d}w  {r['a'][:10]} -> {r['b'][:10]}   "
              f"{r['market_and_exchange_names']}")


def fetch(mkt: str) -> str:
    """Union of EVERY alias, not the first one that returns rows.

    The original version broke on the first non-empty match. Because CFTC
    renames contracts rather than backfilling, that silently kept whichever
    era the first alias covered and discarded the rest.
    """
    by_date, matched, dupes = {}, [], 0
    for prefix in MAP[mkt]:                 # MAP order IS priority: newest first
        got = _rows_for(prefix)
        if not got:
            continue
        matched.append((prefix, len(got),
                        got[0]["report_date_as_yyyy_mm_dd"][:10],
                        got[-1]["report_date_as_yyyy_mm_dd"][:10]))
        for r in got:
            d = r["report_date_as_yyyy_mm_dd"][:10]
            if d in by_date:                # an earlier (newer-named) alias won
                dupes += 1
            else:
                by_date[d] = r
    if not by_date:
        return f"{mkt}: NO MATCH for any of {MAP[mkt]} — run --names {mkt}"
    uniq = [by_date[d] for d in sorted(by_date)]

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{mkt}.csv"), "w") as f:
        f.write("report_date,comm_long,comm_short,oi,market_name\n")
        for r in uniq:
            f.write(",".join([
                r["report_date_as_yyyy_mm_dd"][:10],
                r.get("comm_positions_long_all", ""),
                r.get("comm_positions_short_all", ""),
                r.get("open_interest_all", ""),
                '"' + r["market_and_exchange_names"] + '"']) + "\n")

    d0, d1 = uniq[0]["report_date_as_yyyy_mm_dd"][:10], uniq[-1]["report_date_as_yyyy_mm_dd"][:10]
    note = ""
    if len(matched) > 1:
        note = "  [" + " + ".join(f"{n}w" for _, n, _, _ in matched) + "]"
    if dupes:
        note += f"  [{dupes} overlap weeks, newer name kept]"
    if mkt in UNRESOLVED:
        note += "  *** post-2022 successor UNKNOWN — run --renames ***"
    LAST[mkt] = d1
    return f"{mkt}: {len(uniq)} weeks {d0} -> {d1}{note}"


LAST: dict[str, str] = {}


def renames(date: str = "2022-02-08") -> None:
    """Every contract whose FIRST report is `date` — i.e. the rename cohort.

    A renamed contract is invisible to a keyword search when the new name
    shares no word with the old one. But every member of a rename cohort
    starts on the same day, so asking that question directly enumerates all
    of them at once.
    """
    rows = get({"$select": ("market_and_exchange_names, count(*) AS n, "
                            "min(report_date_as_yyyy_mm_dd) AS a, "
                            "max(report_date_as_yyyy_mm_dd) AS b"),
                "$group": "market_and_exchange_names",
                "$having": f"min(report_date_as_yyyy_mm_dd) = '{date}'",
                "$order": "market_and_exchange_names", "$limit": 2000})
    print(f"contracts whose history begins exactly {date}: {len(rows)}\n")
    for r in sorted(rows, key=lambda x: x["market_and_exchange_names"]):
        print(f"   {int(float(r['n'])):5d}w  -> {r['b'][:10]}   "
              f"{r['market_and_exchange_names']}")
    print(f"\nlooking for the successors to:")
    for m in sorted(UNRESOLVED):
        print(f"   {m:10s} {MAP[m][0]}")


def coverage_report() -> None:
    """Flag any series that stops early relative to the rest of the run.

    A stale contract name does not error, it just stops. Comparing each
    series' last date against the newest in the run catches that; a bare
    row-count threshold does not, because a truncated series can still be
    long -- four of the five stale series in the first run had over 1,000
    weeks and sailed past a 500-week check.
    """
    if not LAST:
        return
    newest = max(LAST.values())
    ny, nm = int(newest[:4]), int(newest[5:7])
    stale = {m: d for m, d in LAST.items()
             if (ny - int(d[:4])) * 12 + (nm - int(d[5:7])) > 2}
    print(f"\nnewest report date in this run: {newest}")
    if stale:
        print(f"STALE ({len(stale)}) — these stop >2 months early and almost")
        print("certainly have a newer contract name:")
        for m, d in sorted(stale.items(), key=lambda kv: kv[1]):
            print(f"   {m:10s} ends {d}     diagnose with:  --names {m}")
    else:
        print("all series reach the newest date — no rename gaps.")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--list":
        list_names(a[1] if len(a) > 1 else "")
        sys.exit(0)
    if a and a[0] == "--probe":
        probe()
        sys.exit(0)
    if a and a[0] == "--renames":
        renames(a[1] if len(a) > 1 else "2022-02-08")
        sys.exit(0)
    if a and a[0] == "--names":
        for m in (a[1:] or sorted(DISCOVER)):
            try:
                names_for(m)
            except Exception as e:
                print(f"{m}: FAILED {e}")
            time.sleep(0.2)
        sys.exit(0)
    todo = a or sorted(MAP)
    for m in todo:
        if m not in MAP:
            print(f"{m}: not in MAP"); continue
        try:
            print(fetch(m), flush=True)
        except Exception as e:
            print(f"{m}: FAILED {type(e).__name__}: {e}", flush=True)
    coverage_report()
