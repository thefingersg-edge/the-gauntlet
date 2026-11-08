#!/usr/bin/env python3
"""PREREGISTRATION_v27 -- how far does the release fade run, and is it
the release at all?

WRITTEN AGAINST THE FROZEN DOCUMENT, whose sha256 is pinned below and
checked at run time. No overnight or multi-day mark for this rule
existed anywhere when this was written.

    S1  CPI + payrolls   descriptive only -- spent by v26.1
    S2  claims only      gated, never used for a horizon question
    S3  control mornings gated as the placebo: is this about releases?

Horizons are the four in section 4 and no others. H2 and H3 cross the
17:00 ET rollover and are charged financing at the measured rates.

    python3 premarket_horizon.py --self-test
    python3 premarket_horizon.py --data-dir ../data/v24
"""

from __future__ import annotations

import argparse
import bisect
import csv
import datetime as dt
import hashlib
import json
import math
import os
import re
import statistics as st
import sys
from zoneinfo import ZoneInfo

from premarket_event import load_events

VERSION = "1.0"
PREREG = "PREREGISTRATION_v27.md"
PREREG_SHA256 = ("88be59abed6fa42282dd5805122730d9"
                 "4d146e39193191fcd48dceb47de19359")

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
INSTRUMENTS = ("SPX500_USD", "NAS100_USD", "US30_USD",
               "DE30_EUR", "EUR_USD", "XAU_USD")
MIN_EVENTS = 150
FORWARD_START = dt.date(2026, 9, 18)        # v25's sample stays unseen

SIG, ENTRY, H0, CLOSE = "08:30", "08:45", "09:45", "15:45"
WANT_ET = (SIG, ENTRY, H0, CLOSE)
#: the UTC times those four land on in EST and in EDT
KEEP_UTC = {"12:30", "13:30", "12:45", "13:45", "14:45", "19:45", "20:45"}
MAX_GAP_DAYS = 5                            # section 4

#: section 5 -- oanda_financing.json, SPX500_USD, live, 2026-09-04
LONG_RATE, SHORT_RATE = -0.0615, 0.0115
LONG_BP = LONG_RATE / 365.0 * 1e4           # -1.685 bp per charged day
SHORT_BP = SHORT_RATE / 365.0 * 1e4         # +0.315 bp per charged day
DAY_COUNT = (1, 1, 1, 1, 3, 0, 0)           # Mon..Sun, OANDA's own
FIN_STRESS = 2.0                            # section 5, reported beside

T_GATE = 2.0                                # section 7
SANITY_MAX_BP = 60.0                        # two days, so wider than v26

_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)


def _guard(names):
    bad = sorted(n for n in names if _FORBIDDEN.search(n))
    if bad:
        raise SystemExit(f"namespace guard: this file must not define {bad}")


def stem(instrument):
    return instrument.replace("_", "").lower()


def read_marks(path):
    """{(ET date, 'HH:MM') -> (o, h, l, c)} for the four ET times only."""
    out = {}
    with open(path, newline="") as fh:
        rd = csv.reader(fh)
        head = next(rd)
        ix = [head.index(k) for k in ("time", "open", "high", "low", "close")]
        for row in rd:
            s = row[ix[0]]
            if s[11:16] not in KEEP_UTC:
                continue
            e = dt.datetime.fromisoformat(s).replace(tzinfo=UTC).astimezone(ET)
            hm = e.strftime("%H:%M")
            if hm not in WANT_ET:
                continue
            out[(e.date(), hm)] = tuple(float(row[i]) for i in ix[1:])
    return out


def mid(b, a, key):
    return (b[key][0] + a[key][0]) / 2.0


def fade_dir(b, a, d):
    o = mid(b, a, (d, SIG))
    c = (b[(d, SIG)][3] + a[(d, SIG)][3]) / 2.0
    return None if c == o else (-1 if c > o else 1)


