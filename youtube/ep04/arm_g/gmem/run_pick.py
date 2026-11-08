from common import *
from engine import _mean
p=dict(L=6,V=40,T=200,K=3.0,H=3,M=99.0); o={"trend":"none"}
ts,gates,eq,uns=gate_all("TUNED PICK (fitted on 2005-2019)",p,o,claimed=-0.25)
def row(l,xs):
    print(f"  {l:<12} n={len(xs):>4} net {_mean([t.net for t in xs]):+.3%}")
for k in ["fx","idx"]: pass
row("indices",[t for t in ts if t.market in IDX]); row("ex-index",[t for t in ts if t.market not in IDX])
row("long",[t for t in ts if t.direction>0]); row("short",[t for t in ts if t.direction<0])
for y in range(2019,2027): row(str(y),[t for t in ts if t.entry_date.year==y])
