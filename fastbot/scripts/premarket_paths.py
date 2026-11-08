#!/usr/bin/env python3
"""PREREGISTRATION_v26 -- does the path tell you when to get out?

WRITTEN AGAINST THE FROZEN DOCUMENTS (v26 and its amendment v26.1),
before any path of the release fade
was measured. The document's sha256 is pinned below and checked at run
time: if the registration changes, this refuses to run. If THIS file is
edited after the first run, that edit is the run.

Dave's question: "if it's a winning trade, did we make the most of it --
could we have made more without risking anything?"

An exit rule cannot create expected profit on a random path. It can only
earn if the real path is predictable, so stage 1 measures that directly
and stage 2 answers the question in money, trade by trade against rule A.

NO BARRIER IS SIMULATED INSIDE A BAR. Every decision is taken at a bar
open and filled at that open's bid or ask. exit_shape.py explains why:
silver15's only false PASS came from guessing the order of a bar's high
and low.

    python3 premarket_paths.py --self-test
    python3 premarket_paths.py --data-dir ../data/v24
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import math
import os
import re
import statistics as st
import sys
from zoneinfo import ZoneInfo

from premarket_event import load_events
from premarket_instruments import trade as v24_trade, VARIANT_A, VARIANT_C

VERSION = "1.1"
PREREG = "PREREGISTRATION_v26.md"
PREREG_SHA256 = ("c5c0a1213a4bc4f5d142aa17330f3475"
                 "d7407bf3273071baddd2f68409aebd7f")
#: v1.1 -- the v26.1 amendment, frozen before the first data run
AMEND = "PREREGISTRATION_v26.1.md"
AMEND_SHA256 = ("050ad7f4a96fef3a2478a0fe87114623"
                "5b3ee939c50f66e664f24ba7dc1d2981")

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
BAR = dt.timedelta(minutes=15)
SLOT = (8, 30)                                   # section 2
RELEASES = ("CPI", "NFP")                        # section 2, claims out
INSTRUMENTS = ("SPX500_USD", "NAS100_USD", "US30_USD",
               "DE30_EUR", "EUR_USD", "XAU_USD")  # section 3
MIN_EVENTS = 150                                 # section 3
FORWARD_START = dt.date(2026, 9, 18)             # section 3: unseen

#: bar offsets from the 08:30 ET signal bar -- marks are bar OPENS
K_ENTRY, K_0900, K_0915, K_0930 = 1, 2, 3, 4
K_0945, K_1045, K_LAST = 5, 9, 13                # K_LAST is 11:45
#: v26.1 -- the hour marks, 09:45 to 15:45, the last cash-session open
K_HOURS = (5, 9, 13, 17, 21, 25, 29)
K_1545 = 29
T_HX = 2.0                                       # v26.1 section 3a

T_STAGE1 = 2.4                                   # section 5
Q3_MIN_BP = 1.0                                  # section 5
T_STAGE2 = 2.5                                   # section 6
BANK_BP, LOCK_BP, TRAIL_BP = 10.0, 3.0, 10.0     # section 6, frozen
LOSER_WAS_UP_BP, WINNER_WAS_DOWN_BP = 3.0, 10.0  # section 6, Part A
SANITY_MAX_BP = 30.0                             # a bug until proven not

#: Gate 0, section 4 -- RESULT_INSTRUMENTS section 1, n and A gross
CONTROL = {"NAS100_USD": (525, 6.97), "US30_USD": (529, 1.17),
           "EUR_USD": (540, 1.54), "XAU_USD": (501, 4.29),
           "DE30_EUR": (531, 2.52)}


def stem(instrument):
    return instrument.replace("_", "").lower()


def read_days(path, days):
    """{utc datetime -> (o, h, l, c)}, only bars on the given dates.

    08:30-11:45 ET is 12:30-16:45 UTC, so the ET date and the UTC date
    of every bar this file uses are the same, and filtering on the date
    prefix loses nothing.
    """
    keep = {d.isoformat() for d in days}
    out = {}
    with open(path, newline="") as fh:
        rd = csv.reader(fh)
        head = next(rd)
        ix = [head.index(k) for k in ("time", "open", "high", "low", "close")]
        for row in rd:
            s = row[ix[0]]
            if s[:10] not in keep:
                continue
            t = dt.datetime.fromisoformat(s).replace(tzinfo=UTC)
            out[t] = tuple(float(row[i]) for i in ix[1:])
    return out


def mid_o(b, a, t):
    return (b[t][0] + a[t][0]) / 2.0


def mid_c(b, a, t):
    return (b[t][3] + a[t][3]) / 2.0


def fade_dir(b, a, t8):
    o, c = mid_o(b, a, t8), mid_c(b, a, t8)
    if c == o:
        return None
    return -1 if c > o else 1


def gross_a(b, a, t8):
    """Rule A gross, this file's own arithmetic -- Gate 0 compares it."""
    t1, t5 = t8 + BAR * K_ENTRY, t8 + BAR * K_0945
    if any(t not in b or t not in a for t in (t8, t1, t5)):
        return None
    d = fade_dir(b, a, t8)
    if d is None:
        return None
    return d * (mid_o(b, a, t5) / mid_o(b, a, t1) - 1.0) * 1e4