def later_days(days, d):
    """The next two dates with a 15:45 bar, each within MAX_GAP_DAYS."""
    i = bisect.bisect_right(days, d)
    out = []
    prev = d
    for j in (i, i + 1):
        if j >= len(days) or (days[j] - prev).days > MAX_GAP_DAYS:
            out.append(None)
            prev = None
            break
        out.append(days[j])
        prev = days[j]
    while len(out) < 2:
        out.append(None)
    return out[0], out[1]


def fin_bp(direction, d_entry, d_exit, mult=1.0):
    """Financing in bp of entry notional. Charged at each 17:00 ET rollover
    crossed; the exit at 15:45 is before that day's rollover."""
    n, c = 0, d_entry
    while c < d_exit:
        n += DAY_COUNT[c.weekday()]
        c += dt.timedelta(days=1)
    return mult * n * (LONG_BP if direction == 1 else SHORT_BP)


def one_trade(b, a, d, days):
    """dict of marks for one morning, or None."""
    if any((d, hm) not in b or (d, hm) not in a for hm in WANT_ET):
        return None
    direction = fade_dir(b, a, d)
    if direction is None:
        return None
    me = mid(b, a, (d, ENTRY))
    if me <= 0:
        return None
    pe = a[(d, ENTRY)][0] if direction == 1 else b[(d, ENTRY)][0]
    d2, d3 = later_days(days, d)
    out = {"dir": direction, "date": d, "gross": {}, "net": {}, "fin": {},
           "mkt": {}}
    for tag, key in (("H0", (d, H0)), ("H1", (d, CLOSE)),
                     ("H2", None if d2 is None else (d2, CLOSE)),
                     ("H3", None if d3 is None else (d3, CLOSE))):
        if key is None or key not in b or key not in a:
            continue
        mx = mid(b, a, key)
        px = b[key][0] if direction == 1 else a[key][0]
        g = direction * (mx / me - 1.0) * 1e4
        n = ((px / pe - 1.0) * 1e4) if direction == 1 \
            else ((1.0 - px / pe) * 1e4)
        f = fin_bp(direction, d, key[0])
        out["gross"][tag] = g
        out["net"][tag] = n
        out["fin"][tag] = f
        out["mkt"][tag] = (mx / me - 1.0) * 1e4
    return out if "H0" in out["gross"] else None


def cluster_t(x, g):
    n = len(x)
    if n < 2:
        return None
    mu = sum(x) / n
    s = {}
    for xi, gi in zip(x, g):
        s[gi] = s.get(gi, 0.0) + (xi - mu)
    G = len(s)
    if G < 2:
        return None
    v = G / (G - 1) * sum(z * z for z in s.values()) / (n * n)
    return None if v <= 0 else mu / math.sqrt(v)


def fmt_t(t):
    return "  --" if t is None else f"{t:+5.2f}"


def gate_g1(mu, t, h1, h2, net_fin):
    return (mu > 0 and t is not None and t >= T_GATE
            and h1 is not None and h2 is not None and h1 > 0 and h2 > 0
            and net_fin > 0)


