"""
k1_hedging.py — hedging pressure from CFTC COT.
Pre-registered in PREREGISTRATION_COT.md. Nothing here deviates from it.

The first test in this project whose predictor is not a price.
"""
from __future__ import annotations
import os, glob
import numpy as np
import pandas as pd
import core

RNG   = np.random.default_rng(20260903)
NBOOT = 2000
COT   = os.path.join(core.HERE, "cot")

# Tuesday snapshot, published Friday 15:30 ET. Pre-registered rule: first
# usable on the FOLLOWING MONDAY (+6 days), then shift(1) for the standard
# execution model. Deliberately conservative -- a 3-day look-ahead here is
# the single most likely way to manufacture a false pass.
LAG_DAYS = 6

# CME quotes JPY/USD and CAD/USD; our CFDs are USD/JPY and USD/CAD. Rather
# than flipping the SIGNAL (error-prone, and it would flip only two markets
# in a way that looks like a plausible weak result), the RETURN is negated so
# every market is expressed in its futures' own quote convention.
INVERT = {"usdjpy", "usdcad"}

CLASS = {"cornusd":"comdty","wheatusd":"comdty","sugarusd":"comdty",
         "natgasusd":"comdty","xauusd":"comdty","xagusd":"comdty",
         "xcuusd":"comdty","xptusd":"comdty",
         "eurusd":"fx","gbpusd":"fx","audusd":"fx","usdjpy":"fx","usdcad":"fx",
         "spx500usd":"equity","nas100usd":"equity",
         "usb10yusd":"rates"}

END = "2026-08-07"        # last date all price series are live (GAUNTLET 1.6)


def markets():
    return sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(COT, "*.csv")))


def hp_raw(mkt: str) -> pd.Series:
    d = pd.read_csv(os.path.join(COT, f"{mkt}.csv"), parse_dates=["report_date"])
    d = d.sort_values("report_date").set_index("report_date")
    hp = -(d["comm_long"] - d["comm_short"]) / d["oi"].replace(0, np.nan)
    return hp.dropna()


def signal(mkt: str, months: int, index: pd.DatetimeIndex) -> pd.Series:
    """Trailing mean of HP over a CALENDAR window, aligned to the price index.

    The window is calendar-based, not a row count. COT was SEMI-MONTHLY before
    1992 (median gap 15-16 days) and weekly after, so a fixed 52-row lookback
    would span 12 months in one era and 26 in another -- the same defect as
    R4, in a different guise. Our window starts 2005 so this is precautionary,
    but the bug would be silent if the sample were ever extended back.
    """
    hp = hp_raw(mkt)
    s = hp.rolling(f"{int(months * 30.44)}D").mean()
    s.index = s.index + pd.Timedelta(days=LAG_DAYS)      # publication lag
    s.index = s.index.tz_localize("UTC")
    return s.reindex(s.index.union(index)).ffill().reindex(index).shift(1)


def panel(mkts, months=12):
    R, S = {}, {}
    for m in mkts:
        df = core.load(m).loc[:END]
        r = np.log(df["close"]).diff()
        R[m] = -r if m in INVERT else r                  # futures quote convention
        S[m] = signal(m, months, df.index)
    R = pd.DataFrame(R); S = pd.DataFrame(S).reindex(R.index)
    return R, S


