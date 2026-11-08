"""
D1 — real yields at 3-12 months, scored against a sign map written first.

Uses the project's own `fetch_fred.load_daily_series`, which applies the
one-business-day publication lag, so the FRED observation dated D is only
visible from D+1. Forward returns are sampled on NON-OVERLAPPING windows.

The test is not "is anything significant" — it is whether nine markets come out
with the signs `PREREGISTRATION_REALYIELD.md` predicted for them, USDJPY
flipping included.
"""
from __future__ import annotations
import os, sys
import numpy as np
import pandas as pd
import core

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fetch_fred import load_daily_series          # noqa: E402  (his lag handling)

RY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dfii10.csv")
HORIZONS = (63, 126, 252)

SIGN_MAP = {                    # predicted sign of corr(signal, forward return)
    "xauusd": -1, "xagusd": -1, "spx500usd": -1, "nas100usd": -1, "de30eur": -1,
    "eurusd": -1, "gbpusd": -1, "audusd": -1, "usdjpy": +1,
    "bcousd": 0, "xcuusd": 0,   # 0 = no prediction, reported but not scored
}


def real_yield_on(index: pd.DatetimeIndex) -> pd.Series:
    ry = load_daily_series(RY_PATH, lag_days=1)
    return ry.reindex(ry.index.union(index)).ffill().reindex(index)


def market_table(mkt: str) -> pd.DataFrame:
    df = core.load(mkt)
    ry = real_yield_on(df.index)
    out = pd.DataFrame(index=df.index)
    out["S1_chg63"] = ry - ry.shift(63)
    out["S2_chg252"] = ry - ry.shift(252)
    out["S3_level"] = ry
    for h in HORIZONS:
        out[f"fwd{h}"] = df["close"].shift(-h) / df["close"] - 1.0
    out["era"] = core.era_of(df.index)
    return out.dropna(subset=["S1_chg63", "S3_level"])


def main():
    tables = {m: market_table(m) for m in core.MARKETS}
    print(f"real yield joined 2006-2026, lagged one business day\n")

    for sig in ("S1_chg63", "S2_chg252", "S3_level"):
        print("=" * 100)
        print(f"SIGNAL: {sig}" + ("   [PRIMARY]" if sig == "S1_chg63" else
                                  "   [secondary — near unit root, see caveat]" if sig == "S3_level" else ""))
        print("=" * 100)
        rows = []
        for m, t in tables.items():
            r = {"market": m, "pred": {1: "+", -1: "-", 0: "."}[SIGN_MAP[m]]}
            for h in HORIZONS:
                sub = t[[sig, f"fwd{h}"]].dropna()
                nov = sub.iloc[::h]                       # non-overlapping
                rho = core.spearman(nov[sig], nov[f"fwd{h}"])
                r[f"h{h}"] = rho
                r[f"n{h}"] = len(nov)
                r[f"ov{h}"] = core.spearman(sub[sig], sub[f"fwd{h}"])
            rows.append(r)
        tab = pd.DataFrame(rows)
        show = tab[["market", "pred"] + [f"h{h}" for h in HORIZONS]
                   + [f"ov{h}" for h in HORIZONS] + ["n252"]]
        print(show.to_string(index=False, formatters={c: "{:+.3f}".format for c in
              [f"h{h}" for h in HORIZONS] + [f"ov{h}" for h in HORIZONS]}))
        print("  h = non-overlapping (scored) · ov = overlapping (not scored)")
        for h in HORIZONS:
            scored = tab[tab.pred != "."]
            hit = sum(np.sign(r[f"h{h}"]) == SIGN_MAP[r["market"]]
                      for _, r in scored.iterrows() if not np.isnan(r[f"h{h}"]))
            jpy = tab.loc[tab.market == "usdjpy", f"h{h}"].iloc[0]
            print(f"  h={h:>3}: sign map matched {hit}/9   "
                  f"USDJPY {jpy:+.3f} ({'FLIPS as predicted' if jpy > 0 else 'does NOT flip'})"
                  f"   [gate: >= 7/9 and USDJPY positive]")
        print()

    print("=" * 100)
    print("Gold, era by era, primary signal — criterion 2")
    print("=" * 100)
    t = tables["xauusd"]
    rows = []
    for e in list(core.ERAS) + ["ALL"]:
        sub = t if e == "ALL" else t[t.era == e]
        r = {"era": e}
        for h in HORIZONS:
            s = sub[["S1_chg63", f"fwd{h}"]].dropna().iloc[::h]
            r[f"h{h}"] = core.spearman(s["S1_chg63"], s[f"fwd{h}"])
            r[f"n{h}"] = len(s)
        rows.append(r)
    print(pd.DataFrame(rows).to_string(index=False, formatters={
        f"h{h}": "{:+.3f}".format for h in HORIZONS}))
    pd.concat(tables, names=["market"]).to_pickle("d1_tables.pkl")


if __name__ == "__main__":
    main()
