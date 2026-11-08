#!/usr/bin/env python3
"""OILCARRY1 mechanical roll fix (logged after the registered run): the roll-day scan shows EIA's RCLC1 switches contract ON the
CL last trading day (offset -1: corr 0.82, step/slope 0.98), not the day after as oilgold_run.py assumed (offset 0: 0.63, 2.61).
Re-runs the identical OILCARRY1 primary with the roll moved one day earlier. Everything else unchanged. Descriptive companion.
I am not a financial adviser. This is a measurement, not a recommendation."""
import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, oilgold_run as G
F = pd.concat({k: G.series(f"oil/wti_f{k}.csv") for k in (1, 2)}, axis=1).dropna(); F = F[(F.index >= "1986-01-01") & (F.index < G.END)]; idx = F.index
roll = pd.Series(False, index=idx)
for y in range(idx[0].year, idx[-1].year + 1):
    for m in range(1, 13):
        p = idx.searchsorted(G.cl_last_trade(y, m), side="right") - 1
        if 0 < p < len(idx): roll.iloc[p] = True
ref = F[1].shift(1).where(~roll, F[2].shift(1)); r = ((F[1] - ref) / ref.abs()).fillna(0.0)
sig = np.sqrt((r ** 2).ewm(com=60).mean() * 252); me = F[1].groupby([idx.year, idx.month]).tail(1).index; c12 = F[1] / F[2] - 1
wt = pd.Series(np.nan, index=idx)
for d in me:
    if sig[d] > 0: wt[d] = float(np.clip(np.sign(c12[d]) * 0.10 / sig[d], -3, 3))
w = wt.ffill().shift(1).fillna(0.0); held = w.shift(1).fillna(0.0); x = held * r - (w - held).abs() * 0.0002; x = x[x.index >= "1987-01-01"]
yrs = (x.index[-1] - x.index[0]).days / 365.25; sh = x.mean() / x.std() * math.sqrt(252); eq = (1 + x).cumprod()
eras = [x[(x.index.year >= a) & (x.index.year <= b)].sum() for a, b in ((1987, 2004), (2005, 2014), (2015, 2026))]
L = [f"OILCARRY1 roll-fixed (offset -1): Sharpe {sh:+.2f}, x sqrt(yrs) {sh * math.sqrt(yrs):+.2f}, {x.mean() * 252 * 100:+.1f}%/yr, worst drawdown {float((eq / eq.cummax() - 1).min()) * 100:.0f}%",
     "  eras: " + "  ".join(f"{a}-{b} {e * 100:+.0f}%" for (a, b), e in zip(((1987, 2004), (2005, 2014), (2015, 2026)), eras))]
open(os.path.join(G.FB, "data", "run_oilcarry1_rollfix.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))
