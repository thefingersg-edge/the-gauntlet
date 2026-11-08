"""PEAD1 engine: drift after the earnings-announcement return (EAR), by liquidity band, net of estimated costs.
All quantities are point-in-time:
  band(ticker, month)   rank of median 20-day dollar volume before the month starts (price >= $5 at that date)
                        L = top 500, M = next 1000, S = next 2000, X = the rest
  bench(date, band)     equal-weight mean daily return (closeadj) of band members
  EAR                   sum over trading days k-1..k+1 of (r - bench), k = first trading day >= 8-K Item 2.02 date
  known                 at the close of k+1;  entry = OPEN of k+2;  exit = close of k+1+H
  signal                EAR in the top decile of all EARs in the same band known in the prior 91 calendar days (>= 50 of them)
  cost                  EDGE spread from the 60 days before k (band median if missing) + 2 x $0.0035 / price
  delisting             position ends at the last close; non-merger delisting adds -30% (Shumway-style)
I am not a financial adviser. This is a measurement tool, not a recommendation."""
import os, bisect, math
import numpy as np
from collections import defaultdict
import ss_lib

BANDS = (("L", 500), ("M", 1000), ("S", 2000))
COMM = 0.0035


def month_of(d):  # int day(s) since 1970 -> month index since 1970-01 (vectorised)
    return np.asarray(d).astype("datetime64[D]").astype("datetime64[M]").astype(np.int64)


def band_stats(store, files):
    """per (ticker, month): median 20-day dollar volume before the month starts, if price >= $5 at that date."""
    per = defaultdict(list)
    for f in files:
        z = ss_lib.load(store, f); d = z["d"]; dv = z["c"].astype(float) * z["v"].astype(float); cu = z["cu"]
        mo = month_of(d); starts = np.r_[0, np.nonzero(np.diff(mo))[0] + 1]
        for s_ in starts:
            if s_ >= 20 and cu[s_ - 1] >= 5:
                per[int(mo[s_])].append((float(np.median(dv[s_ - 20:s_])), f))
    return per


def assign_bands(per):
    band = {}
    for m, lst in per.items():
        lst.sort(reverse=True); i = 0
        for name, size in BANDS:
            for _, f in lst[i:i + size]: band[(f, m)] = name
            i += size
        for _, f in lst[i:]: band[(f, m)] = "X"
    return band


def pass_bands(store, files):
    return assign_bands(band_stats(store, files))


BIDX = {"L": 0, "M": 1, "S": 2, "X": 3}


def bench_acc(store, files, band, d0, nd):
    """vectorised sums/counts of daily returns per (day offset, band)."""
    S = np.zeros((nd, 4)); C = np.zeros((nd, 4))
    for f in files:
        z = ss_lib.load(store, f); d = z["d"]; ca = z["ca"]
        if len(d) < 2: continue
        r = ca[1:] / ca[:-1] - 1; dd = d[1:]; mo = month_of(dd)
        bi = np.array([BIDX.get(band.get((f, int(m))), -1) for m in mo])
        ok = (bi >= 0) & np.isfinite(r) & (np.abs(r) < 2)
        np.add.at(S, (dd[ok] - d0, bi[ok]), r[ok]); np.add.at(C, (dd[ok] - d0, bi[ok]), 1)
    return S, C


def bench_from(S, C, d0, min_n=5):
    out = {}
    for b, j in BIDX.items():
        idx = np.nonzero(C[:, j] >= min_n)[0]
        for i in idx: out[(int(i + d0), b)] = float(S[i, j] / C[i, j])
    return out


def pass_bench(store, files, band):
    lo = min(int(ss_lib.load(store, f)["d"][0]) for f in files); hi = max(int(ss_lib.load(store, f)["d"][-1]) for f in files)
    S, C = bench_acc(store, files, band, lo, hi - lo + 1)
    return bench_from(S, C, lo)


