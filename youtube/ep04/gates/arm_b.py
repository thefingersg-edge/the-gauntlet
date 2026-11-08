#!/usr/bin/env python3
"""ARM B — Path-Continuity Trend. From run1_armB.md, verbatim.

Information discreteness: a 60-day trend is traded only when it was built
from many small same-direction days rather than a few large jumps. The
signal is deliberately orthogonal to prior return and prior volatility,
which is what gate 6 matches on.

Weekend merging in the spec is a no-op here: the daily files contain no
weekend bars.
"""
from __future__ import annotations
import numpy as np, pandas as pd
import engine
from engine import Trade

P = dict(L=60, W=60, theta=-0.10, H=20, k=2.5)
MIRROR = False   # True -> take only ID >= +|theta| (jump-built trends)


def run_market(mkt: str, p: dict = None) -> list[Trade]:
    p = {**P, **(p or {})}
    L, W, H, k, th = int(p["L"]), int(p["W"]), int(p["H"]), p["k"], p["theta"]
    df = engine.load(mkt)
    if len(df) < L + H + 5:
        return []
    c, o = df["close"], df["open"]
    lr = np.log(c).diff()
    R = np.log(c / c.shift(L))
    sig = lr.rolling(W).std(ddof=1)
    P_ = (lr > 0).rolling(W).sum()
    N_ = (lr < 0).rolling(W).sum()
    d = np.sign(R)
    ID = d * (N_ - P_) / L

    idx = df.index; n = len(df)
    cv, ov = c.to_numpy(), o.to_numpy()
    Rv, sv, dv, IDv = R.to_numpy(), sig.to_numpy(), d.to_numpy(), ID.to_numpy()

    trades: list[Trade] = []
    i = L
    while i < n - 1:
        if not (np.isfinite(Rv[i]) and np.isfinite(sv[i]) and np.isfinite(IDv[i])):
            i += 1; continue
        if Rv[i] == 0 or sv[i] <= 0:
            i += 1; continue
        gate = (IDv[i] >= abs(th)) if MIRROR else (IDv[i] <= th)
        if not gate:
            i += 1; continue
        dd = int(dv[i])
        kk = i + 1
        E = ov[kk]
        D = k * sv[i] * np.sqrt(H)

        exit_i = exit_px = None
        for j in range(1, H):                       # stop checked on closes 1..H-1
            m = i + j
            if m >= n: break
            if dd * np.log(cv[m] / E) <= -D:
                if m + 1 < n:
                    exit_i, exit_px = m + 1, ov[m + 1]
                else:
                    exit_i, exit_px = m, cv[m]
                break
        if exit_i is None:                          # time exit at close of bar t+H
            m = min(i + H, n - 1)
            exit_i, exit_px = m, cv[m]

        trades.append(Trade(mkt, dd, idx[kk], idx[exit_i], float(E),
                            float(exit_px), "stop" if exit_i < i + H else "time"))
        i = exit_i                                  # rule re-evaluated at that close
    return trades


def run(p: dict = None) -> list[Trade]:
    out = []
    for m in engine.MARKETS:
        out += run_market(m, p)
    return out


if __name__ == "__main__":
    ts = run()
    nets = [t.net for t in ts]
    print(f"ARM B — {len(ts)} trades, {len({t.market for t in ts})} markets")
    print(f"  mean net {np.mean(nets):+.3%}  gross {np.mean([t.gross for t in ts]):+.3%}  "
          f"cost {np.mean([t.cost() for t in ts]):.3%}")
    print(f"  long {sum(1 for t in ts if t.direction>0)}  short {sum(1 for t in ts if t.direction<0)}"
          f"  median hold {np.median([t.nights for t in ts]):.0f} nights")
