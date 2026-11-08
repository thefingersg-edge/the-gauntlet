#!/usr/bin/env python3
"""PREREGISTRATION_v17 -- the opening "liquidity candle".

Tests the premise under the rule: does a large opening 15m candle
predict a reversal, is that about the OPEN or about the SIZE, and does
prior context separate the successes from the failures?

WHY THE GRID IS THE DESIGN
--------------------------
The precondition check found the 09:30 bar's median range is 0.260 of
ATR14 against a 0.25 threshold -- it fires on 54% of days -- and that
intraday range follows the usual U-shape (0.260 open, 0.136 midday).

So **"a big candle at the open" and "the open" are nearly the same
statement.** A single filter cannot tell which is doing the work. Bars
are therefore bucketed by time of day AND by size quartile computed
*within* that slot, and the two claims are separated:

    Gate B   is 09:30 different from midday, at the same relative size?
    Gate C   at 09:30, is big different from small?

Gate C is the video's actual claim. If it fails the threshold is
decoration.

THE MICROSTRUCTURE TRAP
-----------------------
Selecting bars by large range and then measuring forward return from
that bar's CLOSE manufactures mean reversion out of nothing: a big-range
bar's close sits nearer an extreme, and the spread is wider exactly
then. Entry is therefore the **mid open of the NEXT bar** -- which is
also the only thing anyone could actually trade.

STDLIB ONLY.

    python3 liquidity_candle.py --self-test
    python3 liquidity_candle.py
"""

from __future__ import annotations

import argparse
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

#: ---- FROZEN IN v17 SECTION 3/4 ----
RTH_OPEN, RTH_CLOSE = (9, 30), (16, 0)
ATR_DAYS = 14
H_PRIMARY = 4
H_ROBUST = (1, 12)
THRESHOLD = 0.25                 # the video's rule, for reference only
N_BUCKETS = 4
GATE_T = 2.0
MIDDAY = ((11, 0), (11, 15), (11, 30), (11, 45),
          (12, 0), (12, 15), (12, 30), (12, 45),
          (13, 0), (13, 15), (13, 30), (13, 45), (14, 0))
SANITY_MAX_BP = 30.0
N_ERAS = 3
#: v17 section 5
HAMMER_RATIO = 2.0
DISCOVERY_TO = 2014
ALPHA = 0.05
#: measured in RESULT_PREANN; Gate E needs twice it
SPREAD_BP_RECENT = 0.9


def session_slot(t_utc):
    e = t_utc.astimezone(ET)
    hm = (e.hour, e.minute)
    if RTH_OPEN <= hm < RTH_CLOSE:
        return e.date(), hm
    return None, None


def atr_from(day_ranges, days, i):
    """Mean of the PREVIOUS ATR_DAYS daily ranges. Never includes day i."""
    if i < ATR_DAYS:
        return None
    v = [day_ranges[days[j]] for j in range(i - ATR_DAYS, i)]
    return st.mean(v) if v else None


def rev_bp(o_sig, c_sig, entry, exit_):
    """Reversal in bp: positive means the move went AGAINST the bar."""
    if entry <= 0 or exit_ <= 0 or c_sig == o_sig:
        return None
    d = 1.0 if c_sig > o_sig else -1.0
    return -d * (exit_ / entry - 1.0) * 1e4


def candle_shape(o, h, l, c):
    """('hammer'|'inverted'|'neither', close_location_value)."""
    rng = h - l
    if rng <= 0:
        return "neither", 0.5
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    clv = (c - l) / rng
    if lower >= HAMMER_RATIO * body and upper <= body:
        return "hammer", clv
    if upper >= HAMMER_RATIO * body and lower <= body:
        return "inverted", clv
    return "neither", clv


def buckets(values, n=N_BUCKETS):
    """Boundaries splitting `values` into n equal-count buckets."""
    v = sorted(values)
    if len(v) < n:
        return []
    return [v[int(len(v) * k / n)] for k in range(1, n)]


