"""Shared 15m loader for v51 (BOS/CHoCH) and the v51-v53 budget.
load15(stem) -> numpy arrays: t (datetime64[m], UTC bar start), o,h,l,c (mid), spr_bp (quoted spread at bar open, bp).
SPX500, NAS100, XAUUSD from data/v24 15m bid/ask; UK100 built from data/v38 5m bid/ask (3 x 5m -> 15m on the UTC grid)."""
import csv, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "..", "data")
STEMS = ("spx500usd", "nas100usd", "uk100gbp", "xauusd")


def _read(path):
    rows = {}
    with open(path) as fh:
        rd = csv.reader(fh); next(rd)
        for r in rd:
            rows[r[0]] = (float(r[1]), float(r[2]), float(r[3]), float(r[4]))
    return rows


def load15(stem):
    cache = os.path.join(D, "v51", f"{stem}_15m.npz")
    if os.path.exists(cache):
        z = np.load(cache); return {k: z[k] for k in z.files}
    if stem == "uk100gbp":
        b, a = _read(os.path.join(D, "v38", "uk100gbp_bid_5m.csv")), _read(os.path.join(D, "v38", "uk100gbp_ask_5m.csv"))
    else:
        b, a = _read(os.path.join(D, "v24", f"{stem}_bid_15m.csv")), _read(os.path.join(D, "v24", f"{stem}_ask_15m.csv"))
    ks = sorted(k for k in b if k in a)
    t = np.array(ks, dtype="datetime64[m]")
    B = np.array([b[k] for k in ks]); A = np.array([a[k] for k in ks]); M = (B + A) / 2
    spr = (A[:, 0] / B[:, 0] - 1) * 1e4
    if stem == "uk100gbp":
        g = (t.astype("int64") // 15) * 15
        u, start = np.unique(g, return_index=True)
        end = np.r_[start[1:], len(g)]
        o = M[start, 0]; c = M[end - 1, 3]
        h = np.maximum.reduceat(M[:, 1], start); l = np.minimum.reduceat(M[:, 2], start)
        t = u.astype("datetime64[m]"); spr = spr[start]
    else:
        o, h, l, c = M[:, 0], M[:, 1], M[:, 2], M[:, 3]
    os.makedirs(os.path.join(D, "v51"), exist_ok=True)
    np.savez(cache, t=t, o=o, h=h, l=l, c=c, spr=spr)
    return dict(t=t, o=o, h=h, l=l, c=c, spr=spr)


def swings(h, l, k):
    """Fractal pivots of width k. Returns arrays (is_sh, is_sl) indexed at the pivot bar;
    a pivot at bar i is only KNOWN at bar i+k (confirmation)."""
    n = len(h); sh = np.zeros(n, bool); sl = np.zeros(n, bool)
    from numpy.lib.stride_tricks import sliding_window_view as sw
    if n > 2 * k:
        Wh = sw(h, 2 * k + 1); Wl = sw(l, 2 * k + 1); mid = Wh[:, k]
        left_h = Wh[:, :k].max(1); right_h = Wh[:, k + 1:].max(1)
        left_l = Wl[:, :k].min(1); right_l = Wl[:, k + 1:].min(1)
        sh[k:n - k] = (Wh[:, k] > left_h) & (Wh[:, k] >= right_h)
        sl[k:n - k] = (Wl[:, k] < left_l) & (Wl[:, k] <= right_l)
    return sh, sl


def structure_events(h, l, c, k):
    """Causal BOS / CHoCH on closes. Uses only pivots confirmed by bar j (pivot index <= j-k).
    Returns list of (bar j, kind 'BOS'|'CHOCH', direction +1/-1). Each swing level can be broken once.
    State starts undefined; the first break sets it and is not counted."""
    sh, sl = swings(h, l, k); n = len(c)
    lastH = lastL = None; usedH = usedL = True; state = 0; ev = []
    for j in range(n):
        p = j - k
        if p >= 0:
            if sh[p]: lastH, usedH = h[p], False
            if sl[p]: lastL, usedL = l[p], False
        if lastH is not None and not usedH and c[j] > lastH:
            if state != 0: ev.append((j, "BOS" if state == 1 else "CHOCH", 1))
            state, usedH = 1, True
        elif lastL is not None and not usedL and c[j] < lastL:
            if state != 0: ev.append((j, "BOS" if state == -1 else "CHOCH", -1))
            state, usedL = -1, True
    return ev
