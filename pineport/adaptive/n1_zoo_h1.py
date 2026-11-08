"""
n1_zoo_h1.py — the b3 pattern zoo, unchanged, on H1 bars.
Pre-registered in PREREGISTRATION_ZOO_H1.md.

Imports CANDLES() and PIVOTED() from b3_pattern_zoo verbatim so any difference
in result is attributable to the timeframe, not to a new pattern definition.
Bar-count parameters are deliberately not rescaled: PIVOTED's 10-120 bars mean
hours here where they meant days there, which is what "the same pattern on the
H1 chart" means.
"""
from __future__ import annotations
import os, glob
from math import erfc
import numpy as np
import pandas as pd
import core
from b3_pattern_zoo import candle_features, CANDLES, PIVOTED, atr

SRC      = os.path.dirname(core.HERE)
END      = "2026-08-07"
HORIZONS = (6, 24, 120)          # H1 bars: ~6h, ~1 day, ~5 days
NEFF_BLOCS = 5.0                 # cross-market independence, measured elsewhere
SPREAD_BP  = 1.5                 # XAU_USD round-trip, as a fraction of price


def load_h1(mkt: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(SRC, f"{mkt}_oanda_h1.csv"),
                     usecols=["time", "open", "high", "low", "close", "volume"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.set_index("time").sort_index().loc[:END]
    df["ret"] = df["close"].pct_change()
    return df


def thin(idx: np.ndarray, h: int) -> np.ndarray:
    """Keep a detection only if it is >= h bars after the last kept one, so
    forward windows never overlap. Without this, a 120-bar window overlaps its
    neighbour by 119/120 and the t-statistic is meaningless."""
    keep, last = [], -10**9
    for i in idx:
        if i - last >= h:
            keep.append(i); last = i
    return np.array(keep, dtype=int)


def bh(p):
    p = np.asarray(p, float); o = np.argsort(p); q = np.empty_like(p)
    q[o] = np.minimum.accumulate((p[o]*len(p)/(np.arange(len(p))+1))[::-1])[::-1]
    return np.clip(q, 0, 1)


def main():
    mkts = sorted(m for m in (os.path.basename(p).replace("_d1.csv", "")
                              for p in glob.glob(os.path.join(core.DATA, "*_d1.csv")))
                  if os.path.exists(os.path.join(SRC, f"{m}_oanda_h1.csv")))
    print(f"N1 pattern zoo on H1 | {len(mkts)} markets | horizons {HORIZONS} bars")
    print(f"detectors imported unchanged from b3_pattern_zoo\n")

    rows = []
    for m in mkts:
        df = load_h1(m)
        c = df["close"]
        dets = CANDLES(candle_features(df))
        dets.update(PIVOTED(df))
        base = pd.DataFrame({"era": core.era_of(df.index)}, index=df.index)
        base["prior"] = c / c.shift(24) - 1.0                  # 1 day of H1 bars
        base["vol"] = c.pct_change().rolling(24 * 21).std()    # ~21 days
        for hz in HORIZONS:
            base[f"f{hz}"] = c.shift(-hz) / c - 1.0
        base = base.dropna()
        base["pd_"] = base.groupby("era", observed=True).prior.transform(
            lambda s: pd.qcut(s, 5, labels=False, duplicates="drop"))
        base["vd_"] = base.groupby("era", observed=True).vol.transform(
            lambda s: pd.qcut(s, 5, labels=False, duplicates="drop"))
        pos = {t: i for i, t in enumerate(base.index)}

        for name, (mask, d) in dets.items():
            s = pd.Series(mask, index=df.index).reindex(base.index).fillna(False)
            if s.sum() < 20:
                continue
            fire = np.array([pos[t] for t in base.index[s.values]])
            ctrl = base[~s.values].groupby(["era", "pd_", "vd_"], observed=True)[
                [f"f{hz}" for hz in HORIZONS]].mean()
            for hz in HORIZONS:
                kept = thin(fire, hz)
                if len(kept) < 20:
                    continue
                hits = base.iloc[kept].join(ctrl, on=["era", "pd_", "vd_"], rsuffix="_c")
                hits = hits.dropna(subset=[f"f{hz}_c"])
                if len(hits) < 20:
                    continue
                x = d * (hits[f"f{hz}"] - hits[f"f{hz}_c"])
                eras = [float((d*(g[f"f{hz}"]-g[f"f{hz}_c"])).mean())
                        for e in core.ERAS
                        for g in [hits[hits.era == e]] if len(g) >= 10]
                rows.append(dict(pattern=name, market=m, h=hz, dirn=d,
                                 n_raw=int(s.sum()), n=len(x),
                                 eff_bp=float(x.mean()*1e4), sd=float(x.std()),
                                 eras_same=(len(eras) == 3 and
                                            len({np.sign(e) for e in eras}) == 1)))
    D = pd.DataFrame(rows)
    print(f"{len(D)} pattern x market x horizon cells; "
          f"{D.pattern.nunique()} distinct patterns\n")

    out = []
    for (p, hz), g in D.groupby(["pattern", "h"]):
        n = int(g.n.sum())
        eff = float((g.eff_bp * g.n).sum() / n)                     # n-weighted bp
        sd  = float(np.sqrt((g.sd**2 * g.n).sum() / n)) * 1e4
        n_eff = n * (NEFF_BLOCS / max(g.market.nunique(), 1))
        t = eff / (sd / np.sqrt(max(n_eff, 2))) if sd > 0 else np.nan
        out.append(dict(pattern=p, h=hz, markets=g.market.nunique(), n=n,
                        n_eff=int(n_eff), eff_bp=eff, t=t,
                        p=erfc(abs(t)/np.sqrt(2)) if np.isfinite(t) else 1.0,
                        eras_same=bool(g.eras_same.all())))
    R = pd.DataFrame(out).sort_values("p")
    R["q"] = bh(R.p.values)
    R["beats_cost"] = R.eff_bp.abs() > 2 * SPREAD_BP
    R["PASS"] = (R.t.abs() >= 3.0) & (R.q < 0.05) & R.eras_same & R.beats_cost
    R.to_csv("n1_zoo_h1.csv", index=False)

    print("=" * 96)
    print(f"{len(R)} pattern x horizon tests, BH-corrected   "
          f"(cost bar: |effect| > {2*SPREAD_BP:.1f}bp)")
    print("=" * 96)
    print(R.head(12).to_string(index=False, float_format=lambda v: f"{v:9.3f}"))
    n_raw05 = int((R.p < 0.05).sum()); expect = 0.05 * len(R)
    print(f"\n  max |t| {R.t.abs().max():.2f}   min q {R.q.min():.4f}")
    print(f"  patterns at uncorrected p<0.05: {n_raw05}  (chance expects {expect:.1f})")
    print(f"  clearing the cost bar at all  : {int(R.beats_cost.sum())}")
    print(f"  PASSING ALL FIVE CRITERIA     : {int(R.PASS.sum())}")

    promise = bool(R.PASS.any())
    secondary = n_raw05 > 2 * expect
    print("\n" + "=" * 96)
    print(f"N1 VERDICT: {'PASS' if promise else 'FAIL'}")
    print(f"PROMISE (extend to other timeframes): {promise}")
    print(f"  secondary aggregate signal: {secondary} "
          f"({n_raw05} vs 2x{expect:.1f} expected)")
    print("=" * 96)


if __name__ == "__main__":
    main()
