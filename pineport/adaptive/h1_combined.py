"""
H1 — the passes, combined, per PREREGISTRATION_COMBINED.md.

One component per rung, so each contribution is attributable:

    0  buy and hold the 21-market basket
    1  + inverse trailing-vol sizing
    2  + implied-vol sizing where an index exists
    3  + sign(A) direction (long/short instead of always long)
    4  + real-yield overlay on the discount-rate markets

Gate 1 is the one that matters: does the stack beat its own best single rung?
"""
from __future__ import annotations
import os, sys
import numpy as np
import pandas as pd
import core
from c1_agreement import agreement
from e1_vrp import iv_on
from g2_portfolio import all_markets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fetch_fred import load_daily_series                       # noqa: E402

TARGET, CAP, RV_WIN = 0.10, 3.0, 60
NULL_LAG = 750
IV_FOR = {"spx500usd": "vixcls", "nas100usd": "vxncls", "xauusd": "gvzcls",
          "xagusd": "vxslvcls", "bcousd": "ovxcls", "eurusd": "evzcls"}
#: markets where D3 found a sign-consistent, grid-stable discount-rate response
RY_FOR = ["spx500usd", "nas100usd", "de30eur", "bcousd", "xcuusd"]
RY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "dfii10.csv")


def vol_forecast(df, mkt, use_iv):
    ret = df["ret"]
    rv = ret.rolling(RV_WIN).std() * np.sqrt(core.ppy(ret))
    if not use_iv or mkt not in IV_FOR:
        return rv
    iv = iv_on(IV_FOR[mkt], df.index) / 100.0
    ratio = (rv.expanding(252).mean() / iv.expanding(252).mean()).shift(1)
    return (iv * ratio).combine_first(rv)          # fall back where IV is absent


def ry_overlay(index) -> pd.Series:
    """de-risk when the real yield has been RISING -- D3's measured sign."""
    ry = load_daily_series(RY_PATH, lag_days=1)
    ry = ry.reindex(ry.index.union(index)).ffill(limit=5).reindex(index)
    chg = ry - ry.shift(63)
    z = (chg - chg.expanding(252).mean()) / chg.expanding(252).std()
    return (1.0 - 0.5 * z.clip(-2, 2) / 2.0).clip(0.5, 1.5)   # 0.5x .. 1.5x


def rung(markets, level, ry_lag=0):
    pos, ret = {}, {}
    ryo = None
    for m in markets:
        df = core.load(m)
        r = df["ret"]
        if level == 0:
            p = pd.Series(1.0, index=df.index)
        else:
            vf = vol_forecast(df, m, use_iv=(level >= 2))
            p = (TARGET / vf).clip(upper=CAP)
            if level >= 3:
                p = p * np.sign(agreement(df["close"])).astype(float)
            if level >= 4 and m in RY_FOR:
                if ryo is None or not ryo.index.equals(df.index):
                    ryo = ry_overlay(df.index)
                o = ryo.shift(ry_lag) if ry_lag else ryo
                p = p * o.fillna(1.0)
        pos[m] = p.astype(float).rename(m)
        ret[m] = r.rename(m)
    P = pd.concat(pos.values(), axis=1, sort=False)
    R = pd.concat(ret.values(), axis=1, sort=False)
    return P, R


def run(P, R, cost_bps=1.0):
    """
    Positions persist across days a market does not trade, and the equal weight
    is rebalanced MONTHLY rather than re-derived every day. Re-normalising daily
    across 21 different trading calendars manufactures turnover -- it charged
    buy-and-hold 38 units a year, which is nonsense and made the 5bp gate
    meaningless for every row.
    """
    P = P.ffill()
    R = R.fillna(0.0)
    live = P.notna()
    w = pd.DataFrame(np.nan, index=P.index, columns=P.columns)
    for i in range(0, len(P.index), 21):
        row = live.iloc[i]
        n = row.sum()
        if n:
            w.iloc[i] = row.astype(float) / n
    w = w.ffill()
    eff = (w * P).shift(1)
    turn = eff.diff().abs().sum(axis=1).fillna(0.0)
    return ((eff * R).sum(axis=1) - turn * cost_bps / 1e4).dropna(), turn


