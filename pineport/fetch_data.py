#!/usr/bin/env python3
"""Fetch real gold price data and write it in the format the backtester expects.

READ THIS FIRST -- THE 6-YEAR HOURLY REQUEST CANNOT BE FILLED BY YAHOO
---------------------------------------------------------------------
Yahoo Finance serves intraday history on a sliding window:

    1m                     last 30 days (7 per request)
    2m / 5m / 15m / 30m    last 60 days
    1h / 60m               last 730 days  <-- the ceiling
    1d / 1wk / 1mo         full history (decades)

That is a limit on what Yahoo *has*, not on how much you may ask for at once,
so chunking the requests does not get around it. Asking for six years of hourly
bars returns two years of hourly bars, or an empty frame -- and an empty frame
that silently becomes "the strategy took no trades" is exactly the failure mode
worth avoiding. This script refuses to pretend: it clamps the request, tells you
what it did, and reports what you actually received.

Google Finance is not an option at all -- there is no public historical API, and
`GOOGLEFINANCE()` is a Google Sheets formula that does not serve intraday
history.

For genuine multi-year hourly gold, see `print_alternatives()` at the bottom, or
run `python fetch_data.py --alternatives`.

Usage
-----
    python fetch_data.py --ticker GC=F --interval 1h --years 2
    python fetch_data.py --ticker GC=F --interval 1d --years 6
    python fetch_data.py --ticker GC=F --interval 1h --years 2 --out gold_1h.csv
    python fetch_data.py --alternatives
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# what Yahoo will actually serve
# --------------------------------------------------------------------------

#: interval -> (max days of history available, max days per single request)
YAHOO_LIMITS: dict[str, tuple[int | None, int | None]] = {
    "1m":  (30, 7),
    "2m":  (60, 60),
    "5m":  (60, 60),
    "15m": (60, 60),
    "30m": (60, 60),
    "60m": (730, 180),
    "1h":  (730, 180),
    "90m": (60, 60),
    "1d":  (None, None),
    "1wk": (None, None),
    "1mo": (None, None),
}

TICKERS = {
    "GC=F": "COMEX gold futures, continuous front month. REAL VOLUME. "
            "syminfo.pointvalue = 100.",
    "XAUUSD=X": "Spot gold FX pair. WARNING: Yahoo reports ZERO VOLUME on every "
                "bar, which makes every ta.vwma() in this strategy NaN.",
    "GLD": "SPDR Gold Shares ETF. Real volume, but US equity hours only "
           "(6.5h/day), so hourly bars are not comparable to 24h XAUUSD.",
    "IAU": "iShares Gold Trust ETF. Same caveat as GLD.",
}


@dataclass
class FetchPlan:
    """What was asked for, versus what can be delivered."""
    ticker: str
    interval: str
    requested_days: int
    granted_days: int
    chunk_days: int | None

    @property
    def was_clamped(self) -> bool:
        return self.granted_days < self.requested_days

    def explain(self) -> str:
        lines = [f"ticker    {self.ticker}",
                 f"interval  {self.interval}",
                 f"requested {self.requested_days} days "
                 f"({self.requested_days/365.25:.1f} years)"]
        if self.was_clamped:
            lines.append(
                f"GRANTED   {self.granted_days} days "
                f"({self.granted_days/365.25:.1f} years)  <-- CLAMPED")
            lines.append("")
            lines.append(f"Yahoo only holds {self.granted_days} days of "
                         f"{self.interval} data. The extra history you asked")
            lines.append("for does not exist on this source at this interval. "
                         "Options:")
            lines.append("  - use --interval 1d for the full span, or")
            lines.append("  - run --alternatives for sources with deep intraday "
                         "history.")
        else:
            lines.append(f"granted   {self.granted_days} days "
                         f"({self.granted_days/365.25:.1f} years)")
        return "\n".join(lines)


def plan_fetch(ticker: str, interval: str, years: float) -> FetchPlan:
    """Work out what Yahoo can serve before making any network call."""
    if interval not in YAHOO_LIMITS:
        raise ValueError(f"interval {interval!r} not supported by Yahoo; "
                         f"choose from {sorted(YAHOO_LIMITS)}")
    max_days, chunk = YAHOO_LIMITS[interval]
    requested = int(round(years * 365.25))
    granted = requested if max_days is None else min(requested, max_days)
    return FetchPlan(ticker, interval, requested, granted, chunk)


# --------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------

def fetch(plan: FetchPlan, pause: float = 0.4) -> pd.DataFrame:
    """Download the data, in chunks when the interval requires it.

    Chunked requests are concatenated and de-duplicated on the timestamp index;
    overlapping chunk boundaries are normal and harmless.
    """
    try:
        import yfinance as yf
    except ImportError:
        raise SystemExit(
            "yfinance is not installed in this interpreter.\n"
            "  pip install yfinance\n"
            "If you are running from RStudio, install into the interpreter\n"
            "reticulate is bound to:  reticulate::py_install('yfinance', pip=TRUE)\n"
            "and check which one that is with pineport_env()."
        )

    end = pd.Timestamp.utcnow().normalize() + pd.Timedelta(days=1)
    start = end - pd.Timedelta(days=plan.granted_days)

    if plan.chunk_days is None:
        windows = [(start, end)]
    else:
        windows = []
        cursor = start
        step = pd.Timedelta(days=plan.chunk_days)
        while cursor < end:
            windows.append((cursor, min(cursor + step, end)))
            cursor += step

    print(f"\nfetching {len(windows)} request(s)...")
    frames = []
    for i, (a, b) in enumerate(windows, 1):
        try:
            part = yf.download(plan.ticker, start=a.date(), end=b.date(),
                               interval=plan.interval, auto_adjust=False,
                               progress=False, threads=False)
        except Exception as exc:                       # noqa: BLE001
            print(f"  [{i}/{len(windows)}] {a.date()} -> {b.date()}  FAILED: {exc}")
            continue
        n = 0 if part is None or part.empty else len(part)
        print(f"  [{i}/{len(windows)}] {a.date()} -> {b.date()}  {n} bars")
        if n:
            frames.append(part)
        if len(windows) > 1 and pause:
            import time
            time.sleep(pause)

    if not frames:
        raise SystemExit(
            f"\nNo data returned for {plan.ticker} at {plan.interval}.\n"
            "Common causes: the symbol is wrong, the interval is outside "
            "Yahoo's window,\nor Yahoo is rate-limiting. Try --interval 1d to "
            "confirm the symbol works."
        )

    df = pd.concat(frames)
    return normalise(df)


def normalise(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten yfinance's frame into time-indexed open/high/low/close/volume."""
    df = df.copy()

    # yfinance returns MultiIndex columns for single tickers in recent versions
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    df = df.rename(columns={"adj_close": "adjclose"})

    required = ["open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"missing column(s) {missing}; got {list(df.columns)}")

    df = df[required].astype(float)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df = df.dropna(subset=["open", "high", "low", "close"])

    df.index = pd.to_datetime(df.index, utc=True)
    df.index.name = "time"
    return df


# --------------------------------------------------------------------------
# validation -- pure functions, unit tested below
# --------------------------------------------------------------------------

def validate(df: pd.DataFrame, interval: str) -> dict:
    """Check the data before anyone backtests on it.

    Silent data problems produce confident-looking backtests, which is worse
    than an error. Everything here is a thing that has actually gone wrong on a
    Yahoo pull at some point.
    """
    report: dict[str, object] = {}
    report["bars"] = len(df)
    report["start"] = df.index[0]
    report["end"] = df.index[-1]
    report["span_days"] = (df.index[-1] - df.index[0]).days
    report["duplicate_timestamps"] = int(df.index.duplicated().sum())
    report["monotonic"] = bool(df.index.is_monotonic_increasing)
    report["nan_rows"] = int(df[["open", "high", "low", "close"]].isna().any(axis=1).sum())

    # OHLC integrity
    hi_ok = df["high"] >= df[["open", "close"]].max(axis=1) - 1e-9
    lo_ok = df["low"] <= df[["open", "close"]].min(axis=1) + 1e-9
    hl_ok = df["high"] >= df["low"] - 1e-9
    report["ohlc_violations"] = int((~(hi_ok & lo_ok & hl_ok)).sum())

    # Volume -- the one that silently breaks this particular strategy
    total_volume = float(np.nansum(df["volume"].to_numpy()))
    report["total_volume"] = total_volume
    report["zero_volume_bars"] = int((df["volume"].fillna(0) == 0).sum())
    report["volume_usable"] = total_volume > 0

    # Gaps
    if len(df) > 2:
        deltas = df.index.to_series().diff().dropna()
        expected = deltas.mode().iloc[0]
        report["modal_spacing"] = expected
        big = deltas[deltas > expected * 3]
        report["gaps_over_3x"] = int(len(big))
        report["largest_gap"] = big.max() if len(big) else pd.Timedelta(0)
        report["largest_gap_at"] = big.idxmax() if len(big) else None

    report["price_min"] = float(df["close"].min())
    report["price_max"] = float(df["close"].max())
    return report


def print_report(report: dict, ticker: str) -> bool:
    """Print the validation report. Returns False if the data is unusable."""
    print("\nValidation")
    print("-" * 68)
    print(f"  bars                 {report['bars']:,}")
    print(f"  range                {report['start']:%Y-%m-%d %H:%M} -> "
          f"{report['end']:%Y-%m-%d %H:%M}  ({report['span_days']} days)")
    print(f"  price range          {report['price_min']:,.2f} - {report['price_max']:,.2f}")
    if "modal_spacing" in report:
        print(f"  modal bar spacing    {report['modal_spacing']}")
        print(f"  gaps over 3x spacing {report['gaps_over_3x']}", end="")
        if report["gaps_over_3x"]:
            print(f"   largest {report['largest_gap']} at "
                  f"{report['largest_gap_at']:%Y-%m-%d}")
            print("                       (weekends and holidays are normal "
                  "for a 24/5 market)")
        else:
            print()

    ok = True
    for label, key, bad_when in [
        ("duplicate timestamps", "duplicate_timestamps", lambda v: v > 0),
        ("rows with NaN OHLC", "nan_rows", lambda v: v > 0),
        ("OHLC integrity violations", "ohlc_violations", lambda v: v > 0),
    ]:
        v = report[key]
        flag = "FAIL" if bad_when(v) else "ok"
        if bad_when(v):
            ok = False
        print(f"  {label:<24} {v}  [{flag}]")

    print(f"  total volume         {report['total_volume']:,.0f}", end="")
    if not report["volume_usable"]:
        ok = False
        print("  [FAIL]")
        print()
        print("  This feed reports NO VOLUME. Every band in the RSI Boll Squeeze")
        print("  strategy is a ta.vwma(), which divides by volume -- so every")
        print("  signal would evaluate to NaN and the backtest would report zero")
        print("  trades. That looks like a strategy result but is a data fault.")
        print(f"  Use GC=F instead of {ticker}, or a broker export.")
    else:
        print(f"   ({report['zero_volume_bars']:,} zero-volume bars)  [ok]")

    return ok


# --------------------------------------------------------------------------

def print_alternatives() -> None:
    print("""
Sources that DO hold multi-year hourly gold data
================================================

Yahoo stops at 730 days for hourly. If you need six years, use one of these.

FREE
  Dukascopy               XAUUSD tick data back to ~2003, downloadable as
                          hourly. The standard free source for deep FX/metals
                          history. Python: `dukascopy-python`, or their
                          Historical Data Feed export page.

  Your broker's MT4/MT5   If you have an account with XAUUSD, the terminal
                          holds years of M1/H1 bars. History Center -> export
                          to CSV. Matches what you would actually trade on,
                          which matters more than it sounds.

  TradingView             Scroll far left on the chart to force-load history,
                          then Export chart data. Tedious, and the export is
                          capped by what is loaded, but it is the same feed you
                          verified the port against.

PAID (if it becomes worth it)
  Polygon.io, Databento, EODHD, Tiingo -- all serve years of intraday metals.

WHAT I WOULD ACTUALLY DO
  Your TradingView trade history already covers 2006-2026, and the port is
  verified against it to the bar. The gap is price data, not trade data. A
  Dukascopy pull of XAUUSD hourly from 2003 would cover the whole trade history
  and cost nothing but an afternoon.

  Note the mismatch to expect: Dukascopy and OANDA are different venues, so
  bars will differ slightly and the trade list will not reproduce exactly.
  Keep the OANDA export as the verification reference and use the deep history
  for research. Those are different jobs and it is fine for them to use
  different data.
""")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ticker", default="GC=F",
                    help="GC=F (futures, real volume) | XAUUSD=X (spot, NO "
                         "volume) | GLD | IAU")
    ap.add_argument("--interval", default="1h", choices=sorted(YAHOO_LIMITS))
    ap.add_argument("--years", type=float, default=2.0)
    ap.add_argument("--out", default=None, help="output CSV path")
    ap.add_argument("--alternatives", action="store_true",
                    help="list sources with deep intraday history, then exit")
    ap.add_argument("--self-test", action="store_true",
                    help="exercise the validation logic offline, then exit")
    args = ap.parse_args()

    if args.alternatives:
        print_alternatives()
        return
    if args.self_test:
        sys.exit(self_test())

    print("Ticker notes")
    print("-" * 68)
    print(f"  {args.ticker}: {TICKERS.get(args.ticker, 'unrecognised symbol')}")

    plan = plan_fetch(args.ticker, args.interval, args.years)
    print("\nPlan")
    print("-" * 68)
    print("  " + plan.explain().replace("\n", "\n  "))

    df = fetch(plan)
    report = validate(df, args.interval)
    ok = print_report(report, args.ticker)

    out = args.out or f"gold_{args.ticker.replace('=', '')}_{args.interval}.csv"
    df.to_csv(out)
    print(f"\nwrote {len(df):,} bars to {out}")
    print("\nRun the backtest against it with:")
    print(f"  python run.py backtest --csv {out} --point-value "
          f"{100 if args.ticker == 'GC=F' else 1}")

    if plan.was_clamped:
        print(f"\nREMINDER: you asked for {plan.requested_days/365.25:.1f} years "
              f"and Yahoo served {report['span_days']/365.25:.1f}.")
        print("Run --alternatives for sources that hold the full span.")
    if not ok:
        sys.exit(1)


