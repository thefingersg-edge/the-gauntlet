import numpy as np, pandas as pd, engine, arm_f, equity
ts = arm_f.run()
sizing = lambda t, atr, E, V: (0.04 * E) / (3.0 * atr * V)
eq, _ = equity.simulate(ts, sizing)
yr = eq.resample("YE").last()
rets = yr.pct_change()
rets.iloc[0] = yr.iloc[0] / 10000.0 - 1
claimed = {2008: -0.031, 2018: -0.060, 2020: -0.124, 2022: -0.082, 2026: 0.288}
print("year   ours      its       diff")
for d, v in rets.items():
    y = d.year
    c = claimed.get(y)
    flag = ""
    if c is not None:
        flag = f"   {c:+7.1%}   {v-c:+7.1%}"
    print(f"{y}  {v:+7.1%}{flag}")
