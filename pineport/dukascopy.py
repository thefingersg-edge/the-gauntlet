#!/usr/bin/env python3
"""Fetch deep-history XAUUSD hourly bars from Dukascopy's public data feed.

Dukascopy publish free historical data going back to roughly 2003 for metals,
which covers your entire 2006-2026 TradingView trade history. This is the piece
Yahoo cannot supply -- Yahoo caps hourly at 730 days.

    python dukascopy.py --probe --year 2024 --month 6     # test one month first
    python dukascopy.py --start 2006 --end 2026 --out xauusd_1h.csv
    python dukascopy.py --self-test                       # offline, no network

HOW THE FEED WORKS
------------------
Hourly candles are published one file per instrument per month:

    https://datafeed.dukascopy.com/datafeed/XAUUSD/2024/05/BID_candles_hour_1.bi5
                                                    ^^^^ ^^
                                                    year month

**The month is ZERO-INDEXED.** January is `00`, December is `11`. This trips up
almost everyone who writes one of these; getting it wrong silently returns the
wrong month's data rather than an error, so it is worth stating twice.

Each `.bi5` file is LZMA-compressed. Decompressed, it is a flat array of 24-byte
big-endian records:

    offset  4 bytes  int32    seconds since the start of the month
    open    4 bytes  int32    price * 1000 (for XAUUSD)
    close   4 bytes  int32
    low     4 bytes  int32
    high    4 bytes  int32
    volume  4 bytes  float32

Note the field order: **open, close, low, high** -- not OHLC. Reading it as OHLC
produces bars that look plausible and are wrong, which is the kind of bug that
survives into a backtest. `--self-test` checks the unpacking against a payload
built by hand.

CAVEATS WORTH KNOWING BEFORE YOU TRUST THE OUTPUT
-------------------------------------------------
* Dukascopy is a different venue from OANDA. Bars will differ slightly and your
  TradingView trade list will NOT reproduce exactly. Keep the OANDA chart export
  as the verification reference; use this for research. Different jobs, and it
  is fine for them to use different data.
* Volume is Dukascopy's own measure, not exchange volume. It is non-zero, which
  is what the `ta.vwma()` calls in the strategy actually need.
* Early years are thinner. Check the gap report before drawing conclusions about
  2006-2010.
* This script was written without network access to test against, so the
  decoding logic is unit-tested offline but the live fetch is not. Run `--probe`
  on one month first and eyeball the prices before starting a 20-year pull.
"""

from __future__ import annotations

import argparse
import calendar
import lzma
import os
import struct
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

import numpy as np
import pandas as pd

BASE_URL = "https://datafeed.dukascopy.com/datafeed"
USER_AGENT = "Mozilla/5.0 (compatible; pineport-research/1.0)"

#: 24 bytes: offset, open, close, low, high, volume
CANDLE_STRUCT = struct.Struct(">5if")
CANDLE_SIZE = CANDLE_STRUCT.size

#: Price scaling by instrument. Dukascopy stores prices as integers.
#: Integer price scaling by instrument. If one is wrong or missing, the sanity
#: check in `report()` catches it and prints the divisor to use instead --
#: always run `--probe` on a new instrument before a full pull.
PRICE_DIVISORS = {
    # metals: 3 decimal places
    "XAUUSD": 1000.0, "XAUEUR": 1000.0, "XAUGBP": 1000.0,
    "XAUJPY": 1000.0, "XAUCHF": 1000.0,
    "XAGUSD": 1000.0, "XPTUSD": 1000.0, "XPDUSD": 1000.0,
    # FX majors: 5 decimal places
    "EURUSD": 100000.0, "GBPUSD": 100000.0, "AUDUSD": 100000.0,
    "NZDUSD": 100000.0, "USDCHF": 100000.0, "USDCAD": 100000.0,
    "EURGBP": 100000.0, "EURCHF": 100000.0,
    # JPY crosses: 3 decimal places
    "USDJPY": 1000.0, "EURJPY": 1000.0, "GBPJPY": 1000.0, "AUDJPY": 1000.0,
    # index and commodity CFDs: 3 decimal places
    "USA500IDXUSD": 1000.0, "USA30IDXUSD": 1000.0, "USATECHIDXUSD": 1000.0,
    "DEUIDXEUR": 1000.0, "GBRIDXGBP": 1000.0, "JPNIDXJPY": 1000.0,
    "BRENTCMDUSD": 1000.0, "LIGHTCMDUSD": 1000.0,
    # copper is quoted to 4dp on this feed, unlike the other commodity CFDs
    "COPPERCMDUSD": 10000.0,
}

