#!/usr/bin/env python3
"""PREREGISTRATION_v12 -- Kurov, Wolfe & Gilbert's window, transcribed.

    "from the stock market open on the day before the announcement to
     15 minutes before the announcement"

That sentence is the whole specification. It is implemented literally:

    entry   the OPEN of the 09:30 ET bar on D-1
    exit    the CLOSE of the bar ending at T-15m

v11 banned sweeping over window length and that ban stands. This is not
a sweep: the window was fixed by someone else, in print, years ago, and
this file was written before it was run. A sweep has many candidates and
reports the best; this has one and reports it.

WHAT IS ALREADY KNOWN, SO THIS CANNOT BE READ BACKWARDS
-------------------------------------------------------
    arm 1   the tail T-60m -> T-15m          -2.94 bp   (measured)
    arm 2   the 14 recovered 2011-2012        +29.00    (measured)
    v11.1   the same 20 announcements        +12.72     (measured)
    theirs                                   +44.50
    v12 predicts the head is worth under 10 bp and that this lands
    near +20 -- roughly halfway, not all the way.

STDLIB ONLY.

    python3 preann_replicate.py --self-test
    python3 preann_replicate.py
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

#: ---- FROZEN IN PREREGISTRATION_v12 SECTION 3 ----
OPEN_ET = dt.time(9, 30)
TAIL = dt.timedelta(minutes=15)
MIN_BARS = 60
SANITY_MAX_BP = 70.0
#: v12 section 4, registered before the run.
PREDICTED_HEAD_MAX_BP = 10.0
PREDICTED_TOTAL_BP = 20.0
THEIRS_PC_BP, THEIRS_PC_N = 44.50, 20
THEIRS_NOPC_BP, THEIRS_NOPC_N = -5.10, 30
#: already measured, printed alongside so the arithmetic is visible
V11_PC_BP = 12.72


def release_utc(date_iso, time_et):
    d = dt.date.fromisoformat(date_iso)
    hh, mm = (int(x) for x in time_et.split(":"))
    return dt.datetime(d.year, d.month, d.day, hh, mm,
                       tzinfo=ET).astimezone(UTC)


def prev_open_utc(release_utc_dt):
    """09:30 ET on the calendar day before the announcement, in UTC.

    Built through zoneinfo from the Eastern date, so the DST offset is
    whatever was actually in force that morning -- not the one in force
    at the release, which can differ across a changeover weekend.
    """
    d = release_utc_dt.astimezone(ET).date() - dt.timedelta(days=1)
    return dt.datetime.combine(d, OPEN_ET, tzinfo=ET).astimezone(UTC)


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


def interval_return(bars, keys, t0, t1):
    """Entry at the OPEN of the bar starting t0, exit at the CLOSE of
    the bar starting t1-BAR. Returns (bp, n_bars, last) or (None, why,
    None)."""
    last = t1 - BAR
    if t1 <= t0:
        return None, "empty interval", None
    if t0 not in bars:
        return None, "no bar at the entry", None
    if last not in bars:
        return None, "no bar at the exit", None
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

    print(f"preann_replicate.py v{VERSION} self-test\n")

    print("09:30 ET on D-1, through zoneinfo, on both sides of DST")
    T = release_utc("2015-06-17", "14:00")
    p = prev_open_utc(T)
    check("a June D-1 open is 13:30 UTC (EDT)", p.hour == 13, f"{p}")
    check("and lands on the calendar day before",
          p.astimezone(ET).date() == dt.date(2015, 6, 16))
    Tw = release_utc("2015-01-28", "14:00")
    pw = prev_open_utc(Tw)
    check("a January D-1 open is 14:30 UTC (EST)", pw.hour == 14, f"{pw}")
    check("the two differ by an hour -- an offset constant cannot do both",
          pw.hour - p.hour == 1)
    #: PLANTED: the changeover weekend. The release and the previous
    #: day's open can sit on OPPOSITE sides of a DST switch, so the
    #: offset must come from the D-1 date, not from the release.
    Td = release_utc("2015-03-09", "14:00")
    check("a Monday release after the Sunday switch still finds D-1",
          prev_open_utc(Td).astimezone(ET).date() == dt.date(2015, 3, 8))
    check("D-1 is always exactly one calendar day before",
          all((release_utc(d, "14:00").astimezone(ET).date()
               - prev_open_utc(release_utc(d, "14:00")).astimezone(ET).date())
              == dt.timedelta(days=1)
              for d in ("2011-11-02", "2013-03-20", "2015-12-16")))
    #: a 12:30 release must use the same D-1 open, not a shifted one
    check("a 12:30 release uses the same 09:30 D-1 open",
          prev_open_utc(release_utc("2011-11-02", "12:30"))
          == prev_open_utc(release_utc("2011-11-02", "14:15")))

    print("\nthe window ends 15 minutes before, and never touches T")
    bars, t, i = {}, T - dt.timedelta(hours=30), 0
    while t <= T + dt.timedelta(hours=2):
        bars[t] = (100.0 + i * 0.001, 100.0 + i * 0.001 + 0.0005)
        t += BAR
        i += 1
    keys = sorted(bars)
    r, n, last = interval_return(bars, keys, prev_open_utc(T), T - TAIL)
    check("the last bar CLOSES exactly at T-15m", last + BAR == T - TAIL)
    check("no bar used is at or after T-15m", last < T - TAIL)
    check("nor anywhere near T", last + BAR < T)
    check("the window spans 09:30 D-1 to T-15m",
          n == int((T - TAIL - prev_open_utc(T)) / BAR), f"{n} bars")
    check("which for a 14:00 release is 28.25 hours",
          abs((T - TAIL - prev_open_utc(T)).total_seconds() / 3600
              - 28.25) < 1e-9)

    print("\nrefusals")
    noent = {k: v for k, v in bars.items() if k != prev_open_utc(T)}
    check("a missing D-1 09:30 bar is dropped, not shifted",
          interval_return(noent, sorted(noent), prev_open_utc(T),
                          T - TAIL)[0] is None)
    noex = {k: v for k, v in bars.items() if k != T - TAIL - BAR}
    check("a missing exit bar is dropped",
          interval_return(noex, sorted(noex), prev_open_utc(T),
                          T - TAIL)[0] is None)
    thin = {k: v for k, v in bars.items()
            if k >= T - dt.timedelta(hours=4) or k == prev_open_utc(T)}
    check("a holed window is refused",
          interval_return(thin, sorted(thin), prev_open_utc(T),
                          T - TAIL)[0] is None)

    print("\nthe arithmetic")
    flat = {prev_open_utc(T) + BAR * k: (100.0, 100.0) for k in range(200)}
    fk = sorted(flat)
    check("a flat market reads 0 bp",
          abs(interval_return(flat, fk, prev_open_utc(T),
                              T - TAIL)[0]) < 1e-9)
    up = dict(flat)
    up[prev_open_utc(T)] = (100.0, 100.0)
    up[T - TAIL - BAR] = (100.0, 100.445)
    check("a 0.445% rise reads 44.5 bp -- their own figure",
          abs(interval_return(up, sorted(up), prev_open_utc(T),
                              T - TAIL)[0] - 44.5) < 1e-6,
          f"{interval_return(up, sorted(up), prev_open_utc(T), T-TAIL)[0]:.2f}")

    print("\nthe predictions are in the file, not in the retelling")
    check("v12 predicted the head is worth under 10 bp",
          PREDICTED_HEAD_MAX_BP == 10.0)
    check("and the total near +20, short of their +44.5",
          PREDICTED_TOTAL_BP == 20.0 and THEIRS_PC_BP == 44.50)
    check("the already-measured figure is carried, not re-derived",
          V11_PC_BP == 12.72)

    print("\nthis file holds no position and fits nothing")
    import preann_replicate as _self
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

    print(f"preann_replicate.py v{VERSION}   PREREGISTRATION_v12\n")
    print(f'  "from the stock market open on the day before the '
          f'announcement')
    print(f'   to 15 minutes before the announcement"  -- transcribed, '
          f'not chosen\n')

    bars, nc = load_bars(a.bid, a.ask)
    keys = sorted(bars)
    print(f"  bars aligned: {nc:,}")

    #: Release times: sourced overlay for 2011-2012, events.csv after.
    times = {}
    for r in csv.DictReader(open(a.events)):
        if r["event"] != "FOMC":
            continue
        tm, pc, src = A2.resolve_time(r["date"])
        if tm:
            times[r["date"]] = tm
        elif r["time_quality"] != "UNCERTAIN" and r["time_et"]:
            times[r["date"]] = r["time_et"]

    def measure(dates):
        out, drop = [], {}
        for d in sorted(dates):
            if d not in times:
                drop["no sourced release time"] = \
                    drop.get("no sourced release time", 0) + 1
                continue
            T = release_utc(d, times[d])
            v, n, last = interval_return(bars, keys, prev_open_utc(T),
                                         T - TAIL)
            if v is None:
                drop[n] = drop.get(n, 0) + 1
                continue
            if last + BAR > T - TAIL:
                print(f"    KILL: {d} used a bar at or after T-15m")
                sys.exit(3)
            out.append((d, v, n))
        return out, drop

    pc = [d for d in A2.PRESSER_ALL if "2011-04-01" <= d <= "2015-12-31"]
    nopc = [r["date"] for r in csv.DictReader(open(a.events))
            if r["event"] == "FOMC"
            and A2.NOPC_FROM <= r["date"] <= A2.NOPC_TO
            and r["date"] not in A2.PRESSER_ALL]
    got_pc, drop_pc = measure(pc)
    got_no, drop_no = measure(nopc)

    #: control: the same clock window on non-event days, 14:00 release
    all_ev = {dt.date.fromisoformat(r["date"])
              for r in csv.DictReader(open(a.events))}
    near = {d + dt.timedelta(days=k) for d in all_ev for k in (-1, 0, 1)}
    ctrl, seen = [], set()
    for k in keys:
        d = k.astimezone(ET).date()
        if d in near or d in seen:
            continue
        seen.add(d)
        T = release_utc(d.isoformat(), "14:00")
        c, _, lc = interval_return(bars, keys, prev_open_utc(T), T - TAIL)
        if c is not None:
            ctrl.append(c)

    print(f"  control: {len(ctrl):,} non-event days\n")
    print(f"  THEIR WINDOW, ON THEIR SAMPLES")
    print(f"    {'sample':<30}{'n':>8}{'mean':>9}{'median':>9}{'SE':>7}"
          f"{'theirs':>9}{'SE away':>9}")
    print("    " + "-" * 71)
    res = {}
    for lab, got, exp, theirs in (
            ("with press conference 11-15", got_pc, THEIRS_PC_N,
             THEIRS_PC_BP),
            ("without, 2011-04..2018-12", got_no, THEIRS_NOPC_N,
             THEIRS_NOPC_BP)):
        if len(got) < 2:
            print(f"    {lab:<30}{len(got):>8} too few")
            continue
        v = [x[1] for x in got]
        se = st.stdev(v) / math.sqrt(len(v))
        res[lab] = st.mean(v)
        print(f"    {lab:<30}{f'{len(got)}/{exp}':>8}{st.mean(v):>+9.2f}"
              f"{st.median(v):>+9.2f}{se:>7.2f}{theirs:>+9.2f}"
              f"{(theirs-st.mean(v))/se:>+9.2f}")
    if drop_pc or drop_no:
        print(f"\n    dropped: pc {dict(drop_pc)}  no-pc {dict(drop_no)}")

    if got_pc:
        v = [x[1] for x in got_pc]
        t, diff = welch_t(v, ctrl)
        print(f"\n    vs control: {diff:+.2f} bp, t = {t:.2f}  "
              f"(control mean {st.mean(ctrl):+.2f})")
        bars_n = [x[2] for x in got_pc]
        print(f"    bars per window: {min(bars_n)}-{max(bars_n)} "
              f"(median {int(st.median(bars_n))})")

    print(f"\n  WHERE THE DIFFERENCE WENT")
    m = res.get("with press conference 11-15")
    if m is not None:
        head = m - V11_PC_BP
        print(f"    my window   T-24h -> T-1h      {V11_PC_BP:+7.2f} bp")
        print(f"    their window 09:30 D-1 -> T-15m {m:+7.2f} bp")
        print(f"    the difference (head + tail)    {head:+7.2f} bp")
        print(f"    theirs                          {THEIRS_PC_BP:+7.2f} bp")
        print(f"    STILL UNEXPLAINED               "
              f"{THEIRS_PC_BP - m:+7.2f} bp")
        print(f"\n  AGAINST THE REGISTERED PREDICTION (v12 section 4)")
        print(f"    predicted the head under {PREDICTED_HEAD_MAX_BP:.0f} bp"
              f"    measured {head:+.2f}  -> "
              f"{'HELD' if abs(head) < PREDICTED_HEAD_MAX_BP else 'FAILED'}")
        print(f"    predicted the total near {PREDICTED_TOTAL_BP:+.0f} bp"
              f"   measured {m:+.2f}")
        print(f"    predicted it would still fall short of "
              f"{THEIRS_PC_BP:+.1f}  -> "
              f"{'HELD' if m < THEIRS_PC_BP - 5 else 'FAILED'}")
        if abs(m) > SANITY_MAX_BP:
            print(f"\n    KILL: {m:+.2f} exceeds the {SANITY_MAX_BP:.0f} bp "
                  f"bound -- investigate before reporting.")
            sys.exit(3)
    print(f"\n  The instrument remains E-mini futures against an OANDA "
          f"CFD, and\n  nothing here can close that. v12 section 6 says "
          f"that is where to stop.")


if __name__ == "__main__":
    main()
