from common import *
from engine import _mean
V = {"G0": ({}, {}), "G1": ({"K":2.5}, {}), "G2": ({"K":3.0}, {}),
     "G3": ({}, {"trend":"none"}), "G4": ({"K":2.5}, {"trend":"none"}),
     "G5": ({"K":2.5}, {"trend_at":"t-L"}), "G6": ({"K":2.5,"M":99.0}, {}), "G7": ({"K":2.5,"H":3}, {})}
res = {}
print(f"{'id':<4}{'n12':>5}{'E1':>9}{'E2':>9}{'E1+E2':>9}{'brd12':>6}{'elig':>6} | {'E3':>9}{'nE3':>5}{'full':>9}")
for k,(p,o) in V.items():
    ts,_ = split(arm_gmem.run(p,o))
    d = [t for t in ts if t.era in ("E1","E2")]
    e1=_mean([t.net for t in ts if t.era=="E1"]); e2=_mean([t.net for t in ts if t.era=="E2"])
    pm={m:_mean([t.net for t in d if t.market==m]) for m in {t.market for t in d}}
    brd=sum(v>0 for v in pm.values()); m12=_mean([t.net for t in d])
    el = e1>0 and e2>0 and brd>=14
    e3=[t.net for t in ts if t.era=="E3"]
    res[k]=(el,m12)
    print(f"{k:<4}{len(d):>5}{e1:>+9.3%}{e2:>+9.3%}{m12:>+9.3%}{brd:>6}{str(el):>6} | {_mean(e3):>+9.3%}{len(e3):>5}{_mean([t.net for t in ts]):>+9.3%}")
el=[k for k,(e,m) in res.items() if e]
print("eligible:", el, "pick:", max(el,key=lambda k:res[k][1]) if el else None)
