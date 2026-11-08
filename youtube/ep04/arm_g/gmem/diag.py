from common import *
from engine import _mean
import arm_gmem
ts, _ = split(arm_gmem.run())
def row(lbl, xs):
    if not xs: print(f"  {lbl:<34} n=0"); return
    g=_mean([t.gross for t in xs]); n=_mean([t.net for t in xs])
    se=np.std([t.net for t in xs],ddof=1)/np.sqrt(len(xs)) if len(xs)>1 else np.nan
    print(f"  {lbl:<34} n={len(xs):>4}  gross {g:+.3%}  net {n:+.3%}  t {n/se:+.2f}")
print("BY ERA x SIDE")
for e in ("E1","E2","E3"):
    for d,lab in ((1,"long"),(-1,"short")): row(f"{e} {lab}", [t for t in ts if t.era==e and t.direction==d])
print("BY ASSET CLASS")
cls={"fx":["eurusd","gbpusd","usdjpy","usdcad","audusd","eurgbp","eurjpy"],"metals":["xauusd","xagusd","xptusd","xcuusd"],
     "indices":["spx500usd","nas100usd","de30eur"],"energy":["bcousd","natgasusd"],"rates":["usb10yusd","de10ybeur"],"softs":["cornusd","wheatusd","sugarusd"]}
for k,v in cls.items(): row(k,[t for t in ts if t.market in v])
for k,v in cls.items():
    for e in ("E1","E2","E3"): row(f"  {k} {e}",[t for t in ts if t.market in v and t.era==e])
print("EXIT")
row("stopped",[t for t in ts if t.reason=="stop"]); row("time",[t for t in ts if t.reason=="time"])
print("BY |z| BUCKET at signal")
zs={}
for m in engine.MARKETS:
    c=engine.load(m)["close"]; lr=np.log(c).diff(); z=np.log(c/c.shift(4))/(lr.rolling(60).std(ddof=0)*2); zs[m]=z
for lo,hi in ((2.0,2.25),(2.25,2.5),(2.5,3.0),(3.0,99)):
    sel=[]
    for t in ts:
        s=zs[t.market]; i=s.index.get_loc(t.entry_date)-1; a=abs(s.iloc[i])
        if lo<=a<hi: sel.append(t)
    row(f"|z| {lo}-{hi}",sel)
print("BY YEAR (net mean, n)")
yrs=sorted({t.entry_date.year for t in ts})
print("  "+"  ".join(f"{y}:{_mean([t.net for t in ts if t.entry_date.year==y])*100:+.2f}({sum(t.entry_date.year==y for t in ts)})" for y in yrs))
cr=[t for t in ts if not (pd.Timestamp("2008-09-01",tz="UTC")<=t.entry_date<=pd.Timestamp("2009-03-31",tz="UTC") or pd.Timestamp("2020-02-01",tz="UTC")<=t.entry_date<=pd.Timestamp("2020-05-31",tz="UTC"))]
row("ex-crisis",cr)
row("ALL",ts)
