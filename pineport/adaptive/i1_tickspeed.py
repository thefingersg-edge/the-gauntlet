"""
i1_tickspeed.py — does the surviving trend edge live in large-tick markets
and slow signals?  Pre-registered in PREREGISTRATION_TICKSPEED.md.

Everything here is fixed by that document. The predictor terciles were frozen
before any Sharpe was computed by tier.
"""
from __future__ import annotations
import os, glob, json
import numpy as np
import pandas as pd
import core

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.dirname(HERE)
RNG  = np.random.default_rng(20260903)
NSHUF = 2000

PRE  = ("2005-01-01", "2008-12-31")
POST = ("2009-01-01", "2026-12-31")

# exchange tick of the underlying, in OANDA quote units (see prereg)
EX_TICK = {"spx500usd":0.25, "nas100usd":0.25, "de30eur":1.0,
           "cornusd":0.0025, "wheatusd":0.0025, "sugarusd":0.0001,
           "natgasusd":0.001, "bcousd":0.01, "usb10yusd":1/64,
           "de10ybeur":0.01}


def markets() -> list[str]:
    return sorted(os.path.basename(p).replace("_d1.csv", "")
                  for p in glob.glob(os.path.join(core.DATA, "*_d1.csv")))


def cut(x, lo, hi):
    return x.loc[str(lo):str(hi)]


# ---------------------------------------------------------------- predictor
def tick_table(mkts, vol_window=None, use_exchange=True) -> pd.DataFrame:
    """vol_window=None -> full sample vol (shares a term with Sharpe);
       vol_window=PRE   -> disjoint-sample vol, gate G1."""
    rows = []
    for m in mkts:
        h1 = os.path.join(SRC, f"{m}_oanda_h1.csv")
        c = pd.read_csv(h1, usecols=["close"])["close"].values
        d = np.abs(np.diff(c)); d = d[d > 0]
        oanda = float(np.min(d))
        tick = EX_TICK.get(m, oanda) if use_exchange else oanda
        px = float(np.median(c))
        close = core.load(m)["close"]
        if vol_window:
            close = cut(close, *vol_window)
        sd = float(np.log(close).diff().std())
        rows.append(dict(mkt=m, tick=tick, oanda_tick=oanda, px=px, sd=sd,
                         tps=sd * px / tick))
    t = pd.DataFrame(rows).set_index("mkt").sort_values("tps")
    t["tier"] = pd.qcut(t["tps"], 3, labels=["LARGE", "MID", "SMALL"])
    return t


# ---------------------------------------------------------------- outcome
def sharpe_panel(mkts, window, cost_bps=1.0) -> pd.DataFrame:
    """rows = markets, cols = (fast,slow) pairs, values = Sharpe."""
    out = {}
    for m in mkts:
        df = core.load(m)
        R = core.pair_returns(df, cost_bps=cost_bps)
        R = cut(R, *window)
        out[m] = {p: core.sharpe(R[p]) for p in R.columns}
    return pd.DataFrame(out).T


# ---------------------------------------------------------------- stats
def spearman(a, b):
    return core.spearman(a, b)


def partial_spearman(y, x, z):
    """rho(y, x | z) on ranks, via the inverse correlation matrix."""
    M = pd.concat([pd.Series(y).rank(), pd.Series(x).rank(),
                   pd.Series(z).rank()], axis=1).dropna()
    C = np.corrcoef(M.values.T)
    inv = np.linalg.inv(C)
    return float(-inv[0, 1] / np.sqrt(inv[0, 0] * inv[1, 1]))


def shuffle_gap(values: pd.Series, tiers: pd.Series, a="LARGE", b="SMALL"):
    """observed mean(a) - mean(b), and its null under tier-label shuffling.
    Markets are the resampled unit — 21 markets are not 21 observations."""
    v = values.reindex(tiers.index).astype(float)
    obs = v[tiers == a].mean() - v[tiers == b].mean()
    lab = tiers.values.copy()
    null = np.empty(NSHUF)
    for i in range(NSHUF):
        RNG.shuffle(lab)
        s = pd.Series(lab, index=tiers.index)
        null[i] = v[s == a].mean() - v[s == b].mean()
    return obs, float(np.percentile(null, 95)), float((null >= obs).mean())


def slope_on_speed(S: pd.DataFrame, mkts) -> float:
    """OLS slope of Sharpe on log2(slow), pooled over the given markets."""
    sub = S.loc[[m for m in mkts if m in S.index]]
    x, y = [], []
    for (f, s) in sub.columns:
        col = sub[(f, s)].dropna()
        x += [np.log2(s)] * len(col); y += list(col.values)
    x, y = np.array(x), np.array(y)
    if len(x) < 10: return np.nan
    return float(np.polyfit(x, y, 1)[0])


