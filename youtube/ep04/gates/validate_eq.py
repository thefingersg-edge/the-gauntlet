import numpy as np, pandas as pd, engine, arm_f, equity
ts = arm_f.run()
for risk in (0.02, 0.03, 0.04):
    sizing = lambda t, atr, E, V, r=risk: (r * E) / (3.0 * atr * V)
    eq, log = equity.simulate(ts, sizing)
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1
    pre = eq[eq.index < pd.Timestamp('2018-01-01', tz='UTC')]
    post = eq[eq.index >= pd.Timestamp('2018-01-01', tz='UTC')]
    def seg(s):
        y = (s.index[-1]-s.index[0]).days/365.25
        return (s.iloc[-1]/s.iloc[0])**(1/y)-1, equity.max_drawdown(s)
    pc, pdd = seg(pre); oc, odd = seg(post)
    print(f"risk {risk:.0%}:  full CAGR {cagr:6.1%}  DD {equity.max_drawdown(eq):6.1%}"
          f"   | IS {pc:6.1%}/{pdd:6.1%}  OOS {oc:6.1%}/{odd:6.1%}   end {eq.iloc[-1]:>10,.0f}")
print()
print("IT REPORTED, round 2 (dip-buy alone, 4% risk):")
print("  IS 2005-2017  20.1%/yr  DD 20.9%     OOS 2018-26  9.8%/yr  DD 20.2%")
print("  full 16.0%/yr  DD 20.9%   10,000 -> ~251,700")
print("IT REPORTED, round 3 (dip-buy alone at 3%, sized to 20% breach risk):")
print("  OOS 7.5%/yr  DD 15.3%")
