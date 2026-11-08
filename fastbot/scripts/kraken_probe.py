#!/usr/bin/env python3
"""PHASE 0 for PREREGISTRATION_v4 -- what dated-futures history actually exists?

WHY THIS EXISTS
---------------
PREREGISTRATION_v4.md commits to measuring the Kraken dated BTC futures
basis, and makes that measurement conditional on a data probe that must pass
BEFORE anything is computed:

    retrievable dated-contract history   >= 3 years
    distinct quarterly cycles observed   >= 12
    window contains calendar 2022        REQUIRED
    matching spot series                 REQUIRED

This file is that probe and NOTHING ELSE. It computes no basis, no premium,
no return. It answers one question -- is the measurement possible? -- and
writes a manifest for the phase that may follow.

That separation is deliberate. If the probe could also measure, the
temptation on a marginal result would be to look at the answer before
deciding whether the data qualified, which is the whole failure the
pre-registration exists to prevent. The self-test asserts, by inspecting
this module's namespace, that no measurement function exists here.

WHY IT RUNS LOCALLY
-------------------
Kraken is not reachable from the research sandbox. This runs on your machine
like pull_m1.py did. It uses PUBLIC market data only -- no API key is
needed and none should be supplied.

ENDPOINTS ARE DISCOVERED, NOT ASSUMED
-------------------------------------
I could not verify Kraken's API surface from documentation before writing
this, so it tries a list of candidates and REPORTS which respond. An
endpoint that works is a finding; one that does not is also a finding. The
probe never silently falls back to a source it did not announce.

    python kraken_probe.py --self-test
    python kraken_probe.py
    python kraken_probe.py --out ../data/kraken_manifest.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

VERSION = "1.2"

#: PREREGISTRATION_v4 section 4, frozen. MIN_2022_CYCLES is an
#: operationalisation of the pre-registration's looser phrase "window
#: contains calendar 2022"; it is written down here, before any data has
#: been retrieved, so that the tightening cannot be chosen to fit a result.
MIN_YEARS = 3.0
MIN_CYCLES = 12
MIN_2022_CYCLES = 2
REQUIRE_SPOT = True

FUT = "https://futures.kraken.com"
SPOT = "https://api.kraken.com"

#: Candidates, in the order they will be tried. Every one that responds is
#: reported; the probe does not stop at the first success for the history
#: endpoints, because knowing which tick types exist matters later.
INSTRUMENT_URLS = [
    f"{FUT}/derivatives/api/v3/instruments",
    f"{FUT}/derivatives/api/v3/tickers",
]
CHART_TEMPLATES = [
    FUT + "/api/charts/v1/{tick}/{symbol}/{res}?from={frm}&to={to}",
]
TICK_TYPES = ["trade", "mark", "spot"]
SPOT_URLS = [
    SPOT + "/0/public/OHLC?pair=XXBTZUSD&interval=1440",
    SPOT + "/0/public/OHLC?pair=XBTUSD&interval=1440",
]

#: FF_XBTUSD_260626 / FI_XBTUSD_211231 style. Two letters, underscore,
#: pair, underscore, YYMMDD.
DATED = re.compile(r"^(F[A-Z])_([A-Z]{6})_(\d{6})$")


def _get(url, timeout=30, tries=3, pause=0.6):
    """Fetch bytes, or raise with the URL attached so failures are legible."""
    import urllib.error
    import urllib.request
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:                              # noqa: BLE001
            last = exc
            time.sleep(pause * (k + 1))
    raise RuntimeError(f"{type(last).__name__}: {last}  <- {url}")


def symbol_expiry(symbol):
    """Expiry encoded in a dated Kraken futures symbol, or None.

    Returns a date. YY is read as 2000+YY: Kraken listed no dated crypto
    futures before 2010 and this file will be long dead before 2099.
    """
    import datetime as dt
    m = DATED.match(symbol.upper())
    if not m:
        return None
    yy, mm, dd = int(m.group(3)[:2]), int(m.group(3)[2:4]), int(m.group(3)[4:])
    try:
        return dt.date(2000 + yy, mm, dd)
    except ValueError:
        return None


def expiry_agrees(symbol, reported_ms, tol_days=2):
    """Does the symbol's encoded expiry match what the exchange reports?

    PREREGISTRATION_v4 section 11.6 requires that a mismatched expiry be
    caught rather than silently annualised. Time to expiry is the
    denominator of every basis figure: a contract whose true maturity is 90
    days, annualised as though it were 30, reports three times the premium
    it earned. This is the cheapest place to catch that, and the check runs
    on every instrument before any of them is written to the manifest.

    tol_days allows for timezone and settlement-hour differences only.
    """
    import datetime as dt
    enc = symbol_expiry(symbol)
    if enc is None or reported_ms in (None, 0):
        return None                       # nothing to compare, not a pass
    rep = dt.datetime.utcfromtimestamp(float(reported_ms) / 1000.0).date()
    return abs((rep - enc).days) <= tol_days


def parse_instruments(payload, pair_filter="XBTUSD"):
    """Dated contracts for one pair, from an instruments payload.

    Returns (rows, mismatches). A row carries the symbol, the encoded
    expiry and whether the exchange agreed with it.
    """
    rows, bad = [], []
    items = payload.get("instruments") or payload.get("tickers") or []
    for it in items:
        sym = (it.get("symbol") or "").upper()
        m = DATED.match(sym)
        if not m or m.group(2) != pair_filter.upper():
            continue
        rep = (it.get("lastTradingTime") or it.get("expiryTime")
               or it.get("lastTradeTime"))
        if isinstance(rep, str):
            rep = _iso_ms(rep)
        ok = expiry_agrees(sym, rep)
        row = dict(symbol=sym, kind=m.group(1),
                   expiry=str(symbol_expiry(sym)), agrees=ok,
                   tradeable=bool(it.get("tradeable", True)))
        rows.append(row)
        if ok is False:
            bad.append(row)
    return sorted(rows, key=lambda r: r["expiry"]), bad


def _iso_ms(s):
    import datetime as dt
    try:
        return dt.datetime.fromisoformat(
            s.replace("Z", "+00:00")).timestamp() * 1000.0
    except Exception:                                         # noqa: BLE001
        return None


def cycles_by_year(rows):
    """How many dated cycles fall in each calendar year."""
    out = {}
    for r in rows:
        y = int(r["expiry"][:4])
        out[y] = out.get(y, 0) + 1
    return dict(sorted(out.items()))


def spot_covers(spot_first, spot_last, fut_first, fut_last, tol_days=35):
    """Does the spot series actually span the futures window?

    v1.0 asked only whether A spot series existed. That is not the
    condition PREREGISTRATION_v4 section 4 states, which is a "matching
    spot series over the same window", and the difference is not academic:
    the first live run returned Kraken spot OHLC covering 2024-08 to
    2026-08 against futures history reaching back to 2020-05, and Phase 0
    reported PROCEED. Two years of spot cannot price a 2022 contract. The
    gate passed because it could not fail in the way it was written to.

    Returns (ok, detail).
    """
    import datetime as dt
    if not (spot_first and spot_last and fut_first and fut_last):
        return False, "missing"
    f = dt.date.fromisoformat(str(spot_first))
    l = dt.date.fromisoformat(str(spot_last))
    a = dt.date.fromisoformat(str(fut_first))
    b = dt.date.fromisoformat(str(fut_last))
    lead = (f - a).days
    lag = (b - l).days
    ok = lead <= tol_days and lag <= tol_days
    if ok:
        return True, f"{f} -> {l} covers {a} -> {b}"
    miss = []
    if lead > tol_days:
        miss.append(f"starts {lead} days late")
    if lag > tol_days:
        miss.append(f"ends {lag} days early")
    return False, f"{f} -> {l} vs futures {a} -> {b}: " + ", ".join(miss)


def usable_contracts(hist, tol_days=3):
    """Contracts where BOTH legs exist over the contract's own life.

    A basis needs a future and a spot at the same moment. A contract with
    futures history but no matching index cannot be measured at all, so it
    is not part of the dataset -- it only looks like part of it.

    WHY THIS EXISTS, STATED PLAINLY: v1.1 evaluated three Phase 0
    conditions on every contract with FUTURES history and the fourth on
    whether spot reached back that far. Those are different populations,
    so the four conditions could never agree, and the live run duly
    reported 6.3 years and 26 cycles and then failed on spot coverage.

    I am changing this AFTER seeing a gate fail, which is the pattern this
    project exists to resist, so here is the whole case for the reader to
    judge:

      - no basis has been computed, so nothing outcome-dependent has been
        seen; only data availability
      - no threshold moves. MIN_YEARS, MIN_CYCLES and MIN_2022_CYCLES are
        untouched
      - three of the four conditions become HARDER, not easier: measured
        on the usable set the live data gives 4.8 years instead of 6.3 and
        18 cycles instead of 26
      - the pre-registration says "matching spot series over the same
        window". The window is the measurement window. A window where one
        leg does not exist was never a measurement window

    The bug was in what the conditions were computed over, not in what
    they require.
    """
    import datetime as dt
    ok, dropped = [], []
    for g in hist:
        if not g.get("index_first"):
            dropped.append((g["symbol"], "no index"))
            continue
        a = dt.date.fromisoformat(g["first"])
        b = dt.date.fromisoformat(g["last"])
        i0 = dt.date.fromisoformat(g["index_first"])
        i1 = dt.date.fromisoformat(g["index_last"])
        if (i0 - a).days > tol_days or (b - i1).days > tol_days:
            dropped.append((g["symbol"],
                            f"index {i0}..{i1} inside contract {a}..{b}"))
            continue
        ok.append(g)
    return ok, dropped


def looks_capped(n, first, last):
    """Is a candle count a response limit rather than the data's extent?

    The perpetual control returned exactly 2,000 bars spanning 1,999 days
    and stopping a year before today. That is a cap, not an endpoint. It
    does not invalidate the dated contracts -- 2,000 is far above their
    218 -- but any later attempt to pull a long series must paginate, and
    a round number that exactly matches its own span should never be read
    as "this is all there is".
    """
    import datetime as dt
    if not (n and first and last):
        return False
    span = (dt.date.fromisoformat(str(last))
            - dt.date.fromisoformat(str(first))).days + 1
    round_n = n in (500, 720, 1000, 1440, 2000, 5000, 10000)
    return bool(round_n and abs(span - n) <= max(3, 0.01 * n))


def phase0_verdict(years, cycles, cycles_2022, spot_ok, spot_detail=""):
    """The four frozen conditions. Pure function so it can be tested.

    Returns (proceed, list of (condition, ok, detail)).
    """
    checks = [
        (f"retrievable history >= {MIN_YEARS:.0f} years",
         years >= MIN_YEARS, f"{years:.1f} years"),
        (f"distinct cycles >= {MIN_CYCLES}",
         cycles >= MIN_CYCLES, f"{cycles} cycles"),
        (f"cycles expiring in 2022 >= {MIN_2022_CYCLES}",
         cycles_2022 >= MIN_2022_CYCLES, f"{cycles_2022} in 2022"),
        ("spot series COVERS the futures window",
         bool(spot_ok) or not REQUIRE_SPOT,
         spot_detail or ("found" if spot_ok else "MISSING")),
    ]
    return all(c[1] for c in checks), checks


def quarterly_expiries(years_back=8, today=None):
    """Candidate dated-contract expiries: the last Friday of Mar/Jun/Sep/Dec.

    The live instrument list shows only what is LISTED TODAY -- typically
    two or three contracts. Counting cycles from it would report "fewer
    than 12 cycles" and STOP for a reason that has nothing to do with
    whether history is retrievable, which is the actual Phase 0 question.
    So candidate symbols for PAST quarters are generated and probed, and
    the cycle count comes from what actually responds.
    """
    import datetime as dt
    today = today or dt.date.today()
    out = []
    for y in range(today.year - int(years_back) - 1, today.year + 2):
        for m in (3, 6, 9, 12):
            d = dt.date(y, m, 1) + dt.timedelta(days=32)
            d = d.replace(day=1) - dt.timedelta(days=1)      # month end
            while d.weekday() != 4:                          # back to Friday
                d -= dt.timedelta(days=1)
            if d <= today:
                out.append(d)
    return [d for d in sorted(out)
            if (today - d).days <= years_back * 366]


def discover_history(pair, res="1d", years_back=8, max_probe=16, pause=0.4,
                     prefixes=("FF", "FI"), verbose=True):
    """Which EXPIRED contracts still return candles? Newest first.

    Stops after max_probe candidate expiries so a probe stays polite; the
    number actually attempted is reported, because a cycle count that was
    truncated by a request budget must not be read as a cycle count that
    was limited by the data.
    """
    import datetime as dt
    found, attempted = [], 0
    for exp in reversed(quarterly_expiries(years_back)):
        if attempted >= max_probe:
            break
        attempted += 1
        hit = None
        for pre in prefixes:
            sym = f"{pre}_{pair.upper()}_{exp:%y%m%d}"
            got = probe_history(sym, res, years_back, ticks=("trade", "mark"))
            okk = [g for g in got if g.get("ok")]
            if okk:
                hit = dict(symbol=sym, expiry=str(exp), **okk[0])
                break
            time.sleep(pause)
        if hit:
            #: The settlement INDEX over the same contract's life. This is
            #: the right spot reference -- the contract settles against it,
            #: so it is matched to the window by construction rather than
            #: by hoping a separate spot endpoint reaches far enough back.
            idx = [g for g in probe_history(hit["symbol"], res, years_back,
                                            ticks=("spot",)) if g.get("ok")]
            if idx:
                hit["index_first"] = idx[0]["first"]
                hit["index_last"] = idx[0]["last"]
                hit["index_n"] = idx[0]["n"]
            found.append(hit)
            if verbose:
                print(f"    {hit['symbol']:<20} {hit['tick']:<6} "
                      f"{hit['n']:>5} bars  {hit['first']} -> {hit['last']}")
        elif verbose:
            print(f"    {pair}_{exp:%y%m%d} "
                  f"{'':<8} no history returned")
        time.sleep(pause)
    return found, attempted


def probe_history(symbol, res="1d", years_back=8, ticks=None):
    """Try every tick type for one contract. Reports what came back."""
    import datetime as dt
    now = int(time.time())
    frm = now - int(years_back * 365.25 * 86400)
    found = []
    for tick in (ticks or TICK_TYPES):
        for tmpl in CHART_TEMPLATES:
            url = tmpl.format(tick=tick, symbol=symbol, res=res,
                              frm=frm, to=now)
            try:
                js = json.loads(_get(url))
            except Exception as exc:                          # noqa: BLE001
                found.append(dict(tick=tick, ok=False,
                                  detail=str(exc)[:90]))
                continue
            c = js.get("candles") or js.get("result") or []
            if not c:
                found.append(dict(tick=tick, ok=False, detail="no candles"))
                continue
            ts = [int(x["time"]) // 1000 if int(x["time"]) > 1e11
                  else int(x["time"]) for x in c]
            found.append(dict(
                tick=tick, ok=True, n=len(c),
                first=str(dt.datetime.utcfromtimestamp(min(ts)).date()),
                last=str(dt.datetime.utcfromtimestamp(max(ts)).date())))
            break
    return found


def probe_cap(res="1d", years_back=8, symbol="PI_XBTUSD"):
    """Is the candle count per response CAPPED?

    Every dated contract in the first live run returned at most 218 bars,
    and 218 appeared repeatedly. That is either the contracts' true listed
    life or a response limit silently truncating every history in the
    sample -- and those two readings support opposite conclusions.

    A perpetual has years of continuous data. Ask it for the same window:
    if it also comes back near 218, the limit is the API and every count
    above is truncated. If it returns thousands, the 218s are real.
    """
    got = [g for g in probe_history(symbol, res, years_back,
                                    ticks=("trade",)) if g.get("ok")]
    if not got:
        return None
    return got[0]


def probe_spot():
    """Which spot source responds, and how much history does it give?"""
    import datetime as dt
    for url in SPOT_URLS:
        try:
            js = json.loads(_get(url))
        except Exception as exc:                              # noqa: BLE001
            print(f"    {url.split('pair=')[-1]:<12} FAIL {str(exc)[:60]}")
            continue
        if js.get("error"):
            print(f"    {url.split('pair=')[-1]:<12} error "
                  f"{js['error']}")
            continue
        res = js.get("result", {})
        key = next((k for k in res if k != "last"), None)
        if not key:
            continue
        rows = res[key]
        t0, t1 = rows[0][0], rows[-1][0]
        print(f"    {key:<12} {len(rows):,} daily candles  "
              f"{dt.datetime.utcfromtimestamp(t0).date()} -> "
              f"{dt.datetime.utcfromtimestamp(t1).date()}")
        return dict(source=url, pair=key, n=len(rows),
                    first=str(dt.datetime.utcfromtimestamp(t0).date()),
                    last=str(dt.datetime.utcfromtimestamp(t1).date()))
    return None


def run(args):
    import datetime as dt
    print(f"kraken_probe.py v{VERSION}   PHASE 0 -- AVAILABILITY ONLY\n")

    print("  INSTRUMENTS")
    payload, used = None, None
    for url in INSTRUMENT_URLS:
        try:
            payload = json.loads(_get(url))
            used = url
            print(f"    {url.rsplit('/', 1)[-1]:<14} OK")
            break
        except Exception as exc:                              # noqa: BLE001
            print(f"    {url.rsplit('/', 1)[-1]:<14} FAIL "
                  f"{str(exc)[:70]}")
    if payload is None:
        raise SystemExit("\n  STOP: no instrument list could be retrieved.\n"
                         "  Phase 0 fails on availability, not on a result.")

    rows, bad = parse_instruments(payload, args.pair)
    print(f"\n  {len(rows)} dated {args.pair} contracts visible")
    if bad:
        print(f"    {len(bad)} REJECTED -- symbol expiry disagrees with the "
              f"exchange:")
        for b in bad[:5]:
            print(f"      {b['symbol']}  encoded {b['expiry']}")
        rows = [r for r in rows if r["agrees"] is not False]
    by_year = cycles_by_year(rows)
    if by_year:
        print("    by expiry year: " + "  ".join(
            f"{y}:{n}" for y, n in by_year.items()))

    #: The live instrument list shows only what is LISTED today. The
    #: question Phase 0 actually asks is whether EXPIRED contracts remain
    #: retrievable, and that can only be answered by asking for one.
    print("\n  HISTORY FOR EXPIRED CONTRACTS -- the question that decides "
          "this")
    print(f"    probing up to {args.max_probe} past quarterly expiries, "
          f"newest first")
    hist, attempted = discover_history(args.pair, args.res, args.years_back,
                                       args.max_probe, args.pause)
    oldest = newest = None
    for g in hist:
        d0 = dt.date.fromisoformat(g["first"])
        d1 = dt.date.fromisoformat(g["last"])
        oldest = d0 if oldest is None else min(oldest, d0)
        newest = d1 if newest is None else max(newest, d1)
    print(f"\n    {len(hist)} of {attempted} probed expiries returned "
          f"history")
    if len(hist) == attempted and attempted >= args.max_probe:
        print("    NOTE: every probe succeeded and the budget was reached, "
              "so this")
        print("    count is limited by --max-probe, not by the data. Raise "
              "it before")
        print("    reading the cycle count as a limit.")

    print("\n  RESPONSE-LIMIT CONTROL")
    mx = max([g["n"] for g in hist], default=0)
    cap = probe_cap(args.res, args.years_back)
    if cap:
        print(f"    perpetual {cap['n']:,} bars  {cap['first']} -> "
              f"{cap['last']}   (largest contract: {mx})")
        if looks_capped(cap["n"], cap["first"], cap["last"]):
            print(f"    NOTE: {cap['n']:,} bars over "
                  f"{cap['n']} days, ending well before today -- that is a "
                  f"RESPONSE CAP,")
            print("    not the perpetual's extent. It is far above the "
                  "dated contracts' 218,")
            print("    so those are real lives; but any long pull later "
                  "must paginate.")
        elif cap["n"] <= mx * 1.2:
            print("    WARNING: the perpetual returns no more than the "
                  "dated contracts do.")
            print("    Every history above is probably TRUNCATED by a "
                  "response limit, not")
            print("    bounded by the contract's life. Paginate before "
                  "believing any of it.")
        else:
            print("    the perpetual returns far more, so the dated counts "
                  "are real lives,")
            print("    not truncation")
    else:
        print("    could not probe the perpetual; cap status unknown")

    print("\n  SPOT")
    print("    Kraken spot OHLC:")
    spot = probe_spot()
    #: prefer the settlement index, which is matched to each contract
    idx_first = min([g["index_first"] for g in hist if g.get("index_first")],
                    default=None)
    idx_last = max([g["index_last"] for g in hist if g.get("index_last")],
                   default=None)
    n_idx = sum(1 for g in hist if g.get("index_first"))
    print(f"    settlement index: {n_idx}/{len(hist)} contracts returned "
          f"one" + (f", {idx_first} -> {idx_last}" if idx_first else ""))

    #: The measurable dataset is contracts with BOTH legs, and every
    #: condition is evaluated on that one population.
    use, dropped = usable_contracts(hist)
    print(f"\n  USABLE DATASET -- contracts with a future AND a matching "
          f"index")
    print(f"    {len(use)} usable, {len(dropped)} dropped")
    for sym, why in dropped[:8]:
        print(f"      {sym:<20} {why}")
    if not use:
        u_first = u_last = None
        years, c2022 = 0.0, 0
        s_ok, s_detail = False, "no contract has both legs"
    else:
        u_first = min(g["first"] for g in use)
        u_last = max(g["last"] for g in use)
        years = (dt.date.fromisoformat(u_last)
                 - dt.date.fromisoformat(u_first)).days / 365.25
        c2022 = cycles_by_year([{"expiry": g["expiry"]} for g in use]
                               ).get(2022, 0)
        s_ok, s_detail = True, (f"both legs over {u_first} -> {u_last} "
                                f"by construction")
        print(f"    window {u_first} -> {u_last}")
        print("    by expiry year: " + "  ".join(
            f"{y}:{n}" for y, n in cycles_by_year(
                [{"expiry": g["expiry"]} for g in use]).items()))
    proceed, checks = phase0_verdict(years, len(use), c2022, s_ok, s_detail)

    print("\n  PHASE 0 VERDICT -- conditions frozen in PREREGISTRATION_v4")
    for name, ok, detail in checks:
        print(f"    [{'PASS' if ok else 'FAIL'}] {name:<34} {detail}")
    print(f"\n  {'PROCEED' if proceed else 'STOP'}")
    if not proceed:
        print("  Phase 0 fails. Per section 4 this is written up as a")
        print("  cost-of-information result. It does NOT fall back to")
        print("  perpetual funding rates -- silver15 already measured those")
        print("  and rejected them, and substituting the answer that is")
        print("  available for the question that was asked is the whole")
        print("  thing this pre-registration exists to stop.")

    man = dict(version=VERSION, generated=dt.datetime.utcnow().isoformat(),
               instrument_source=used, pair=args.pair,
               listed=rows, rejected=bad, retrievable=hist,
               probed=attempted, spot=spot, cap_control=cap,
               index_first=idx_first, index_last=idx_last,
               usable=use, dropped=dropped,
               window_first=u_first, window_last=u_last,
               years=round(years, 2), cycles=len(hist), cycles_2022=c2022,
               proceed=bool(proceed))
    if args.out:
        with open(os.path.expanduser(args.out), "w") as fh:
            json.dump(man, fh, indent=2)
        print(f"\n  manifest -> {args.out}")
    return 0 if proceed else 2


def self_test():
    import datetime as dt
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            #: a tuple is always truthy -- passing spot_covers() straight in
            #: would make the check unfailable
            raise TypeError(f"check({name!r}) got {type(cond).__name__}, "
                            f"not a boolean")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" +
              (f"   {detail}" if detail else ""))

    print(f"kraken_probe.py v{VERSION} self-test\n")

    print("symbol expiry parsing")
    check("a dated symbol yields its expiry",
          symbol_expiry("FF_XBTUSD_260626") == dt.date(2026, 6, 26),
          f"{symbol_expiry('FF_XBTUSD_260626')}")
    check("a perpetual is not a dated contract",
          symbol_expiry("PI_XBTUSD") is None)
    check("an impossible date is rejected, not clamped",
          symbol_expiry("FF_XBTUSD_261332") is None)

    print("\nthe expiry cross-check catches a mismatch (section 11.6)")
    good = dt.datetime(2026, 6, 26).timestamp() * 1000
    check("symbol and exchange agreeing passes",
          expiry_agrees("FF_XBTUSD_260626", good) is True)
    #: Planted: the exchange says September, the symbol says June. Left
    #: uncaught, every basis on this contract would be annualised over 30
    #: days instead of ~120 and report roughly four times its true premium.
    wrong = dt.datetime(2026, 9, 25).timestamp() * 1000
    check("a three-month mismatch is CAUGHT",
          expiry_agrees("FF_XBTUSD_260626", wrong) is False,
          "91 days apart")
    check("a one-day settlement-hour difference is tolerated",
          expiry_agrees("FF_XBTUSD_260626",
                        dt.datetime(2026, 6, 27).timestamp() * 1000) is True)
    check("a missing exchange expiry is NOT silently a pass",
          expiry_agrees("FF_XBTUSD_260626", None) is None)

    print("\nmismatched contracts are dropped before the manifest")
    payload = {"instruments": [
        {"symbol": "FF_XBTUSD_260626", "lastTradingTime": good},
        {"symbol": "FF_XBTUSD_260925",
         "lastTradingTime": dt.datetime(2026, 6, 26).timestamp() * 1000},
        {"symbol": "PI_XBTUSD"},
        {"symbol": "FF_ETHUSD_260626", "lastTradingTime": good},
    ]}
    rows, bad = parse_instruments(payload, "XBTUSD")
    check("perpetuals and other pairs are excluded",
          [r["symbol"] for r in rows] == ["FF_XBTUSD_260626",
                                          "FF_XBTUSD_260925"],
          f"{[r['symbol'] for r in rows]}")
    check("the planted mismatch is flagged", len(bad) == 1
          and bad[0]["symbol"] == "FF_XBTUSD_260925", f"{len(bad)} flagged")

    print("\nPhase 0 gates, each shown FAILING on a planted case")
    p, _ = phase0_verdict(5.0, 20, 4, {"pair": "X"})
    check("a qualifying dataset proceeds", p)
    p, c = phase0_verdict(2.9, 20, 4, {"pair": "X"})
    check("just under 3 years FAILS", not p, f"{c[0][2]}")
    p, c = phase0_verdict(5.0, 11, 4, {"pair": "X"})
    check("11 cycles FAILS", not p, f"{c[1][2]}")
    #: The condition this project cares about most. A long, deep sample
    #: that happens to skip the bear market must not pass: RESULT_VRP.md
    #: recorded Sharpe +1.34 for 2010-2017 against +0.32 full-sample.
    p, c = phase0_verdict(6.0, 24, 1, {"pair": "X"})
    check("a big sample that skips 2022 FAILS", not p, f"{c[2][2]}")
    p, c = phase0_verdict(5.0, 20, 4, None)
    check("no spot series FAILS", not p, f"{c[3][2]}")

    print("\nthe spot COVERAGE gate, and the live case that defeated v1.0")
    #: NB the locals below are named `cov`, not `ok`. An earlier version
    #: unpacked spot_covers() into `ok`, which is this function's pass/fail
    #: accumulator -- so every subsequent check ANDed against a coverage
    #: boolean instead of the running total, and the suite reported
    #: FAILURES ABOVE with every individual line showing PASS. A test
    #: harness that can corrupt its own verdict is worse than no harness.
    cov, d = spot_covers("2020-05-01", "2026-08-18",
                         "2020-05-29", "2026-06-26")
    check("a spot series spanning the futures window passes", cov, d)
    #: Exactly what the first live run returned. v1.0 asked only whether a
    #: spot series existed, saw 721 candles, and reported PROCEED on a
    #: window that cannot price a single 2022 contract.
    cov, d = spot_covers("2024-08-28", "2026-08-18",
                         "2020-05-29", "2026-06-26")
    check("the REAL 2024-2026 spot against 2020-2026 futures FAILS",
          not cov, d)
    cov, _ = spot_covers("2020-05-01", "2025-01-01",
                         "2020-05-29", "2026-06-26")
    check("a spot series that stops early also FAILS", not cov)
    cov, _ = spot_covers("2020-06-20", "2026-08-18",
                         "2020-05-29", "2026-06-26")
    check("a few weeks of lead-in is tolerated", cov)
    cov, _ = spot_covers(None, None, "2020-05-29", "2026-06-26")
    check("a missing spot series is not silently a pass", not cov)
    p, c = phase0_verdict(6.1, 24, 4, *spot_covers(
        "2024-08-28", "2026-08-18", "2020-05-29", "2026-06-26"))
    check("and the full verdict now STOPS on the live data", not p,
          "PROCEED withdrawn")

    print("\nthe usable dataset needs BOTH legs, per contract")

    def C(sym, a, b, i0=None, i1=None):
        g = dict(symbol=sym, first=a, last=b, expiry=b)
        if i0:
            g.update(index_first=i0, index_last=i1)
        return g
    hist = [
        C("FULL", "2022-01-03", "2022-06-24", "2022-01-03", "2022-06-24"),
        C("NOINDEX", "2021-01-04", "2021-06-25"),
        #: planted: the index appears halfway through the contract's life,
        #: so half of it has a future and no spot to price it against
        C("HALF", "2020-02-28", "2020-06-26", "2020-04-20", "2020-06-26"),
        C("SHORTEND", "2023-01-03", "2023-06-30", "2023-01-03", "2023-05-01"),
    ]
    use, dropped = usable_contracts(hist)
    check("a fully covered contract is usable",
          [g["symbol"] for g in use] == ["FULL"],
          f"{[g['symbol'] for g in use]}")
    check("no index at all is dropped",
          ("NOINDEX", "no index") in [(s, w) for s, w in dropped])
    check("an index starting mid-life is dropped",
          any(s == "HALF" for s, _ in dropped))
    check("an index ending early is dropped",
          any(s == "SHORTEND" for s, _ in dropped))

    print("\nthe live data, evaluated both ways")
    #: v1.1 measured years and cycles on every contract with FUTURES data
    #: and coverage against that same span. Recorded here so the change is
    #: visible rather than quietly applied.
    p_old, c_old = phase0_verdict(6.3, 26, 4, *spot_covers(
        "2021-07-07", "2026-06-26", "2020-02-26", "2026-06-26"))
    check("the OLD reading STOPS", not p_old, f"{c_old[3][2][:44]}...")
    p_new, c_new = phase0_verdict(4.8, 18, 4, True, "both legs")
    check("the usable-set reading PROCEEDS", p_new,
          "4.8 years, 18 cycles, 4 in 2022")
    check("and it is STRICTER on the conditions it shares",
          4.8 < 6.3 and 18 < 26, "6.3->4.8 years, 26->18 cycles")
    #: the gate must still be able to stop
    p_thin, _ = phase0_verdict(4.8, 11, 4, True, "both legs")
    check("a usable set of only 11 cycles still STOPS", not p_thin)
    p_no22, _ = phase0_verdict(4.8, 18, 1, True, "both legs")
    check("a usable set that misses 2022 still STOPS", not p_no22)

    print("\nround-number response caps are recognised")
    check("2,000 bars spanning 2,000 days is a cap",
          looks_capped(2000, "2020-02-26", "2025-08-17"), "the perpetual")
    check("218 bars over 218 days is NOT flagged",
          not looks_capped(218, "2025-11-21", "2026-06-26"),
          "a real contract life")
    check("a long series well short of a round number is not flagged",
          not looks_capped(1873, "2020-01-01", "2026-08-18"))

    print("\ncycle counting by year")
    rows2 = [{"expiry": "2022-03-25"}, {"expiry": "2022-06-24"},
             {"expiry": "2023-03-31"}]
    check("years are counted, not contracts",
          cycles_by_year(rows2) == {2022: 2, 2023: 1},
          f"{cycles_by_year(rows2)}")

    print("\ncandidate expiries are generated, not read off the live list")
    qs = quarterly_expiries(8, dt.date(2026, 8, 18))
    check("four per year", all(
        sum(1 for d in qs if d.year == y) == 4
        for y in range(2019, 2026)), f"{len(qs)} over 8 years")
    check("all fall on a Friday",
          all(d.weekday() == 4 for d in qs),
          f"{sorted({d.strftime('%A') for d in qs})}")
    check("all fall in Mar/Jun/Sep/Dec",
          all(d.month in (3, 6, 9, 12) for d in qs))
    check("each is the LAST Friday of its month",
          all((d + dt.timedelta(days=7)).month != d.month for d in qs))
    check("nothing in the future is proposed",
          max(qs) <= dt.date(2026, 8, 18), f"{max(qs)}")
    #: the whole point of generating these: enough cycles to clear Gate C
    check("eight years yields well over the 12-cycle minimum",
          len(qs) >= MIN_CYCLES * 2, f"{len(qs)} candidates")
    check("2022 is reachable", sum(1 for d in qs if d.year == 2022) == 4)

    print("\nthis file measures NOTHING")
    #: Checked by inspecting the module namespace. Grepping this file's own
    #: source for forbidden words has produced a self-matching false pass
    #: three times in this project -- the check kept finding itself.
    import kraken_probe as _self
    banned = ("basis", "premium", "carry", "annualis", "annualiz",
              "sharpe", "backtest", "signal", "pnl")
    def scan():
        return [x for x in dir(_self) if not x.startswith("_")
                and any(w in x.lower() for w in banned)]
    check("no basis / premium / carry function exists here", scan() == [],
          f"{scan()}")
    #: A gate that has never been observed to fail has not been tested.
    #: Inject a measurement-shaped name and confirm the detector fires,
    #: then remove it. Without this the check above passes whether or not
    #: it works.
    setattr(_self, "annualised_basis", lambda: None)
    fired = scan() == ["annualised_basis"]
    delattr(_self, "annualised_basis")
    check("and the detector demonstrably FIRES when one is added", fired
          and scan() == [], "planted annualised_basis, caught, removed")

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default="XBTUSD")
    ap.add_argument("--res", default="1d")
    ap.add_argument("--max-probe", type=int, default=24,
                    help="how many past quarterly expiries to probe")
    ap.add_argument("--years-back", type=float, default=8.0)
    ap.add_argument("--pause", type=float, default=0.4)
    ap.add_argument("--out", default="")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else run(a))


if __name__ == "__main__":
    main()
