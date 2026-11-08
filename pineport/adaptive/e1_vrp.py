"""
E1 — the variance risk premium, scored against a sign map written first.

    VRP_t = IV_t - RV21_t      both known at t, IV lagged one business day

Every correlation is averaged over EVERY possible start of the non-overlapping
sampling grid, because that check changed the answer in the real-yield study.
"""
from __future__ import annotations
import os, sys
import numpy as np
import pandas as pd
import core

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from fetch_fred import load_daily_series          # noqa: E402

MACRO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "macro")
HORIZONS = (21, 63, 126)
MAX_FFILL = 5          # business days -- see iv_on()

PAIRS = {                      # implied-vol file -> instrument
    "vixcls": "spx500usd",
    "gvzcls": "xauusd",
    "ovxcls": "bcousd",
    "evzcls": "eurusd",
}


def iv_on(name: str, index: pd.DatetimeIndex, max_ffill: int = MAX_FFILL) -> pd.Series:
    """Align a FRED series onto bar dates, forward-filling ONLY across short gaps.

    An unbounded ffill is correct for weekends and holidays and catastrophic for
    a DISCONTINUED series: VXSLV stopped in 2022-02 and was being carried forward
    to 2026, inventing 1,636 days -- 29% of the sample -- of frozen implied vol,
    and EVZ 513 days. Both were the markets that "failed"; the failure was this
    function. Bars past the end of the series are now NaN and get dropped.
    """
    s = load_daily_series(os.path.join(MACRO, f"{name}.csv"), lag_days=1)
    out = s.reindex(s.index.union(index)).ffill(limit=max_ffill).reindex(index)
    live = out.dropna()
    if len(live):
        gap = (index[-1] - live.index[-1]).days
        if gap > 30:
            print(f"  [iv_on] {name}: series ends {live.index[-1].date()}, "
                  f"{gap} days before the market data -- those bars are dropped, "
                  f"not carried forward")
    return out


def build(iv_name: str, mkt: str) -> pd.DataFrame:
    df = core.load(mkt)
    iv = iv_on(iv_name, df.index)
    ppy = core.ppy(df["ret"])
    rv = df["ret"].rolling(21).std() * np.sqrt(ppy) * 100      # IV series are in %
    t = pd.DataFrame(index=df.index)
    t["IV"] = iv
    t["RV"] = rv
    t["VRP"] = iv - rv
    for h in HORIZONS:
        t[f"fwd{h}"] = df["close"].shift(-h) / df["close"] - 1.0
        t[f"absfwd{h}"] = t[f"fwd{h}"].abs() / (rv / 100 * np.sqrt(h / ppy))
    t["era"] = core.era_of(df.index)
    return t.dropna(subset=["VRP"])


def grid_rho(sub: pd.DataFrame, a: str, b: str, h: int):
    d = sub[[a, b]].dropna()
    rhos = [core.spearman(d.iloc[o::h][a], d.iloc[o::h][b]) for o in range(h)]
    rhos = np.array([x for x in rhos if not np.isnan(x)])
    if len(rhos) == 0:
        return np.nan, np.nan, 0
    return rhos.mean(), (np.sign(rhos) == np.sign(rhos.mean())).mean(), len(d) // h


