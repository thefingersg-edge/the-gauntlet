#!/usr/bin/env python3
"""Remove stale/low-activity bars from OANDA candle files.

OANDA returns candles for hours when the market is effectively shut. They are
not flagged, and they are not zero-volume -- they carry volume 1, which is why
the zero-volume filter used for Dukascopy does not catch them.

Measured on XAU_USD, 124,147 hourly candles:

    day    bars     median volume   share with volume < 10
    Mon   24,449          1,529            0.4%
    Fri   22,298          1,854            1.0%
    Sat      470              1          100.0%
    Sun    2,608            512           31.9%

The distribution is starkly bimodal -- roughly 1 for stale bars against 1,500+
for traded ones -- so a threshold of 10 sits in an empty gap rather than on a
slope. The Sunday session open is visible in the same data: median volume goes
from 1 at 21:00 UTC to 1,126 at 22:00.

Why it matters: a stale bar usually has high == low, so its true range is zero.
That drags ATR down, shrinks rolling standard deviations, and can manufacture a
band crossover out of nothing. At 1.4% of bars it is small but not harmless,
and it lands disproportionately at week boundaries where gaps already occur.

    python clean_feeds.py --report              # show what would be removed
    python clean_feeds.py --apply               # rewrite the files
    python clean_feeds.py --self-test
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import _normalise, _read_csv              # noqa: E402

#: Volume below this FRACTION of the instrument's own median counts as dead.
#: Relative, not absolute -- a first version used a flat "volume < 10" and would
#: have deleted 12.7% of copper, whose overnight hours are genuinely thin
#: (weekday medians run from 47 at 21:00 to 3,122 at 13:00) rather than stale.
#: Applying a gold-calibrated constant to a different instrument is the same
#: scale-dependence bug found three times in the strategy itself.
DEAD_VOLUME_FRACTION = 0.01


def stale_mask(df: pd.DataFrame,
               fraction: float = DEAD_VOLUME_FRACTION) -> pd.Series:
    """Bars where the market was effectively shut.

    BOTH conditions are required:

    * **zero true range** (high == low) -- the bar carries no price
      information, so it cannot be a real quote update; and
    * **volume below `fraction` of this instrument's own median** -- scaled per
      instrument so a thin market is not mistaken for a dead one.

    A quiet-but-real bar keeps its low ATR contribution, which is correct: the
    market genuinely was quiet. Only bars that moved not at all, on essentially
    no activity, are removed.
    """
    flat = df["high"] <= df["low"] + 1e-12
    med = _local_median(df["volume"])
    dead = df["volume"] <= (med * fraction).clip(lower=0.0)
    return flat & dead


def _local_median(vol: pd.Series, window: str = "30D") -> pd.Series:
    """Rolling median volume, not a single number for the whole file.

    A GLOBAL median silently fails on long, fine-grained series. Gold M1 runs
    from a median of 4 ticks/minute in 2006 to 519 in 2026 -- a 130x change.
    One global median (~40) puts the 1% threshold at 0.4, below the minimum
    possible volume of 1, so the rule never fires and the file reports zero
    stale bars while 31% of its 2006 bars have high == low.

    This is the same scale-dependence that produced the copper divisor error
    and the original `volume < 10` cut: a constant calibrated at one scale,
    applied at another. A rolling window tracks the regime instead.
    """
    if not isinstance(vol.index, pd.DatetimeIndex) or len(vol) < 100:
        return pd.Series(vol.median(), index=vol.index)
    med = vol.rolling(window, min_periods=50).median()
    return med.fillna(vol.median())


def assess(df: pd.DataFrame, fraction: float = DEAD_VOLUME_FRACTION) -> dict:
    stale = stale_mask(df, fraction)
    weekend = df.index.dayofweek >= 5
    return {
        "bars": len(df),
        "stale": int(stale.sum()),
        "stale_pct": 100.0 * stale.mean(),
        "stale_and_flat": int(stale.sum()),          # flat is required
        "stale_on_weekend": int((stale & weekend).sum()),
        "weekend_total": int(weekend.sum()),
        "kept": int((~stale).sum()),
        "threshold": float(_local_median(df["volume"]).median() * fraction),
        "median_volume_kept": float(df.loc[~stale, "volume"].median()) if (~stale).any() else np.nan,
    }


def clean(df: pd.DataFrame,
          fraction: float = DEAD_VOLUME_FRACTION) -> pd.DataFrame:
    """Drop dead bars. Nothing is interpolated -- gaps stay gaps."""
    return df.loc[~stale_mask(df, fraction)].copy()


def self_test() -> int:
    fails = []

    def check(n, c, d=""):
        print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"  {d}" if not c else ""))
        if not c:
            fails.append(n)

    idx = pd.date_range("2024-01-01", periods=200, freq="1h", tz="UTC")
    df = pd.DataFrame({"open": 2000.0, "high": 2002.0, "low": 1998.0,
                       "close": 2001.0, "volume": 1500.0}, index=idx)
    # 20 stale bars: flat, volume 1
    stale_i = list(range(50, 70))
    df.iloc[stale_i, df.columns.get_loc("volume")] = 1.0
    for c in ("open", "high", "low", "close"):
        df.iloc[stale_i, df.columns.get_loc(c)] = 2000.0

    a = assess(df)
    check("stale bars detected", a["stale"] == 20, f"{a['stale']}")
    check("recognised as flat", a["stale_and_flat"] == 20)
    out = clean(df)
    check("stale bars removed", len(out) == 180, f"{len(out)}")
    check("no dead bar survives", int(stale_mask(out).sum()) == 0)
    check("index stays sorted", bool(out.index.is_monotonic_increasing))
    check("real bars untouched", bool((out["close"] == 2001.0).all()))

    import pine_ta as ta
    atr_before = ta.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
    atr_after = ta.atr(out["high"], out["low"], out["close"], 14).iloc[-1]
    check("stale bars had depressed ATR", atr_before <= atr_after + 1e-9,
          f"{atr_before:.4f} vs {atr_after:.4f}")

    check("clean() is idempotent", len(clean(clean(df))) == len(clean(df)))

    print("\n" + "=" * 56)
    if fails:
        print(f"{len(fails)} FAILED: {', '.join(fails)}")
        return 1
    print("all checks passed")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pattern", default="*_oanda_h1.csv")
    ap.add_argument("--fraction", type=float, default=DEAD_VOLUME_FRACTION,
                    help="dead = flat AND volume <= this fraction of the instrument median")
    ap.add_argument("--apply", action="store_true", help="rewrite the files")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())
    if not (args.apply or args.report):
        raise SystemExit("pass --report or --apply (or --self-test)")

    files = sorted(glob.glob(args.pattern))
    if not files:
        raise SystemExit(f"no files matching {args.pattern!r}")

    print(f"dead bar = zero range AND volume <= {100*args.fraction:g}% of that "
      f"instrument's median volume\n")
    print(f"{'file':<26}{'bars':>10}{'stale':>8}{'%':>7}{'flat':>7}"
          f"{'weekend':>9}{'kept':>10}")
    print("-" * 80)
    for f in files:
        df = _normalise(_read_csv(f))
        a = assess(df, args.fraction)
        print(f"{f:<26}{a['bars']:>10,}{a['stale']:>8,}{a['stale_pct']:>6.2f}%"
              f"{a['stale_and_flat']:>7,}{a['stale_on_weekend']:>9,}{a['kept']:>10,}")
        if args.apply:
            out = clean(df, args.fraction)
            out.to_csv(f)
    if args.apply:
        print("\nfiles rewritten. Gaps are left as gaps -- nothing interpolated.")
    else:
        print("\n--report only; re-run with --apply to rewrite.")


if __name__ == "__main__":
    main()
