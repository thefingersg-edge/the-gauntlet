"""Verify the hourly timestamp convention against the daily bars.

If hourly stamps are UTC by bar OPEN, the daily bar labelled D should be the
aggregate of hourly bars from 17:00 New York on D-1 to 17:00 New York on D.
DST moves that between 21:00 and 22:00 UTC, so the test must use the zone,
not a fixed offset. This is gate C8 (session integrity) applied to our own
data before any strategy uses it.
"""
import pandas as pd, numpy as np, os
H = os.path.expanduser("~/mnt/Claude/pineport")
D = os.path.expanduser("~/mnt/Claude/pineport/adaptive/data")

def load_h1(mkt):
    df = pd.read_csv(f"{H}/{mkt}_oanda_h1.csv", parse_dates=["time"])
    t = df["time"]
    if t.dt.tz is None:
        t = t.dt.tz_localize("UTC")          # hypothesis under test
    df["time"] = t
    return df.set_index("time").sort_index()

for mkt in ("nas100usd", "de30eur"):
    h = load_h1(mkt)
    d = pd.read_csv(f"{D}/{mkt}_d1.csv", parse_dates=["time"]).set_index("time").sort_index()
    # label each hourly bar with the NY-session day it belongs to
    ny = h.index.tz_convert("America/New_York")
    sess = (ny + pd.Timedelta(hours=7)).normalize()   # 17:00 -> next day 00:00
    g = h.groupby(sess.tz_localize(None))
    agg = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(),
                        "low": g["low"].min(), "close": g["close"].last()})
    agg.index = agg.index.tz_localize("UTC")
    j = d.join(agg, how="inner", rsuffix="_h")
    j = j.dropna()
    if j.empty:
        print(f"{mkt}: NO OVERLAP"); continue
    for col in ("open", "high", "low", "close"):
        rel = (j[col] - j[f"{col}_h"]).abs() / j[col]
        print(f"{mkt:<11} {col:<6} bars {len(j):>5}  "
              f"match<0.1% {100*(rel<0.001).mean():5.1f}%   median err {rel.median():.2e}")
    print()