#: Sanity ranges used to catch a wrong divisor before it reaches a backtest.
#: Deliberately wide -- these catch factor-of-ten errors, not fine detail.
PLAUSIBLE_RANGE = {
    "XAUUSD": (200.0, 20000.0), "XAUEUR": (200.0, 20000.0),
    "XAUGBP": (200.0, 20000.0), "XAUCHF": (200.0, 20000.0),
    "XAUJPY": (20000.0, 2000000.0),
    "XAGUSD": (2.0, 200.0), "XPTUSD": (200.0, 5000.0), "XPDUSD": (100.0, 5000.0),
    "EURUSD": (0.5, 2.0), "GBPUSD": (0.8, 2.5), "AUDUSD": (0.4, 1.5),
    "NZDUSD": (0.3, 1.2), "USDCHF": (0.5, 2.0), "USDCAD": (0.8, 2.0),
    "EURGBP": (0.5, 1.2), "EURCHF": (0.8, 2.0),
    "USDJPY": (60.0, 300.0), "EURJPY": (80.0, 350.0),
    "GBPJPY": (100.0, 400.0), "AUDJPY": (40.0, 200.0),
    "USA500IDXUSD": (500.0, 20000.0), "USA30IDXUSD": (5000.0, 100000.0),
    "USATECHIDXUSD": (1000.0, 60000.0), "DEUIDXEUR": (3000.0, 60000.0),
    "GBRIDXGBP": (3000.0, 20000.0), "JPNIDXJPY": (5000.0, 100000.0),
    "BRENTCMDUSD": (10.0, 300.0), "LIGHTCMDUSD": (5.0, 300.0),
    "COPPERCMDUSD": (0.5, 20.0),
}

#: History start dates differ a lot. FX and metals go back to ~2003; index and
#: commodity CFDs typically start much later. Probe before assuming a range.
TYPICAL_HISTORY_START = {
    "fx / metals": "2003",
    "index CFDs": "2010-2012",
    "commodity CFDs": "2011-2013",
}


# --------------------------------------------------------------------------
# URL construction
# --------------------------------------------------------------------------

def month_url(instrument: str, year: int, month: int, side: str = "BID",
              period: str = "hour_1") -> str:
    """Build the feed URL for one month of candles.

    ``month`` is given 1-12 as a human would write it and converted to
    Dukascopy's zero-indexed form here, in one place, so the off-by-one can only
    happen once.
    """
    if not 1 <= month <= 12:
        raise ValueError(f"month must be 1-12, got {month}")
    return (f"{BASE_URL}/{instrument}/{year:04d}/{month - 1:02d}/"
            f"{side}_candles_{period}.bi5")


# --------------------------------------------------------------------------
# decoding -- pure, unit tested offline
# --------------------------------------------------------------------------

def decompress_bi5(raw: bytes) -> bytes:
    """Decompress a ``.bi5`` payload.

    The files are LZMA-alone (not xz), and some carry an unknown-size header,
    so several decoder configurations are tried before giving up. An empty
    payload is legitimate -- weekends and holidays have no candles.
    """
    if not raw:
        return b""

    attempts = (
        dict(format=lzma.FORMAT_ALONE),
        dict(format=lzma.FORMAT_AUTO),
        dict(format=lzma.FORMAT_RAW,
             filters=[{"id": lzma.FILTER_LZMA1, "preset": 6}]),
    )
    last: Exception | None = None
    for kwargs in attempts:
        try:
            return lzma.LZMADecompressor(**kwargs).decompress(raw)
        except Exception as exc:                        # noqa: BLE001
            last = exc
    raise ValueError(f"could not decompress bi5 payload ({len(raw)} bytes): {last}")


def decode_candles(payload: bytes, base: pd.Timestamp,
                   divisor: float) -> pd.DataFrame:
    """Turn a decompressed candle payload into an OHLCV frame.

    ``base`` is the start of the period the offsets are relative to -- the first
    instant of the month for ``hour_1`` files.
    """
    cols = ["open", "high", "low", "close", "volume"]
    if not payload:
        return pd.DataFrame(columns=cols,
                            index=pd.DatetimeIndex([], tz="UTC", name="time"))

    usable = len(payload) - (len(payload) % CANDLE_SIZE)
    if usable != len(payload):
        print(f"    warning: payload has {len(payload) % CANDLE_SIZE} trailing "
              f"bytes, ignoring them")

    records = [CANDLE_STRUCT.unpack_from(payload, i)
               for i in range(0, usable, CANDLE_SIZE)]
    if not records:
        return pd.DataFrame(columns=cols,
                            index=pd.DatetimeIndex([], tz="UTC", name="time"))

    arr = np.asarray(records, dtype=np.float64)
    # Column order in the file is offset, OPEN, CLOSE, LOW, HIGH, volume.
    offsets, o, c, l, h, vol = (arr[:, i] for i in range(6))

    idx = base + pd.to_timedelta(offsets, unit="s")
    df = pd.DataFrame({
        "open": o / divisor, "high": h / divisor,
        "low": l / divisor, "close": c / divisor,
        "volume": vol,
    }, index=pd.DatetimeIndex(idx, name="time"))

    return df.sort_index()


