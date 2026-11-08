#!/usr/bin/env python3
"""PREREGISTRATION_v14 -- the day-before session, on FOMC, CPI and NFP.

    SEGMENT   09:30 ET -> 16:00 ET on D-1, on M15 bars

One construction, three event types. Gate E failed on a uniform window;
this re-asks it on the segment the FOMC decomposition identified as
carrying the effect:

    09:30 D-1 -> 14:00 D-1   +38.26 bp   t 4.02   17/20   <- the money
    14:00 D-1 -> 13:00 D     +12.72 bp   t 1.07    8/20
    13:00 D   -> 13:45 D      -4.96 bp   t -2.10   8/20

THE CALIBRATION LINE, AND IT CAN VOID THE RUN
---------------------------------------------
v14 section 6: the 20 press-conference FOMC announcements of 2011-2015
must land between +30 and +50 bp on this segment. That figure is known
from v12's decomposition. If it does not, this file is building the
segment differently from that decomposition and **every number it
prints, CPI included, is void**. A test whose calibration is not checked
is a test that cannot fail for the right reason.

STDLIB ONLY.

    python3 preann_session.py --self-test
    python3 preann_session.py
"""

from __future__ import annotations

import argparse
import bisect
import csv
import datetime as dt
import math
import os
import statistics as st
import sys
from zoneinfo import ZoneInfo

VERSION = "1.0"

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
BAR = dt.timedelta(minutes=15)

#: ---- FROZEN IN PREREGISTRATION_v14 SECTION 3 ----
SESSION_OPEN = dt.time(9, 30)
SESSION_CLOSE = dt.time(16, 0)
SEG_BARS = 26                      # 6.5 hours of 15m starts
MIN_BARS = 20                      # a holed session is dropped
SANITY_MAX_BP = 70.0
#: v14 section 4 and 6.
CAL_LO, CAL_HI = 30.0, 50.0        # the press-conference calibration band
PRED = {"FOMC": (5.0, 20.0), "CPI": (-10.0, 10.0), "NFP": (-10.0, 10.0)}
FALSIFY_CPI_BP = 25.0
ERA_BREAK = 2016


def release_utc(date_iso, time_et):
    d = dt.date.fromisoformat(date_iso)
    hh, mm = (int(x) for x in time_et.split(":"))
    return dt.datetime(d.year, d.month, d.day, hh, mm,
                       tzinfo=ET).astimezone(UTC)


def session_bounds(event_date_iso):
    """(open_utc, close_utc) for the regular session on D-1.

    Built from the D-1 Eastern date through zoneinfo, so the offset is
    whatever was in force that day -- which can differ from the offset
    on the event date across a changeover weekend.
    """
    d = dt.date.fromisoformat(event_date_iso) - dt.timedelta(days=1)
    o = dt.datetime.combine(d, SESSION_OPEN, tzinfo=ET).astimezone(UTC)
    c = dt.datetime.combine(d, SESSION_CLOSE, tzinfo=ET).astimezone(UTC)
    return o, c


def load_bars(path_bid, path_ask):
    def rd(p):
        out = {}
        with open(p) as fh:
            for r in csv.DictReader(fh):
                t = dt.datetime.fromisoformat(r["time"]).replace(tzinfo=UTC)
                out[t] = (float(r["open"]), float(r["close"]))
        return out
    b, a = rd(path_bid), rd(path_ask)
    common = b.keys() & a.keys()
    return ({t: ((b[t][0] + a[t][0]) / 2.0, (b[t][1] + a[t][1]) / 2.0)
             for t in common}, len(common))


def seg_return(bars, keys, t0, t1):
    """Entry at the OPEN of the bar starting t0, exit at the CLOSE of the
    bar starting t1-BAR. (bp, n, last) or (None, why, None)."""
    last = t1 - BAR
    if t0 not in bars:
        return None, "no bar at the open", None
    if last not in bars:
        return None, "no bar at the close", None
    n = bisect.bisect_right(keys, last) - bisect.bisect_left(keys, t0)
    if n < MIN_BARS:
        return None, f"only {n} bars", None
    o, c = bars[t0][0], bars[last][1]
    if not o or not c:
        return None, "zero price", None
    return (c / o - 1.0) * 1e4, n, last


