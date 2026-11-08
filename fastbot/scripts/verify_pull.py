#!/usr/bin/env python3
"""Verify a pull_m1 dataset. STDLIB ONLY.

WHY THIS FILE EXISTS
--------------------
pull_m1.py --verify imports numpy and pandas, which this project's
python3 does not have. It has never run. A verifier that cannot be run
is worse than none, because the pull reports success and the check that
would have caught a bad pull is the one step everyone skips.

WHAT IT CHECKS, AND WHY EACH ONE HAS BITTEN THIS PROJECT
--------------------------------------------------------
  grid          every timestamp on the stated interval, strictly
                increasing, no duplicates
  pairing       bid and ask carry the SAME timestamps -- a mid built
                from two different grids is a fiction
  bid <= ask    an inverted quote is a parse error, not a market
  OHLC          low <= open, close <= high on every row
  bid == ask    reported BY YEAR, not as one number. SPX500_USD is
                bid == ask for every bar before 2012 -- back-filled
                index data, not dealt quotes -- and a single overall
                percentage hides exactly which years are unusable
  gaps          the largest holes, so a silent truncation shows up
  provenance    the .meta.json written beside each file, if present

It prints a verdict per file and exits non-zero if any file fails, so it
can gate a pipeline rather than just inform one.

    python3 verify_pull.py --self-test
    python3 verify_pull.py --data-dir ../data/v24
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import glob
import json
import os
import sys

VERSION = "1.0"

TF_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600}
#: A weekend hole is the market being shut. Anything longer than this
#: inside a trading week is worth printing.
GAP_REPORT = 5
#: Above this, the instrument's spread axis does not exist for that year
#: and cost cannot be measured on it. PREREGISTRATION_v24 section 7.
FLAT_YEAR_WARN = 0.5


def read_rows(path):
    with open(path) as fh:
        for r in csv.DictReader(fh):
            yield r


def check_one(path, step):
    """(ok, dict of findings). Streams -- these files are 500k rows."""
    n = 0
    prev = None
    bad_grid = bad_ohlc = dupes = backwards = 0
    first = last = None
    times = []
    for r in read_rows(path):
        try:
            t = dt.datetime.fromisoformat(r["time"])
            o, h, l, c = (float(r["open"]), float(r["high"]),
                          float(r["low"]), float(r["close"]))
        except (ValueError, KeyError):
            bad_grid += 1
            continue
        n += 1
        if first is None:
            first = t
        last = t
        times.append(t)
        if int(t.timestamp()) % step:
            bad_grid += 1
        if prev is not None:
            if t == prev:
                dupes += 1
            elif t < prev:
                backwards += 1
        prev = t
        #: PLANTED IN THE SELF-TEST: a bar whose low exceeds its open is
        #: not a market, it is a parse error wearing OHLC's clothes.
        if not (l <= o <= h and l <= c <= h):
            bad_ohlc += 1
    gaps = []
    for i in range(1, len(times)):
        d = (times[i] - times[i - 1]).total_seconds()
        if d > step:
            gaps.append((d / 3600.0, times[i - 1], times[i]))
    gaps.sort(reverse=True)
    return dict(rows=n, first=first, last=last, bad_grid=bad_grid,
                bad_ohlc=bad_ohlc, dupes=dupes, backwards=backwards,
                gaps=gaps[:GAP_REPORT], times=times)


def cross_check(bid_path, ask_path):
    """Pairing, inversion and the flat-quote year profile, in one pass."""
    b = {}
    for r in read_rows(bid_path):
        b[r["time"]] = (float(r["open"]), float(r["close"]))
    inverted = 0
    flat = collections.Counter()
    total = collections.Counter()
    only_ask = 0
    for r in read_rows(ask_path):
        k = r["time"]
        if k not in b:
            only_ask += 1
            continue
        bo, bc = b.pop(k)
        ao, ac = float(r["open"]), float(r["close"])
        y = k[:4]
        total[y] += 1
        if ac < bc or ao < bo:
            inverted += 1
        if ac == bc:
            flat[y] += 1
    return dict(inverted=inverted, only_ask=only_ask, only_bid=len(b),
                flat=flat, total=total)


def meta_ok(path):
    """The provenance file beside a pull, if pull_m1 wrote one."""
    p = path + ".meta.json"
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return {}


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"verify_pull.py v{VERSION} self-test\n")
    import tempfile
    d = tempfile.mkdtemp()

    def write(name, rows):
        p = os.path.join(d, name)
        with open(p, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["time", "open", "high",
                                               "low", "close", "volume"])
            w.writeheader()
            w.writerows(rows)
        return p

    def bar(t, o=100.0, h=101.0, l=99.0, c=100.5, v=10):
        return dict(time=t, open=o, high=h, low=l, close=c, volume=v)

    good = [bar("2020-01-02 00:00:00"), bar("2020-01-02 00:15:00"),
            bar("2020-01-02 00:30:00")]
    r = check_one(write("good_bid_15m.csv", good), 900)
    print("a clean file passes every structural check")
    check("three rows, none off-grid, none out of order",
          r["rows"] == 3 and r["bad_grid"] == 0 and r["dupes"] == 0
          and r["backwards"] == 0)
    check("and no OHLC violation", r["bad_ohlc"] == 0)

    print("\nand each fault is caught SEPARATELY, not lumped together")
    #: PLANTED: 00:07 is not on a 15-minute grid. A pull that silently
    #: mixes granularities would pass a row count and fail here.
    off = check_one(write("off.csv", [bar("2020-01-02 00:00:00"),
                                      bar("2020-01-02 00:07:00")]), 900)
    check("an off-grid timestamp is caught", off["bad_grid"] == 1,
          f"{off['bad_grid']}")
    dup = check_one(write("dup.csv", [bar("2020-01-02 00:00:00"),
                                      bar("2020-01-02 00:00:00")]), 900)
    check("a duplicate timestamp is caught", dup["dupes"] == 1)
    back = check_one(write("back.csv", [bar("2020-01-02 00:15:00"),
                                        bar("2020-01-02 00:00:00")]), 900)
    check("a backwards timestamp is caught", back["backwards"] == 1)
    #: PLANTED: low above open. This is what a column-order mistake looks
    #: like, and it would otherwise flow into every price this project
    #: computes.
    bad = check_one(write("bad.csv", [bar("2020-01-02 00:00:00",
                                          o=100.0, h=101.0, l=100.5,
                                          c=100.5)]), 900)
    check("an impossible OHLC bar is caught", bad["bad_ohlc"] == 1)
    check("and a gap is measured in hours, largest first",
          check_one(write("gap.csv", [bar("2020-01-02 00:00:00"),
                                      bar("2020-01-02 04:00:00")]),
                    900)["gaps"][0][0] == 4.0)

    print("\nbid and ask are checked AGAINST EACH OTHER")
    b = write("x_bid_15m.csv", [bar("2020-01-02 00:00:00", c=100.0),
                                bar("2020-01-02 00:15:00", c=100.0)])
    a = write("x_ask_15m.csv", [bar("2020-01-02 00:00:00", c=100.2),
                                bar("2020-01-02 00:15:00", c=100.2)])
    x = cross_check(b, a)
    check("a normal pair has no inversions and no orphans",
          x["inverted"] == 0 and x["only_ask"] == 0 and x["only_bid"] == 0)
    #: PLANTED: ask below bid. Not a market -- a parse error.
    a2 = write("y_ask_15m.csv", [bar("2020-01-02 00:00:00", c=99.9),
                                 bar("2020-01-02 00:15:00", c=100.2)])
    check("an INVERTED quote is caught", cross_check(b, a2)["inverted"] == 1)
    #: PLANTED: the grids differ. A mid built from two different grids is
    #: a fiction, and row counts alone would not show it.
    a3 = write("z_ask_15m.csv", [bar("2020-01-02 00:00:00", c=100.2),
                                 bar("2020-01-02 00:30:00", c=100.2)])
    z = cross_check(b, a3)
    check("timestamps present on one side only are counted both ways",
          z["only_ask"] == 1 and z["only_bid"] == 1,
          f"ask-only {z['only_ask']}, bid-only {z['only_bid']}")

    print("\nflat quotes are reported BY YEAR, which is the whole point")
    #: PLANTED: the SPX500_USD failure. 2011 is entirely bid == ask and
    #: 2013 is not. One overall percentage would read 50% and tell you
    #: nothing about which half is usable.
    b4 = write("w_bid_15m.csv", [bar("2011-01-03 00:00:00", c=100.0),
                                 bar("2013-01-02 00:00:00", c=100.0)])
    a4 = write("w_ask_15m.csv", [bar("2011-01-03 00:00:00", c=100.0),
                                 bar("2013-01-02 00:00:00", c=100.2)])
    w = cross_check(b4, a4)
    check("2011 reads 100% flat", w["flat"]["2011"] == w["total"]["2011"] == 1)
    check("2013 reads 0% flat",
          w["flat"]["2013"] == 0 and w["total"]["2013"] == 1)
    check("so the unusable years are NAMED, not averaged away",
          set(w["total"]) == {"2011", "2013"})

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="../data/v24")
    ap.add_argument("--suffix", default="15m")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    step = TF_SECONDS.get(a.suffix)
    if step is None:
        raise SystemExit(f"  unknown suffix {a.suffix!r}; "
                         f"known: {', '.join(TF_SECONDS)}")

    print(f"verify_pull.py v{VERSION}   {a.data_dir}   interval {a.suffix}\n")
    stems = sorted({os.path.basename(p).rsplit("_", 2)[0]
                    for p in glob.glob(os.path.join(
                        a.data_dir, f"*_bid_{a.suffix}.csv"))})
    if not stems:
        raise SystemExit(f"  no *_bid_{a.suffix}.csv files in {a.data_dir}")

    failed = []
    for s in stems:
        pb = os.path.join(a.data_dir, f"{s}_bid_{a.suffix}.csv")
        pa = os.path.join(a.data_dir, f"{s}_ask_{a.suffix}.csv")
        if not os.path.exists(pa):
            print(f"  {s:<14} NO ASK FILE")
            failed.append(s)
            continue
        rb, ra = check_one(pb, step), check_one(pa, step)
        x = cross_check(pb, pa)
        faults = (rb["bad_grid"] + ra["bad_grid"] + rb["bad_ohlc"]
                  + ra["bad_ohlc"] + rb["dupes"] + ra["dupes"]
                  + rb["backwards"] + ra["backwards"] + x["inverted"]
                  + x["only_ask"] + x["only_bid"])
        verdict = "OK" if faults == 0 else f"{faults} FAULT(S)"
        if faults:
            failed.append(s)
        print(f"  {s:<14}{rb['rows']:>9,} rows   "
              f"{rb['first']:%Y-%m-%d} .. {rb['last']:%Y-%m-%d}   {verdict}")
        if faults:
            for lab, v in (("off-grid", rb["bad_grid"] + ra["bad_grid"]),
                           ("bad OHLC", rb["bad_ohlc"] + ra["bad_ohlc"]),
                           ("duplicate", rb["dupes"] + ra["dupes"]),
                           ("backwards", rb["backwards"] + ra["backwards"]),
                           ("ask < bid", x["inverted"]),
                           ("ask only", x["only_ask"]),
                           ("bid only", x["only_bid"])):
                if v:
                    print(f"  {'':<14}  {lab:<12}{v:>8,}")
        flat_years = [y for y in sorted(x["total"])
                      if x["flat"][y] / x["total"][y] > FLAT_YEAR_WARN]
        if flat_years:
            print(f"  {'':<14}  bid == ask over {FLAT_YEAR_WARN:.0%} in: "
                  f"{' '.join(flat_years)}")
            print(f"  {'':<14}  -> the spread axis does not exist in those "
                  f"years; cost is unmeasurable there (v24 s7)")
        if rb["gaps"]:
            big = rb["gaps"][0]
            print(f"  {'':<14}  largest gap {big[0]:.1f}h  "
                  f"{big[1]:%Y-%m-%d %H:%M} -> {big[2]:%Y-%m-%d %H:%M}")
        m = meta_ok(pb)
        if m:
            print(f"  {'':<14}  provenance: {m.get('tool', '?')} "
                  f"v{m.get('version', '?')}  "
                  f"{m.get('granularity', '?')}  {m.get('host', '?')}")
        elif m is not None:
            print(f"  {'':<14}  provenance file present but UNREADABLE")

    print(f"\n  {len(stems) - len(failed)} of {len(stems)} clean")
    if failed:
        print(f"  FAULTS IN: {', '.join(failed)}")
        sys.exit(2)


if __name__ == "__main__":
    main()
