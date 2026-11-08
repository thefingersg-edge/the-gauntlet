from common import *
from engine import _mean
ts, gates, eq, unseen = gate_all("ARM G-mem spec 2 (as written)")
non = [t for t in ts if t.market not in IDX]
pm = {m: _mean([t.net for t in non if t.market == m]) for m in {t.market for t in non}}
print("\n  --- spec 2's own abandon conditions ---")
print(f"  (a) any gate fails: {sum(not g['pass'] for g in gates)} failed")
print(f"  (b) ex-index net {_mean([t.net for t in non]):+.4%} on {len(non)} (abandon if <= 0); {sum(v>0 for v in pm.values())} of {len(pm)} positive")
e1=_mean([t.net for t in ts if t.era=='E1']); e3=_mean([t.net for t in ts if t.era=='E3'])
print(f"  (c) E1 {e1:+.4%}  E3 {e3:+.4%}  (abandon if E3 < E1/2)")
print(f"  stops {sum(t.reason=='stop' for t in ts)}  long {sum(t.direction>0 for t in ts)}  short {sum(t.direction<0 for t in ts)}  median nights {np.median([t.nights for t in ts]):.0f}")
