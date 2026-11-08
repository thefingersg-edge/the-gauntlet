"""
D2 — the two checks D1's numbers depend on.

1. SAMPLING-OFFSET ROBUSTNESS. A non-overlapping sample of 24-26 points has to
   start somewhere. If rho swings with where the grid starts, the number is an
   artefact of the grid, not a measurement. This project has already been bitten
   by exactly this on 4H bar alignment.

2. IS IT JUST THE DOLLAR? A synthetic dollar is built from the four USD pairs on
   disk. If real yields only predict the dollar, the equity results should
   disappear once the dollar is partialled out.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import core
from d1_realyield import market_table, SIGN_MAP, HORIZONS


def offset_robustness():
    print("=" * 96)
    print("1. Sampling-offset robustness — primary signal, every possible start of the grid")
    print("=" * 96)
    rows = []
    for m in core.MARKETS:
        t = market_table(m)
        r = {"market": m, "pred": {1: "+", -1: "-", 0: "."}[SIGN_MAP[m]]}
        for h in HORIZONS:
            sub = t[["S1_chg63", f"fwd{h}"]].dropna()
            rhos = [core.spearman(sub.iloc[o::h]["S1_chg63"], sub.iloc[o::h][f"fwd{h}"])
                    for o in range(h)]
            rhos = np.array([x for x in rhos if not np.isnan(x)])
            r[f"h{h}_mean"] = rhos.mean()
            r[f"h{h}_lo"] = rhos.min()
            r[f"h{h}_hi"] = rhos.max()
            r[f"h{h}_signstable"] = float((np.sign(rhos) == np.sign(rhos.mean())).mean())
        rows.append(r)
    tab = pd.DataFrame(rows)
    for h in HORIZONS:
        print(f"\n  horizon {h} days")
        cols = ["market", "pred", f"h{h}_mean", f"h{h}_lo", f"h{h}_hi", f"h{h}_signstable"]
        print(tab[cols].to_string(index=False, formatters={
            c: "{:+.3f}".format for c in cols[2:5]} | {f"h{h}_signstable": "{:.0%}".format}))
        scored = tab[tab.pred != "."]
        hit = sum(np.sign(r[f"h{h}_mean"]) == SIGN_MAP[r["market"]] for _, r in scored.iterrows())
        jpy = tab.loc[tab.market == "usdjpy", f"h{h}_mean"].iloc[0]
        print(f"    averaged over all starts: sign map matched {hit}/9, "
              f"USDJPY {jpy:+.3f}")
    tab.to_csv("d2_offset_robustness.csv", index=False)
    return tab


def dollar_control():
    print("\n" + "=" * 96)
    print("2. Is it just the dollar?")
    print("=" * 96)
    legs = {"eurusd": -1, "gbpusd": -1, "audusd": -1, "usdjpy": +1}
    rets = []
    for m, w in legs.items():
        rets.append(w * core.load(m)["ret"].rename(m))
    usd = pd.concat(rets, axis=1).mean(axis=1).dropna()
    usd_idx = (1 + usd).cumprod()

    t = market_table("xauusd")[["S1_chg63"]]
    out = []
    for h in HORIZONS:
        d = pd.DataFrame({"sig": t["S1_chg63"]}).join(
            (usd_idx.shift(-h) / usd_idx - 1.0).rename("fwd_usd")).dropna().iloc[::h]
        out.append(dict(horizon=h, n=len(d), rho_dollar=core.spearman(d.sig, d.fwd_usd)))
    print("  real-yield change vs the forward synthetic dollar:")
    print(pd.DataFrame(out).to_string(index=False, formatters={"rho_dollar": "{:+.3f}".format}))

    print("\n  equity and metal correlations, before and after removing the dollar:")
    rows = []
    for m in ("spx500usd", "nas100usd", "de30eur", "xauusd", "xagusd"):
        tm = market_table(m)
        r = {"market": m}
        for h in HORIZONS:
            d = tm[["S1_chg63", f"fwd{h}"]].join(
                (usd_idx.shift(-h) / usd_idx - 1.0).rename("fwd_usd")).dropna().iloc[::h]
            raw = core.spearman(d["S1_chg63"], d[f"fwd{h}"])
            # partial correlation on ranks
            R = d[["S1_chg63", f"fwd{h}", "fwd_usd"]].rank()
            C = R.corr().values
            inv = np.linalg.pinv(C)
            part = -inv[0, 1] / np.sqrt(inv[0, 0] * inv[1, 1])
            r[f"h{h}_raw"] = raw
            r[f"h{h}_partial"] = part
        rows.append(r)
    tab = pd.DataFrame(rows)
    print(tab.to_string(index=False, formatters={c: "{:+.3f}".format
          for c in tab.columns if c != "market"}))
    tab.to_csv("d2_dollar_control.csv", index=False)


if __name__ == "__main__":
    offset_robustness()
    dollar_control()