def month_base(year: int, month: int) -> pd.Timestamp:
    return pd.Timestamp(year=year, month=month, day=1, tz="UTC")


def filter_flat_bars(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Remove Dukascopy's non-trading-hour padding.

    Dukascopy publish a bar for every hour of the calendar, including weekends
    and the daily settlement break. Outside trading hours they repeat the last
    price with **zero volume**, so a raw month contains 24 x days bars rather
    than the ~24 x 5/7 x days a 24/5 market actually trades.

    Those padded bars must go, and not merely for tidiness:

    * Every band in this strategy is a ``ta.vwma()``, which divides by summed
      volume. A window landing entirely inside padding is 0/0 -> NaN.
    * Flat bars make ``ta.rsi(close, 1)`` undefined (no price change),
      ``ta.stdev`` zero, and ``ta.atr`` zero.
    * OANDA -- the feed the port is verified against -- omits closed hours
      entirely. Keeping the padding would shift every bar index, and this
      strategy indexes into history directly (``close[since_entry_long]``, a
      942-bar lookback, a 4H resample). Misaligned indices produce a backtest
      that runs cleanly and means nothing.

    Zero volume is the marker of "no trading occurred". The returned stats
    include a cross-check that the dropped bars were also price-flat, which is
    what you would expect if they really are padding.
    """
    is_padding = df["volume"].fillna(0) <= 0
    flat = df["high"] <= df["low"] + 1e-12

    stats = {
        "before": len(df),
        "dropped": int(is_padding.sum()),
        "dropped_and_flat": int((is_padding & flat).sum()),
        "dropped_not_flat": int((is_padding & ~flat).sum()),
        "flat_but_traded": int((~is_padding & flat).sum()),
    }
    out = df.loc[~is_padding].copy()
    stats["after"] = len(out)
    return out, stats


def report_filter(stats: dict) -> None:
    kept = stats["after"]
    print(f"\n  non-trading padding removed")
    print(f"    bars before            {stats['before']:,}")
    print(f"    zero-volume bars       {stats['dropped']:,} "
          f"({100*stats['dropped']/max(stats['before'],1):.1f}%)")
    print(f"      of which price-flat  {stats['dropped_and_flat']:,}  "
          f"(expected: padding repeats the last price)")
    if stats["dropped_not_flat"]:
        print(f"      NOT flat             {stats['dropped_not_flat']:,}  "
              f"<-- unusual; zero volume but the price moved")
    print(f"    bars kept              {kept:,}")
    expected = stats["before"] * 5 / 7
    if kept and abs(kept - expected) / expected > 0.25:
        print(f"    note: kept {kept:,} vs ~{expected:,.0f} expected for a 24/5 "
              f"market -- worth a look")


# --------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------

@dataclass
class FetchStats:
    ok: int = 0
    empty: int = 0
    missing: int = 0
    failed: int = 0


#: Server-side conditions that mean "try again later", not "this is broken".
#: 503 is what Dukascopy returns when it is throttling a long run of requests.
RETRYABLE_CODES = {408, 425, 429, 500, 502, 503, 504}


def http_get(url: str, timeout: float = 30.0, retries: int = 6,
             backoff: float = 2.0, verbose: bool = False) -> bytes | None:
    """GET with retries. Returns None for 404 (a month with no data published).

    Rate-limit and overload responses get exponential backoff rather than the
    quick successive retries that would simply be throttled again. Dukascopy is
    a free service and 503 during a 240-request run is it asking for patience,
    so the delay grows 2s, 4s, 8s, 16s, 32s -- which is slower but finishes,
    where hammering does not.

    A ``Retry-After`` header, when present, overrides the computed delay.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    delay = 2.0
    last_reason = ""

    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()

        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None                      # legitimately absent
            if exc.code not in RETRYABLE_CODES:
                raise
            last_reason = f"HTTP {exc.code}"
            hinted = exc.headers.get("Retry-After") if exc.headers else None
            if hinted:
                try:
                    delay = max(delay, float(hinted))
                except ValueError:
                    pass

        except Exception as exc:                 # noqa: BLE001
            last_reason = type(exc).__name__

        if attempt == retries:
            raise RuntimeError(
                f"{last_reason} after {retries} attempts. Dukascopy is "
                f"throttling; re-run the same command later -- cached months "
                f"are skipped.")

        if verbose:
            print(f"      {last_reason}, waiting {delay:.0f}s "
                  f"(attempt {attempt}/{retries})")
        time.sleep(delay)
        delay *= backoff

    return None


def cache_paths(cache_dir: str, instrument: str, side: str,
                year: int, month: int) -> tuple[str, str]:
    """Return (data path, 'known empty' sentinel path) for one month."""
    stem = os.path.join(cache_dir,
                        f"{instrument}_{side}_{year:04d}_{month:02d}")
    return stem + ".bi5", stem + ".empty"


def fetch_month(instrument: str, year: int, month: int, side: str,
                divisor: float, cache_dir: str | None,
                timeout: float, retries: int = 6,
                verbose: bool = False) -> pd.DataFrame:
    """Fetch and decode one month, using a local cache when available.

    Two kinds of cache entry are kept. A ``.bi5`` file holds a successful
    download. A zero-byte ``.empty`` sentinel records that the server answered
    404 -- legitimate for months before the instrument's history starts.
    Without the sentinel, every re-run would re-request those months forever.

    Failures (timeouts, rate limits) are deliberately NOT cached, so re-running
    the same command retries exactly the months that did not succeed.
    """
    data_path = empty_path = None
    if cache_dir:
        data_path, empty_path = cache_paths(cache_dir, instrument, side,
                                            year, month)
        if os.path.exists(data_path):
            with open(data_path, "rb") as fh:
                raw = fh.read()
            return decode_candles(decompress_bi5(raw), month_base(year, month),
                                  divisor)
        if os.path.exists(empty_path):
            return decode_candles(b"", month_base(year, month), divisor)

    raw = http_get(month_url(instrument, year, month, side), timeout=timeout,
                   retries=retries, verbose=verbose)

    if raw is None:                       # 404 -- no data published
        if empty_path:
            os.makedirs(cache_dir, exist_ok=True)
            open(empty_path, "wb").close()
        return decode_candles(b"", month_base(year, month), divisor)

    if data_path:
        os.makedirs(cache_dir, exist_ok=True)
        with open(data_path, "wb") as fh:
            fh.write(raw)

    return decode_candles(decompress_bi5(raw), month_base(year, month), divisor)


def cache_report(cache_dir: str, instrument: str, side: str,
                 months: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Show which months are cached, and return the ones still outstanding."""
    have, empty, missing = [], [], []
    for y, m in months:
        data_path, empty_path = cache_paths(cache_dir, instrument, side, y, m)
        if os.path.exists(data_path):
            have.append((y, m))
        elif os.path.exists(empty_path):
            empty.append((y, m))
        else:
            missing.append((y, m))

    print(f"\nCache coverage for {instrument} {side}")
    print("-" * 68)
    print(f"  downloaded        {len(have)}")
    print(f"  known empty (404) {len(empty)}")
    print(f"  still missing     {len(missing)}")

    by_year: dict[int, list[str]] = {}
    for y, m in months:
        data_path, empty_path = cache_paths(cache_dir, instrument, side, y, m)
        mark = ("#" if os.path.exists(data_path)
                else "." if os.path.exists(empty_path) else "?")
        by_year.setdefault(y, []).append(mark)

    print("\n  # downloaded   . empty(404)   ? missing")
    print("        JFMAMJJASOND")
    for y in sorted(by_year):
        print(f"  {y}  {''.join(by_year[y])}")

    if missing:
        print(f"\n  {len(missing)} month(s) outstanding. Re-run the same command "
              f"to retry\n  only those -- completed months are read from cache:")
        print("    --pause 1.0 --timeout 60   (slower and more patient, if the")
        print("                                failures look like rate limits)")
    return missing


def month_range(start_year: int, start_month: int,
                end_year: int, end_month: int) -> list[tuple[int, int]]:
    out = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        out.append((y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def fetch_range(instrument: str, start: tuple[int, int], end: tuple[int, int],
                side: str, divisor: float, cache_dir: str | None,
                pause: float, timeout: float, retries: int = 6
                ) -> tuple[pd.DataFrame, FetchStats]:
    months = month_range(*start, *end)
    print(f"\nfetching {len(months)} month(s) of {instrument} {side} hourly "
          f"candles")
    print(f"  {months[0][0]}-{months[0][1]:02d} -> {months[-1][0]}-{months[-1][1]:02d}")
    if cache_dir:
        print(f"  cache: {cache_dir}  (re-runs skip months already downloaded)")

    stats = FetchStats()
    failed_months: list[tuple[int, int]] = []
    frames = []
    for i, (y, m) in enumerate(months, 1):
        label = f"  [{i:>3}/{len(months)}] {y}-{m:02d}"
        try:
            part = fetch_month(instrument, y, m, side, divisor, cache_dir,
                               timeout, retries=retries, verbose=True)
        except Exception as exc:                        # noqa: BLE001
            print(f"{label}  FAILED: {exc}")
            stats.failed += 1
            failed_months.append((y, m))
            continue

        if part.empty:
            print(f"{label}  no data")
            stats.empty += 1
        else:
            frames.append(part)
            stats.ok += 1
            if i % 12 == 0 or i == len(months):
                print(f"{label}  {len(part):>4} bars   "
                      f"(running total {sum(len(f) for f in frames):,})")
        if pause:
            time.sleep(pause)

    if failed_months:
        print(f"\n  {len(failed_months)} month(s) failed and were NOT cached, so")
        print(f"  re-running the identical command retries only these:")
        for y, m in failed_months[:24]:
            print(f"    {y}-{m:02d}")
        if len(failed_months) > 24:
            print(f"    ... and {len(failed_months) - 24} more")

    if not frames:
        raise SystemExit(
            "\nNo data retrieved. Run --probe on a single recent month to check "
            "connectivity\nand the instrument name before pulling a long range."
        )

    df = pd.concat(frames)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df, stats


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def sanity_check_prices(df: pd.DataFrame, instrument: str) -> bool:
    """Catch a wrong price divisor before the data reaches a backtest."""
    lo, hi = PLAUSIBLE_RANGE.get(instrument, (0.0, float("inf")))
    median = float(df["close"].median())
    if lo <= median <= hi:
        return True
    print(f"\n  PRICE SCALE LOOKS WRONG")
    print(f"  Median close is {median:,.3f}, expected roughly {lo:,.0f}-{hi:,.0f} "
          f"for {instrument}.")
    # Suggest the divisor landing closest to the middle of the plausible range,
    # not merely the first one that fits -- several can fit at the edges.
    applied = PRICE_DIVISORS.get(instrument, 1000.0)
    raw_median = median * applied
    target = (lo * hi) ** 0.5
    candidates = [10.0 ** k for k in range(0, 9)]
    best, best_err = None, float("inf")
    for candidate in candidates:
        scaled = raw_median / candidate
        if not lo <= scaled <= hi:
            continue
        err = abs(np.log(scaled / target))
        if err < best_err:
            best, best_err = candidate, err
    if best is not None:
        print(f"  Try --price-divisor {best:g} "
              f"(would give a median of {raw_median / best:,.2f}).")
    else:
        print(f"  No power-of-ten divisor lands in range; raw median is "
              f"{raw_median:,.0f}.")
    return False


def report(df: pd.DataFrame, stats: FetchStats, instrument: str) -> bool:
    print("\nResult")
    print("-" * 68)
    print(f"  months ok / empty / failed   {stats.ok} / {stats.empty} / {stats.failed}")
    print(f"  bars                         {len(df):,}")
    print(f"  range                        {df.index[0]:%Y-%m-%d %H:%M} -> "
          f"{df.index[-1]:%Y-%m-%d %H:%M}")
    print(f"  span                         "
          f"{(df.index[-1] - df.index[0]).days / 365.25:.1f} years")
    print(f"  price range                  {df['close'].min():,.2f} - "
          f"{df['close'].max():,.2f}")

    ok = sanity_check_prices(df, instrument)

    hi_ok = df["high"] >= df[["open", "close"]].max(axis=1) - 1e-9
    lo_ok = df["low"] <= df[["open", "close"]].min(axis=1) + 1e-9
    violations = int((~(hi_ok & lo_ok)).sum())
    print(f"  OHLC integrity violations    {violations}"
          f"  [{'ok' if violations == 0 else 'FAIL'}]")
    if violations:
        ok = False

    total_volume = float(np.nansum(df["volume"].to_numpy()))
    print(f"  total volume                 {total_volume:,.0f}"
          f"  [{'ok' if total_volume > 0 else 'FAIL'}]")
    if total_volume <= 0:
        ok = False
        print("    Every ta.vwma() in the strategy divides by volume; a "
              "zero-volume feed\n    produces NaN signals and a zero-trade "
              "backtest that looks like a result.")

    deltas = df.index.to_series().diff().dropna()
    if len(deltas):
        modal = deltas.mode().iloc[0]
        print(f"  modal bar spacing            {modal}")

        # Every weekend is a ~49h gap. Reporting those as anomalies would bury
        # the ones that matter, so they are classified out: a gap is "weekend"
        # when the bar before it is a Friday and the bar after is Sun or Mon.
        big = deltas[deltas > modal * 3]
        if len(big):
            ends = big.index
            starts = df.index[df.index.get_indexer(ends) - 1]
            is_weekend = (starts.dayofweek == 4) & (ends.dayofweek.isin([6, 0]))
            weekend_gaps = int(is_weekend.sum())
            other = big[~is_weekend]

            print(f"  weekend closes               {weekend_gaps}  "
                  f"(expected ~52/year)")
            print(f"  other gaps over 3 bars       {len(other)}")
            if len(other):
                print("    largest non-weekend gaps:")
                for ts, gap in other.nlargest(5).items():
                    i = df.index.get_loc(ts)
                    print(f"      {gap}  ending {ts:%Y-%m-%d %H:%M} "
                          f"(from {df.index[i-1]:%Y-%m-%d %H:%M})")
                print("    Holidays (Christmas, New Year) and thin early-history")
                print("    liquidity account for most of these. Long gaps")
                print("    concentrated in one year are worth a closer look.")

    by_year = df.groupby(df.index.year).size()
    print("\n  bars per year:")
    for year, n in by_year.items():
        flag = "  <-- thin" if n < 3000 else ""
        print(f"    {year}  {n:>6,}{flag}")

    return ok


# --------------------------------------------------------------------------
# offline self-test
# --------------------------------------------------------------------------

def self_test() -> int:
    failures = []

    def check(name, cond, detail=""):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
        if not cond:
            failures.append(name)

    print("URL construction")
    url = month_url("XAUUSD", 2024, 1)
    check("January maps to 00 (zero-indexed month)", url.endswith("/2024/00/BID_candles_hour_1.bi5"),
          f"got {url}")
    check("December maps to 11",
          month_url("XAUUSD", 2024, 12).endswith("/2024/11/BID_candles_hour_1.bi5"))
    check("ASK side selectable",
          "ASK_candles_hour_1" in month_url("XAUUSD", 2024, 6, side="ASK"))
    for bad in (0, 13):
        try:
            month_url("XAUUSD", 2024, bad)
            check(f"month {bad} rejected", False, "no error")
        except ValueError:
            check(f"month {bad} rejected", True)

    print("\nbinary decoding")
    # Build a payload by hand: 3 hourly candles at the start of a month.
    truth = [
        # offset_s,  open,    close,   low,     high,    volume
        (0,          2000_000, 2005_000, 1998_000, 2007_000, 12.5),
        (3600,       2005_000, 2001_000, 2000_000, 2008_000, 9.25),
        (7200,       2001_000, 2010_000, 2000_500, 2011_000, 30.0),
    ]
    payload = b"".join(CANDLE_STRUCT.pack(*r) for r in truth)
    check("record size is 24 bytes", CANDLE_SIZE == 24, f"got {CANDLE_SIZE}")

    df = decode_candles(payload, month_base(2024, 6), 1000.0)
    check("all records decoded", len(df) == 3, f"got {len(df)}")
    check("first timestamp is the month start",
          df.index[0] == pd.Timestamp("2024-06-01", tz="UTC"), f"got {df.index[0]}")
    check("offsets are seconds",
          df.index[1] == pd.Timestamp("2024-06-01 01:00", tz="UTC"), f"got {df.index[1]}")
    check("price divisor applied", abs(df["open"].iloc[0] - 2000.0) < 1e-9,
          f"got {df['open'].iloc[0]}")

    # The field-order trap: file order is open, CLOSE, LOW, HIGH.
    check("close read from field 2", abs(df["close"].iloc[0] - 2005.0) < 1e-9,
          f"got {df['close'].iloc[0]} (expected 2005.0 -- field order is o,c,l,h)")
    check("low read from field 3", abs(df["low"].iloc[0] - 1998.0) < 1e-9,
          f"got {df['low'].iloc[0]}")
    check("high read from field 4", abs(df["high"].iloc[0] - 2007.0) < 1e-9,
          f"got {df['high'].iloc[0]}")
    check("volume preserved", abs(df["volume"].iloc[0] - 12.5) < 1e-6)
    check("decoded bars satisfy OHLC integrity",
          bool((df["high"] >= df[["open", "close"]].max(axis=1)).all()
               and (df["low"] <= df[["open", "close"]].min(axis=1)).all()))

    print("\nLZMA round trip")
    for fmt_name, kwargs in (("alone", dict(format=lzma.FORMAT_ALONE)),
                             ("xz", dict(format=lzma.FORMAT_XZ))):
        compressed = lzma.compress(payload, **kwargs)
        try:
            out = decompress_bi5(compressed)
            check(f"{fmt_name}-compressed payload decompresses", out == payload)
        except Exception as exc:                        # noqa: BLE001
            check(f"{fmt_name}-compressed payload decompresses", False, str(exc))

    check("empty payload returns empty frame", decode_candles(b"", month_base(2024, 6), 1000.0).empty)
    check("empty bytes decompress to empty", decompress_bi5(b"") == b"")
    check("truncated payload ignores the tail",
          len(decode_candles(payload + b"\x00\x03", month_base(2024, 6), 1000.0)) == 3)

    print("\nmonth ranges")
    r = month_range(2023, 11, 2024, 2)
    check("range spans the year boundary",
          r == [(2023, 11), (2023, 12), (2024, 1), (2024, 2)], f"got {r}")
    check("20 years is 240 months", len(month_range(2006, 1, 2025, 12)) == 240)
    check("single month works", month_range(2024, 6, 2024, 6) == [(2024, 6)])

    print("\nnon-trading padding filter")
    # A week where Sat/Sun are padded flat at zero volume, as Dukascopy publish it.
    idx = pd.date_range("2024-06-01", periods=24 * 7, freq="1h", tz="UTC")
    rng = np.random.default_rng(1)
    close = 2300 + np.cumsum(rng.standard_normal(len(idx)) * 0.5)
    frame = pd.DataFrame({"open": close, "high": close + 1, "low": close - 1,
                          "close": close, "volume": 1.0}, index=idx)
    weekend = frame.index.dayofweek >= 5
    frame.loc[weekend, ["open", "high", "low", "close"]] = 2300.0
    frame.loc[weekend, "volume"] = 0.0

    filtered, fstats = filter_flat_bars(frame)
    check("padding dropped", fstats["dropped"] == int(weekend.sum()),
          f"dropped {fstats['dropped']}, expected {int(weekend.sum())}")
    check("traded bars kept", len(filtered) == len(frame) - int(weekend.sum()))
    check("dropped bars were price-flat",
          fstats["dropped_and_flat"] == fstats["dropped"])
    check("no weekend bars survive", int((filtered.index.dayofweek >= 5).sum()) == 0)
    check("zero-volume bars all gone", bool((filtered["volume"] > 0).all()))
    check("index still sorted", bool(filtered.index.is_monotonic_increasing))

    print("\nprice sanity check")
    idx = pd.date_range("2024-01-01", periods=10, freq="1h", tz="UTC")
    good = pd.DataFrame({"open": 2000.0, "high": 2001.0, "low": 1999.0,
                         "close": 2000.0, "volume": 1.0}, index=idx)
    check("plausible gold prices accepted", sanity_check_prices(good, "XAUUSD"))
    bad = good * 1000
    check("wrong divisor detected", not sanity_check_prices(bad, "XAUUSD"))

    print("\n" + "=" * 60)
    if failures:
        print(f"{len(failures)} FAILED: {', '.join(failures)}")
        return 1
    print("all checks passed (network path untested -- run --probe first)")
    return 0


# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--instrument", default="XAUUSD")
    ap.add_argument("--start", default="2006", help="start year, or YYYY-MM")
    ap.add_argument("--end", default=None, help="end year, or YYYY-MM (default: now)")
    ap.add_argument("--side", default="BID", choices=["BID", "ASK", "MID"],
                    help="MID averages BID and ASK, doubling the requests")
    ap.add_argument("--price-divisor", type=float, default=None,
                    help="override the integer price scale (XAUUSD default 1000)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--cache-dir", default=".dukascopy_cache",
                    help="raw .bi5 cache; re-runs skip completed months")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--pause", type=float, default=0.4,
                    help="seconds between requests. Raise to 1.0+ if you are "
                         "seeing 503s -- that is Dukascopy throttling.")
    ap.add_argument("--timeout", type=float, default=45.0)
    ap.add_argument("--retries", type=int, default=6,
                    help="attempts per month, with exponential backoff on "
                         "429/503 and other transient codes")
    ap.add_argument("--cache-report", action="store_true",
                    help="show which months are cached and which are still "
                         "outstanding, without fetching anything")
    ap.add_argument("--keep-flat", action="store_true",
                    help="keep Dukascopy's zero-volume non-trading padding. "
                         "Off by default because the padding breaks every "
                         "ta.vwma() and shifts the bar index away from OANDA's.")
    ap.add_argument("--probe", action="store_true",
                    help="fetch a single month and print it -- do this first")
    ap.add_argument("--year", type=int, default=2024, help="probe year")
    ap.add_argument("--month", type=int, default=6, help="probe month (1-12)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())

    divisor = args.price_divisor or PRICE_DIVISORS.get(args.instrument, 1000.0)
    cache_dir = None if args.no_cache else args.cache_dir

    if args.probe:
        url = month_url(args.instrument, args.year, args.month, args.side)
        print(f"probing {url}")
        df = fetch_month(args.instrument, args.year, args.month,
                         args.side if args.side != "MID" else "BID",
                         divisor, cache_dir, args.timeout)
        if df.empty:
            print("\nNo data for that month. Check the instrument name and try a "
                  "recent month\n(e.g. --year 2024 --month 6).")
            sys.exit(1)

        print(f"\n{len(df)} raw bars")
        if not args.keep_flat:
            df, fstats = filter_flat_bars(df)
            report_filter(fstats)
            if df.empty:
                print("\nEverything was zero-volume. Re-run with --keep-flat to "
                      "inspect the raw data.")
                sys.exit(1)

        print(f"\nfirst 5 traded bars:")
        print(df.head(5).to_string())
        print("...")
        print(df.tail(3).to_string())

        by_dow = df.groupby(df.index.dayofweek).size()
        names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        print("\nbars by weekday (Sat should be ~0 for a 24/5 market):")
        print("  " + "  ".join(f"{names[d]} {n}" for d, n in by_dow.items()))

        sanity_check_prices(df, args.instrument)
        print("\nIf those prices look like gold, run the full pull:")
        print(f"  python dukascopy.py --start {args.start} --out "
              f"{args.instrument.lower()}_1h.csv")
        return

    def parse_period(text: str, default_month: int) -> tuple[int, int]:
        if "-" in text:
            y, m = text.split("-")
            return int(y), int(m)
        return int(text), default_month

    start = parse_period(args.start, 1)
    if args.end:
        end = parse_period(args.end, 12)
    else:
        now = pd.Timestamp.utcnow()
        end = (now.year, now.month)

    if args.cache_report:
        if not cache_dir:
            raise SystemExit("--cache-report needs a cache directory")
        side = "BID" if args.side == "MID" else args.side
        cache_report(cache_dir, args.instrument, side, month_range(*start, *end))
        return

    if args.side == "MID":
        bid, stats = fetch_range(args.instrument, start, end, "BID", divisor,
                                 cache_dir, args.pause, args.timeout,
                                 retries=args.retries)
        ask, _ = fetch_range(args.instrument, start, end, "ASK", divisor,
                             cache_dir, args.pause, args.timeout,
                             retries=args.retries)
        common = bid.index.intersection(ask.index)
        df = (bid.loc[common] + ask.loc[common]) / 2.0
        df["volume"] = bid.loc[common, "volume"] + ask.loc[common, "volume"]
        print(f"\nmid prices from {len(common):,} matched bid/ask bars")
    else:
        df, stats = fetch_range(args.instrument, start, end, args.side, divisor,
                                cache_dir, args.pause, args.timeout,
                                retries=args.retries)

    if not args.keep_flat:
        df, fstats = filter_flat_bars(df)
        report_filter(fstats)

    ok = report(df, stats, args.instrument)

    out = args.out or f"{args.instrument.lower()}_1h_dukascopy.csv"
    df.to_csv(out)
    print(f"\nwrote {len(df):,} bars to {out}")
    print("\nNext:")
    print(f"  python run.py backtest --csv {out} --point-value 1")
    print(f"  python run.py diagnose --csv {out}")
    print(f"  python variants.py --csv {out}")
    print("\nRemember: Dukascopy is a different venue from OANDA, so this will")
    print("not reproduce your TradingView trade list exactly. Keep the OANDA")
    print("chart export as the verification reference.")

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
