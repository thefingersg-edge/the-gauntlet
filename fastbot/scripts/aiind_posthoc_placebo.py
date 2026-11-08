import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd, aiind_run as R, aiind_port as P
from numba import njit
btc = R.load_btc(); a = [btc[k].to_numpy() for k in "ohlcv"]
tg, d = P.knn_signals(*a)
W0, W1 = R.ts("2021-07-01"), R.ts("2026-09-30 23:59")
lc, sc = d["longc"], d["shortc"]
@njit
def sim(lc, sc, q, seed):
    np.random.seed(seed); n = lc.size; out = np.zeros(n); pos = 0.0
    for t in range(n):
        if (lc[t] or sc[t]) and np.random.random() < q:
            pos = 1.0 if lc[t] else -1.0
        out[t] = pos
    return out
base = R.trades(btc, tg, R.btc_cost(10), W0, W1); n_knn = len(base)
dk = R.daily_pnl(btc, tg, R.btc_cost(10), W0, W1)
# calibrate q to match trade count
qs = np.linspace(0.05, 0.6, 23); cnt = []
for q in qs:
    cnt.append(len(R.trades(btc, sim(lc, sc, q, 1), R.btc_cost(10), W0, W1)))
q = float(np.interp(n_knn, cnt, qs))
res = []
for s in range(200):
    T = sim(lc, sc, q, 100 + s)
    tr = R.trades(btc, T, R.btc_cost(0), W0, W1); dd = R.daily_pnl(btc, T, R.btc_cost(10), W0, W1)
    res.append((len(tr), tr.net_bp.mean(), dd.mean()))
res = np.array(res)
g = R.trades(btc, tg, R.btc_cost(0), W0, W1).net_bp.mean()
print(f"POST-HOC placebo (not registered): random filter keeping each crossover with p={q:.3f}, 200 draws, same window")
print(f"  kNN: {n_knn} trades, gross {g:+.2f} bp/trade, daily net {dk.mean():+.1f} bp")
print(f"  random: trades median {np.median(res[:,0]):.0f}; gross median {np.median(res[:,1]):+.2f} bp/trade (5-95% {np.percentile(res[:,1],5):+.2f} .. {np.percentile(res[:,1],95):+.2f}); daily net median {np.median(res[:,2]):+.1f} (5-95% {np.percentile(res[:,2],5):+.1f} .. {np.percentile(res[:,2],95):+.1f})")
print(f"  kNN gross beats {np.mean(res[:,1] < g)*100:.0f}% of random draws; kNN daily net beats {np.mean(res[:,2] < dk.mean())*100:.0f}%")
