import numpy as np, pandas as pd, engine, arm_f, equity
ts = arm_f.run()
sizing = lambda t, atr, E, V: (0.02 * E) / (3.0 * atr * V)
eq, log = equity.simulate(ts, sizing)
print(f"ARM F part A — daily equity, own sizing (2% risk)")
print(f"  start 10,000   end {eq.iloc[-1]:,.0f}   bars {len(eq)}")
yrs = (eq.index[-1] - eq.index[0]).days / 365.25
print(f"  CAGR {((eq.iloc[-1]/eq.iloc[0])**(1/yrs)-1):.1%}  over {yrs:.1f}y")
print(f"  max drawdown at DAILY resolution: {equity.max_drawdown(eq):.1%}")
print(f"  {log}")
g = equity.g7_daily_risk(eq, claimed=-0.211)
for k, v in g.items(): print(f"  {k}: {v}")
