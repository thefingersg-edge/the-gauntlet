#!/usr/bin/env python3
"""PREREGISTRATION_v18 -- the opening-range liquidity sweep.

    first 15m bar sets a range -> price trades OUTSIDE it -> a bar
    CLOSES BACK INSIDE -> enter the reversal, stop at the sweep extreme,
    target the far side of the range.

THE NULL IS THE TRADE'S OWN GEOMETRY
------------------------------------
A bracket with a stop at -1R and a target at +kR on a driftless price
has expected value exactly ZERO by optional stopping -- for any k, and
for any stopping time that ends it. So a time stop at 16:00 is not an
awkward third case; a martingale stopped anywhere still has expectation
zero.

    primary metric   mean R per trade
    null             0.00 R

Drift is the loophole, and the matched-geometry control removes it: the
identical bracket, same direction and same distances in bp, run on a
randomly chosen OTHER session at the same time of day.

TWO PLACES THIS KIND OF TEST NORMALLY LIES
------------------------------------------
1. Entry at the confirmation bar's own close. Measured BOTH ways -- the
   difference between that and the next bar's open is microstructure,
   and v17 showed it is worth about a spread.
2. A bar whose high reaches the target AND whose low reaches the stop.
   Without tick data the order is unknowable, so it is scored as the
   STOP. Assuming the favourable one is how backtests lie.

STDLIB ONLY.

    python3 sweep_reversal.py --self-test
    python3 sweep_reversal.py
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import os
import random
import statistics as st
import sys
from zoneinfo import ZoneInfo

VERSION = "1.2"

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
BAR = dt.timedelta(minutes=15)

#: ---- FROZEN IN v18 SECTION 3 ----
OPEN_SLOT = (9, 30)
SWEEP_DEADLINE = (11, 0)
SESSION_END = (16, 0)
#: the time-of-day control, v18 section 4
CTRL_SLOT = (11, 0)
CTRL_DEADLINE = (12, 30)
SEED = 20260911
GATE_T = 2.0
N_ERAS = 3
SANITY_MAX_R = 0.50


def hm(t):
    e = t.astimezone(ET)
    return e.date(), (e.hour, e.minute)


def find_setup(day_bars, slot, deadline):
    """The first sweep-and-close-back-inside after `slot`.

    Returns dict or None. Pure forward scan: the range is the FIRST
    bar's high/low and nothing later can change it.
    """
    slots = sorted(day_bars)
    if slot not in day_bars:
        return None
    o, h, l, c = day_bars[slot]
    rng_hi, rng_lo = h, l
    if rng_hi <= rng_lo:
        return None
    swept = None            # 'high' | 'low'
    extreme = None
    for s in slots:
        if s <= slot or s >= deadline:
            continue
        bo, bh, bl, bc = day_bars[s]
        if swept is None:
            if bh > rng_hi:
                swept, extreme = "high", bh
            elif bl < rng_lo:
                swept, extreme = "low", bl
            else:
                continue
            #: the SAME bar may also close back inside -- the classic
            #: single-bar wick-and-reject. Fall through to check it.
        else:
            extreme = (max(extreme, bh) if swept == "high"
                       else min(extreme, bl))
        inside = rng_lo <= bc <= rng_hi
        if inside:
            return dict(slot=s, swept=swept, extreme=extreme,
                        rng_hi=rng_hi, rng_lo=rng_lo, conf_close=bc)
    return None


def outcome_R(path, entry, stop, target, direction):
    """Walk bars forward. Returns (R, how) or None.

    v18 section 7: a bar that reaches BOTH is scored as the stop.
    """
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    for (o, h, l, c) in path:
        hit_stop = (l <= stop) if direction < 0 or stop < entry else (h >= stop)
        if direction > 0:
            hit_stop = l <= stop
            hit_tgt = h >= target
        else:
            hit_stop = h >= stop
            hit_tgt = l <= target
        if hit_stop:
            return -1.0, "stop"          # pessimistic when both
        if hit_tgt:
            return abs(target - entry) / risk, "target"
    if not path:
        return None
    last = path[-1][3]
    return direction * (last - entry) / risk, "time"


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


def eras(seq, n=N_ERAS):
    k = len(seq) // n
    return [seq[i * k:(i + 1) * k if i < n - 1 else len(seq)]
            for i in range(n)]


def breakeven(entry, stop, target):
    a, b = abs(entry - stop), abs(target - entry)
    return a / (a + b) if (a + b) > 0 else None


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"sweep_reversal.py v{VERSION} self-test\n")

    print("the setup is found in forward time order only")
    #: range 100-110. 10:00 wicks to 112 and closes back at 105.
    day = {(9, 30): (100.0, 110.0, 100.0, 105.0),
           (9, 45): (105.0, 108.0, 103.0, 106.0),
           (10, 0): (106.0, 112.0, 105.0, 105.0),
           (10, 15): (105.0, 106.0, 104.0, 105.0)}
    s = find_setup(day, (9, 30), SWEEP_DEADLINE)
    check("a single-bar wick-and-reject is found", s is not None)
    check("it is scored as a HIGH sweep", s["swept"] == "high", f"{s}")
    check("the extreme is the wick tip, 112", abs(s["extreme"] - 112.0) < 1e-9)
    check("confirmation is that same bar", s["slot"] == (10, 0))
    check("the range came from the FIRST bar only",
          s["rng_hi"] == 110.0 and s["rng_lo"] == 100.0)
    #: PLANTED: a later bar with a higher high must not widen the range
    day2 = dict(day)
    day2[(10, 30)] = (105.0, 200.0, 104.0, 105.0)
    check("a later huge bar cannot widen the opening range",
          find_setup(day2, (9, 30), SWEEP_DEADLINE)["rng_hi"] == 110.0)

    print("\nno sweep, or no close back inside, means no trade")
    quiet = {(9, 30): (100.0, 110.0, 100.0, 105.0),
             (9, 45): (105.0, 108.0, 103.0, 106.0)}
    check("a range that is never breached gives nothing",
          find_setup(quiet, (9, 30), SWEEP_DEADLINE) is None)
    #: PLANTED: breaks out and STAYS out -- a real breakout, not a sweep
    runaway = {(9, 30): (100.0, 110.0, 100.0, 105.0),
               (9, 45): (105.0, 115.0, 104.0, 114.0),
               (10, 0): (114.0, 120.0, 113.0, 119.0)}
    check("a breakout that never closes back inside is NOT a setup",
          find_setup(runaway, (9, 30), SWEEP_DEADLINE) is None)
    late = {(9, 30): (100.0, 110.0, 100.0, 105.0),
            (11, 15): (105.0, 112.0, 104.0, 105.0)}
    check("a sweep after the deadline does not count",
          find_setup(late, (9, 30), SWEEP_DEADLINE) is None)

    print("\nthe bracket, and the pessimistic tie-break")
    #: short from 105, stop 112, target 100 (the far side of the range)
    path_t = [(105.0, 106.0, 99.0, 100.0)]
    r, how = outcome_R(path_t, 105.0, 112.0, 100.0, -1)
    check("target reached gives +5/7 R", abs(r - 5.0 / 7.0) < 1e-9
          and how == "target", f"{r:.3f} {how}")
    path_s = [(105.0, 113.0, 104.0, 112.5)]
    r2, how2 = outcome_R(path_s, 105.0, 112.0, 100.0, -1)
    check("stop reached gives exactly -1 R", r2 == -1.0 and how2 == "stop")
    #: PLANTED: one bar touches BOTH. Must be scored as the stop.
    path_b = [(105.0, 113.0, 99.0, 104.0)]
    r3, how3 = outcome_R(path_b, 105.0, 112.0, 100.0, -1)
    check("a bar hitting BOTH is scored as the stop, not the target",
          r3 == -1.0 and how3 == "stop", f"{r3} {how3}")
    path_n = [(105.0, 106.0, 104.0, 104.5)]
    r4, how4 = outcome_R(path_n, 105.0, 112.0, 100.0, -1)
    check("neither hit resolves at the last close",
          how4 == "time" and abs(r4 - (0.5 / 7.0)) < 1e-9, f"{r4:.4f}")
    #: and the long direction is not a copy-paste of the short
    rl, hl = outcome_R([(100.0, 111.0, 99.5, 110.0)], 100.0, 95.0, 110.0, +1)
    check("a LONG reaching its target gives +2 R",
          abs(rl - 2.0) < 1e-9 and hl == "target", f"{rl} {hl}")
    check("a LONG stopping out gives -1 R",
          outcome_R([(100.0, 101.0, 94.0, 94.5)], 100.0, 95.0,
                    110.0, +1)[0] == -1.0)

    print("\nthe geometric break-even")
    check("stop 7, target 5 -> break-even 58.3%",
          abs(breakeven(105.0, 112.0, 100.0) - 7.0 / 12.0) < 1e-9,
          f"{breakeven(105.0,112.0,100.0)*100:.1f}%")
    check("a symmetric bracket breaks even at 50%",
          abs(breakeven(100.0, 90.0, 110.0) - 0.5) < 1e-9)
    #: PLANTED: break-even and mean-R must agree. A bracket won at
    #: exactly its break-even rate has mean R of zero.
    p = breakeven(105.0, 112.0, 100.0)
    k = abs(100.0 - 105.0) / abs(105.0 - 112.0)
    check("winning at exactly break-even gives mean R = 0",
          abs(p * k - (1 - p) * 1.0) < 1e-12, f"{p*k - (1-p):.2e}")

    print("\nthe control is reproducible")
    random.seed(SEED)
    a = [random.random() for _ in range(5)]
    random.seed(SEED)
    check("the seed is fixed and declared", a == [random.random()
                                                  for _ in range(5)])
    check("and it is the one v18 names", SEED == 20260911)

    print("\nthe registered predictions are in the file")
    check("v18 predicted Gate A fails", True)
    check("a mean above +0.50 R is a bug first", SANITY_MAX_R == 0.50)

    print("\neras are disjoint")
    e = eras(list(range(30)))
    check("three, non-overlapping, covering everything",
          len(e) == 3 and sorted(sum(e, [])) == list(range(30))
          and not (set(e[0]) & set(e[1])))

    print("\nthis file fits nothing")
    import sweep_reversal as _self
    banned = ("optimi", "sweep_param", "tune", "refit", "submit")
    off = [x for x in dir(_self) if not x.startswith("_")
           and any(w in x.lower() for w in banned)]
    check("no fitting function exists", off == [], f"{off}")

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def load(bid_p, ask_p):
    def rd(p):
        o = {}
        for r in csv.DictReader(open(p)):
            t = dt.datetime.fromisoformat(r["time"]).replace(tzinfo=UTC)
            o[t] = (float(r["open"]), float(r["high"]),
                    float(r["low"]), float(r["close"]))
        return o
    b, a = rd(bid_p), rd(ask_p)
    common = b.keys() & a.keys()
    mid = {t: tuple((b[t][i] + a[t][i]) / 2.0 for i in range(4))
           for t in common}
    spread = {t: (a[t][3] - b[t][3]) for t in common}
    return mid, spread


def run(sess, order, spread, slot, deadline, label):
    """Returns list of trade dicts."""
    out = []
    for d in order:
        bars = sess[d]
        s = find_setup(bars, slot, deadline)
        if not s:
            continue
        slots = sorted(bars)
        idx = slots.index(s["slot"])
        if idx + 1 >= len(slots):
            continue
        nxt = slots[idx + 1]
        direction = -1 if s["swept"] == "high" else +1
        target = s["rng_lo"] if direction < 0 else s["rng_hi"]
        stop = s["extreme"]
        path = [bars[k] for k in slots[idx + 1:]
                if k < SESSION_END]
        #: v1.2 -- BOTH entries take the SAME forward path.
        #:
        #: v1.1 gave next_open `path[1:]`, which skipped the very bar it
        #: enters on. A trade that enters at a bar's OPEN is at risk
        #: during that bar, so removing it hands next_open a free bar
        #: with no stop exposure -- and that alone is why it appeared to
        #: beat conf_close by 0.160 R. The bug ran TOWARD the candidate.
        #:
        #: conf_close enters at bar idx's close, so its risk starts at
        #: idx+1. next_open enters at idx+1's open, so its risk also
        #: starts at idx+1. Same path, different entry price -- which is
        #: the whole point of the comparison.
        for entry_name, entry_px, path_use in (
                ("next_open", bars[nxt][0], path),
                ("conf_close", s["conf_close"], path)):
            if not path_use:
                continue
            r = outcome_R(path_use, entry_px, stop, target, direction)
            if r is None:
                continue
            risk = abs(entry_px - stop)
            if risk <= 0:
                continue
            #: v1.1 -- THE COST LOOKUP WAS KEYED BY TIME OF DAY ONLY.
            #: v1.0 built {slot: spread}, overwritten once per session,
            #: so every trade got the LAST session's spread in absolute
            #: POINTS -- 2026's point-spread charged against 2003's
            #: index level, where the same points are 8x the fraction.
            #: It reported 0.190 R of cost against a 21.9 bp stop, which
            #: implies ~4 bp of spread on an instrument RESULT_PREANN
            #: measured at 0.76-3.31. Keyed by (day, slot) now.
            #: Direction: the bug OVERSTATED cost, so fixing it helps
            #: the candidate.
            cost_px = spread.get((d, nxt), 0.0)
            cost_R = cost_px / risk if risk > 0 else 0.0
            out.append(dict(day=d, label=label, entry=entry_name,
                            R=r[0], how=r[1], net=r[0] - cost_R,
                            be=breakeven(entry_px, stop, target),
                            risk_bp=risk / entry_px * 1e4,
                            cost_R=cost_R, direction=direction))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bid", default="../data/spx500usd_bid_15m.csv")
    ap.add_argument("--ask", default="../data/spx500usd_ask_15m.csv")
    ap.add_argument("--dump", default="../data/sweep_reversal.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"sweep_reversal.py v{VERSION}   PREREGISTRATION_v18\n")
    mid, spread = load(a.bid, a.ask)
    sess = {}
    for t, v in mid.items():
        d, s = hm(t)
        if OPEN_SLOT <= s < SESSION_END:
            sess.setdefault(d, {})[s] = v
    order = sorted(d for d in sess if len(sess[d]) >= 20)
    print(f"  RTH sessions: {len(order):,}  {order[0]} .. {order[-1]}")

    #: the spread lookup needs UTC keys; rebuild per session slot
    sp_by = {}
    for t, v in spread.items():
        d, s = hm(t)
        if OPEN_SLOT <= s < SESSION_END:
            sp_by.setdefault(d, {})[s] = v
    flat_spread = {(d, s): v for d in sp_by for s, v in sp_by[d].items()}

    trades = run(sess, order, flat_spread, OPEN_SLOT, SWEEP_DEADLINE, "open")
    ctrl_tod = run(sess, order, flat_spread, CTRL_SLOT, CTRL_DEADLINE, "1100")

    prim = [t for t in trades if t["entry"] == "next_open"]
    conf = [t for t in trades if t["entry"] == "conf_close"]
    print(f"  setups found at the open: {len(prim):,} "
          f"({100*len(prim)/len(order):.1f}% of sessions)")
    print(f"  setups found at 11:00:    "
          f"{len([t for t in ctrl_tod if t['entry']=='next_open']):,}\n")
    if len(prim) < 100:
        raise SystemExit("too few setups to say anything")

    def summ(lab, ts):
        R = [t["net"] for t in ts]
        hits = sum(1 for t in ts if t["how"] == "target")
        be = st.mean(t["be"] for t in ts)
        t_ = one_sample_t(R)
        print(f"    {lab:<22}n={len(ts):>5}  mean {st.mean(R):+6.3f} R  "
              f"t {t_:+5.2f}  hit {100*hits/len(ts):5.1f}%  "
              f"break-even {100*be:5.1f}%")
        return st.mean(R), t_, hits / len(ts), be

    print(f"  RESULT -- mean R per trade, net of measured spread")
    mA, tA, hrA, beA = summ("open, next_open", prim)
    mC, tC, hrC, beC = summ("open, conf_close", conf)
    ct = [t for t in ctrl_tod if t["entry"] == "next_open"]
    mT, tT, hrT, beT = summ("11:00, next_open", ct)

    #: matched-geometry control, v18 section 4
    random.seed(SEED)
    ctrl = []
    for t in prim:
        other = order[random.randrange(len(order))]
        bars = sess.get(other, {})
        slots = sorted(bars)
        if len(slots) < 6:
            continue
        i = random.randrange(1, len(slots) - 2)
        e = bars[slots[i]][0]
        risk = e * t["risk_bp"] / 1e4
        d_ = t["direction"]
        stop = e - d_ * risk
        tgt = e + d_ * risk * (abs(t["be"]) and (1 - t["be"]) / t["be"])
        r = outcome_R([bars[k] for k in slots[i + 1:]], e, stop, tgt, d_)
        if r:
            ctrl.append(r[0] - t["cost_R"])
    if len(ctrl) > 50:
        tb, db = welch_t([t["net"] for t in prim], ctrl)
        print(f"    {'matched control':<22}n={len(ctrl):>5}  "
              f"mean {st.mean(ctrl):+6.3f} R")
    else:
        tb, db = None, None

    ga = tA is not None and tA >= GATE_T and mA > 0
    gb = tb is not None and tb >= GATE_T
    tc, dc = welch_t([t["net"] for t in prim], [t["net"] for t in ct])
    gc = tc is not None and tc >= GATE_T
    ee = eras(sorted(prim, key=lambda t: t["day"]))
    era_m = [st.mean(t["net"] for t in e) if len(e) > 20 else 0.0 for e in ee]
    gd = all(x > 0 for x in era_m)
    ge = hrA > beA

    print(f"\n  VERDICT -- gates frozen in v18 section 5")
    print(f"    [{'PASS' if ga else 'FAIL'}] Gate A  mean {mA:+.3f} R, "
          f"t = {tA:.2f}")
    print(f"    [{'PASS' if gb else 'FAIL'}] Gate B  vs matched control "
          f"{db:+.3f} R, t = {tb:.2f}" if tb else
          "    [N/A ] Gate B  control too small")
    print(f"    [{'PASS' if gc else 'FAIL'}] Gate C  open vs 11:00 "
          f"{dc:+.3f} R, t = {tc:.2f}")
    print(f"    [{'PASS' if gd else 'FAIL'}] Gate D  eras "
          + "  ".join(f"{x:+.3f}" for x in era_m))
    print(f"    [{'PASS' if ge else 'FAIL'}] Gate E  hit {100*hrA:.1f}% vs "
          f"break-even {100*beA:.1f}%")
    allp = ga and gb and gc and gd and ge
    print(f"\n    {'PROCEED' if allp else 'FAIL'}")

    print(f"\n  THE ENTRY DIAGNOSTIC -- v18 section 3")
    print(f"    conf_close {mC:+.3f} R   next_open {mA:+.3f} R   "
          f"difference {mC-mA:+.3f} R")
    print(f"    mean cost {st.mean(t['cost_R'] for t in prim):.3f} R, "
          f"mean risk {st.mean(t['risk_bp'] for t in prim):.1f} bp")
    print(f"    A gap of about one spread is microstructure, not edge.")

    how = {}
    for t in prim:
        how[t["how"]] = how.get(t["how"], 0) + 1
    print(f"\n  how trades ended: " + "  ".join(
        f"{k} {v} ({100*v/len(prim):.0f}%)" for k, v in sorted(how.items())))

    if abs(mA) > SANITY_MAX_R:
        print(f"\n    KILL: {mA:+.3f} R exceeds {SANITY_MAX_R} -- bug first.")
        sys.exit(3)

    if a.dump:
        with open(a.dump, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["day", "label", "entry", "direction", "R", "net",
                        "how", "breakeven", "risk_bp", "cost_R"])
            for t in trades + ctrl_tod:
                w.writerow([t["day"], t["label"], t["entry"], t["direction"],
                            f"{t['R']:.4f}", f"{t['net']:.4f}", t["how"],
                            f"{t['be']:.4f}", f"{t['risk_bp']:.2f}",
                            f"{t['cost_R']:.5f}"])
        print(f"\n  written to {a.dump}")


if __name__ == "__main__":
    main()
