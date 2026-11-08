#!/usr/bin/env python3
"""v39 inputs, built from existing data, no model fitted:
  shapes.npz   the last 24 and 78 five-minute returns before each v37 decision
               point (aligned row-for-row with timeline_v37/matrix.npz)
  meta.npz     every v36 noise-band trade on SPX500 with the row of the
               timeline it may use (the latest decision point at or before
               its signal bar) -- for meta-labelling
"""
import datetime as dt, math, statistics as st, numpy as np
import momentum_v36 as M
from reactive import load, hm, net_open_to_close, gross_open_to_close

z = np.load("../data/timeline_v37/matrix.npz")
dates, hms = z["date"], z["hm"]
days = load("../data", "spx500usd")
ds = sorted(days)
# continuous RTH close series
key, closes = [], []
for d in ds:
    for h in sorted(days[d]):
        key.append((d.isoformat(), h)); closes.append(days[d][h][3])
pos = {k: i for i, k in enumerate(key)}
closes = np.array(closes)
lr = np.diff(np.log(closes), prepend=np.log(closes[0]))
S24 = np.full((len(dates), 24), np.nan, np.float32)
S78 = np.full((len(dates), 78), np.nan, np.float32)
for r, (d, h) in enumerate(zip(dates, hms)):
    i = pos.get((d, h))
    if i is None or i < 80:
        continue
    for w, S in ((24, S24), (78, S78)):
        x = lr[i - w + 1: i + 1]
        sd = x.std()
        if sd > 0:
            S[r] = (x - x.mean()) / sd
np.savez_compressed("../data/v39/shapes.npz", s24=S24, s78=S78)
print("shapes:", np.isfinite(S24[:, 0]).sum(), "rows with a 24-bar shape")

# ---- meta-labelling trade list (v36 rule N, SPX) --------------------------
row_of = {}
for r, (d, h) in enumerate(zip(dates, hms)):
    row_of.setdefault(d, []).append((h, r))
def trades_for(bars, prev_close, sig):
    op = bars["09:30"][0]; ur, dr = max(op, prev_close), min(op, prev_close)
    side, ent, k_in, out = 0, None, None, []
    def close_at(b, s):
        out.append((s, k_in, gross_open_to_close(ent, b, s), net_open_to_close(ent, b, s)))
    for k in M.CHECKS:
        nxt = hm(k, 1)
        if k not in bars or nxt not in bars or sig.get(k) is None:
            continue
        c = bars[k][3]; U, L = ur*(1+sig[k]), dr*(1-sig[k]); vw = M.session_vwap(bars, k)
        if side == 1 and c < max(U, vw):
            close_at(M._as_close(bars[nxt]), 1); side = 0
        elif side == -1 and c > min(L, vw):
            close_at(M._as_close(bars[nxt]), -1); side = 0
        if side == 0:
            if c > U: side, ent, k_in = 1, bars[nxt], k
            elif c < L: side, ent, k_in = -1, bars[nxt], k
    if side:
        close_at(bars["15:55"], side)
    return out
T = []
hist = []
for i in range(1, len(ds)):
    d, bars, prev = ds[i], days[ds[i]], days[ds[i-1]]
    mv = {k: abs(bars[k][3]/bars["09:30"][0]-1) for k in M.CHECKS if k in bars} if "09:30" in bars else {}
    if len(hist) >= M.LOOKBACK and "15:55" in prev and "09:30" in bars and "15:55" in bars and d < dt.date(2026, 9, 18):
        sig = {}
        for k in M.CHECKS:
            xs = [h[k] for h in hist[-M.LOOKBACK:] if k in h]
            sig[k] = st.mean(xs) if len(xs) >= 10 else None
        for s, k_in, g, n in trades_for(bars, prev["15:55"][3], sig):
            cand = [r for h, r in row_of.get(d.isoformat(), []) if h <= k_in]
            if cand:
                T.append((d.isoformat(), k_in, s, g, n, cand[-1]))
    if mv: hist.append(mv)
np.savez_compressed("../data/v39/meta.npz", date=np.array([t[0] for t in T]), signal_bar=np.array([t[1] for t in T]),
                    side=np.array([t[2] for t in T], np.int8), gross=np.array([t[3] for t in T], np.float32),
                    net=np.array([t[4] for t in T], np.float32), row=np.array([t[5] for t in T], np.int64))
print("meta: noise-band trades with a timeline row:", len(T))
