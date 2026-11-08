"""
C1 — grid agreement as a SIZE, not a selection.

    A_t = mean over the 26 fixed crossover pairs of sign(SMA_fast - SMA_slow)

Nothing is fitted. The question is whether |A| — how much the lookbacks agree —
is worth anything as an exposure multiplier, over and above (a) its own sign,
(b) a single good fixed lookback, (c) the mere distribution of exposures, and
(d) volatility targeting.

Every position is decided at bar t's close and held over t+1. Costs are charged
on |change in position|, so the netting of the aggregate is counted honestly.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import core

VOL_TARGET = 0.10
VOL_WIN = 60
LEV_CAP = 3.0
NULL_LAG = 750          # far enough that |A| is unrelated to today's state


def agreement(close: pd.Series) -> pd.Series:
    smas = {n: close.rolling(n).mean() for n in sorted(set(core.FAST + core.SLOW))}
    sig = [np.sign(smas[f] - smas[s]) for f, s in core.PAIRS]
    return pd.concat(sig, axis=1).mean(axis=1)


def stats(pos: pd.Series, ret: pd.Series, cost_bps: float) -> dict:
    p = pos.shift(1)
    turn = p.diff().abs().fillna(0.0)
    r = (p * ret - turn * cost_bps / 1e4).dropna()
    eq = (1 + r).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    yrs = max(core.years(r), 1e-9)
    return dict(sharpe=core.sharpe(r), ann_ret=eq.iloc[-1] ** (1 / yrs) - 1,
                ann_vol=core.ann_vol(r), maxdd=dd,
                exposure=p.abs().mean(), turnover=turn.sum() / yrs, series=r)


def build(df: pd.DataFrame) -> dict[str, pd.Series]:
    close, ret = df["close"], df["ret"]
    A = agreement(close)
    sA, aA = np.sign(A), A.abs()
    vol = ret.rolling(VOL_WIN).std() * np.sqrt(core.ppy(ret))
    scale = (VOL_TARGET / vol).clip(upper=LEV_CAP)
    fixed160 = np.sign(close - close.rolling(160).mean())

    out = {
        "agree_linear": A,
        "agree_sign_only": sA,
        "agree_g0.5": sA * aA ** 0.5,
        "agree_g1.5": sA * aA ** 1.5,
        "agree_g2": sA * aA ** 2.0,
        "gate_0.2": sA.where(aA >= 0.2, 0.0),
        "gate_0.4": sA.where(aA >= 0.4, 0.0),
        "gate_0.6": sA.where(aA >= 0.6, 0.0),
        "gate_0.8": sA.where(aA >= 0.8, 0.0),
        "fixed_160": fixed160,
        "fixed_centre_pair": np.sign(close.rolling(16).mean() - close.rolling(128).mean()),
        "null_shuffled_size": sA * aA.shift(NULL_LAG),
        "voltgt_on_fixed160": fixed160 * scale,
        "voltgt_on_agree_sign": sA * scale,
        "agree_x_voltgt": A * scale,
    }
    return {k: v.astype(float) for k, v in out.items()}


def main():
    for cost in (1.0, 5.0):
        per_market, pooled = {}, {}
        for m in core.MARKETS:
            df = core.load(m)
            for k, pos in build(df).items():
                s = stats(pos, df["ret"], cost)
                per_market.setdefault(k, {})[m] = s["sharpe"]
                pooled.setdefault(k, []).append(s["series"].rename(m))
                if cost == 1.0:
                    for f in ("ann_ret", "ann_vol", "maxdd", "exposure", "turnover"):
                        per_market.setdefault(f"_{f}", {}).setdefault(k, []).append(s[f])

        rows = []
        for k in build(core.load("xauusd")).keys():
            port = pd.concat(pooled[k], axis=1).mean(axis=1)
            era = core.era_of(port.index)
            pm = pd.Series(per_market[k])
            row = dict(rule=k, portfolio=core.sharpe(port),
                       **{e[:2]: core.sharpe(port[(era == e).values]) for e in core.ERAS},
                       median_mkt=pm.median(),
                       beats_centre=int((pm > pd.Series(per_market["fixed_centre_pair"])).sum()),
                       beats_null=int((pm > pd.Series(per_market["null_shuffled_size"])).sum()))
            if cost == 1.0:
                row["exposure"] = np.mean(per_market["_exposure"][k])
                row["turnover"] = np.mean(per_market["_turnover"][k])
            rows.append(row)
        tab = pd.DataFrame(rows)
        print("=" * 108)
        print(f"C1 — equal-weight 11-market portfolio, {cost:.0f}bp per unit turnover")
        print("=" * 108)
        fmt = {c: "{:+.3f}".format for c in ["portfolio", "E1", "E2", "E3", "median_mkt"]}
        if cost == 1.0:
            fmt.update(exposure="{:.2f}".format, turnover="{:.1f}".format)
        print(tab.to_string(index=False, formatters=fmt))
        tab.to_csv(f"c1_agreement_{int(cost)}bp.csv", index=False)
        if cost == 1.0:
            pd.DataFrame(per_market).drop(columns=[c for c in per_market if c.startswith("_")]) \
              .to_csv("c1_per_market.csv")


if __name__ == "__main__":
    main()
