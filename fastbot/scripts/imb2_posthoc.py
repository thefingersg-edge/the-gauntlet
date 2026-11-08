import sys, numpy as np, random
sys.argv=['x']; sys.path.insert(0,'.')
import imb2_run as I
src=open('imb2_run.py').read()
# reuse internals by exec of main pieces: simpler re-implement quickly
import csv, os
from collections import defaultdict
D=I.D; first={}
for r in csv.DictReader(open(os.path.join(D,'imb2_msgs.csv'))):
    k=(r['date'],r['venue'],r['symbol']); ms=float(r['ms'])
    if k not in first or ms<first[k][0]:
        sg=1 if r['side']=='B' else (-1 if r['side'] in ('A','S') else 0)
        first[k]=(ms,sg*float(r['imb_qty'])*float(r['ref_price']),float(r['paired_qty'])*float(r['ref_price']))
by=defaultdict(list)
for (d,_,_),v in first.items(): by[d].append(v)
dates=sorted(by); S=[];dd=[]
for d in dates:
    num=sum(s for ms,s,p in by[d] if ms<=1000); den=sum(p for ms,s,p in by[d] if ms<=1000)
    if den>0: S.append(num/den); dd.append(d)
Z=I.zser(dd,S)
PX={}
for r in csv.DictReader(open(os.path.join(D,'imb2_px.csv'))):
    if r['inst']!='SPY': continue
    try: PX[r['date']]=(float(r['b1000']),float(r['a1000']),float(r['b60000']),float(r['a60000']))
    except: pass
def net(d,s):
    b0,a0,b1,a1=PX[d]; g=(b1/a0-1)*1e4 if s>0 else (b0/a1-1)*1e4; return g-2*0.0035/((b0+a0)/2)*1e4
rows=[(d,net(d,1 if z>0 else -1)) for d,z in Z.items() if abs(z)>=1 and d in PX]
by_y=defaultdict(list)
for d,v in rows: by_y[d[:4]].append(v)
for y in sorted(by_y): a=np.array(by_y[y]); print(y,len(a),round(a.mean(),2),round(a.mean()/(a.std(ddof=1)/np.sqrt(len(a))),2))
a=np.array([v for d,v in rows]); print('all',len(a),a.mean())
trim=np.sort(a)[5:-5]; print('trim 5 each side mean',trim.mean())
random.seed(0); pl=[]
for k in range(200):
    pl.append(np.mean([net(d,random.choice([1,-1])) for d,z in Z.items() if abs(z)>=1 and d in PX]))
print('random-side placebo mean of means',np.mean(pl),'p95',np.percentile(pl,95))
