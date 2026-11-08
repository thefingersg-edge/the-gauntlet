#!/usr/bin/env python3
"""ARM C — sized equity curve at its own rules, for gate C5 and the forward
test baseline.

Its sizing, verbatim: risk 1.0% of current equity; Units = floor(risk /
(0.30 x ATR)); one unit is $1 per index point; notional cap units x price
<= 3 x equity; skip if units rounds to 0. No financing: nothing is held
overnight.

Resolution is the ENTRY BAR, not the day, because a strategy flat by 16:00
every day shows nothing at daily resolution -- which is the whole point of
the gate.
"""
from __future__ import annotations
import numpy as np, pandas as pd, engine, arm_c
from part_b import load_h1

def simulate(start=10000.0, risk=0.01, stop_atr=0.30, notional_cap=3.0):
    ts = sorted(arm_c.run(), key=lambda t: t.entry_date)
    atr = {m: arm_c.wilder_atr_daily(m, arm_c.P["atr_n"]) for m in arm_c.MARKETS}
    atr_by_day = {m: pd.Series(a.to_numpy(), index=a.index.normalize())
                  for m, a in atr.items()}
    E = start
    curve, skipped = [], 0
    for t in ts:
        prev_day = pd.Timestamp(t.entry_date.tz_convert("America/New_York")
                                .normalize().tz_localize(None), tz="UTC") - pd.Timedelta(days=1)
        a = atr_by_day[t.market].asof(prev_day)
        if not np.isfinite(a) or a <= 0:
            skipped += 1; continue
        units = np.floor((risk * E) / (stop_atr * a) * 100) / 100.0
        if units * t.entry_px > notional_cap * E:
            units = np.floor((notional_cap * E / t.entry_px) * 100) / 100.0
        if units <= 0:
            skipped += 1; continue
        pnl = units * t.direction * (t.exit_px - t.entry_px)
        pnl -= abs(units * t.entry_px) * engine.SPREAD_RT[t.market]
        E += pnl
        curve.append((t.entry_date, E))
        if E <= 0:
            print("  ACCOUNT WIPED OUT at", t.entry_date); break
    s = pd.Series([v for _, v in curve], index=[d for d, _ in curve])
    return s, skipped


if __name__ == "__main__":
    eq, sk = simulate()
    peak = eq.cummax()
    dd = ((eq - peak) / peak).min()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / 10000.0) ** (1 / yrs) - 1 if eq.iloc[-1] > 0 else float("nan")
    print(f"ARM C — sized at its own 1% risk rule")
    print(f"  trades sized {len(eq)}   skipped {sk}")
    print(f"  10,000 -> {eq.iloc[-1]:,.0f}   CAGR {cagr:+.1%}   over {yrs:.1f}y")
    print(f"  max drawdown at ENTRY-BAR resolution: {dd:.1%}")
    # what its own cost assumption would have given
    import copy
    save = dict(engine.SPREAD_RT)
    engine.SPREAD_RT["spx500usd"] = 1.0 / 7700
    engine.SPREAD_RT["nas100usd"] = 2.0 / 25000
    eq2, _ = simulate()
    engine.SPREAD_RT.update(save)
    y2 = (eq2.index[-1] - eq2.index[0]).days / 365.25
    c2 = (eq2.iloc[-1] / 10000.0) ** (1 / y2) - 1 if eq2.iloc[-1] > 0 else float("nan")
    print(f"\n  under ITS OWN spread assumption (1pt spx, 2pt nas):")
    print(f"  10,000 -> {eq2.iloc[-1]:,.0f}   CAGR {c2:+.1%}   "
          f"max DD {(((eq2-eq2.cummax())/eq2.cummax()).min()):.1%}")
