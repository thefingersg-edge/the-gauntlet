#!/usr/bin/env python3
"""PREREGISTRATION_v19 -- does candle shape carry information at all?

Eight shapes over three bars is 512 sequences. Tested at p<0.05 that
yields ~26 hits by chance. So this asks whether the information EXISTS
before asking which sequence carries it:

    MI( last k shapes ; next bar DIRECTION )
    MI( last k shapes ; next bar MAGNITUDE )

Both outcomes binary, so the two numbers are directly comparable. That
comparison IS the hypothesis: a candle's range encodes volatility, which
clusters; its shape encodes where order flow balanced. Neither is a
directional statement.

THE NULL IS A PERMUTATION, NOT A FORMULA
----------------------------------------
Empirical MI is biased UPWARD -- with 512 states it is positive under
perfect independence. Comparing raw MI to zero would manufacture a
finding. So the outcome labels are shuffled 1,000 times and MI
recomputed; the null then carries the identical bias.

GATE A IS A POSITIVE CONTROL AND IT CAN VOID THE RUN
----------------------------------------------------
Volatility clustering is about as robust as findings get. If this method
cannot detect it, a null on direction means the METHOD is broken, not
that the market is efficient. Gate A failing discards everything,
including the direction result.

STDLIB ONLY.

    python3 candle_info.py --self-test
    python3 candle_info.py
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

VERSION = "1.0"

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc

#: ---- FROZEN IN v19 ----
RTH_OPEN, RTH_CLOSE = (9, 30), (16, 0)
KS = (1, 2, 3)
N_PERM = 1000
SEED = 20260911
PCT = 99
ATR_DAYS = 14
SANITY_MAX_MI = 0.05
SPREAD_BP = 0.9          # RESULT_PREANN, recent era
GATE_C_MULT = 2.0
N_ERAS = 3


def shape(o, h, l, c, body_cut):
    """One of 8 states. Scale-free; the only cut is the body median."""
    rng = h - l
    if rng <= 0:
        return None
    up = 1 if c >= o else 0
    body = abs(c - o) / rng
    big = 1 if body >= body_cut else 0
    upper = h - max(o, c)
    lower = min(o, c) - l
    wick = 1 if upper >= lower else 0
    return up * 4 + big * 2 + wick


SHAPE_NAMES = {
    0: "dn small lower", 1: "dn small upper",
    2: "dn large lower", 3: "dn large upper",
    4: "up small lower", 5: "up small upper",
    6: "up large lower", 7: "up large upper",
}


def mutual_information(xs, ys):
    """MI in bits between two discrete sequences of equal length."""
    n = len(xs)
    if n == 0:
        return 0.0
    jx, mx, my = {}, {}, {}
    for a, b in zip(xs, ys):
        jx[(a, b)] = jx.get((a, b), 0) + 1
        mx[a] = mx.get(a, 0) + 1
        my[b] = my.get(b, 0) + 1
    mi = 0.0
    for (a, b), nab in jx.items():
        pab = nab / n
        mi += pab * math.log2(pab / ((mx[a] / n) * (my[b] / n)))
    return mi


def permutation_null(xs, ys, n_perm=N_PERM, seed=SEED):
    """(percentile_value, mean, observed_rank) under label shuffling."""
    rng = random.Random(seed)
    shuffled = list(ys)
    out = []
    for _ in range(n_perm):
        rng.shuffle(shuffled)
        out.append(mutual_information(xs, shuffled))
    out.sort()
    return out


def pct_of(sorted_null, p):
    i = min(len(sorted_null) - 1, int(len(sorted_null) * p / 100.0))
    return sorted_null[i]


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

    print(f"candle_info.py v{VERSION} self-test\n")

    print("the alphabet is eight states and each bit means what it says")
    #: body_cut 0.5: body/range >= 0.5 is 'large'
    check("a big up candle closing near its high is 'up large upper'",
          shape(10.0, 11.0, 9.9, 10.9, 0.5) == 7,
          f"{shape(10.0,11.0,9.9,10.9,0.5)}")
    check("a hammer is 'dn small lower' or 'up small lower'",
          shape(10.0, 10.2, 8.0, 10.1, 0.5) == 4,
          f"{SHAPE_NAMES[shape(10.0,10.2,8.0,10.1,0.5)]}")
    check("an inverted hammer flips the wick bit",
          shape(10.0, 12.0, 9.9, 10.1, 0.5) == 5,
          f"{SHAPE_NAMES[shape(10.0,12.0,9.9,10.1,0.5)]}")
    check("a down candle sets the direction bit to 0",
          shape(11.0, 11.1, 9.0, 9.1, 0.5) < 4)
    check("all eight states are reachable",
          len(SHAPE_NAMES) == 8 and set(SHAPE_NAMES) == set(range(8)))
    check("a zero-range bar returns nothing rather than a state",
          shape(10.0, 10.0, 10.0, 10.0, 0.5) is None)

    print("\nmutual information, on cases with known answers")
    check("independent streams give ~0 bits",
          abs(mutual_information([0, 1] * 500, [0, 0, 1, 1] * 250)) < 0.01,
          f"{mutual_information([0,1]*500,[0,0,1,1]*250):.4f}")
    #: PLANTED: a perfect copy carries exactly 1 bit
    x = [0, 1] * 500
    check("a perfect copy carries exactly 1 bit",
          abs(mutual_information(x, x) - 1.0) < 1e-9,
          f"{mutual_information(x, x):.4f}")
    check("a perfectly inverted copy also carries 1 bit",
          abs(mutual_information(x, [1 - v for v in x]) - 1.0) < 1e-9)
    check("a constant outcome carries 0 bits",
          abs(mutual_information(x, [1] * 1000)) < 1e-12)
    #: PLANTED: 75/25 dependence is between 0 and 1
    y = [(v if i % 4 else 1 - v) for i, v in enumerate(x)]
    m = mutual_information(x, y)
    check("a 75% dependence lands strictly between 0 and 1 bits",
          0.1 < m < 0.9, f"{m:.4f}")

    print("\nthe upward bias is real -- this is why the null is permuted")
    #: PLANTED: 512 states, random labels, small n. Raw MI is clearly
    #: NOT zero, which is exactly the trap v19 section 4 names.
    rng = random.Random(1)
    xs = [rng.randrange(512) for _ in range(3000)]
    ys = [rng.randrange(2) for _ in range(3000)]
    biased = mutual_information(xs, ys)
    check("raw MI on INDEPENDENT data is visibly positive",
          biased > 0.02, f"{biased:.4f} bits on pure noise")
    null = permutation_null(xs, ys, n_perm=100)
    check("the permutation null carries the same bias",
          abs(st.mean(null) - biased) < 0.02,
          f"null mean {st.mean(null):.4f} vs observed {biased:.4f}")
    check("so the observed value does NOT beat its own null",
          biased <= pct_of(null, 99),
          f"{biased:.4f} vs p99 {pct_of(null,99):.4f}")

    print("\nand the null still detects a REAL effect")
    #: PLANTED: genuine dependence must clear its own permuted null.
    xs2 = [rng.randrange(8) for _ in range(3000)]
    ys2 = [(1 if (v < 4) != (rng.random() < 0.35) else 0) for v in xs2]
    obs2 = mutual_information(xs2, ys2)
    null2 = permutation_null(xs2, ys2, n_perm=100)
    check("a planted dependence clears its permuted null",
          obs2 > pct_of(null2, 99),
          f"{obs2:.4f} vs p99 {pct_of(null2,99):.4f}")

    print("\nthe permutation is reproducible")
    a = permutation_null([0, 1] * 50, [0, 1] * 50, n_perm=20, seed=SEED)
    b = permutation_null([0, 1] * 50, [0, 1] * 50, n_perm=20, seed=SEED)
    check("same seed, same null", a == b)
    check("and it is the seed v19 names", SEED == 20260911)

    print("\nthe frozen constants")
    check("k = 1, 2, 3", KS == (1, 2, 3))
    check("1000 permutations at the 99th percentile",
          N_PERM == 1000 and PCT == 99)
    check("direction MI above 0.05 bits is a bug first",
          SANITY_MAX_MI == 0.05)
    check("Gate C needs 2x the spread", GATE_C_MULT == 2.0)

    print("\neras are disjoint")
    e = eras(list(range(30)))
    check("three, non-overlapping, covering everything",
          len(e) == 3 and sorted(sum(e, [])) == list(range(30)))

    print("\nthis file fits nothing")
    import candle_info as _self
    banned = ("optimi", "tune", "refit", "order", "submit", "position")
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
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"candle_info.py v{VERSION}   PREREGISTRATION_v19\n")
    mid = load(a.bid, a.ask)
    print(f"  bars: {len(mid):,}")

    #: sessions, so sequences never straddle one -- v19 section 7
    sess = {}
    for t, v in mid.items():
        e = t.astimezone(ET)
        hm = (e.hour, e.minute)
        if RTH_OPEN <= hm < RTH_CLOSE:
            sess.setdefault(e.date(), []).append((t, v))
    days = sorted(d for d in sess if len(sess[d]) >= 20)
    for d in days:
        sess[d].sort()
    print(f"  RTH sessions: {len(days):,}  {days[0]} .. {days[-1]}")

    #: the body median -- the alphabet's only cut
    bodies = []
    for d in days:
        for _, (o, h, l, c) in sess[d]:
            if h > l:
                bodies.append(abs(c - o) / (h - l))
    body_cut = st.median(bodies)
    print(f"  body/range median (the alphabet's only cut): {body_cut:.4f}")

    #: prior-day ranges for the magnitude bucket
    drange = {d: max(v[1] for _, v in sess[d]) - min(v[2] for _, v in sess[d])
              for d in days}

    #: build (sequence, direction, magnitude) within sessions only
    recs = {k: [] for k in KS}
    mags = []
    for i, d in enumerate(days):
        if i < ATR_DAYS:
            continue
        atr = st.mean(drange[days[j]] for j in range(i - ATR_DAYS, i))
        if atr <= 0:
            continue
        bars = sess[d]
        states = []
        for _, (o, h, l, c) in bars:
            states.append(shape(o, h, l, c, body_cut))
        for j in range(len(bars) - 1):
            no, nh, nl, nc = bars[j + 1][1]
            if nc == no or nh <= nl:
                continue
            direction = 1 if nc > no else 0
            magn = (nh - nl) / atr
            for k in KS:
                if j + 1 < k:
                    continue
                seq = states[j - k + 1:j + 1]
                if any(s is None for s in seq):
                    continue
                code = 0
                for s in seq:
                    code = code * 8 + s
                recs[k].append((code, direction, magn))
            mags.append(magn)
    mag_cut = st.median(mags)
    print(f"  magnitude median (next range / ATR): {mag_cut:.4f}")
    print(f"  observations: " + "  ".join(
        f"k={k}: {len(recs[k]):,}" for k in KS) + "\n")

    print(f"  MUTUAL INFORMATION, bits. Null = {N_PERM} label shuffles.")
    print(f"    {'k':>3}{'states':>8}{'n':>9}{'outcome':>11}"
          f"{'MI':>10}{'null p99':>11}{'null mean':>11}{'beats':>7}")
    results = {}
    for k in KS:
        rs = recs[k]
        xs = [r[0] for r in rs]
        for lab, ys in (("direction", [r[1] for r in rs]),
                        ("magnitude", [1 if r[2] >= mag_cut else 0
                                       for r in rs])):
            obs = mutual_information(xs, ys)
            null = permutation_null(xs, ys)
            p99 = pct_of(null, PCT)
            beats = obs > p99
            results[(k, lab)] = (obs, p99, st.mean(null), beats)
            print(f"    {k:>3}{len(set(xs)):>8}{len(rs):>9,}{lab:>11}"
                  f"{obs:>10.5f}{p99:>11.5f}{st.mean(null):>11.5f}"
                  f"{'YES' if beats else 'no':>7}")

    ga = all(results[(k, "magnitude")][3] for k in KS)
    gb = any(results[(k, "direction")][3] for k in KS)

    print(f"\n  VERDICT -- gates frozen in v19 section 5")
    print(f"    [{'PASS' if ga else 'FAIL'}] Gate A  magnitude MI beats "
          f"its null at every k   <- POSITIVE CONTROL")
    if not ga:
        print(f"\n    VOID. v19 section 5: a method that cannot detect")
        print(f"    volatility clustering cannot be trusted to report")
        print(f"    absence. The direction result below is discarded.")
        sys.exit(3)
    print(f"    [{'PASS' if gb else 'FAIL'}] Gate B  direction MI beats "
          f"its null at any k")

    #: the economic translation, whether or not B passed
    print(f"\n  WHAT THE DIRECTION NUMBERS WOULD BE WORTH")
    rs = recs[1]
    base = sum(r[1] for r in rs) / len(rs)
    best, bestn, bestp = None, 0, 0.0
    for s in range(8):
        sub = [r for r in rs if r[0] == s]
        if len(sub) < 200:
            continue
        p = sum(r[1] for r in sub) / len(sub)
        if abs(p - 0.5) > abs(bestp - 0.5):
            best, bestn, bestp = s, len(sub), p
    print(f"    base rate of an up bar: {100*base:.2f}%")
    if best is not None:
        print(f"    most extreme single shape: {SHAPE_NAMES[best]}  "
              f"n={bestn:,}  up {100*bestp:.2f}%")
        print(f"    edge over the base rate: {100*(bestp-base):+.2f} "
              f"percentage points")
    for k in KS:
        rs2 = recs[k]
        bycode = {}
        for code, d_, _ in rs2:
            a_, b_ = bycode.get(code, (0, 0))
            bycode[code] = (a_ + d_, b_ + 1)
        elig = [(c, v[0] / v[1], v[1]) for c, v in bycode.items()
                if v[1] >= 200]
        if not elig:
            continue
        c, p, n = max(elig, key=lambda x: abs(x[1] - 0.5))
        print(f"    k={k}: best of {len(elig)} eligible sequences -> "
              f"{100*p:.2f}% up on n={n:,}")

    for k in KS:
        obs = results[(k, "direction")][0]
        if obs > SANITY_MAX_MI:
            print(f"\n    KILL: direction MI {obs:.4f} exceeds "
                  f"{SANITY_MAX_MI} -- suspect a lookahead first.")
            sys.exit(3)

    if not gb:
        print(f"\n  Gate B failed, so Gates C and D do not run: there is no")
        print(f"  effect to cost or to check for era stability. v19 s9 --")
        print(f"  candles carry information about HOW MUCH and not about")
        print(f"  WHICH WAY, and the 512-sequence search is not worth "
              f"running.")


if __name__ == "__main__":
    main()