def main():
    tabs = {iv: build(iv, m) for iv, m in PAIRS.items()}
    print("=" * 104)
    print("E1 — VRP vs forward return.  All rho averaged over every sampling-grid start.")
    print("     Predicted sign: POSITIVE on all four pairs.")
    print("=" * 104)
    rows = []
    for iv, m in PAIRS.items():
        t = tabs[iv]
        r = {"iv": iv.upper()[:3], "market": m, "span": f"{t.index[0].year}-{t.index[-1].year}"}
        for h in HORIZONS:
            rho, stab, n = grid_rho(t, "VRP", f"fwd{h}", h)
            r[f"h{h}"] = rho
            r[f"s{h}"] = stab
            r[f"n{h}"] = n
        rows.append(r)
    tab = pd.DataFrame(rows)
    cols = ["iv", "market", "span"] + sum([[f"h{h}", f"s{h}", f"n{h}"] for h in HORIZONS], [])
    print(tab[cols].to_string(index=False, formatters=
          {f"h{h}": "{:+.3f}".format for h in HORIZONS} |
          {f"s{h}": "{:.0%}".format for h in HORIZONS}))
    for h in HORIZONS:
        hit = int((tab[f"h{h}"] > 0).sum())
        stab = int((tab[f"s{h}"] >= 0.8).sum())
        print(f"  h={h:>3}: predicted sign on {hit}/4 pairs   "
              f"grid-stable (>=80%) on {stab}/4   [gate: >= 3/4 both]")

    # ---- gate 4: does subtracting realised vol add anything? ----
    print("\n" + "=" * 104)
    print("Gate 4 — VRP against the implied-vol LEVEL alone, and realised vol alone")
    print("=" * 104)
    rows = []
    for iv, m in PAIRS.items():
        t = tabs[iv]
        r = {"iv": iv.upper()[:3], "market": m}
        for h in HORIZONS:
            r[f"VRP_h{h}"] = grid_rho(t, "VRP", f"fwd{h}", h)[0]
            r[f"IV_h{h}"] = grid_rho(t, "IV", f"fwd{h}", h)[0]
            r[f"RV_h{h}"] = grid_rho(t, "RV", f"fwd{h}", h)[0]
        rows.append(r)
    t4 = pd.DataFrame(rows)
    print(t4.to_string(index=False, formatters={c: "{:+.3f}".format
          for c in t4.columns if c not in ("iv", "market")}))
    for h in HORIZONS:
        better = int((t4[f"VRP_h{h}"].abs() > t4[f"IV_h{h}"].abs()).sum())
        print(f"  h={h:>3}: |VRP| beats |IV level| on {better}/4   [gate: >= 3/4]")

    # ---- gate 5: own vol index vs VIX applied to the same instrument ----
    print("\n" + "=" * 104)
    print("Gate 5 — the instrument's OWN vol index against VIX on the same instrument")
    print("=" * 104)
    rows = []
    for iv, m in PAIRS.items():
        if iv == "vixcls":
            continue
        own, vix = tabs[iv], build("vixcls", m)
        r = {"market": m}
        for h in HORIZONS:
            r[f"own_h{h}"] = grid_rho(own, "VRP", f"fwd{h}", h)[0]
            r[f"vix_h{h}"] = grid_rho(vix, "VRP", f"fwd{h}", h)[0]
        rows.append(r)
    t5 = pd.DataFrame(rows)
    print(t5.to_string(index=False, formatters={c: "{:+.3f}".format
          for c in t5.columns if c != "market"}))

    # ---- era stability on the longest pair ----
    print("\n" + "=" * 104)
    print("Gate 3 — era stability, VIX/SPX500")
    print("=" * 104)
    t = tabs["vixcls"]
    rows = []
    for e in list(core.ERAS) + ["ALL"]:
        sub = t if e == "ALL" else t[t.era == e]
        r = {"era": e}
        for h in HORIZONS:
            rho, stab, n = grid_rho(sub, "VRP", f"fwd{h}", h)
            r[f"h{h}"], r[f"n{h}"] = rho, n
        rows.append(r)
    print(pd.DataFrame(rows).to_string(index=False, formatters={
        f"h{h}": "{:+.3f}".format for h in HORIZONS}))

    # ---- the pre-stated sizing question ----
    print("\n" + "=" * 104)
    print("Stated in advance, not a gate — VRP vs forward |return| / prior vol")
    print("=" * 104)
    rows = []
    for iv, m in PAIRS.items():
        t = tabs[iv]
        r = {"iv": iv.upper()[:3], "market": m}
        for h in HORIZONS:
            rho, stab, n = grid_rho(t, "VRP", f"absfwd{h}", h)
            r[f"h{h}"], r[f"s{h}"] = rho, stab
        rows.append(r)
    ts = pd.DataFrame(rows)
    print(ts.to_string(index=False, formatters={f"h{h}": "{:+.3f}".format for h in HORIZONS}
          | {f"s{h}": "{:.0%}".format for h in HORIZONS}))
    tab.to_csv("e1_vrp_direction.csv", index=False)
    ts.to_csv("e1_vrp_sizing.csv", index=False)


if __name__ == "__main__":
    main()
