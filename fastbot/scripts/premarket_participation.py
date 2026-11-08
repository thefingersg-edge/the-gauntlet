#!/usr/bin/env python3
"""PREREGISTRATION_v29 Part 1 -- does participation in the release bar
move the bounce?

P = the 08:30 bar's tick count against the median of the instrument's
prior 24 same-class events. fade/sigma = a + b ln(P), six instruments
pooled, errors clustered by date. Two-sided, because stale-quote and
crowded-flow stories disagree on the sign.

    python3 premarket_participation.py --self-test
    python3 premarket_participation.py --data-dir ../data/v24
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

import numpy as np

from premarket_event import load_events
from premarket_factor import morning, trailing_sigma, regress, tstat

VERSION = "1.0"
DOC = ("PREREGISTRATION_v29.md",
       "8feb1816d22b098f2773ab1e8d9b7d15fe2224b8f4e7f382d77fe9490635c5e3")
ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
INSTRUMENTS = ("SPX500_USD", "NAS100_USD", "US30_USD",
               "DE30_EUR", "EUR_USD", "XAU_USD")
SIG, ENTRY, H0, CLOSE = "08:30", "08:45", "09:45", "15:45"
WANT_ET = (SIG, ENTRY, H0, CLOSE)
KEEP_UTC = {"12:30", "13:30", "12:45", "13:45", "14:45", "19:45", "20:45"}
FORWARD_START = dt.date(2026, 9, 18)
WINDOW = 24
T_GATE = 2.4
V27_FILE = "../data/horizon_v27_trades.csv"

_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)


def _guard(names):
    bad = sorted(n for n in names if _FORBIDDEN.search(n))
    if bad:
        raise SystemExit(f"namespace guard: this file must not define {bad}")


def stem(i):
    return i.replace("_", "").lower()


def read_marks_vol(path):
    """({(date, hm): (o,h,l,c)}, {date: tick count of the 08:30 bar})."""
    out, vol = {}, {}
    with open(path, newline="") as fh:
        rd = csv.reader(fh)
        head = next(rd)
        ix = [head.index(k) for k in ("time", "open", "high", "low", "close")]
        iv = head.index("volume")
        for row in rd:
            s = row[ix[0]]
            if s[11:16] not in KEEP_UTC:
                continue
            e = dt.datetime.fromisoformat(s).replace(tzinfo=UTC).astimezone(ET)
            hm = e.strftime("%H:%M")
            if hm in WANT_ET:
                out[(e.date(), hm)] = tuple(float(row[i]) for i in ix[1:])
                if hm == SIG:
                    vol[e.date()] = float(row[iv])
    return out, vol


def trailing_median(xs):
    """For each event, the median of the PRIOR WINDOW values, else None."""
    return [st.median(xs[i - WINDOW:i]) if i >= WINDOW else None
            for i in range(len(xs))]


def g1_pass(b, t):
    return t is not None and abs(t) >= T_GATE


def g2_pass(b1, b2, t2):
    """Replication: same sign as G1's slope, t >= 2.4 in that direction."""
    return t2 is not None and b1 * b2 > 0 and abs(t2) >= T_GATE