_guard(list(globals()))


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"premarket_horizon.py v{VERSION} self-test\n")

    print("financing is the measured rate, and the day count is OANDA's")
    check("a long pays about 1.68 bp a day, a short is paid about 0.32",
          abs(LONG_BP + 1.685) < 0.01 and abs(SHORT_BP - 0.315) < 0.01,
          f"{LONG_BP:+.3f} / {SHORT_BP:+.3f} bp per charged day")
    mon, thu, fri = dt.date(2026, 1, 5), dt.date(2026, 1, 8), dt.date(2026, 1, 9)
    check("Monday to Tuesday is one charged day",
          abs(fin_bp(1, mon, mon + dt.timedelta(1)) - LONG_BP) < 1e-9)
    #: PLANTED: Friday's rollover carries the weekend. A file that counts
    #: calendar days here understates a Friday trade by two days.
    check("Friday to Monday is THREE charged days, not one",
          abs(fin_bp(1, fri, fri + dt.timedelta(3)) - 3 * LONG_BP) < 1e-9)
    check("Thursday to Monday is four",
          abs(fin_bp(1, thu, thu + dt.timedelta(4)) - 4 * LONG_BP) < 1e-9)
    check("a short is CREDITED, not charged",
          fin_bp(-1, mon, mon + dt.timedelta(1)) > 0
          and fin_bp(1, mon, mon + dt.timedelta(1)) < 0)
    check("no rollover is crossed inside one day",
          fin_bp(1, mon, mon) == 0.0)

    print("\nthe next trading day skips weekends and refuses a long gap")
    days = [dt.date(2026, 1, 5), dt.date(2026, 1, 6), dt.date(2026, 1, 9),
            dt.date(2026, 1, 12), dt.date(2026, 1, 20)]
    check("after Friday the next 15:45 is Monday, and the 8-day gap after it is refused",
          later_days(days, dt.date(2026, 1, 9))[0] == dt.date(2026, 1, 12),
          f"{later_days(days, dt.date(2026, 1, 9))}")
    #: PLANTED: a gap of eight days is a closed market, not a next day.
    check("an 8-day gap is refused, and refuses the one after it too",
          later_days(days, dt.date(2026, 1, 12)) == (None, None))
    check("the day itself is never its own next day",
          later_days(days, dt.date(2026, 1, 5))[0] == dt.date(2026, 1, 6))

    print("\nmarks, direction and cost")
    #: 08:30 rises 100 -> 101, so the fade is SHORT. Price then falls.
    def synth(vals, spread=0.0):
        b, a = {}, {}
        for (d, hm), (o, c) in vals.items():
            b[(d, hm)] = (o - spread / 2, o, o, c - spread / 2)
            a[(d, hm)] = (o + spread / 2, o, o, c + spread / 2)
        return b, a
    d0 = dt.date(2026, 1, 8)                      # a Thursday
    d1, d2 = dt.date(2026, 1, 9), dt.date(2026, 1, 12)
    vals = {(d0, SIG): (100.0, 101.0), (d0, ENTRY): (101.0, 101.0),
            (d0, H0): (100.0, 100.0), (d0, CLOSE): (99.0, 99.0),
            (d1, CLOSE): (98.0, 98.0), (d2, CLOSE): (97.0, 97.0)}
    b, a = synth(vals)
    tr = one_trade(b, a, d0, [d0, d1, d2])
    check("an up 08:30 bar is faded SHORT", tr["dir"] == -1)
    check("H0 is the 09:45 mark from the 08:45 open",
          abs(tr["gross"]["H0"] - (1 - 100.0 / 101.0) * 1e4) < 1e-9,
          f"{tr['gross']['H0']:+.1f} bp")
    check("H3 reaches the second trading day",
          abs(tr["gross"]["H3"] - (1 - 97.0 / 101.0) * 1e4) < 1e-9,
          f"{tr['gross']['H3']:+.1f} bp")
    check("with bid == ask, net equals gross at every horizon",
          all(abs(tr["net"][k] - tr["gross"][k]) < 1e-9 for k in tr["net"]))
    check("H0 and H1 pay no financing; H2 and H3 do",
          tr["fin"]["H0"] == 0 and tr["fin"]["H1"] == 0
          and tr["fin"]["H2"] != 0 and tr["fin"]["H3"] != 0)
    #: PLANTED: entry Thursday, out Friday = 1 day; out Monday = 4 days,
    #: because Friday's rollover carries the weekend.
    check("this short is credited 1 day to +1 and 4 days to +2",
          abs(tr["fin"]["H2"] - SHORT_BP) < 1e-9
          and abs(tr["fin"]["H3"] - 4 * SHORT_BP) < 1e-9,
          f"{tr['fin']['H2']:+.2f} / {tr['fin']['H3']:+.2f} bp")
    b2, a2 = synth(vals, spread=0.10)
    tr2 = one_trade(b2, a2, d0, [d0, d1, d2])
    cost = tr2["gross"]["H0"] - tr2["net"]["H0"]
    check("a spread costs one round trip, not zero and not two",
          8.0 < cost < 12.0, f"{cost:.2f} bp on a 0.10 spread at ~101")
    check("the market move is unsigned by the trade's direction",
          tr["mkt"]["H1"] < 0 < tr["gross"]["H1"],
          "price fell, a short made money")
    check("a doji 08:30 bar is not a trade",
          one_trade(*synth({(d0, SIG): (100.0, 100.0),
                            (d0, ENTRY): (100.0, 100.0),
                            (d0, H0): (100.0, 100.0),
                            (d0, CLOSE): (100.0, 100.0)}), d0, [d0]) is None)
    del b[(d0, CLOSE)]
    check("a missing 15:45 bar drops the morning entirely",
          one_trade(b, a, d0, [d0, d1, d2]) is None)

    print("\nstatistics and the gate")
    per_date = [3.0, -1.0, 4.0, 1.0, -5.0, 9.0, 2.0, 6.0, -2.0, 5.0]
    x = [v for v in per_date for _ in range(6)]
    g = [i for i in range(len(per_date)) for _ in range(6)]
    plain = st.mean(per_date) / (st.stdev(per_date) / math.sqrt(len(per_date)))
    check("six instruments on one date count once",
          abs(cluster_t(x, g) - plain) < 1e-9,
          f"clustered {cluster_t(x, g):+.3f}  naive "
          f"{st.mean(x) / (st.stdev(x) / math.sqrt(len(x))):+.3f}")
    check("G1 needs size, t, stable halves AND a positive net of financing",
          gate_g1(4.0, 2.5, 3.0, 5.0, 1.2))
    check("G1 fails when financing eats it",
          not gate_g1(4.0, 2.5, 3.0, 5.0, -0.3))
    check("G1 fails at t = 1.9",
          not gate_g1(4.0, 1.9, 3.0, 5.0, 1.2))
    check("G1 fails when the halves disagree",
          not gate_g1(4.0, 2.5, -1.0, 9.0, 1.2))

    print("\nthe frozen constants")
    check("four horizons: 09:45, 15:45, +1 day, +2 days",
          WANT_ET == ("08:30", "08:45", "09:45", "15:45")
          and MAX_GAP_DAYS == 5)
    check("gate at 2.0, financing stress at 2x", T_GATE == 2.0
          and FIN_STRESS == 2.0)
    check("six instruments, floor 150, forward sample excluded",
          len(INSTRUMENTS) == 6 and MIN_EVENTS == 150
          and FORWARD_START == dt.date(2026, 9, 18))
    check("no order, execute, submit or position name in this file",
          not [n for n in globals() if _FORBIDDEN.search(n)])

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="../data/v24")
    ap.add_argument("--events", default="../data/events_v2.csv")
    ap.add_argument("--financing", default="../data/oanda_financing.json")
    ap.add_argument("--out", default="../data/horizon_v27_trades.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"premarket_horizon.py v{VERSION}   PREREGISTRATION_v27\n")
    print("  I am not a financial adviser. This is a measurement, not a")
    print("  recommendation to take a position.\n")

    here = os.path.dirname(os.path.abspath(__file__))
    got = hashlib.sha256(
        open(os.path.join(here, "..", PREREG), "rb").read()).hexdigest()
    if got != PREREG_SHA256:
        print(f"  {PREREG} changed since it was frozen ({got[:12]}). Refused.")
        sys.exit(2)
    print(f"  {PREREG} sha256 {got[:16]}... matches the frozen copy")
    try:
        f = json.load(open(os.path.join(here, a.financing)))
        same = (abs(f["long_rate"] - LONG_RATE) < 1e-9
                and abs(f["short_rate"] - SHORT_RATE) < 1e-9)
        print(f"  financing {f['instrument']} long {f['long_rate']:+.4f} "
              f"short {f['short_rate']:+.4f}   "
              f"{'matches section 5' if same else 'DOES NOT MATCH section 5'}")
        if not same:
            sys.exit(2)
    except FileNotFoundError:
        print(f"  {a.financing} not found -- section 5's declared rates used")
    print()

    pre, _ = load_events(a.events, from_year=1900)
    s1_days = {d for d, e in pre.items() if {"CPI", "NFP"} & e}
    s2_days = {d for d, e in pre.items() if "CLAIMS" in e} - s1_days
    print(f"  CPI/payrolls dates {len(s1_days):,}   claims-only dates "
          f"{len(s2_days):,}   control: every other morning\n")

    rows = {"S1": [], "S2": [], "S3": []}
    counts = {}
    for ins in INSTRUMENTS:
        pb = os.path.join(a.data_dir, f"{stem(ins)}_bid_15m.csv")
        pa = os.path.join(a.data_dir, f"{stem(ins)}_ask_15m.csv")
        if not (os.path.exists(pb) and os.path.exists(pa)):
            print(f"  {ins:<12} NO DATA")
            continue
        b, ask = read_marks(pb), read_marks(pa)
        days = sorted({d for (d, hm) in b if hm == CLOSE and (d, hm) in ask})
        mornings = sorted({d for (d, hm) in b if hm == SIG and (d, hm) in ask
                           and d < FORWARD_START})
        n = {"S1": 0, "S2": 0, "S3": 0}
        for d in mornings:
            s = "S1" if d in s1_days else ("S2" if d in s2_days else "S3")
            tr = one_trade(b, ask, d, days)
            if tr is None:
                continue
            tr["ins"] = ins
            rows[s].append(tr)
            n[s] += 1
        counts[ins] = n
        print(f"  {ins:<12} S1 {n['S1']:>4}   S2 {n['S2']:>4}   "
              f"S3 {n['S3']:>5}   mornings {len(mornings):,}")

    with open(a.out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sample", "instrument", "date", "dir"]
                   + [f"{p}_{h}" for p in ("gross", "net", "fin", "mkt")
                      for h in ("H0", "H1", "H2", "H3")])
        for s in ("S1", "S2", "S3"):
            for t in rows[s]:
                w.writerow([s, t["ins"], t["date"].isoformat(), t["dir"]]
                           + [("" if h not in t[p] else f"{t[p][h]:.6f}")
                              for p in ("gross", "net", "fin", "mkt")
                              for h in ("H0", "H1", "H2", "H3")])
    print(f"\n  per-trade marks written to {a.out}")

    def block(tag, name, gated):
        tr = [t for t in rows[tag]
              if counts.get(t["ins"], {}).get(tag, 0) >= MIN_EVENTS]
        if not tr:
            print(f"\n  {name}: nothing over the floor")
            return None
        dates = sorted({t["date"] for t in tr})
        cut = dates[len(dates) // 2]
        print(f"\n  {name}   n {len(tr):,} trades on {len(dates):,} mornings"
              f"   {dates[0]} .. {dates[-1]}   halves at {cut}"
              + ("" if gated else "   DESCRIPTIVE ONLY, v27 section 3"))
        print(f"    {'horizon':<10}{'n':>7}{'gross':>8}{'positive':>10}"
              f"{'SD':>7}{'net':>8}{'net+fin':>9}{'+fin x2':>9}"
              f"{'vs H0':>8}{'t':>7}")
        res = {}
        for h, lab in (("H0", "09:45"), ("H1", "15:45"),
                       ("H2", "+1 day"), ("H3", "+2 days")):
            sel = [t for t in tr if h in t["gross"]]
            if len(sel) < 2:
                continue
            g = [t["gross"][h] for t in sel]
            n1 = [t["net"][h] for t in sel]
            n2 = [t["net"][h] + t["fin"][h] for t in sel]
            n3 = [t["net"][h] + FIN_STRESS * t["fin"][h] for t in sel]
            inc = [t["gross"][h] - t["gross"]["H0"] for t in sel]
            tt = cluster_t(inc, [t["date"] for t in sel]) if h != "H0" else None
            res[h] = dict(n=len(sel), gross=st.mean(g), net=st.mean(n1),
                          netfin=st.mean(n2), inc=st.mean(inc), t=tt,
                          sel=sel, inc_v=inc)
            print(f"    {lab:<10}{len(sel):>7}{st.mean(g):>+8.2f}"
                  f"{sum(1 for v in g if v > 0) / len(g):>10.0%}"
                  f"{st.stdev(g):>7.1f}{st.mean(n1):>+8.2f}"
                  f"{st.mean(n2):>+9.2f}{st.mean(n3):>+9.2f}"
                  + (f"{'':>8}{'':>7}" if h == "H0"
                     else f"{st.mean(inc):>+8.2f}{fmt_t(tt):>7}"))
        longs = sum(1 for t in tr if t["dir"] == 1) / len(tr)
        for h, lab in (("H2", "+1 day"), ("H3", "+2 days")):
            sel = [t for t in tr if h in t["mkt"]]
            if not sel:
                continue
            mk = st.mean(t["mkt"][h] for t in sel)
            print(f"    diagnostic {lab}: long on {longs:.0%} of trades, "
                  f"market moved {mk:+.2f} bp, so drift x imbalance = "
                  f"{(2 * longs - 1) * mk:+.2f} bp of the {res[h]['gross']:+.2f}")
        return res

    r1 = block("S1", "S1  CPI and payrolls", False)
    r2 = block("S2", "S2  claims only", True)
    r3 = block("S3", "S3  control mornings", True)

    print(f"\n  GATES -- frozen in PREREGISTRATION_v27 section 7")
    if r2 and "H2" in r2:
        sel, inc = r2["H2"]["sel"], r2["H2"]["inc_v"]
        cut = sorted({t["date"] for t in sel})[len({t["date"] for t in sel}) // 2]
        h1 = [v for v, t in zip(inc, sel) if t["date"] < cut]
        h2 = [v for v, t in zip(inc, sel) if t["date"] >= cut]
        ok = gate_g1(r2["H2"]["inc"], r2["H2"]["t"],
                     st.mean(h1) if h1 else None, st.mean(h2) if h2 else None,
                     r2["H2"]["netfin"])
        print(f"    [{'PASS' if ok else 'FAIL'}] G1 claims, H0 -> +1 day "
              f"{r2['H2']['inc']:+.2f} bp   t {fmt_t(r2['H2']['t']).strip()}"
              f"   halves {st.mean(h1):+.2f} / {st.mean(h2):+.2f}"
              f"   net+fin {r2['H2']['netfin']:+.2f} bp")
        if abs(r2["H2"]["inc"]) > SANITY_MAX_BP:
            print(f"    SANITY -- above {SANITY_MAX_BP} bp. A bug until shown "
                  f"otherwise.")
            sys.exit(5)
    if r3 and "H2" in r3:
        t3 = r3["H2"]["t"]
        hot = t3 is not None and abs(t3) >= T_GATE
        print(f"    [ G2 ] control mornings, H0 -> +1 day "
              f"{r3['H2']['inc']:+.2f} bp   t {fmt_t(t3).strip()}")
        msg = ("THE DRIFT IS NOT RELEASE-SPECIFIC -- it is there on "
               "ordinary mornings too" if hot else
               "flat on ordinary mornings, so what drift there is stays "
               "linked to the release")
        print(f"           {msg}")


if __name__ == "__main__":
    main()
