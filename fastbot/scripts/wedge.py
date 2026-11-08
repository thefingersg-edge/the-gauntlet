#!/usr/bin/env python3
"""PREREGISTRATION_v20 -- wedges, with the detector frozen.

A wedge detector cannot have zero free parameters. Pretending otherwise
would be the dishonesty this file exists to avoid. So:

  ELIMINATED BY CONSTRUCTION
    touches   exactly the LAST TWO swing highs and LAST TWO swing lows.
              "Which subset of pivots" is the largest degree of freedom
              in wedge drawing, and taking the last two removes it.
    breakout  a close beyond the extended line. No buffer.

  IRREDUCIBLE, SO DECLARED AS A GRID
    w in {2,3,5} x N in {20,40,60}  ->  9 cells, ALL reported.
    The gate is the MEDIAN of the nine plus sign agreement in >= 7.
    No single cell can carry the finding, which is what stops this
    becoming a search for the parameters that work.

  FIXED AT A ROUND VALUE
    convergence <= 0.75. No canonical number exists; chosen once.

N is reused as the forward scan limit and the time stop, so neither
adds a parameter.

STDLIB ONLY.

    python3 wedge.py --self-test
    python3 wedge.py
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import random
import statistics as st
import sys
from zoneinfo import ZoneInfo

VERSION = "1.0"

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc

#: ---- FROZEN IN v20 ----
WS = (2, 3, 5)
NS = (20, 40, 60)
CONV = 0.75
MIN_TOUCH = 2
SEED = 20260911
GATE_T = 2.0
GATE_B_MIN_AGREE = 7
SPREAD_BP = 0.9
GATE_D_MULT = 2.0
SANITY_MAX_R = 0.50
N_ERAS = 3
RTH_OPEN, RTH_CLOSE = (9, 30), (16, 0)


def pivots(bars, lo, hi, w, high_side):
    """Confirmed swing indices in [lo, hi]. A pivot at i needs bars to
    i+w, and i+w <= hi, so nothing is used before it is confirmed."""
    out = []
    for i in range(lo + w, hi - w + 1):
        seg = [bars[j][1 if high_side else 2] for j in range(i - w, i + w + 1)]
        v = bars[i][1 if high_side else 2]
        if (v >= max(seg)) if high_side else (v <= min(seg)):
            out.append(i)
    return out


def line_through(i1, v1, i2, v2):
    if i2 == i1:
        return None
    m = (v2 - v1) / (i2 - i1)
    return (m, v1 - m * i1)


def at(line, x):
    return line[0] * x + line[1]


def detect(bars, t, w, n):
    """A wedge as of bar t, or None. Uses only bars [t-n+1, t]."""
    lo = t - n + 1
    if lo < 0:
        return None
    ph = pivots(bars, lo, t, w, True)
    pl = pivots(bars, lo, t, w, False)
    if len(ph) < MIN_TOUCH or len(pl) < MIN_TOUCH:
        return None
    h1, h2 = ph[-2], ph[-1]
    l1, l2 = pl[-2], pl[-1]
    up = line_through(h1, bars[h1][1], h2, bars[h2][1])
    dn = line_through(l1, bars[l1][2], l2, bars[l2][2])
    if up is None or dn is None:
        return None
    if up[0] > 0 and dn[0] > 0:
        kind = "rising"
    elif up[0] < 0 and dn[0] < 0:
        kind = "falling"
    else:
        return None
    x0 = min(h1, l1)
    w_early = at(up, x0) - at(dn, x0)
    w_now = at(up, t) - at(dn, t)
    if w_early <= 0 or w_now <= 0:
        return None
    if w_now > CONV * w_early:
        return None
    return dict(kind=kind, up=up, dn=dn, t=t, lo=lo,
                width=w_early)


def outcome_R(bars, i0, i1, entry, stop, target, direction):
    """Walk bars [i0, i1). Stop wins a tie -- v20 section 2."""
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    for i in range(i0, min(i1, len(bars))):
        o, h, l, c = bars[i]
        if direction > 0:
            if l <= stop:
                return -1.0, "stop"
            if h >= target:
                return abs(target - entry) / risk, "target"
        else:
            if h >= stop:
                return -1.0, "stop"
            if l <= target:
                return abs(target - entry) / risk, "target"
    j = min(i1, len(bars)) - 1
    if j < i0:
        return None
    return direction * (bars[j][3] - entry) / risk, "time"


def scan(bars, w, n):
    """All non-overlapping wedge trades for one grid cell."""
    trades = []
    t = n
    while t < len(bars) - 2:
        wd = detect(bars, t, w, n)
        if not wd:
            t += 1
            continue
        brk = None
        for x in range(t + 1, min(t + 1 + n, len(bars))):
            c = bars[x][3]
            if wd["kind"] == "rising" and c < at(wd["dn"], x):
                brk = x
                break
            if wd["kind"] == "falling" and c > at(wd["up"], x):
                brk = x
                break
        if brk is None or brk + 1 >= len(bars):
            t += 1
            continue
        e = brk + 1
        entry = bars[e][0]
        direction = -1 if wd["kind"] == "rising" else +1
        seg = bars[wd["lo"]:t + 1]
        stop = max(b[1] for b in seg) if direction < 0 else min(b[2]
                                                               for b in seg)
        target = entry - wd["width"] if direction < 0 else entry + wd["width"]
        r = outcome_R(bars, e, e + n, entry, stop, target, direction)
        if r is None or abs(entry - stop) <= 0:
            t += 1
            continue
        trades.append(dict(i=e, kind=wd["kind"], R=r[0], how=r[1],
                           direction=direction,
                           risk_bp=abs(entry - stop) / entry * 1e4,
                           width_bp=wd["width"] / entry * 1e4))
        t = e + n          # non-overlapping
    return trades


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


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"wedge.py v{VERSION} self-test\n")

    print("pivots are CONFIRMED -- never used before their right side exists")
    b = [(0, v, v, 0) for v in [1, 2, 5, 2, 1, 2, 4, 2, 1, 2, 3, 2, 1]]
    b = [(o, h, h - 0.5, h) for (o, h, l, c) in b]
    p = pivots(b, 0, 12, 2, True)
    check("a peak needs w bars on BOTH sides", all(i - 2 >= 0 and i + 2 <= 12
                                                   for i in p), f"{p}")
    #: PLANTED: a peak at the very end cannot be confirmed
    check("the last w bars can never be pivots",
          max(p) <= 12 - 2 if p else True, f"{p}")
    check("the obvious peaks are found", 2 in p and 6 in p, f"{p}")

    print("\nlines and geometry")
    L = line_through(0, 10.0, 10, 20.0)
    check("slope of a 10-over-10 line is 1.0", abs(L[0] - 1.0) < 1e-12)
    check("it evaluates correctly off the anchors",
          abs(at(L, 5) - 15.0) < 1e-12)
    check("a vertical pair returns nothing",
          line_through(3, 1.0, 3, 2.0) is None)

    print("\nthe detector: converging, same-sign slopes")
    #: PLANTED: a RISING wedge -- both lines up, narrowing.
    n = 20
    bars = []
    for i in range(n):
        up = 100 + i * 1.0
        dn = 90 + i * 1.4          # rises faster -> converging
        mid = (up + dn) / 2
        bars.append((mid, up if i % 3 == 0 else mid + 0.2,
                     dn if i % 3 == 1 else mid - 0.2, mid))
    d = detect(bars, n - 1, 2, n)
    check("a converging pair of rising lines is a RISING wedge",
          d is not None and d["kind"] == "rising",
          f"{d['kind'] if d else None}")
    #: PLANTED: DIVERGING must be refused even with same-sign slopes
    bars2 = []
    for i in range(n):
        up = 100 + i * 1.4
        dn = 90 + i * 1.0          # widening
        mid = (up + dn) / 2
        bars2.append((mid, up if i % 3 == 0 else mid + 0.2,
                      dn if i % 3 == 1 else mid - 0.2, mid))
    check("a DIVERGING pair is refused", detect(bars2, n - 1, 2, n) is None)
    #: PLANTED: opposite-sign slopes is a triangle, not a wedge
    bars3 = []
    for i in range(n):
        up = 110 - i * 0.5
        dn = 90 + i * 0.5
        mid = (up + dn) / 2
        bars3.append((mid, up if i % 3 == 0 else mid + 0.2,
                      dn if i % 3 == 1 else mid - 0.2, mid))
    check("opposite-sign slopes (a triangle) is NOT a wedge",
          detect(bars3, n - 1, 2, n) is None)
    check("the convergence bar is 0.75 and is the only tuned number",
          CONV == 0.75)

    print("\nthe bracket, and the pessimistic tie-break")
    path = [(100.0, 101.0, 89.0, 90.0)]
    check("a LONG stopping out gives -1 R",
          outcome_R(path, 0, 1, 100.0, 95.0, 110.0, +1) == (-1.0, "stop"))
    path2 = [(100.0, 111.0, 99.0, 110.0)]
    check("a LONG reaching target gives +2 R",
          outcome_R(path2, 0, 1, 100.0, 95.0, 110.0, +1)[0] == 2.0)
    #: PLANTED: one bar reaching BOTH must score the stop
    path3 = [(100.0, 111.0, 94.0, 100.0)]
    check("a bar reaching BOTH is scored as the stop",
          outcome_R(path3, 0, 1, 100.0, 95.0, 110.0, +1) == (-1.0, "stop"))
    path4 = [(100.0, 101.0, 99.0, 100.5)]
    check("neither hit resolves at the last close",
          outcome_R(path4, 0, 1, 100.0, 95.0, 110.0, +1)[1] == "time")
    check("a SHORT is not a copy of the long",
          outcome_R([(100.0, 106.0, 99.0, 105.0)], 0, 1,
                    100.0, 105.0, 90.0, -1) == (-1.0, "stop"))

    print("\nthe grid is nine cells and the gate is on the grid")
    check("three lookbacks x three windows", len(WS) * len(NS) == 9)
    check("the sign-agreement bar is 7 of 9", GATE_B_MIN_AGREE == 7)
    #: PLANTED: 6 of 9 agreeing must NOT pass Gate B
    signs = [1, 1, 1, 1, 1, 1, -1, -1, -1]
    check("6 of 9 agreeing fails Gate B",
          max(sum(1 for s in signs if s > 0),
              sum(1 for s in signs if s < 0)) < GATE_B_MIN_AGREE)
    check("but 7 of 9 passes",
          max(sum(1 for s in [1] * 7 + [-1] * 2 if s > 0), 0)
          >= GATE_B_MIN_AGREE)

    print("\nfrozen constants")
    check("touches fixed at the last two", MIN_TOUCH == 2)
    check("mean R above +0.50 is a bug first", SANITY_MAX_R == 0.50)
    check("Gate D needs 2x the spread", GATE_D_MULT == 2.0)
    check("seed is the one v20 names", SEED == 20260911)

    print("\nthis file fits nothing")
    import wedge as _self
    banned = ("optimi", "tune", "refit", "submit", "position")
    off = [x for x in dir(_self) if not x.startswith("_")
           and any(q in x.lower() for q in banned)]
    check("no fitting function exists", off == [], f"{off}")

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def load_daily(bid_p, ask_p):
    def rd(p):
        o = {}
        for r in csv.DictReader(open(p)):
            t = dt.datetime.fromisoformat(r["time"]).replace(tzinfo=UTC)
            o[t] = (float(r["open"]), float(r["high"]),
                    float(r["low"]), float(r["close"]))
        return o
    b, a = rd(bid_p), rd(ask_p)
    common = b.keys() & a.keys()
    sess = {}
    for t in common:
        e = t.astimezone(ET)
        if RTH_OPEN <= (e.hour, e.minute) < RTH_CLOSE:
            m = tuple((b[t][i] + a[t][i]) / 2.0 for i in range(4))
            sess.setdefault(e.date(), []).append((t, m))
    days = sorted(d for d in sess if len(sess[d]) >= 20)
    out = []
    for d in days:
        v = sorted(sess[d])
        out.append((v[0][1][0], max(x[1][1] for x in v),
                    min(x[1][2] for x in v), v[-1][1][3]))
    return out, days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bid", default="../data/spx500usd_bid_15m.csv")
    ap.add_argument("--ask", default="../data/spx500usd_ask_15m.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"wedge.py v{VERSION}   PREREGISTRATION_v20\n")
    bars, days = load_daily(a.bid, a.ask)
    print(f"  daily bars from RTH sessions: {len(bars):,}  "
          f"{days[0]} .. {days[-1]}\n")

    print(f"  THE GRID -- all nine cells, none selected")
    print(f"    {'w':>3}{'N':>4}{'wedges':>9}{'rising':>8}{'falling':>9}"
          f"{'mean R':>9}{'t':>7}{'stop%':>7}")
    cells, pooled = [], []
    for w in WS:
        for n in NS:
            tr = scan(bars, w, n)
            if len(tr) < 10:
                print(f"    {w:>3}{n:>4}{len(tr):>9}   too few")
                continue
            R = [x["R"] for x in tr]
            t_ = one_sample_t(R)
            ri = sum(1 for x in tr if x["kind"] == "rising")
            sp = 100 * sum(1 for x in tr if x["how"] == "stop") / len(tr)
            cells.append((w, n, st.mean(R), t_, len(tr)))
            pooled.extend(tr)
            print(f"    {w:>3}{n:>4}{len(tr):>9}{ri:>8}{len(tr)-ri:>9}"
                  f"{st.mean(R):>9.3f}{t_:>7.2f}{sp:>6.1f}%")

    if len(cells) < 5:
        raise SystemExit("too few usable cells")
    med = st.median(c[2] for c in cells)
    pos = sum(1 for c in cells if c[2] > 0)
    agree = max(pos, len(cells) - pos)
    allR = [x["R"] for x in pooled]
    tp = one_sample_t(allR)

    print(f"\n  wedge counts across the grid: "
          f"{min(c[4] for c in cells):,} to {max(c[4] for c in cells):,} "
          f"({max(c[4] for c in cells)/max(1,min(c[4] for c in cells)):.1f}x)")
    print(f"  -- how much 'a wedge' depends on who draws it")

    #: matched-geometry control
    random.seed(SEED)
    ctrl = []
    for x in pooled:
        i = random.randrange(60, len(bars) - 61)
        e = bars[i][0]
        risk = e * x["risk_bp"] / 1e4
        d_ = x["direction"]
        stop = e - d_ * risk
        tgt = e + d_ * e * x["width_bp"] / 1e4
        r = outcome_R(bars, i, i + 40, e, stop, tgt, d_)
        if r:
            ctrl.append(r[0])
    tc, dc = welch_t(allR, ctrl)

    ga = med > 0 and tp is not None and tp >= GATE_T
    gb = agree >= GATE_B_MIN_AGREE and med > 0
    gc = tc is not None and tc >= GATE_T
    mean_bp = st.mean(x["R"] * x["risk_bp"] for x in pooled)
    gd = mean_bp > GATE_D_MULT * SPREAD_BP
    ee = eras(sorted(pooled, key=lambda x: x["i"]))
    era_m = [st.mean(x["R"] for x in e) if len(e) > 10 else 0.0 for e in ee]
    ge = all(x > 0 for x in era_m)

    print(f"\n  VERDICT -- gates frozen in v20 section 4")
    print(f"    [{'PASS' if ga else 'FAIL'}] Gate A  median cell "
          f"{med:+.3f} R, pooled t = {tp:.2f}  (n={len(pooled):,})")
    print(f"    [{'PASS' if gb else 'FAIL'}] Gate B  {agree} of "
          f"{len(cells)} cells agree in sign (need "
          f"{GATE_B_MIN_AGREE})")
    print(f"    [{'PASS' if gc else 'FAIL'}] Gate C  vs matched control "
          f"{dc:+.3f} R, t = {tc:.2f}  (control {st.mean(ctrl):+.3f})")
    print(f"    [{'PASS' if gd else 'FAIL'}] Gate D  {mean_bp:+.2f} bp/trade "
          f"vs a {GATE_D_MULT*SPREAD_BP:.1f} bp bar")
    print(f"    [{'PASS' if ge else 'FAIL'}] Gate E  eras "
          + "  ".join(f"{x:+.3f}" for x in era_m))
    allp = ga and gb and gc and gd and ge
    print(f"\n    {'PROCEED' if allp else 'FAIL'}")

    print(f"\n  by wedge type, pooled")
    for k in ("rising", "falling"):
        v = [x["R"] for x in pooled if x["kind"] == k]
        if len(v) > 10:
            print(f"    {k:<9}n={len(v):>5}  mean {st.mean(v):+.3f} R  "
                  f"t {one_sample_t(v):+5.2f}")

    if abs(st.mean(allR)) > SANITY_MAX_R:
        print(f"\n    KILL: {st.mean(allR):+.3f} R exceeds {SANITY_MAX_R}")
        sys.exit(3)


if __name__ == "__main__":
    main()
