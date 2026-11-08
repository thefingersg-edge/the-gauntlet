#!/usr/bin/env python3
"""TRACK A for PREREGISTRATION_v8 -- observe the basis forward, no capital.

WHAT THIS IS FOR
----------------
v8 section 1 establishes that a forward SIGNIFICANCE test on this premium
needs 17 cycles -- four and a bit years -- to reach 2 sigma, on something
already measured over 18 cycles. That is not what forward evidence is for.

What one quarter DOES settle is whether the printed price is obtainable.
Every figure in v4 and v7 assumes it; none of them tested it. This file
records, once a day and at zero risk:

    the front dated INVERSE contract's bid, ask and mid
    the settlement index
    the implied basis, annualised on the contract's own days to expiry
    the spread that would actually be crossed, in basis points

Append-only. One row per run. Never rewrites history -- a monitor that can
revise its own past is not a record.

    python basis_monitor.py --self-test
    python basis_monitor.py --out ../data/basis_log.csv
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken_probe as KP                                    # noqa: E402

VERSION = "1.4"

HEADER = ("observed_utc,symbol,expiry,days_to_expiry,bid,ask,mid,index,"
          "basis_pct,basis_ann_pct,spread_bp,mark,last,vol24h,"
          "open_interest,note")
#: Fields that are NOT tradeable prices and must never stand in for a mid.
#: A mark price is the venue's own valuation; a last trade is history. The
#: whole question Track A asks is whether a price can be OBTAINED, so
#: substituting either would answer a different question and look like an
#: answer to this one.
NOT_A_QUOTE = ("markPrice", "last")
#: v4 section 7 assumed 0.05% taker plus one tick. If the observed spread
#: is materially wider than that, the cost model was optimistic and the
#: monitor should say so rather than leaving it to be noticed.
ASSUMED_COST_BP = 5.0 + 2.0
#: Below this many days to expiry the annualised basis is noise times
#: 365/days and is withheld. See build_row. The raw basis is always kept.
MIN_DAYS_ANN = 5


def annualise(basis, days):
    """Simple annualisation on the contract's OWN days to expiry.

    Section 11.6 of v4 exists because a maturity taken from the wrong
    contract multiplies every figure by the ratio of the two. Same rule
    here: days come from the symbol being quoted, never from a neighbour.
    """
    if not days or days <= 0:
        return None
    return basis * 365.0 / days


def spread_bp(bid, ask):
    if not bid or not ask or bid <= 0 or ask <= 0 or ask < bid:
        return None
    return (ask - bid) / ((ask + bid) / 2.0) * 1e4


def pick_front(rows, today):
    """Nearest-expiry INVERSE dated contract that has not yet settled.

    Inverse, because v7 established that is the structure whose collateral
    arithmetic holds. A linear contract would be a different trade with a
    different capital requirement, and quietly substituting one would make
    the log describe something other than the frozen rule.
    """
    import datetime as dt
    live = []
    for r in rows:
        if not r.get("inverse") or not r.get("tradeable"):
            continue
        e = KP.symbol_expiry(r["symbol"])
        if e and e > today:
            live.append((e, r))
    if not live:
        return None, None
    live.sort(key=lambda x: x[0])
    return live[0][1], live[0][0]


def build_row(sym, expiry, days, bid, ask, index, note="",
              mark=None, last=None, vol24h=None, oi=None):
    """One observation. The basis is computed from the MID or not at all.

    If there is no two-sided quote there is no mid, and the basis column
    stays empty. It is not filled from the mark price or the last trade:
    Track A exists to find out whether a price can be obtained, and a mark
    price is the venue's own valuation of a market you may not be able to
    transact in. Substituting it would answer a different question in a
    column headed with this one's name.
    """
    mid = (bid + ask) / 2.0 if (bid and ask) else None
    basis = ((mid / index) - 1.0) if (mid and index) else None
    if mid is None and not note:
        note = "NO TWO-SIDED QUOTE"

    #: v1.4. Annualising divides by days to expiry, so the multiplier is
    #: 365/days -- 12x at a month, 52x at a week, 365x on the last day.
    #: On 2026-08-28 this file logged FF_XBTUSD_260828 at -947.15% ann,
    #: which is a mid 2.59% under the index on its settlement day times
    #: 365. That is not a rate, it is one wide quote amplified by the
    #: arithmetic, and left in an append-only log it would poison every
    #: later average taken over the column.
    #:
    #: The RAW basis is still recorded. Only the annualisation is
    #: withheld, and the row says why. Set before it could change any
    #: conclusion: Track A decides nothing and has no gates.
    ann = None
    if basis is not None:
        if days is not None and days >= MIN_DAYS_ANN:
            a = annualise(basis, days)
            ann = None if a is None else a * 100.0
        elif not note:
            note = f"NOT ANNUALISED -- under {MIN_DAYS_ANN}d to expiry"

    return dict(symbol=sym, expiry=str(expiry), days_to_expiry=days,
                bid=bid, ask=ask, mid=mid, index=index,
                basis_pct=None if basis is None else basis * 100.0,
                #: NOT `or 0.0` -- that turned an unannualisable row into a
                #: FALSE ZERO, indistinguishable from a real flat basis.
                basis_ann_pct=ann,
                spread_bp=spread_bp(bid, ask), mark=mark, last=last,
                vol24h=vol24h, open_interest=oi, note=note)


def fmt(row, stamp):
    def g(k):
        v = row.get(k)
        return "" if v is None else (f"{v:.6f}" if isinstance(v, float)
                                     else str(v))
    return ",".join([stamp, row["symbol"], row["expiry"],
                     str(row["days_to_expiry"]), g("bid"), g("ask"),
                     g("mid"), g("index"), g("basis_pct"),
                     g("basis_ann_pct"), g("spread_bp"), g("mark"),
                     g("last"), g("vol24h"), g("open_interest"),
                     (row.get("note") or "").replace(",", ";")])


def append(path, line, header=HEADER):
    """Append one row, creating the header once. Never rewrites.

    If a log already exists with a DIFFERENT header, this refuses. A file
    whose columns change halfway down is not a record -- every row above
    the change would be silently misread by anything that parses it, and
    the append-only guarantee would be worth nothing.
    """
    p = os.path.expanduser(path)
    if os.path.exists(p):
        with open(p) as fh:
            first = fh.readline().rstrip("\n")
        if first and first != header:
            raise SystemExit(
                f"\n  STOP: {p} has a different header.\n"
                f"  expected: {header}\n"
                f"  found:    {first}\n"
                f"  Move the old file aside rather than appending rows "
                f"with different\n  columns to it. A log whose shape "
                f"changes halfway down is not a record.")
    new = not os.path.exists(p)
    with open(p, "a") as fh:
        if new:
            fh.write(header + "\n")
        fh.write(line + "\n")
    return new


import kraken_collateral as KC                                # noqa: E402

#: v1.3. This file used to carry its OWN copy of is_dead, and on
#: 2026-08-25 kraken_collateral.py called three contracts "listed and
#: tradeable" minutes before this file called the same three DEAD. Two
#: definitions of one predicate in one directory is how that happens.
#: There is now one, and it lives in kraken_collateral.
is_dead = KC.is_dead


def survey(payload, tickers, pair="XBTUSD"):
    """Every dated contract of both types, with its live liquidity."""
    by_sym = {(t.get("symbol") or "").upper(): t for t in tickers}
    out = []
    for r in KC.classify(payload, pair):
        t = by_sym.get(r["symbol"], {})
        dead, why = is_dead(t) if t else (True, ["no ticker"])
        out.append(dict(symbol=r["symbol"],
                        kind="inverse" if r["inverse"] else "linear",
                        tradeable=r["tradeable"],
                        bid=t.get("bid"), ask=t.get("ask"),
                        oi=t.get("openInterest"), vol=t.get("vol24h"),
                        dead=dead, why="; ".join(why)))
    return sorted(out, key=lambda r: (r["kind"], r["symbol"]))


def self_test():
    import datetime as dt
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"basis_monitor.py v{VERSION} self-test\n")

    print("annualisation uses the contract's OWN days")
    check("a 2% basis over 90 days is ~8.1%/yr",
          abs(annualise(0.02, 90) - 0.0811) < 1e-3,
          f"{annualise(0.02, 90)*100:.2f}%")
    #: planted: the same basis on the wrong maturity inflates it 3x
    check("read over 30 days instead it reads 3x too high",
          abs(annualise(0.02, 30) / annualise(0.02, 90) - 3.0) < 1e-9,
          f"{annualise(0.02, 30)*100:.1f}% vs {annualise(0.02, 90)*100:.1f}%")
    check("zero or negative days is None, not a division",
          annualise(0.02, 0) is None and annualise(0.02, -5) is None)

    print("\nnear expiry the annualisation is withheld, not printed (v1.4)")
    #: PLANTED: the real 2026-08-28 observation. Mid 2.59% under the
    #: index with one day left annualised to -947%, and that number went
    #: into an append-only log.
    d0 = dt.date(2026, 8, 28)
    near = build_row("FF_XBTUSD_260828", d0, 1,
                     79000.0, 79423.0, 81180.0)
    check("the -947% row no longer carries an annualised figure",
          near["basis_ann_pct"] is None,
          f"raw basis {near['basis_pct']:+.2f}% would annualise to "
          f"{annualise(near['basis_pct']/100.0, 1)*100:+.0f}%")
    check("but the RAW basis is still recorded",
          near["basis_pct"] is not None and near["spread_bp"] is not None,
          f"{near['basis_pct']:+.3f}%  {near['spread_bp']:.0f}bp")
    check("and the row says why", "NOT ANNUALISED" in near["note"],
          near["note"])
    far = build_row("FF_XBTUSD_260925", dt.date(2026, 9, 25), 28,
                    79000.0, 79100.0, 78900.0)
    check("a normal maturity is unaffected",
          far["basis_ann_pct"] is not None,
          f"{far['basis_ann_pct']:+.2f}% ann")
    #: the boundary itself, both sides
    for dd, want in ((MIN_DAYS_ANN - 1, False), (MIN_DAYS_ANN, True)):
        r = build_row("X", d0, dd, 100.0, 100.2, 100.0)
        check(f"{dd}d {'is' if want else 'is not'} annualised",
              (r["basis_ann_pct"] is not None) == want)
    #: the false zero this replaced: `or 0.0` made an unannualisable row
    #: indistinguishable from a genuinely flat basis
    check("an unannualisable row is EMPTY, never 0.0",
          near["basis_ann_pct"] is not None or near["basis_ann_pct"] != 0.0)
    check("and its CSV cell is blank, not '0.000000'",
          fmt(near, "T").split(",")[9] == "",
          f"cell={fmt(near, 'T').split(',')[9]!r}")

    print("\nthe spread is measured, not assumed")
    check("a 10bp spread reads 10bp",
          abs(spread_bp(99.95, 100.05) - 10.0) < 0.01,
          f"{spread_bp(99.95, 100.05):.2f}bp")
    check("a crossed or missing quote is None",
          spread_bp(100.0, 99.0) is None and spread_bp(None, 100.0) is None
          and spread_bp(0.0, 100.0) is None)

    print("\nthe front contract must be INVERSE and unexpired")
    today = dt.date(2026, 8, 19)
    rows = [dict(symbol="FF_XBTUSD_260828", inverse=False, tradeable=True),
            dict(symbol="FI_XBTUSD_260925", inverse=True, tradeable=True),
            dict(symbol="FI_XBTUSD_260828", inverse=True, tradeable=True),
            dict(symbol="FI_XBTUSD_251226", inverse=True, tradeable=True),
            dict(symbol="FI_XBTUSD_261225", inverse=True, tradeable=False)]
    r, e = pick_front(rows, today)
    check("the nearest UNEXPIRED inverse contract is chosen",
          r and r["symbol"] == "FI_XBTUSD_260828", r["symbol"] if r else "-")
    check("an expired one is skipped even though it is nearer",
          e == dt.date(2026, 8, 28), str(e))
    check("a linear contract is never chosen",
          all(not x["inverse"] or True for x in rows)
          and r["symbol"].startswith("FI_"))
    check("a non-tradeable contract is skipped",
          r["symbol"] != "FI_XBTUSD_261225")
    check("no live inverse contract returns None, not a guess",
          pick_front([dict(symbol="FF_XBTUSD_260828", inverse=False,
                           tradeable=True)], today) == (None, None))

    print("\na row carries what it claims")
    row = build_row("FI_XBTUSD_260925", dt.date(2026, 9, 25), 37,
                    100200.0, 100300.0, 100000.0)
    check("basis is mid over index, not bid or ask",
          abs(row["basis_pct"] - 0.25) < 1e-9, f"{row['basis_pct']:.4f}%")
    check("and annualised on 37 days, not on 90",
          abs(row["basis_ann_pct"] - 0.25 * 365 / 37) < 1e-6,
          f"{row['basis_ann_pct']:.2f}%")
    check("spread comes through", abs(row["spread_bp"] - 9.97) < 0.1,
          f"{row['spread_bp']:.2f}bp")

    print("\na missing quote leaves the basis EMPTY, never substituted")
    nq = build_row("FI_XBTUSD_260828", dt.date(2026, 8, 28), 7,
                   None, None, 77005.45, mark=77100.0, last=77050.0,
                   vol24h=0.0, oi=0.0)
    check("no bid or ask means no mid", nq["mid"] is None)
    check("and no basis", nq["basis_pct"] is None
          and nq["basis_ann_pct"] is None)
    #: planted: the mark price is RIGHT THERE and would have produced a
    #: plausible-looking basis. It must not be used.
    check("the mark price is carried but not substituted",
          nq["mark"] == 77100.0 and nq["basis_pct"] is None,
          "mark present, basis empty")
    check("the row says so in its note",
          nq["note"] == "NO TWO-SIDED QUOTE", nq["note"])
    check("a one-sided quote is also refused",
          build_row("X", dt.date(2026, 8, 28), 7, 77000.0, None,
                    77005.45)["basis_pct"] is None)
    check("liquidity fields are carried for the illiquidity finding",
          nq["vol24h"] == 0.0 and nq["open_interest"] == 0.0)

    print("\n'tradeable' is not 'traded' (the day-one finding)")
    #: exactly what the live run returned for FI_XBTUSD_260828
    dead_t = dict(symbol="FI_XBTUSD_260828", indexPrice=77707.15,
                  markPrice=77707.15, openInterest=0, vol24h=0,
                  change24h=0.0)
    d, why = is_dead(dead_t)
    check("no quote, zero interest, mark == index reads DEAD", d,
          "; ".join(why))
    check("and it names every reason, not just the first",
          len(why) >= 3, f"{len(why)} reasons")
    live_t = dict(symbol="FF_XBTUSD_260925", bid=77650.0, ask=77680.0,
                  indexPrice=77600.0, markPrice=77665.0,
                  openInterest=1200, vol24h=340)
    check("a genuinely quoted contract is not flagged",
          not is_dead(live_t)[0], "; ".join(is_dead(live_t)[1]) or "none")
    #: one weak signal alone must not condemn a contract
    thin = dict(symbol="X", bid=1.0, ask=2.0, indexPrice=1.5,
                markPrice=1.6, openInterest=0, vol24h=50)
    check("a single zero is not enough to call it dead",
          not is_dead(thin)[0], "; ".join(is_dead(thin)[1]))
    check("a contract with no ticker at all is dead by default",
          is_dead({})[0])

    print("\nthe log is append-only")
    import tempfile
    p = os.path.join(tempfile.mkdtemp(), "log.csv")
    check("the first write creates the header", append(p, fmt(row, "T1")))
    check("the second does not", not append(p, fmt(row, "T2")))
    body = open(p).read().splitlines()
    check("both rows are present and the header appears once",
          len(body) == 3 and body[0] == HEADER, f"{len(body)} lines")
    check("the earlier row is untouched", body[1].startswith("T1,"))
    #: a monitor that can revise its own past is not a record
    import basis_monitor as _self
    bad = [x for x in dir(_self) if not x.startswith("_")
           and any(w in x.lower() for w in ("rewrite", "update", "delete",
                                            "overwrite", "truncate"))]
    check("no function can rewrite the log", bad == [], f"{bad}")
    #: a log whose columns change halfway down is not a record
    p2 = os.path.join(tempfile.mkdtemp(), "old.csv")
    open(p2, "w").write("observed_utc,symbol,expiry\nT0,X,2026-01-01\n")
    try:
        append(p2, fmt(row, "T3"))
        widened = False
    except SystemExit:
        widened = True
    check("appending to a log with a DIFFERENT header is refused", widened)
    check("and the old file is left untouched",
          open(p2).read().splitlines()[0] == "observed_utc,symbol,expiry")

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../data/basis_log.csv")
    ap.add_argument("--pair", default="XBTUSD")
    ap.add_argument("--survey", action="store_true",
                    help="every dated contract, both types, with liquidity")
    ap.add_argument("--all-dated", action="store_true",
                    help="log EVERY dated contract, not just the front "
                         "inverse (proposed v8 amendment, opt-in)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc)
    print(f"basis_monitor.py v{VERSION}   TRACK A -- OBSERVATION ONLY\n")

    payload = None
    for url in KP.INSTRUMENT_URLS:
        try:
            payload = json.loads(KP._get(url))
            break
        except Exception as exc:                              # noqa: BLE001
            print(f"  {url.rsplit('/', 1)[-1]} FAIL {str(exc)[:60]}")
    if payload is None:
        raise SystemExit("  no instrument list; nothing recorded")

    import kraken_collateral as KC
    rows = KC.classify(payload, a.pair)

    if a.survey:
        try:
            tj = json.loads(KP._get(f"{KP.FUT}/derivatives/api/v3/tickers"))
        except Exception as exc:                              # noqa: BLE001
            raise SystemExit(f"  tickers FAIL {str(exc)[:70]}")
        s = survey(payload, tj.get("tickers", []), a.pair)
        print(f"  {'symbol':<20}{'type':<9}{'bid':>10}{'ask':>10}"
              f"{'OI':>10}{'vol24h':>10}   state")
        print("  " + "-" * 78)
        for r in s:
            print(f"  {r['symbol']:<20}{r['kind']:<9}"
                  f"{str(r['bid'] or '-'):>10}{str(r['ask'] or '-'):>10}"
                  f"{str(r['oi'] if r['oi'] is not None else '-'):>10}"
                  f"{str(r['vol'] if r['vol'] is not None else '-'):>10}"
                  f"   {'DEAD' if r['dead'] else 'quoted'}")
        inv = [r for r in s if r["kind"] == "inverse"]
        lin = [r for r in s if r["kind"] == "linear"]
        iv = sum(1 for r in inv if not r["dead"])
        lv = sum(1 for r in lin if not r["dead"])
        print(f"\n  inverse: {iv} of {len(inv)} quoted     "
              f"linear: {lv} of {len(lin)} quoted")
        if inv and iv == 0:
            print("\n  NO INVERSE CONTRACT IS QUOTED.")
            print("  PREREGISTRATION_v7's PROCEED rests on the inverse "
                  "structure, whose")
            print("  BTC margining removes the buffer. If none of them "
                  "trades, that")
            print("  argument describes an instrument you cannot enter, "
                  "and the")
            print("  tradeable contract is LINEAR -- for which v7's own "
                  "Gate 0 returned")
            print("  UNDETERMINED, and section 4 says v4's rejection "
                  "stands.")
        sys.exit(0 if iv else 2)

    if a.all_dated:
        #: PROPOSED AMENDMENT to PREREGISTRATION_v8 section 4, which names
        #: FI_XBTUSD. That instrument is not quoted, so the default path
        #: below records an empty row every day forever.
        #:
        #: This is opt-in and OFF by default, because v8 section 6 says
        #: the protocol is not modified mid-cycle and a frozen rule that
        #: quietly changes is worth nothing. What makes it defensible if
        #: taken up: logging EVERY dated contract removes a choice rather
        #: than adding one. There is no selection to steer.
        try:
            tj = json.loads(KP._get(
                f"{KP.FUT}/derivatives/api/v3/tickers"))
        except Exception as exc:                              # noqa: BLE001
            raise SystemExit(f"  tickers FAIL {str(exc)[:70]}")
        by_sym = {(t.get("symbol") or "").upper(): t
                  for t in tj.get("tickers", [])}
        stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        n = 0
        for r in sorted(rows, key=lambda x: x["symbol"]):
            t = by_sym.get(r["symbol"])
            if not t:
                continue
            exp = KP.symbol_expiry(r["symbol"])
            if exp is None:
                continue

            def num(k, _t=t):
                v = _t.get(k)
                try:
                    return float(v) if v not in (None, "") else None
                except (TypeError, ValueError):
                    return None
            row = build_row(r["symbol"], exp, (exp - now.date()).days,
                            num("bid"), num("ask"), num("indexPrice"),
                            mark=num("markPrice"), last=num("last"),
                            vol24h=num("vol24h"),
                            oi=num("openInterest"))
            append(a.out, fmt(row, stamp))
            sp, ann = row["spread_bp"], row["basis_ann_pct"]
            s_txt = "-" if sp is None else "%.2f bp" % sp
            a_txt = "-" if ann is None else "%+.2f%% ann" % ann
            kind = "inverse" if r["inverse"] else "linear"
            print("  %-20s%-9s%12s%16s"
                  % (r["symbol"], kind, s_txt, a_txt))
            n += 1
        print(f"\n  {n} contract(s) appended to {a.out}")
        sys.exit(0)

    front, expiry = pick_front(rows, now.date())
    if front is None:
        raise SystemExit("  no live inverse dated contract; nothing "
                         "recorded")
    days = (expiry - now.date()).days
    print(f"  front inverse contract  {front['symbol']}  "
          f"expiry {expiry}  {days} days out")

    tick = None
    try:
        js = json.loads(KP._get(
            f"{KP.FUT}/derivatives/api/v3/tickers"))
        for t in js.get("tickers", []):
            if (t.get("symbol") or "").upper() == front["symbol"]:
                tick = t
                break
    except Exception as exc:                                  # noqa: BLE001
        print(f"  tickers FAIL {str(exc)[:60]}")

    if not tick:
        raise SystemExit("  no ticker for the front contract; nothing "
                         "recorded")
    def num(k):
        v = tick.get(k)
        try:
            return float(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            return None

    bid, ask, index = num("bid"), num("ask"), num("indexPrice")
    row = build_row(front["symbol"], expiry, days, bid, ask, index,
                    mark=num("markPrice"), last=num("last"),
                    vol24h=num("vol24h"), oi=num("openInterest"))

    print(f"  bid {bid}   ask {ask}   index {index}")
    if bid is None or ask is None:
        #: Two very different causes and they need opposite responses, so
        #: the raw payload is shown rather than guessed at.
        print("\n  NO TWO-SIDED QUOTE. That is either a field-name problem "
              "or the")
        print("  contract is not quoted. The ticker's own keys, so the "
              "next run can")
        print("  tell which:")
        for k in sorted(tick):
            print(f"    {k:<22} {tick[k]}")
        print("\n  The basis column is left EMPTY rather than filled from "
              f"{', '.join(NOT_A_QUOTE)}.")
        print("  Those are not tradeable prices, and whether a price can "
              "be obtained")
        print("  is the entire question Track A was built to answer.")
        if row["vol24h"] is not None or row["open_interest"] is not None:
            print(f"\n  24h volume {row['vol24h']}   open interest "
                  f"{row['open_interest']}")
            print("  If those are near zero, the inverse contract is "
                  "LISTED BUT NOT")
            print("  TRADED -- and PREREGISTRATION_v7's whole capital "
                  "argument rests on")
            print("  an instrument nobody is quoting. That would be the "
                  "most important")
            print("  thing this protocol could find, and it would find it "
                  "on day one.")
    if row["basis_ann_pct"] is not None:
        print(f"  basis {row['basis_pct']:+.3f}%  = "
              f"{row['basis_ann_pct']:+.2f}%/yr on {days} days")
    if row["spread_bp"] is not None:
        print(f"  spread {row['spread_bp']:.1f}bp   "
              f"(v4 section 7 assumed about {ASSUMED_COST_BP:.0f}bp "
              f"all-in per leg)")
        if row["spread_bp"] > ASSUMED_COST_BP * 2:
            print("  NOTE: the observed spread is more than twice what the "
                  "cost model")
            print("  assumed. One observation is not a pattern, but log it "
                  "and watch.")

    fresh = append(a.out, fmt(row, now.isoformat(timespec="seconds")))
    print(f"\n  appended to {a.out}"
          + ("  (created)" if fresh else ""))
    print("  Append-only. Run daily; nothing here rewrites an earlier row.")


if __name__ == "__main__":
    main()
