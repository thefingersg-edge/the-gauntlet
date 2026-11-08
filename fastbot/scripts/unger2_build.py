#!/usr/bin/env python3
"""unger2_build.py -- UNGER2 data preparation (mechanical, no results). Runs on the Mac / VM next to the data.
  python3 unger2_build.py futures CL|GC  -> data/unger2/{CL,GC}_15m.npz  from data/unger2/futures/*_YYYY.csv (Databento 1m, CL.v.0 / GC.v.0)
  python3 unger2_build.py dax            -> data/unger2/de30_5m.npz      from data/v38/de30eur_{bid,ask}_5m.csv (OANDA)
15m futures bars: UTC 15-minute buckets; o = first open, h = max, l = min, c = last close, iid = instrument of the last minute,
roll = 1 if the instrument changes inside the bucket or differs from the previous bucket. Trades in the 1m files only (no quotes).
DAX: mid OHLC from bid/ask, spr_bp = (ask_open / bid_open - 1) x 1e4 at each bar's open (as struct15).
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, glob
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "..", "data")


def futures(root):
    parts = []
    for p in sorted(glob.glob(os.path.join(D, "unger2", "futures", f"{root}_*.csv"))):
        x = pd.read_csv(p, usecols=["ts_event", "instrument_id", "open", "high", "low", "close"])
        x["t"] = pd.to_datetime(x["ts_event"].str[:19]); x["b"] = x["t"].dt.floor("15min")
        g = x.groupby("b", sort=True)
        a = pd.DataFrame(dict(o=g["open"].first(), h=g["high"].max(), l=g["low"].min(), c=g["close"].last(),
                              iid=g["instrument_id"].last(), nid=g["instrument_id"].nunique()))
        parts.append(a); print(os.path.basename(p), len(a), flush=True)
    A = pd.concat(parts); A = A[~A.index.duplicated(keep="first")].sort_index()
    roll = ((A["nid"] > 1) | (A["iid"] != A["iid"].shift(1))).to_numpy().copy(); roll[0] = False
    out = os.path.join(D, "unger2", f"{root}_15m.npz")
    np.savez(out, t=A.index.to_numpy().astype("datetime64[m]"), o=A["o"].to_numpy(float), h=A["h"].to_numpy(float),
             l=A["l"].to_numpy(float), c=A["c"].to_numpy(float), iid=A["iid"].to_numpy(np.int64), roll=roll)
    print(out, len(A), "bars,", int(roll.sum()), "roll buckets")


def dax():
    b = pd.read_csv(os.path.join(D, "v38", "de30eur_bid_5m.csv")); a = pd.read_csv(os.path.join(D, "v38", "de30eur_ask_5m.csv"))
    m = b.merge(a, on="time", suffixes=("_b", "_a"))
    t = pd.to_datetime(m["time"]).to_numpy().astype("datetime64[m]")
    mid = {k: ((m[f"{k}_b"] + m[f"{k}_a"]) / 2).to_numpy(float) for k in ("open", "high", "low", "close")}
    spr = ((m["open_a"] / m["open_b"] - 1) * 1e4).to_numpy(float)
    out = os.path.join(D, "unger2", "de30_5m.npz")
    np.savez(out, t=t, o=mid["open"], h=mid["high"], l=mid["low"], c=mid["close"], spr=spr); print(out, len(t), "bars")


if __name__ == "__main__":
    os.makedirs(os.path.join(D, "unger2"), exist_ok=True)
    if sys.argv[1] == "futures": futures(sys.argv[2])
    elif sys.argv[1] == "dax": dax()
