"""
A3 — does an adaptive lookback beat a fixed one?

One rule family so the comparison is like-for-like:

    position_t = sign(close_t - VMA_t),  held over t+1
    VMA is an EMA whose alpha_t = 2/(L_t + 1)

    fixed        L_t = L0                                   (constant)
    ER-adaptive  Kaufman KAMA smoothing constant            (efficiency ratio)
    vol-scaled   L_t = L0 * (vol_t / vol_ref_t) ** gamma    (gamma=0 -> fixed)
    cycle-scaled L_t = k * dominant_cycle_t

vol_ref_t is an EXPANDING median, so no future information enters the
normalisation. Every adaptive variant collapses to a fixed rule at one of its
parameter values, which is the built-in null.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import core

COST_BPS = 1.0


def vma(close: np.ndarray, L: np.ndarray) -> np.ndarray:
    out = np.empty_like(close)
    out[0] = close[0]
    a = 2.0 / (np.clip(L, 2.0, 500.0) + 1.0)
    for i in range(1, len(close)):
        ai = a[i]
        if not np.isfinite(ai):
            ai = 2.0 / 101.0
        out[i] = out[i - 1] + ai * (close[i] - out[i - 1])
    return out


def kama(close: np.ndarray, er: np.ndarray, fast: int = 2, slow: int = 30) -> np.ndarray:
    fa, sa = 2.0 / (fast + 1), 2.0 / (slow + 1)
    sc = (np.nan_to_num(er, nan=0.0) * (fa - sa) + sa) ** 2
    out = np.empty_like(close)
    out[0] = close[0]
    for i in range(1, len(close)):
        out[i] = out[i - 1] + sc[i] * (close[i] - out[i - 1])
    return out


def evaluate(df: pd.DataFrame, line: np.ndarray) -> pd.Series:
    pos = pd.Series(np.sign(df["close"].values - line), index=df.index).shift(1)
    turn = pos.diff().abs().fillna(0.0)
    return pos * df["ret"] - turn * COST_BPS / 1e4


def variants(df: pd.DataFrame) -> dict[str, pd.Series]:
    close = df["close"].values.astype(float)
    ret = df["ret"]
    vol = core.realised_vol(ret, 63)
    vol_ref = vol.expanding(252).median().shift(1)        # causal normalisation
    cyc = core.dominant_cycle(df["close"])
    er10 = core.efficiency_ratio(df["close"], 10)

    out = {}
    for L0 in (10, 20, 40, 80, 160, 320):
        out[f"fixed_{L0}"] = evaluate(df, vma(close, np.full(len(close), float(L0))))
    for slow in (10, 20, 30, 60, 120):
        out[f"kama_{slow}"] = evaluate(df, kama(close, er10.values, 2, slow))
    for g in (-1.0, -0.5, 0.0, 0.5, 1.0):
        L = (80.0 * (vol / vol_ref) ** g).clip(5, 400).fillna(80.0).values
        out[f"volscale_{g:+.1f}"] = evaluate(df, vma(close, L))
    for k in (0.5, 1.0, 2.0, 3.0, 4.0):
        L = (k * cyc).clip(5, 400).fillna(80.0).values
        out[f"cycle_x{k:g}"] = evaluate(df, vma(close, L))
    return out


def main():
    per_market, pooled = {}, {}
    for m in core.MARKETS:
        df = core.load(m)
        v = variants(df)
        per_market[m] = {k: core.sharpe(s) for k, s in v.items()}
        for k, s in v.items():
            pooled.setdefault(k, []).append(s.rename(m))

    names = list(next(iter(per_market.values())).keys())
    pm = pd.DataFrame(per_market).T[names]

    port = {k: pd.concat(v, axis=1).mean(axis=1) for k, v in pooled.items()}
    port_sharpe = {k: core.sharpe(s) for k, s in port.items()}

    era = core.era_of(next(iter(port.values())).index)
    era_sharpe = {k: {e: core.sharpe(s[(era == e).values]) for e in core.ERAS}
                  for k, s in port.items()}

    print("=" * 96)
    print("Per-market Sharpe, 2005-2026, 1bp per unit turnover")
    print("=" * 96)
    print(pm.to_string(float_format=lambda x: f"{x:+.2f}"))

    print("\n" + "=" * 96)
    print("Equal-weight 11-market portfolio")
    print("=" * 96)
    best_fixed = max(v for k, v in port_sharpe.items() if k.startswith("fixed"))
    rows = []
    for k in names:
        rows.append(dict(rule=k, portfolio=port_sharpe[k],
                         **{e[:2]: era_sharpe[k][e] for e in core.ERAS},
                         beats_best_fixed=port_sharpe[k] > best_fixed,
                         mkts_beating_fixed80=int((pm[k] > pm["fixed_80"]).sum())))
    tab = pd.DataFrame(rows)
    print(tab.to_string(index=False, formatters={c: "{:+.3f}".format
          for c in ["portfolio", "E1", "E2", "E3"]}))
    print(f"\nbest fixed portfolio Sharpe = {best_fixed:+.3f}")
    pm.to_csv("a3_per_market_sharpe.csv")
    tab.to_csv("a3_portfolio.csv", index=False)


if __name__ == "__main__":
    main()