_guard(list(globals()))


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int, np.bool_)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"premarket_participation.py v{VERSION} self-test\n")
    xs = [10.0] * WINDOW + [1000.0, 10.0]
    tm = trailing_median(xs)
    check("no baseline for the first 24 events", tm[WINDOW - 1] is None
          and tm[WINDOW] == 10.0)
    #: PLANTED: a spike must be measured against the past, not itself.
    check("a spike is measured against the PAST, not against itself",
          xs[WINDOW] / tm[WINDOW] == 100.0, "P = 100")
    check("and the median shrugs the spike off afterwards",
          tm[WINDOW + 1] == 10.0)

    rng = np.random.default_rng(9)
    n = 3000
    lp = rng.normal(0, 0.6, n)
    cl = [i % 500 for i in range(n)]
    y = -0.3 * lp + rng.normal(0, 1, n)
    b, V = regress(y, np.column_stack([np.ones(n), lp]), cl)
    t = tstat(b, V, 1)
    check("a planted negative slope is recovered, sign and size",
          -0.4 < b[1] < -0.2 and t < -T_GATE, f"b {b[1]:+.3f} t {t:+.2f}")
    y0 = rng.normal(0, 1, n)
    b0, V0 = regress(y0, np.column_stack([np.ones(n), lp]), cl)
    check("pure noise does not pass G1",
          not g1_pass(b0[1], tstat(b0, V0, 1)), f"t {tstat(b0, V0, 1):+.2f}")
    check("G1 is two-sided", g1_pass(-0.3, -2.5) and g1_pass(0.3, 2.5)
          and not g1_pass(0.3, 2.3))
    check("G2 needs the SAME sign as G1",
          g2_pass(-0.3, -0.2, -2.6) and not g2_pass(-0.3, 0.2, 2.6))
    check("gate at 2.4, window 24, forward sample out",
          T_GATE == 2.4 and WINDOW == 24
          and FORWARD_START == dt.date(2026, 9, 18))
    check("no order, execute, submit or position name in this file",
          not [n_ for n_ in globals() if _FORBIDDEN.search(n_)])
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="../data/v24")
    ap.add_argument("--events", default="../data/events_v2.csv")
    ap.add_argument("--out", default="../data/participation_v29_trades.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"premarket_participation.py v{VERSION}   PREREGISTRATION_v29 Part 1\n")
    print("  I am not a financial adviser. This is a measurement, not a")
    print("  recommendation to take a position.\n")
    here = os.path.dirname(os.path.abspath(__file__))
    got = hashlib.sha256(open(os.path.join(here, "..", DOC[0]), "rb").read()
                         ).hexdigest()
    if got != DOC[1]:
        print(f"  {DOC[0]} changed since it was frozen. Refused.")
        sys.exit(2)
    print(f"  {DOC[0]} sha256 {got[:16]}... matches the frozen copy\n")

    pre, _ = load_events(a.events, from_year=1900)
    s1 = {d for d, e in pre.items() if {"CPI", "NFP"} & e}
    s2 = {d for d, e in pre.items() if "CLAIMS" in e} - s1

    recs = {"S1": [], "S2": [], "S3": []}
    for ins in INSTRUMENTS:
        b, vb = read_marks_vol(os.path.join(a.data_dir, f"{stem(ins)}_bid_15m.csv"))
        ask, _ = read_marks_vol(os.path.join(a.data_dir, f"{stem(ins)}_ask_15m.csv"))
        rows = {"S1": [], "S2": [], "S3": []}
        for d in sorted(vb):
            if d >= FORWARD_START:
                continue
            m = morning(b, ask, d)
            if m is None:
                continue
            rows["S1" if d in s1 else "S2" if d in s2 else "S3"].append(
                (d, m[0], m[1], vb[d]))
        for cls, rr in rows.items():
            sig = trailing_sigma([r[1] for r in rr])
            med = trailing_median([r[3] for r in rr])
            n = 0
            for (d, mv, y0, v), s, md in zip(rr, sig, med):
                if s is None or s <= 0 or md is None or md <= 0 or v <= 0:
                    continue
                recs[cls].append(dict(ins=ins, date=d, y0=y0, sigma=s,
                                      P=v / md, vol=v))
                n += 1
        print(f"  {ins:<12} usable  S1 {sum(1 for r in recs['S1'] if r['ins']==ins):>4}"
              f"   S2 {sum(1 for r in recs['S2'] if r['ins']==ins):>4}"
              f"   S3 {sum(1 for r in recs['S3'] if r['ins']==ins):>5}")

    with open(a.out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sample", "instrument", "date", "fade_0945", "sigma_bp",
                    "ticks", "P"])
        for cls in recs:
            for r in recs[cls]:
                w.writerow([cls, r["ins"], r["date"].isoformat(),
                            f"{r['y0']:.6f}", f"{r['sigma']:.6f}",
                            f"{r['vol']:.0f}", f"{r['P']:.6f}"])

    v27 = {}
    for r in csv.DictReader(open(os.path.join(here, V27_FILE))):
        if r["gross_H0"]:
            v27[(r["instrument"], r["date"])] = float(r["gross_H0"])
    matched, worst = 0, 0.0
    for cls in recs:
        for r in recs[cls]:
            k = (r["ins"], r["date"].isoformat())
            if k in v27:
                matched += 1
                worst = max(worst, abs(r["y0"] - v27[k]))
    g0 = matched > 1000 and worst < 1e-6
    print(f"\n  GATE 0  {matched:,} trades matched v27, max |diff| {worst:.1e} bp"
          f"   [{'PASS' if g0 else 'FAIL'}]")
    if not g0:
        print("  VOID -- pipeline failure.")
        sys.exit(3)

    def fit(cls):
        rr = recs[cls]
        y = [r["y0"] / r["sigma"] for r in rr]
        X = np.column_stack([np.ones(len(rr)), [math.log(r["P"]) for r in rr]])
        b, V = regress(y, X, [r["date"] for r in rr])
        # raw bp with instrument fixed effects -- reported only
        ins = sorted({r["ins"] for r in rr})
        Xr = np.column_stack([[math.log(r["P"]) for r in rr]]
                             + [[1.0 if r["ins"] == i else 0.0 for r in rr]
                                for i in ins])
        br, Vr = regress([r["y0"] for r in rr], Xr, [r["date"] for r in rr])
        return dict(n=len(rr), b=b[1], t=tstat(b, V, 1), braw=br[0],
                    traw=tstat(br, Vr, 0))

    print(f"\n  fade/sigma = a + b ln(P)   (six instruments pooled)")
    print(f"    {'sample':<22}{'n':>7}{'b':>9}{'t':>8}"
          f"{'raw bp per ln P':>18}{'t':>8}")
    res = {}
    for cls, nm in (("S1", "S1 CPI+payrolls"), ("S2", "S2 claims"),
                    ("S3", "S3 control")):
        res[cls] = fit(cls)
        r = res[cls]
        print(f"    {nm:<22}{r['n']:>7}{r['b']:>+9.3f}{r['t']:>+8.2f}"
              f"{r['braw']:>+18.2f}{r['traw']:>+8.2f}")

    print(f"\n  thirds of P, mean fade in bp -- reported, gating nothing")
    for cls, nm in (("S1", "S1 CPI+payrolls"), ("S2", "S2 claims"),
                    ("S3", "S3 control")):
        rr = sorted(recs[cls], key=lambda r: r["P"])
        k = len(rr) // 3
        parts = [rr[:k], rr[k:2 * k], rr[2 * k:]]
        print(f"    {nm:<22}" + "".join(
            f"   P~{st.median(r['P'] for r in p):4.2f}: {st.mean(r['y0'] for r in p):+6.2f}"
            for p in parts))

    print(f"\n  GATES -- frozen in PREREGISTRATION_v29 section 3")
    g1 = g1_pass(res["S1"]["b"], res["S1"]["t"])
    print(f"    [{'PASS' if g1 else 'FAIL'}] G1 CPI+payrolls  b {res['S1']['b']:+.3f}"
          f"  t {res['S1']['t']:+.2f}  (two-sided, |t| >= {T_GATE})")
    if g1:
        g2 = g2_pass(res["S1"]["b"], res["S2"]["b"], res["S2"]["t"])
        print(f"    [{'PASS' if g2 else 'FAIL'}] G2 claims replication  b "
              f"{res['S2']['b']:+.3f}  t {res['S2']['t']:+.2f}")
    else:
        print(f"    [ -- ] G2 not evaluated: G1 failed (section 3)")
    print(f"    [ S3 ] control  b {res['S3']['b']:+.3f}  t {res['S3']['t']:+.2f}"
          f"  (interpretation only)")


if __name__ == "__main__":
    main()