def path(b, a, t8):
    """Marks, executable exits and hold excursions for one trade, or None.

    m[k]    mid P&L in bp at the open of bar k, from the entry mid
    net[k]  executable P&L in bp if closed at the open of bar k: a long
            is bought at the entry ask and sold at bar k's bid; a short
            is sold at the entry bid and bought back at bar k's ask, on
            ENTRY notional -- (Pe - Px) / Pe, the v24 fix
    mfe/mae best and worst executable P&L during the hold, from the bars
            08:45 to 09:30 and the 09:45 open. Hindsight, Part A only.
    """
    ts = [t8 + BAR * k for k in range(K_LAST + 1)]
    if any(t not in b or t not in a for t in ts):
        return None
    d = fade_dir(b, a, ts[0])
    if d is None:
        return None
    me = mid_o(b, a, ts[K_ENTRY])
    if me <= 0:
        return None
    m = [None] + [d * (mid_o(b, a, ts[k]) / me - 1.0) * 1e4
                  for k in range(1, K_LAST + 1)]
    hold = range(K_ENTRY, K_0945)
    if d == 1:
        pe = a[ts[K_ENTRY]][0]
        net = [None] + [(b[ts[k]][0] / pe - 1.0) * 1e4
                        for k in range(1, K_LAST + 1)]
        hi = max([b[ts[k]][1] for k in hold] + [b[ts[K_0945]][0]])
        lo = min([b[ts[k]][2] for k in hold] + [b[ts[K_0945]][0]])
        mfe, mae = (hi / pe - 1.0) * 1e4, (lo / pe - 1.0) * 1e4
    else:
        pe = b[ts[K_ENTRY]][0]
        net = [None] + [(1.0 - a[ts[k]][0] / pe) * 1e4
                        for k in range(1, K_LAST + 1)]
        lo = min([a[ts[k]][2] for k in hold] + [a[ts[K_0945]][0]])
        hi = max([a[ts[k]][1] for k in hold] + [a[ts[K_0945]][0]])
        mfe, mae = (1.0 - lo / pe) * 1e4, (1.0 - hi / pe) * 1e4
    return dict(d=d, m=m, net=net, mfe=mfe, mae=mae)


def hour_marks(b, a, t8, p):
    """{k: (m, net)} at the hourly opens 09:45 .. 15:45, or None. v26.1."""
    ts = {k: t8 + BAR * k for k in K_HOURS}
    if any(t not in b or t not in a for t in ts.values()):
        return None
    t1 = t8 + BAR * K_ENTRY
    me, d, out = mid_o(b, a, t1), p["d"], {}
    for k, t in ts.items():
        m = d * (mid_o(b, a, t) / me - 1.0) * 1e4
        if d == 1:
            net = (b[t][0] / a[t1][0] - 1.0) * 1e4
        else:
            net = (1.0 - a[t][0] / b[t1][0]) * 1e4
        out[k] = (m, net)
    return out


# ---- the exit rules, section 6. Decisions at bar opens only. ----------

def rule_a(p):
    return p["net"][K_0945]


def rule_e1(p):
    """BANK: the first open at 09:00, 09:15 or 09:30 with m >= +10."""
    for k in (K_0900, K_0915, K_0930):
        if p["m"][k] >= BANK_BP:
            return p["net"][k]
    return p["net"][K_0945]


def rule_e2(p):
    """LOCK: +10 seen at one of those opens sets a +3 floor for LATER ones."""
    armed = False
    for k in (K_0900, K_0915, K_0930):
        if not armed:
            armed = p["m"][k] >= BANK_BP
        elif p["m"][k] < LOCK_BP:
            return p["net"][k]
    return p["net"][K_0945]


def rule_e3(p):
    """EXTEND: a winner at 09:45 is held to the 10:45 open."""
    return p["net"][K_1045] if p["m"][K_0945] > 0 else p["net"][K_0945]


def rule_e4(p):
    """TRAIL: a winner at 09:45 is held; floor = max(m(09:45), best - 10)."""
    m = p["m"]
    if not m[K_0945] > 0:
        return p["net"][K_0945]
    best = m[K_0945]
    for k in range(K_0945 + 1, K_LAST + 1):
        if m[k] < max(m[K_0945], best - TRAIL_BP):
            return p["net"][k]
        best = max(best, m[k])
    return p["net"][K_LAST]


RULES = (("E1 bank +10", rule_e1), ("E2 lock +3 after +10", rule_e2),
         ("E3 extend winners", rule_e3), ("E4 trail winners", rule_e4))


# ---- statistics ---------------------------------------------------------

def cluster_t(x, g):
    """t for the mean of x, standard error clustered on g (release date)."""
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


def cluster_t_diff(xw, gw, xl, gl):
    """t for mean(xw) - mean(xl), clustered, by the influence function."""
    if len(xw) < 2 or len(xl) < 2:
        return None, None
    mw, ml = sum(xw) / len(xw), sum(xl) / len(xl)
    s = {}
    for x, g in zip(xw, gw):
        s[g] = s.get(g, 0.0) + (x - mw) / len(xw)
    for x, g in zip(xl, gl):
        s[g] = s.get(g, 0.0) - (x - ml) / len(xl)
    G = len(s)
    v = G / (G - 1) * sum(z * z for z in s.values())
    return (mw - ml), (None if v <= 0 else (mw - ml) / math.sqrt(v))


