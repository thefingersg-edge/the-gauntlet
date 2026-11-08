from common import *
from engine import _mean
import engine, arm_gmem
H4 = os.path.join(os.path.expanduser("~"),"mnt","RStudio","Claude","pineport","adaptive","data_h4")
_c = {}
def load_h4(m):
    if m not in _c:
        df = pd.read_csv(os.path.join(H4, f"{m}_h4.csv"), parse_dates=["time"]).set_index("time").sort_index()
        _c[m] = df[~df.index.duplicated(keep="first")]
    return _c[m]
engine.load = load_h4; arm_gmem.engine.load = load_h4
P = dict(L=6,V=40,T=200,K=3.0,H=3,M=99.0); O={"trend":"none"}
ts = [t for t in arm_gmem.run(P,O) if t.era != "OUT"]
base = _mean([t.net for t in ts])
runf = lambda q: [t for t in arm_gmem.run({**P,**q},O) if t.era!="OUT"]
gates=[engine.g1_sign_consistency(ts),engine.g2_breadth(ts),engine.g3_effect_size(ts),engine.g4_sample(ts),
       engine.g5_robustness(runf,P,base),engine.g6_matched_control(ts)]
print(engine.summarise("TUNED RULE ON H4 (never tuned here)",ts,gates))
x=np.array([t.net for t in ts]); print(f"\n  t-stat {x.mean()/(x.std(ddof=1)/np.sqrt(len(x))):+.2f}")
def row(l,xs): print(f"  {l:<10} n={len(xs):>5}  gross {_mean([t.gross for t in xs]):+.3%}  net {_mean([t.net for t in xs]):+.3%}")
row("indices",[t for t in ts if t.market in IDX]); row("ex-index",[t for t in ts if t.market not in IDX])
row("long",[t for t in ts if t.direction>0]); row("short",[t for t in ts if t.direction<0])
row("0 nights",[t for t in ts if t.nights==0]); row("1+ nights",[t for t in ts if t.nights>0])
print("  per year:", [ (y, sum(t.entry_date.year==y for t in ts)) for y in (2023,2024,2025,2026)])
e=gates[0]["by_era"]; ok=all(v>0 for v in e.values()) and base>=0.001
print("\n  PLAN VERDICT:", "PASS - mechanism holds on H4" if ok else "FAIL - daily result treated as fitted noise")