def bucket_of(x, bounds):
    b = 0
    for e in bounds:
        if x >= e:
            b += 1
    return b


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


def norm_p(t):
    """Two-sided p from a normal approximation. Stdlib only."""
    if t is None:
        return 1.0
    return 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(t) / math.sqrt(2.0))))


def holm(pvals, alpha=ALPHA):
    """Holm-Bonferroni. Returns [(name, p, reject)] in input order."""
    order = sorted(range(len(pvals)), key=lambda i: pvals[i][1])
    n = len(pvals)
    out = {}
    still = True
    for rank, i in enumerate(order):
        name, p = pvals[i]
        thresh = alpha / (n - rank)
        if still and p <= thresh:
            out[name] = (p, True, thresh)
        else:
            still = False
            out[name] = (p, False, thresh)
    return [(nm, *out[nm]) for nm, _ in pvals]


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

    print(f"liquidity_candle.py v{VERSION} self-test\n")

    print("ATR uses only PRIOR days")
    days = [dt.date(2020, 1, d) for d in range(1, 21)]
    rngs = {d: 10.0 for d in days}
    #: PLANTED: day 15 has a huge range. Its OWN atr must not see it.
    rngs[days[15]] = 1000.0
    check("a huge day does not inflate its own ATR",
          abs(atr_from(rngs, days, 15) - 10.0) < 1e-9,
          f"{atr_from(rngs, days, 15)}")
    check("but the NEXT day's ATR does see it",
          atr_from(rngs, days, 16) > 10.0,
          f"{atr_from(rngs, days, 16):.1f}")
    check("the first 14 days have no ATR at all",
          atr_from(rngs, days, 13) is None
          and atr_from(rngs, days, 14) is not None)

    print("\nthe reversal sign convention")
    #: PLANTED: an UP bar followed by a fall is a reversal (positive).
    check("up bar, price falls 10bp -> +10 reversal",
          abs(rev_bp(100.0, 101.0, 100.0, 99.9) - 10.0) < 1e-6,
          f"{rev_bp(100.0,101.0,100.0,99.9):.2f}")
    check("up bar, price rises 10bp -> -10 (continuation)",
          abs(rev_bp(100.0, 101.0, 100.0, 100.1) + 10.0) < 1e-6)
    check("DOWN bar, price rises 10bp -> +10 reversal",
          abs(rev_bp(101.0, 100.0, 100.0, 100.1) - 10.0) < 1e-6,
          f"{rev_bp(101.0,100.0,100.0,100.1):.2f}")
    check("a doji (close == open) has no direction and is skipped",
          rev_bp(100.0, 100.0, 100.0, 101.0) is None)

    print("\nthe candle geometry, frozen at 2x")
    #: a long lower wick, small body at the top
    check("a hammer is detected",
          candle_shape(10.0, 10.2, 8.0, 10.1)[0] == "hammer",
          f"{candle_shape(10.0,10.2,8.0,10.1)}")
    check("an inverted hammer is detected",
          candle_shape(10.0, 12.0, 9.9, 10.1)[0] == "inverted")
    check("a plain wide-body candle is neither",
          candle_shape(10.0, 12.0, 8.0, 11.9)[0] == "neither")
    #: PLANTED: close location value must be 1.0 at the high, 0 at the low
    check("close at the high gives CLV 1.0",
          abs(candle_shape(10.0, 12.0, 8.0, 12.0)[1] - 1.0) < 1e-9)
    check("close at the low gives CLV 0.0",
          abs(candle_shape(10.0, 12.0, 8.0, 8.0)[1]) < 1e-9)
    check("a zero-range bar does not divide by zero",
          candle_shape(10.0, 10.0, 10.0, 10.0) == ("neither", 0.5))

    print("\nsize buckets are equal-count")
    vals = list(range(100))
    bd = buckets(vals)
    got = [sum(1 for v in vals if bucket_of(v, bd) == b) for b in range(4)]
    check("four buckets of 25", got == [25, 25, 25, 25], f"{got}")
    check("the smallest value is in bucket 0", bucket_of(0, bd) == 0)
    check("the largest is in bucket 3", bucket_of(99, bd) == 3)

    print("\nHolm actually corrects")
    #: PLANTED: ten p-values with one at 0.03. Uncorrected it "passes";
    #: Holm must reject it, because 0.03 > 0.05/10.
    ten = [(f"f{i}", 0.6) for i in range(9)] + [("lucky", 0.03)]
    res = {nm: rej for nm, p, rej, th in holm(ten)}
    check("p=0.03 among ten is REJECTED by Holm",
          res["lucky"] is False)
    check("but p=0.001 among ten survives",
          {nm: r for nm, p, r, t in
           holm([(f"f{i}", 0.6) for i in range(9)]
                + [("real", 0.001)])}["real"] is True)
    check("and the strongest is tested at alpha/n",
          abs(holm(ten)[9][3] - ALPHA / 10) < 1e-12,
          f"{holm(ten)[9][3]:.4f}")
    #: PLANTED: Holm must stop at the first failure. v1.0's first
    #: fixture was (0.001, 0.02, 0.03), which Holm rejects ENTIRELY and
    #: correctly -- 0.02 <= 0.05/2 and 0.03 <= 0.05/1. The expectation
    #: was wrong, not the arithmetic. This fixture actually stops:
    #: 0.03 > 0.05/2, so b fails and c is not tested.
    seq = [("a", 0.001), ("b", 0.03), ("c", 0.04)]
    r2 = {nm: rj for nm, p, rj, t in holm(seq)}
    check("a chain stops at the first non-rejection",
          r2["a"] and not r2["b"] and not r2["c"], f"{r2}")
    check("and the step-down thresholds are alpha/(n-rank)",
          [round(t, 6) for nm, p, rj, t in holm(seq)]
          == [round(ALPHA / 3, 6), round(ALPHA / 2, 6), round(ALPHA, 6)])
    check("c is not rejected even though 0.04 < alpha alone",
          not r2["c"] and 0.04 < ALPHA)

    print("\ndiscovery and confirmation are disjoint")
    d = [y for y in range(2003, 2027) if y <= DISCOVERY_TO]
    c = [y for y in range(2003, 2027) if y > DISCOVERY_TO]
    check("no year is in both", set(d) & set(c) == set())
    check("together they cover the span", len(d) + len(c) == 24)
    check("discovery ends 2014", max(d) == 2014 and min(c) == 2015)

    print("\neras are disjoint (AUDIT.md)")
    e = eras(list(range(30)))
    check("three, non-overlapping, covering everything",
          len(e) == 3 and sorted(sum(e, [])) == list(range(30))
          and not (set(e[0]) & set(e[1])))

    print("\nthe entry price is never the signal bar's close")
    src = open(os.path.abspath(__file__)).read()
    check("rev_bp takes entry and exit as separate arguments",
          "def rev_bp(o_sig, c_sig, entry, exit_)" in src)
    #: PLANTED: if entry were c_sig this would be 0 by construction
    check("entry and signal close are independent inputs",
          rev_bp(100.0, 101.0, 101.5, 101.5) == 0.0)

    print("\nthis file holds no position and fits nothing")
    import liquidity_candle as _self
    banned = ("optimi", "sweep", "tune", "refit", "order", "submit",
              "position")
    off = [x for x in dir(_self) if not x.startswith("_")
           and any(w in x.lower() for w in banned)]
    check("no fitting or trading function exists", off == [], f"{off}")

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
    return {t: tuple((b[t][i] + a[t][i]) / 2.0 for i in range(4))
            for t in common}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bid", default="../data/spx500usd_bid_15m.csv")
    ap.add_argument("--ask", default="../data/spx500usd_ask_15m.csv")
    ap.add_argument("--dump", default="../data/liquidity_candle.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"liquidity_candle.py v{VERSION}   PREREGISTRATION_v17\n")
    mid = load(a.bid, a.ask)
    print(f"  mid bars: {len(mid):,}")

    sess = {}
    for t, v in mid.items():
        d, hm = session_slot(t)
        if d:
            sess.setdefault(d, {})[hm] = (t, v)
    days = sorted(d for d in sess if len(sess[d]) >= 20)
    print(f"  RTH sessions: {len(days):,}  {days[0]} .. {days[-1]}")
    drange = {d: (max(v[1][1] for v in sess[d].values())
                  - min(v[1][2] for v in sess[d].values())) for d in days}

    #: build every bar-observation
    obs = []
    for i, d in enumerate(days):
        atr = atr_from(drange, days, i)
        if not atr or atr <= 0:
            continue
        slots = sorted(sess[d])
        for hm in slots:
            t, (o, h, l, c) = sess[d][hm]
            nxt = mid.get(t + BAR)
            ex = mid.get(t + BAR * H_PRIMARY)
            if not nxt or not ex:
                continue
            r = rev_bp(o, c, nxt[0], ex[3])
            if r is None:
                continue
            shape, clv = candle_shape(o, h, l, c)
            obs.append(dict(day=d, hm=hm, ratio=(h - l) / atr, rev=r,
                            shape=shape, clv=clv, year=d.year))
    print(f"  usable bar-observations: {len(obs):,}\n")

    #: size quartiles WITHIN each time slot -- v17 section 3
    byslot = {}
    for x in obs:
        byslot.setdefault(x["hm"], []).append(x)
    for hm, xs in byslot.items():
        bd = buckets([x["ratio"] for x in xs])
        for x in xs:
            x["q"] = bucket_of(x["ratio"], bd) if bd else 0

    def cell(hms, q):
        return [x["rev"] for x in obs if x["hm"] in hms and x["q"] == q]

    OPEN = (RTH_OPEN,)
    print(f"  REVERSAL (bp) at H={H_PRIMARY} bars, by slot and size "
          f"quartile within slot")
    print(f"    {'slot':<8}{'Q1 small':>11}{'Q2':>9}{'Q3':>9}"
          f"{'Q4 big':>10}{'Q4-Q1':>9}{'t':>7}")
    for lab, hms in (("09:30", OPEN), ("10:00", ((10, 0),)),
                     ("midday", MIDDAY), ("15:45", ((15, 45),))):
        cells = [cell(hms, q) for q in range(4)]
        if min(len(c) for c in cells) < 30:
            continue
        t, diff = welch_t(cells[3], cells[0])
        print(f"    {lab:<8}" + "".join(f"{st.mean(c):>10.2f}" for c in cells)
              + f"{diff:>10.2f}{t:>7.2f}")

    q4o = cell(OPEN, 3)
    q1o = cell(OPEN, 0)
    q4m = cell(MIDDAY, 3)
    ta = one_sample_t(q4o)
    ga = ta is not None and ta >= GATE_T
    tb, db = welch_t(q4o, q4m)
    gb = tb is not None and tb >= GATE_T
    tc, dc = welch_t(q4o, q1o)
    gc = tc is not None and tc >= GATE_T

    print(f"\n  VERDICT -- gates frozen in v17 section 4")
    print(f"    [{'PASS' if ga else 'FAIL'}] Gate A  09:30 Q4 mean "
          f"{st.mean(q4o):+.2f} bp, t = {ta:.2f}  (n={len(q4o)})")
    print(f"    [{'PASS' if gb else 'FAIL'}] Gate B  open minus midday "
          f"{db:+.2f} bp, t = {tb:.2f}   <- is it the OPEN?")
    print(f"    [{'PASS' if gc else 'FAIL'}] Gate C  big minus small at "
          f"09:30 {dc:+.2f} bp, t = {tc:.2f}   <- is it the SIZE?")

    ordered = sorted(obs, key=lambda x: x["day"])
    op = [x for x in ordered if x["hm"] == RTH_OPEN]
    ee = eras(op)
    era_d = []
    for e in ee:
        h = [x["rev"] for x in e if x["q"] == 3]
        lo = [x["rev"] for x in e if x["q"] == 0]
        era_d.append(st.mean(h) - st.mean(lo) if len(h) > 5 and len(lo) > 5
                     else 0.0)
    gd = all(x > 0 for x in era_d)
    print(f"    [{'PASS' if gd else 'FAIL'}] Gate D  eras "
          + "  ".join(f"{x:+.2f}" for x in era_d))
    ge = dc > 2 * SPREAD_BP_RECENT
    print(f"    [{'PASS' if ge else 'FAIL'}] Gate E  {dc:+.2f} bp vs "
          f"2x spread ({2*SPREAD_BP_RECENT:.1f} bp)")

    allp = ga and gb and gc and gd and ge
    print(f"\n    {'PROCEED' if allp else 'FAIL'}")
    if abs(st.mean(q4o)) > SANITY_MAX_BP:
        print(f"\n    KILL: {st.mean(q4o):+.2f} exceeds {SANITY_MAX_BP} bp "
              f"-- treat as a bug first. v17 section 6.")
        sys.exit(3)

    print(f"\n  ROBUSTNESS at the pre-specified horizons (not gates)")
    for H in H_ROBUST:
        vals = []
        for x in op:
            d = x["day"]
            t = sess[d][x["hm"]][0]
            n2, e2 = mid.get(t + BAR), mid.get(t + BAR * H)
            if not n2 or not e2:
                continue
            o, _, _, c = sess[d][x["hm"]][1]
            r = rev_bp(o, c, n2[0], e2[3])
            if r is not None:
                vals.append((x["q"], r))
        hi = [r for q, r in vals if q == 3]
        lo = [r for q, r in vals if q == 0]
        if len(hi) > 30 and len(lo) > 30:
            t2, d2 = welch_t(hi, lo)
            print(f"    H={H:>2} bars  Q4 {st.mean(hi):+6.2f}  "
                  f"Q1 {st.mean(lo):+6.2f}  diff {d2:+6.2f}  t {t2:+5.2f}")

    print(f"\n  THE 25% RULE AS STATED, for reference")
    fired = [x["rev"] for x in op if x["ratio"] >= THRESHOLD]
    notf = [x["rev"] for x in op if x["ratio"] < THRESHOLD]
    if len(fired) > 30 and len(notf) > 30:
        t3, d3 = welch_t(fired, notf)
        print(f"    fires on {100*len(fired)/len(op):.1f}% of openings  "
              f"({len(fired)} of {len(op)})")
        print(f"    fired {st.mean(fired):+.2f} bp   did not "
              f"{st.mean(notf):+.2f}   diff {d3:+.2f}  t {t3:+.2f}")

    if not ga:
        print(f"\n  PRIOR-CONTEXT SEARCH: NOT RUN.")
        print(f"  v17 section 5 gates it on Gate A. Searching for "
              f"conditions under\n  which a non-existent effect works is "
              f"the fishing the section exists\n  to prevent. Ten "
              f"features, Holm-corrected, on a discovery era, would\n  "
              f"still have produced something -- and it would have meant "
              f"nothing.")

    if a.dump:
        with open(a.dump, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["day", "hm", "ratio", "q", "rev_bp", "shape", "clv"])
            for x in sorted(obs, key=lambda x: (x["day"], x["hm"])):
                w.writerow([x["day"], f"{x['hm'][0]:02d}:{x['hm'][1]:02d}",
                            f"{x['ratio']:.4f}", x["q"], f"{x['rev']:.4f}",
                            x["shape"], f"{x['clv']:.3f}"])
        print(f"\n  written to {a.dump}")


if __name__ == "__main__":
    main()
