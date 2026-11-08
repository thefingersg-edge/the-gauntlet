#!/usr/bin/env python3
"""PREREGISTRATION_v34 -- the v33 lenses as GENERAL intraday signals.

No event calendar. Every US cash session, SPX500 / NAS100 / US30, 5m bars.

A. VWAP / POC MAGNET. At 10:30, 11:30, 12:30, 13:30, 14:30 ET measure the
   distance from price to the session VWAP (and POC) built from bars that
   closed before that time. Trade TOWARD the level when the distance is in
   the top fifth of its own trailing 250-day history at that slot; exit 60
   minutes later. Direction is fixed in advance: toward the level.

B. RULE OF 16. Levels = prior cash close +/- (prior VIX close / 16) %. The
   first 5m close beyond a level (09:30-14:50) is the event; enter at the
   next open, exit 60 minutes later. Fade or follow is decided by the
   2005-2012 discovery era's sign and then held fixed for 2013-2026.

Gated on 2013-01-01 .. 2026-09-17, NET of the bid/ask actually quoted.
Frozen in PREREGISTRATION_v34.md, sha256 checked before any return is read.

    python3 general_levels.py --self-test
    python3 general_levels.py --budget     # volatility and counts only
    python3 general_levels.py
"""

from __future__ import annotations

import argparse
import bisect
import csv
import datetime as dt
import hashlib
import math
import os
import re
import statistics as st
import sys

import numpy as np

from premarket_factor import regress, tstat
from premarket_levels import vwap, poc, to_et, read_vix, vix_before

VERSION = "1.0"
DOC = ("PREREGISTRATION_v34.md", "546725b24f667016fe4e96266b75d296b4aa882010a3065c26c0e4314362f3d3")
INSTR = ("spx500usd", "nas100usd", "us30usd")
SLOTS = ("10:30", "11:30", "12:30", "13:30", "14:30")
HOLD = dt.timedelta(minutes=60)
TRAIL, QUANT = 250, 0.80
DISC_END = dt.date(2012, 12, 31)
HOLD_END = dt.date(2026, 9, 17)
ERAS = ((2013, 2017), (2018, 2021), (2022, 2026))
EXCL = (2020, 2021)
T_GATE, T_REPL = 2.39, 1.64
MIN_BARS = 70
VIX_FILE = "../data/VIXCLS.csv"

_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)


def _guard(names):
    bad = sorted(n for n in names if _FORBIDDEN.search(n))
    if bad:
        raise SystemExit(f"namespace guard: {bad}")


def load(data_dir, ins):
    """days[d] = {hm: (mid o,h,l,c, vol, bid_o, ask_o)} for 09:30..15:55 ET."""
    ask = {}
    with open(os.path.join(data_dir, f"{ins}_ask_5m.csv")) as fh:
        rd = csv.reader(fh)
        next(rd)
        for r in rd:
            if 13 <= int(r[0][11:13]) <= 20:
                ask[r[0]] = tuple(float(x) for x in r[1:5])
    days = {}
    with open(os.path.join(data_dir, f"{ins}_bid_5m.csv")) as fh:
        rd = csv.reader(fh)
        next(rd)
        for r in rd:
            if not 13 <= int(r[0][11:13]) <= 20 or r[0] not in ask:
                continue
            e = to_et(r[0])
            t = e.time()
            if t < dt.time(9, 30) or t > dt.time(15, 55):
                continue
            b = tuple(float(x) for x in r[1:5])
            a = ask[r[0]]
            m = tuple((b[i] + a[i]) / 2 for i in range(4))
            days.setdefault(e.date(), {})[e.strftime("%H:%M")] = (
                m[0], m[1], m[2], m[3], float(r[5]), b[0], a[0])
    return {d: v for d, v in days.items() if len(v) >= MIN_BARS}


def hm_add(hm, delta):
    t = dt.datetime.strptime(hm, "%H:%M") + delta
    return t.strftime("%H:%M")


def net_bp(bar_in, bar_out, side):
    """Pay the quoted spread: long buys ask / sells bid, short the reverse."""
    if side > 0:
        return (bar_out[5] / bar_in[6] - 1.0) * 1e4
    return -(bar_out[6] / bar_in[5] - 1.0) * 1e4


def gross_bp(bar_in, bar_out, side):
    return side * (bar_out[0] / bar_in[0] - 1.0) * 1e4


def trailing_cut(hist, x):
    """Is |x| in the top fifth of the PRIOR TRAIL values? None until full."""
    if len(hist) < TRAIL:
        return None
    w = sorted(hist[-TRAIL:])
    return abs(x) >= w[int(QUANT * TRAIL)]


