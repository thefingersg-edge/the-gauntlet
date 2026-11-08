#!/usr/bin/env python3
"""Score any arm through the seven gates. One path for every arm."""
import sys, numpy as np, pandas as pd, engine, equity
from engine import _mean


def score(name, module, sizing=None, claimed_dd=None, skip_robust=(), quiet=False):
    ts = module.run()
    if not ts:
        print(f"{name}: NO TRADES"); return None
    base = _mean([t.net for t in ts])
    gates = [engine.g1_sign_consistency(ts), engine.g2_breadth(ts),
             engine.g3_effect_size(ts), engine.g4_sample(ts),
             engine.g5_robustness(module.run, module.P, base, skip=skip_robust),
             engine.g6_matched_control(ts)]
    eq = None
    if sizing is not None:
        eq, _ = equity.simulate(ts, sizing)
        gates.append(equity.g7_daily_risk(eq, claimed=claimed_dd))
    if not quiet:
        print(engine.summarise(name, ts, gates))
        if eq is not None:
            yrs = (eq.index[-1] - eq.index[0]).days / 365.25
            print(f"\n    equity 10,000 -> {eq.iloc[-1]:,.0f}   "
                  f"CAGR {((eq.iloc[-1]/eq.iloc[0])**(1/yrs)-1):.1%}   "
                  f"daily max DD {equity.max_drawdown(eq):.1%}")
    return ts, gates, eq


def brief(name, ts, gates):
    c = sum(1 for g in gates if g["pass"])
    nets = [t.net for t in ts]
    return (f"{name:<28} {c} of {len(gates)}   {len(ts):>5} trades  "
            f"{len({t.market for t in ts}):>2} mkts  net/trade {np.mean(nets):+.3%}  "
            f"| " + "  ".join(("P" if g["pass"] else "F") for g in gates))
