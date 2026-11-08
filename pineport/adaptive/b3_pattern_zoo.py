"""
B3 — the standard pattern taxonomy, scored in full.

Candlestick detectors use no pivots, which is the point: pivots are what killed
Parts B and B2. All thresholds are in ATR multiples (GAUNTLET 1.3).

Every pattern is scored against non-detection days in the same market, era,
prior-return decile AND volatility decile.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import core
from b1_shapes import pivots
from g2_portfolio import all_markets

HORIZONS = (1, 5, 21)


def atr(df, n=14):
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def candle_features(df):
    o, h, l, c = (df[k].values for k in ("open", "high", "low", "close"))
    a = atr(df).values
    body = c - o
    rng = np.maximum(h - l, 1e-12)
    upper = h - np.maximum(o, c)
    lower = np.minimum(o, c) - l
    return dict(o=o, h=h, l=l, c=c, a=a, body=body, absbody=np.abs(body),
                rng=rng, upper=upper, lower=lower)


# --- each detector returns a boolean array and the textbook direction --------
def CANDLES(f):
    o, h, l, c, a = f["o"], f["h"], f["l"], f["c"], f["a"]
    b, ab, rng, up, lo = f["body"], f["absbody"], f["rng"], f["upper"], f["lower"]
    pb, pab = np.roll(b, 1), np.roll(ab, 1)
    po, pc = np.roll(o, 1), np.roll(c, 1)
    big = ab > 0.5 * a
    out = {}
    out["engulf_bull"] = ((pb < 0) & (b > 0) & (c > po) & (o < pc) & big, +1)
    out["engulf_bear"] = ((pb > 0) & (b < 0) & (c < po) & (o > pc) & big, -1)
    out["hammer"] = ((lo > 2 * ab) & (up < 0.3 * ab) & (ab > 0.05 * a)
                     & (np.roll(c, 1) < np.roll(c, 5)), +1)
    out["hanging_man"] = ((lo > 2 * ab) & (up < 0.3 * ab) & (ab > 0.05 * a)
                          & (np.roll(c, 1) > np.roll(c, 5)), -1)
    out["shooting_star"] = ((up > 2 * ab) & (lo < 0.3 * ab) & (ab > 0.05 * a)
                            & (np.roll(c, 1) > np.roll(c, 5)), -1)
    out["inverted_hammer"] = ((up > 2 * ab) & (lo < 0.3 * ab) & (ab > 0.05 * a)
                              & (np.roll(c, 1) < np.roll(c, 5)), +1)
    out["harami_bull"] = ((pb < -0.5 * a) & (np.maximum(o, c) < po)
                          & (np.minimum(o, c) > pc) & (b > 0), +1)
    out["harami_bear"] = ((pb > 0.5 * a) & (np.maximum(o, c) < pc)
                          & (np.minimum(o, c) > po) & (b < 0), -1)
    out["marubozu_bull"] = ((b > 0.7 * rng) & (ab > 0.8 * a), +1)
    out["marubozu_bear"] = ((-b > 0.7 * rng) & (ab > 0.8 * a), -1)
    out["dragonfly_doji"] = ((ab < 0.1 * rng) & (lo > 0.6 * rng), +1)
    out["gravestone_doji"] = ((ab < 0.1 * rng) & (up > 0.6 * rng), -1)
    b2, b1 = np.roll(b, 2), np.roll(b, 1)
    ab2, ab1 = np.roll(ab, 2), np.roll(ab, 1)
    out["morning_star"] = ((b2 < -0.5 * a) & (ab1 < 0.3 * ab2) & (b > 0.5 * a), +1)
    out["evening_star"] = ((b2 > 0.5 * a) & (ab1 < 0.3 * ab2) & (b < -0.5 * a), -1)
    out["three_white_soldiers"] = ((b2 > 0.3 * a) & (b1 > 0.3 * a) & (b > 0.3 * a)
                                   & (c > np.roll(c, 1)), +1)
    out["three_black_crows"] = ((b2 < -0.3 * a) & (b1 < -0.3 * a) & (b < -0.3 * a)
                                & (c < np.roll(c, 1)), -1)
    out["piercing_line"] = ((pb < -0.5 * a) & (o < np.roll(l, 1))
                            & (c > (po + pc) / 2) & (c < po), +1)
    out["dark_cloud"] = ((pb > 0.5 * a) & (o > np.roll(h, 1))
                         & (c < (po + pc) / 2) & (c > po), -1)
    out["gap_up"] = (l > np.roll(h, 1) + 0.1 * a, +1)
    out["gap_down"] = (h < np.roll(l, 1) - 0.1 * a, -1)
    for k in out:
        m, d = out[k]
        m = m.copy(); m[:30] = False
        out[k] = (m, d)
    return out


def PIVOTED(df, k=3, tol=0.03, depth=0.03, lo_bars=10, hi_bars=120, confirm=20):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    n = len(c)
    hi, lo = pivots(h, l, k)
    hic, loc = hi + k, lo + k
    res = {name: (np.zeros(n, bool), d) for name, d in
           (("asc_triangle", +1), ("desc_triangle", -1), ("rectangle", 0),
            ("broadening", 0), ("triple_top", -1), ("triple_bottom", +1),
            ("rounding_bottom", +1))}
    for t in range(hi_bars + 4 * k, n):
        H = hi[(hic <= t) & (hi >= t - hi_bars)]
        L = lo[(loc <= t) & (lo >= t - hi_bars)]
        if len(H) < 2 or len(L) < 2:
            continue
        flat_h = abs(h[H[-1]] - h[H[-2]]) / h[H[-2]] <= tol
        flat_l = abs(l[L[-1]] - l[L[-2]]) / l[L[-2]] <= tol
        rise_l = l[L[-1]] > l[L[-2]] * (1 + tol)
        fall_h = h[H[-1]] < h[H[-2]] * (1 - tol)
        if flat_h and rise_l and c[t] > h[H[-1]]:
            res["asc_triangle"][0][t] = True
        if flat_l and fall_h and c[t] < l[L[-1]]:
            res["desc_triangle"][0][t] = True
        if flat_h and flat_l:
            res["rectangle"][0][t] = True
        if h[H[-1]] > h[H[-2]] * (1 + tol) and l[L[-1]] < l[L[-2]] * (1 - tol):
            res["broadening"][0][t] = True
        if len(H) >= 3 and max(abs(h[H[-1]] - h[H[-2]]), abs(h[H[-2]] - h[H[-3]])) \
                / h[H[-2]] <= tol and c[t] < min(l[L[-2:]]):
            res["triple_top"][0][t] = True
        if len(L) >= 3 and max(abs(l[L[-1]] - l[L[-2]]), abs(l[L[-2]] - l[L[-3]])) \
                / l[L[-2]] <= tol and c[t] > max(h[H[-2:]]):
            res["triple_bottom"][0][t] = True
    win = 60
    cs = pd.Series(c)
    mn = cs.rolling(win).min()
    rb = ((cs.shift(win // 2) <= mn.shift(win // 2) * (1 + tol / 2))
          & (cs > cs.shift(win // 2) * (1 + depth))
          & (cs.shift(win) > cs.shift(win // 2) * (1 + depth))).fillna(False).values
    res["rounding_bottom"] = (rb, +1)
    return {k_: v for k_, v in res.items() if v[1] != 0}


def main():
    mkts = all_markets()
    rows = []
    for m in mkts:
        df = core.load(m)
        c = df["close"]
        f = candle_features(df)
        dets = CANDLES(f)
        dets.update(PIVOTED(df))
        base = pd.DataFrame({"era": core.era_of(df.index)}, index=df.index)
        base["prior"] = c / c.shift(21) - 1.0
        base["vol"] = c.pct_change().rolling(63).std()
        for hz in HORIZONS:
            base[f"f{hz}"] = c.shift(-hz) / c - 1.0
        base = base.dropna()
        base["pd_"] = base.groupby("era", observed=True).prior.transform(
            lambda s: pd.qcut(s, 5, labels=False, duplicates="drop"))
        base["vd_"] = base.groupby("era", observed=True).vol.transform(
            lambda s: pd.qcut(s, 5, labels=False, duplicates="drop"))
        for name, (mask, d) in dets.items():
            s = pd.Series(mask, index=df.index).reindex(base.index).fillna(False)
            if s.sum() < 5:
                continue
            # Control pool = every day the pattern did NOT fire. An earlier
            # version excluded a +/-21 bar WINDOW around each detection; with a
            # pattern firing thousands of times that removes nearly the whole
            # series and leaves cell means computed on a handful of survivors --
            # it reported a +4.67% baseline against a +0.76% unconditional.
            # Overlapping forward windows are the lesser evil than an empty
            # control.
            ctrl = base[~s.values].groupby(["era", "pd_", "vd_"], observed=True)[
                [f"f{hz}" for hz in HORIZONS]].mean()
            hits = base[s.values].join(ctrl, on=["era", "pd_", "vd_"], rsuffix="_c")
            hits = hits.dropna(subset=[f"f{hz}_c" for hz in HORIZONS])
            if not len(hits):
                continue
            r = dict(pattern=name, market=m, dirn=d, n=len(hits))
            for hz in HORIZONS:
                r[f"x{hz}"] = float((d * (hits[f"f{hz}"] - hits[f"f{hz}_c"])).mean())
            for e in core.ERAS:
                g = hits[hits.era == e]
                r[f"e_{e[:2]}"] = float((d * (g["f21"] - g["f21_c"])).mean()) \
                    if len(g) >= 10 else np.nan
            rows.append(r)

    D = pd.DataFrame(rows)
    agg = []
    for p, g in D.groupby("pattern"):
        n = int(g.n.sum())
        row = dict(pattern=p, n=n, markets=len(g))
        for hz in HORIZONS:
            w = (g[f"x{hz}"] * g.n).sum() / g.n.sum()
            row[f"x{hz}"] = w
            row[f"pos{hz}"] = int((g[f"x{hz}"] > 0).sum())
        eras = [g[f"e_{e[:2]}"].mean() for e in core.ERAS]
        row["E1"], row["E2"], row["E3"] = eras
        row["era_consistent"] = bool(np.isfinite(eras).all()
                                     and abs(sum(np.sign(eras))) == 3)
        agg.append(row)
    A = pd.DataFrame(agg).sort_values("x21", ascending=False)

    print("=" * 118)
    print("Controlled excess return, signed by the textbook call, matched on "
          "market / era / prior-return / volatility")
    print("=" * 118)
    show = A[["pattern", "n", "markets", "x1", "x5", "x21", "pos21",
              "E1", "E2", "E3", "era_consistent"]]
    print(show.to_string(index=False, formatters={c: "{:+.4f}".format
          for c in ["x1", "x5", "x21", "E1", "E2", "E3"]}))

    print("\n" + "=" * 118)
    print("GATES — 1: same sign in 3 eras · 2: >=14/21 markets · "
          "3: |excess| >= 0.20% · 4: n >= 200")
    print("=" * 118)
    passed = []
    for _, r in A.iterrows():
        best = max(HORIZONS, key=lambda h: abs(r[f"x{h}"]))
        g1 = r.era_consistent
        g2 = r[f"pos{21}"] >= 14
        g3 = abs(r[f"x{best}"]) >= 0.002
        g4 = r.n >= 200
        if g1 and g2 and g3 and g4:
            passed.append(r.pattern)
        flags = "".join("1" if x else "." for x in (g1, g2, g3, g4))
        if g1 or (g2 and g3):
            print(f"  {r.pattern:<22} n={r.n:>6}  best h{best} {r[f'x{best}']:+.4f}  "
                  f"eras {'Y' if g1 else 'n'}  markets {r['pos21']:>2}/21  gates {flags}")
    print(f"\n  PASSED ALL FOUR: {passed if passed else 'none'}")
    print(f"  patterns tested: {len(A)} · expected false passes under the null: ~0.6")
    A.to_csv("b3_zoo.csv", index=False)


if __name__ == "__main__":
    main()
