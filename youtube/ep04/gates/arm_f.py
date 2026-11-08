#!/usr/bin/env python3
"""ARM F, Part A — dip-buy. Implemented from run1_armF.md section A, verbatim.

Part B (the overnight sleeve) needs hourly bars and is a separate module.

Implementation choices where the specification left a gap are listed at the
foot of this file. None is resolved silently.
"""
from __future__ import annotations
import numpy as np, pandas as pd
import engine
from engine import Trade

ARM_F_MARKETS = ["spx500usd", "nas100usd", "de30eur"]

P = dict(sma_trend=200, rsi_n=2, rsi_entry=20, rsi_exit=70,
         limit_atr=0.25, atr_n=20, stop_atr=3.0, time_limit=10)


def rsi_wilder(close: pd.Series, n: int) -> pd.Series:
    d = close.diff()
    g = d.clip(lower=0.0)
    l = (-d).clip(lower=0.0)
    a = 1.0 / n
    ag = g.ewm(alpha=a, adjust=False).mean()
    al = l.ewm(alpha=a, adjust=False).mean()
    rs = ag / al.replace(0.0, np.nan)
    out = 100.0 - 100.0 / (1.0 + rs)
    return out.fillna(100.0)


def atr_simple(df: pd.DataFrame, n: int) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def run_market(mkt: str, p: dict = None) -> list[Trade]:
    p = {**P, **(p or {})}
    df = engine.load(mkt)
    c, o, h, lo = df["close"], df["open"], df["high"], df["low"]
    sma = c.rolling(p["sma_trend"]).mean()
    rsi = rsi_wilder(c, p["rsi_n"])
    atr = atr_simple(df, p["atr_n"])
    idx = df.index
    n = len(df)
    cv, ov, hv, lv = c.to_numpy(), o.to_numpy(), h.to_numpy(), lo.to_numpy()
    smav, rsiv, atrv = sma.to_numpy(), rsi.to_numpy(), atr.to_numpy()

    trades: list[Trade] = []
    i = p["sma_trend"]            # warm-up: no signals before 200 bars exist
    while i < n - 1:
        if not (np.isfinite(smav[i]) and np.isfinite(atrv[i])):
            i += 1; continue
        if not (cv[i] > smav[i] and rsiv[i] < p["rsi_entry"]):
            i += 1; continue

        limit = cv[i] - p["limit_atr"] * atrv[i]
        k = i + 1                                   # order valid for bar t+1 only
        if k >= n or not lv[k] <= limit:
            i += 1; continue
        fill = min(ov[k], limit)                    # gap-through fills at the open
        stop = fill - p["stop_atr"] * atrv[i]

        exit_i, exit_px, reason = None, None, ""
        j = k
        bar_in_trade = 1
        while j < n:
            if lv[j] <= stop:                       # (a) stop, intrabar
                exit_i, exit_px, reason = j, (min(ov[j], stop) if ov[j] <= stop else stop), "stop"
                break
            if rsiv[j] > p["rsi_exit"] and j + 1 < n:   # (b) RSI exit at next open
                exit_i, exit_px, reason = j + 1, ov[j + 1], "rsi"
                break
            if bar_in_trade >= p["time_limit"] and j + 1 < n:  # (c) time exit
                exit_i, exit_px, reason = j + 1, ov[j + 1], "time"
                break
            j += 1; bar_in_trade += 1
        if exit_i is None:
            break

        trades.append(Trade(mkt, +1, idx[k], idx[exit_i], float(fill),
                            float(exit_px), reason))
        i = exit_i                                  # new signal may fire on the exit bar's close
    return trades


def run(p: dict = None) -> list[Trade]:
    out = []
    for m in ARM_F_MARKETS:
        out += run_market(m, p)
    return out


if __name__ == "__main__":
    ts = run()
    print(f"ARM F part A — {len(ts)} trades")
    for m in ARM_F_MARKETS:
        s = [t for t in ts if t.market == m]
        print(f"  {m:<12} {len(s):>4} trades")
    pre = [t for t in ts if t.entry_date < pd.Timestamp('2018-01-01', tz='UTC')]
    post = [t for t in ts if t.entry_date >= pd.Timestamp('2018-01-01', tz='UTC')]
    print(f"\n  its split:  2005-2017 {len(pre)}   2018+ {len(post)}")
    print(f"  it reported: 2005-2017 416   2018+ 281   total 697   (spx 237)")
