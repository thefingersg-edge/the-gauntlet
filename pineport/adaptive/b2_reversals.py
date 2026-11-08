"""
B2 — reversal patterns: double tops and bottoms, head and shoulders.

Part B tested converging trendlines only. These are a LEVEL construction, not a
slope one, which is why they might survive the pivot-perturbation gate that the
wedges failed at 41%.

Causal throughout: a pivot at bar i is visible from i+k, confirmation is a close.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import core
from b1_shapes import pivots
from g2_portfolio import all_markets

FWD = 21


def detect(df, k=3, tol=0.03, depth=0.03, min_sep=10, max_sep=120,
           confirm=20, cooldown=10):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    n = len(c)
    hi, lo = pivots(h, l, k)
    hi_c, lo_c = hi + k, lo + k
    ev, last = [], -10 ** 9

    for t in range(max_sep + 4 * k, n - FWD):
        if t - last < cooldown:
            continue
        H = hi[(hi_c <= t) & (hi >= t - max_sep)]
        L = lo[(lo_c <= t) & (lo >= t - max_sep)]
        kind = prior = None

        # --- double top: two highs at a level, close breaks the trough -----
        if len(H) >= 2 and len(L) >= 1:
            a, b = H[-2], H[-1]
            if min_sep <= b - a <= max_sep and abs(h[b] - h[a]) / h[a] <= tol:
                mid = L[(L > a) & (L < b)]
                if len(mid):
                    m = mid[np.argmin(l[mid])]
                    if (min(h[a], h[b]) - l[m]) / l[m] >= depth and \
                       t - b <= confirm and c[t] < l[m]:
                        kind, prior = "double_top", -1.0

        # --- double bottom -------------------------------------------------
        if kind is None and len(L) >= 2 and len(H) >= 1:
            a, b = L[-2], L[-1]
            if min_sep <= b - a <= max_sep and abs(l[b] - l[a]) / l[a] <= tol:
                mid = H[(H > a) & (H < b)]
                if len(mid):
                    m = mid[np.argmax(h[mid])]
                    if (h[m] - max(l[a], l[b])) / h[m] >= depth and \
                       t - b <= confirm and c[t] > h[m]:
                        kind, prior = "double_bottom", +1.0

        # --- head and shoulders: 3 highs, middle highest, neckline break ---
        if kind is None and len(H) >= 3 and len(L) >= 2:
            p1, p2, p3 = H[-3], H[-2], H[-1]
            if h[p2] > h[p1] and h[p2] > h[p3] and \
               abs(h[p3] - h[p1]) / h[p1] <= tol and min_sep <= p3 - p1 <= max_sep:
                neck = L[(L > p1) & (L < p3)]
                if len(neck) >= 2:
                    nl = float(np.mean(l[neck]))
                    if (h[p2] - nl) / nl >= depth and t - p3 <= confirm and c[t] < nl:
                        kind, prior = "head_shoulders", -1.0

        if kind is None and len(L) >= 3 and len(H) >= 2:
            p1, p2, p3 = L[-3], L[-2], L[-1]
            if l[p2] < l[p1] and l[p2] < l[p3] and \
               abs(l[p3] - l[p1]) / l[p1] <= tol and min_sep <= p3 - p1 <= max_sep:
                neck = H[(H > p1) & (H < p3)]
                if len(neck) >= 2:
                    nl = float(np.mean(h[neck]))
                    if (nl - l[p2]) / nl >= depth and t - p3 <= confirm and c[t] > nl:
                        kind, prior = "inv_head_shoulders", +1.0

        if kind is None:
            continue
        vol = pd.Series(c).pct_change().rolling(63).std().values[t]
        ev.append(dict(t=t, date=df.index[t], kind=kind, prior=prior,
                       fwd=c[t + FWD] / c[t] - 1.0, vol=vol))
        last = t
    return pd.DataFrame(ev)


def main():
    mkts = all_markets()
    allev, base = [], []
    for m in mkts:
        df = core.load(m)
        e = detect(df)
        if len(e):
            e["market"] = m
            e["era"] = [next((n for n, (a, b) in core.ERAS.items()
                              if pd.Timestamp(a, tz="UTC") <= d <= pd.Timestamp(b, tz="UTC")),
                             None) for d in e.date]
            allev.append(e)
        c = df["close"]
        base.append(pd.DataFrame({
            "fwd": c.shift(-FWD) / c - 1.0,
            "vol": c.pct_change().rolling(63).std(),
            "era": core.era_of(df.index), "market": m}).dropna())
    E = pd.concat(allev, ignore_index=True).dropna(subset=["vol", "fwd"])
    B = pd.concat(base, ignore_index=True)

    print("=" * 90)
    print(f"{len(E)} detections across {E.market.nunique()} markets, "
          f"{E.date.min().date()} -> {E.date.max().date()}")
    print(E.groupby("kind").size().to_string())
    print("per era:", E.groupby("era").size().to_dict(), " [gate 2: >=30 each]")

    print("\n" + "=" * 90)
    print("GATE 3/4 — 21-day forward return signed by the textbook call")
    print("=" * 90)
    r = E.prior * E.fwd
    rows = []
    for e in list(core.ERAS) + ["ALL"]:
        m = slice(None) if e == "ALL" else (E.era == e).values
        x = r[m]
        rows.append(dict(era=e, n=len(x), mean=x.mean(),
                         t=x.mean() / (x.std() / np.sqrt(max(len(x), 1)))))
    print(pd.DataFrame(rows).to_string(index=False, formatters={
        "mean": "{:+.4f}".format, "t": "{:+.2f}".format}))
    per = E.assign(r=r).groupby("market").r.mean()
    print(f"  unconditional 21-day return, same data: {B.fwd.mean():+.4f}")
    print(f"  positive in {int((per > 0).sum())}/{len(per)} markets   "
          f"[gate 3: same sign in 3 eras and >=14/21]")
    print(f"  beats the unconditional in "
          f"{int((per > B.fwd.mean()).sum())}/{len(per)}   [gate 4]")
    print("\n  by pattern:")
    for kind, g in E.groupby("kind"):
        rr = g.prior * g.fwd
        print(f"    {kind:<20} n={len(g):>5}  mean {rr.mean():+.4f}  "
              f"t {rr.mean()/(rr.std()/np.sqrt(len(g))):+.2f}")

    print("\n" + "=" * 90)
    print("GATE 5 — magnitude, against a volatility-matched control")
    print("=" * 90)
    E["norm"] = E.fwd.abs() / (E.vol * np.sqrt(FWD))
    B = B.assign(norm=B.fwd.abs() / (B.vol * np.sqrt(FWD)))
    rows = []
    for e in list(core.ERAS) + ["ALL"]:
        ev = E if e == "ALL" else E[E.era == e]
        bb = B if e == "ALL" else B[B.era == e]
        rows.append(dict(era=e, n=len(ev), pattern=ev.norm.mean(),
                         baseline=bb.norm.mean(),
                         ratio=ev.norm.mean() / bb.norm.mean()))
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    print("\n" + "=" * 90)
    print("GATE 1 — stability under detector perturbation (gold, dates within +/-2 bars)")
    print("=" * 90)
    df = core.load("xauusd")
    b = set(detect(df).t.tolist())
    for name, kw in (("pivot k=2", dict(k=2)), ("pivot k=4", dict(k=4)),
                     ("tol 0.015", dict(tol=0.015)), ("tol 0.045", dict(tol=0.045)),
                     ("depth 0.02", dict(depth=0.02)), ("depth 0.05", dict(depth=0.05))):
        a = set(detect(df, **kw).t.tolist())
        hit = sum(any(abs(x - y) <= 2 for y in a) for x in b)
        print(f"  {name:<12} base {len(b):>4}  alt {len(a):>4}  "
              f"overlap {hit/max(len(b),1):.0%}   [gate: >=80%]")
    E.to_csv("b2_events.csv", index=False)


if __name__ == "__main__":
    main()
