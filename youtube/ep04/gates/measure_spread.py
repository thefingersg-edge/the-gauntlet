#!/usr/bin/env python3
"""Measure the round-trip spread per market from OANDA's own bid and ask
candle streams. Replaces the borrowed table in engine.py.

Spread is an observable, not an estimate. Using one arm's guess to judge
the others was the flaw this fixes (see ../COST_MODEL.md).

Method, fixed before looking at the numbers:
  * per hourly bar, spread = (ask_close - bid_close) / mid_close
  * MEDIAN over the sample, not mean -- the mean is dragged by the thin
    hours around the daily rollover and by holidays
  * liquid hours only: 07:00-21:00 UTC, which is London open to New York
    close. A strategy that trades at 03:00 would pay more; none of these
    six do, except ARM C, which trades 15:00 New York, inside this window
  * doubled for a round trip (one spread paid in, one paid out)
"""
import os, numpy as np, pandas as pd
SRC = os.path.expanduser("~/mnt/Claude/pineport")
MK = ["eurusd","gbpusd","usdjpy","usdcad","audusd","eurgbp","eurjpy",
      "xauusd","xagusd","xptusd","xcuusd","spx500usd","nas100usd","de30eur",
      "bcousd","natgasusd","usb10yusd","de10ybeur","cornusd","wheatusd","sugarusd"]
BORROWED = {  # the table copied from ARM B, for comparison
 "eurusd":2,"gbpusd":3,"usdjpy":2,"usdcad":3,"audusd":3,"eurgbp":3,"eurjpy":4,
 "xauusd":5,"xagusd":10,"xptusd":25,"xcuusd":15,"spx500usd":3,"nas100usd":4,
 "de30eur":4,"bcousd":8,"natgasusd":30,"usb10yusd":6,"de10ybeur":6,
 "cornusd":25,"wheatusd":25,"sugarusd":30}

def rd(mkt, side):
    df = pd.read_csv(f"{SRC}/{mkt}_oanda_h1_{side}.csv")
    df["time"] = pd.to_datetime(df["time"], format="ISO8601", utc=True)
    return df.set_index("time")["close"]

print(f"  {'market':<11} {'measured RT':>12} {'borrowed':>10} {'ratio':>7}  {'bars':>8}")
print("  " + "-"*56)
out = {}
for m in MK:
    try:
        b, a = rd(m, "bid"), rd(m, "ask")
    except FileNotFoundError:
        print(f"  {m:<11}  missing"); continue
    j = pd.concat([b.rename("b"), a.rename("a")], axis=1).dropna()
    j = j[(j.index.hour >= 7) & (j.index.hour < 21)]
    mid = (j.a + j.b) / 2.0
    sp = ((j.a - j.b) / mid).replace([np.inf, -np.inf], np.nan).dropna()
    sp = sp[sp > 0]
    rt = 2.0 * float(np.median(sp))
    out[m] = rt
    bp, old = rt*1e4, BORROWED[m]
    print(f"  {m:<11} {bp:>10.2f}bp {old:>8}bp {bp/old:>6.2f}x  {len(sp):>8,}")

print("\nSPREAD_RT = {")
for m in MK:
    if m in out: print(f'    "{m}": {out[m]:.5f},')
print("}")
