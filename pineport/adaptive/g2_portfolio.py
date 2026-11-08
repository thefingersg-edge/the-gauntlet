"""
G2 — portfolio construction, per PREREGISTRATION_PORTFOLIO.md.

Gate 0 passed at N_eff 6.01 against a threshold of 6.0 -- marginally -- so the
allocation rules are tested.

The per-market rule is IDENTICAL under every allocation: sign(A) direction,
inverse trailing-realised-vol sizing. The only thing that varies is the weight
across markets. That is GATE 5 satisfied by construction rather than checked
afterwards -- volatility appears in the per-market sizing and in the weights, and
if the per-market half moved too, any gain would be unattributable.

Every weight is causal: rolling windows, shifted, monthly rebalance.
"""
from __future__ import annotations
import glob, os
import numpy as np
import pandas as pd
import core
from c1_agreement import agreement

TARGET, CAP, RV_WIN = 0.10, 3.0, 60
NULL_LAG = 750
WINDOWS = (63, 126, 252, 504)

#: a-priori clusters -- fixed by what the instrument IS, never fitted
CLUSTERS = {
    "spx500usd": "equity", "nas100usd": "equity", "de30eur": "equity",
    "xauusd": "metal", "xagusd": "metal", "xptusd": "metal",
    "bcousd": "energy", "natgasusd": "energy", "xcuusd": "industrial",
    "wheatusd": "ag", "cornusd": "ag", "sugarusd": "ag",
    "eurusd": "fx", "gbpusd": "fx", "audusd": "fx", "usdjpy": "fx",
    "eurgbp": "fx", "eurjpy": "fx", "usdcad": "fx",
    "usb10yusd": "rates", "de10ybeur": "rates",
}


def all_markets():
    return sorted(os.path.basename(p).replace("_d1.csv", "")
                  for p in glob.glob(os.path.join(core.DATA, "*_d1.csv")))


def per_market(markets):
    pos, ret = {}, {}
    for m in markets:
        df = core.load(m)
        r = df["ret"]
        vol = r.rolling(RV_WIN).std() * np.sqrt(core.ppy(r))
        pos[m] = (np.sign(agreement(df["close"])).astype(float)
                  * (TARGET / vol).clip(upper=CAP)).rename(m)
        ret[m] = r.rename(m)
    return (pd.concat(pos.values(), axis=1, sort=False),
            pd.concat(ret.values(), axis=1, sort=False))


def weights(S, kind, win):
    idx = S.index
    # R2: pandas rolling(win) defaults to min_periods=win, so on a ragged
    # multi-market index it needs `win` CONSECUTIVE non-NaN rows. Five markets
    # (cornusd, de10ybeur, de30eur, sugarusd, wheatusd) never got a single
    # non-NaN vol row, so they were silently dropped from every vol-weighted
    # rule while `equal` — which never touches vol — kept them. The headline
    # table compared different market sets. 0.8 matches the `live` threshold
    # already used below, so the two now agree.
    vol = S.rolling(win, min_periods=int(win * 0.8)).std().shift(1)
    W = pd.DataFrame(np.nan, index=idx, columns=S.columns)
    for i in range(win + 1, len(idx), 21):
        hist = S.iloc[i - win:i]
        live = S.columns[hist.notna().sum() >= win * 0.8]
        if len(live) < 3:
            continue
        v = vol.iloc[i][live].replace(0, np.nan)
        if kind == "equal":
            w = pd.Series(1.0, index=live)
        elif kind == "invvol":
            w = 1.0 / v
        elif kind == "riskparity":
            c = hist[live].corr().sum(axis=1).clip(lower=1.0)
            w = 1.0 / (v * np.sqrt(c))
        elif kind == "cluster":
            cl = pd.Series([CLUSTERS.get(m, "other") for m in live], index=live)
            n_cl = cl.nunique()
            w = pd.Series(index=live, dtype=float)
            for g in cl.unique():
                mem = cl.index[cl == g]
                w[mem] = 1.0 / (n_cl * len(mem))
            w = w / v
        else:
            raise ValueError(kind)
        w = w.replace([np.inf, -np.inf], np.nan).dropna()
        if w.sum() > 0:
            W.loc[idx[i], w.index] = (w / w.sum()).values
    return W.ffill()


def portfolio(P, R, W, cost_bps=1.0):
    """R3: `.sum(axis=1)` returns 0.0 for an all-NaN row, so the following
    `.dropna()` removed nothing and ~2,900 leading zeros entered the Sharpe —
    understating it by ~23% and giving the rule and its null different spans.
    `min_count=1` makes an all-NaN row NaN, so dropna() does its job."""
    eff = (W * P).shift(1)
    turn = eff.diff().abs().sum(axis=1).fillna(0.0)
    gross = (eff * R).sum(axis=1, min_count=1)
    r = (gross - turn * cost_bps / 1e4).where(gross.notna()).dropna()
    return r, turn.reindex(r.index)