def plain_t(x):
    if len(x) < 2 or st.stdev(x) == 0:
        return None
    return st.mean(x) / (st.stdev(x) / math.sqrt(len(x)))


def split_halves(dates):
    """The median release date; the first half is strictly before it."""
    ds = sorted(set(dates))
    return ds[len(ds) // 2]


def p5(x):
    return st.quantiles(x, n=20, method="inclusive")[0]


def stage1_pass(kind, mean, t, h1, h2):
    if t is None or h1 is None or h2 is None:
        return False
    if kind == "neg":
        return mean < 0 and t <= -T_STAGE1 and h1 < 0 and h2 < 0
    return mean >= Q3_MIN_BP and t >= T_STAGE1 and h1 > 0 and h2 > 0


def stage2_pass(dmean, dtt, p5_rule, p5_a, worst_rule, worst_a):
    return (dmean > 0 and dtt is not None and dtt >= T_STAGE2
            and p5_rule >= p5_a and worst_rule >= worst_a)


def in_window(d):
    return d < FORWARD_START


def fmt_t(t):
    return "   --" if t is None else f"{t:+6.2f}"


# ---- the guard every probe in this project carries --------------------

_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)


def _guard(names):
    bad = sorted(n for n in names if _FORBIDDEN.search(n))
    if bad:
        raise SystemExit(f"namespace guard: this file must not define {bad}")


_guard(list(globals()))


# ---- self-test -----------------------------------------------------------

