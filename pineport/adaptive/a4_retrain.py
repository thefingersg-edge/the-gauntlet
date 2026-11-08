"""
A4 — how often should the parameters be re-fitted?

The premise being tested: "the market has shifted, so the model needs
retraining." Implemented as the thing anyone actually does — pick the pair
that did best over the trailing N days, trade it for the next M days, repeat.

N = inf, M = inf is "never retrain".  Everything is strictly out of sample:
selection uses data up to the rebalance bar, the position starts the next bar.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import core

WINDOWS = [63, 126, 252, 504, 1008, "expanding"]
HOLDS = [21, 63, 252]


def selection_series(R: pd.DataFrame, N, M: int) -> pd.Series:
    score = (R.expanding(252).sum() if N == "expanding" else R.rolling(N).sum())
    score = score.shift(1)                       # known at the rebalance bar
    pick = score.idxmax(axis=1)
    mask = np.zeros(len(R), dtype=bool)
    mask[::M] = True
    pick = pick.where(pd.Series(mask, index=R.index)).ffill()
    vals = pd.Series(index=R.index, dtype=float)
    for pair in R.columns:
        m = (pick == pair).values
        if m.any():
            vals[m] = R.loc[m, pair]
    return vals.dropna()


def main():
    curves = {}
    for m in core.MARKETS:
        df = core.load(m)
        R = core.pair_returns(df).dropna(how="all")
        for N in WINDOWS:
            for M in HOLDS:
                key = (f"{N}", M)
                curves.setdefault(key, []).append(selection_series(R, N, M).rename(m))
        for label, pair in (("never_centre", core.CENTRE_PAIR),):
            curves.setdefault((label, 0), []).append(R[pair].rename(m))
        curves.setdefault(("never_gridmean", 0), []).append(
            R.mean(axis=1).rename(m))

    rows = []
    for key, seqs in curves.items():
        port = pd.concat(seqs, axis=1).mean(axis=1)
        era = core.era_of(port.index)
        rows.append(dict(train=key[0], hold=key[1], portfolio=core.sharpe(port),
                         **{e[:2]: core.sharpe(port[(era == e).values])
                            for e in core.ERAS},
                         n_markets=len(seqs)))
    tab = pd.DataFrame(rows)
    order = {"never_centre": -2, "never_gridmean": -1, "expanding": 9999}
    tab["_o"] = tab.train.map(lambda x: order.get(x, int(x) if x.isdigit() else 0))
    tab = tab.sort_values(["_o", "hold"]).drop(columns="_o")
    print("=" * 78)
    print("A4 — retrain frequency, equal-weight 11-market portfolio, 1bp costs")
    print("   train = trailing window used to pick the pair (days)")
    print("   hold  = bars before the next re-pick")
    print("=" * 78)
    print(tab.to_string(index=False, formatters={c: "{:+.3f}".format
          for c in ["portfolio", "E1", "E2", "E3"]}))
    tab.to_csv("a4_retrain.csv", index=False)


if __name__ == "__main__":
    main()
