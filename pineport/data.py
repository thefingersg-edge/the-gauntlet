"""OHLCV loading and higher-timeframe resampling.

Two jobs:
  1. Fetch hourly gold data from yfinance with an on-disk cache, and normalise
     the frame into the ``open/high/low/close/volume`` columns the strategy uses.
  2. Reproduce Pine's ``request.security(..., lookahead_off)`` so the 4-hour
     trend filter sees exactly what TradingView shows it -- no lookahead.
"""

from __future__ import annotations

import hashlib
import os
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")

REQUIRED = ["open", "high", "low", "close", "volume"]


class ZeroVolumeError(RuntimeError):
    """Raised when a feed reports no volume and VWMA would silently be NaN."""


@dataclass
class DataInfo:
    """Provenance for a loaded frame, so results can be traced back."""
    ticker: str
    interval: str
    bars: int
    start: pd.Timestamp
    end: pd.Timestamp
    volume_synthetic: bool

    def describe(self) -> str:
        vol = " (synthetic unit volume)" if self.volume_synthetic else ""
        return (f"{self.ticker} {self.interval}: {self.bars} bars, "
                f"{self.start:%Y-%m-%d %H:%M} -> {self.end:%Y-%m-%d %H:%M}{vol}")


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def load_ohlcv(ticker: str = "GC=F", period: str = "730d", interval: str = "1h",
               on_zero_volume: str = "unit", use_cache: bool = True,
               csv_path: str | None = None) -> tuple[pd.DataFrame, DataInfo]:
    """Load OHLCV bars, from a CSV if given, otherwise from yfinance.

    Parameters
    ----------
    on_zero_volume:
        What to do when the feed reports zero/absent volume, which would make
        every VWMA in the strategy NaN. ``"unit"`` substitutes volume=1 (so VWMA
        collapses to a plain SMA and the strategy still runs, with a warning),
        ``"error"`` raises, ``"ignore"`` leaves the zeros in place.

    Notes
    -----
    yfinance caps intraday history at roughly 730 days. ``period="5y"`` with
    ``interval="1h"`` returns an error or an empty frame, not 5 years of data.
    """
    if csv_path:
        df = _read_csv(csv_path)
        source = os.path.basename(csv_path)
    else:
        df = _fetch_yfinance(ticker, period, interval, use_cache)
        source = ticker

    df = _normalise(df)

    synthetic = False
    total_volume = float(np.nansum(df["volume"].to_numpy()))
    if total_volume <= 0:
        if on_zero_volume == "error":
            raise ZeroVolumeError(
                f"{source} reports zero volume on every bar. Every ta.vwma() in "
                f"this strategy would evaluate to NaN and no trade would ever "
                f"fire. Use a feed with real volume (GC=F) or pass "
                f"on_zero_volume='unit'."
            )
        if on_zero_volume == "unit":
            warnings.warn(
                f"{source} has no volume data; substituting volume=1 on every "
                f"bar. Every VWMA in the strategy therefore behaves as a plain "
                f"SMA, which will NOT match a TradingView run on a "
                f"volume-bearing symbol.",
                stacklevel=2,
            )
            df["volume"] = 1.0
            synthetic = True

    info = DataInfo(
        ticker=source, interval=interval, bars=len(df),
        start=df.index[0], end=df.index[-1], volume_synthetic=synthetic,
    )
    return df, info


def _fetch_yfinance(ticker: str, period: str, interval: str, use_cache: bool) -> pd.DataFrame:
    key = hashlib.md5(f"{ticker}|{period}|{interval}".encode()).hexdigest()[:16]
    cache_file = os.path.join(CACHE_DIR, f"{key}.parquet")

    if use_cache and os.path.exists(cache_file):
        try:
            return pd.read_parquet(cache_file)
        except Exception:
            pass

    import yfinance as yf

    df = yf.download(ticker, period=period, interval=interval,
                     auto_adjust=False, progress=False)
    if df is None or df.empty:
        raise RuntimeError(
            f"yfinance returned no data for {ticker} period={period} "
            f"interval={interval}. Intraday history is capped at ~730 days; "
            f"try period='730d'."
        )

    if use_cache:
        os.makedirs(CACHE_DIR, exist_ok=True)
        try:
            df.to_parquet(cache_file)
        except Exception:
            pass
    return df