def zweights(S: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional z-score, dollar-neutral, unit gross. Ranking is WITHIN
    date ACROSS markets -- never on pooled levels (the a2 defect)."""
    # Minimum cross-section width must SCALE with the basket. A hardcoded 8
    # silently returned all-NaN for the fx (n=5) and equity (n=2) sub-baskets,
    # i.e. pre-registered criterion 6 did not run at all on the first pass.
    need = max(2, min(8, S.shape[1] // 2 + 1))
    live = S.notna().sum(axis=1) >= need
    z = S.sub(S.mean(axis=1), axis=0).div(S.std(axis=1).replace(0, np.nan), axis=0)
    z = z.sub(z.mean(axis=1), axis=0)                    # enforce dollar-neutral
    w = z.div(z.abs().sum(axis=1).replace(0, np.nan), axis=0)
    return w.where(live)


def run(R, S, cost_bps=1.0):
    w = zweights(S)
    eff = w.shift(1)
    turn = eff.diff().abs().sum(axis=1).fillna(0.0)
    return ((eff * R).sum(axis=1, min_count=1) - turn * cost_bps / 1e4).dropna(), turn


def block_boot(r: pd.Series, n=NBOOT, mean_block=63):
    """Stationary block bootstrap of the Sharpe."""
    x = r.dropna().values; N = len(x)
    if N < 100: return np.array([np.nan])
    out = np.empty(n)
    for i in range(n):
        idx, j = [], 0
        while j < N:
            st = RNG.integers(0, N); L = max(1, RNG.geometric(1 / mean_block))
            idx += [(st + k) % N for k in range(min(L, N - j))]; j += L
        y = x[np.array(idx[:N])]
        out[i] = y.mean() / y.std() * np.sqrt(core.ppy(r)) if y.std() else np.nan
    return out


def main():
    mkts = markets()
    R, S = panel(mkts)
    print(f"K1 hedging pressure | {len(mkts)} markets | {R.index[0].date()} -> {R.index[-1].date()}")
    print(f"returns negated (futures quote convention): {sorted(INVERT)}")
    print(f"publication lag: report Tue -> usable Mon (+{LAG_DAYS}d) -> shift(1)\n")

    r, turn = run(R, S)
    sh = core.sharpe(r)
    floor = 1 / np.sqrt(core.years(r) * 5.0)      # N_eff ~5 for this universe
    print("=" * 70)
    print(f"PRIMARY  rank-weighted, dollar-neutral, 1bp")
    print("=" * 70)
    print(f"  Sharpe        {sh:+.4f}      pass requires >= +0.29")
    print(f"  ann return    {core.ann_return(r):+.4%}")
    print(f"  ann vol       {core.ann_vol(r):+.4%}")
    print(f"  turnover      {turn.mean()*core.ppy(r):.1f} units/yr")
    print(f"  noise floor   {floor:.3f}  ({core.years(r):.1f} yrs x N_eff 5)")

    print("\n  eras:")
    signs = []
    for name, (a, b) in core.ERAS.items():
        e = core.sharpe(r.loc[a:b]); signs.append(np.sign(e))
        print(f"    {name}: {e:+.4f}")

    print("\n  destroyed-timing null (signal lagged 750 bars):")
    rn, _ = run(R, S.shift(750))
    nb = block_boot(rn)
    print(f"    null Sharpe {core.sharpe(rn):+.4f}   bootstrap p95 {np.nanpercentile(nb,95):+.4f}")

    print("\n  cost robustness:")
    for c in (0.0, 3.0):
        print(f"    {c:.0f}bp: {core.sharpe(run(R,S,c)[0]):+.4f}")

    print("\n  plateau in lookback (9 / 12 / 18 months):")
    plat = {}
    for mo in (9, 12, 18):
        _, Sm = panel(mkts, months=mo)
        plat[mo] = core.sharpe(run(R, Sm)[0])
        print(f"    {mo:2d}m: {plat[mo]:+.4f}")

    print("\n  by class (published result is NOT uniform — it reverses in rates):")
    for cl in ("comdty", "fx", "equity", "rates"):
        sub = [m for m in mkts if CLASS.get(m) == cl]
        if len(sub) < 2:
            print(f"    {cl:7s} n={len(sub)}  (too few to form a cross-section)"); continue
        rc, _ = run(R[sub], S[sub])
        print(f"    {cl:7s} n={len(sub)}  Sharpe {core.sharpe(rc):+.4f}")

    print("\n  MIRROR — rank on 1/OI alone, signal term removed:")
    OI = {}
    for m in mkts:
        d = pd.read_csv(os.path.join(COT, f"{m}.csv"), parse_dates=["report_date"])
        o = d.set_index("report_date")["oi"].sort_index()
        o.index = o.index + pd.Timedelta(days=LAG_DAYS); o.index = o.index.tz_localize("UTC")
        OI[m] = (1.0 / o).reindex(o.index.union(R.index)).ffill().reindex(R.index).shift(1)
    rm, _ = run(R, pd.DataFrame(OI))
    print(f"    Sharpe {core.sharpe(rm):+.4f}   (if comparable to primary, signal is an OI tilt)")

    ok = (sh >= 0.29 and len(set(signs)) == 1
          and sh > np.nanpercentile(nb, 95)
          and core.sharpe(run(R, S, 3.0)[0]) >= 0.29
          and len({np.sign(v) for v in plat.values()}) == 1)
    print("\n" + "=" * 70)
    print(f"K1 VERDICT: {'PASS' if ok else 'FAIL'}")
    print("=" * 70)
    r.to_csv("k1_returns.csv")


if __name__ == "__main__":
    main()
