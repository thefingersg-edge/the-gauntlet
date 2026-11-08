#!/usr/bin/env python3
"""PHASE 1, STAGE 1 for PREREGISTRATION_v5 -- carry against realised drift.

WHAT THIS IS, AND WHAT IT IS NOT
--------------------------------
Gate 0 credited each pair with its entire net differential and charged it
NOTHING for spot drift. RESULT_FXCARRY_P0 recorded why that is fatal on the
lira crosses: the carry trade in EUR_TRY is to be SHORT the pair -- to buy
lira -- collecting 22.3% a year while the lira falls against the euro. The
gate's denominator is the standard deviation of log returns, which excludes
the mean drift entirely, so a currency in one-way structural decline scores
a spectacular ratio while losing money every quarter.

This file measures the second component: what the spot leg actually did, in
the direction the carry puts you.

    total  =  (|D| - m)  +  drift in the carry direction

It is NOT the backtest. It pairs TODAY's differential with HISTORICAL
drift, and those belong to different periods. Where a currency's rate and
its depreciation are both driven by the same inflation -- the lira being
the case in point -- the mismatch is small and the answer is close to
arithmetic. Where they are not, this is a sanity bound and the full Phase 1
with historical differentials is what settles it.

It can move the estimate in EITHER direction. Favourable drift raises the
total. This is not a filter that only rejects; it is the half of Phase 1
that needs no data that is not already available.

THE SIGN IS THE WHOLE DIFFICULTY. If D < 0 the carry side is SHORT, and a
RISING price is then adverse. Getting that backwards flips every conclusion
on half the universe, so it is planted and tested below.

    python fx_drift_bound.py --self-test
    python fx_drift_bound.py --manifest ../data/fx_carry.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fx_carry_probe as P                                   # noqa: E402

VERSION = "1.2"

WINDOWS = [("full", None), ("10y", 10), ("5y", 5), ("3y", 3), ("1y", 1)]
MIN_DAYS = 200
#: A window labelled "1y" must END at the present or the label is a lie.
MAX_STALE_DAYS = 10
MAX_STALE_SHARE = 0.20
N_ERAS = 3
#: PREREGISTRATION_v5 section 5. The same bar DESIGN_BRIEF has used
#: throughout; here applied to total/vol, which is a Sharpe proxy for an
#: unlevered notional and is generous because it charges no spread.
BAR = 0.40


def series_from(rows):
    """(date, close) pairs out of whatever shape fetch_oanda returns.

    closes_from() in fx_carry_probe discards the timestamp, which is fine
    for a volatility estimate and useless for slicing by window. Same
    discover-rather-than-assume approach, extended to the time field.
    """
    import datetime as dt
    out = []
    for r in rows:
        t = c = None
        if isinstance(r, dict):
            t = r.get("time", r.get("t", r.get("date")))
            c = (r.get("close") if "close" in r else
                 r.get("c") if "c" in r else
                 (r.get("mid") or {}).get("c"))
        elif isinstance(r, (list, tuple)) and len(r) >= 5:
            t, c = r[0], r[4]
        if t is None or c is None:
            continue
        try:
            c = float(c)
        except (TypeError, ValueError):
            continue
        if c <= 0:
            continue
        d = None
        if isinstance(t, dt.datetime):
            d = t.date()
        elif isinstance(t, dt.date):
            d = t
        elif isinstance(t, (int, float)):
            v = float(t)
            if v > 1e11:                      # milliseconds
                v /= 1000.0
            try:
                d = dt.datetime.utcfromtimestamp(v).date()
            except (OverflowError, OSError, ValueError):
                continue
        else:
            s = str(t).strip().replace("Z", "+00:00")
            try:
                d = dt.datetime.fromisoformat(s).date()
            except ValueError:
                try:
                    d = dt.date.fromisoformat(s[:10])
                except ValueError:
                    continue
        if d is not None:
            out.append((d, c))
    out.sort(key=lambda x: x[0])
    return out


def is_fresh(series, today, max_age_days=MAX_STALE_DAYS):
    """Does the series actually reach the present?

    v1.0 requested count=5000 from a start twenty years back, and OANDA
    returns the FIRST 5000 candles from that point -- not the most recent
    5000. Every pair with more than 5000 days of history therefore ended
    in late 2023, and every window label was silently wrong: the column
    headed "1y" was 2022-11 to 2023-11, and the "full" history stopped
    almost three years before the run.

    Worse, the whole file pairs TODAY's differential with that drift, and
    the missing stretch contains the August 2024 yen carry unwind -- the
    single most relevant episode for this trade in the entire sample.

    The tell was in the output and I did not have a gate for it: USD_CNH
    was the only pair reaching 2026, and it was the only one with fewer
    than 5000 bars, so the cap never bound on it.
    """
    if not series:
        return False, None
    age = (today - series[-1][0]).days
    return age <= max_age_days, age


def pull_series(fo, host, token, instrument, start, pause=0.15,
                page=5000, max_pages=12):
    """Daily closes from `start` to the present, paginating forward.

    A single request is capped, so one call cannot span twenty years.
    Walks the cursor to the last bar received and asks again until a short
    page arrives or nothing new comes back.
    """
    import datetime as dt
    import time
    out, cursor = [], start
    for _ in range(max_pages):
        payload = fo.api_get(
            fo.build_url(host, instrument, "D", "M", cursor, count=page),
            token)
        rows = series_from(fo.parse_candles(payload, "M"))
        new = [r for r in rows if not out or r[0] > out[-1][0]]
        if not new:
            break
        out.extend(new)
        cursor = dt.datetime.combine(
            out[-1][0] + dt.timedelta(days=1), dt.time(),
            tzinfo=dt.timezone.utc)
        if len(rows) < page * 0.8:
            break
        time.sleep(pause)
    return out


def carry_side(D):
    """+1 long, -1 short. You take whichever side the financing pays."""
    return 1 if D > 0 else -1


def era_slices(series, n=N_ERAS):
    """DISJOINT thirds of the sample, by calendar time.

    WINDOWS above are NESTED -- full, 10y, 5y, 3y and 1y all end today and
    each contains the next. "Positive in all five" therefore sounds like
    five independent confirmations and is nothing of the kind: a pair with
    one spectacular recent year and a flat decade before it can be positive
    in every one of them, because the good year is inside all five.

    PREREGISTRATION_v5 Gate B asks for the sign to hold in every ERA, and
    an era is disjoint. That is a far harder test and it is the one the
    pre-registration actually specified.
    """
    import datetime as dt
    if len(series) < MIN_DAYS * n:
        return []
    d0, d1 = series[0][0], series[-1][0]
    step = (d1 - d0).days / n
    out = []
    for k in range(n):
        a = d0 + dt.timedelta(days=int(k * step))
        b = d0 + dt.timedelta(days=int((k + 1) * step))
        sub = [x for x in series if a <= x[0] <= b]
        out.append((f"{a:%Y}-{b:%Y}", sub))
    return out


def drift(series, years=None):
    """Annualised log drift of the PRICE, and the span actually used.

    Returned as the price's own drift, sign-neutral. Applying the position
    direction is the caller's job and is where the error would be.
    """
    import datetime as dt
    if len(series) < MIN_DAYS:
        return None, None
    s = series
    if years:
        cutoff = series[-1][0] - dt.timedelta(days=int(years * 365.25))
        s = [x for x in series if x[0] >= cutoff]
        if len(s) < MIN_DAYS:
            return None, None
    span = (s[-1][0] - s[0][0]).days / 365.25
    if span <= 0:
        return None, None
    return math.log(s[-1][1] / s[0][1]) / span, span


def total_return(D, m, g, side=None):
    """Net carry plus drift IN THE DIRECTION THE CARRY PUTS YOU.

    side is derived from D unless given. A short position earns -g, so a
    pair with a negative differential and a rising price is losing on both
    legs at once -- which is precisely the lira case, and precisely what
    Gate 0 could not see.
    """
    if g is None:
        return None
    s = carry_side(D) if side is None else side
    return (abs(D) - m) + s * g


def breakeven(D, m):
    """The annual drift that exactly cancels the net carry.

    Signed as the PRICE move that would do it, so it can be compared with
    the measured drift directly.
    """
    return -carry_side(D) * (abs(D) - m)


def assess(rows):
    """Per-pair totals across every window. Pure, so it can be tested."""
    out = []
    for r in rows:
        rec = dict(instrument=r["instrument"], D=r["D"], m=r["m"],
                   vol=r.get("vol"), net=abs(r["D"]) - r["m"],
                   side=carry_side(r["D"]),
                   breakeven=breakeven(r["D"], r["m"]), windows={})
        for name, yrs in WINDOWS:
            g, span = drift(r.get("series") or [], yrs)
            rec["windows"][name] = dict(
                drift=g, span=span,
                total=total_return(r["D"], r["m"], g))
        rec["eras"] = []
        for label, sub in era_slices(r.get("series") or []):
            g, _ = drift(sub)
            rec["eras"].append((label, total_return(r["D"], r["m"], g)))
        full = rec["windows"]["full"]["total"]
        rec["ratio"] = (full / r["vol"]) if (full is not None
                                            and r.get("vol")) else None
        era_t = [t for _, t in rec["eras"]]
        rec["gate_b"] = bool(era_t) and all(
            t is not None and t > 0 for t in era_t)
        rec["gate_a"] = bool(rec["ratio"] is not None
                             and rec["ratio"] >= BAR)
        out.append(rec)
    return out


def report(recs):
    print(f"\n  {'pair':<10}{'side':>6}{'net carry':>11}{'breakeven':>11}"
          + "".join(f"{n:>9}" for n, _ in WINDOWS))
    print("  " + "-" * (38 + 9 * len(WINDOWS)))
    for r in recs:
        line = (f"  {r['instrument']:<10}"
                f"{'long' if r['side'] > 0 else 'short':>6}"
                f"{r['net']*100:>10.2f}%{r['breakeven']*100:>10.2f}%")
        for n, _ in WINDOWS:
            g = r["windows"][n]["drift"]
            line += (f"{g*100:>8.1f}%" if g is not None else f"{'--':>9}")
        print(line)

    print(f"\n  TOTAL = net carry + drift in the carry direction")
    print(f"  {'pair':<10}" + "".join(f"{n:>10}" for n, _ in WINDOWS)
          + "   verdict")
    print("  " + "-" * (10 + 10 * len(WINDOWS) + 12))
    for r in recs:
        line = f"  {r['instrument']:<10}"
        tots = []
        for n, _ in WINDOWS:
            t = r["windows"][n]["total"]
            tots.append(t)
            line += (f"{t*100:>9.1f}%" if t is not None else f"{'--':>10}")
        good = [t for t in tots if t is not None]
        if not good:
            v = "no data"
        elif all(t > 0 for t in good):
            v = "positive in all"
        elif all(t <= 0 for t in good):
            v = "NEGATIVE in all"
        else:
            v = "mixed"
        print(line + f"   {v}")

    labels = [l for l, _ in recs[0]["eras"]] if recs and recs[0]["eras"] \
        else []
    if labels:
        print(f"\n  DISJOINT ERAS -- the nested windows above are not five "
              f"independent looks")
        print(f"  {'pair':<10}{'total/vol':>11}"
              + "".join(f"{l:>12}" for l in labels)
              + f"{'A':>4}{'B':>4}")
        print("  " + "-" * (21 + 12 * len(labels) + 8))
        for r in sorted(recs, key=lambda x: -(x["ratio"] or -9)):
            line = (f"  {r['instrument']:<10}"
                    + (f"{r['ratio']:>11.2f}" if r["ratio"] is not None
                       else f"{'--':>11}"))
            for _, t in r["eras"]:
                line += (f"{t*100:>11.1f}%" if t is not None
                         else f"{'--':>12}")
            line += f"{'ok' if r['gate_a'] else '.':>4}"
            line += f"{'ok' if r['gate_b'] else '.':>4}"
            print(line)
        both = [r for r in recs if r["gate_a"] and r["gate_b"]]
        print(f"\n  A = total/vol >= {BAR:.2f} on the full sample "
              f"({sum(1 for r in recs if r['gate_a'])} of {len(recs)})")
        print(f"  B = positive in EVERY disjoint era "
              f"({sum(1 for r in recs if r['gate_b'])} of {len(recs)})")
        print(f"  both: {len(both) or 'NONE'}"
              + (f"  -- {', '.join(r['instrument'] for r in both)}"
                 if both else ""))

    print("\n  READ THIS AS A BOUND, NOT A BACKTEST. It pairs TODAY's")
    print("  differential with HISTORICAL drift. Where a currency's rate "
          "and its")
    print("  depreciation share one cause -- inflation -- the mismatch is "
          "small.")
    print("  Where they do not, only the full Phase 1 with historical")
    print("  differentials settles it.")
    return recs


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    import datetime as dt
    print(f"fx_drift_bound.py v{VERSION} self-test\n")

    print("the carry side follows the sign of the differential")
    check("a positive differential is held LONG", carry_side(0.03) == 1)
    check("a negative differential is held SHORT", carry_side(-0.03) == -1)

    print("\nthe direction is applied to drift, and this is the easy error")
    #: EUR_TRY exactly: D negative so the carry side is SHORT, collecting
    #: 22.3%. The PRICE rises 35%/yr as the lira falls. Short a rising
    #: price loses. Getting the sign backwards would report +57%.
    t = total_return(-0.2966 - 0.0, 0.0735, 0.35)
    check("short a RISING price loses on both legs",
          abs(t - (0.2231 - 0.35)) < 1e-9, f"{t*100:+.2f}%/yr")
    check("the sign error would have reported the opposite",
          abs((0.2231 + 0.35) - 0.5731) < 1e-9,
          "flipping it gives +57.3%, which is the mistake to avoid")
    #: and the mirror: long a rising price with a positive differential
    t2 = total_return(0.0449, 0.0106, 0.02)
    check("long a rising price gains on both legs",
          abs(t2 - (0.0343 + 0.02)) < 1e-9, f"{t2*100:+.2f}%/yr")
    t3 = total_return(0.0449, 0.0106, -0.02)
    check("long a falling price gives back part of the carry",
          abs(t3 - (0.0343 - 0.02)) < 1e-9, f"{t3*100:+.2f}%/yr")

    print("\nfavourable drift RAISES the total -- this is not a one-way "
          "filter")
    check("a short position with a falling price beats its carry",
          total_return(-0.03, 0.01, -0.05) > (0.03 - 0.01),
          f"{total_return(-0.03, 0.01, -0.05)*100:+.1f}% vs a 2.0% carry")

    print("\nbreakeven is the drift that exactly cancels the carry")
    b = breakeven(-0.2966, 0.0735)
    check("a short's breakeven is a POSITIVE price move",
          abs(b - 0.2231) < 1e-9, f"{b*100:+.2f}%")
    check("and total is exactly zero at breakeven",
          abs(total_return(-0.2966, 0.0735, b)) < 1e-12)
    b2 = breakeven(0.0449, 0.0106)
    check("a long's breakeven is a NEGATIVE price move",
          abs(b2 + 0.0343) < 1e-9, f"{b2*100:+.2f}%")
    check("and total is zero there too",
          abs(total_return(0.0449, 0.0106, b2)) < 1e-12)

    print("\ndrift is annualised, and windows are honoured")
    base = dt.date(2016, 1, 1)
    #: exactly 10% a year for ten years
    ser = [(base + dt.timedelta(days=k), 100.0 * math.exp(0.10 * k / 365.25))
           for k in range(0, 3653)]
    g, span = drift(ser)
    check("a 10%/yr series measures 10%", abs(g - 0.10) < 1e-6,
          f"{g*100:.4f}% over {span:.1f}y")
    g5, span5 = drift(ser, 5)
    check("the 5-year window sees 5 years", abs(span5 - 5.0) < 0.02,
          f"{span5:.2f}y")
    check("and the same drift, since it is constant",
          abs(g5 - 0.10) < 1e-6, f"{g5*100:.4f}%")
    #: planted: a series with a REGIME CHANGE must show different drifts
    ser2 = ser[:1827] + [(d, p * math.exp(-0.30 * (i) / 365.25))
                         for i, (d, p) in enumerate(ser[1827:])]
    ga, _ = drift(ser2)
    gb, _ = drift(ser2, 3)
    check("a regime change shows up as different windows",
          abs(ga - gb) > 0.10, f"full {ga*100:.1f}% vs 3y {gb*100:.1f}%")
    check("too little history is None, not zero",
          drift(ser[:50])[0] is None)
    check("an empty series is None, not zero", drift([])[0] is None)

    print("\nthe candle shape is discovered, timestamps included")
    d0 = dt.date(2024, 1, 2)
    check("positional rows parse",
          series_from([(1704153600, 1, 1, 1, 1.25, 0)])[0][1] == 1.25)
    check("an ISO string parses",
          series_from([{"time": "2024-01-02T00:00:00Z",
                        "mid": {"c": "1.25"}}]) == [(d0, 1.25)])
    check("milliseconds are detected",
          series_from([{"time": 1704153600000, "close": 1.25}])[0][1] == 1.25)
    check("rows are sorted by date",
          [d for d, _ in series_from([
              {"time": "2024-01-03", "close": 2.0},
              {"time": "2024-01-02", "close": 1.0}])]
          == [dt.date(2024, 1, 2), dt.date(2024, 1, 3)])
    check("an unparseable row is dropped, not guessed",
          series_from([{"time": "not-a-date", "close": 1.0},
                       object(), {"close": 1.0}]) == [])

    print("\nthe series must REACH THE PRESENT, or every window label lies")
    today = dt.date(2026, 8, 19)
    fresh_ser = [(today - dt.timedelta(days=k), 100.0) for k in range(400)]
    fresh_ser.sort()
    ok_f, age_f = is_fresh(fresh_ser, today)
    check("a series ending today is fresh", ok_f, f"age {age_f}d")
    #: EXACTLY what v1.0 returned: count=5000 from twenty years back gives
    #: the FIRST 5000 candles, so everything with deep history stopped in
    #: late 2023 and the column headed "1y" was 2022-11 to 2023-11.
    stale_ser = [(dt.date(2023, 11, 1) - dt.timedelta(days=k), 100.0)
                 for k in range(400)]
    stale_ser.sort()
    ok_s, age_s = is_fresh(stale_ser, today)
    check("the v1.0 truncation is CAUGHT", not ok_s,
          f"ends 2023-11-01, stale by {age_s} days")
    check("a weekend or holiday gap is tolerated",
          is_fresh([(today - dt.timedelta(days=4), 1.0)], today)[0])
    check("an empty series is not silently fresh",
          not is_fresh([], today)[0])
    #: the drift function cannot see the problem -- it happily annualises a
    #: window that ended three years ago, which is why the gate is separate
    g_stale, span_stale = drift(
        [(dt.date(2020, 1, 1) + dt.timedelta(days=k),
          100.0 * math.exp(0.05 * k / 365.25)) for k in range(1400)], 1)
    check("drift() alone reports a clean 1y number on stale data",
          g_stale is not None and abs(g_stale - 0.05) < 1e-6,
          "which is why freshness is checked separately")

    print("\nthe full assessment, on the three cases that matter")
    def mk(name, D, m, g):
        n = 2000
        ser = [(dt.date(2016, 1, 1) + dt.timedelta(days=k),
                100.0 * math.exp(g * k / 365.25)) for k in range(n)]
        return dict(instrument=name, D=D, m=m, vol=0.18, series=ser)
    recs = assess([mk("EUR_TRY", -0.2966, 0.0735, 0.35),
                   mk("GBP_CHF", 0.0399, 0.0107, -0.01),
                   mk("GOOD", 0.05, 0.01, 0.02)])
    by = {r["instrument"]: r for r in recs}
    check("the lira case is NEGATIVE despite a 22% carry",
          by["EUR_TRY"]["windows"]["full"]["total"] < 0,
          f"{by['EUR_TRY']['windows']['full']['total']*100:+.1f}%/yr")
    check("a modest adverse drift only dents a real carry",
          0 < by["GBP_CHF"]["windows"]["full"]["total"] < 0.0292 + 1e-9,
          f"{by['GBP_CHF']['windows']['full']['total']*100:+.2f}%/yr")
    check("favourable drift exceeds the carry alone",
          by["GOOD"]["windows"]["full"]["total"] > 0.04,
          f"{by['GOOD']['windows']['full']['total']*100:+.2f}%/yr")

    print("\nnested windows are not disjoint eras (sec 5, Gate B)")
    #: Planted so the two views DISAGREE, which the first attempt failed
    #: to do: a flat series with one good year kept every era positive
    #: because the carry alone carried them, proving nothing. This one has
    #: a genuinely bad middle stretch (-5%/yr against a +1.5% carry) and a
    #: spectacular final year. Every NESTED window contains that year, so
    #: full/10y/5y/3y/1y all read positive; the middle disjoint era does
    #: not.
    n = 20 * 365

    def seg(yr):
        if yr < 6.7:
            return 0.02
        if yr < 13.3:
            return -0.05
        return 0.60 if yr >= 19.0 else 0.03
    px, p = [], 100.0
    for k in range(n):
        p *= math.exp(seg(k / 365.25) / 365.25)
        px.append((dt.date(2006, 8, 24) + dt.timedelta(days=k), p))
    r = assess([dict(instrument="SPIKE", D=0.02, m=0.005, vol=0.10,
                     series=px)])[0]
    nested = [r["windows"][nm]["total"] for nm, _ in WINDOWS]
    check("all five NESTED windows are positive",
          all(t is not None and t > 0 for t in nested),
          " ".join(f"{t*100:+.1f}" for t in nested))
    check("but a disjoint era is not, so Gate B FAILS",
          not r["gate_b"],
          " ".join(f"{t*100:+.1f}" for _, t in r["eras"]))
    check("three eras, and they do not overlap",
          len(r["eras"]) == N_ERAS,
          " ".join(l for l, _ in r["eras"]))
    #: and a genuinely steady pair passes both
    steady = [(dt.date(2006, 8, 24) + dt.timedelta(days=k),
               100.0 * math.exp(0.03 * k / 365.25)) for k in range(n)]
    r2 = assess([dict(instrument="STEADY", D=0.02, m=0.005, vol=0.10,
                      series=steady)])[0]
    check("a steady pair passes Gate B", r2["gate_b"],
          " ".join(f"{t*100:+.1f}" for _, t in r2["eras"]))
    check("Gate A is total/vol against the bar",
          abs(r2["ratio"] - (0.015 + 0.03) / 0.10) < 1e-6
          and r2["gate_a"], f"{r2['ratio']:.2f}")
    #: and a pair that clears B but not A must not be reported as both
    r3 = assess([dict(instrument="THIN", D=0.02, m=0.005, vol=0.40,
                      series=steady)])[0]
    check("a thin ratio fails Gate A even with a perfect era record",
          r3["gate_b"] and not r3["gate_a"], f"{r3['ratio']:.2f}")

    print("\nthis file places NO orders")
    import fx_drift_bound as _self
    banned = ("order", "execute", "submit", "buy", "sell")
    def scan():
        return [x for x in dir(_self) if not x.startswith("_")
                and any(w in x.lower() for w in banned)]
    check("no order / execute / submit function", scan() == [], f"{scan()}")
    setattr(_self, "submit_order", lambda: None)
    fired = scan() == ["submit_order"]
    delattr(_self, "submit_order")
    check("and the detector demonstrably FIRES when one is added",
          fired and scan() == [])

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="../data/fx_carry.json")
    ap.add_argument("--fetch-oanda-dir", default=P.DEFAULT_FO_DIR)
    ap.add_argument("--env", default="live", choices=("live", "practice"))
    ap.add_argument("--min-ratio", type=float, default=P.GATE_0_RATIO,
                    help="Gate 0 survivors; use 0 to assess every FX pair")
    ap.add_argument("--pause", type=float, default=0.15)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    import time
    from datetime import datetime, timedelta, timezone
    man = json.load(open(os.path.expanduser(a.manifest)))
    rows = [r for r in man["rows"]
            if r.get("fx") and r.get("ratio") is not None
            and r["ratio"] >= a.min_ratio]
    if not rows:
        raise SystemExit(f"  no pairs at ratio >= {a.min_ratio}")

    print(f"fx_drift_bound.py v{VERSION}   PHASE 1 STAGE 1 -- "
          f"CARRY vs REALISED DRIFT\n")
    print(f"  {len(rows)} pair(s) at carry-to-vol >= {a.min_ratio:.2f}")

    fo = P.load_fo(a.fetch_oanda_dir)
    host, token = fo.HOSTS[a.env], fo.load_token()
    start = datetime.now(timezone.utc) - timedelta(days=365 * 20)
    today = datetime.now(timezone.utc).date()
    stale = []
    for r in rows:
        try:
            r["series"] = pull_series(fo, host, token, r["instrument"],
                                      start, a.pause)
        except Exception as exc:                              # noqa: BLE001
            print(f"    {r['instrument']:<12} FAIL "
                  f"{fo.redact(str(exc), token)[:50]}")
            r["series"] = []
        fresh, age = is_fresh(r["series"], today)
        if r["series"]:
            print(f"    {r['instrument']:<12} {len(r['series']):>5} days  "
                  f"{r['series'][0][0]} -> {r['series'][-1][0]}"
                  + ("" if fresh else f"   STALE by {age} days"))
        if not fresh:
            stale.append(r["instrument"])
            r["series"] = []
        time.sleep(a.pause)

    if stale:
        print(f"\n  {len(stale)} of {len(rows)} series do not reach the "
              f"present and are EXCLUDED:")
        print("    " + ", ".join(stale[:12])
              + (" ..." if len(stale) > 12 else ""))
        if len(stale) > MAX_STALE_SHARE * len(rows):
            raise SystemExit(
                f"\n  STOP: {len(stale)}/{len(rows)} stale. That is the "
                f"pull, not the instruments.\n  Every window label would "
                f"be wrong -- a column headed '1y' that ends three\n  years "
                f"ago is not a one-year window. Fix the pagination before "
                f"reading\n  any number below.")

    report(assess([r for r in rows if r["series"]]))


if __name__ == "__main__":
    main()
