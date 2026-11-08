#!/usr/bin/env python3
"""ARM G-mem (spec 2, memory-open side test). ARM_G_SPEC_trend_side_reversal.md verbatim.
Per-market, uncapped, as section 5 says gates 1-6 are scored."""
import os, sys
GATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "gates")
sys.path.insert(0, os.path.abspath(GATES))
import numpy as np, pandas as pd, engine
from engine import Trade
engine.DATA = os.path.join(os.path.expanduser("~"), "mnt", "RStudio", "Claude", "pineport", "adaptive", "data")

P = dict(L=4, V=60, T=200, K=2.0, H=5, M=3.0)
# variant switches (not parameters; default = spec 2 exactly)
OPT = dict(side="both", trend="with", trend_at="t", markets=None)

def run_market(mkt, p, opt):
    df = engine.load(mkt)
    L, V, T, H = int(p["L"]), int(p["V"]), int(p["T"]), int(p["H"])
    K, M = p["K"], p["M"]
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    cs = df["close"]
    lr = np.log(cs).diff()
    sig = lr.rolling(V).std(ddof=0).to_numpy()
    z = (np.log(cs / cs.shift(L)) / (lr.rolling(V).std(ddof=0) * np.sqrt(L))).to_numpy()
    sma = cs.rolling(T).mean()
    if opt["trend_at"] == "t-L":
        up = (cs.shift(L) > sma.shift(L)).to_numpy(); dn = (cs.shift(L) < sma.shift(L)).to_numpy()
    else:
        up = (cs > sma).to_numpy(); dn = (cs < sma).to_numpy()
    sm = sma.to_numpy()
    idx = df.index; n = len(c); out = []; t = 0
    while t < n - 1:
        if not (np.isfinite(z[t]) and np.isfinite(sm[t]) and sig[t] > 0):
            t += 1; continue
        d = 0
        if opt["trend"] == "with":
            if z[t] <= -K and up[t]: d = 1
            elif z[t] >= K and dn[t]: d = -1
        elif opt["trend"] == "against":       # fade shocks that go WITH the trend
            if z[t] <= -K and dn[t]: d = 1
            elif z[t] >= K and up[t]: d = -1
        else:                                  # no trend filter
            if z[t] <= -K: d = 1
            elif z[t] >= K: d = -1
        if opt["side"] == "long" and d < 0: d = 0
        if opt["side"] == "short" and d > 0: d = 0
        if d == 0:
            t += 1; continue
        E = t + 1
        stop = c[t] * (1 - d * M * sig[t] * np.sqrt(H))
        px = None; xi = None; why = None
        for j in range(E, min(E + H, n)):
            if j > E or True:
                if d > 0 and o[j] <= stop: px, xi, why = o[j], j, "stop"; break
                if d < 0 and o[j] >= stop: px, xi, why = o[j], j, "stop"; break
            if d > 0 and l[j] <= stop: px, xi, why = stop, j, "stop"; break
            if d < 0 and h[j] >= stop: px, xi, why = stop, j, "stop"; break
        if px is None:
            if E + H >= n: break
            px, xi, why = o[E + H], E + H, "time"
        out.append(Trade(mkt, d, idx[E], idx[xi], float(o[E]), float(px), why))
        # flat after the exit fill; a stop at bar xi allows a signal at xi's close,
        # a time exit at the open of xi allows a signal at xi's close too
        t = xi
    return out

def run(p=None, opt=None):
    p = {**P, **(p or {})}; opt = {**OPT, **(opt or {})}
    ms = opt["markets"] or engine.MARKETS
    ts = []
    for m in ms:
        ts += run_market(m, p, opt)
    return [x for x in ts if x.era != "OUT" or x.entry_date > pd.Timestamp("2026-08-31", tz="UTC")]
