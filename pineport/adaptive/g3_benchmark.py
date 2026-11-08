"""
G3 — the benchmark correction.

Two errors are fixed here, both found in the benchmark audit:

1. **Sharpe was computed on raw returns, not excess returns.** Every Sharpe in
   this project used mean/sd of the return series with no risk-free subtraction.
   Fed funds averaged 1.86% over 2005-2026, so every number was inflated.

2. **The benchmark was an equal-weight long basket of 21 CFDs, gross of
   funding** -- not a portfolio anyone holds, padded with seven arbitrarily-long
   FX pairs, and unachievable as measured.

Everything below is an EXCESS return over cash. A position of size w in a risky
asset, funded at the cash rate, earns r_asset - w * rf. For a long/short book
the net exposure is what gets funded, which is why those rules barely notice.

Caveat stated rather than hidden: instruments are treated uniformly as
spot-like CFDs where a long pays funding. A bond or index FUTURE already embeds
funding in its price, so for those this over-charges. The direction of that
error favours the long-only rows, which are the ones being questioned.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import core
from h1_combined import rung, LABELS
from g2_portfolio import all_markets, CLUSTERS

RF = pd.read_csv("../fedfunds.csv", parse_dates=[0], index_col=0).iloc[:, 0].dropna() / 100.0


def rf_daily(idx):
    r = RF.reindex(idx.tz_localize(None)).ffill()
    return pd.Series(r.values / core.ppy(idx), index=idx).fillna(0.0)


def excess(gross_ret, net_expo, spread=0.0):
    """subtract the funding actually paid on the exposure actually run"""
    rf = rf_daily(gross_ret.index)
    ppy = core.ppy(gross_ret.index)
    return gross_ret - net_expo.reindex(gross_ret.index).fillna(0.0) * (rf + spread / ppy)


def perf(name, ex):
    ex = ex.dropna()
    eq = (1 + ex).cumprod(); yrs = core.years(ex)
    era = core.era_of(ex.index)
    return dict(strategy=name, sharpe=core.sharpe(ex),
                excess_ret=eq.iloc[-1] ** (1 / yrs) - 1,
                vol=core.ann_vol(ex),
                maxdd=(eq / eq.cummax() - 1).min(),
                **{e[:2]: core.sharpe(ex[(era == e).values])
                   for e in core.ERAS})


def weighted(markets, weights):
    R = pd.concat([core.load(m)["ret"].rename(m) for m in markets], axis=1, sort=False)
    R = R.fillna(0.0)
    w = pd.Series(weights, index=markets)
    return (R * w).sum(axis=1), pd.Series(float(w.sum()), index=R.index)


def main():
    mkts = all_markets()
    rows = []

    # --- achievable passive benchmarks ------------------------------------
    rows.append(perf("cash (the floor)", pd.Series(0.0, index=core.load("spx500usd").index)))
    for name, mk, wt in (
            ("S&P 500, long", ["spx500usd"], [1.0]),
            ("60/40 S&P + US 10y", ["spx500usd", "usb10yusd"], [0.6, 0.4]),
            ("equities + gold, equal", ["spx500usd", "nas100usd", "de30eur", "xauusd"],
             [0.25] * 4)):
        g, ne = weighted(mk, wt)
        rows.append(perf(name, excess(g, ne)))

    # --- the old benchmark, and what it looks like paid for ----------------
    nonfx = [m for m in mkts if CLUSTERS.get(m) != "fx"]
    for name, mk in (("21-market basket (the old benchmark)", mkts),
                     ("14 non-FX basket", nonfx)):
        g, ne = weighted(mk, [1.0 / len(mk)] * len(mk))
        rows.append(perf(name, excess(g, ne)))

    # --- the rungs ---------------------------------------------------------
    for lvl, lab in enumerate(LABELS):
        P, R = rung(mkts, lvl)
        Pf = P.ffill()
        w = Pf.notna().astype(float); w = w.div(w.sum(axis=1).replace(0, np.nan), axis=0)
        eff = (w * Pf).shift(1)
        turn = eff.diff().abs().sum(axis=1).fillna(0.0)
        g = ((eff * R.fillna(0.0)).sum(axis=1) - turn * 1.0 / 1e4)
        rows.append(perf(lab, excess(g, eff.sum(axis=1))))

    t = pd.DataFrame(rows)
    print("=" * 104)
    print("EXCESS returns over cash, funding charged on the exposure actually run")
    print("=" * 104)
    print(t.to_string(index=False, formatters={
        "sharpe": "{:+.3f}".format, "excess_ret": "{:+.2%}".format,
        "vol": "{:.2%}".format, "maxdd": "{:.1%}".format,
        "E1": "{:+.3f}".format, "E2": "{:+.3f}".format, "E3": "{:+.3f}".format}))

    print("\n" + "=" * 104)
    print("With a 2% retail CFD financing spread on top")
    print("=" * 104)
    rows2 = []
    g, ne = weighted(mkts, [1.0 / len(mkts)] * len(mkts))
    rows2.append(perf("21-market basket", excess(g, ne, 0.02)))
    for lvl, lab in enumerate(LABELS):
        P, R = rung(mkts, lvl)
        Pf = P.ffill()
        w = Pf.notna().astype(float); w = w.div(w.sum(axis=1).replace(0, np.nan), axis=0)
        eff = (w * Pf).shift(1)
        turn = eff.diff().abs().sum(axis=1).fillna(0.0)
        gg = ((eff * R.fillna(0.0)).sum(axis=1) - turn * 1.0 / 1e4)
        rows2.append(perf(lab, excess(gg, eff.sum(axis=1), 0.02)))
    t2 = pd.DataFrame(rows2)[["strategy", "sharpe", "excess_ret", "maxdd"]]
    print(t2.to_string(index=False, formatters={
        "sharpe": "{:+.3f}".format, "excess_ret": "{:+.2%}".format,
        "maxdd": "{:.1%}".format}))

    print("\n" + "=" * 104)
    rungs = t[t.strategy.str.match(r"^\d ")]
    passives = t[~t.strategy.str.match(r"^\d ") & (t.strategy != "cash (the floor)")]
    print(f"Rungs beating cash: {int((rungs.sharpe > 0).sum())} of {len(rungs)}")
    print(f"Rungs beating the WORST passive comparator "
          f"({passives.sharpe.min():+.3f}): "
          f"{int((rungs.sharpe > passives.sharpe.min()).sum())} of {len(rungs)}")
    best = rungs.sort_values("sharpe").iloc[-1]
    print(f"Best rung: {best.strategy} at {best.sharpe:+.3f}, "
          f"excess return {best.excess_ret:+.2%}")
    for _, r in t.head(4).iterrows():
        print(f"  passive comparator — {r.strategy:<24} {r.sharpe:+.3f}  "
              f"excess {r.excess_ret:+.2%}  dd {r.maxdd:.1%}")
    t.to_csv("g3_benchmark.csv", index=False)


if __name__ == "__main__":
    main()
