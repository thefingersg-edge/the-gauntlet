"""
B — do converging-trendline shapes (wedges, triangles) carry information?

Detection is fully causal: a swing pivot at bar i is only visible from bar i+k,
and every trendline is fitted to pivots already confirmed at the decision bar.

Two claims are tested separately, because they are different claims:
    B3 DIRECTION  — does the textbook direction of the shape predict the sign
                    of the next 21 days?
    B4 MAGNITUDE  — does the compression predict the SIZE of the next 21 days,
                    relative to the volatility going in?

and one gate is applied before either:
    B1 STABILITY  — do the detections survive perturbing the detector?
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import core

FWD = 21


def pivots(h: np.ndarray, l: np.ndarray, k: int):
    """indices of swing highs/lows; a pivot at i is CONFIRMED at i+k."""
    n = len(h)
    hi, lo = [], []
    for i in range(k, n - k):
        w = slice(i - k, i + k + 1)
        if h[i] == h[w].max() and (h[w] == h[i]).sum() == 1:
            hi.append(i)
        if l[i] == l[w].min() and (l[w] == l[i]).sum() == 1:
            lo.append(i)
    return np.array(hi), np.array(lo)


def fit(idx, val):
    x = np.asarray(idx, dtype=float)
    y = np.asarray(val, dtype=float)
    b = ((x - x.mean()) * (y - y.mean())).sum() / max(((x - x.mean()) ** 2).sum(), 1e-12)
    return b, y.mean() - b * x.mean()


def detect(df: pd.DataFrame, k=3, conv=0.7, lookback=120, cooldown=10):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    n = len(c)
    hi, lo = pivots(h, l, k)
    hi_conf, lo_conf = hi + k, lo + k          # bar at which each becomes visible
    events = []
    last = -10 ** 9
    for t in range(lookback + 4 * k, n - FWD):
        if t - last < cooldown:
            continue
        H = hi[(hi_conf <= t) & (hi >= t - lookback)]
        L = lo[(lo_conf <= t) & (lo >= t - lookback)]
        if len(H) < 3 or len(L) < 3:
            continue
        H, L = H[-3:], L[-3:]
        bh, ah = fit(H, h[H])
        bl, al = fit(L, l[L])
        start = min(H[0], L[0])
        gap0 = (ah + bh * start) - (al + bl * start)
        gap1 = (ah + bh * t) - (al + bl * t)
        if gap0 <= 0 or gap1 <= 0 or gap1 >= conv * gap0:
            continue                            # not converging enough
        span = t - start
        if span < 20:
            continue
        # classify
        sh, sl = np.sign(bh), np.sign(bl)
        if bh < 0 and bl > 0:
            kind, prior = "sym_triangle", np.sign(c[t] - c[max(t - 120, 0)])
        elif bh > 0 and bl > 0:
            kind, prior = "rising_wedge", -1.0
        elif bh < 0 and bl < 0:
            kind, prior = "falling_wedge", +1.0
        else:
            kind, prior = "other", 0.0
        if prior == 0:
            continue
        upper, lower = ah + bh * t, al + bl * t
        brk = +1.0 if c[t] > upper else (-1.0 if c[t] < lower else 0.0)
        vol = pd.Series(c).pct_change().rolling(63).std().values[t]
        fwd = c[t + FWD] / c[t] - 1.0
        events.append(dict(t=t, date=df.index[t], kind=kind, prior=prior,
                           breakout=brk, fwd=fwd, vol=vol, span=span,
                           compression=gap1 / gap0))
        last = t
    return pd.DataFrame(events)


def baseline(df: pd.DataFrame):
    c = df["close"]
    fwd = c.shift(-FWD) / c - 1.0
    vol = c.pct_change().rolling(63).std()
    return fwd, vol


def main():
    all_ev, base_rows = {}, {}
    for m in core.MARKETS:
        df = core.load(m)
        ev = detect(df)
        ev["market"] = m
        ev["era"] = [next((n for n, (a, b) in core.ERAS.items()
                           if pd.Timestamp(a, tz="UTC") <= d <= pd.Timestamp(b, tz="UTC")),
                          None) for d in ev.date]
        all_ev[m] = ev
        fwd, vol = baseline(df)
        base_rows[m] = pd.DataFrame({"fwd": fwd, "vol": vol,
                                     "era": core.era_of(df.index)}).dropna()
    E = pd.concat(all_ev.values(), ignore_index=True).dropna(subset=["vol", "fwd"])
    B = pd.concat(base_rows.values(), keys=base_rows.keys(), names=["market"])

    print("=" * 78)
    print(f"Detections: {len(E)} across 11 markets, "
          f"{E.date.min().date()} -> {E.date.max().date()}")
    print(E.groupby(["kind"]).size().to_string())
    print("\nper era:", E.groupby("era").size().to_dict(),
          "   [B2 gate: >= 30 per era]")

    # ---------------- B3 direction ----------------
    print("\n" + "=" * 78)
    print("B3 DIRECTION — mean 21d forward return signed by the textbook call")
    print("=" * 78)
    for label, sig in (("pattern prior", E.prior),
                       ("breakout direction", E.breakout)):
        sub = E[sig != 0]
        s = sig[sig != 0]
        r = (s * sub.fwd)
        rows = []
        for e in core.ERAS:
            m = (sub.era == e).values
            rows.append(dict(era=e, n=int(m.sum()), mean=r[m].mean(),
                             t=r[m].mean() / (r[m].std() / np.sqrt(max(m.sum(), 1)))))
        rows.append(dict(era="ALL", n=len(r), mean=r.mean(),
                         t=r.mean() / (r.std() / np.sqrt(len(r)))))
        tab = pd.DataFrame(rows)
        n_mkt = sum(((E[sig != 0].groupby("market")
                      .apply(lambda g: (g.prior if label == "pattern prior"
                                        else g.breakout).mul(g.fwd).mean())) > 0))
        print(f"\n  signal = {label}    baseline unconditional |mean| "
              f"= {B.fwd.mean():+.4f}")
        print(tab.to_string(index=False, formatters={"mean": "{:+.4f}".format,
                                                     "t": "{:+.2f}".format}))
        print(f"  positive in {n_mkt}/11 markets   [B3 gate: same sign in all "
              f"3 eras and >= 7/11 markets]")

    # ---------------- B4 magnitude ----------------
    print("\n" + "=" * 78)
    print("B4 MAGNITUDE — |21d forward return| / prior 63d vol, after "
          "compression vs baseline")
    print("=" * 78)
    E["norm"] = E.fwd.abs() / (E.vol * np.sqrt(FWD))
    B = B.assign(norm=B.fwd.abs() / (B.vol * np.sqrt(FWD)))
    rows = []
    for e in list(core.ERAS) + ["ALL"]:
        ev = E if e == "ALL" else E[E.era == e]
        bb = B if e == "ALL" else B[B.era == e]
        rows.append(dict(era=e, n=len(ev), pattern=ev.norm.mean(),
                         baseline=bb.norm.mean(),
                         ratio=ev.norm.mean() / bb.norm.mean()))
    print(pd.DataFrame(rows).to_string(index=False,
          formatters={"pattern": "{:.3f}".format, "baseline": "{:.3f}".format,
                      "ratio": "{:.3f}".format}))
    per_mkt = E.groupby("market").norm.mean() / B.groupby(level=0).norm.mean()
    print(f"  ratio > 1 in {int((per_mkt > 1).sum())}/11 markets   "
          f"[B4 gate: same sign in all 3 eras and >= 7/11 markets]")
    print("  per market:", per_mkt.round(3).to_dict())

    # ---------------- B1 stability ----------------
    print("\n" + "=" * 78)
    print("B1 STABILITY — detection overlap under detector perturbation "
          "(dates within +/-2 bars)")
    print("=" * 78)
    df = core.load("xauusd")
    base = set(detect(df).t.tolist())
    for name, kw in (("pivot k=2", dict(k=2)), ("pivot k=4", dict(k=4)),
                     ("conv 0.6", dict(conv=0.6)), ("conv 0.8", dict(conv=0.8)),
                     ("lookback 90", dict(lookback=90)),
                     ("lookback 150", dict(lookback=150))):
        alt = set(detect(df, **kw).t.tolist())
        hit = sum(any(abs(a - b) <= 2 for b in alt) for a in base)
        print(f"  {name:<14} base {len(base):>4}  alt {len(alt):>4}  "
              f"overlap {hit/max(len(base),1):.0%}   [gate: >= 80%]")
    E.to_csv("b1_events.csv", index=False)


if __name__ == "__main__":
    main()
