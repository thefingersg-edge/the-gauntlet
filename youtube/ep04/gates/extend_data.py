#!/usr/bin/env python3
"""Extend the daily files with TradingView's OANDA feed, after proving every
overlapping bar reproduces exactly.

Mapping, derived not assumed: a TradingView daily bar stamped 21:00 UTC
(22:00 under EST) is the session ending 17:00 New York, which our files
label 00:00 UTC on the NEXT day. Converted via the zone, so DST is handled.

The final bar of BOTH sources is dropped: our own last bar was captured
mid-session (spx500usd 2026-08-07 shows high 7760.8 / volume 117,576 against
the completed 7766.7 / 145,922), and TradingView's last bar is still forming.
"""
import json, numpy as np, pandas as pd, os, engine

TV = json.load(open("tv_data.json"))
OUT = os.path.expanduser("~/mnt/Claude/pineport/adaptive/data")

def tv_frame(mkt):
    v = TV[mkt]
    t = pd.to_datetime(v["t"], unit="s", utc=True)
    ny = t.tz_convert("America/New_York")
    lbl = (ny + pd.Timedelta(hours=7)).normalize().tz_localize(None).tz_localize("UTC")
    df = pd.DataFrame({"open": v["o"], "high": v["h"], "low": v["l"],
                       "close": v["c"], "volume": v["v"]}, index=lbl)
    return df.sort_index()

print("OVERLAP CHECK — every complete shared bar must reproduce exactly\n")
ok_all = True
for mkt in TV:
    ours = engine.load(mkt)
    theirs = tv_frame(mkt)
    both = ours.index.intersection(theirs.index)
    both = both[:-1]                      # our last bar is incomplete
    if len(both) == 0:
        print(f"  {mkt}: NO OVERLAP"); ok_all = False; continue
    bad = 0
    for col in ("open", "high", "low", "close"):
        rel = (ours.loc[both, col] - theirs.loc[both, col]).abs() / ours.loc[both, col]
        bad += int((rel > 1e-6).sum())
    print(f"  {mkt:<11} {len(both):>3} shared complete bars   "
          f"{'EXACT MATCH' if bad == 0 else f'{bad} MISMATCHES'}")
    ok_all &= (bad == 0)

if not ok_all:
    raise SystemExit("\nOverlap does not reproduce. Not splicing.")

print("\nEXTENDING")
for mkt in TV:
    ours = engine.load(mkt)
    theirs = tv_frame(mkt).iloc[:-1]      # their last bar is still forming
    new = theirs[theirs.index > ours.index[-2]]   # drop our incomplete last bar
    merged = pd.concat([ours.iloc[:-1], new])
    merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    path = f"{OUT}/{mkt}_d1.csv"
    merged.to_csv(path, index_label="time")
    print(f"  {mkt:<11} {len(ours)} -> {len(merged)} bars   "
          f"now ends {merged.index[-1].date()}  (+{len(merged)-len(ours)+1} new)")
