"""
verify.py — sanity checks on the two experiments, so the negatives are
believable rather than merely convenient.

1. Is the shape detector actually finding compressions? (If it is not, B3/B4
   measured nothing.)
2. Does volatility actually expand after a detected compression, at the
   horizon where the pattern is supposed to pay?
3. Are the A4 retrain-frequency differences bigger than the noise? Paired
   per-market differences, which cancel the common market factor.
4. Lookahead audit: does shifting every signal one more bar change anything?
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import core
import b1_shapes as B


def check_detector():
    print("=" * 78)
    print("1-2. Is the detector finding real compressions, and does vol expand after?")
    print("=" * 78)
    rows = []
    for m in core.MARKETS:
        df = core.load(m)
        ev = B.detect(df)
        r = df["close"].pct_change()
        v21 = r.rolling(21).std()
        fwd21 = v21.shift(-21)
        idx = ev.t.values
        rows.append(dict(
            market=m, n=len(idx),
            vol_at_detect=v21.iloc[idx].mean(),
            vol_uncond=v21.mean(),
            ratio_before=v21.iloc[idx].mean() / v21.mean(),
            vol_after_detect=fwd21.iloc[idx].mean(),
            expansion=fwd21.iloc[idx].mean() / v21.iloc[idx].mean(),
            expansion_uncond=(fwd21 / v21).mean(),
        ))
    t = pd.DataFrame(rows)
    print(t.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print(f"\n  compression check: 21d vol at detection is "
          f"{t.ratio_before.mean():.2f}x the unconditional level "
          f"(< 1 means the detector really is firing in quiet markets)")
    print(f"  expansion check:   vol over the NEXT 21d is "
          f"{t.expansion.mean():.2f}x the vol at detection, against "
          f"{t.expansion_uncond.mean():.2f}x unconditionally")


def check_a4_noise():
    print("\n" + "=" * 78)
    print("3. A4 differences vs noise — paired per-market Sharpe differences")
    print("=" * 78)
    import a4_retrain as A4
    keep = {"never_gridmean": None, "expanding_252": ("expanding", 252),
            "roll252_63": (252, 63), "roll63_21": (63, 21),
            "roll1008_252": (1008, 252)}
    per = {k: [] for k in keep}
    for m in core.MARKETS:
        df = core.load(m)
        R = core.pair_returns(df).dropna(how="all")
        per["never_gridmean"].append(core.sharpe(R.mean(axis=1)))
        for k, spec in keep.items():
            if spec is None:
                continue
            per[k].append(core.sharpe(A4.selection_series(R, spec[0], spec[1])))
    P = pd.DataFrame(per, index=core.MARKETS)
    print(P.to_string(float_format=lambda x: f"{x:+.3f}"))
    base = P["never_gridmean"]
    print()
    for k in P.columns:
        if k == "never_gridmean":
            continue
        d = P[k] - base
        se = d.std() / np.sqrt(len(d))
        print(f"  {k:<14} mean diff vs never-retrain {d.mean():+.3f}  "
              f"SE {se:.3f}  t {d.mean()/se:+.2f}")


def check_lookahead():
    print("\n" + "=" * 78)
    print("4. Lookahead audit — one extra bar of delay on every position")
    print("=" * 78)
    for m in ("xauusd", "spx500usd"):
        df = core.load(m)
        pos = core.pair_positions(df["close"])[core.CENTRE_PAIR]
        a = core.sharpe(pos * df["ret"])
        b = core.sharpe(pos.shift(1) * df["ret"])
        print(f"  {m:<10} as run {a:+.3f}   one bar later {b:+.3f}   "
              f"delta {b-a:+.3f}")
    print("  (a large drop here would mean the edge lives in the fill bar, "
          "i.e. lookahead; a small one is normal decay)")


if __name__ == "__main__":
    check_detector()
    check_a4_noise()
    check_lookahead()


def check_vol_matched():
    """
    5. The control B4 needs: wedge days are quiet days, and quiet days mean-revert
       upward in volatility anyway. So compare each detection only against
       NON-detection days in the same market, same era and same volatility decile.
    """
    print("\n" + "=" * 78)
    print("5. Vol-matched control for the compression claim")
    print("=" * 78)
    rows = []
    for m in core.MARKETS:
        df = core.load(m)
        ev = B.detect(df)
        r = df["close"].pct_change()
        v21 = r.rolling(21).std()
        fwd_v = v21.shift(-21)
        fwd_ret = df["close"].shift(-21) / df["close"] - 1.0
        era = core.era_of(df.index)
        d = pd.DataFrame({"v": v21, "fv": fwd_v, "fr": fwd_ret, "era": era}).dropna()
        d["dec"] = d.groupby("era", observed=True).v.transform(
            lambda s: pd.qcut(s, 10, labels=False, duplicates="drop"))
        flag = pd.Series(False, index=df.index)
        flag.iloc[ev.t.values] = True
        near = flag.rolling(43, center=True, min_periods=1).max().astype(bool)
        d["hit"] = flag.reindex(d.index).fillna(False)
        d["near"] = near.reindex(d.index).fillna(False)
        d["exp"] = d.fv / d.v
        d["norm"] = d.fr.abs() / (d.v * np.sqrt(21))
        hits = d[d.hit]
        ctrl = d[~d.near]
        key = ["era", "dec"]
        cm = ctrl.groupby(key, observed=True)[["exp", "norm"]].mean()
        j = hits.join(cm, on=key, rsuffix="_ctrl").dropna()
        rows.append(dict(market=m, n=len(j),
                         exp_pattern=j.exp.mean(), exp_ctrl=j.exp_ctrl.mean(),
                         norm_pattern=j.norm.mean(), norm_ctrl=j.norm_ctrl.mean()))
    t = pd.DataFrame(rows)
    t["exp_diff"] = t.exp_pattern - t.exp_ctrl
    t["norm_ratio"] = t.norm_pattern / t.norm_ctrl
    print(t.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print(f"\n  vol expansion vs vol-matched control: "
          f"{t.exp_diff.mean():+.4f} on average, "
          f"positive in {int((t.exp_diff > 0).sum())}/11 markets")
    print(f"  normalised move size vs control: ratio "
          f"{t.norm_ratio.mean():.3f}, above 1 in "
          f"{int((t.norm_ratio > 1).sum())}/11 markets")
