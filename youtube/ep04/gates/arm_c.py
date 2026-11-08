#!/usr/bin/env python3
"""ARM C — US index first-hour -> last-hour momentum. From run1_armC.md.

Hourly bars, UTC-stamped by open (verified in verify_h1.py). All session
times are America/New_York local with DST, never a fixed UTC offset.

IMPLEMENTATION CHOICES, logged:
  1. "Skip early-close days (13:00 ET)" is handled by the absence of a
     15:00 ET bar -- no bar, no trade. No holiday calendar is needed.
  2. "Skip the day after an NYSE holiday" is implemented as: the previous
     15:00 ET bar must fall on the immediately preceding weekday
     (Friday->Monday allowed). Any wider gap is skipped.
  3. Entry is the OPEN of the 15:00 bar and the time exit is the CLOSE of
     that same bar, so every trade lasts one hour, as specified.
"""
from __future__ import annotations
import numpy as np, pandas as pd
import engine
from engine import Trade
from part_b import load_h1

MARKETS = ["spx500usd", "nas100usd"]
P = dict(atr_n=14, thresh_atr=0.20, stop_atr=0.30,
         open_hour=9, entry_hour=15)


def wilder_atr_daily(mkt, n):
    df = engine.load(mkt)
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / int(n), adjust=False).mean()


def run_market(mkt: str, p: dict = None) -> list[Trade]:
    p = {**P, **(p or {})}
    h = load_h1(mkt)
    ny = h.index.tz_convert("America/New_York")
    day = pd.DatetimeIndex(ny).normalize().tz_localize(None)
    hour = pd.DatetimeIndex(ny).hour
    o, c, hi, lo = (h[x].to_numpy() for x in ("open", "close", "high", "low"))

    eh, oh = int(p["entry_hour"]), int(p["open_hour"])
    ent_i = dict(zip(day[hour == eh], np.flatnonzero(hour == eh)))
    opn_i = dict(zip(day[hour == oh], np.flatnonzero(hour == oh)))

    atr = wilder_atr_daily(mkt, p["atr_n"])
    atr_by_day = pd.Series(atr.to_numpy(), index=atr.index.normalize())

    days = sorted(ent_i)
    trades: list[Trade] = []
    for n_, d in enumerate(days):
        if n_ == 0:
            continue
        prev = days[n_ - 1]
        gap = (d - prev).days
        if not (gap == 1 or (d.weekday() == 0 and gap == 3)):
            continue                                   # holiday gap -> skip
        if d not in opn_i:
            continue                                   # no 09:00 bar
        i_ent, i_prev, i_opn = ent_i[d], ent_i[prev], opn_i[d]
        # last COMPLETED daily bar before 15:00 ET today closed 17:00 ET
        # yesterday, so its label is the previous session
        a = atr_by_day.asof(pd.Timestamp(prev, tz="UTC"))
        if not np.isfinite(a) or a <= 0:
            continue
        move = c[i_opn] - c[i_prev]
        thr = p["thresh_atr"] * a
        d_ = 1 if move >= thr else (-1 if move <= -thr else 0)
        if d_ == 0:
            continue
        fill = o[i_ent]
        stop = fill - d_ * p["stop_atr"] * a
        if d_ > 0 and lo[i_ent] <= stop:
            px, why = stop, "stop"
        elif d_ < 0 and hi[i_ent] >= stop:
            px, why = stop, "stop"
        else:
            px, why = c[i_ent], "time"
        trades.append(Trade(mkt, d_, h.index[i_ent], h.index[i_ent],
                            float(fill), float(px), why))
    return trades


def run(p: dict = None) -> list[Trade]:
    out = []
    for m in MARKETS:
        out += run_market(m, p)
    return out


if __name__ == "__main__":
    ts = run(); nets = [t.net for t in ts]
    print(f"ARM C — {len(ts)} trades, {len({t.market for t in ts})} markets")
    print(f"  mean net {np.mean(nets):+.4%}  gross {np.mean([t.gross for t in ts]):+.4%}  "
          f"cost {np.mean([t.cost() for t in ts]):.4%}")
    print(f"  long {sum(1 for t in ts if t.direction>0)}  short {sum(1 for t in ts if t.direction<0)}"
          f"  stops {sum(1 for t in ts if t.reason=='stop')}")
    print(f"  distinct days {len({t.entry_date.date() for t in ts})}")
    for m in MARKETS:
        s = [t for t in ts if t.market == m]
        if s: print(f"    {m:<11} {len(s):>5} trades  net {np.mean([t.net for t in s]):+.4%}")