def pass_events(store, files, band, bench, ann, bad, good, H=(20, 60)):
    byt = defaultdict(list)
    for t, d in ann: byt[t].append(d)
    out = []
    for f in files:
        t = f[:-4]
        if t not in byt: continue
        z = ss_lib.load(store, f); d = z["d"]; ca = z["ca"]; o, h, l, c, cu = z["o"], z["h"], z["l"], z["c"], z["cu"]
        r = np.r_[np.nan, ca[1:] / ca[:-1] - 1]; n = len(d)
        for ad in sorted(set(byt[t])):
            k = bisect.bisect_left(d, ad)
            if k < 61 or k + 2 >= n: continue
            b = band.get((f, int(month_of(d[k]))))
            if b is None: continue
            bm = [bench.get((int(d[j]), b)) for j in (k - 1, k, k + 1)]
            if None in bm or not np.all(np.isfinite(r[k - 1:k + 2])): continue
            ear = float(np.sum(r[k - 1:k + 2]) - sum(bm))
            sp = ss_lib.edge_spread(o[k - 60:k], h[k - 60:k], l[k - 60:k], c[k - 60:k])
            e = k + 2; adj = ca[e] / c[e] if c[e] > 0 else np.nan
            rec = dict(t=t, band=b, ad=int(ad), known=int(d[k + 1]), entry=int(d[e]), ear=ear, spread=sp,
                       comm=2 * COMM / float(cu[k + 1]) if cu[k + 1] > 0 else np.nan)
            for HH in H:
                x = k + 1 + HH; delist = 0.0
                if x >= n:                                     # data ends inside the hold
                    x = n - 1
                    if t in bad and bad[t] <= int(d[-1]) + 30 and t not in good: delist = -0.30
                    if x < e: continue
                gross = (1 + delist) * ca[x] / (o[e] * adj) - 1
                bb = [bench.get((int(d[j]), b), 0.0) for j in range(e, x + 1)]
                rec[f"g{HH}"] = float(gross); rec[f"x{HH}"] = float(gross - (np.prod([1 + v for v in bb]) - 1))
                rec[f"end{HH}"] = int(d[x])
                if HH == max(H):
                    px = np.r_[o[e] * adj, ca[e:x + 1]]; dr = px[1:] / px[:-1] - 1
                    rec["path"] = (dr - np.array(bb)).astype(np.float32)
            out.append(rec)
    return out


def signals(ev, window=91, q=0.9, min_n=50):
    """Top-decile flag using only EARs known strictly before this event's known date, same band, prior 91 days."""
    byb = defaultdict(list)
    for e in ev: byb[e["band"]].append(e)
    for b, L in byb.items():
        L.sort(key=lambda e: e["known"]); ks = [e["known"] for e in L]; ears = [e["ear"] for e in L]
        for i, e in enumerate(L):
            lo = bisect.bisect_left(ks, e["known"] - window); hi = bisect.bisect_left(ks, e["known"])
            pool = ears[lo:hi]
            e["thr"] = float(np.quantile(pool, q)) if len(pool) >= min_n else np.nan
            e["long"] = bool(np.isfinite(e["thr"]) and e["ear"] > e["thr"])
    return ev


def fill_costs(ev):
    med = defaultdict(list)
    for e in ev:
        if np.isfinite(e["spread"]): med[e["band"]].append(e["spread"])
    m = {b: float(np.median(v)) for b, v in med.items()}
    for e in ev:
        e["cost"] = (e["spread"] if np.isfinite(e["spread"]) else m.get(e["band"], 0.01)) + (e["comm"] if np.isfinite(e["comm"]) else 0)
    return ev


def clustered_mean_t(vals, keys):
    vals = np.asarray(vals, float); g = defaultdict(float); n = len(vals)
    if n < 10: return float("nan"), float("nan"), n
    m = vals.mean(); u = vals - m
    for v, k in zip(u, keys): g[k] += v
    se = math.sqrt(sum(s * s for s in g.values())) / n
    return float(m), float(m / se) if se > 0 else float("nan"), n


def week(d): return int(d) // 7


def quarter(d):  # cluster key: calendar quarter of entry (60-day holds overlap within ~a quarter)
    return int(month_of(int(d))) // 3