def _read_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    time_col = next(
        (c for c in df.columns if c.lower() in
         ("time", "date", "datetime", "timestamp", "date_time")),
        df.columns[0],
    )
    df[time_col] = parse_time_column(df[time_col])
    df = df.dropna(subset=[time_col]).set_index(time_col).sort_index()
    return df


def parse_time_column(col: pd.Series) -> pd.Series:
    """Parse a time column, handling TradingView's Unix-epoch exports.

    TradingView's "Export chart data" writes ``time`` as **integer seconds since
    the epoch**. Passing those to ``pd.to_datetime`` without a unit makes pandas
    read them as *nanoseconds*, silently placing every bar in January 1970 --
    the data looks loaded, the index looks fine, and nothing matches. Magnitude
    is used to pick the unit: seconds, milliseconds, microseconds or ISO text.
    """
    numeric = pd.to_numeric(col, errors="coerce")
    if numeric.notna().mean() > 0.9:
        scale = float(numeric.abs().median())
        if scale > 1e17:
            unit = "ns"
        elif scale > 1e14:
            unit = "us"
        elif scale > 1e11:
            unit = "ms"
        elif scale > 1e8:
            unit = "s"
        else:
            unit = None
        if unit is not None:
            return pd.to_datetime(numeric, unit=unit, utc=True, errors="coerce")
    return pd.to_datetime(col, utc=True, errors="coerce", format="mixed")


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # yfinance returns a MultiIndex column frame for single tickers in v0.2.5x+
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    aliases = {"adj_close": "adjclose", "vol": "volume", "o": "open",
               "h": "high", "l": "low", "c": "close", "v": "volume"}
    df = df.rename(columns=aliases)

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"missing required column(s) {missing}; got {list(df.columns)}")

    df = df[REQUIRED].astype(float)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df = df.dropna(subset=["open", "high", "low", "close"])

    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")

    return df


# --------------------------------------------------------------------------
# higher-timeframe access (request.security replication)
# --------------------------------------------------------------------------

def resample_ohlcv(df: pd.DataFrame, rule: str, origin: str = "start_day") -> pd.DataFrame:
    """Aggregate bars up to a higher timeframe.

    ``origin`` controls where the higher-timeframe grid is anchored. TradingView
    anchors 4H bars for 24-hour instruments at midnight exchange time, which
    ``"start_day"`` reproduces for UTC-indexed data.
    """
    agg = {"open": "first", "high": "max", "low": "min",
           "close": "last", "volume": "sum"}
    out = df.resample(rule, origin=origin, label="left", closed="left").agg(agg)
    return out.dropna(subset=["open", "high", "low", "close"])


def security_lookahead_off(df: pd.DataFrame, rule: str,
                           fn, origin: str = "start_day") -> pd.Series:
    """Pine ``request.security(sym, tf, expr, barmerge.lookahead_off)``.

    ``fn`` receives the resampled higher-timeframe frame and returns a Series on
    that frame's index.

    The lookahead-off contract is the part that people get wrong: while a
    higher-timeframe bar is still forming, ``request.security`` returns the value
    from the *previous, already-closed* higher-timeframe bar. So the value is
    shifted one HTF bar forward before being broadcast down to the base
    timeframe. Skipping that shift leaks the 4H close into 1H bars that occurred
    before it happened, and inflates the backtest.
    """
    htf = resample_ohlcv(df, rule, origin=origin)
    values = pd.Series(fn(htf), index=htf.index).astype(float)

    # Only bars from a *closed* HTF bar are visible.
    visible = values.shift(1)

    # Map each base bar to the HTF bucket it falls in, then take that bucket's
    # (already shifted) value.
    bucket = df.index.floor(_rule_to_freq(rule))
    out = visible.reindex(bucket)
    out.index = df.index
    return out


def _rule_to_freq(rule: str) -> str:
    return rule
