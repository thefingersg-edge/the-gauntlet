#!/usr/bin/env python3
"""ARM 1 of PREREGISTRATION_v11 -- the 45 minutes RESULT_PREANN excluded.

RESULT_PREANN measured T-24h -> T-1h. Kurov, Wolfe & Gilbert measure to
about T-15m. This measures the interval in between, and ONLY that
interval:

    SEGMENT   T-60m -> T-15m     3 bars at M15
              entry: OPEN of the bar starting at T-60m
              exit:  CLOSE of the bar starting at T-30m

**It is disjoint from the window already measured.** It abuts it. So the
two add to reconstruct T-24h -> T-15m, nothing is double counted, and no
window length is being swept -- which is what would make this a fishing
expedition rather than a reconciliation.

THE DANGER, NAMED IN v11 SECTION 6
----------------------------------
This puts a measurement 15 minutes from an announcement -- closer than
anything else in this project. An error in the release timestamp of one
bar would drag the reaction into the segment and read as a large, clean,
spurious result. So:

  * events flagged UNCERTAIN are excluded outright;
  * no bar in the segment may be stamped at or after T-15m, checked per
    event, and the run is VOID if any is;
  * T-15m -> T and the T -> T+1h reaction are measured alongside as
    diagnostics. If the segment looks like the reaction rather than like
    the window, that is contamination, not a finding.

STDLIB ONLY.

    python3 preann_segment.py --self-test
    python3 preann_segment.py
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

#: ---- FROZEN IN PREREGISTRATION_v11 SECTION 4 ----
SEG_FROM = dt.timedelta(minutes=60)     # T-60m
SEG_TO = dt.timedelta(minutes=15)       # T-15m
SEG_BARS = 3
#: diagnostics, v11 section 6
LAST15_BARS = 1
REACTION = dt.timedelta(minutes=60)
REACTION_BARS = 4
#: v11 section 6: two thirds of Lucca & Moench's whole 24h figure earned
#: in 45 minutes is a bug until proven otherwise.
SANITY_MAX_BP = 30.0
#: v11 section 5's registered expectation. Printed with the result so
#: the comparison cannot be quietly restated afterwards.
PREDICTED_MAX_BP = 15.0
RECONCILE_FROM, RECONCILE_TO = 2013, 2015
KUROV_BP = 44.50
MINE_BP = 0.36


def release_utc(date_iso, time_et):
    d = dt.date.fromisoformat(date_iso)
    hh, mm = (int(x) for x in time_et.split(":"))
    return dt.datetime(d.year, d.month, d.day, hh, mm,
                       tzinfo=ET).astimezone(UTC)


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
             for t in common}, len(b), len(a), len(common))


def interval_return(bars, keys, t0, t1):
    """Return over [t0, t1): entry at the OPEN of the bar starting t0,
    exit at the CLOSE of the bar starting t1-BAR.

    EVERY bar in between must be present -- a segment this short cannot
    be allowed to span a hole. Returns (bp, n_bars, last_bar_start) or
    (None, reason, None).
    """
    want = int((t1 - t0) / BAR)
    if want < 1:
        return None, "empty interval", None
    last = t1 - BAR
    if t0 not in bars or last not in bars:
        return None, "missing endpoint bar", None
    i = bisect.bisect_left(keys, t0)
    j = bisect.bisect_right(keys, last)
    n = j - i
    if n != want:
        return None, f"holed: {n} bars, wanted {want}", None
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


def one_sample_t(x):
    if len(x) < 2:
        return None
    s = st.stdev(x)
    return None if s == 0 else st.mean(x) / (s / math.sqrt(len(x)))


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"preann_segment.py v{VERSION} self-test\n")

    print("the timezone -- an hour of error puts the segment past T")
    w = release_utc("2015-01-28", "14:00")
    s = release_utc("2015-06-17", "14:00")
    check("January 14:00 ET is 19:00 UTC", w.hour == 19, f"{w}")
    check("June 14:00 ET is 18:00 UTC", s.hour == 18, f"{s}")
    check("an 08:30 release converts too",
          release_utc("2020-03-06", "08:30").hour == 13)

    print("\nthe segment lands where v11 section 4 says")
    T = release_utc("2015-06-17", "14:00")
    bars = {}
    t = T - dt.timedelta(hours=3)
    i = 0
    while t <= T + dt.timedelta(hours=3):
        bars[t] = (100.0 + i * 0.01, 100.0 + i * 0.01 + 0.004)
        t += BAR
        i += 1
    keys = sorted(bars)
    r, n, last = interval_return(bars, keys, T - SEG_FROM, T - SEG_TO)
    check(f"the segment is exactly {SEG_BARS} bars", n == SEG_BARS, f"{n}")
    check("it starts at T-60m",
          (T - SEG_FROM) == T - dt.timedelta(minutes=60))
    check("the last bar used starts at T-30m",
          last == T - dt.timedelta(minutes=30), f"{last}")
    #: PLANTED: the kill condition. Nothing may touch T-15m.
    check("the last bar CLOSES exactly at T-15m",
          last + BAR == T - SEG_TO)
    check("no bar used is at or after T-15m", last < T - SEG_TO)
    check("and none is anywhere near T", last + BAR < T)

    print("\nthe diagnostics are the right shape")
    _, n15, _ = interval_return(bars, keys, T - SEG_TO, T)
    _, nrx, lrx = interval_return(bars, keys, T, T + REACTION)
    check(f"T-15m -> T is {LAST15_BARS} bar", n15 == LAST15_BARS, f"{n15}")
    check(f"the reaction is {REACTION_BARS} bars", nrx == REACTION_BARS)
    check("the reaction starts AT T, not before", lrx >= T)

    print("\nholes are refused, not spanned")
    holed = {k: v for k, v in bars.items() if k != T - dt.timedelta(minutes=45)}
    r2, why, _ = interval_return(holed, sorted(holed), T - SEG_FROM, T - SEG_TO)
    check("one missing middle bar voids the segment", r2 is None, str(why))
    noend = {k: v for k, v in bars.items() if k != T - dt.timedelta(minutes=30)}
    check("a missing exit bar voids it",
          interval_return(noend, sorted(noend), T - SEG_FROM,
                          T - SEG_TO)[0] is None)
    nostart = {k: v for k, v in bars.items() if k != T - SEG_FROM}
    check("a missing entry bar voids it",
          interval_return(nostart, sorted(nostart), T - SEG_FROM,
                          T - SEG_TO)[0] is None)

    print("\nthe arithmetic")
    flat = {T - SEG_FROM + BAR * i: (100.0, 100.0) for i in range(8)}
    check("a flat market reads 0 bp",
          abs(interval_return(flat, sorted(flat), T - SEG_FROM,
                              T - SEG_TO)[0]) < 1e-9)
    up = dict(flat)
    up[T - SEG_FROM] = (100.0, 100.0)
    up[T - dt.timedelta(minutes=30)] = (100.0, 100.45)
    check("a 0.45% rise reads 45 bp",
          abs(interval_return(up, sorted(up), T - SEG_FROM,
                              T - SEG_TO)[0] - 45.0) < 1e-6,
          f"{interval_return(up, sorted(up), T-SEG_FROM, T-SEG_TO)[0]:.2f}")
    #: PLANTED: the bisect count must equal a brute-force count, or the
    #: hole detection is decorative.
    brute = sum(1 for k in bars
                if T - SEG_FROM <= k <= T - dt.timedelta(minutes=30))
    check("the fast bar count equals a brute-force one",
          brute == SEG_BARS, f"{brute}")

    print("\nstatistics")
    t1, d = welch_t([1.0] * 30 + [3.0] * 30, [0.0] * 30 + [2.0] * 30)
    check("a 1.0 difference gives t>2", t1 > 2.0 and abs(d - 1.0) < 1e-9)
    check("identical samples give t=0",
          abs(welch_t([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])[0]) < 1e-9)

    print("\nthe registered prediction is in the file, not in the retelling")
    check("v11 predicted the segment is under 15 bp",
          PREDICTED_MAX_BP == 15.0)
    check("and above 30 bp is a bug until proven otherwise",
          SANITY_MAX_BP == 30.0)

    print("\nthis file holds no position and fits nothing")
    import preann_segment as _self
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
    ap.add_argument("--dump", default=None)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"preann_segment.py v{VERSION}   ARM 1 -- PREREGISTRATION_v11\n")
    print(f"  segment T-60m -> T-15m on M15, disjoint from RESULT_PREANN's")
    print(f"  window. Frozen before any segment return was looked at.\n")

    bars, nb, na, nc = load_bars(a.bid, a.ask)
    keys = sorted(bars)
    print(f"  bars: bid {nb:,}  ask {na:,}  aligned {nc:,}")

    ev = [r for r in csv.DictReader(open(a.events))
          if r["event"] == "FOMC" and r["time_quality"] != "UNCERTAIN"
          and r["time_et"]]
    print(f"  FOMC events with a usable time: {len(ev)}")

    seg, l15, rxn = [], [], []
    violations, drops = 0, {}
    for r in ev:
        T = release_utc(r["date"], r["time_et"])
        s, n, last = interval_return(bars, keys, T - SEG_FROM, T - SEG_TO)
        if s is None:
            drops[n] = drops.get(n, 0) + 1
            continue
        if last + BAR > T - SEG_TO:                  # v11 section 6
            violations += 1
            continue
        d = dt.date.fromisoformat(r["date"])
        seg.append((d, s))
        x, _, _ = interval_return(bars, keys, T - SEG_TO, T)
        if x is not None:
            l15.append(x)
        y, _, _ = interval_return(bars, keys, T, T + REACTION)
        if y is not None:
            rxn.append(y)

    print(f"\n  KILL CHECK -- bars at or after T-15m: {violations} "
          f"({'OK' if violations == 0 else 'RUN IS VOID'})")
    if violations:
        sys.exit(3)
    if drops:
        print(f"  dropped: " + ", ".join(f"{k}={v}"
                                         for k, v in sorted(drops.items())[:5]))

    #: The control: the same clock segment on non-event days. Built the
    #: way RESULT_PREANN built its own, so the two are comparable --
    #: the release time of the FIRST usable event of this type.
    tm = ev[0]["time_et"]
    all_ev = {dt.date.fromisoformat(r["date"])
              for r in csv.DictReader(open(a.events))}
    near = {d + dt.timedelta(days=k) for d in all_ev for k in (-1, 0, 1)}
    ctrl, seen = [], set()
    for k in keys:
        d = k.astimezone(ET).date()
        if d in near or d in seen:
            continue
        seen.add(d)
        T = release_utc(d.isoformat(), tm)
        c, _, lc = interval_return(bars, keys, T - SEG_FROM, T - SEG_TO)
        if c is not None:
            ctrl.append(c)
    print(f"  control: {len(ctrl):,} non-event days at {tm} ET")

    vals = [x[1] for x in seg]
    t, diff = welch_t(vals, ctrl)
    print(f"\n  ARM 1 RESULT")
    print(f"    {'sample':<22}{'n':>5}{'mean bp':>10}{'median':>9}"
          f"{'ctrl':>8}{'excess':>9}{'t':>7}")
    print("    " + "-" * 60)
    print(f"    {'all measurable':<22}{len(vals):>5}{st.mean(vals):>10.2f}"
          f"{st.median(vals):>9.2f}{st.mean(ctrl):>8.2f}{diff:>9.2f}{t:>7.2f}")
    rec = [v for d, v in seg if RECONCILE_FROM <= d.year <= RECONCILE_TO]
    if len(rec) >= 2:
        tr, dr = welch_t(rec, ctrl)
        print(f"    {f'{RECONCILE_FROM}-{RECONCILE_TO} (the shared block)':<22}"
              f"{len(rec):>5}{st.mean(rec):>10.2f}{st.median(rec):>9.2f}"
              f"{st.mean(ctrl):>8.2f}{dr:>9.2f}{tr:>7.2f}")

    print(f"\n  DIAGNOSTICS -- v11 section 6. Is this the window or the "
          f"reaction?")
    print(f"    segment   T-60m -> T-15m   n={len(seg):>3}  "
          f"mean {st.mean(vals):+8.2f} bp  sd {st.stdev(vals):6.1f}")
    if l15:
        print(f"    last 15m  T-15m -> T      n={len(l15):>3}  "
              f"mean {st.mean(l15):+8.2f} bp  sd {st.stdev(l15):6.1f}")
    if rxn:
        print(f"    REACTION  T -> T+1h       n={len(rxn):>3}  "
              f"mean {st.mean(rxn):+8.2f} bp  sd {st.stdev(rxn):6.1f}")
        rel = st.stdev(vals) / st.stdev(rxn)
        print(f"    the segment's spread is {rel:.2f}x the reaction's."
              + ("  A segment resembling the reaction would mean the"
                 if rel > 0.7 else ""))
        if rel > 0.7:
            print(f"    release timestamp is wrong -- v11 voids the arm.")

    print(f"\n  AGAINST THE REGISTERED PREDICTION (v11 section 5)")
    print(f"    predicted: under {PREDICTED_MAX_BP:.0f} bp, and therefore "
          f"NOT the explanation")
    m = st.mean(vals)
    print(f"    measured:  {m:+.2f} bp on all events, "
          f"{st.mean(rec) if rec else float('nan'):+.2f} on {RECONCILE_FROM}-"
          f"{RECONCILE_TO}")
    print(f"    -> the prediction "
          f"{'HELD' if abs(m) < PREDICTED_MAX_BP else 'FAILED'}")
    gap = KUROV_BP - MINE_BP
    closed = st.mean(rec) if rec else 0.0
    print(f"\n    the gap to reconcile is {gap:.2f} bp "
          f"({KUROV_BP:.2f} - {MINE_BP:.2f})")
    print(f"    arm 1 accounts for {closed:+.2f} bp of it "
          f"({100*closed/gap:+.1f}%)")

    if abs(m) > SANITY_MAX_BP:
        print(f"\n    KILL: {m:+.2f} bp exceeds the {SANITY_MAX_BP:.0f} bp "
              f"bound. v11 section 6 treats this as a")
        print(f"    timestamp fault, not a discovery. Investigate first.")
        sys.exit(3)

    if a.dump:
        with open(a.dump, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["date", "segment_bp"])
            for d, v in sorted(seg):
                w.writerow([d.isoformat(), f"{v:.4f}"])
        print(f"\n  written to {a.dump}")
    print("\n  Arm 2 (the 14 excluded 2011-2012 events) is separate and "
          "needs a\n  Federal Reserve source before it may run at all.")


if __name__ == "__main__":
    main()