def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"premarket_paths.py v{VERSION} self-test\n")
    T0 = dt.datetime(2020, 6, 5, 12, 30, tzinfo=UTC)     # 08:30 ET, EDT
    T1 = dt.datetime(2020, 1, 10, 13, 30, tzinfo=UTC)    # 08:30 ET, EST

    def synth(opens, spread=0.0, start=T0, spikes=None):
        """Bars whose OPENS are `opens`; close = next open; optional spikes."""
        b, a = {}, {}
        for i, o in enumerate(opens):
            c = opens[i + 1] if i + 1 < len(opens) else o
            hi, lo = max(o, c), min(o, c)
            if spikes and i in spikes:
                hi, lo = max(hi, spikes[i][0]), min(lo, spikes[i][1])
            t = start + BAR * i
            b[t] = (o - spread / 2, hi - spread / 2, lo - spread / 2,
                    c - spread / 2)
            a[t] = (o + spread / 2, hi + spread / 2, lo + spread / 2,
                    c + spread / 2)
        return b, a

    print("the offsets land on the clock times section 5 names")
    for T in (T0, T1):
        e = [(T + BAR * k).astimezone(ET).strftime("%H:%M")
             for k in (0, K_ENTRY, K_0915, K_0945, K_1045, K_LAST)]
        check(f"{T.date()} ({'EDT' if T is T0 else 'EST'}): "
              f"08:30 08:45 09:15 09:45 10:45 11:45",
              e == ["08:30", "08:45", "09:15", "09:45", "10:45", "11:45"],
              " ".join(e))
    for T in (T0, T1):
        e = [(T + BAR * k).astimezone(ET).strftime("%H:%M") for k in K_HOURS]
        check(f"{T.date()}: the v26.1 hour marks are 09:45 .. 15:45",
              e == ["09:45", "10:45", "11:45", "12:45", "13:45", "14:45",
                    "15:45"], " ".join(e))

    print("\nmarks and exits")
    #: PLANTED: signal bar rises 100 -> 101, so the fade is SHORT. Price
    #: then falls to 100 by 09:45: a winning short of ~99 bp.
    opens = [100.0, 101.0, 100.8, 100.5, 100.2, 100.0] + [100.0] * 9
    b, a = synth(opens)
    p = path(b, a, T0)
    check("an up signal bar is faded SHORT", p is not None and p["d"] == -1)
    want = -1 * (100.0 / 101.0 - 1.0) * 1e4
    check("m(09:45) is measured from the 08:45 OPEN, not the signal close",
          abs(p["m"][K_0945] - want) < 1e-9, f"{p['m'][K_0945]:+.2f} bp")
    check("with bid == ask, every executable exit equals its mark",
          all(abs(p["net"][k] - p["m"][k]) < 1e-9
              for k in range(1, K_LAST + 1)),
          "the short leg is on entry notional")
    b2, a2 = synth(opens, spread=0.10)
    p2 = path(b2, a2, T0)
    cost = p2["m"][K_0945] - p2["net"][K_0945]
    check("a spread costs one spread per round trip, not zero, not two",
          8.0 < cost < 12.0, f"{cost:.2f} bp on a 0.10 spread at ~101")
    check("and this file's rule A gross agrees with v24's trade()",
          abs(gross_a(b2, a2, T0) - v24_trade(b2, a2, T0, VARIANT_A)[0])
          < 1e-9)
    b5, a5 = synth(opens + [99.0] * 16, spread=0.10)     # past 15:45
    ph = path(b5, a5, T0)
    hm = hour_marks(b5, a5, T0, ph)
    check("the v26.1 hour marks agree with path() where they overlap",
          hm is not None and all(abs(hm[k][0] - ph["m"][k]) < 1e-9
                                 and abs(hm[k][1] - ph["net"][k]) < 1e-9
                                 for k in (K_0945, K_1045, K_LAST)))
    check("and m(15:45) is the fade's P&L at 15:45",
          abs(hm[K_1545][0] - (-1) * (99.0 / 101.0 - 1.0) * 1e4) < 1e-9,
          f"{hm[K_1545][0]:+.1f} bp")
    del b5[T0 + BAR * K_1545]
    check("a missing 15:45 bar drops the trade from HX only",
          hour_marks(b5, a5, T0, ph) is None and path(b5, a5, T0) is not None)

    print("\nwhat makes a trade unusable")
    b3, a3 = synth(opens)
    del b3[T0 + BAR * K_LAST]
    check("a missing bar anywhere to 11:45 drops the trade",
          path(b3, a3, T0) is None)
    check("a doji signal bar is not a trade",
          path(*synth([100.0, 100.0] + [100.0] * 13), T0) is None)
    check("the forward test's first day is outside the window",
          not in_window(dt.date(2026, 9, 18))
          and in_window(dt.date(2026, 9, 17)))

    print("\nPart A reads the hold and nothing after it")
    #: PLANTED: a spike in the 08:45 bar (inside the hold) and a bigger
    #: one in the 09:45 bar (after the time exit). Only the first counts.
    b4, a4 = synth(opens, spikes={1: (101.2, 99.0), 5: (101.0, 95.0)})
    p4 = path(b4, a4, T0)
    check("the best price during the hold is the in-hold spike (99.0)",
          abs(p4["mfe"] - (1.0 - 99.0 / 101.0) * 1e4) < 1e-9,
          f"mfe {p4['mfe']:+.1f} bp")
    check("the 09:45 bar's bigger spike (95.0) is NOT counted",
          p4["mfe"] < (1.0 - 95.0 / 101.0) * 1e4)
    check("the worst price during the hold is the in-hold spike (101.2)",
          abs(p4["mae"] - (1.0 - 101.2 / 101.0) * 1e4) < 1e-9,
          f"mae {p4['mae']:+.1f} bp")

    print("\nthe four rules do exactly what section 6 says")

    def P(marks):
        mm = [None] + list(marks)
        return dict(m=mm, net=[None] + [x - 1.0 for x in marks])
    #          08:45  09:00  09:15  09:30  09:45  10:00 ...           11:45
    rise = P([0.0, 4.0, 12.0, 6.0, 8.0, 9.0, 15.0, 22.0, 13.0,
              14.0, 14.0, 14.0, 14.0])
    check("E1 banks at the first open at or above +10 (09:15)",
          rule_e1(rise) == 11.0)
    check("E1 holds a trade that never reaches +10 to 09:45",
          rule_e1(P([0, 4, 9, 9.9, 7] + [0] * 8)) == 6.0)
    check("E1 does not look at 09:45 or later",
          rule_e1(P([0, 1, 2, 3, 40] + [0] * 8)) == 39.0)
    check("E2 locks after +10 at 09:00 and exits when 09:15 is under +3",
          rule_e2(P([0, 11, 2, 20, 5] + [0] * 8)) == 1.0)
    check("E2 armed at 09:15 and 09:30 still above +3: 09:45 time exit",
          rule_e2(rise) == 7.0)
    check("E2 armed at 09:30 has no later open before 09:45",
          rule_e2(P([0, 1, 2, 12, -5] + [0] * 8)) == -6.0)
    check("E3 holds a 09:45 winner to 10:45",
          rule_e3(rise) == 12.0)
    check("E3 closes a 09:45 loser at 09:45",
          rule_e3(P([0, 1, 1, 1, -2] + [50] * 8)) == -3.0)
    #: rise: m(09:45) +8, then 9, 15, 22 (best 22). The floor becomes
    #: max(8, 22 - 10) = 12, and 13, 14, 14, 14, 14 never go under it, so
    #: the trade rides to the 11:45 cap. v1.0 planted 12.0 here -- an exit
    #: at 10:45 -- and that expectation was wrong: 13 is not under 12. The
    #: self-test caught the TEST, before any data run.
    check("E4 holds at 13 when the floor is 12, and rides to 11:45",
          rule_e4(rise) == 13.0, "13 is not under max(8, 22 - 10) = 12")
    check("E4 exits the first time the mark is under the floor",
          rule_e4(P([0, 0, 0, 0, 8, 9, 15, 22, 11.9, 30, 0, 0, 0])) == 10.9,
          "11.9 < max(8, 22 - 10)")
    check("E4 never lets a 09:45 winner fall below its 09:45 mark",
          rule_e4(P([0, 0, 0, 0, 8, 7.9] + [30] * 7)) == 6.9)
    check("E4 rides to 11:45 if never stopped",
          rule_e4(P([0, 0, 0, 0, 8, 9, 10, 11, 12, 13, 14, 15, 16])) == 15.0)
    check("E4 leaves a 09:45 loser alone",
          rule_e4(P([0, 0, 0, 0, -8] + [30] * 8)) == -9.0)

    print("\nstatistics")
    #: PLANTED: six identical copies per date are ONE observation per
    #: date. The clustered t must equal the plain t of the per-date values.
    per_date = [3.0, -1.0, 4.0, 1.0, -5.0, 9.0, 2.0, 6.0, -2.0, 5.0]
    x = [v for v in per_date for _ in range(6)]
    g = [i for i in range(len(per_date)) for _ in range(6)]
    check("six copies of one date count once",
          abs(cluster_t(x, g) - plain_t(per_date)) < 1e-9,
          f"clustered {cluster_t(x, g):+.3f}  plain {plain_t(per_date):+.3f}"
          f"  naive {plain_t(x):+.3f}")
    import random
    rnd = random.Random(1)
    xw = [rnd.gauss(1.0, 5.0) for _ in range(800)]
    xl = [rnd.gauss(0.0, 7.0) for _ in range(900)]
    d, tdiff = cluster_t_diff(xw, range(800), xl, range(800, 1700))
    welch = d / math.sqrt(st.variance(xw) / 800 + st.variance(xl) / 900)
    check("with every trade its own cluster the difference t is Welch's",
          abs(tdiff - welch) / abs(welch) < 0.01,
          f"{tdiff:+.3f} vs {welch:+.3f}")
    check("halves split at the median date",
          split_halves([dt.date(2010, 1, 1), dt.date(2011, 1, 1),
                        dt.date(2012, 1, 1), dt.date(2012, 1, 1)])
          == dt.date(2011, 1, 1))

    print("\nthe gates are the frozen ones")
    check("stage 1 at 2.4, stage 2 at 2.5, Q3 needs +1.0 bp",
          T_STAGE1 == 2.4 and T_STAGE2 == 2.5 and Q3_MIN_BP == 1.0)
    check("bank +10, lock +3, trail 10",
          (BANK_BP, LOCK_BP, TRAIL_BP) == (10.0, 3.0, 10.0))
    check("v26.1: HX is one look at 2.0, ending at the 15:45 open",
          T_HX == 2.0 and K_1545 == 29 and K_HOURS[0] == K_0945)
    check("Q1 passes on a real, stable giveback",
          stage1_pass("neg", -3.0, -2.5, -2.0, -4.0))
    check("but not when the halves disagree",
          not stage1_pass("neg", -3.0, -2.5, -7.0, +1.0))
    check("and not at t = -2.3",
          not stage1_pass("neg", -3.0, -2.3, -2.0, -4.0))
    check("Q3 needs the SIZE as well as the t",
          not stage1_pass("pos", 0.8, 3.0, 0.7, 0.9)
          and stage1_pass("pos", 1.2, 3.0, 1.0, 1.4))
    check("stage 2 fails a richer rule with a fatter tail",
          not stage2_pass(2.0, 3.0, -40.0, -35.0, -90.0, -90.0))
    check("and passes only on all three conditions",
          stage2_pass(2.0, 3.0, -35.0, -35.0, -90.0, -90.0))
    check("Gate 0 carries the published numbers",
          CONTROL["NAS100_USD"] == (525, 6.97)
          and CONTROL["XAU_USD"] == (501, 4.29) and len(CONTROL) == 5)
    check("six instruments, CPI and payrolls, window ends 2026-09-17",
          len(INSTRUMENTS) == 6 and RELEASES == ("CPI", "NFP")
          and FORWARD_START == dt.date(2026, 9, 18))
    check("no order, execute, submit or position name in this file",
          not [n for n in globals() if _FORBIDDEN.search(n)])

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


