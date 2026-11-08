"""
make_h4.py — build 4-hour bars from the OANDA H1 feed.

WHY THIS FILE EXISTS
--------------------
`../resampled_h4/` was built with a naive pandas resample on UTC, which lands
the bars on 00/04/08/12/16/20 UTC. OANDA's own H4 candles are anchored to the
17:00 New York trading-day boundary and therefore MOVE WITH US DST:

    EDT (UTC-4)  boundaries at UTC hours  1, 5,  9, 13, 17, 21
    EST (UTC-5)  boundaries at UTC hours  2, 6, 10, 14, 18, 22

The naive grid shares ZERO timestamps with OANDA's native H4 files. This is the
same error class as R4 on the daily bars, one timeframe down.

VALIDATION (against the 11 native ../*_oanda_h4.csv files, which are ground truth)
    xauusd: 31,665 shared timestamps, 22 OHLC mismatches (0.069%)
            ALL 22 are incomplete blocks (1-3 H1 bars present, i.e. H1 feed gaps)
            complete 4-bar blocks that mismatch: 0
    eurusd / spx500usd: same pattern, >=99.9% timestamp overlap
MIN_BARS = 4 therefore drops every known mismatch: a 4h bar is emitted only
when all four of its H1 bars are present.
"""
import os, sys, glob
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.dirname(HERE)              # pineport/, where *_oanda_h1.csv live
OUT  = os.path.join(HERE, "data_h4")
NY   = "America/New_York"
MIN_BARS = 4                              # complete blocks only


def bar_start(t: pd.Series) -> pd.Series:
    """Start of the 17:00-New-York-anchored 4h block containing each timestamp.

    Uses the actual UTC offset at each instant rather than tz arithmetic on the
    grid, so the DST transitions need no special casing.
    """
    off    = t.dt.tz_convert(NY).map(lambda x: x.utcoffset().total_seconds() / 3600.0)
    anchor = np.where(off == -4.0, 1, 2)           # UTC hour of a block boundary
    back   = (t.dt.hour.to_numpy() - anchor) % 4   # hours since that boundary
    return t - pd.to_timedelta(back, unit="h")


def build(mkt: str) -> str:
    p = os.path.join(SRC, f"{mkt}_oanda_h1.csv")
    if not os.path.exists(p):
        return f"{mkt}: MISSING"
    df = pd.read_csv(p, usecols=["time", "open", "high", "low", "close", "volume"])
    df["time"] = pd.to_datetime(df["time"], utc=True)   # naive files ARE UTC
    df = df.sort_values("time").drop_duplicates("time")
    df["bs"] = bar_start(df["time"])

    g = df.groupby("bs").agg(open=("open", "first"), high=("high", "max"),
                             low=("low", "min"),    close=("close", "last"),
                             volume=("volume", "sum"), nbar=("close", "size"))
    n_all = len(g)
    g = g[(g["nbar"] >= MIN_BARS) & (g["high"] > g["low"])].drop(columns="nbar")
    g.index.name = "time"

    os.makedirs(OUT, exist_ok=True)
    g.to_csv(os.path.join(OUT, f"{mkt}_h4.csv"))
    yrs = (g.index[-1] - g.index[0]).days / 365.25
    return (f"{mkt}: {len(g)} bars ({n_all - len(g)} incomplete dropped) "
            f"{g.index[0].date()} -> {g.index[-1].date()} ({len(g)/yrs:.1f} bars/yr)")


def all_available() -> list[str]:
    return sorted(os.path.basename(p).replace("_oanda_h1.csv", "")
                  for p in glob.glob(os.path.join(SRC, "*_oanda_h1.csv")))


if __name__ == "__main__":
    todo = all_available() if sys.argv[1:] == ["--all"] else sys.argv[1:]
    for m in todo:
        print(build(m), flush=True)