# --------------------------------------------------------------------------
# offline self-test
# --------------------------------------------------------------------------

def self_test() -> int:
    """Exercise everything that does not need the network."""
    failures = []

    def check(name, cond, detail=""):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
        if not cond:
            failures.append(name)

    print("planning")
    p = plan_fetch("GC=F", "1h", 6)
    check("6 years of hourly is clamped to 730 days", p.granted_days == 730,
          f"got {p.granted_days}")
    check("clamping is reported", p.was_clamped)
    check("hourly requests are chunked", p.chunk_days == 180)

    p2 = plan_fetch("GC=F", "1d", 6)
    check("6 years of daily is NOT clamped", not p2.was_clamped)
    check("daily needs no chunking", p2.chunk_days is None)
    check("1m is clamped to 30 days", plan_fetch("GC=F", "1m", 6).granted_days == 30)
    try:
        plan_fetch("GC=F", "4h", 1)
        check("unsupported interval rejected", False, "no error raised")
    except ValueError:
        check("unsupported interval rejected", True)

    print("\nvalidation")
    idx = pd.date_range("2024-01-01", periods=500, freq="1h", tz="UTC")
    rng = np.random.default_rng(0)
    close = 2000 + np.cumsum(rng.standard_normal(500))
    good = pd.DataFrame({
        "open": close, "high": close + 2, "low": close - 2,
        "close": close, "volume": rng.integers(100, 999, 500).astype(float),
    }, index=idx)
    r = validate(good, "1h")
    check("clean data passes OHLC check", r["ohlc_violations"] == 0)
    check("clean data has usable volume", r["volume_usable"])
    check("no false-positive gaps", r["gaps_over_3x"] == 0)

    zero = good.copy(); zero["volume"] = 0.0
    check("zero volume detected", not validate(zero, "1h")["volume_usable"])

    broken = good.copy()
    broken.iloc[10, broken.columns.get_loc("high")] = broken["low"].iloc[10] - 5
    check("OHLC violation detected", validate(broken, "1h")["ohlc_violations"] > 0)

    gapped = pd.concat([good.iloc[:100], good.iloc[300:]])
    check("gap detected", validate(gapped, "1h")["gaps_over_3x"] == 1,
          f"got {validate(gapped, '1h')['gaps_over_3x']}")

    print("\nnormalise")
    mi = good.copy()
    mi.columns = pd.MultiIndex.from_product([["Open", "High", "Low", "Close", "Volume"],
                                             ["GC=F"]])
    flat = normalise(mi)
    check("MultiIndex columns flattened", list(flat.columns) ==
          ["open", "high", "low", "close", "volume"], f"got {list(flat.columns)}")
    check("index is UTC", str(flat.index.tz) == "UTC")

    dupes = pd.concat([good.iloc[:50], good.iloc[:50]])
    check("duplicate timestamps dropped", len(normalise(dupes)) == 50)

    print("\n" + "=" * 60)
    if failures:
        print(f"{len(failures)} FAILED: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    main()