def report(name, r, turn):
    era = core.era_of(r.index)
    eq = (1 + r).cumprod()
    yrs = core.years(r)
    return dict(rule=name, start=str(r.index[0].date()), n=len(r),
                sharpe=core.sharpe(r),
                **{e[:2]: core.sharpe(r[(era == e).values]) for e in core.ERAS},
                ann_ret=eq.iloc[-1] ** (1 / yrs) - 1,
                ann_vol=core.ann_vol(r),
                maxdd=(eq / eq.cummax() - 1).min(),
                turnover=turn.sum() / yrs)


def main():
    mkts = all_markets()
    P, R = per_market(mkts)
    S = (P.shift(1) * R)
    print(f"{len(mkts)} markets, identical per-market rule, monthly rebalance\n")

    rows, series = [], {}
    for kind in ("equal", "invvol", "riskparity", "cluster"):
        r, t = portfolio(P, R, weights(S, kind, 252))
        series[kind] = r
        rows.append(report(kind, r, t))

    rnull, t = portfolio(P, R, weights(S, "riskparity", 252).shift(NULL_LAG))
    rows.append(report("null_shuffled_weights", rnull, t))
    # R9: shifting the weights by NULL_LAG also shifts the null's START, so the
    # rule and its benchmark were scored on different spans. Score the rule on
    # the null's span too, so the comparison is matched.
    _rp = series["riskparity"].reindex(rnull.index).dropna()
    print(f"R9 matched-span check: risk parity on the NULL's span "
          f"({rnull.index[0].date()} -> {rnull.index[-1].date()}) "
          f"= {core.sharpe(_rp):+.3f} vs null {core.sharpe(rnull):+.3f}\n")
    bh = R.mean(axis=1).dropna()
    rows.append(report("buy_hold_basket", bh, pd.Series(0.0, index=bh.index)))

    tab = pd.DataFrame(rows)
    print("=" * 108)
    print("Allocation rules — 21 markets, 1bp per unit turnover")
    print("=" * 108)
    print(tab.to_string(index=False, formatters={
        "sharpe": "{:+.3f}".format, "E1": "{:+.3f}".format, "E2": "{:+.3f}".format,
        "E3": "{:+.3f}".format, "ann_ret": "{:+.2%}".format,
        "ann_vol": "{:.2%}".format, "maxdd": "{:.1%}".format,
        "turnover": "{:.1f}".format}))

    eq = tab[tab.rule == "equal"].iloc[0]
    print(f"\nGate 1/2 — against equal weighting ({eq.sharpe:+.3f}):")
    for _, x in tab.iterrows():
        if x.rule in ("equal", "buy_hold_basket"):
            continue
        eras = all(x[e[:2]] > eq[e[:2]] for e in core.ERAS)
        print(f"  {x.rule:<22} {x.sharpe:+.3f}  "
              f"{'BEATS' if x.sharpe > eq.sharpe else 'loses'}   "
              f"all three eras: {'YES' if eras else 'no'}")

    print("\nGate 3 — plateau across the covariance estimation window")
    pr = []
    for win in WINDOWS:
        r, _ = portfolio(P, R, weights(S, "riskparity", win))
        pr.append(dict(window=win, sharpe=core.sharpe(r)))
    pt = pd.DataFrame(pr)
    print(pt.to_string(index=False, formatters={"sharpe": "{:+.3f}".format}))
    print(f"  spread {pt.sharpe.min():+.3f} to {pt.sharpe.max():+.3f} "
          f"(range {pt.sharpe.max() - pt.sharpe.min():.3f})")

    print("\nGate 6 — costs")
    for c in (1.0, 5.0):
        rp, _ = portfolio(P, R, weights(S, "riskparity", 252), c)
        ew, _ = portfolio(P, R, weights(S, "equal", 252), c)
        print(f"  {c:.0f}bp: risk parity {core.sharpe(rp):+.3f}   "
              f"equal {core.sharpe(ew):+.3f}")

    print("\nGate 7 — against buy-and-hold the same 21-market basket")
    bhr = tab[tab.rule == "buy_hold_basket"].iloc[0]
    best = tab[~tab.rule.isin(["buy_hold_basket", "null_shuffled_weights"])] \
        .sort_values("sharpe").iloc[-1]
    print(f"  best allocation  {best.rule} {best.sharpe:+.3f}  "
          f"ret {best.ann_ret:+.2%}  dd {best.maxdd:.1%}")
    print(f"  buy and hold     {bhr.sharpe:+.3f}  "
          f"ret {bhr.ann_ret:+.2%}  dd {bhr.maxdd:.1%}")
    tab.to_csv("g2_portfolio.csv", index=False)


if __name__ == "__main__":
    main()
