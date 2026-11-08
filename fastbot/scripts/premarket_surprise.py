#!/usr/bin/env python3
"""PREREGISTRATION_v32 Part A -- on weekly claims, a sample never looked
at for this: is the bounce bigger when the print surprised more?

    python3 premarket_surprise.py --self-test
    python3 premarket_surprise.py
"""
from __future__ import annotations

import argparse, csv, datetime as dt, hashlib, os, re, statistics as st, sys
import numpy as np

from premarket_event import load_events
from premarket_factor import morning, trailing_sigma, regress, tstat
from premarket_participation import read_marks_vol, stem

VERSION = "1.0"
DOC = ("PREREGISTRATION_v32.md",
       "6d3137fb0134868927e893398687f70a3fd4ad1eeb5fc592bc962a813a56b770")
INSTRUMENTS = ("SPX500_USD", "NAS100_USD", "US30_USD", "DE30_EUR", "EUR_USD", "XAU_USD")
FORWARD_START = dt.date(2026, 9, 18)
PANDEMIC = (dt.date(2020, 3, 1), dt.date(2021, 12, 31))
CAP, T_GATE = 3.0, 2.0
_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)


def claims_surprise(before, onday):
    """print - mean(last four published the day before); None if no new print."""
    if len(before) < 4 or not onday or onday[-1][0] <= before[-1][0]:
        return None
    return onday[-1][1] - st.mean(v for _, v in before[-4:])


def in_pandemic(d):
    return PANDEMIC[0] <= d <= PANDEMIC[1]


def _guard(names):
    bad = [n for n in names if _FORBIDDEN.search(n)]
    if bad:
        raise SystemExit(f"namespace guard: {bad}")


