#!/usr/bin/env python3
"""ARM F, full specification: part A dip-buy + part B overnight."""
import numpy as np, pandas as pd, engine, arm_f, part_b, equity
from engine import _mean

A = arm_f.run()
B = part_b.run()
ALL = A + B

def ann(ts, lbl):
    nets = [t.net for t in ts]
    yrs = (max(t.exit_date for t in ts) - min(t.entry_date for t in ts)).days / 365.25
    print(f"  {lbl:<22} {len(ts):>5} trades   mean net {np.mean(nets):+.4%}   "
          f"gross {np.mean([t.gross for t in ts]):+.4%}   "
          f"cost {np.mean([t.cost() for t in ts]):.4%}   "
          f"~{np.mean(nets)*len(ts)/yrs:+.1%}/yr on notional")

print("PER SLEEVE, our single cost model:")
ann(A, "part A dip-buy"); ann(B, "part B overnight"); ann(ALL, "combined (pooled)")

base = _mean([t.net for t in ALL])
gates = [engine.g1_sign_consistency(ALL), engine.g2_breadth(ALL),
         engine.g3_effect_size(ALL), engine.g4_sample(ALL)]

# gate 5: part A params perturbed; part B's 16:00/09:00 hours are
# hypothesis-defining (GATES_ARM_C.md amendment) -> primary perturbs them,
# secondary holds them.
def run_both(p):
    pa = {k: v for k, v in p.items() if k in arm_f.P}
    pb = {k: v for k, v in p.items() if k in ("enter", "exit")}
    return arm_f.run(pa) + (part_b.run(pb) if pb else B)

params = dict(arm_f.P)
g5_primary = engine.g5_robustness(run_both, {**params, "enter": 16, "exit": 9}, base)
g5_secondary = engine.g5_robustness(run_both, params, base)
g5_primary["gate"] = "5 ROBUSTNESS (primary: all params)"
g5_secondary["gate"] = "5 ROBUSTNESS (secondary: session hours held)"
# gate 6 is a DAILY-resolution control; part B's trades are hourly and
# cannot be matched against daily bars at all. Reported on the daily sleeve
# with the limitation stated, rather than as a spurious "not determinable".
g6 = engine.g6_matched_control(A)
g6["gate"] = "6 MATCHED CONTROL (daily sleeve only)"
g6["limitation"] = ("part B's 8,013 overnight trades are hourly and have no "
                    "daily control pool; an hourly control would be needed, "
                    "as built for ARM C. Its net edge is +0.001%/trade, so "
                    "this cannot change the picture.")
gates += [g5_primary, g5_secondary, g6]

# gate 7: part A sized at 2% risk, part B at 0.5 x E notional per index
sizing = lambda t, atr, E, V: (0.02 * E) / (3.0 * atr * V)
eqA, _ = equity.simulate(A, sizing)
# part B P&L applied on its exit date, scaled to 0.5 x E of notional
pb_daily = {}
for t in B:
    pb_daily.setdefault(pd.Timestamp(t.exit_date.date(), tz="UTC"), []).append(t.net * 0.5)
eq = eqA.copy()
mult = 1.0
vals = []
for d, v in eqA.items():
    r = sum(pb_daily.get(d, []))
    mult *= (1.0 + r)
    vals.append(v * mult)
eq = pd.Series(vals, index=eqA.index)
gates.append(equity.g7_daily_risk(eq, claimed=-0.211))

print(engine.summarise("ARM F full spec (A + B)", ALL, gates))
yrs = (eq.index[-1] - eq.index[0]).days / 365.25
print(f"\n    combined equity 10,000 -> {eq.iloc[-1]:,.0f}   "
      f"CAGR {((eq.iloc[-1]/eq.iloc[0])**(1/yrs)-1):.1%}   "
      f"daily max DD {equity.max_drawdown(eq):.1%}")
print(f"    it claimed: 12.6%/yr, 21.1% DD, 10,000 -> ~132,500")