def magnet_rows(days, ins):
    out, hist = [], {}
    for d in sorted(days):
        bars = days[d]
        for s in SLOTS:
            x = hm_add(s, HOLD)
            if s not in bars or x not in bars:
                continue
            prior = [(v[1], v[2], v[3], v[4]) for hm, v in bars.items() if hm < s]
            if len(prior) < 10:
                continue
            P = bars[s][0]
            for lens, L in (("VWAP", vwap(prior)), ("POC", poc(prior, P))):
                if L is None:
                    continue
                D = (L / P - 1.0) * 1e4
                h = hist.setdefault((lens, s), [])
                cut = trailing_cut(h, D)
                h.append(abs(D))
                side = 1 if D > 0 else -1
                out.append(dict(lens=lens, ins=ins, date=d, slot=s, D=D,
                                trade=cut, side=side,
                                fwd=(bars[x][0] / P - 1.0) * 1e4,
                                gross=gross_bp(bars[s], bars[x], side),
                                net=net_bp(bars[s], bars[x], side),
                                spread=(bars[s][6] / bars[s][5] - 1.0) * 1e4))
    return out


def r16_rows(days, ins, vix):
    out, ds = [], sorted(days)
    for i in range(1, len(ds)):
        d, prev = ds[i], days[ds[i - 1]]
        if "15:55" not in prev:
            continue
        v = vix_before(vix, d)
        if v is None:
            continue
        C, I = prev["15:55"][3], v * 6.25
        up, dn = C * (1 + I / 1e4), C * (1 - I / 1e4)
        bars = days[d]
        for hm in sorted(bars):
            if hm > "14:50":
                break
            c = bars[hm][3]
            if c > up or c < dn:
                ent = hm_add(hm, dt.timedelta(minutes=5))
                x = hm_add(ent, HOLD)
                if ent in bars and x in bars:
                    k = 1 if c > up else -1
                    out.append(dict(ins=ins, date=d, hm=hm, dir=k, I=I,
                                    b_in=bars[ent], b_out=bars[x]))
                break
    return out


def era_of(d):
    return "disc" if d <= DISC_END else ("hold" if d <= HOLD_END else None)


def cl_mean(rows, key):
    """Mean and date-clustered t (intercept-only OLS)."""
    if len(rows) < 30:
        return None, None, len(rows)
    beta, V = regress([r[key] for r in rows], [[1.0] for _ in rows],
                      [r["date"] for r in rows])
    return float(beta[0]), tstat(beta, V, 0), len(rows)


def verdict(hold, eras, ex):
    m, t, _ = hold
    main = m is not None and m > 0 and t is not None and t >= T_GATE
    era_ok = all(e[0] is not None and e[0] > 0 for e in eras)
    ex_ok = ex[0] is not None and ex[0] > 0 and ex[1] is not None and ex[1] >= T_REPL
    if main and era_ok and ex_ok:
        return "PASS"
    return "FAIL" + ("" if not main else " (main passed, eras/ex-2020-21 did not)")