# ---- the run ------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="../data/v24")
    ap.add_argument("--events", default="../data/events_v2.csv")
    ap.add_argument("--out", default="../data/paths_v26_trades.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"premarket_paths.py v{VERSION}   PREREGISTRATION_v26\n")
    print("  I am not a financial adviser. This is a measurement, not a")
    print("  recommendation to take a position.\n")

    here = os.path.dirname(os.path.abspath(__file__))
    for doc, want in ((PREREG, PREREG_SHA256), (AMEND, AMEND_SHA256)):
        got = hashlib.sha256(
            open(os.path.join(here, "..", doc), "rb").read()).hexdigest()
        if got != want:
            print(f"  {doc} has changed since it was frozen ({got[:12]}).")
            print(f"  A registration edited after the fact is not one. "
                  f"Refused.")
            sys.exit(2)
        print(f"  {doc} sha256 {got[:16]}... matches the frozen copy")
    print()

    pre, _ = load_events(a.events, from_year=1900)
    ev_days = sorted(d for d in pre if any(r in pre[d] for r in RELEASES))
    rel = {d: "+".join(r for r in RELEASES if r in pre[d]) for d in ev_days}

    recs, control, per = [], {}, {}
    for ins in INSTRUMENTS:
        pb = os.path.join(a.data_dir, f"{stem(ins)}_bid_15m.csv")
        pa = os.path.join(a.data_dir, f"{stem(ins)}_ask_15m.csv")
        if not (os.path.exists(pb) and os.path.exists(pa)):
            print(f"  {ins:<12} NO DATA")
            continue
        bid, ask = read_days(pb, ev_days), read_days(pa, ev_days)
        slot = {}
        for t in bid.keys() & ask.keys():
            e = t.astimezone(ET)
            if (e.hour, e.minute) == SLOT:
                slot[e.date()] = t
        if ins in CONTROL:
            mine, theirs, worst = [], [], 0.0
            for d in ev_days:
                t = slot.get(d)
                if t is None:
                    continue
                ta = v24_trade(bid, ask, t, VARIANT_A)
                tc = v24_trade(bid, ask, t, VARIANT_C)
                if ta is None or tc is None:
                    continue
                g = gross_a(bid, ask, t)
                mine.append(g)
                theirs.append(ta[0])
                worst = max(worst, abs(g - ta[0]))
            control[ins] = (len(mine), st.mean(mine) if mine else None,
                            worst)
        rows, dropped = [], 0
        for d in ev_days:
            if not in_window(d):
                continue
            t = slot.get(d)
            if t is None:
                continue
            p = path(bid, ask, t)
            if p is None:
                dropped += 1
                continue
            rows.append((ins, d, rel[d], p, hour_marks(bid, ask, t, p)))
        per[ins] = rows
        print(f"  {ins:<12} {len(rows):>4} usable events   "
              f"{rows[0][1] if rows else '--'} .. "
              f"{rows[-1][1] if rows else '--'}   ({dropped} dropped: a bar "
              f"missing to 11:45, or a doji)")

    # ---- Gate 0 --------------------------------------------------------
    print(f"\n  GATE 0 -- positive control, section 4")
    g0 = True
    for ins, (n0, m0) in CONTROL.items():
        n, m, worst = control.get(ins, (0, None, None))
        good = (n == n0 and m is not None and abs(m - m0) <= 0.005 + 1e-9
                and worst is not None and worst < 1e-9)
        g0 &= good
        print(f"    {ins:<12} n {n:>4} (v24 {n0})   A gross "
              f"{m if m is None else f'{m:+.4f}'} (v24 {m0:+.2f})   "
              f"max |mine - v24| {worst if worst is None else f'{worst:.1e}'}"
              f"   [{'PASS' if good else 'FAIL'}]")
    if not g0:
        print("\n    VOID -- the new file cannot reproduce a published number")
        print("    from the same bars. That is a bug here, not a finding.")
        sys.exit(3)

    pooled = [r for ins in INSTRUMENTS for r in per.get(ins, [])
              if len(per.get(ins, [])) >= MIN_EVENTS]
    small = [ins for ins in INSTRUMENTS
             if 0 < len(per.get(ins, [])) < MIN_EVENTS]
    dates = [r[1] for r in pooled]
    cut = split_halves(dates)
    print(f"\n  pooled: {len(pooled):,} trades on {len(set(dates)):,} release "
          f"dates, {min(dates)} .. {max(dates)}; halves split at {cut}"
          + (f"; under the floor, not pooled: {small}" if small else ""))

    with open(a.out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["instrument", "date", "release", "dir"]
                   + [f"m{k}" for k in range(1, K_LAST + 1)]
                   + [f"net{k}" for k in range(1, K_LAST + 1)]
                   + ["mfe", "mae"]
                   + [f"h{k}_m" for k in K_HOURS[3:]]
                   + [f"h{k}_net" for k in K_HOURS[3:]])
        for ins, d, rl, p, hm in pooled:
            w.writerow([ins, d.isoformat(), rl, p["d"]]
                       + [f"{p['m'][k]:.6f}" for k in range(1, K_LAST + 1)]
                       + [f"{p['net'][k]:.6f}" for k in range(1, K_LAST + 1)]
                       + [f"{p['mfe']:.6f}", f"{p['mae']:.6f}"]
                       + [("" if hm is None else f"{hm[k][0]:.6f}")
                          for k in K_HOURS[3:]]
                       + [("" if hm is None else f"{hm[k][1]:.6f}")
                          for k in K_HOURS[3:]])
    print(f"  per-trade marks written to {a.out}")

    # ---- Stage 1 -------------------------------------------------------
    def question(rows, k_at, k_to, side):
        sel = [r for r in rows
               if (r[3]["m"][k_at] > 0 if side == "win"
                   else r[3]["m"][k_at] < 0)]
        x = [r[3]["m"][k_to] - r[3]["m"][k_at] for r in sel]
        g = [r[1] for r in sel]
        return sel, x, g

    Q = (("Q1", "BANKING", "in profit at 09:15", K_0915, K_0945, "win", "neg"),
         ("Q2", "STOPS", "losing at 09:15", K_0915, K_0945, "lose", "neg"),
         ("Q3", "TRAILING", "in profit at 09:45", K_0945, K_1045, "win", "pos"))
    print(f"\n  STAGE 1 -- is the path predictable?  (section 5)")
    print(f"    {'':<4}{'question':<30}{'n':>6}{'mean bp':>9}{'t':>8}"
          f"{'1st half':>10}{'2nd half':>10}")
    verdict1, sanity = {}, True
    for qid, name, who, k_at, k_to, side, kind in Q:
        sel, x, g = question(pooled, k_at, k_to, side)
        mu, t = st.mean(x), cluster_t(x, g)
        h1 = [v for v, d in zip(x, g) if d < cut]
        h2 = [v for v, d in zip(x, g) if d >= cut]
        m1, m2 = (st.mean(h1) if h1 else None), (st.mean(h2) if h2 else None)
        ok = stage1_pass(kind, mu, t, m1, m2)
        verdict1[qid] = (ok, mu, t)
        sanity &= abs(mu) <= SANITY_MAX_BP
        span = "09:15->09:45" if k_to == K_0945 else "09:45->10:45"
        print(f"    {qid:<4}{name + ' ' + span:<30}{len(x):>6}{mu:>+9.2f}"
              f"{fmt_t(t):>8}{m1:>+10.2f}{m2:>+10.2f}   "
              f"[{'PASS' if ok else 'FAIL'}]")
        print(f"    {'':<4}  trades {who}")
    if not sanity:
        print(f"\n    SANITY -- a mean above {SANITY_MAX_BP} bp is a bug until")
        print(f"    proven otherwise. Stopping here.")
        sys.exit(5)

    print(f"\n    reported, not gated:")
    for lab, k_at, k_to in (("09:15", K_0915, K_0945),
                            ("09:45", K_0945, K_1045)):
        _, xw, gw = question(pooled, k_at, k_to, "win")
        _, xl, gl = question(pooled, k_at, k_to, "lose")
        dd, tt = cluster_t_diff(xw, gw, xl, gl)
        print(f"    at {lab}: winners then {st.mean(xw):+.2f} bp (n {len(xw)}),"
              f" losers then {st.mean(xl):+.2f} bp (n {len(xl)}),"
              f" winners - losers {dd:+.2f}  t {fmt_t(tt).strip()}")

    print(f"\n    per instrument (plain t, one trade per date):")
    print(f"    {'instrument':<12}{'Q1':>14}{'Q2':>14}{'Q3':>14}")
    for ins in INSTRUMENTS:
        rows = per.get(ins, [])
        if len(rows) < MIN_EVENTS:
            continue
        cells = []
        for qid, _, _, k_at, k_to, side, _ in Q:
            _, x, _ = question(rows, k_at, k_to, side)
            cells.append(f"{st.mean(x):+6.2f} {fmt_t(plain_t(x)).strip():>6}")
        print(f"    {ins:<12}" + "".join(f"{c:>14}" for c in cells))
    print(f"\n    per release (clustered t):")
    for rl in ("CPI", "NFP"):
        rows = [r for r in pooled if rl in r[2].split("+")]
        cells = []
        for qid, _, _, k_at, k_to, side, _ in Q:
            _, x, g = question(rows, k_at, k_to, side)
            cells.append(f"{st.mean(x):+6.2f} {fmt_t(cluster_t(x, g)).strip():>6}")
        print(f"    {rl:<12}" + "".join(f"{c:>14}" for c in cells))

    print(f"\n    NOT REGISTERED -- added for Dave's hold-time question, no")
    print(f"    verdict: ALL trades, 09:45 -> 10:45, winners and losers")
    x = [r[3]["m"][K_1045] - r[3]["m"][K_0945] for r in pooled]
    print(f"    mean {st.mean(x):+.2f} bp   t {fmt_t(cluster_t(x, dates)).strip()}"
          f"   n {len(x)}")

    # ---- Stage 2, Part A ------------------------------------------------
    A = [rule_a(r[3]) for r in pooled]
    win = [r for r, v in zip(pooled, A) if v > 0]
    lose = [r for r, v in zip(pooled, A) if v <= 0]
    print(f"\n  STAGE 2 PART A -- money left on the table. HINDSIGHT. "
          f"Descriptive only.")
    fin = [rule_a(r[3]) for r in win]
    best = [r[3]["mfe"] for r in win]
    left = [b_ - f for b_, f in zip(best, fin)]
    print(f"    rule A winners   n {len(win):>5}   closed at {st.mean(fin):+.2f}"
          f" bp   best during the hold {st.mean(best):+.2f}   left on the "
          f"table {st.mean(left):+.2f} (median {st.median(left):+.2f})")
    was_up = [r for r in lose if r[3]["mfe"] >= LOSER_WAS_UP_BP]
    was_dn = [r for r in win if r[3]["mae"] <= -WINNER_WAS_DOWN_BP]
    print(f"    rule A losers    n {len(lose):>5}   {len(was_up) / len(lose):.0%}"
          f" were up at least +{LOSER_WAS_UP_BP:.0f} bp net at some point")
    print(f"    rule A winners   {len(was_dn) / len(win):.0%} were down at "
          f"least {WINNER_WAS_DOWN_BP:.0f} bp at some point on the way")

    # ---- Stage 2, Part B ------------------------------------------------
    print(f"\n  STAGE 2 PART B -- could we have made more without risking "
          f"anything?  (section 6)")
    pa5, worst_a = p5(A), min(A)
    print(f"    {'rule':<22}{'net bp':>8}{'vs A':>8}{'t':>8}{'5th pct':>9}"
          f"{'worst':>9}{'changed':>9}")
    print(f"    {'rule A (time exit)':<22}{st.mean(A):>+8.2f}{'':>8}{'':>8}"
          f"{pa5:>+9.1f}{worst_a:>+9.1f}")
    verdict2 = {}
    for name, fn in RULES:
        R = [fn(r[3]) for r in pooled]
        D = [x - y for x, y in zip(R, A)]
        t = cluster_t(D, dates)
        ok = stage2_pass(st.mean(D), t, p5(R), pa5, min(R), worst_a)
        verdict2[name] = (ok, st.mean(D), t)
        changed = sum(1 for x in D if x != 0) / len(D)
        print(f"    {name:<22}{st.mean(R):>+8.2f}{st.mean(D):>+8.2f}"
              f"{fmt_t(t):>8}{p5(R):>+9.1f}{min(R):>+9.1f}{changed:>9.0%}"
              f"   [{'PASS' if ok else 'FAIL'}]")
    print(f"\n    per instrument, rule minus A in bp (plain t):")
    print(f"    {'instrument':<12}" + "".join(f"{n.split()[0]:>14}"
                                             for n, _ in RULES))
    for ins in INSTRUMENTS:
        rows = per.get(ins, [])
        if len(rows) < MIN_EVENTS:
            continue
        cells = []
        for _, fn in RULES:
            D = [fn(r[3]) - rule_a(r[3]) for r in rows]
            cells.append(f"{st.mean(D):+6.2f} {fmt_t(plain_t(D)).strip():>6}")
        print(f"    {ins:<12}" + "".join(f"{c:>14}" for c in cells))

    # ---- v26.1 -- the longer holds ---------------------------------------
    print(f"\n  AMENDMENT v26.1 -- does the fade keep going after 09:45?")
    hx_rows = [r for r in pooled if r[4] is not None]
    print(f"    {len(hx_rows):,} of {len(pooled):,} trades have every hour "
          f"mark to 15:45")

    def hx_stat(rows):
        x = [r[4][K_1545][0] - r[4][K_0945][0] for r in rows]
        g = [r[1] for r in rows]
        h1 = [v for v, d in zip(x, g) if d < cut]
        h2 = [v for v, d in zip(x, g) if d >= cut]
        return (st.mean(x), cluster_t(x, g),
                st.mean(h1) if h1 else None, st.mean(h2) if h2 else None,
                len(x))

    hx_mu, hx_t, hx_1, hx_2, hx_n = hx_stat(hx_rows)
    hx_ok = (hx_t is not None and hx_1 is not None and hx_2 is not None
             and hx_mu > 0 and hx_t >= T_HX and hx_1 > 0 and hx_2 > 0)
    print(f"    HX  m(15:45) - m(09:45), all trades   n {hx_n}   "
          f"{hx_mu:+.2f} bp   t {fmt_t(hx_t).strip()}   halves "
          f"{hx_1:+.2f} / {hx_2:+.2f}   [{'PASS' if hx_ok else 'FAIL'}]")
    xm, xt, x1, x2, xn = hx_stat([r for r in hx_rows
                                  if r[0] != "SPX500_USD"])
    print(f"        without SPX500_USD (declared, v26.1 s2)   n {xn}   "
          f"{xm:+.2f} bp   t {fmt_t(xt).strip()}   halves {x1:+.2f} / "
          f"{x2:+.2f}")
    if abs(hx_mu) > SANITY_MAX_BP:
        print(f"\n    SANITY -- a mean above {SANITY_MAX_BP} bp. Stopping.")
        sys.exit(5)

    def clock(k):
        return (dt.datetime(2020, 1, 1, 8, 30) + BAR * k).strftime("%H:%M")

    print(f"\n    the shape of the average trade -- descriptive, no verdict")
    print(f"    {'at the open of':<16}{'gross':>8}{'in profit':>11}{'SD':>8}"
          f"{'net':>8}{'net Sharpe/yr':>15}")
    for k in K_HOURS:
        gm = [r[4][k][0] for r in hx_rows]
        nt = [r[4][k][1] for r in hx_rows]
        sh = st.mean(nt) / st.stdev(nt) * math.sqrt(24)
        print(f"    {clock(k):<16}{st.mean(gm):>+8.2f}"
              f"{sum(1 for v in gm if v > 0) / len(gm):>11.0%}"
              f"{st.stdev(gm):>8.1f}{st.mean(nt):>+8.2f}{sh:>15.2f}"
              + ("   <- rule A" if k == K_0945 else ""))
    print(f"\n    after 09:45, by where the trade stood at 09:45 (mean bp):")
    print(f"    {'':<24}" + "".join(f"{clock(k):>8}" for k in K_HOURS[1:]))
    for lab, keep in (("winning at 09:45", lambda r: r[4][K_0945][0] > 0),
                      ("losing at 09:45", lambda r: r[4][K_0945][0] < 0)):
        rows = [r for r in hx_rows if keep(r)]
        print(f"    {lab + f' (n {len(rows)})':<24}" + "".join(
            f"{st.mean(r[4][k][0] - r[4][K_0945][0] for r in rows):>+8.2f}"
            for k in K_HOURS[1:]))

    # ---- verdict --------------------------------------------------------
    print(f"\n  VERDICT -- gates frozen in PREREGISTRATION_v26")
    for qid, (ok, mu, t) in verdict1.items():
        print(f"    [{'PASS' if ok else 'FAIL'}] {qid}  {mu:+.2f} bp  "
              f"t {fmt_t(t).strip()}")
    for name, (ok, mu, t) in verdict2.items():
        print(f"    [{'PASS' if ok else 'FAIL'}] {name}  {mu:+.2f} bp vs A  "
              f"t {fmt_t(t).strip()}")
    print(f"    [{'PASS' if hx_ok else 'FAIL'}] HX (v26.1)  {hx_mu:+.2f} bp "
          f"after 09:45  t {fmt_t(hx_t).strip()}")


if __name__ == "__main__":
    main()
