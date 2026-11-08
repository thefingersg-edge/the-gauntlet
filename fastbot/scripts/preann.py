#!/usr/bin/env python3
"""PHASE 1 for PREREGISTRATION_v10.1 -- the pre-announcement window.

Every threshold here is copied from that document, which was frozen
before any price was joined to events.csv. None of them may move. If a
gate needs changing to produce a result, the run is abandoned and
recorded as abandoned -- v10 section 6.

WHAT IS MEASURED (v10 section 3)
--------------------------------
For each event, the return on SPX500_USD from T - 24 hours to T - 1 hour,
where T is that event's release timestamp, on M15 bars.

    entry   the OPEN of the bar starting at T - 24h
    exit    the CLOSE of the bar starting at T - 1h15m, which ends at T-1h

Ending a full hour before the release is more conservative than Lucca &
Moench's fifteen minutes and buys robustness against timestamp error --
the failure this whole intraday choice exposes the measurement to.

THE PART THAT WILL BREAK IT IF IT IS WRONG
------------------------------------------
**The timezone.** events.csv carries Eastern release times. OANDA stamps
bars in UTC. Eastern is UTC-5 in winter and UTC-4 in summer, and the
changeover dates move. An hour of error puts the window's tail INSIDE the
announcement and turns a measurement of anticipation into a measurement
of reaction -- which would read as a large, clean, completely spurious
result.

So the conversion uses zoneinfo, not an offset constant, and the self-test
plants both sides of a DST boundary. The kill condition in section 6 --
no bar in the window at or after T -- is then checked PER EVENT rather
than trusted from the construction.

STDLIB ONLY. No pandas, no numpy.

    python3 preann.py --self-test
    python3 preann.py
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

VERSION = "1.2"

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
BAR = dt.timedelta(minutes=15)

#: ---- FROZEN IN PREREGISTRATION_v10.1 ----
WINDOW_START = dt.timedelta(hours=24)
WINDOW_END = dt.timedelta(hours=1)
GATE_A_T = 2.0
GATE_C_MIN_EVENTS = 120
GATE_D_T = 1.5
GATE_E_MIN_TYPES = 2
N_ERAS = 3
#: The window runs [T-24h, T-1h15m] inclusive, which is 22.75 hours of
#: bar starts: 22.75/0.25 + 1 = 92 bars, NOT the 96 a full day would
#: hold. Fewer than MIN_BARS and the window is holed -- a weekend, a
#: holiday, or a data gap -- and it is dropped rather than stretched
#: across the hole.
MIN_BARS = 80
FULL_BARS = 92
#: v10 section 6: a result materially above the published 49bp means the
#: window has crept past T and is eating the reaction.
SANITY_MAX_BP = 70.0
#: Gate D's conditioning variable may go stale over a long holiday, but
#: not by a week. Beyond this the event is dropped from Gate D rather
#: than conditioned on a number from another regime.
MAX_VIX_STALE_DAYS = 6


def release_utc(date_iso, time_et):
    """The release instant, in UTC.

    An offset constant would be wrong for half the year and catastrophic
    in the two weeks a year when the US and Europe disagree about DST.
    """
    d = dt.date.fromisoformat(date_iso)
    hh, mm = (int(x) for x in time_et.split(":"))
    naive = dt.datetime(d.year, d.month, d.day, hh, mm)
    return naive.replace(tzinfo=ET).astimezone(UTC)


def load_bars(path_bid, path_ask):
    """{utc datetime -> (open_mid, close_mid)}. Mid computed here.

    pull_m1.py's --derive-mid needs pandas, which is not installed. It is
    not needed: the mid is (bid+ask)/2 and this file can do that itself
    while it reads, which also means bid and ask are never silently
    assumed to align -- a timestamp present in one and not the other is
    counted and reported.
    """
    def rd(p):
        out = {}
        with open(p) as fh:
            for r in csv.DictReader(fh):
                t = dt.datetime.fromisoformat(r["time"]).replace(tzinfo=UTC)
                out[t] = (float(r["open"]), float(r["close"]))
        return out
    b, a = rd(path_bid), rd(path_ask)
    common = b.keys() & a.keys()
    bars = {t: ((b[t][0] + a[t][0]) / 2.0, (b[t][1] + a[t][1]) / 2.0)
            for t in common}
    return bars, len(b), len(a), len(common)


def window_return(bars, t_rel):
    """Return over [T-24h, T-1h], or (None, reason).

    Returns (ret_bp, n_bars, last_bar_start).
    """
    start = t_rel - WINDOW_START
    end_bar = t_rel - WINDOW_END - BAR      # its close lands on T-1h
    if start not in bars:
        return None, "no bar at T-24h", None
    if end_bar not in bars:
        return None, "no bar ending at T-1h", None
    n = sum(1 for k in bars if start <= k <= end_bar)
    if n < MIN_BARS:
        return None, f"only {n} bars", None
    o = bars[start][0]
    c = bars[end_bar][1]
    if not o or not c:
        return None, "zero price", None
    return (c / o - 1.0) * 1e4, n, end_bar


def window_open_et_date(t_rel):
    """The Eastern calendar date on which the window opens."""
    return (t_rel - WINDOW_START).astimezone(ET).date()


def vix_asof(vix_dates, vix, open_date):
    """The last VIX close STRICTLY BEFORE the window opens.

    v10 section 5 fixes Gate D's split at "the VIX as of the close
    before the window opens -- strictly lagged, no exceptions", and
    section 6 voids the run on any lookahead.

    The window opens at T-24h. For an 08:30 or a 14:00 ET release that
    instant falls DURING the previous session -- hours before its 16:15
    close. So D-1's own VIX close is INSIDE the window and must not be
    used. v1.1 used it, preferring D-1 and only falling back to D-2 when
    D-1 was missing; that was a 2h15m peek into the interval being
    measured.

    This takes the latest close on a date strictly earlier than the
    window-open date -- normally D-2 for a D-dated event, skipping
    holidays backwards, never forwards.

    Returns (value, date_used) or (None, None).
    """
    i = bisect.bisect_left(vix_dates, open_date)
    if i == 0:
        return None, None
    d = vix_dates[i - 1]
    if (open_date - d).days > MAX_VIX_STALE_DAYS:
        return None, None
    return vix[d], d


def welch_t(x, y):
    """Two-sample t on the difference of means. Stdlib only."""
    if len(x) < 2 or len(y) < 2:
        return None, None
    mx, my = st.mean(x), st.mean(y)
    vx, vy = st.variance(x), st.variance(y)
    se = math.sqrt(vx / len(x) + vy / len(y))
    if se == 0:
        return None, None
    return (mx - my) / se, mx - my


def one_sample_t(x):
    if len(x) < 2:
        return None
    s = st.stdev(x)
    return None if s == 0 else st.mean(x) / (s / math.sqrt(len(x)))


def eras(seq, n=N_ERAS):
    """Disjoint, contiguous thirds. NOT nested -- AUDIT.md section 3."""
    k = len(seq) // n
    return [seq[i * k:(i + 1) * k if i < n - 1 else len(seq)]
            for i in range(n)]


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"preann.py v{VERSION} self-test\n")

    print("the timezone conversion -- the one that would fake a result")
    #: PLANTED: both sides of a DST boundary. An offset constant gets one
    #: of these wrong by an hour, which puts the window's tail inside the
    #: announcement and reads as a large, clean, spurious effect.
    win = release_utc("2015-01-28", "14:00")
    sum_ = release_utc("2015-06-17", "14:00")
    check("a January 14:00 ET is 19:00 UTC (EST, -5)",
          win.hour == 19 and win.tzinfo == UTC, f"{win}")
    check("a June 14:00 ET is 18:00 UTC (EDT, -4)",
          sum_.hour == 18, f"{sum_}")
    check("the two differ by an hour in UTC -- an offset constant cannot "
          "do both", win.hour - sum_.hour == 1)
    check("an 08:30 BLS release converts too",
          release_utc("2020-03-06", "08:30").hour == 13,
          f"{release_utc('2020-03-06','08:30')}")
    #: the changeover weekend itself
    check("the Sunday DST switch is handled",
          release_utc("2021-03-15", "14:00").hour == 18
          and release_utc("2021-03-12", "14:00").hour == 19)

    print("\nthe window lands where v10 section 3 says")
    T = release_utc("2015-06-17", "14:00")
    bars = {}
    t = T - WINDOW_START
    i = 0
    while t <= T + dt.timedelta(hours=2):
        bars[t] = (100.0 + i * 0.01, 100.0 + i * 0.01 + 0.005)
        t += BAR
        i += 1
    r, n, last = window_return(bars, T)
    check(f"the window holds exactly {FULL_BARS} bars, not 96",
          n == FULL_BARS, f"{n} bars -- 22.75h of starts at 15m")
    check("and the LAST bar used ends exactly at T-1h",
          last + BAR == T - WINDOW_END, f"{last} + 15m")
    #: PLANTED: the kill condition. No bar in the window may touch T.
    check("no bar used is at or after T", last < T)
    check("the last bar is a full hour before the release",
          (T - (last + BAR)) == dt.timedelta(hours=1))

    print("\nholed windows are dropped, not stretched")
    holed = {k: v for k, v in bars.items()
             if not (T - dt.timedelta(hours=12) < k
                     < T - dt.timedelta(hours=4))}
    r2, why, _ = window_return(holed, T)
    check("a window missing 8 hours is refused", r2 is None, str(why))
    missing_start = {k: v for k, v in bars.items()
                     if k != T - WINDOW_START}
    check("no bar at T-24h is refused",
          window_return(missing_start, T)[0] is None)
    missing_end = {k: v for k, v in bars.items()
                   if k != T - WINDOW_END - BAR}
    check("no bar ending at T-1h is refused",
          window_return(missing_end, T)[0] is None)

    print("\nthe arithmetic")
    flat = {T - WINDOW_START + BAR * i: (100.0, 100.0) for i in range(96)}
    check("a flat market returns 0 bp",
          abs(window_return(flat, T)[0]) < 1e-9)
    up = dict(flat)
    up[T - WINDOW_START] = (100.0, 100.0)
    up[T - WINDOW_END - BAR] = (100.0, 100.5)
    check("a 0.5% rise reads 50 bp",
          abs(window_return(up, T)[0] - 50.0) < 1e-6,
          f"{window_return(up, T)[0]:.2f}")

    print("\nstatistics")
    t1, d = welch_t([1.0] * 30 + [3.0] * 30, [0.0] * 30 + [2.0] * 30)
    check("a 1.0 difference with equal spread gives t>2",
          t1 > 2.0 and abs(d - 1.0) < 1e-9, f"t={t1:.2f}")
    check("identical samples give t=0",
          abs(welch_t([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])[0]) < 1e-9)
    check("one-sample t on centred data is 0",
          abs(one_sample_t([-1.0, 0.0, 1.0])) < 1e-9)

    print("\neras are disjoint (AUDIT.md section 3)")
    e = eras(list(range(30)))
    check("three eras", len(e) == 3)
    check("they do not overlap",
          not (set(e[0]) & set(e[1])) and not (set(e[1]) & set(e[2])))
    check("and they cover everything",
          sorted(sum(e, [])) == list(range(30)))
    #: PLANTED: nested windows are the failure AUDIT.md named -- one event
    #: counted three times. Disjoint eras cannot do that.
    check("no era is a prefix of the whole", e[0] != list(range(30)))

    print("\nGate D's lag -- the close before the window OPENS, not D-1")
    #: PLANTED: v1.1 preferred D-1's close. The window opens at 14:00 ET
    #: on D-1 and D-1's VIX prints at 16:15 ET -- 2h15m INSIDE it. If
    #: this check ever passes with vd == D-1 the run is lookahead.
    Tj = release_utc("2015-06-17", "14:00")
    wj = window_open_et_date(Tj)
    check("the window opens on D-1, not on the event day",
          wj == dt.date(2015, 6, 16), f"{wj}")
    vfix = {dt.date(2015, 6, 15): 13.0,
            dt.date(2015, 6, 16): 14.0,     # inside the window
            dt.date(2015, 6, 17): 99.0}     # the event day itself
    v_, vd_ = vix_asof(sorted(vfix), vfix, wj)
    check("D-1's own close is REFUSED -- it prints inside the window",
          vd_ == dt.date(2015, 6, 15) and v_ == 13.0, f"used {vd_} = {v_}")
    check("the event day's close is unreachable", vd_ < wj)
    #: a holiday at D-2 must fall back, never forward
    vhol = {dt.date(2015, 6, 12): 11.0, dt.date(2015, 6, 16): 14.0}
    check("a missing D-2 falls back to D-5, not forward to D-1",
          vix_asof(sorted(vhol), vhol, wj)[1] == dt.date(2015, 6, 12))
    #: and an 08:30 release opens on D-1 too, so the same rule holds
    w830 = window_open_et_date(release_utc("2015-06-05", "08:30"))
    check("an 08:30 release also opens its window on D-1",
          w830 == dt.date(2015, 6, 4), f"{w830}")
    #: staleness
    vold = {dt.date(2015, 5, 1): 11.0}
    check(f"a gap over {MAX_VIX_STALE_DAYS} days drops the event",
          vix_asof(sorted(vold), vold, wj)[0] is None)
    check("an empty series returns nothing rather than raising",
          vix_asof([], {}, wj)[0] is None)
    #: exhaustive: no date on or after the open may EVER be selected
    span = sorted(dt.date(2015, 6, 1) + dt.timedelta(days=i)
                  for i in range(30))
    vall = {d: 10.0 + i for i, d in enumerate(span)}
    bad = [d for d in span[3:]
           if (vix_asof(span, vall, d)[1] or dt.date.min) >= d]
    check("across 27 planted opens, none selects a date >= the open",
          bad == [], f"{len(bad)} violations")

    print("\nthis file holds no position and fits nothing")
    import preann as _self
    banned = ("sweep", "optimi", "tune", "grid", "refit", "order",
              "submit", "position")
    check("no fitting or trading function exists",
          [x for x in dir(_self) if not x.startswith("_")
           and any(w in x.lower() for w in banned)] == [])

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def load_vix(path):
    out = {}
    if not os.path.exists(path):
        return out
    with open(path) as fh:
        for r in csv.reader(fh):
            if len(r) < 2:
                continue
            try:
                out[dt.date.fromisoformat(r[0].strip())] = float(r[1])
            except (ValueError, IndexError):
                continue
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="../data/events.csv")
    ap.add_argument("--bid", default="../data/spx500usd_bid_15m.csv")
    ap.add_argument("--ask", default="../data/spx500usd_ask_15m.csv")
    ap.add_argument("--vix", default="../data/VIXCLS.csv")
    ap.add_argument("--dump", default=None,
                    help="write per-event window returns to CSV")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"preann.py v{VERSION}   PHASE 1 -- PREREGISTRATION_v10.1\n")
    print(f"  window T-24h to T-1h on M15   Gate A t>={GATE_A_T}   "
          f"Gate C {GATE_C_MIN_EVENTS}   Gate D t>={GATE_D_T}")
    print("  Frozen before any price was joined. One run.\n")

    bars, nb, na, nc = load_bars(a.bid, a.ask)
    lo, hi = min(bars), max(bars)
    print(f"  bars: bid {nb:,}  ask {na:,}  aligned {nc:,}  "
          f"({nb - nc:,} unmatched)")
    print(f"  span: {lo:%Y-%m-%d %H:%M} -> {hi:%Y-%m-%d %H:%M} UTC")

    ev = [r for r in csv.DictReader(open(a.events))
          if r["time_quality"] != "UNCERTAIN" and r["time_et"]]
    print(f"  events with a usable time: {len(ev)}")

    #: Per-event windows, and the kill-condition check per event.
    got = {}
    drops = {}
    violations = 0
    for r in ev:
        T = release_utc(r["date"], r["time_et"])
        ret, n, last = window_return(bars, T)
        if ret is None:
            drops[n] = drops.get(n, 0) + 1
            continue
        if last >= T:                       # v10 section 6
            violations += 1
            continue
        got.setdefault(r["event"], []).append(
            (dt.date.fromisoformat(r["date"]), ret, T))
    print(f"\n  KILL CHECK -- bars at or after T: {violations} "
          f"({'OK' if violations == 0 else 'RUN IS VOID'})")
    if violations:
        sys.exit(3)
    print(f"  dropped windows: "
          + ", ".join(f"{k}={v}" for k, v in sorted(drops.items())[:6]))

    #: The CONTROL uses the SAME clock window on non-event days. A window
    #: spanning an overnight plus a morning has its own intraday drift,
    #: so comparing it to a whole-day return would compare two different
    #: things and call the difference an effect.
    all_ev_dates = {dt.date.fromisoformat(r["date"])
                    for r in csv.DictReader(open(a.events))}
    near = set()
    for d in all_ev_dates:
        for k in (-1, 0, 1):
            near.add(d + dt.timedelta(days=k))

    print(f"\n  {'event':<6}{'N':>5}{'mean bp':>10}{'ctrl bp':>10}"
          f"{'excess':>9}{'t':>7}")
    print("  " + "-" * 50)
    results = {}
    for etype, rows in sorted(got.items()):
        tm = ev[0]["time_et"]
        tm = next(r["time_et"] for r in ev if r["event"] == etype)
        ctrl = []
        seen = set()
        for k in bars:
            d = k.astimezone(ET).date()
            if d in near or d in seen:
                continue
            seen.add(d)
            T = release_utc(d.isoformat(), tm)
            c, _, lastc = window_return(bars, T)
            if c is not None and lastc < T:
                ctrl.append(c)
        vals = [x[1] for x in rows]
        t, diff = welch_t(vals, ctrl)
        results[etype] = (rows, vals, ctrl, t, diff)
        print(f"  {etype:<6}{len(vals):>5}{st.mean(vals):>10.2f}"
              f"{st.mean(ctrl):>10.2f}{diff:>9.2f}{t:>7.2f}")

    print(f"\n  VERDICT -- gates frozen in PREREGISTRATION_v10.1 section 5")
    rows, vals, ctrl, t, diff = results.get("FOMC", ([], [], [], None, None))
    ga = t is not None and t >= GATE_A_T
    print(f"    [{'PASS' if ga else 'FAIL'}] Gate A  FOMC excess "
          f"{diff:+.2f} bp, t = {t:.2f}" if t else "    [N/A ] Gate A")

    rows_sorted = sorted(rows)
    ee = eras([x[1] for x in rows_sorted])
    era_means = [st.mean(e) - st.mean(ctrl) for e in ee if e]
    gb = all(m > 0 for m in era_means)
    print(f"    [{'PASS' if gb else 'FAIL'}] Gate B  eras "
          + "  ".join(f"{m:+.2f}" for m in era_means))

    gc = len(vals) >= GATE_C_MIN_EVENTS
    print(f"    [{'PASS' if gc else 'FAIL'}] Gate C  {len(vals)} events "
          f"(need {GATE_C_MIN_EVENTS})")

    vix = load_vix(a.vix)
    if not vix:
        print(f"    [N/A ] Gate D  no VIX at {a.vix} -- download VIXCLS")
        gd = None
    else:
        vix_dates = sorted(vix)
        pairs, lags, peeks, stale = [], {}, 0, 0
        for d, r, T in rows_sorted:
            w_open = window_open_et_date(T)
            v, vd = vix_asof(vix_dates, vix, w_open)
            if v is None:
                stale += 1
                continue
            if vd >= w_open:                # v10 section 6 -- lookahead
                peeks += 1
                continue
            lags[(d - vd).days] = lags.get((d - vd).days, 0) + 1
            pairs.append((v, r))
        if peeks:
            print(f"\n    KILL: {peeks} events used a VIX close at or "
                  f"after the window opened.")
            sys.exit(3)
        med = st.median([v for v, _ in pairs])
        hi_ = [r for v, r in pairs if v >= med]
        lo_ = [r for v, r in pairs if v < med]
        td, dd = welch_t(hi_, lo_)
        gd = td is not None and td >= GATE_D_T
        print(f"    [{'PASS' if gd else 'FAIL'}] Gate D  high-VIX minus "
              f"low-VIX {dd:+.2f} bp, t = {td:.2f}  (median VIX {med:.1f})")
        #: Printed as evidence, not asserted. The window opens on D-1
        #: DURING that session, so a lag of 1 day would be a peek and
        #: must not appear here.
        print(f"           n={len(pairs)} hi={len(hi_)} lo={len(lo_)}"
              + (f"  {stale} dropped for stale VIX" if stale else "")
              + "   lag D-n: "
              + " ".join(f"{k}d x{v}" for k, v in sorted(lags.items())))

    pos = [e for e, (_, v, c, tt, dd) in results.items() if dd and dd > 0]
    ge = len(pos) >= GATE_E_MIN_TYPES
    print(f"    [{'PASS' if ge else 'FAIL'}] Gate E  positive on "
          f"{len(pos)} of {len(results)}: {', '.join(sorted(pos)) or 'none'}")

    if diff and abs(diff) > SANITY_MAX_BP:
        print(f"\n    KILL: {diff:+.2f} bp exceeds the {SANITY_MAX_BP:.0f} "
              f"bp sanity bound.")
        print("    v10 section 6 treats this as the window having crept "
              "past T,")
        print("    not as a discovery. Investigate before reporting.")
        sys.exit(3)

    allp = all(x for x in (ga, gb, gc, ge) if x is not None)
    print(f"\n    {'PROCEED' if allp else 'FAIL'}")

    #: ---- CAVEATS, not gates. -------------------------------------
    #: The verdict above is settled. Nothing below can change it, and
    #: none of it was chosen after seeing the number: reporting the
    #: distribution behind a mean is what RESULT_KRAKENBASIS_v7 did when
    #: two ETF quarters turned out to carry half its result, and the mean
    #: survived that check only barely. A mean is not a finding until you
    #: know how few observations made it.
    if rows_sorted:
        print(f"\n  CONCENTRATION -- caveat reporting, not a gate")
        v = sorted(vals, reverse=True)
        base = st.mean(vals) - st.mean(ctrl)
        for k in (1, 3, 5, 10):
            kept = sorted(vals, reverse=True)[k:]
            print(f"    drop the top {k:>2} event(s):  "
                  f"{st.mean(kept) - st.mean(ctrl):+7.2f} bp   "
                  f"(from {base:+.2f})")
        print(f"    median event {st.median(vals):+.2f} bp vs mean "
              f"{st.mean(vals):+.2f} -- a mean far above its median is "
              f"carried by a tail")
        print(f"    positive events: "
              f"{sum(1 for x in vals if x > 0)}/{len(vals)}")

        print(f"\n  BY PERIOD -- disjoint, and this is the era test's detail")
        buckets = {}
        for d, r, _T in rows_sorted:
            b = f"{(d.year // 4) * 4}-{(d.year // 4) * 4 + 3}"
            buckets.setdefault(b, []).append(r)
        for b in sorted(buckets):
            xs = buckets[b]
            print(f"    {b}  n={len(xs):>3}  mean {st.mean(xs):+8.2f} bp"
                  f"   median {st.median(xs):+7.2f}")

    if a.dump:
        with open(a.dump, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["event", "date", "window_bp",
                        "window_open_et", "vix_date_used", "vix"])
            vix_dates_d = sorted(vix) if vix else []
            for etype, rr in sorted(got.items()):
                for d, r, T in sorted(rr):
                    w_open = window_open_et_date(T)
                    v, vd = (vix_asof(vix_dates_d, vix, w_open)
                             if vix_dates_d else (None, None))
                    w.writerow([etype, d.isoformat(), f"{r:.4f}",
                                w_open.isoformat(),
                                vd.isoformat() if vd else "",
                                f"{v:.2f}" if v is not None else ""])
        print(f"\n  per-event returns written to {a.dump}")
    print("\n  This measures anticipation, not tradeability. v10 section 7:")
    print("  nothing here touches costs, and four of four earlier "
          "candidates")
    print("  died there rather than on the premium.")
    sys.exit(0 if allp else 2)


if __name__ == "__main__":
    main()
