#!/usr/bin/env python3
"""audit_v56.py -- independent checks on RESULT_BREADTH_v56, run 2026-10-02 AFTER
the verdict. Descriptive only: they cannot change a frozen result.

  1. alignment: does S5FI/ADD on date t co-move with the S&P on t (correct),
     t-1 (late stamp, harmless) or t+1 (look-ahead)?
  2. reproduction of the registered gate statistics.
  3. rotation null: rotate S5FI against r20 by 2,000 random offsets of at least a
     year. That keeps both series' own autocorrelation, so it asks how often an
     unrelated breadth path of the same shape scores as well.
  4. Newey-West lag sensitivity.

    python3 audit_v56.py
"""
import numpy as np
import breadth_v56 as B, tv_series as TV


def main():
    S = B.sessions(); ds = sorted(S)
    r = {ds[i]: (S[ds[i]][1] / S[ds[i - 1]][1] - 1) * 1e4 for i in range(1, len(ds))}
    print("1. alignment (series change on t vs SPX 15:45->15:45 return on t+k)")
    for name in ("S5FI", "ADD"):
        s = dict(TV.read(name, B.TVD)); sd = sorted(s)
        ch = dict(s) if name == "ADD" else {sd[i]: s[sd[i]] - s[sd[i - 1]] for i in range(1, len(sd))}
        for k in (-1, 0, 1):
            xs, ys = [], []
            for i, d in enumerate(ds):
                j = i + k
                if 0 < j < len(ds) and d in ch and ds[j] in r:
                    xs.append(ch[d]); ys.append(r[ds[j]])
            print(f"   {name:<4} k={k:+d}  corr {np.corrcoef(xs, ys)[0, 1]:+.3f}  n {len(xs)}")
    F = B.fwd(S, 20); s5 = dict(TV.read("S5FI", B.TVD))
    ts = [t for t in sorted(F) if t >= B.START and t in s5]
    y = np.array([F[t][0] for t in ts]); x = np.array([s5[t] / 10 for t in ts]); low = (x < 2).astype(float)
    b, t = B.nw_ols(y, x, 20); bd, td = B.nw_ols(y, low, 20)
    print(f"\n2. reproduced: slope {b[1]:+.2f} bp (NW t {t[1]:+.2f}); low-minus-rest {bd[1]:+.1f} bp (NW t {td[1]:+.2f}); n {len(y)}, n_low {int(low.sum())}")
    rng = np.random.default_rng(56); n = len(y)
    tb, tl = [], []
    for o in rng.integers(252, n - 252, 2000):
        xr = np.roll(x, o)
        tb.append(B.nw_ols(y, xr, 20)[1][1]); tl.append(B.nw_ols(y, (xr < 2).astype(float), 20)[1][1])
    tb, tl = np.array(tb), np.array(tl)
    print(f"\n3. rotation null (2,000 offsets >= 252 sessions, seed 56)")
    print(f"   P(slope t <= {t[1]:.2f}) = {(tb <= t[1]).mean():.3f}   null sd of t {tb.std():.2f}")
    print(f"   P(low t  >= {td[1]:.2f}) = {(tl >= td[1]).mean():.3f}   null sd of t {tl.std():.2f}")
    print("\n4. NW lag sensitivity")
    for L in (20, 40, 60, 120):
        print(f"   lag {L:>3}: slope t {B.nw_ols(y, x, L)[1][1]:+.2f}   low t {B.nw_ols(y, low, L)[1][1]:+.2f}")


if __name__ == "__main__":
    main()