def stats(name, r, turn):
    era = core.era_of(r.index)
    eq = (1 + r).cumprod(); yrs = core.years(r)
    return dict(rung=name, sharpe=core.sharpe(r),
                **{e[:2]: core.sharpe(r[(era == e).values]) for e in core.ERAS},
                ann_ret=eq.iloc[-1] ** (1 / yrs) - 1,
                ann_vol=core.ann_vol(r),
                maxdd=(eq / eq.cummax() - 1).min(),
                turnover=turn.sum() / yrs)


LABELS = ["0 buy and hold", "1 + trailing-vol sizing", "2 + implied-vol sizing",
          "3 + sign(A) direction", "4 + real-yield overlay"]


def main():
    mkts = all_markets()
    print(f"{len(mkts)} markets · implied vol on "
          f"{sum(m in IV_FOR for m in mkts)} · real-yield overlay on "
          f"{sum(m in RY_FOR for m in mkts)}\n")

    series, rows = {}, []
    for lvl, lab in enumerate(LABELS):
        P, R = rung(mkts, lvl)
        r, t = run(P, R)
        series[lab] = r
        rows.append(stats(lab, r, t))
    tab = pd.DataFrame(rows)

    common = None
    for v in series.values():
        common = v.index if common is None else common.intersection(v.index)
    rows = [stats(k, v.reindex(common).dropna(),
                  pd.Series(0.0, index=common)) for k, v in series.items()]
    al = pd.DataFrame(rows)[["rung", "sharpe", "E1", "E2", "E3"]]

    print("=" * 104)
    print("Each rung adds one component — 21 markets, equal weight, 1bp")
    print("=" * 104)
    print(tab.to_string(index=False, formatters={
        "sharpe": "{:+.3f}".format, "E1": "{:+.3f}".format, "E2": "{:+.3f}".format,
        "E3": "{:+.3f}".format, "ann_ret": "{:+.2%}".format,
        "ann_vol": "{:.2%}".format, "maxdd": "{:.1%}".format,
        "turnover": "{:.1f}".format}))
    print("\naligned to a common window:")
    print(al.to_string(index=False, formatters={c: "{:+.3f}".format
          for c in ["sharpe", "E1", "E2", "E3"]}))

    print("\n" + "=" * 104)
    best_rung = tab.sharpe.max()
    full = tab.iloc[-1]
    bh = tab.iloc[0]
    print(f"Gate 1 — full stack {full.sharpe:+.3f} vs its best single rung "
          f"{best_rung:+.3f}: "
          f"{'PASS' if full.sharpe >= best_rung - 1e-9 else 'FAIL'}")
    eras_ok = all(full[e[:2]] > bh[e[:2]] for e in core.ERAS)
    print(f"Gate 2 — beats buy-and-hold in all three eras: "
          f"{'PASS' if eras_ok else 'FAIL'}")
    print(f"Gate 3 — Sharpe vs buy-and-hold: {full.sharpe:+.3f} vs {bh.sharpe:+.3f} "
          f"({'PASS' if full.sharpe > bh.sharpe else 'FAIL — risk case required'})"
          f"   drawdown {full.maxdd:.1%} vs {bh.maxdd:.1%}")

    print("\nGate 4 — costs")
    for c in (1.0, 5.0):
        line = []
        for lvl, lab in enumerate(LABELS):
            P, R = rung(mkts, lvl)
            r, _ = run(P, R, c)
            line.append(f"{lab.split()[0]}:{core.sharpe(r):+.3f}")
        print(f"  {c:.0f}bp  " + "  ".join(line))

    print("\nGate 5 — the real-yield overlay against a destroyed-timing null")
    P, R = rung(mkts, 4); r4, _ = run(P, R)
    Pn, Rn = rung(mkts, 4, ry_lag=NULL_LAG); rn, _ = run(Pn, Rn)
    P3, R3 = rung(mkts, 3); r3, _ = run(P3, R3)
    print(f"  no overlay {core.sharpe(r3):+.3f} · real overlay {core.sharpe(r4):+.3f} "
          f"· shuffled-timing overlay {core.sharpe(rn):+.3f}")
    print("  " + ("PASS — the overlay's timing carries information"
                  if core.sharpe(r4) > max(core.sharpe(rn), core.sharpe(r3))
                  else "FAIL — drop rung 4"))
    tab.to_csv("h1_combined.csv", index=False)


if __name__ == "__main__":
    main()
