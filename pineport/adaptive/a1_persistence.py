"""
A1 — is the ex-post optimal crossover lookback persistent?

If the parameter you would adapt towards is not persistent, no adaptation rule
can reach it, and questions A2/A3 are moot. This is the cheapest kill test in
the programme, so it runs first.

A1a  lag-1 Spearman autocorrelation of the block-optimal speed s* = log2(slow*)
A1b  "trade last block's winner" vs the fixed centre pair, and vs the whole
     grid of fixed pairs (percentile rank), plus a picked-loser anti-benchmark
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import core

BLOCKS = {"M": "month", "Q": "quarter", "Y": "year"}


def run_market(mkt: str, freq: str, cost_bps: float = 1.0) -> dict:
    df = core.load(mkt)
    R = core.pair_returns(df, cost_bps=cost_bps)          # daily net returns per pair
    R = R.dropna(how="all")
    key = R.index.tz_localize(None).to_period(freq)

    block_sum = R.groupby(key).sum()                       # block x pair
    counts = R.groupby(key).size()
    ok = counts >= (15 if freq == "M" else 45 if freq == "Q" else 180)
    block_sum = block_sum[ok]
    blocks = block_sum.index

    best = block_sum.idxmax(axis=1)
    worst = block_sum.idxmin(axis=1)
    # top-5 centroid: argmax over 26 noisy pairs is a very high-variance target,
    # so the same question is asked again of a smoothed one.
    order = np.argsort(-block_sum.values, axis=1)
    cols = list(block_sum.columns)
    top5 = [[cols[j] for j in order[i, :5]] for i in range(len(block_sum))]
    s_top5 = pd.Series([np.mean([np.log2(p[1]) for p in row]) for row in top5],
                       index=blocks)
    s_star = pd.Series([np.log2(p[1]) for p in best], index=blocks)
    f_star = pd.Series([np.log2(p[0]) for p in best], index=blocks)

    rho_slow = core.spearman(s_star.values[1:], s_star.values[:-1])
    rho_top5 = core.spearman(s_top5.values[1:], s_top5.values[:-1])
    rho_fast = core.spearman(f_star.values[1:], f_star.values[:-1])

    # --- A1b: strictly out-of-sample "trade last block's winner" -------------
    daily_block = pd.Series(R.index.tz_localize(None).to_period(freq), index=R.index)
    pick, anti, pick5 = {}, {}, {}
    for i in range(1, len(blocks)):
        pick[blocks[i]] = best.iloc[i - 1]
        anti[blocks[i]] = worst.iloc[i - 1]
        pick5[blocks[i]] = top5[i - 1]

    def series_from(choice):
        vals = pd.Series(index=R.index, dtype=float)
        for b, pair in choice.items():
            m = daily_block == b
            vals[m] = R.loc[m, pair]
        return vals.dropna()

    def series_from_basket(choice):
        vals = pd.Series(index=R.index, dtype=float)
        for b, pairs in choice.items():
            m = daily_block == b
            vals[m] = R.loc[m, pairs].mean(axis=1)
        return vals.dropna()

    adaptive = series_from(pick)
    adaptive5 = series_from_basket(pick5)
    antipick = series_from(anti)
    span = adaptive.index

    fixed = {p: R.loc[span, p] for p in core.PAIRS}
    fixed_sharpe = {p: core.sharpe(s) for p, s in fixed.items()}
    adaptive_sharpe = core.sharpe(adaptive)
    centre_sharpe = fixed_sharpe[core.CENTRE_PAIR]
    beat = np.mean([adaptive_sharpe > v for v in fixed_sharpe.values() if not np.isnan(v)])

    era = core.era_of(span)
    per_era = {}
    for name in core.ERAS:
        m = (era == name).values
        if m.sum() < 200:
            continue
        per_era[name] = (core.sharpe(adaptive[m]),
                         core.sharpe(fixed[core.CENTRE_PAIR][m]))

    return dict(
        market=mkt, freq=freq, n_blocks=len(blocks),
        rho_slow=rho_slow, rho_fast=rho_fast, rho_top5=rho_top5,
        adaptive=adaptive_sharpe, adaptive5=core.sharpe(adaptive5),
        centre=centre_sharpe,
        anti=core.sharpe(antipick),
        grid_median=float(np.nanmedian(list(fixed_sharpe.values()))),
        grid_best=float(np.nanmax(list(fixed_sharpe.values()))),
        pct_of_grid_beaten=beat,
        per_era=per_era,
    )


def main():
    rows = []
    for freq in ("M", "Q", "Y"):
        for mkt in core.MARKETS:
            rows.append(run_market(mkt, freq))
    out = pd.DataFrame(rows)
    out.to_pickle("a1_raw.pkl")

    for freq, label in BLOCKS.items():
        sub = out[out.freq == freq]
        print(f"\n=== block = 1 {label} " + "=" * 46)
        t = sub[["market", "n_blocks", "rho_slow", "rho_top5", "adaptive",
                 "adaptive5", "centre", "grid_median", "anti",
                 "pct_of_grid_beaten"]]
        print(t.to_string(index=False,
              formatters={c: "{:.3f}".format for c in
                          ["rho_slow", "rho_top5", "adaptive", "adaptive5",
                           "centre", "grid_median", "anti",
                           "pct_of_grid_beaten"]}))
        print(f"  A1a  median rho(slow) = {sub.rho_slow.median():+.3f}   "
              f"positive in {int((sub.rho_slow > 0).sum())}/11   "
              f"[pass: >= +0.20 and >= 8/11]")
        print(f"  A1a' median rho(top5 centroid) = {sub.rho_top5.median():+.3f}   "
              f"positive in {int((sub.rho_top5 > 0).sum())}/11")
        wins = int((sub.adaptive > sub.centre).sum())
        w5 = int((sub.adaptive5 > sub.centre).sum())
        print(f"  A1b  adaptive beats centre pair in {wins}/11 markets   "
              f"[pass: >= 8/11];  top-5 basket {w5}/11")
        print(f"       mean Sharpe: chase-winner {sub.adaptive.mean():+.3f}  "
              f"top5 {sub.adaptive5.mean():+.3f}  centre {sub.centre.mean():+.3f}  "
              f"grid-median {sub.grid_median.mean():+.3f}  "
              f"chase-LOSER {sub.anti.mean():+.3f}")
        eras = {}
        for _, r in sub.iterrows():
            for e, (a, c) in r.per_era.items():
                eras.setdefault(e, []).append(a > c)
        for e, v in sorted(eras.items()):
            print(f"        {e}: adaptive wins {sum(v)}/{len(v)}")


if __name__ == "__main__":
    main()
