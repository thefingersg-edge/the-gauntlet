#!/usr/bin/env python3
"""Integrity check for a fetched OHLC CSV. Run after every pull.

WHY THIS EXISTS

This tree has produced two data bugs of the same class, both found by asking
what the broker's clock does rather than by looking at results (standing rule
5): daily bars rolling at 21:00 UTC instead of 17:00 New York, and a
`resampled_h4/` grid sharing ZERO timestamps with OANDA's own H4 candles. A
third, in `dukascopy_intraday.py`, dated every bar one day late because
Dukascopy zero-indexes the month but not the day -- it moved a correlation from
0.043 to 0.976 once fixed.

None of those announced themselves. A fetch that exits 0 and writes a plausible
file is not evidence the file is right, so this checks the properties that were
actually wrong in those three cases, and fails loudly.

    python verify_feed.py spx500usd_oanda_m5.csv
    python verify_feed.py --expect-granularity M5 spx500usd_oanda_m5.csv
    python verify_feed.py *.csv            # whole-tree sweep

Exit code is non-zero if any FAIL fires, so it can gate a pull script.
"""
from __future__ import annotations

import argparse
import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np                                   # noqa: E402
import pandas as pd                                  # noqa: E402

from data import _normalise, _read_csv               # noqa: E402

#: Nominal bar length in minutes. Used to classify gaps, not to demand a
#: perfectly regular grid -- real feeds have weekends and holidays.
MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30,
           "H1": 60, "H4": 240, "D": 1440}


def infer_granularity(idx: pd.DatetimeIndex) -> str | None:
    """Modal spacing, as a granularity name. The modal gap is the bar size;
    the mean is not -- weekend gaps drag it upwards."""
    if len(idx) < 3:
        return None
    g = pd.Series(idx).diff().dt.total_seconds().div(60).dropna()
    if g.empty:
        return None
    modal = g.mode().iloc[0]
    for name, m in MINUTES.items():
        if abs(modal - m) < 1e-6:
            return name
    return None


