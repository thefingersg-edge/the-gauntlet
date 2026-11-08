import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import arm_gmem, engine, equity
from engine import _mean
CUT = pd.Timestamp("2026-08-31 23:59", tz="UTC")
IDX = {"spx500usd", "nas100usd", "de30eur"}

def split(ts):
    return [t for t in ts if t.entry_date <= CUT and t.era != "OUT"], [t for t in ts if t.entry_date > CUT]

_sig = {}
def sigma_at(mkt, date, V=60):
    if mkt not in _sig:
        c = engine.load(mkt)["close"]; _sig[mkt] = np.log(c).diff().rolling(V).std(ddof=0)
    s = _sig[mkt]; i = s.index.get_loc(date)
    return float(s.iloc[i - 1])

def sizing(t, atr, E, V):
    sg = sigma_at(t.market, t.entry_date)
    notional = min(0.0020 * E / sg, 1.0 * E)
    return notional / (t.entry_px * V)

def gate_all(name, p=None, opt=None, claimed=None, quiet=False):
    allts = arm_gmem.run(p, opt); ts, unseen = split(allts)
    base = _mean([t.net for t in ts])
    runf = lambda q: split(arm_gmem.run({**(p or {}), **q}, opt))[0]
    P = {**arm_gmem.P, **(p or {})}
    gates = [engine.g1_sign_consistency(ts), engine.g2_breadth(ts), engine.g3_effect_size(ts),
             engine.g4_sample(ts), engine.g5_robustness(runf, P, base), engine.g6_matched_control(ts)]
    eq, _ = equity.simulate(ts, sizing)
    gates.append(equity.g7_daily_risk(eq, claimed=claimed))
    if not quiet:
        print(engine.summarise(name, ts, gates))
        yrs = (eq.index[-1] - eq.index[0]).days / 365.25
        print(f"\n    equity 10,000 -> {eq.iloc[-1]:,.0f}  CAGR {((eq.iloc[-1]/eq.iloc[0])**(1/yrs)-1):.1%}  daily max DD {equity.max_drawdown(eq):.1%}")
        print(f"    unseen after 2026-08-31: n={len(unseen)}  net {_mean([t.net for t in unseen]):+.4%}" if unseen else "    unseen: none")
    return ts, gates, eq, unseen