def welch_t(x, y):
    if len(x) < 2 or len(y) < 2:
        return None, None
    se = math.sqrt(st.variance(x) / len(x) + st.variance(y) / len(y))
    if se == 0:
        return None, None
    return (st.mean(x) - st.mean(y)) / se, st.mean(x) - st.mean(y)


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"preann_session.py v{VERSION} self-test\n")

    print("the session is D-1's, in Eastern, through zoneinfo")
    o, c = session_bounds("2015-06-17")
    check("it lands on the calendar day before",
          o.astimezone(ET).date() == dt.date(2015, 6, 16))
    check("a June session opens 13:30 UTC (EDT)", o.hour == 13, f"{o}")
    check("and closes 20:00 UTC", c.hour == 20, f"{c}")
    ow, cw = session_bounds("2015-01-28")
    check("a January session opens 14:30 UTC (EST)", ow.hour == 14)
    check("the two differ by an hour -- no offset constant works",
          ow.hour - o.hour == 1)
    #: PLANTED: the event and its D-1 can sit on OPPOSITE sides of a DST
    #: switch, so the offset must come from D-1, not from the event.
    om, cm = session_bounds("2015-03-09")          # Mon after the switch
    check("a Monday event after the switch uses Sunday's offset",
          om.astimezone(ET).date() == dt.date(2015, 3, 8)
          and om.astimezone(ET).time() == SESSION_OPEN)
    check("the session is 6.5 hours", (c - o) == dt.timedelta(hours=6.5))
    check(f"which is {SEG_BARS} bars of 15 minutes",
          int((c - o) / BAR) == SEG_BARS, f"{int((c-o)/BAR)}")

    print("\nthe segment ends at the close and never reaches the release")
    #: CPI/NFP release at 08:30 the NEXT morning, FOMC at 14:00. The
    #: segment ends at 16:00 on D-1, so it cannot touch either.
    for d, tm in (("2015-06-17", "14:00"), ("2015-06-17", "08:30")):
        T = release_utc(d, tm)
        _, cc = session_bounds(d)
        check(f"a {tm} release is after the D-1 close", cc < T,
              f"close {cc} < T {T}")
    check("the gap to a 14:00 FOMC is 22 hours",
          release_utc("2015-06-17", "14:00") - session_bounds("2015-06-17")[1]
          == dt.timedelta(hours=22))
    check("and to an 08:30 CPI it is 16.5 -- the asymmetry v14 s3 names",
          release_utc("2015-06-17", "08:30") - session_bounds("2015-06-17")[1]
          == dt.timedelta(hours=16.5))

    print("\nthe arithmetic")
    o, c = session_bounds("2015-06-17")
    bars = {o + BAR * i: (100.0, 100.0) for i in range(SEG_BARS)}
    keys = sorted(bars)
    r, n, last = seg_return(bars, keys, o, c)
    check(f"a full session is {SEG_BARS} bars", n == SEG_BARS, f"{n}")
    check("the last bar CLOSES at 16:00", last + BAR == c)
    check("a flat session reads 0 bp", abs(r) < 1e-9)
    up = dict(bars)
    up[o] = (100.0, 100.0)
    up[c - BAR] = (100.0, 100.3826)
    check("a 0.3826% rise reads 38.26 bp -- the FOMC figure",
          abs(seg_return(up, sorted(up), o, c)[0] - 38.26) < 1e-4,
          f"{seg_return(up, sorted(up), o, c)[0]:.2f}")

    print("\nrefusals")
    noo = {k: v for k, v in bars.items() if k != o}
    check("a missing 09:30 bar is dropped, not shifted",
          seg_return(noo, sorted(noo), o, c)[0] is None)
    noc = {k: v for k, v in bars.items() if k != c - BAR}
    check("a missing close bar is dropped",
          seg_return(noc, sorted(noc), o, c)[0] is None)
    thin = {k: v for k, v in bars.items()
            if k in (o, c - BAR) or k < o + BAR * 5}
    check("a holed session is refused",
          seg_return(thin, sorted(thin), o, c)[0] is None)
    #: a weekend D-1 has no session at all
    wk, _ = session_bounds("2015-06-15")       # D-1 = Sunday
    check("a weekend D-1 is a Sunday and will have no bars",
          wk.astimezone(ET).date().weekday() == 6)

    print("\nthe predictions and the void condition are in the file")
    check("CPI predicted within +/-10 bp", PRED["CPI"] == (-10.0, 10.0))
    check("NFP predicted within +/-10 bp", PRED["NFP"] == (-10.0, 10.0))
    check("FOMC predicted +5..+20", PRED["FOMC"] == (5.0, 20.0))
    check("the calibration band is +30..+50", (CAL_LO, CAL_HI) == (30.0, 50.0))
    check("CPI above +25 falsifies the FOMC-specific reading",
          FALSIFY_CPI_BP == 25.0)
    #: PLANTED: the calibration band must be able to REJECT. If it
    #: spanned everything it would never void anything.
    check("the band rejects the null and the reaction alike",
          not (CAL_LO <= 0.0 <= CAL_HI) and not (CAL_LO <= 100.0 <= CAL_HI))

    print("\nthis file holds no position and fits nothing")
    import preann_session as _self
    banned = ("sweep", "optimi", "tune", "grid", "refit", "order",
              "submit", "position")
    check("no fitting or trading function exists",
          [x for x in dir(_self) if not x.startswith("_")
           and any(w in x.lower() for w in banned)] == [])

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="../data/events.csv")
    ap.add_argument("--bid", default="../data/spx500usd_bid_15m.csv")
    ap.add_argument("--ask", default="../data/spx500usd_ask_15m.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import preann_arm2 as A2

    print(f"preann_session.py v{VERSION}   PREREGISTRATION_v14\n")
    print(f"  segment 09:30 -> 16:00 ET on D-1. One construction, three")
    print(f"  event types. Frozen before any CPI session was measured.\n")

    bars, nc = load_bars(a.bid, a.ask)
    keys = sorted(bars)
    print(f"  bars aligned: {nc:,}")

    ev = list(csv.DictReader(open(a.events)))
    got, drops = {}, {}
    for r in ev:
        if r["time_quality"] == "UNCERTAIN" and r["event"] == "FOMC" \
                and not A2.resolve_time(r["date"])[0]:
            continue
        o, c = session_bounds(r["date"])
        v, n, last = seg_return(bars, keys, o, c)
        if v is None:
            drops.setdefault(r["event"], {})
            drops[r["event"]][n] = drops[r["event"]].get(n, 0) + 1
            continue
        if last + BAR > c:
            print(f"    KILL: {r['date']} used a bar past the close")
            sys.exit(3)
        got.setdefault(r["event"], []).append((r["date"], v))

    #: control: the same 09:30-16:00 segment on non-event days
    all_ev = {dt.date.fromisoformat(r["date"]) for r in ev}
    near = {d + dt.timedelta(days=k) for d in all_ev for k in (-1, 0, 1)}
    ctrl, seen = [], set()
    for k in keys:
        d = k.astimezone(ET).date()
        if d in near or d in seen:
            continue
        seen.add(d)
        o = dt.datetime.combine(d, SESSION_OPEN, tzinfo=ET).astimezone(UTC)
        c = dt.datetime.combine(d, SESSION_CLOSE, tzinfo=ET).astimezone(UTC)
        v, _, _ = seg_return(bars, keys, o, c)
        if v is not None:
            ctrl.append(v)
    print(f"  control: {len(ctrl):,} non-event sessions, "
          f"mean {st.mean(ctrl):+.2f} bp\n")

    #: ---- the calibration line runs FIRST. It can void everything. ----
    pc = [v for d, v in got.get("FOMC", [])
          if d in A2.PRESSER_ALL and "2011-04-01" <= d <= "2015-12-31"]
    print(f"  CALIBRATION (v14 section 6) -- must land in "
          f"+{CAL_LO:.0f}..+{CAL_HI:.0f}")
    if len(pc) < 2:
        print(f"    VOID: only {len(pc)} press-conference events measurable")
        sys.exit(3)
    cal = st.mean(pc)
    okc = CAL_LO <= cal <= CAL_HI
    print(f"    FOMC press conference 2011-15   n={len(pc)}   "
          f"{cal:+.2f} bp   {'OK' if okc else 'OUT OF BAND'}")
    if not okc:
        print(f"\n    VOID -- this file builds the segment differently from")
        print(f"    v12's decomposition. Every number below, CPI included,")
        print(f"    is discarded. v14 section 6.")
        sys.exit(3)
    print(f"    the segment matches v12's decomposition. Proceeding.\n")

    print(f"  {'event':<7}{'n':>5}{'mean bp':>10}{'median':>9}{'ctrl':>8}"
          f"{'excess':>9}{'t':>7}{'positive':>10}")
    print("  " + "-" * 65)
    res = {}
    for et in ("FOMC", "CPI", "NFP"):
        rows = got.get(et, [])
        if len(rows) < 2:
            continue
        v = [x[1] for x in rows]
        t, diff = welch_t(v, ctrl)
        res[et] = diff
        print(f"  {et:<7}{len(v):>5}{st.mean(v):>10.2f}{st.median(v):>9.2f}"
              f"{st.mean(ctrl):>8.2f}{diff:>9.2f}{t:>7.2f}"
              f"{f'{sum(1 for x in v if x>0)}/{len(v)}':>10}")

    print(f"\n  BY ERA -- v13 put the FOMC break at {ERA_BREAK}")
    print(f"  {'event':<7}{'pre-' + str(ERA_BREAK):>12}{'n':>5}"
          f"{str(ERA_BREAK) + '+':>12}{'n':>5}")
    for et in ("FOMC", "CPI", "NFP"):
        rows = got.get(et, [])
        pre = [v for d, v in rows if int(d[:4]) < ERA_BREAK]
        post = [v for d, v in rows if int(d[:4]) >= ERA_BREAK]
        if len(pre) < 2 or len(post) < 2:
            continue
        print(f"  {et:<7}{st.mean(pre) - st.mean(ctrl):>+12.2f}{len(pre):>5}"
              f"{st.mean(post) - st.mean(ctrl):>+12.2f}{len(post):>5}")

    if drops:
        print(f"\n  dropped (weekend D-1, holes, missing endpoints):")
        for et, dd in sorted(drops.items()):
            print(f"    {et:<5} " + ", ".join(f"{k}={v}"
                                              for k, v in sorted(dd.items(),
                                                                 key=str)[:4]))

    print(f"\n  AGAINST THE REGISTERED PREDICTIONS (v14 section 4)")
    for et in ("FOMC", "CPI", "NFP"):
        if et not in res:
            continue
        lo, hi = PRED[et]
        print(f"    {et:<5} predicted {lo:+.0f}..{hi:+.0f}   "
              f"measured {res[et]:+7.2f}   "
              f"{'HELD' if lo <= res[et] <= hi else 'MISSED'}")

    print(f"\n  THE FALSIFICATION CONDITION (v14 section 5)")
    cpi = res.get("CPI")
    if cpi is None:
        print(f"    CPI not measurable -- cannot be evaluated")
    elif cpi > FALSIFY_CPI_BP:
        print(f"    CPI {cpi:+.2f} EXCEEDS +{FALSIFY_CPI_BP:.0f}.")
        print(f"    The FOMC finding is NOT FOMC-specific. RESULT_KUROV")
        print(f"    section 7 is wrong and Gate E must be re-derived, not")
        print(f"    merely restated. This needs its own pre-registration")
        print(f"    before anyone believes it.")
    else:
        print(f"    CPI {cpi:+.2f} is below the +{FALSIFY_CPI_BP:.0f} "
              f"threshold.")
        print(f"    The day-before session does not pay for CPI, so the")
        print(f"    FOMC effect stays FOMC-specific and Gate E's FAIL")
        print(f"    survives being re-asked on the right segment.")

    for et, d in res.items():
        if abs(d) > SANITY_MAX_BP:
            print(f"\n    KILL: {et} {d:+.2f} exceeds {SANITY_MAX_BP:.0f} bp")
            sys.exit(3)
    print(f"\n  v14 section 7: this measures one segment and touches no "
          f"cost.\n  A null here says this segment does not pay for CPI, "
          f"not that none does.")


if __name__ == "__main__":
    main()