def check(path: str, expect: str | None, quiet: bool) -> tuple[int, int]:
    fails, warns = 0, 0
    lines: list[str] = []

    def fail(msg: str) -> None:
        nonlocal fails
        fails += 1
        lines.append(f"  FAIL  {msg}")

    def warn(msg: str) -> None:
        nonlocal warns
        warns += 1
        lines.append(f"  warn  {msg}")

    try:
        d = _normalise(_read_csv(path))
    except Exception as exc:                          # noqa: BLE001
        print(f"\n{os.path.basename(path)}\n  FAIL  unreadable: {exc}")
        return 1, 0

    if d.empty:
        print(f"\n{os.path.basename(path)}\n  FAIL  no rows")
        return 1, 0

    idx = d.index
    gran = infer_granularity(idx)

    # -- structure -----------------------------------------------------------
    if not idx.is_monotonic_increasing:
        fail("index not monotonic -- rows out of order")
    n_dupe = int(idx.duplicated().sum())
    if n_dupe:
        fail(f"{n_dupe:,} duplicate timestamps")
    if idx.tz is None:
        warn("index is tz-naive; OANDA returns UTC and the comparison code "
             "assumes it. A naive index silently compares wrong against a "
             "tz-aware one.")

    # -- OHLC sanity ---------------------------------------------------------
    ohlc = ["open", "high", "low", "close"]
    missing = [c for c in ohlc if c not in d.columns]
    if missing:
        fail(f"missing columns: {missing}")
        print(f"\n{os.path.basename(path)}")
        print("\n".join(lines))
        return fails, warns

    n_nan = int(d[ohlc].isna().sum().sum())
    if n_nan:
        fail(f"{n_nan:,} NaN in OHLC")
    n_hl = int((d["high"] < d["low"]).sum())
    if n_hl:
        fail(f"{n_hl:,} bars with high < low")
    # open/close must sit inside the bar's range -- a classic sign of a
    # mis-joined or mis-resampled file.
    n_out = int(((d["open"] > d["high"]) | (d["open"] < d["low"])
                 | (d["close"] > d["high"]) | (d["close"] < d["low"])).sum())
    if n_out:
        fail(f"{n_out:,} bars with open/close outside [low, high]")
    if (d[ohlc] <= 0).any().any():
        fail("non-positive prices present")

    # -- granularity ---------------------------------------------------------
    if expect:
        if gran is None:
            fail(f"expected {expect} but modal spacing matches no known bar size")
        elif gran != expect:
            fail(f"expected {expect} but the modal spacing is {gran} -- "
                 f"wrong granularity, or a resampled grid masquerading as native")
    if gran and gran in MINUTES:
        step = MINUTES[gran]
        g = pd.Series(idx).diff().dt.total_seconds().div(60).dropna()
        n_short = int((g < step).sum())
        if n_short:
            fail(f"{n_short:,} gaps SHORTER than one {gran} bar -- "
                 f"overlapping or interleaved rows")
        # minute-of-hour should land on the grid for intraday bars
        if step < 60:
            offgrid = int((idx.minute % step != 0).sum())
            if offgrid:
                fail(f"{offgrid:,} timestamps off the {step}-minute grid")

    # -- the bug this tree actually hit: a one-day date shift ----------------
    # A correctly dated feed has (almost) no bars on Saturday, and few on
    # Sunday before the 22:00 UTC open. The Dukascopy day-index bug showed up
    # here first: shifting every bar by one day puts Friday's session on
    # Saturday.
    dow = idx.dayofweek
    sat = int((dow == 5).sum())
    if sat / len(idx) > 0.02:
        fail(f"{sat:,} bars ({100*sat/len(idx):.1f}%) fall on a Saturday -- "
             f"this is the signature of an off-by-one DATE index, the "
             f"dukascopy_intraday.py bug. Do not use this file.")
    elif sat:
        # Distinguish a handful of stray ticks from a real problem. On the
        # SPX500 M5 feed the six Saturday bars are all 2012, all volume 1, and
        # all flat (open == high == low == close) -- isolated bad ticks, not a
        # shift. Saying so here saves the next reader the investigation.
        s = d[dow == 5]
        n_flat = int(((s["open"] == s["high"]) & (s["high"] == s["low"])
                      & (s["low"] == s["close"])).sum())
        lo_vol = int((s["volume"] <= 1).sum()) if "volume" in s.columns else 0
        if n_flat == len(s) and lo_vol == len(s):
            warn(f"{sat:,} Saturday bars ({100*sat/len(idx):.3f}%), ALL flat "
                 f"(o=h=l=c) with volume <= 1 -- isolated stray ticks, not a "
                 f"date shift. Benign; years {sorted(set(s.index.year))}")
        else:
            warn(f"{sat:,} Saturday bars ({100*sat/len(idx):.2f}%), of which "
                 f"{n_flat} flat and {lo_vol} at volume <= 1 -- too few for a "
                 f"date shift, but not all strays either. Worth a look.")

    # -- coverage ------------------------------------------------------------
    years = (idx[-1] - idx[0]).days / 365.25
    per_year = d.groupby(idx.year).size()
    if len(per_year) > 2:
        # ignore first and last (partial) years when judging consistency
        mid = per_year.iloc[1:-1]
        if len(mid) > 1 and mid.min() < 0.5 * mid.median():
            thin = mid[mid < 0.5 * mid.median()]
            warn(f"thin years vs median {int(mid.median()):,}: "
                 + ", ".join(f"{y}={n:,}" for y, n in thin.items()))

    if "volume" in d.columns:
        n_zv = int((d["volume"] == 0).sum())
        if n_zv / len(d) > 0.05:
            warn(f"{n_zv:,} zero-volume bars ({100*n_zv/len(d):.1f}%)")

    status = "FAIL" if fails else ("warn" if warns else "ok")
    head = (f"\n{os.path.basename(path):<34}{status:>6}   "
            f"{len(d):>10,} bars  {gran or '?':>3}  "
            f"{idx[0].date()} -> {idx[-1].date()}  ({years:.1f}y)")
    if quiet and not fails and not warns:
        return 0, 0
    print(head)
    print("\n".join(lines))
    return fails, warns


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--expect-granularity", default=None,
                    help="require this bar size (M1/M5/M15/H1/H4/D). Without "
                         "it the granularity is inferred and only checked for "
                         "internal consistency.")
    ap.add_argument("--quiet", action="store_true",
                    help="print only files with findings")
    a = ap.parse_args()

    tf, tw = 0, 0
    for p in a.files:
        f, w = check(p, a.expect_granularity, a.quiet)
        tf += f
        tw += w

    print(f"\n{len(a.files)} file(s): {tf} FAIL, {tw} warn")
    if tf:
        print("A FAIL means the file should not be used until it is understood.")
    sys.exit(1 if tf else 0)


if __name__ == "__main__":
    main()
