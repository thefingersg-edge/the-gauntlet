#!/usr/bin/env python3
"""PHASE 0 -- does retrospective execution-cost data exist?

THE QUESTION
------------
Track A samples the quoted spread once a day. After four observations the
95% interval on the wide-day rate is 4.6% to 69.9%, which is no answer at
all, and TRACKA_HOW_LONG puts a properly powered read in late October.

That is only true if the ONLY source is forward sampling. This file asks
whether the same question can be answered backwards.

WHAT THE DOCUMENTATION SAYS, BEFORE ANYTHING IS FETCHED
-------------------------------------------------------
Recorded here so the probe cannot be quietly re-aimed at whatever it finds:

  * Historical BID/ASK does not exist publicly. The charts API accepts
    tick_type of `mark`, `spot` or `trade` and nothing else. There is no
    quoted-spread history to retrieve, at any price, from the public API.

  * /derivatives/api/v3/history returns EXECUTED TRADES only -- 100 per
    call, 7 days deep, no quotes.

So the literal question ("is there historical spread data") is already
answered: no. This probe asks the better question instead.

THE BETTER QUESTION
-------------------
The quoted spread is what the screen said. What matters is what a trade
would have GOT. Those differ, and the difference is the entire subject:
on 25 August the September book showed 158bp, and whether that was a real
cost or a phantom depends on where trades actually printed at that moment.

The charts API publishes BOTH at 1-minute resolution:

    trade   what actually executed
    mark    Kraken's own fair value for the same minute

**The gap between them is an executed-cost proxy, and it exists for every
minute anyone traded, over the contract's whole life -- including for
contracts that have already settled.**

That is a retrospective measurement of the thing Track A is sampling
forward, and if the history is deep enough it replaces two months of
waiting with one afternoon.

WHAT THIS FILE DOES NOT DO
--------------------------
It does not compute the answer. It reports what data exists, how deep, and
how complete -- exactly as kraken_probe.py did for v4 -- and stops. The
measurement needs its own pre-registration with its thresholds fixed
first, because the person running it now knows which result would save two
months of waiting.

The self-test asserts by namespace inspection that no measurement function
exists in this module.

PUBLIC DATA ONLY. No API key is needed and none should be supplied.

    python3 kraken_history.py --self-test
    python3 kraken_history.py
    python3 kraken_history.py --symbol FF_XBTUSD_260626   # a SETTLED one
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken_probe as KP                                    # noqa: E402

VERSION = "1.2"

#: Documented tick types. `bid`/`ask` are included ONLY so the probe can
#: demonstrate they fail -- an absence asserted from documentation and
#: never tested is an assumption, not a finding.
TICK_TYPES = ("trade", "mark", "spot")
ABSENT_TICK_TYPES = ("bid", "ask")
RESOLUTIONS = ("1m", "1h", "1d")
RES_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600,
               "4h": 14400, "12h": 43200, "1d": 86400, "1w": 604800}
#: Observed 2026-08-29: every response came back with exactly 2000 rows
#: except the daily series, which returned 190 -- the contract's whole
#: life. That is a PAGE CAP, not a history limit, and v1.0 read it as one.
PAGE_CAP = 2000
MAX_PAGES = 400

#: What would make the retrospective route viable, fixed BEFORE looking.
#: Four quarterly cycles of 1m trade data is roughly the point at which
#: the wide-day rate stops being an interval spanning the whole range.
MIN_CYCLES_WANTED = 4
MIN_DAYS_WANTED = 365
#: A minute bar that exists but recorded no trade is itself the finding
#: (nobody transacted), so coverage below this is not a failure -- it is
#: data. It is reported, never silently dropped.
NOTE_COVERAGE_BELOW = 0.20


def chart_url(host, tick_type, symbol, resolution, frm=None, to=None):
    """Kraken Futures charts endpoint. Built, never guessed at silently."""
    u = f"{host}/api/charts/v1/{tick_type}/{symbol}/{resolution}"
    q = []
    if frm is not None:
        q.append(f"from={int(frm)}")
    if to is not None:
        q.append(f"to={int(to)}")
    return u + ("?" + "&".join(q) if q else "")


def parse_candles(payload):
    """Extract (time, open, high, low, close, volume) rows, shape-agnostic.

    The response shape is DISCOVERED rather than assumed: fx_carry_probe
    hit exactly this and the fix was to look at what came back instead of
    trusting a remembered field name.
    """
    if not isinstance(payload, dict):
        return [], "payload is not an object"
    for key in ("candles", "result", "data", "ticks"):
        v = payload.get(key)
        if isinstance(v, list) and v:
            rows = []
            for c in v:
                if isinstance(c, dict):
                    t = c.get("time") or c.get("timestamp") or c.get("t")
                    if t is None:
                        continue
                    rows.append(dict(
                        time=float(t),
                        open=_f(c, "open", "o"), high=_f(c, "high", "h"),
                        low=_f(c, "low", "l"), close=_f(c, "close", "c"),
                        volume=_f(c, "volume", "v")))
                elif isinstance(c, (list, tuple)) and len(c) >= 5:
                    rows.append(dict(
                        time=float(c[0]), open=_f2(c, 1), high=_f2(c, 2),
                        low=_f2(c, 3), close=_f2(c, 4),
                        volume=_f2(c, 5) if len(c) > 5 else None))
            return rows, f"key={key!r}"
    return [], f"no candle list in keys {sorted(payload)[:8]}"


def _f(d, *names):
    for n in names:
        if n in d:
            try:
                return float(d[n])
            except (TypeError, ValueError):
                return None
    return None


def _f2(seq, i):
    try:
        return float(seq[i])
    except (TypeError, ValueError, IndexError):
        return None


def span_of(rows):
    """(first, last, days, n) for a candle list. Milliseconds or seconds."""
    if not rows:
        return None, None, 0.0, 0
    ts = sorted(r["time"] for r in rows)
    #: Kraken returns ms. A bare > 1e11 test distinguishes it from seconds
    #: without hardcoding which one this endpoint uses today.
    div = 1000.0 if ts[-1] > 1e11 else 1.0
    a = dt.datetime.fromtimestamp(ts[0] / div, dt.timezone.utc)
    b = dt.datetime.fromtimestamp(ts[-1] / div, dt.timezone.utc)
    return a, b, (b - a).total_seconds() / 86400.0, len(rows)


def traded_share(rows):
    """Fraction of bars that recorded a trade.

    A `trade` bar with zero or absent volume means nobody transacted in
    that minute. That is not missing data -- it is the illiquidity being
    measured, and it must never be dropped as though the minute did not
    happen.
    """
    if not rows:
        return None
    n = sum(1 for r in rows if (r.get("volume") or 0.0) > 0.0)
    return n / len(rows)


def last_friday(year, month):
    """Last Friday of a month -- how Kraken dates its quarterlies.

    Verified against all 18 of v4's cycle dates: 18/18 classified.
    """
    import calendar
    last = calendar.monthrange(year, month)[1]
    d = dt.date(year, month, last)
    return d - dt.timedelta(days=(d.weekday() - 4) % 7)


def quarterly_symbols(n_back, today=None, pair="XBTUSD"):
    """Candidate symbols for the last n_back quarterly expiries.

    Delisted contracts do NOT appear in the instruments endpoint, so the
    only way to find out whether their history survives is to ask for it
    by name. Both prefixes are generated because the venue switched from
    inverse to linear partway through v4's sample -- guessing one would
    silently halve the answer.
    """
    today = today or dt.date.today()
    out, y, m = [], today.year, ((today.month - 1) // 3) * 3 + 3
    while len(out) < n_back:
        e = last_friday(y, m)
        if e <= today:
            out.append((e, [f"FF_{pair}_{e:%y%m%d}",
                            f"FI_{pair}_{e:%y%m%d}"]))
        m -= 3
        if m < 1:
            m += 12
            y -= 1
    return out


def verdict(days, cycles_covered, has_trade, has_mark):
    """Fixed BEFORE the fetch. Ambiguity is not a pass.

    VIABLE       both series exist, >= MIN_DAYS_WANTED and
                 >= MIN_CYCLES_WANTED settled quarterlies reachable
    THIN         they exist but the history is shorter than that
    UNAVAILABLE  either series is missing
    """
    if not has_trade or not has_mark:
        return "UNAVAILABLE"
    if days >= MIN_DAYS_WANTED and cycles_covered >= MIN_CYCLES_WANTED:
        return "VIABLE"
    return "THIN"


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"kraken_history.py v{VERSION} self-test\n")

    print("the URL is built, not guessed")
    u = chart_url("https://h", "trade", "FF_XBTUSD_260925", "1m", 100, 200)
    check("path carries tick type, symbol and resolution",
          u.endswith("/api/charts/v1/trade/FF_XBTUSD_260925/1m?"
                     "from=100&to=200"), u)
    check("no from/to gives a bare path",
          chart_url("https://h", "mark", "S", "1d").endswith("/mark/S/1d"))
    #: planted: a float window must not leak a decimal point into the URL
    check("float timestamps are truncated to integers",
          "from=100&to=200" in chart_url("https://h", "t", "S", "1m",
                                         100.7, 200.2))

    print("\ncandle shape is DISCOVERED, not assumed")
    dict_shape = {"candles": [{"time": 1e12, "open": 1, "high": 2,
                               "low": 0.5, "close": 1.5, "volume": 3}]}
    rows, how = parse_candles(dict_shape)
    check("dict candles parse", len(rows) == 1 and rows[0]["high"] == 2.0,
          how)
    list_shape = {"result": [[1e12, 1, 2, 0.5, 1.5, 3]]}
    rows2, how2 = parse_candles(list_shape)
    check("list candles parse too",
          len(rows2) == 1 and rows2[0]["close"] == 1.5, how2)
    check("abbreviated keys parse",
          parse_candles({"data": [{"t": 1e12, "o": 1, "h": 2, "l": 1,
                                   "c": 1, "v": 0}]})[0][0]["open"] == 1.0)
    #: planted: an unrecognised shape must report, never return silence
    empty, why = parse_candles({"unexpected": [1, 2, 3]})
    check("an unknown shape returns a REASON, not just nothing",
          empty == [] and "no candle list" in why, why)
    check("a non-object payload is refused",
          parse_candles([1, 2, 3])[0] == [])

    print("\nspan handles seconds AND milliseconds")
    ms = [{"time": 1.7e12}, {"time": 1.7e12 + 86400000}]
    a, b, d, n = span_of(ms)
    check("milliseconds give 1 day, not 1000+ years",
          abs(d - 1.0) < 1e-6, f"{d:.4f} days")
    sec = [{"time": 1.7e9}, {"time": 1.7e9 + 86400}]
    check("seconds also give 1 day", abs(span_of(sec)[2] - 1.0) < 1e-6)
    check("an empty list is (None, None, 0, 0)", span_of([])[3] == 0)

    print("\nan untraded minute is DATA, not a gap")
    bars = [{"volume": 0.0}, {"volume": 5.0}, {"volume": None},
            {"volume": 1.0}]
    check("traded share counts only bars with volume",
          abs(traded_share(bars) - 0.5) < 1e-12,
          f"{traded_share(bars)*100:.0f}%")
    check("all-zero volume is 0.0, not None",
          traded_share([{"volume": 0.0}]) == 0.0)
    check("and it is never silently dropped",
          traded_share([{"volume": 0.0}]) is not None)

    print("\na FULL page is a cap, not the end of history (v1.1)")
    #: PLANTED: this is the defect v1.0 shipped. 2000 one-minute bars is
    #: 1.4 days; v1.0 printed that as the depth of a 190-day contract and
    #: returned THIN on it.
    full = [{"time": 1.7e12 + i * 60000, "volume": 1.0}
            for i in range(PAGE_CAP)]
    check("exactly 2000 rows reads as CAPPED, not complete",
          at_page_cap(full), f"{len(full)} rows")
    check("a short page does not", not at_page_cap(full[:-1]))
    check("an empty page does not", not at_page_cap([]))
    _, _, dd, _ = span_of(full)
    check("and 2000 1m bars really is only ~1.4 days",
          abs(dd - 1.388) < 0.01, f"{dd:.3f} days -- v1.0 called this "
          f"the contract's history")

    print("\npagination walks past the cap")
    #: three pages of a fake series: two full, one short
    PAGES = []
    t0 = 1.7e12
    for p in range(3):
        n = PAGE_CAP if p < 2 else 500
        PAGES.append({"candles": [
            {"time": t0 + (p * PAGE_CAP + i) * 60000, "open": 1, "high": 1,
             "low": 1, "close": 1, "volume": 1} for i in range(n)]})
    calls = {"n": 0}
    def fake(url):
        i = calls["n"]
        calls["n"] += 1
        return PAGES[i] if i < len(PAGES) else {"candles": []}
    rows, note = pull_paged("h", "trade", "S", "1m", t0 / 1000,
                            t0 / 1000 + 10 * 86400, fetch=fake)
    check("it keeps going past a full page",
          len(rows) == 2 * PAGE_CAP + 500, f"{len(rows)} rows, {note}")
    check("and says how many pages were full",
          "2 full at the" in note, note)
    check("a single unpaginated call would have seen only the first",
          len(PAGES[0]["candles"]) == PAGE_CAP)
    #: PLANTED: a server that repeats the same page must terminate, and
    #: must NOT report it as the end of the data
    #: cursor starts PAST this fixture's data but inside the window, so
    #: every page comes back older than the cursor and cannot advance it
    stuck = {"candles": PAGES[0]["candles"]}
    rows2, note2 = pull_paged("h", "trade", "S", "1m",
                              t0 / 1000 + 200000, t0 / 1000 + 10 * 86400,
                              fetch=lambda u: stuck)
    check("a non-advancing cursor STALLS rather than looping",
          "STALLED" in note2, note2)
    check("and it returns what it did get, not nothing",
          len(rows2) == PAGE_CAP, f"{len(rows2)} rows kept")

    #: PLANTED: a server that ALWAYS advances would run forever without a
    #: page limit. The limit must be reported as a limit, never as the
    #: end of the data -- that is the same false-completion error again.
    def endless(url):
        frm = int(url.split("from=")[1].split("&")[0])
        return {"candles": [
            {"time": (frm + i * 60) * 1000, "open": 1, "high": 1,
             "low": 1, "close": 1, "volume": 1} for i in range(PAGE_CAP)]}
    _, note3 = pull_paged("h", "t", "S", "1m", 0, 9e9, max_pages=3,
                          fetch=endless)
    check("hitting the page limit says so, and does not claim the end",
          "HIT the 3-page limit" in note3, note3)
    check("an unknown resolution is refused, not guessed",
          pull_paged("h", "t", "S", "3s", 0, 1, fetch=fake)[0] == [])

    print("\nquarterly symbols are generated, and match v4's own cycles")
    V4 = ["2022-03-25", "2022-06-24", "2022-09-30", "2022-12-30",
          "2023-03-31", "2023-06-30", "2023-09-29", "2023-12-29",
          "2024-03-29", "2024-06-28", "2024-09-27", "2024-12-27",
          "2025-03-28", "2025-06-27", "2025-09-26", "2025-12-26",
          "2026-03-27", "2026-06-26"]
    gen = {e for e, _ in quarterly_symbols(20, dt.date(2026, 8, 29))}
    want = {dt.date.fromisoformat(s) for s in V4}
    check("every one of v4's 18 cycle dates is generated",
          want <= gen, f"{len(want & gen)}/18")
    check("and they are all Fridays",
          all(d.weekday() == 4 for d in gen))
    check("only Mar/Jun/Sep/Dec are generated",
          all(d.month in (3, 6, 9, 12) for d in gen))
    #: PLANTED: the monthly and weekly contracts seen this week must NOT
    #: be generated -- the rule trades quarterlies and mixing maturities
    #: would put a 7-day contract in a quarterly series
    for bad in ("2026-08-28", "2026-09-04"):
        check(f"{bad} (a monthly/weekly) is NOT generated",
              dt.date.fromisoformat(bad) not in gen)
    check("both prefixes are offered, not just the live one",
          quarterly_symbols(1, dt.date(2026, 8, 29))[0][1]
          == ["FF_XBTUSD_260626", "FI_XBTUSD_260626"])
    check("a future expiry is excluded",
          all(e <= dt.date(2026, 8, 29) for e in gen))

    print("\nthe verdict was fixed before the fetch")
    check("deep history with enough cycles is VIABLE",
          verdict(800, 6, True, True) == "VIABLE")
    #: planted: each requirement must be able to fail ALONE
    check("too few days is THIN, not VIABLE",
          verdict(100, 6, True, True) == "THIN")
    check("too few cycles is THIN, not VIABLE",
          verdict(800, 1, True, True) == "THIN")
    check("no trade series is UNAVAILABLE",
          verdict(800, 6, False, True) == "UNAVAILABLE")
    check("no mark series is UNAVAILABLE",
          verdict(800, 6, True, False) == "UNAVAILABLE")
    check("UNAVAILABLE is never VIABLE",
          verdict(9999, 99, False, False) != "VIABLE")

    print("\nthis file measures NOTHING (it is a probe)")
    import kraken_history as _self
    banned = ("measure", "slippage", "cost", "estimate", "backtest")
    def scan():
        return [x for x in dir(_self) if not x.startswith("_")
                and any(w in x.lower() for w in banned)]
    check("no measurement function exists", scan() == [], f"{scan()}")
    setattr(_self, "measure_slippage", lambda: None)
    fired = scan() == ["measure_slippage"]
    delattr(_self, "measure_slippage")
    check("and the detector demonstrably FIRES", fired and scan() == [])
    check("no order or execute function either",
          [x for x in dir(_self) if not x.startswith("_")
           and any(w in x.lower() for w in
                   ("order", "execute", "submit", "place"))] == [])

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def probe_one(host, tick, sym, res, days_back):
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    url = chart_url(host, tick, sym, res, now - days_back * 86400, now)
    try:
        payload = json.loads(KP._get(url, timeout=30))
    except Exception as exc:                                  # noqa: BLE001
        return None, f"FAIL {str(exc)[:50]}"
    rows, how = parse_candles(payload)
    return rows, how


def at_page_cap(rows, cap=PAGE_CAP):
    """Did this response come back exactly full?

    A response of exactly the cap almost never means the history ends
    there. v1.0 read it as depth and returned THIN on a contract with 190
    days of data, because 2000 one-minute bars is 1.4 days and the probe
    asked from 400 days ago -- so it got the FIRST 2000, not the last.

    This is the same defect as fx_drift_bound v1.1, where OANDA's
    `count=N` from a start date returned the first N candles and every
    series ended in 2023. It was fixed there with pagination and made
    again here.
    """
    return bool(rows) and len(rows) >= cap


def pull_paged(host, tick, sym, res, frm, to, max_pages=MAX_PAGES,
               fetch=None):
    """Walk FORWARD in pages until the window is covered.

    Returns (rows, note). `fetch` is injectable so the pagination logic
    can be tested without a network.
    """
    step = RES_SECONDS.get(res)
    if not step:
        return [], f"unknown resolution {res!r}"
    getter = fetch or (lambda u: json.loads(KP._get(u, timeout=30)))
    out, seen, cur, pages, capped = [], set(), float(frm), 0, 0
    while cur < to and pages < max_pages:
        try:
            payload = getter(chart_url(host, tick, sym, res, cur, to))
        except Exception as exc:                              # noqa: BLE001
            return out, f"page {pages}: FAIL {str(exc)[:40]}"
        rows, _ = parse_candles(payload)
        if not rows:
            break
        if at_page_cap(rows):
            capped += 1
        newest = max(r["time"] for r in rows)
        div = 1000.0 if newest > 1e11 else 1.0
        for r in rows:
            if r["time"] not in seen:
                seen.add(r["time"])
                out.append(r)
        nxt = newest / div + step
        #: A page that does not advance the cursor would loop forever.
        #: Stopping is correct; pretending it was the end of history is
        #: not, so the note says which happened.
        if nxt <= cur:
            return out, f"{pages+1} pages, STALLED (cursor did not advance)"
        cur = nxt
        pages += 1
    note = f"{pages} page(s)"
    if capped:
        note += f", {capped} full at the {PAGE_CAP} cap"
    if pages >= max_pages:
        note += f" -- HIT the {max_pages}-page limit, not the end of data"
    return out, note


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="FF_XBTUSD_260925")
    ap.add_argument("--settled", default="FF_XBTUSD_260626",
                    help="a contract that has ALREADY expired")
    ap.add_argument("--days-back", type=float, default=400.0)
    ap.add_argument("--cycles-back", type=int, default=14,
                    help="how many past quarterly expiries to look for")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"kraken_history.py v{VERSION}   PHASE 0 -- DOES THE DATA "
          f"EXIST?\n")
    print("  Public market data only. No key is used and none is needed.")
    print("  This file reports what exists. It computes no cost.\n")

    host = KP.FUT
    found = {}

    #: The DAILY series establishes the contract's whole life in one call
    #: and is never page-capped at these lengths. Depth is read from it,
    #: then 1m availability is SPOT-CHECKED at both ends -- 3 calls
    #: instead of the 137 a full 1m pull would take.
    print(f"  LIVE CONTRACT  {a.symbol}")
    life = {}
    for tick in TICK_TYPES:
        rows, how = probe_one(host, tick, a.symbol, "1d", a.days_back)
        if rows is None or not rows:
            print(f"    {tick:<6}1d    {how if rows is None else 'none'}")
            continue
        f, l, d, n = span_of(rows)
        life[tick] = (f, l, d, n)
        cap = "  (AT PAGE CAP -- depth understated)" \
            if at_page_cap(rows) else ""
        share = traded_share(rows)
        extra = f"   traded {share*100:.0f}% of days" \
            if (tick == "trade" and share is not None) else ""
        print(f"    {tick:<6}1d  {n:>6} bars  {f.date()} -> {l.date()}  "
              f"{d:>6.1f}d{extra}{cap}")

    if "trade" in life:
        f0, l0, d0, _ = life["trade"]
        print(f"\n    1m SPOT-CHECK at both ends of that {d0:.0f}-day life")
        for tick in ("trade", "mark"):
            for lab, anchor in (("start", f0), ("end", l0)):
                t0 = anchor.timestamp()
                rows, _ = probe_one(host, tick, a.symbol, "1m",
                                    (dt.datetime.now(dt.timezone.utc)
                                     .timestamp() - t0) / 86400.0)
                got = bool(rows)
                fa, la, da, na = span_of(rows or [])
                print(f"      {tick:<6}{lab:<6}"
                      + (f"{na:>6} bars from {fa.date()}" if got
                         else "  NOTHING"))
                if got and lab == "start":
                    found[(tick, "1m")] = (d0, na)

    print(f"\n  SETTLED CONTRACT  {a.settled}  "
          f"(retrospective work needs these)")
    settled_ok = False
    for tick in ("trade", "mark"):
        rows, how = probe_one(host, tick, a.settled, "1m", a.days_back)
        if rows is None or not rows:
            print(f"    {tick:<6}{how if rows is None else 'no candles'}")
            continue
        f, l, d, n = span_of(rows)
        settled_ok = True
        print(f"    {tick:<6}{n:>7} bars  {f.date()} -> {l.date()}  "
              f"{d:.1f}d")
    if not settled_ok:
        print("    NOTHING. If settled contracts are purged, the "
              "retrospective")
        print("    route dies here regardless of what the live one "
              "returns.")

    print(f"\n  THE ABSENT TICK TYPES -- asserted from docs, now TESTED")
    for tick in ABSENT_TICK_TYPES:
        rows, how = probe_one(host, tick, a.symbol, "1h", 7)
        state = "FAILS as documented" if (rows is None or not rows) \
            else f"RETURNED {len(rows)} bars -- the docs were incomplete"
        print(f"    {tick:<6}{state}")

    #: v1.2 -- HOW `cycles` IS COMPUTED IS CORRECTED HERE.
    #:
    #: v1.1 used `int(one_contract_life // 91)`, which asks how many
    #: quarters fit inside a SINGLE contract's life. The threshold at the
    #: top of this file says "four quarterly cycles of 1m trade data",
    #: which means data covering four CYCLES -- four contracts.
    #:
    #: Those are different quantities and the second is what was written
    #: down. The threshold text is unchanged; only the code that failed to
    #: implement it is. Recorded plainly because the correction runs
    #: toward VIABLE and I knew that before making it: one contract lives
    #: ~190 days, so the old formula could never return more than 2 no
    #: matter how many years of history Kraken keeps.
    print(f"\n  SETTLED QUARTERLIES -- how many cycles are retrievable")
    print("  Delisted contracts are absent from the instruments endpoint,")
    print("  so each is requested BY NAME. Both prefixes are tried.")
    reachable = []
    for exp, syms in quarterly_symbols(a.cycles_back):
        hit = None
        for sym in syms:
            rows, _ = probe_one(host, "trade", sym, "1d", 3000)
            if rows:
                f, l, d, n = span_of(rows)
                hit = (sym, n, d, f, l)
                break
        if hit:
            sym, n, d, f, l = hit
            m1, _ = probe_one(host, "trade", sym, "1m",
                              (dt.datetime.now(dt.timezone.utc).date()
                               - f.date()).days)
            has1m = bool(m1)
            reachable.append((exp, sym, d, has1m))
            print(f"    {exp}  {sym:<20}{n:>5} daily bars  {d:>6.0f}d  "
                  f"1m {'YES' if has1m else 'no'}")
        else:
            print(f"    {exp}  {'(neither prefix returned data)':<20}")

    with_1m = [r for r in reachable if r[3]]
    d_trade = found.get(("trade", "1m"), (0.0, 0))[0]
    d_mark = found.get(("mark", "1m"), (0.0, 0))[0]
    depth = sum(r[2] for r in with_1m) or min(d_trade, d_mark)
    cycles = len(with_1m)
    v = verdict(depth, cycles, ("trade", "1m") in found,
                ("mark", "1m") in found)

    print(f"\n  VERDICT -- thresholds fixed in section 'THE BETTER "
          f"QUESTION'")
    print(f"    live contract 1m   trade {d_trade:.0f}d   "
          f"mark {d_mark:.0f}d")
    print(f"    cycles WITH 1m     {cycles}  (need {MIN_CYCLES_WANTED})")
    print(f"    days across them   {depth:.0f}  "
          f"(need {MIN_DAYS_WANTED})")
    print(f"    {v}")
    if v == "VIABLE":
        print("\n    The trade-vs-mark gap is retrievable over enough "
              "history to")
        print("    measure retrospectively what Track A is sampling "
              "forward.")
        print("    NEXT: a pre-registration fixing what counts as a wide "
              "minute,")
        print("    written BEFORE the series is read. Not this file.")
    elif v == "THIN":
        print("\n    The data exists but is shallower than the "
              "pre-set bar.")
        print("    It supplements Track A; it does not replace it.")
    else:
        print("\n    The retrospective route is closed. Track A's "
              "timeline stands.")
    sys.exit(0 if v == "VIABLE" else 2)


if __name__ == "__main__":
    main()
