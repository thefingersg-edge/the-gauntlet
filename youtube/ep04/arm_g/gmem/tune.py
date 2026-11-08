import itertools, csv, sys
from multiprocessing import Pool
import common, arm_gmem
from engine import _mean
TRAIN_END = common.pd.Timestamp("2019-06-30 23:59", tz="UTC")
G = list(itertools.product([2,3,4,5,6],[40,60,100],[100,200,300],[1.5,2.0,2.5,3.0],[3,5,8],[3.0,99.0],["with","none"]))
def one(g):
    L,V,T,K,H,M,tr = g
    ts,uns = common.split(arm_gmem.run(dict(L=L,V=V,T=T,K=K,H=H,M=M),{"trend":tr}))
    trn=[t for t in ts if t.entry_date<=TRAIN_END]
    e1=_mean([t.net for t in trn if t.era=="E1"]); e2=_mean([t.net for t in trn if t.era=="E2"])
    pm={}
    for t in trn: pm.setdefault(t.market,[]).append(t.net)
    brd=sum(1 for v in pm.values() if _mean(v)>0)
    e3=[t.net for t in ts if t.era=="E3"]
    return dict(L=L,V=V,T=T,K=K,H=H,M=M,trend=tr,n_train=len(trn),E1=e1,E2=e2,train=_mean([t.net for t in trn]),
                brd_train=brd,n_E3=len(e3),E3=_mean(e3),n_unseen=len(uns),unseen=_mean([t.net for t in uns]))
if __name__=="__main__":
    k=int(sys.argv[1]); part=G[k*720:(k+1)*720]
    with Pool(4) as p: rows=p.map(one,part,chunksize=8)
    with open(f"tune_grid_{k}.csv","w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print("done",len(rows))
