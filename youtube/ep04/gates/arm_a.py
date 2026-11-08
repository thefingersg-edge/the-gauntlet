#!/usr/bin/env python3
"""ARM A — Donchian 55/20 breakout with EMA50/200 trend filter, all 21 markets.

From run1_armA.md, verbatim.

IMPLEMENTATION CHOICES where the spec was ambiguous (logged, not resolved
quietly):
  1. "At the close of every bar after the entry bar, including the entry
     bar's own close" contradicts itself. Implemented as INCLUDING the
     entry bar's close.
  2. The initial stop is from the SIGNAL bar's close (as written), not the
     fill price.
  3. A position open at the end of the data is closed at the last close and
     counted, so no trade is silently dropped.
"""
from __future__ import annotations
import numpy as np, pandas as pd
import engine
from engine import Trade

P = dict(entry_ch=55, trail_ch=20, ema_fast=50, ema_slow=200,
         atr_n=20, stop_atr=3.0, warmup=200)


def wilder_atr(df: pd.DataFrame, n: int) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False).mean()


def run_market(mkt: str, p: dict = None) -> list[Trade]:
    p = {**P, **(p or {})}
    df = engine.load(mkt)
    if len(df) < p["warmup"] + 10:
        return []
    c, o, h, l = df["close"], df["open"], df["high"], df["low"]
    hh_e = h.rolling(p["entry_ch"]).max().shift(1)
    ll_e = l.rolling(p["entry_ch"]).min().shift(1)
    hh_t = h.rolling(p["trail_ch"]).max().shift(1)
    ll_t = l.rolling(p["trail_ch"]).min().shift(1)
    ef = c.ewm(span=p["ema_fast"], adjust=False).mean()
    es = c.ewm(span=p["ema_slow"], adjust=False).mean()
    atr = wilder_atr(df, p["atr_n"])

    idx = df.index; n = len(df)
    cv, ov, hv, lv = (x.to_numpy() for x in (c, o, h, l))
    HE, LE, HT, LT = (x.to_numpy() for x in (hh_e, ll_e, hh_t, ll_t))
    EF, ES, AT = ef.to_numpy(), es.to_numpy(), atr.to_numpy()

    trades: list[Trade] = []
    i = p["warmup"]
    while i < n - 1:
        if not np.isfinite(HE[i]) or not np.isfinite(AT[i]):
            i += 1; continue
        long = cv[i] > HE[i] and EF[i] > ES[i]
        short = cv[i] < LE[i] and EF[i] < ES[i]
        if not (long or short):
            i += 1; continue
        d = 1 if long else -1
        k = i + 1
        fill = ov[k]
        stop = cv[i] - d * p["stop_atr"] * AT[i]

        exit_i = exit_px = None
        j = k
        while j < n:
            # trailing update uses the signal-style channel, at each close
            if np.isfinite(LT[j]) and np.isfinite(HT[j]):
                stop = max(stop, LT[j]) if d > 0 else min(stop, HT[j])
            hit = (lv[j] <= stop) if d > 0 else (hv[j] >= stop)
            if hit:
                if d > 0:
                    exit_px = min(ov[j], stop)
                else:
                    exit_px = max(ov[j], stop)
                exit_i = j
                break
            j += 1
        if exit_i is None:                     # open at end of data
            exit_i, exit_px = n - 1, cv[n - 1]
        trades.append(Trade(mkt, d, idx[k], idx[exit_i], float(fill),
                            float(exit_px), "stop"))
        i = exit_i + 1
    return trades


def run(p: dict = None) -> list[Trade]:
    out = []
    for m in engine.MARKETS:
        out += run_market(m, p)
    return out


if __name__ == "__main__":
    ts = run()
    print(f"ARM A — {len(ts)} trades across {len({t.market for t in ts})} markets")
    nets = [t.net for t in ts]
    print(f"  mean net {np.mean(nets):+.3%}  gross {np.mean([t.gross for t in ts]):+.3%}  "
          f"cost {np.mean([t.cost() for t in ts]):.3%}")
    print(f"  long {sum(1 for t in ts if t.direction>0)}  short {sum(1 for t in ts if t.direction<0)}")
    print(f"  median hold {np.median([t.nights for t in ts]):.0f} nights")