# ---------------------------------------------------------------- run
def main():
    mkts = markets()
    T = tick_table(mkts)
    print(f"{len(mkts)} markets | tiers frozen in PREREGISTRATION_TICKSPEED.md\n")
    for tier in ["LARGE", "MID", "SMALL"]:
        print(f"  {tier:6s}: {' '.join(T.index[T.tier == tier])}")

    S_post = sharpe_panel(mkts, POST)
    S_pre  = sharpe_panel(mkts, PRE)
    mean_post = S_post.mean(axis=1)

    print("\n" + "=" * 72)
    print("H1  Sharpe (2009+) vs ticks_per_sd — lower tps = larger tick")
    print("=" * 72)
    rho = spearman(mean_post.reindex(T.index), T.tps)
    print(f"  rho = {rho:+.3f}   (pass requires <= -0.45)")
    obs, p95, pval = shuffle_gap(mean_post, T.tier)
    print(f"  LARGE - SMALL mean Sharpe = {obs:+.4f}   shuffle p95 = {p95:+.4f}"
          f"   p = {pval:.3f}   (pass requires obs > p95)")

    print("\n  per-tier mean Sharpe, 2009+:")
    for tier in ["LARGE", "MID", "SMALL"]:
        v = mean_post.reindex(T.index[T.tier == tier])
        print(f"    {tier:6s} n={len(v):2d}  mean {v.mean():+.4f}  median {v.median():+.4f}")

    print("\n  era sign consistency (E2, E3 computed separately):")
    era_rho = {}
    for name in ["E2_2012_2019", "E3_2019_2026"]:
        a, b = core.ERAS[name]
        r = spearman(sharpe_panel(mkts, (a, b)).mean(axis=1).reindex(T.index), T.tps)
        era_rho[name] = r
        print(f"    {name}: rho = {r:+.3f}")

    print("\n" + "=" * 72)
    print("H2  slope of Sharpe on log2(slow), by tier")
    print("=" * 72)
    slopes = {t: slope_on_speed(S_post, T.index[T.tier == t]) for t in ["LARGE","MID","SMALL"]}
    for t, s in slopes.items():
        print(f"    {t:6s} slope = {s:+.4f} Sharpe per doubling of lookback")
    print(f"  SMALL - LARGE slope gap = {slopes['SMALL'] - slopes['LARGE']:+.4f}"
          f"   (pass requires SMALL > LARGE and gap beyond shuffle p95)")

    print("\n" + "=" * 72)
    print("SHARED-TERM GATE — ticks_per_sd has sd in its numerator,")
    print("Sharpe has sd in its denominator. This is the VRP failure mode.")
    print("=" * 72)
    T_pre = tick_table(mkts, vol_window=PRE)
    g1 = spearman(mean_post.reindex(T_pre.index), T_pre.tps)
    print(f"  G1 disjoint-sample vol (tick from 2005-08 vol, Sharpe from 2009+):")
    print(f"     rho = {g1:+.3f}   vs full-sample {rho:+.3f}")
    g2 = partial_spearman(mean_post.reindex(T.index).values, T.tps.values, T.sd.values)
    print(f"  G2 partial rho(Sharpe, tps | sd) = {g2:+.3f}"
          f"   (must keep sign and >= half of {abs(rho):.3f})")
    g3 = spearman(mean_post.reindex(T.index), T.sd)
    print(f"  G3 mirror rho(Sharpe, sd) with tick held out = {g3:+.3f}")
    print(f"     -> if |{g3:+.3f}| >= |{rho:+.3f}| the tick term is decoration")

    print("\n" + "=" * 72)
    print("H3  pre-2009 vs post-2008 (DECLARED UNDERPOWERED — reported, not scored)")
    print("=" * 72)
    print(f"  pre-break window = 4.0 years, SE(Sharpe) per market ~ 0.50")
    for tier in ["LARGE", "MID", "SMALL"]:
        idx = T.index[T.tier == tier]
        a = S_pre.reindex(idx).mean(axis=1).mean()
        b = S_post.reindex(idx).mean(axis=1).mean()
        print(f"    {tier:6s} pre {a:+.3f} -> post {b:+.3f}   ({b-a:+.3f})")
    print("\n  by signal speed, all markets:")
    for s in sorted({p[1] for p in S_post.columns}):
        cols = [p for p in S_post.columns if p[1] == s]
        print(f"    slow={s:3d} ({s*365.25/257:5.0f} cal days)  "
              f"pre {S_pre[cols].mean().mean():+.3f} -> post {S_post[cols].mean().mean():+.3f}")

    print("\n" + "=" * 72)
    print("ROBUSTNESS")
    print("=" * 72)
    for c in (0.0, 3.0):
        r = spearman(sharpe_panel(mkts, POST, cost_bps=c).mean(axis=1).reindex(T.index), T.tps)
        print(f"  R1 cost {c:.0f}bp: rho = {r:+.3f}")
    To = tick_table(mkts, use_exchange=False)
    print(f"  R2 OANDA-grid tick: rho = {spearman(mean_post.reindex(To.index), To.tps):+.3f}"
          f"   (tier moves: {(To.tier.astype(str) != T.tier.reindex(To.index).astype(str)).sum()}/21)")
    keep = [m for m in T.index if m != "de30eur"]
    print(f"  R3 drop de30eur:    rho = {spearman(mean_post.reindex(keep), T.tps.reindex(keep)):+.3f}")

    verdict = (rho <= -0.45 and obs > p95
               and np.sign(era_rho["E2_2012_2019"]) == np.sign(era_rho["E3_2019_2026"]) == np.sign(rho)
               and abs(g2) >= 0.5 * abs(rho) and np.sign(g2) == np.sign(rho)
               and abs(g3) < abs(rho))
    kill = abs(rho) < 0.20 and (slopes["SMALL"] - slopes["LARGE"]) < 0.02
    print("\n" + "=" * 72)
    print(f"H1 VERDICT: {'PASS' if verdict else 'FAIL'}")
    print(f"KILL CONDITION MET: {kill}"
          f"   ({'stop testing trend variants' if kill else 'trend family not yet exhausted'})")
    print("=" * 72)

    pd.concat([T, mean_post.rename("sharpe_post")], axis=1).to_csv("i1_tickspeed.csv")
    S_post.to_csv("i1_sharpe_post.csv"); S_pre.to_csv("i1_sharpe_pre.csv")


if __name__ == "__main__":
    main()