_guard(list(globals()))


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, np.bool_)):
            raise TypeError(name)
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"   {detail}" if detail else ""))

    print(f"general_levels.py v{VERSION} self-test\n")
    bi = (100.0, 0, 0, 0, 0, 99.99, 100.01)
    bo = (101.0, 0, 0, 0, 0, 100.99, 101.01)
    check("long pays the spread: net < gross",
          net_bp(bi, bo, 1) < gross_bp(bi, bo, 1))
    check("short pays the spread: net < gross",
          net_bp(bi, bo, -1) < gross_bp(bi, bo, -1))
    flat = (100.0, 0, 0, 0, 0, 99.99, 100.01)
    check("a flat hour loses exactly the spread",
          abs(net_bp(flat, flat, 1) - (99.99 / 100.01 - 1) * 1e4) < 1e-9 and net_bp(flat, flat, 1) < 0)
    check("trailing cut is None until 250 priors", trailing_cut([1.0] * 249, 5.0) is None)
    check("trailing cut uses PRIOR values only (x itself not in window)",
          trailing_cut(list(range(250)), 199.0) is False
          and trailing_cut(list(range(250)), 200.0) is True)
    check("era split", era_of(dt.date(2012, 12, 31)) == "disc"
          and era_of(dt.date(2013, 1, 2)) == "hold"
          and era_of(dt.date(2026, 9, 18)) is None)
    # r16 on a synthetic day: prior close 100, VIX 16 -> I = 100 bp -> up at 101
    def bar(p):
        return (p, p, p, p, 1.0, p - 0.01, p + 0.01)
    prev = {"15:55": bar(100.0)}
    today = {}
    t = dt.datetime(2020, 1, 3, 9, 30)
    for i in range(78):
        today[(t + dt.timedelta(minutes=5 * i)).strftime("%H:%M")] = bar(100.5)
    today["10:00"] = bar(101.2)
    ev = r16_rows({dt.date(2020, 1, 2): prev, dt.date(2020, 1, 3): today}, "x",
                  [(dt.date(2020, 1, 2), 16.0)])
    check("first close above +1 implied move is the event, entry next bar",
          len(ev) == 1 and ev[0]["hm"] == "10:00" and ev[0]["dir"] == 1
          and ev[0]["b_in"] == today["10:05"] and ev[0]["b_out"] == today["11:05"])
    today2 = dict(today)
    today2["10:00"] = bar(100.9)
    ev2 = r16_rows({dt.date(2020, 1, 2): prev, dt.date(2020, 1, 3): today2}, "x",
                   [(dt.date(2020, 1, 2), 16.0)])
    check("PLANTED: a move inside the band is NOT an event", ev2 == [])
    rng = np.random.default_rng(3)
    good = [dict(date=i // 3, y=0.8 + float(rng.normal(0, 10))) for i in range(9000)]
    noise = [dict(date=i // 3, y=float(rng.normal(0, 10))) for i in range(9000)]
    g, n0 = cl_mean(good, "y"), cl_mean(noise, "y")
    check("a planted +0.8 bp edge is found", g[0] > 0 and g[1] >= T_GATE, f"t {g[1]:+.2f}")
    check("PLANTED FAIL: noise does not pass", not (n0[0] > 0 and n0[1] >= T_GATE),
          f"t {n0[1]:+.2f}")
    check("verdict: a bad era fails the lens",
          verdict((1, 3, 0), [(1, 2, 0), (-1, 0, 0), (1, 2, 0)], (1, 2, 0)).startswith("FAIL"))
    check("verdict: ex-2020-21 weak fails the lens",
          verdict((1, 3, 0), [(1, 2, 0)] * 3, (0.2, 1.0, 0)).startswith("FAIL"))
    check("verdict: all good -> PASS", verdict((1, 3, 0), [(1, 2, 0)] * 3, (1, 2, 0)) == "PASS")
    check("frozen", SLOTS == ("10:30", "11:30", "12:30", "13:30", "14:30")
          and TRAIL == 250 and QUANT == 0.80 and T_GATE == 2.39
          and HOLD == dt.timedelta(minutes=60))
    check("namespace guard", not [n for n in globals() if _FORBIDDEN.search(n)])
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="../data")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--budget", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    here = os.path.dirname(os.path.abspath(__file__))
    print(f"general_levels.py v{VERSION}   PREREGISTRATION_v34\n")
    print("  I am not a financial adviser. This is a measurement, not a")
    print("  recommendation to take a position.\n")
    if not a.budget:
        got = hashlib.sha256(open(os.path.join(here, "..", DOC[0]), "rb").read()).hexdigest()
        if got != DOC[1]:
            print(f"  {DOC[0]} changed since frozen ({got[:12]}). Refused.")
            sys.exit(2)
        print(f"  {DOC[0]} sha256 {got[:16]}... matches\n")
    vix = read_vix(os.path.join(here, VIX_FILE))
    mag, r16 = [], []
    for ins in INSTR:
        days = load(a.data_dir, ins)
        m, r = magnet_rows(days, ins), r16_rows(days, ins, vix)
        mag += m
        r16 += r
        print(f"  {ins:<10} {len(days):>5} sessions  {len(m):>6} magnet slots"
              f"  {len(r):>5} rule-of-16 events")
    for r in mag:
        r["era"] = era_of(r["date"])
    for r in r16:
        r["era"] = era_of(r["date"])

    if a.budget:
        # volatility only: |fwd| scale is direction-free; no sign is read
        print("\n  POWER BUDGET (holdout; SDs and counts only)")
        for lens in ("VWAP", "POC"):
            rs = [r for r in mag if r["lens"] == lens and r["era"] == "hold" and r["trade"]]
            sd = st.stdev(r["fwd"] for r in rs)
            nd = len({r["date"] for r in rs})
            sp = st.median(r["spread"] for r in rs)
            print(f"    {lens:<5} trades {len(rs):>6} on {nd:>5} dates  SD(60m) {sd:5.1f} bp"
                  f"  median spread {sp:.2f} bp  MDE ~ {(T_GATE + .84) * sd / math.sqrt(nd):.2f} bp")
        rs = [r for r in r16 if r["era"] == "hold"]
        sd = st.stdev((r["b_out"][0] / r["b_in"][0] - 1) * 1e4 for r in rs)
        nd = len({r["date"] for r in rs})
        print(f"    R16   trades {len(rs):>6} on {nd:>5} dates  SD(60m) {sd:5.1f} bp"
              f"  MDE ~ {(T_GATE + .84) * sd / math.sqrt(nd):.2f} bp")
        print(f"    disc-era R16 events: {sum(r['era'] == 'disc' for r in r16)}")
        return

    res = {}
    print("\n  A. MAGNET  (trade toward level when |D| in trailing top fifth; 60 min)")
    for lens in ("VWAP", "POC"):
        allr = [r for r in mag if r["lens"] == lens]
        hs = [r for r in allr if r["era"] == "hold"]
        beta, V = regress([r["fwd"] for r in hs], [[1.0, r["D"]] for r in hs],
                          [r["date"] for r in hs])
        bd = [r for r in allr if r["era"] == "disc"]
        beta_d, V_d = regress([r["fwd"] for r in bd], [[1.0, r["D"]] for r in bd],
                              [r["date"] for r in bd])
        print(f"    {lens}: slope of fwd return on D (all slots)   disc {beta_d[1]:+.4f} "
              f"t {tstat(beta_d, V_d, 1):+.2f}   hold {beta[1]:+.4f} t {tstat(beta, V, 1):+.2f}")
        tr = [r for r in allr if r["trade"]]
        dg = cl_mean([r for r in tr if r["era"] == "disc"], "gross")
        hg = cl_mean([r for r in tr if r["era"] == "hold"], "gross")
        hn = cl_mean([r for r in tr if r["era"] == "hold"], "net")
        eras = [cl_mean([r for r in tr if r["era"] == "hold" and lo <= r["date"].year <= hi], "net")
                for lo, hi in ERAS]
        ex = cl_mean([r for r in tr if r["era"] == "hold" and r["date"].year not in EXCL], "net")
        v = verdict(hn, eras, ex)
        res[lens] = v
        print(f"      rule  disc gross {dg[0]:+.2f} (t {dg[1]:+.2f}, n {dg[2]})   hold gross "
              f"{hg[0]:+.2f} (t {hg[1]:+.2f})   HOLD NET {hn[0]:+.2f} t {hn[1]:+.2f} n {hn[2]}")
        print("      net by era  " + "   ".join(f"{lo}-{hi} {e[0]:+.2f} (t {e[1]:+.2f})"
                                                for (lo, hi), e in zip(ERAS, eras))
              + f"   ex-2020/21 {ex[0]:+.2f} (t {ex[1]:+.2f})   -> {v}")
        for ins in INSTR:
            x = cl_mean([r for r in tr if r["era"] == "hold" and r["ins"] == ins], "net")
            print(f"        {ins:<10} hold net {x[0]:+.2f} t {x[1]:+.2f} n {x[2]}")

    print("\n  B. RULE OF 16  (first 5m close beyond prior close +/- VIX/16 %; 60 min)")
    for r in r16:
        r["cont"] = gross_bp(r["b_in"], r["b_out"], r["dir"])
    dc = cl_mean([r for r in r16 if r["era"] == "disc"], "cont")
    s = 1 if dc[0] > 0 else -1
    print(f"    discovery 2005-2012: continuation {dc[0]:+.2f} bp t {dc[1]:+.2f} n {dc[2]}"
          f"  -> holdout trades {'WITH the break' if s > 0 else 'AGAINST the break (fade)'}")
    for r in r16:
        side = r["dir"] * s
        r["gross"] = gross_bp(r["b_in"], r["b_out"], side)
        r["net"] = net_bp(r["b_in"], r["b_out"], side)
    hs = [r for r in r16 if r["era"] == "hold"]
    hg, hn = cl_mean(hs, "gross"), cl_mean(hs, "net")
    eras = [cl_mean([r for r in hs if lo <= r["date"].year <= hi], "net") for lo, hi in ERAS]
    ex = cl_mean([r for r in hs if r["date"].year not in EXCL], "net")
    v = verdict(hn, eras, ex)
    res["R16"] = v
    print(f"    hold gross {hg[0]:+.2f} (t {hg[1]:+.2f})   HOLD NET {hn[0]:+.2f} t {hn[1]:+.2f} n {hn[2]}")
    print("    net by era  " + "   ".join(f"{lo}-{hi} {e[0]:+.2f} (t {e[1]:+.2f})"
                                          for (lo, hi), e in zip(ERAS, eras))
          + f"   ex-2020/21 {ex[0]:+.2f} (t {ex[1]:+.2f})   -> {v}")
    print(f"    reported: holdout continuation (unsigned by discovery) "
          f"{cl_mean(hs, 'cont')[0]:+.2f} t {cl_mean(hs, 'cont')[1]:+.2f}")
    for ins in INSTR:
        x = cl_mean([r for r in hs if r["ins"] == ins], "net")
        print(f"      {ins:<10} hold net {x[0]:+.2f} t {x[1]:+.2f} n {x[2]}")
    print("\n  VERDICTS  " + "   ".join(f"{k}: {v}" for k, v in res.items()))


if __name__ == "__main__":
    main()
