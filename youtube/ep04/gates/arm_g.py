#!/usr/bin/env python3
"""ARM G — trend-aligned shock reversal, 21 markets, daily.
From PREREGISTRATION_ARM_G.md, verbatim.

Unlike arms A-F this one has a BOOK CAP (max 8 concurrent positions across
the whole panel, filled in descending |z|), so signals cannot be generated
per market independently. The spec is explicit that "the gate trade list is
the trade list of this capped book", so the simulation walks the global
date timeline.

Sunday-bar merging in the spec is a no-op here: make_daily.py already bins
to the 17:00 New York rollover and emits no weekend-dated rows.
"""
from __future__ import annotations
import numpy as np, pandas as pd
import engine
from engine import Trade

P = dict(L=4, W=60, theta=2.0, N=200, H=4, k=4.0, M=8)


def signals(mkt: str, p: dict):
    """Per-market signal frame: direction, z, sigma, indexed by bar."""
    df = engine.load(mkt)
    L, W, N = int(p["L"]), int(p["W"]), int(p["N"])
    if len(df) < N + L + 2:
        return None
    c = df["close"]
    lr = np.log(c).diff()
    sig = lr.rolling(W).std(ddof=1)
    z = np.log(c / c.shift(L)) / (sig * np.sqrt(L))
    sma = c.rolling(N).mean()
    # trend read at bar t-L, BEFORE the shock began -- a large shock must not
    # be able to flip its own filter
    trend = np.sign(c.shift(L) - sma.shift(L))
    long_ok = (trend > 0) & (z <= -p["theta"])
    short_ok = (trend < 0) & (z >= p["theta"])
    d = pd.Series(0, index=df.index, dtype=int)
    d[long_ok] = 1
    d[short_ok] = -1
    ok = sig.notna() & (sig > 0) & z.notna() & trend.notna()
    d[~ok] = 0
    return pd.DataFrame({"d": d, "z": z, "sigma": sig}, index=df.index)


def run(p: dict = None) -> list[Trade]:
    p = {**P, **(p or {})}
    H, k, M = int(p["H"]), p["k"], int(p["M"])
    S, DF = {}, {}
    for m in engine.MARKETS:
        s = signals(m, p)
        if s is not None:
            S[m] = s
            DF[m] = engine.load(m)
    if not S:
        return []
    dates = sorted(set().union(*[set(s.index) for s in S.values()]))
    pos_of = {m: {d: i for i, d in enumerate(DF[m].index)} for m in S}

    open_pos: dict[str, dict] = {}
    trades: list[Trade] = []

    for t in dates:
        # --- exits first, so slots free up before the day's entries
        for m in list(open_pos):
            pp = open_pos[m]
            i = pos_of[m].get(t)
            if i is None:
                continue
            row = DF[m].iloc[i]
            d, Sx = pp["d"], pp["stop"]
            hit = (row["open"] <= Sx or row["low"] <= Sx) if d > 0 \
                  else (row["open"] >= Sx or row["high"] >= Sx)
            px = why = None
            if hit:                                   # stop checked before time
                if d > 0:
                    px = row["open"] if row["open"] <= Sx else Sx
                else:
                    px = row["open"] if row["open"] >= Sx else Sx
                why = "stop"
            elif i >= pp["exit_i"]:                   # time exit, close of t+H
                px, why = row["close"], "time"
            if px is not None:
                trades.append(Trade(m, d, pp["entry_date"], t,
                                    float(pp["entry_px"]), float(px), why))
                del open_pos[m]

        # --- entries, descending |z|, ties alphabetical, cap M
        cand = []
        for m, s in S.items():
            if m in open_pos or t not in s.index:
                continue
            r = s.loc[t]
            if r["d"] != 0 and np.isfinite(r["z"]):
                cand.append((abs(r["z"]), m, int(r["d"]), r["sigma"]))
        if not cand:
            continue
        cand.sort(key=lambda x: (-x[0], x[1]))
        for _, m, d, sg in cand:
            if len(open_pos) >= M:
                break
            i = pos_of[m][t]
            if i + 1 >= len(DF[m]):
                continue
            E = float(DF[m]["open"].iloc[i + 1])
            stop = E * (1 - d * k * sg)
            open_pos[m] = dict(d=d, entry_px=E, stop=stop,
                               entry_date=DF[m].index[i + 1],
                               exit_i=i + 1 + H - 1)
    return trades


if __name__ == "__main__":
    ts = run()
    nets = [t.net for t in ts]
    print(f"ARM G — {len(ts)} trades, {len({t.market for t in ts})} markets")
    print(f"  mean net {np.mean(nets):+.4%}  gross {np.mean([t.gross for t in ts]):+.4%}  "
          f"cost {np.mean([t.cost() for t in ts]):.4%}")
    print(f"  long {sum(1 for t in ts if t.direction>0)}  short {sum(1 for t in ts if t.direction<0)}"
          f"   stops {sum(1 for t in ts if t.reason=='stop')}"
          f"   median hold {np.median([t.nights for t in ts]):.0f} nights")
