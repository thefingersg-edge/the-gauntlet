#!/usr/bin/env python3
"""ARM E — "Twin Sleeve": trend on all 21 + RSI2 index mean reversion.
From run1_armE.md, verbatim."""
from __future__ import annotations
import numpy as np, pandas as pd
import engine
from engine import Trade
from arm_f import rsi_wilder

B_MARKETS = ["spx500usd", "nas100usd", "de30eur"]
P = dict(ema_fast=20, ema_slow=100, warmup=253,
         b_sma=200, b_rsi_n=2, b_rsi=10, b_exit_sma=5,
         b_atr_n=10, b_stop_atr=2.5, b_time=10)


def atr_simple(df, n):
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(int(n)).mean()


def sleeve_a(mkt, p):
    """Always in the market, long or short; reverses when the EMA pair flips."""
    df = engine.load(mkt)
    if len(df) < p["warmup"] + 10: return []
    c, o = df["close"], df["open"]
    ef = c.ewm(span=int(p["ema_fast"]), adjust=False).mean()
    es = c.ewm(span=int(p["ema_slow"]), adjust=False).mean()
    d = np.where(ef > es, 1, -1)
    idx = df.index; n = len(df); ov = o.to_numpy(); cv = c.to_numpy()
    out = []
    i = int(p["warmup"])
    cur, start = int(d[i]), i + 1
    while i < n - 1:
        if int(d[i]) != cur:
            k = i + 1
            if start < k:
                out.append(Trade(mkt, cur, idx[start], idx[k], float(ov[start]),
                                 float(ov[k]), "reverse"))
            cur, start = int(d[i]), k
        i += 1
    if start < n - 1:
        out.append(Trade(mkt, cur, idx[start], idx[n - 1], float(ov[start]),
                         float(cv[n - 1]), "end"))
    return out


def sleeve_b(mkt, p):
    df = engine.load(mkt)
    c, o, h, l = df["close"], df["open"], df["high"], df["low"]
    sma = c.rolling(int(p["b_sma"])).mean()
    sma_x = c.rolling(int(p["b_exit_sma"])).mean()
    rsi = rsi_wilder(c, int(p["b_rsi_n"]))
    atr = atr_simple(df, p["b_atr_n"])
    idx = df.index; n = len(df)
    cv, ov, lv = c.to_numpy(), o.to_numpy(), l.to_numpy()
    smav, sxv, rv, AT = sma.to_numpy(), sma_x.to_numpy(), rsi.to_numpy(), atr.to_numpy()
    out, i = [], int(p["b_sma"])
    while i < n - 1:
        if not (np.isfinite(smav[i]) and np.isfinite(AT[i])): i += 1; continue
        if not (cv[i] > smav[i] and rv[i] < p["b_rsi"]): i += 1; continue
        k = i + 1; fill = ov[k]; stop = fill - p["b_stop_atr"] * AT[i]
        exit_i = exit_px = None; reason = ""
        j, bar = k, 1
        while j < n:
            if lv[j] <= stop:
                exit_i, exit_px, reason = j, min(ov[j], stop), "stop"; break
            if np.isfinite(sxv[j]) and cv[j] > sxv[j] and j + 1 < n:
                exit_i, exit_px, reason = j + 1, ov[j + 1], "profit"; break
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
    for m in engine.MARKETS: out += sleeve_a(m, p)
    for m in B_MARKETS: out += sleeve_b(m, p)
    return out


if __name__ == "__main__":
    ts = run(); nets = [t.net for t in ts]
    print(f"ARM E — {len(ts)} trades, {len({t.market for t in ts})} markets")
    print(f"  mean net {np.mean(nets):+.3%}  gross {np.mean([t.gross for t in ts]):+.3%}  "
          f"cost {np.mean([t.cost() for t in ts]):.3%}  median hold {np.median([t.nights for t in ts]):.0f}n")
