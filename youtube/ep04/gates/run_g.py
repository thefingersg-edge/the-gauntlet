import numpy as np, pandas as pd, engine, arm_g, score
from engine import _mean
sizing = lambda t, atr, E, V: (0.0025 * E) / (atr * V)
r = score.score("ARM G (trend-aligned shock reversal)", arm_g, sizing, claimed_dd=-0.20)
ts = r[0]
print("\n  --- ARM G's own kill conditions ---")
IDX = {"spx500usd", "nas100usd", "de30eur"}
non = [t for t in ts if t.market not in IDX]
pm = {m: _mean([t.net for t in non if t.market == m]) for m in {t.market for t in non}}
posn = sum(1 for v in pm.values() if v > 0)
print(f"  K2 is it ARM F relabelled: ex-index pooled net {_mean([t.net for t in non]):+.4%} "
      f"(abandon if < +0.10%), {posn} of {len(pm)} positive (abandon if < 11)")
for e in ("E1", "E2", "E3"):
    sh = [t.net for t in ts if t.era == e and t.direction < 0]
    print(f"  K3 short side {e}: {_mean(sh):+.4%}  n={len(sh)}")
e1 = _mean([t.net for t in ts if t.era == "E1"]); e3 = _mean([t.net for t in ts if t.era == "E3"])
print(f"  K4 decay: E1 {e1:+.4%}  E3 {e3:+.4%}  (abandon if E3 < E1/3)")
cr = [t for t in ts if not (pd.Timestamp("2008-09-01",tz="UTC") <= t.entry_date <= pd.Timestamp("2009-03-31",tz="UTC")
      or pd.Timestamp("2020-02-01",tz="UTC") <= t.entry_date <= pd.Timestamp("2020-05-31",tz="UTC"))]
print(f"  K5 ex-crisis: {_mean([t.net for t in cr]):+.4%} on {len(cr)} trades (abandon if negative)")
