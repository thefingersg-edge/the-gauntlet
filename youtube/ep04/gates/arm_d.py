#!/usr/bin/env python3
"""ARM D — v3: multi-horizon trend (sleeve A, 18 markets) + index mean
reversion (sleeve B, 3 indices). From run1_armD.md turn 10, verbatim."""
from __future__ import annotations
import numpy as np, pandas as pd
import engine
from engine import Trade

A_MARKETS = ["eurusd", "gbpusd", "usdjpy", "usdcad", "audusd",
             "xauusd", "xagusd", "xptusd", "xcuusd",
             "spx500usd", "de30eur", "bcousd", "natgasusd",
             "usb10yusd", "de10ybeur", "cornusd", "wheatusd", "sugarusd"]
B_MARKETS = ["spx500usd", "nas100usd", "de30eur"]

P = dict(h1=63, h2=126, h3=252, atr_n=20, stop_atr=5.0, cooldown=10,
         warmup=253, b_sma=200, b_ibs=0.20, b_stop_atr=4.0, b_time=5)


def atr_simple(df, n):
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def sleeve_a(mkt, p):
    df = engine.load(mkt)
    if len(df) < p["warmup"] + 10: return []
    c, o, h, l = df["close"], df["open"], df["high"], df["low"]
    S = (np.sign(c - c.shift(int(p["h1"]))) + np.sign(c - c.shift(int(p["h2"])))
         + np.sign(c - c.shift(int(p["h3"]))))
    atr = atr_simple(df, int(p["atr_n"]))
    idx = df.index; n = len(df)
    cv, ov, hv, lv = (x.to_numpy() for x in (c, o, h, l))
    Sv, AT = S.to_numpy(), atr.to_numpy()
    out, i, block_until = [], int(p["warmup"]), -1
    while i < n - 1:
        if i < block_until or not np.isfinite(Sv[i]) or not np.isfinite(AT[i]):
            i += 1; continue
        d = 1 if Sv[i] >= 2 else (-1 if Sv[i] <= -2 else 0)
        if d == 0: i += 1; continue
        k = i + 1; fill = ov[k]
        stop = fill - d * p["stop_atr"] * AT[i]
        best = cv[i]
        exit_i = exit_px = None; reason = ""
        j = k
        while j < n:
            best = max(best, cv[j]) if d > 0 else min(best, cv[j])
            if np.isfinite(AT[j]):
                cand = best - d * p["stop_atr"] * AT[j]
                stop = max(stop, cand) if d > 0 else min(stop, cand)
            hit = (lv[j] <= stop) if d > 0 else (hv[j] >= stop)
            if hit:                                   # stop takes precedence
                exit_px = min(ov[j], stop) if d > 0 else max(ov[j], stop)
                exit_i, reason = j, "stop"; break
            sig_exit = (Sv[j] <= 0) if d > 0 else (Sv[j] >= 0)
            if sig_exit and j + 1 < n:
                exit_i, exit_px, reason = j + 1, ov[j + 1], "signal"; break
            j += 1
        if exit_i is None: exit_i, exit_px, reason = n - 1, cv[n - 1], "end"
        out.append(Trade(mkt, d, idx[k], idx[exit_i], float(fill), float(exit_px), reason))
        i = exit_i
        if reason == "stop": block_until = exit_i + int(p["cooldown"])
    return out


def sleeve_b(mkt, p):
    df = engine.load(mkt)
    c, o, h, l = df["close"], df["open"], df["high"], df["low"]
    sma = c.rolling(int(p["b_sma"])).mean()
    atr = atr_simple(df, int(p["atr_n"]))
    rng = (h - l).replace(0, np.nan)
    ibs = ((c - l) / rng).fillna(0.5)
    idx = df.index; n = len(df)
    cv, ov, hv, lv = (x.to_numpy() for x in (c, o, h, l))
    smav, AT, IB = sma.to_numpy(), atr.to_numpy(), ibs.to_numpy()
    out, i = [], int(p["b_sma"])
    while i < n - 1:
        if not (np.isfinite(smav[i]) and np.isfinite(AT[i])): i += 1; continue
        if not (cv[i] > smav[i] and IB[i] < p["b_ibs"]): i += 1; continue
        k = i + 1; fill = ov[k]; stop = fill - p["b_stop_atr"] * AT[i]
        exit_i = exit_px = None; reason = ""
        j, bar = k, 1
        while j < n:
            if lv[j] <= stop:
                exit_i, exit_px, reason = j, (min(ov[j], stop)), "stop"; break
            if j > k and cv[j] > hv[j - 1] and j + 1 < n:
                exit_i, exit_px, reason = j + 1, ov[j + 1], "bounce"; break
            if bar >= int(p["b_time"]) and j + 1 < n:
                exit_i, exit_px, reason = j + 1, ov[j + 1], "time"; break
            j += 1; bar += 1
        if exit_i is None: exit_i, exit_px, reason = n - 1, cv[n - 1], "end"
        out.append(Trade(mkt, 1, idx[k], idx[exit_i], float(fill), float(exit_px), reason))
        i = exit_i
    return out


def run(p: dict = None) -> list[Trade]:
    p = {**P, **(p or {})}
    out = []
    for m in A_MARKETS: out += sleeve_a(m, p)
    for m in B_MARKETS: out += sleeve_b(m, p)
    return out


if __name__ == "__main__":
    ts = run(); nets = [t.net for t in ts]
    a = [t for t in ts if t.reason in ("stop", "signal", "end") and t.direction in (1, -1)]
    print(f"ARM D — {len(ts)} trades, {len({t.market for t in ts})} markets")
    print(f"  mean net {np.mean(nets):+.3%}  gross {np.mean([t.gross for t in ts]):+.3%}  "
          f"cost {np.mean([t.cost() for t in ts]):.3%}  median hold {np.median([t.nights for t in ts]):.0f}n")
