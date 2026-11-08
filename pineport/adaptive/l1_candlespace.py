"""
l1_candlespace.py — discovered candle geometry.
Pre-registered in PREREGISTRATION_CANDLESPACE.md.

Inverts every earlier pattern test: instead of scoring a NAMED shape, let
k-means propose the vocabulary from ATR-normalised OHLC, then score what it
proposes on a held-out era.

The prior literature's failure mode is that naive clustering rediscovers
volatility. Guarded by construction (ATR normalisation, no vol/trend feature)
and by gate G1, which can withdraw the whole run.
"""
from __future__ import annotations
import os, glob
from math import erfc
import numpy as np
import pandas as pd
import core

RNG = np.random.default_rng(20260905)
END = "2026-08-07"
TRAIN_END, TEST_START = "2019-06-30", "2019-07-01"
KS, HORIZONS, WINDOWS = (6, 10, 16, 24), (1, 5, 21), (1, 2, 3)
SEEDS = 5
FIT_N = 20000     # rows used to fit centroids; assignment uses everything


def atr(df, n=14):
    tr = pd.concat([df.high - df.low,
                    (df.high - df.close.shift()).abs(),
                    (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()


def features(mkt, k):
    """ATR-normalised geometry of the last k candles. Causal: A is measured
    at the bar BEFORE the window opens, so nothing inside the window scales
    itself."""
    df = core.load(mkt).loc[:END]
    A = atr(df).shift(k).replace(0, np.nan)
    cols = {}
    for i in range(k):
        s = -(k - 1 - i)                       # s = -(k-1) .. 0
        o, h, l, c = (df[x].shift(-s) if s else df[x] for x in ("open","high","low","close"))
        cols[f"body{i}"]  = (c - o) / A
        cols[f"upper{i}"] = (h - np.maximum(o, c)) / A
        cols[f"lower{i}"] = (np.minimum(o, c) - l) / A
        if i:
            cols[f"gap{i}"] = (o - df["close"].shift(-s + 1)) / A
    X = pd.DataFrame(cols, index=df.index)
    aux = pd.DataFrame({"ret": df["ret"],
                        "prior": np.log(df.close).diff(21),
                        "vol": df["ret"].rolling(63).std()}, index=df.index)
    for h in HORIZONS:
        aux[f"f{h}"] = np.log(df.close).shift(-h) - np.log(df.close)
    aux["era"] = core.era_of(df.index)
    aux["mkt"] = mkt
    return X, aux


def build(k):
    Xs, As = [], []
    for m in sorted(os.path.basename(p).replace("_d1.csv","")
                    for p in glob.glob(os.path.join(core.DATA, "*_d1.csv"))):
        X, a = features(m, k)
        keep = X.notna().all(axis=1) & a[["prior","vol"]].notna().all(axis=1)
        Xs.append(X[keep]); As.append(a[keep])
    X = pd.concat(Xs); A = pd.concat(As)
    A["pd_"] = A.groupby("era", observed=True).prior.transform(
        lambda s: pd.qcut(s, 5, labels=False, duplicates="drop"))
    A["vd_"] = A.groupby("era", observed=True).vol.transform(
        lambda s: pd.qcut(s, 5, labels=False, duplicates="drop"))
    return X, A


def kmeans(X, k, seed, iters=30):
    """Plain Lloyd's with k-means++ seeding — no sklearn dependency.
    Fitted on a subsample; the returned centroids are then applied to all."""
    rng = np.random.default_rng(seed)
    if len(X) > FIT_N:
        X = X[rng.choice(len(X), FIT_N, replace=False)]
    C = [X[rng.integers(len(X))]]
    for _ in range(k - 1):
        d = np.min(((X[:, None, :] - np.array(C)[None]) ** 2).sum(-1), axis=1)
        C.append(X[rng.choice(len(X), p=d / d.sum())])
    C = np.array(C)
    for _ in range(iters):
        lab = ((X[:, None, :] - C[None]) ** 2).sum(-1).argmin(1)
        new = np.array([X[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)])
        if np.allclose(new, C): break
        C = new
    return C, lab


def assign(X, C, chunk=20000):
    out = np.empty(len(X), dtype=int)
    for i in range(0, len(X), chunk):
        b = X[i:i+chunk]
        out[i:i+chunk] = ((b[:, None, :] - C[None]) ** 2).sum(-1).argmin(1)
    return out


def cramers_v(a, b):
    # 21 markets concatenated share dates, so the index has duplicate labels
    # and crosstab cannot align on it. Strip to positional arrays.
    ct = pd.crosstab(pd.Series(np.asarray(a)), pd.Series(np.asarray(b))).values
    chi2 = ((ct - ct.sum(1, keepdims=True) * ct.sum(0, keepdims=True) / ct.sum()) ** 2
            / (ct.sum(1, keepdims=True) * ct.sum(0, keepdims=True) / ct.sum())).sum()
    n = ct.sum()
    return float(np.sqrt(chi2 / (n * (min(ct.shape) - 1))))


def bh(p):
    p = np.asarray(p); o = np.argsort(p); q = np.empty_like(p)
    q[o] = np.minimum.accumulate((p[o] * len(p) / (np.arange(len(p)) + 1))[::-1])[::-1]
    return np.clip(q, 0, 1)


def main():
    print("L1 discovered candle geometry — pre-registered "
          "PREREGISTRATION_CANDLESPACE.md\n")
    all_p, rows = [], []
    for k in WINDOWS:
        X, A = build(k)
        tr = A.index <= pd.Timestamp(TRAIN_END, tz="UTC")
        te = A.index >= pd.Timestamp(TEST_START, tz="UTC")
        mu, sd = X[tr].mean(), X[tr].std().replace(0, 1)
        Z = ((X - mu) / sd).values
        print(f"window k={k}: {X.shape[1]} dims, {tr.sum():,} train rows, {te.sum():,} test rows")
        for nk in KS:
            C, _ = kmeans(Z[tr], nk, seed=0)
            lab = assign(Z, C)
            A["cl"] = lab
            v_vol = cramers_v(A["cl"].values[te], A["vd_"].values[te])
            v_mkt = cramers_v(A["cl"].values[te], A["mkt"].values[te])
            # stability: re-cluster under 5 seeds, mean best-match overlap
            ov = []
            for s in range(1, SEEDS + 1):
                C2, _ = kmeans(Z[tr], nk, seed=s)
                l2 = assign(Z, C2)
                ct = pd.crosstab(pd.Series(np.asarray(lab)), pd.Series(np.asarray(l2))).values
                ov.append((ct.max(1) / ct.sum(1)).mean())
            stab = float(np.mean(ov))
            print(f"   k={nk:2d}  G1 vol V={v_vol:.3f}  G2 mkt V={v_mkt:.3f}  "
                  f"stability={stab:.2f}" + ("   <-- G1 BREACH" if v_vol >= 0.25 else ""))
            for cl in range(nk):
                m = te & (A.cl == cl).values
                if m.sum() < 200: continue
                sub = A[m]
                ctrl = A[te & (A.cl != cl).values].groupby(
                    ["era","pd_","vd_"], observed=True)[[f"f{h}" for h in HORIZONS]].mean()
                j = sub.join(ctrl, on=["era","pd_","vd_"], rsuffix="_c")
                for h in HORIZONS:
                    d = (j[f"f{h}"] - j[f"f{h}_c"]).dropna()
                    if len(d) < 200: continue
                    # rows are not observations: deflate by the market-bloc
                    # ratio, N_eff ~5 against however many markets contributed
                    n_eff = len(d) * (5.0 / max(sub.mkt.nunique(), 1))
                    t = d.mean() / (d.std() / np.sqrt(max(n_eff, 2)))
                    p = erfc(abs(t) / np.sqrt(2))
                    all_p.append(p)
                    rows.append(dict(win=k, k=nk, cl=cl, h=h, n=len(d),
                                     eff=d.mean(), t=t, p=p, stab=stab,
                                     v_vol=v_vol, v_mkt=v_mkt))
    R = pd.DataFrame(rows)
    R["q"] = bh(R.p.values)
    R["pass"] = (R.t.abs() >= 3.0) & (R.q < 0.05) & (R.stab >= 0.80) & (R.v_vol < 0.25)
    R.to_csv("l1_candlespace.csv", index=False)

    print(f"\n{'='*70}\n{len(R)} cluster x horizon x k tests, BH-corrected")
    print(f"{'='*70}")
    print(f"  G1 vol-capture breached at: {sorted(R.loc[R.v_vol>=0.25,['win','k']].apply(tuple,axis=1).unique()) or 'nowhere'}")
    print(f"  max |t| = {R.t.abs().max():.2f}   min q = {R.q.min():.4f}")
    print(f"  stability range {R.stab.min():.2f} - {R.stab.max():.2f}  (pass needs >= 0.80)")
    print(f"  clusters passing ALL criteria: {int(R['pass'].sum())}")
    if R['pass'].any():
        print(R[R['pass']].sort_values('q').head(12).to_string(index=False))
    print(f"\n{'='*70}")
    print(f"L1 VERDICT: {'PASS' if R['pass'].any() else 'FAIL — no discovered shape survives'}")
    print(f"KILL CONDITION MET: {not R['pass'].any()}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