_guard(list(globals()))


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"premarket_surprise.py v{VERSION} self-test\n")
    b = [("2020-01-04", 200.0), ("2020-01-11", 210.0), ("2020-01-18", 220.0),
         ("2020-01-25", 230.0)]
    check("surprise = print minus the mean of the four before",
          claims_surprise(b, [("2020-02-01", 245.0)]) == 245.0 - 215.0)
    #: PLANTED: a vintage date with no new week is not a release.
    check("no new week on the day -> no surprise",
          claims_surprise(b, [("2020-01-25", 230.0)]) is None)
    check("the pandemic window is the frozen one",
          in_pandemic(dt.date(2020, 3, 1)) and in_pandemic(dt.date(2021, 12, 31))
          and not in_pandemic(dt.date(2022, 1, 1)))
    check("cap 3, gate 2.0 one-sided", CAP == 3.0 and T_GATE == 2.0)
    check("no order, execute, submit or position name in this file",
          not [n for n in globals() if _FORBIDDEN.search(n)])
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="../data/v24")
    ap.add_argument("--events", default="../data/events_v2.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    print(f"premarket_surprise.py v{VERSION}   PREREGISTRATION_v32 Part A\n")
    print("  I am not a financial adviser. This is a measurement, not a")
    print("  recommendation to take a position.\n")
    here = os.path.dirname(os.path.abspath(__file__))
    got = hashlib.sha256(open(os.path.join(here, "..", DOC[0]), "rb").read()).hexdigest()
    if got != DOC[1]:
        print("  registration changed since frozen. Refused."); sys.exit(2)
    print(f"  {DOC[0]} sha256 {got[:16]}... matches\n")

    pre, _ = load_events(a.events, from_year=1900)
    s1 = {d for d, e in pre.items() if {"CPI", "NFP"} & e}
    s2 = {d for d, e in pre.items() if "CLAIMS" in e} - s1

    recs = []
    for ins in INSTRUMENTS:
        b, _v = read_marks_vol(os.path.join(a.data_dir, f"{stem(ins)}_bid_15m.csv"))
        ask, _ = read_marks_vol(os.path.join(a.data_dir, f"{stem(ins)}_ask_15m.csv"))
        rows = {"S1": [], "S2": [], "S3": []}
        for d in sorted({x for (x, hm) in b if hm == "08:30"}):
            if d >= FORWARD_START:
                continue
            m = morning(b, ask, d)
            if m is not None:
                rows["S1" if d in s1 else "S2" if d in s2 else "S3"].append((d,) + m)
        rr = rows["S2"]
        for (d, mv, y0, y1), s in zip(rr, trailing_sigma([r[1] for r in rr])):
            if s and s > 0:
                recs.append(dict(ins=ins, date=d, y0=y0, sigma=s))
    v27 = {(r["instrument"], r["date"]): float(r["gross_H0"])
           for r in csv.DictReader(open(os.path.join(here, "../data/horizon_v27_trades.csv"))) if r["gross_H0"]}
    diffs = [abs(r["y0"] - v27[(r["ins"], r["date"].isoformat())]) for r in recs
             if (r["ins"], r["date"].isoformat()) in v27]
    g0 = len(diffs) > 1000 and max(diffs) < 1e-6
    print(f"  GATE 0  {len(diffs):,} claims-morning trades matched v27, max |diff| "
          f"{max(diffs):.1e}   [{'PASS' if g0 else 'FAIL'}]")
    if not g0:
        sys.exit(3)

    vint = {}
    for r in csv.DictReader(open("../data/v31/vintages.csv")):
        if r["series"] == "ICSA" and r["status"] == "ok":
            vint.setdefault((r["event_date"], r["vintage_date"]), []).append(
                (r["obs_date"], float(r["value"])))
    sur = {}
    for d in s2:
        s = claims_surprise(sorted(vint.get((d.isoformat(), (d - dt.timedelta(days=1)).isoformat()), [])),
                            sorted(vint.get((d.isoformat(), d.isoformat()), [])))
        if s is not None:
            sur[d] = s
    print(f"  claims releases with a surprise: {len(sur)}   "
          f"({sum(1 for d in sur if in_pandemic(d))} in the pandemic window)\n")

    def run(label, keep, cap):
        vals = {d: v for d, v in sur.items() if keep(d)}
        sd = st.stdev(vals.values())
        z = {d: min(abs(v) / sd, cap) if cap else abs(v) / sd for d, v in vals.items()}
        rows = [r for r in recs if r["date"] in z]
        y = [r["y0"] / r["sigma"] for r in rows]
        X = np.column_stack([np.ones(len(rows)), [z[r["date"]] for r in rows]])
        bb, V = regress(y, X, [r["date"] for r in rows])
        t = tstat(bb, V, 1)
        ds = sorted(z); cut = ds[len(ds) // 2]
        halves = []
        for part in ([r for r in rows if r["date"] < cut], [r for r in rows if r["date"] >= cut]):
            yy = [r["y0"] / r["sigma"] for r in part]
            XX = np.column_stack([np.ones(len(part)), [z[r["date"]] for r in part]])
            b2, V2 = regress(yy, XX, [r["date"] for r in part])
            halves.append((b2[1], tstat(b2, V2, 1)))
        med = st.median(z.values())
        big = [r["y0"] for r in rows if z[r["date"]] > med]
        small = [r["y0"] for r in rows if z[r["date"]] <= med]
        print(f"  {label}")
        print(f"    n {len(rows)} trades on {len(z)} releases   b {bb[1]:+.3f}  t {t:+.2f}"
              f"   halves {halves[0][0]:+.3f} (t {halves[0][1]:+.2f}) / "
              f"{halves[1][0]:+.3f} (t {halves[1][1]:+.2f})")
        print(f"    fade, bigger-surprise half {st.mean(big):+.2f} bp   smaller half "
              f"{st.mean(small):+.2f} bp")
        return bb[1], t

    b, t = run("PRIMARY -- pandemic excluded, |z| capped at 3", lambda d: not in_pandemic(d), CAP)
    print()
    run("REPORTED -- all dates, uncapped", lambda d: True, None)
    ok = b > 0 and t >= T_GATE
    print(f"\n  GATE -- frozen in PREREGISTRATION_v32 section 2")
    print(f"    [{'PASS' if ok else 'FAIL'}] GA  b {b:+.3f}  t {t:+.2f}  (one-sided, t >= {T_GATE})")


if __name__ == "__main__":
    main()
