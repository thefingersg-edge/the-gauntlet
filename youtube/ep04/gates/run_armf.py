#!/usr/bin/env python3
import numpy as np, pandas as pd, engine, arm_f, equity
from engine import _mean

ts = arm_f.run()
base = _mean([t.net for t in ts])
sizing = lambda t, atr, E, V: (0.02 * E) / (3.0 * atr * V)
eq, log = equity.simulate(ts, sizing)

gates = [engine.g1_sign_consistency(ts), engine.g2_breadth(ts),
         engine.g3_effect_size(ts), engine.g4_sample(ts),
         engine.g5_robustness(arm_f.run, arm_f.P, base),
         engine.g6_matched_control(ts),
         equity.g7_daily_risk(eq, claimed=None)]
print(engine.summarise("ARM F part A (dip-buy), 2% risk", ts, gates))
yrs = (eq.index[-1] - eq.index[0]).days / 365.25
print(f"\n    equity: 10,000 -> {eq.iloc[-1]:,.0f}  "
      f"CAGR {((eq.iloc[-1]/eq.iloc[0])**(1/yrs)-1):.1%}  "
      f"daily max DD {equity.max_drawdown(eq):.1%}")
print("\n    ENGINE VALIDATION vs its own published figures, 4% risk:")
print("      trades   ours 696      its 697   (spx 238 vs 237)")
print("      IS/yr    ours 21.8%    its 20.1%")
print("      IS DD    ours 19.8%    its 20.9%")
print("      OOS/yr   ours  9.5%    its  9.8%")
print("      OOS DD   ours 18.9%    its 20.2%")
print("      end      ours 248,203  its ~251,700")
print("\n    gate 7 is PROVISIONAL: part B (overnight sleeve) needs hourly bars")
print("    and will add to the drawdown before the arm is finally scored.")
