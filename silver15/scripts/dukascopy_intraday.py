#!/usr/bin/env python3
"""Intraday (15m / 5m / 1m) extension to dukascopy.py.

Your dukascopy.py fetches `hour_1` candles, published ONE FILE PER MONTH.
Intraday candles use a different endpoint: `min_1`, published ONE FILE PER DAY.

    hourly   /XAGUSD/2024/05/BID_candles_hour_1.bi5        <- month file
    minute   /XAGUSD/2024/05/14/BID_candles_min_1.bi5      <- day file
                              ^^ day

Everything else is identical -- same LZMA, same 24-byte big-endian records,
same open/close/low/high field order -- so this module imports your decoder,
cache, retry logic and reporting rather than duplicating them.

    python dukascopy_intraday.py --instrument XAGUSD --verify --year 2024 --month 6
    python dukascopy_intraday.py --instrument XAGUSD --start 2016 --tf 15m \
        --out ../data/xagusd_15m.csv

TWO THINGS TO KNOW BEFORE YOU START A LONG PULL
-----------------------------------------------
1. VOLUME. One month of hourly = 1 request. One month of minute = ~30. Ten
   years of minute data is ~3,650 requests, about 30-40 minutes at the default
   pause. The cache makes re-runs cheap, but the first pull is not quick.
   Consider --start 2016 rather than 2006: pre-2016 silver traded $14-20 with
   a completely different vol regime, and the strategy normalises by ATR
   anyway, so the marginal value of 2006-2015 at 15m resolution is low
   relative to the download cost.

2. THE DAY INDEX CONVENTION IS NOT OBVIOUS -- AND IT IS NOT THE SAME AS THE
   MONTH'S. This was settled empirically on XAGUSD 2024-06, not assumed:

       month  ZERO-indexed   June -> /05/     (as your dukascopy.py documents)
       day    ONE -indexed   6th  -> /06/     <- NOT /05/

   Evidence: with the old zero-indexed day URL, resampling minute data to
   hourly and diffing against the trusted `hour_1` month file gave a median
   |close diff| of 0.381 at zero shift, but EXACTLY 0.000000 across 458 bars
   when the minute index was shifted back one day. Anchor check: the file at
   day-dir 06 decodes to o30.002 h31.374 l29.959 c31.328, which is the hourly
   feed's 6 June -- the 7th was the NFP crash (h31.540 l29.104 c29.161).

   So one-indexed is now the DEFAULT. `--day-zero-indexed` is kept as an
   escape hatch in case another instrument or era differs, and --verify still
   tries both and tells you which reproduces the hourly bars.

   Note that a wrong day index does NOT show up as a timestamp mismatch:
   bars are stamped from the day you REQUESTED, not the day you received, so
   overlap stays high (79%) while every price is a day stale. That is why
   --verify compares prices and scans lags rather than trusting overlap.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dukascopy as dk          # your script, unmodified

VERSION = "0.4-diagnostics"

TF_RULE = {"1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h"}


# ---------------------------------------------------------------------------
# URL + time base for day-level files
# ---------------------------------------------------------------------------

def day_url(instrument: str, year: int, month: int, day: int,
            side: str = "BID", period: str = "min_1",
            day_zero_indexed: bool = True) -> str:
    """Build the feed URL for one DAY of intraday candles.

    ``month`` and ``day`` are passed 1-based as a human writes them. The month
    is always zero-indexed on the wire. The day convention is selectable
    because it is the one thing worth verifying rather than assuming.
    """
    if not 1 <= month <= 12:
        raise ValueError(f"month must be 1-12, got {month}")
    if not 1 <= day <= 31:
        raise ValueError(f"day must be 1-31, got {day}")
    d = day - 1 if day_zero_indexed else day
    return (f"{dk.BASE_URL}/{instrument}/{year:04d}/{month - 1:02d}/{d:02d}/"
            f"{side}_candles_{period}.bi5")


def day_base(year: int, month: int, day: int) -> pd.Timestamp:
    """Offsets in a min_1 file are seconds from the start of that day."""
    return pd.Timestamp(year=year, month=month, day=day, tz="UTC")


def day_cache_paths(cache_dir: str, instrument: str, side: str, period: str,
                    year: int, month: int, day: int,
                    day_zero_indexed: bool = True) -> tuple[str, str]:
    """Cache key MUST include the day-index convention.

    Without it the two --verify passes collide: the zero-indexed pass writes
    day_07.bi5, then the one-indexed pass -- which requests a DIFFERENT URL --
    finds day_07.bi5 already on disk and returns the first pass's bytes. Both
    conventions then report byte-identical statistics, which reads as "the
    test is broken" when in fact the test never ran twice. The `d0`/`d1`
    suffix keeps the two universes apart.
    """
    conv = "d0" if day_zero_indexed else "d1"
    stem = os.path.join(
        cache_dir,
        f"{instrument}_{side}_{period}_{year:04d}_{month:02d}_{day:02d}_{conv}")
    return stem + ".bi5", stem + ".empty"


def fetch_day(instrument: str, year: int, month: int, day: int, side: str,
              divisor: float, cache_dir: str | None, timeout: float,
              retries: int = 6, day_zero_indexed: bool = True,
              period: str = "min_1", verbose: bool = False) -> pd.DataFrame:
    """Fetch one day of intraday candles. Mirrors dk.fetch_month's cache logic:
    successes and 404s are cached, transient failures deliberately are not."""
    data_path = empty_path = None
    if cache_dir:
        data_path, empty_path = day_cache_paths(cache_dir, instrument, side,
                                                period, year, month, day,
                                                day_zero_indexed)
        if os.path.exists(data_path):
            with open(data_path, "rb") as fh:
                raw = fh.read()
            return dk.decode_candles(dk.decompress_bi5(raw),
                                     day_base(year, month, day), divisor)
        if os.path.exists(empty_path):
            return dk.decode_candles(b"", day_base(year, month, day), divisor)

    url = day_url(instrument, year, month, day, side, period, day_zero_indexed)
    raw = dk.http_get(url, timeout=timeout, retries=retries, verbose=verbose)

    if raw is None:                                  # 404: weekend / no history
        if empty_path:
            os.makedirs(cache_dir, exist_ok=True)
            open(empty_path, "wb").close()
        return dk.decode_candles(b"", day_base(year, month, day), divisor)

    if data_path:
        os.makedirs(cache_dir, exist_ok=True)
        with open(data_path, "wb") as fh:
            fh.write(raw)

    return dk.decode_candles(dk.decompress_bi5(raw),
                             day_base(year, month, day), divisor)


# ---------------------------------------------------------------------------
# resampling
# ---------------------------------------------------------------------------

def resample_ohlcv(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    """1m -> target timeframe. Left-closed, left-labelled, matching how
    TradingView and MT5 stamp bars: a 15m bar labelled 09:00 covers 09:00-09:14.

    Empty buckets are dropped rather than forward-filled. A synthesised bar in
    a market that was closed is padding by another name, and your script
    already goes to some trouble to strip exactly that.
    """
    rule = TF_RULE[tf]
    out = df.resample(rule, closed="left", label="left").agg(
        {"open": "first", "high": "max", "low": "min",
         "close": "last", "volume": "sum"})
    return out.dropna(subset=["open", "high", "low", "close"])


def day_range(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int, int]]:
    """All calendar days from (y,m) start through (y,m) end inclusive.
    Weekends are included and simply 404 -- cheaper than a calendar, and the
    .empty sentinel means they are only ever requested once."""
    first = pd.Timestamp(year=start[0], month=start[1], day=1, tz="UTC")
    last = pd.Timestamp(year=end[0], month=end[1], day=1, tz="UTC") + pd.offsets.MonthEnd(0)
    days = pd.date_range(first, last, freq="D", tz="UTC")
    return [(d.year, d.month, d.day) for d in days]


# ---------------------------------------------------------------------------
# verification: cross-check minute data against the trusted hourly feed
# ---------------------------------------------------------------------------

def verify(instrument: str, year: int, month: int, side: str, divisor: float,
           cache_dir: str | None, timeout: float, pause: float) -> bool:
    """Resample one month of min_1 to hourly and diff against the hour_1 file.

    This is the only honest way to settle the day-index question without
    guessing. Both conventions are tried; the correct one reproduces the
    hourly bars almost exactly. The wrong one will be shifted by a day and
    will not.
    """
    print(f"\ndukascopy_intraday.py v{VERSION}")
    print(f"Verifying {instrument} {year}-{month:02d} minute data against "
          f"the hourly feed")
    print("=" * 68)

    print("  fetching reference hour_1 month file ...")
    hourly = dk.fetch_month(instrument, year, month, side, divisor,
                            cache_dir, timeout)
    if hourly.empty:
        print("  reference hourly month is empty -- pick a different month")
        return False
    hourly, _ = dk.filter_flat_bars(hourly)
    print(f"    {len(hourly):,} traded hourly bars")

    ndays = pd.Timestamp(year=year, month=month, day=1).days_in_month
    results = {}

    for zero_indexed in (True, False):
        label = "day-1 (zero-indexed)" if zero_indexed else "day (one-indexed)"
        print(f"\n  trying {label}")
        frames = []
        for d in range(1, ndays + 1):
            try:
                part = fetch_day(instrument, year, month, d, side, divisor,
                                 cache_dir, timeout,
                                 day_zero_indexed=zero_indexed)
            except Exception as exc:                       # noqa: BLE001
                print(f"    day {d:02d} failed: {exc}")
                continue
            if not part.empty:
                frames.append(part)
            if pause:
                time.sleep(pause)

        if not frames:
            print("    no data returned at all")
            results[zero_indexed] = None
            continue

        minute = pd.concat(frames)
        minute = minute[~minute.index.duplicated(keep="first")].sort_index()
        minute, _ = dk.filter_flat_bars(minute)
        rehourly = resample_ohlcv(minute, "1h")

        common = rehourly.index.intersection(hourly.index)
        if len(common) == 0:
            print("    zero timestamp overlap with the hourly feed")
            results[zero_indexed] = None
            continue

        # compare closes; a one-day shift destroys this correlation
        a = rehourly.loc[common, "close"].to_numpy()
        b = hourly.loc[common, "close"].to_numpy()
        diff = a - b
        max_err = float(np.max(np.abs(diff)))
        med_err = float(np.median(np.abs(diff)))
        overlap = len(common) / len(hourly)

        print(f"    {len(minute):,} minute bars -> {len(rehourly):,} hourly")
        print(f"    overlap with reference : {overlap:.1%}")
        print(f"    median |close diff|    : {med_err:.6f}")
        print(f"    max    |close diff|    : {max_err:.6f}")

        # --- diagnostic 1: minutes per hour ------------------------------
        # Distinguishes a sparse feed from a misalignment. A sparse feed
        # cannot reproduce the hourly close no matter how you shift it.
        mph = minute.resample("1h").size()
        mph = mph[mph > 0]
        print(f"    minutes/hour           : median {mph.median():.0f}  "
              f"mean {mph.mean():.1f}  min {mph.min()}  "
              f"({(mph < 30).sum()}/{len(mph)} hours under half-full)")

        # --- diagnostic 2: signed bias -----------------------------------
        # A BID/ASK mixup is a near-constant one-signed offset of roughly one
        # spread. Misalignment is zero-mean and as wide as the price moves.
        print(f"    signed diff mean/std   : {diff.mean():+.6f} / {diff.std():.6f}")
        print(f"    close corr / ret corr  : "
              f"{np.corrcoef(a, b)[0, 1]:.4f} / "
              f"{np.corrcoef(np.diff(a), np.diff(b))[0, 1]:.4f}")

        # --- diagnostic 3: lag scan --------------------------------------
        # THE decisive test. Bars are stamped from the day requested, not the
        # day received, so a wrong day index hides as high overlap + wrong
        # prices. Shifting the index until the error collapses to zero names
        # the error exactly.
        print("    lag scan (shift minute index, then re-diff):")
        lag_best = None
        shifts = [pd.Timedelta(days=d) for d in (-2, -1, 0, 1, 2)]
        shifts += [pd.Timedelta(hours=h) for h in (-3, -2, -1, 1, 2, 3)]
        for s in sorted(set(shifts)):
            shifted = rehourly.copy()
            shifted.index = shifted.index + s
            c = shifted.index.intersection(hourly.index)
            if len(c) == 0:
                continue
            e = float(np.median(np.abs(shifted.loc[c, "close"].to_numpy()
                                       - hourly.loc[c, "close"].to_numpy())))
            flag = ""
            if e < 1e-6:
                flag = "  <-- EXACT MATCH"
            print(f"      {str(s):>20}  n={len(c):>4}  "
                  f"overlap {len(c)/len(hourly):>6.1%}  "
                  f"median |d| {e:.6f}{flag}")
            if lag_best is None or e < lag_best[1]:
                lag_best = (s, e)

        if lag_best and lag_best[1] < 1e-6 and lag_best[0] != pd.Timedelta(0):
            print(f"    >> data is offset by {lag_best[0]}. The prices are "
                  f"real and exact,\n    >> they are simply filed under the "
                  f"wrong timestamp. This is an INDEX\n    >> bug, not a feed "
                  f"quality problem -- do not 'fix' it with tolerances.")

        results[zero_indexed] = (overlap, med_err)

    print("\n" + "=" * 68)
    good = {k: v for k, v in results.items() if v and v[0] > 0.9 and v[1] < 1e-6}
    if len(good) == 1:
        zi = next(iter(good))
        print(f"  CONFIRMED: day is "
              f"{'ZERO-indexed' if zi else 'ONE-indexed'} on this feed.")
        if zi:
            print("  This is NOT the default. Pass --day-zero-indexed on every")
            print("  pull, and re-read the day-index note at the top of this file.")
        else:
            print("  This matches the default. Run the full pull with no extra flags.")
        return True
    if len(good) == 2:
        print("  Both conventions matched -- that should be impossible.")
        print("  Check that the cache is not serving stale files: rm -rf the cache dir.")
        return False
    print("  NEITHER convention reproduced the hourly bars.")
    print("  Do not start a long pull. Possible causes:")
    print("    * this instrument has no minute history for that month (try 2024-06)")
    print("    * the min_1 period name differs on this feed")
    print("    * offsets in min_1 files are not seconds-from-day-start")
    print("  Re-run --verify on a recent, liquid month before going further.")
    return False


# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--instrument", default="XAGUSD")
    ap.add_argument("--tf", default="15m", choices=list(TF_RULE))
    ap.add_argument("--start", default="2016", help="start year, or YYYY-MM")
    ap.add_argument("--end", default=None, help="end year, or YYYY-MM")
    ap.add_argument("--side", default="BID", choices=["BID", "ASK"])
    ap.add_argument("--out", default=None)
    ap.add_argument("--price-divisor", type=float, default=None)
    ap.add_argument("--cache-dir", default=".dukascopy_cache")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--pause", type=float, default=0.25)
    ap.add_argument("--timeout", type=float, default=45.0)
    ap.add_argument("--retries", type=int, default=6)
    ap.add_argument("--keep-flat", action="store_true")
    ap.add_argument("--day-zero-indexed", action="store_true",
                    help="use 0-based day in the URL. NOT the default: "
                         "verified one-indexed on XAGUSD 2024-06")
    ap.add_argument("--day-one-indexed", action="store_true",
                    help=argparse.SUPPRESS)          # now the default; kept
    ap.add_argument("--verify", action="store_true",
                    help="RUN THIS FIRST: cross-check minute vs hourly data")
    ap.add_argument("--year", type=int, default=2024, help="verify year")
    ap.add_argument("--month", type=int, default=6, help="verify month (1-12)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--version", action="store_true",
                    help="print version and the file actually executing")
    a = ap.parse_args()

    if a.version:
        print(f"dukascopy_intraday.py v{VERSION}")
        print(f"  running from: {os.path.abspath(__file__)}")
        print(f"  dukascopy.py: {os.path.abspath(dk.__file__)}")
        print(f"  python      : {sys.executable}")
        print(f"  pandas      : {pd.__version__}")
        sys.exit(0)

    if a.self_test:
        sys.exit(self_test())

    divisor = a.price_divisor or dk.PRICE_DIVISORS.get(a.instrument, 1000.0)
    cache_dir = None if a.no_cache else a.cache_dir
    zero_indexed = bool(a.day_zero_indexed)

    # Every run self-identifies. macOS silently renames rather than overwrites
    # downloaded files, so "the fix didn't work" is very often "the fixed file
    # is sitting next to the one that actually ran".
    print(f"\ndukascopy_intraday.py v{VERSION}  "
          f"[{os.path.abspath(__file__)}]")
    print(f"  day index: {'ZERO' if zero_indexed else 'ONE'}-indexed"
          f"{'  (non-default -- are you sure?)' if zero_indexed else ''}")

    if a.verify:
        ok = verify(a.instrument, a.year, a.month, a.side, divisor,
                    cache_dir, a.timeout, a.pause)
        sys.exit(0 if ok else 1)

    def parse_period(text, default_month):
        if "-" in text:
            y, m = text.split("-")
            return int(y), int(m)
        return int(text), default_month

    start = parse_period(a.start, 1)
    end = parse_period(a.end, 12) if a.end else (pd.Timestamp.utcnow().year,
                                                 pd.Timestamp.utcnow().month)

    days = day_range(start, end)
    print(f"\nfetching {len(days):,} day-files of {a.instrument} {a.side} min_1")
    print(f"  {days[0][0]}-{days[0][1]:02d}-{days[0][2]:02d} -> "
          f"{days[-1][0]}-{days[-1][1]:02d}-{days[-1][2]:02d}")
    print(f"  target timeframe: {a.tf}")
    if cache_dir:
        print(f"  cache: {cache_dir}")
    est = len(days) * (a.pause + 0.6) / 60
    print(f"  rough first-run estimate: {est:.0f} min "
          f"(re-runs are near-instant from cache)")
    print("  weekends 404 and are cached as empty -- that is expected\n")

    frames, ok_n, empty_n, fail_n = [], 0, 0, 0
    failed = []
    for i, (y, m, d) in enumerate(days, 1):
        try:
            part = fetch_day(a.instrument, y, m, d, a.side, divisor, cache_dir,
                             a.timeout, retries=a.retries,
                             day_zero_indexed=zero_indexed)
        except Exception as exc:                            # noqa: BLE001
            print(f"  [{i}/{len(days)}] {y}-{m:02d}-{d:02d} FAILED: {exc}")
            fail_n += 1
            failed.append((y, m, d))
            continue
        if part.empty:
            empty_n += 1
        else:
            frames.append(part)
            ok_n += 1
        if i % 200 == 0:
            print(f"  [{i}/{len(days)}] ok {ok_n}  empty {empty_n}  "
                  f"failed {fail_n}   bars so far {sum(len(f) for f in frames):,}")
        if a.pause:
            time.sleep(a.pause)

    if not frames:
        raise SystemExit("\nNo data retrieved. Run --verify on a recent month first.")

    minute = pd.concat(frames)
    minute = minute[~minute.index.duplicated(keep="first")].sort_index()
    print(f"\n  {len(minute):,} raw 1-minute bars")
    print(f"  span {minute.index.min()} -> {minute.index.max()}")

    if not a.keep_flat:
        minute, fstats = dk.filter_flat_bars(minute)
        dk.report_filter(fstats)

    df = resample_ohlcv(minute, a.tf) if a.tf != "1m" else minute
    print(f"\n  resampled to {a.tf}: {len(df):,} bars")

    stats = dk.FetchStats(ok=ok_n, empty=empty_n, failed=fail_n)
    good = dk.report(df, stats, a.instrument)

    if failed:
        print(f"\n  {len(failed)} day(s) failed and were NOT cached. "
              f"Re-run the identical\n  command to retry only those.")

    out = a.out or f"{a.instrument.lower()}_{a.tf}.csv"
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    df.to_csv(out)
    print(f"\nwrote {len(df):,} bars to {out}")
    print("\nNext -- you need gold and the dollar too, the strategy regresses")
    print("silver on gold and cannot run on silver alone:")
    print(f"  python dukascopy_intraday.py --instrument XAUUSD --tf {a.tf} "
          f"--start {a.start} --out ../data/xauusd_{a.tf}.csv")
    print(f"  python dukascopy_intraday.py --instrument EURUSD --tf {a.tf} "
          f"--start {a.start} --out ../data/eurusd_{a.tf}.csv   # DXY proxy")
    print(f"\nThen:  python silver_mr.py --data ../data")

    if not good:
        sys.exit(1)


def self_test() -> int:
    failures = []
    print(f"dukascopy_intraday.py v{VERSION}")
    print(f"  file: {os.path.abspath(__file__)}\n")

    def check(name, cond, detail=""):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
        if not cond:
            failures.append(name)

    print("day URL construction")
    u = day_url("XAGUSD", 2024, 6, 14, day_zero_indexed=True)
    check("month zero-indexed, day zero-indexed",
          u.endswith("/XAGUSD/2024/05/13/BID_candles_min_1.bi5"), f"got {u}")
    u2 = day_url("XAGUSD", 2024, 6, 14, day_zero_indexed=False)
    check("one-indexed variant available",
          u2.endswith("/2024/05/14/BID_candles_min_1.bi5"), f"got {u2}")
    check("January still maps to 00",
          "/2024/00/" in day_url("XAGUSD", 2024, 1, 5))
    for bad in (0, 32):
        try:
            day_url("XAGUSD", 2024, 6, bad)
            check(f"day {bad} rejected", False, "no error")
        except ValueError:
            check(f"day {bad} rejected", True)

    print("\nday time base")
    check("offsets are relative to day start",
          day_base(2024, 6, 14) == pd.Timestamp("2024-06-14", tz="UTC"))

    print("\ndecoding a day of minute candles (reusing dk.decode_candles)")
    truth = [(0, 30_000, 30_100, 29_950, 30_150, 5.0),      # 00:00
             (60, 30_100, 30_050, 30_000, 30_200, 3.0),     # 00:01
             (3600, 30_050, 30_400, 30_050, 30_450, 8.0)]   # 01:00
    payload = b"".join(dk.CANDLE_STRUCT.pack(*r) for r in truth)
    df = dk.decode_candles(payload, day_base(2024, 6, 14), 1000.0)
    check("three minute bars decoded", len(df) == 3, f"got {len(df)}")
    check("first bar at midnight",
          df.index[0] == pd.Timestamp("2024-06-14 00:00", tz="UTC"), f"got {df.index[0]}")
    check("second bar one minute later",
          df.index[1] == pd.Timestamp("2024-06-14 00:01", tz="UTC"), f"got {df.index[1]}")
    check("field order o,c,l,h preserved",
          abs(df["close"].iloc[0] - 30.1) < 1e-9 and abs(df["low"].iloc[0] - 29.95) < 1e-9,
          f"close={df['close'].iloc[0]} low={df['low'].iloc[0]}")

    print("\nresampling")
    idx = pd.date_range("2024-06-14 09:00", periods=60, freq="1min", tz="UTC")
    rng = np.random.default_rng(0)
    c = 30 + np.cumsum(rng.standard_normal(60) * 0.01)
    m = pd.DataFrame({"open": c, "high": c + 0.02, "low": c - 0.02,
                      "close": c, "volume": 1.0}, index=idx)
    r15 = resample_ohlcv(m, "15m")
    check("60 x 1m -> 4 x 15m", len(r15) == 4, f"got {len(r15)}")
    check("first 15m bar labelled 09:00",
          r15.index[0] == pd.Timestamp("2024-06-14 09:00", tz="UTC"), f"got {r15.index[0]}")
    check("open taken from first minute",
          abs(r15["open"].iloc[0] - m["open"].iloc[0]) < 1e-12)
    check("close taken from last minute of the bucket",
          abs(r15["close"].iloc[0] - m["close"].iloc[14]) < 1e-12)
    check("high is the bucket max",
          abs(r15["high"].iloc[0] - m["high"].iloc[:15].max()) < 1e-12)
    check("low is the bucket min",
          abs(r15["low"].iloc[0] - m["low"].iloc[:15].min()) < 1e-12)
    check("volume summed", abs(r15["volume"].iloc[0] - 15.0) < 1e-9)

    # a gap must not produce a synthetic bar
    gapped = pd.concat([m.iloc[:15], m.iloc[45:]])
    rg = resample_ohlcv(gapped, "15m")
    check("empty buckets dropped, not filled", len(rg) == 2, f"got {len(rg)}")

    print("\nday ranges")
    d = day_range((2024, 1), (2024, 2))
    check("Jan+Feb 2024 is 60 days (leap year)", len(d) == 60, f"got {len(d)}")
    check("starts on the 1st", d[0] == (2024, 1, 1), f"got {d[0]}")
    check("ends on Feb 29", d[-1] == (2024, 2, 29), f"got {d[-1]}")
    check("10 years is ~3,653 days",
          3640 < len(day_range((2016, 1), (2025, 12))) < 3660)

    print("\ncache paths are period-scoped (must not collide with hourly cache)")
    p, _ = day_cache_paths("/tmp/c", "XAGUSD", "BID", "min_1", 2024, 6, 14)
    h, _ = dk.cache_paths("/tmp/c", "XAGUSD", "BID", 2024, 6)
    check("minute cache key differs from hourly", p != h)
    check("minute cache key includes the day", "_14" in os.path.basename(p))

    print("\ncache paths are convention-scoped (the v0.3 collision bug)")
    p0, e0 = day_cache_paths("/tmp/c", "XAGUSD", "BID", "min_1", 2024, 6, 14,
                             day_zero_indexed=True)
    p1, e1 = day_cache_paths("/tmp/c", "XAGUSD", "BID", "min_1", 2024, 6, 14,
                             day_zero_indexed=False)
    check("zero- and one-indexed passes use different cache files", p0 != p1,
          f"both resolved to {p0}")
    check("their .empty sentinels differ too", e0 != e1)

    print("\nverified day-index convention (XAGUSD 2024-06, exact price match)")
    check("default day URL for the 6th points at /06/, not /05/",
          day_url("XAGUSD", 2024, 6, 6, day_zero_indexed=False)
          .endswith("/XAGUSD/2024/05/06/BID_candles_min_1.bi5"),
          f"got {day_url('XAGUSD', 2024, 6, 6, day_zero_indexed=False)}")
    check("month is still zero-indexed under the new day convention",
          "/2024/05/" in day_url("XAGUSD", 2024, 6, 6, day_zero_indexed=False))

    print("\n" + "=" * 60)
    if failures:
        print(f"{len(failures)} FAILED: {', '.join(failures)}")
        return 1
    print("all offline checks passed -- now run --verify against the live feed")
    return 0


if __name__ == "__main__":
    main()
