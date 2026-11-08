"""
A2 — is next quarter's best crossover SPEED predictable from today's state?

Headline target is the FAST-minus-SLOW spread, because that is the decision:
"should the crossover be faster or slower over the coming quarter".

    FAST bucket : pairs with slow lookback in {8, 16, 32}
    SLOW bucket : pairs with slow lookback in {128, 256}
    spread_t    = mean block return of FAST - mean block return of SLOW

Predictors are the eight pre-registered state variables, stamped on the LAST
BAR of the PRIOR block, so nothing from the scored block is used.

Pre-registered pass: |rho| >= 0.15 with the SAME SIGN in all three eras, in
>= 7 of 11 markets, for at least one state variable.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import core

FREQ = "Q"
FAST_BUCKET = [p for p in core.PAIRS if p[1] <= 32]
SLOW_BUCKET = [p for p in core.PAIRS if p[1] >= 128]
STATES = ["efficiency_ratio", "realised_vol", "vol_of_vol", "variance_ratio",
          "hurst", "adx", "dominant_cycle", "autocorr_1", "abs_autocorr_1"]


def market_table(mkt: str) -> pd.DataFrame:
    df = core.load(mkt)
    R = core.pair_returns(df).dropna(how="all")
    st = core.state_frame(df)

    key = R.index.tz_localize(None).to_period(FREQ)
    block_sum = R.groupby(key).sum()
    counts = R.groupby(key).size()
    block_sum = block_sum[counts >= 45]

    spread = (block_sum[FAST_BUCKET].mean(axis=1)
              - block_sum[SLOW_BUCKET].mean(axis=1))
    order = np.argsort(-block_sum.values, axis=1)
    cols = list(block_sum.columns)
    s_top5 = pd.Series(
        [np.mean([np.log2(cols[j][1]) for j in order[i, :5]])
         for i in range(len(block_sum))], index=block_sum.index)

    # state stamped on the last bar of each block, then lagged one block
    st_block = st.groupby(st.index.tz_localize(None).to_period(FREQ)).last()
    st_block = st_block.reindex(block_sum.index).shift(1)

    out = st_block.copy()
    out["spread"] = spread
    out["s_top5"] = s_top5
    ends = block_sum.index.to_timestamp(how="end")
    out["era"] = [next((n for n, (a, b) in core.ERAS.items()
                        if pd.Timestamp(a) <= t <= pd.Timestamp(b)), None)
                  for t in ends]
    return out.dropna(subset=["spread"])


def main():
    tables = {m: market_table(m) for m in core.MARKETS}
    pooled = pd.concat(tables.values(), keys=tables.keys(), names=["market"])

    for target in ("spread", "s_top5"):
        print(f"\n{'='*78}\nTARGET: {target}   "
              f"({'fast-minus-slow block return' if target=='spread' else 'top-5 centroid speed'})\n{'='*78}")
        rows = []
        for s in STATES:
            per_market = []
            for m, t in tables.items():
                by_era = [core.spearman(t.loc[t.era == e, s], t.loc[t.era == e, target])
                          for e in core.ERAS]
                full = core.spearman(t[s], t[target])
                signs = [np.sign(x) for x in by_era if not np.isnan(x)]
                consistent = len(signs) == 3 and abs(sum(signs)) == 3
                strong = consistent and abs(np.nanmean(by_era)) >= 0.15
                per_market.append((m, full, by_era, consistent, strong))
            n_cons = sum(p[3] for p in per_market)
            n_strong = sum(p[4] for p in per_market)
            pooled_by_era = [core.spearman(pooled.loc[pooled.era == e, s],
                                           pooled.loc[pooled.era == e, target])
                             for e in core.ERAS]
            rows.append(dict(state=s,
                             pooled_E1=pooled_by_era[0], pooled_E2=pooled_by_era[1],
                             pooled_E3=pooled_by_era[2],
                             pooled_all=core.spearman(pooled[s], pooled[target]),
                             sign_consistent=f"{n_cons}/11",
                             consistent_and_strong=f"{n_strong}/11"))
        tab = pd.DataFrame(rows)
        print(tab.to_string(index=False, formatters={c: "{:+.3f}".format for c in
              ["pooled_E1", "pooled_E2", "pooled_E3", "pooled_all"]}))

    # --- tercile view: does a high state reading actually favour fast? -------
    print(f"\n{'='*78}\nTERCILE VIEW — mean fast-minus-slow spread by tercile of "
          f"the prior quarter's state\n{'='*78}")
    rows = []
    for s in STATES:
        r = {"state": s}
        for e in list(core.ERAS) + ["ALL"]:
            sub = pooled if e == "ALL" else pooled[pooled.era == e]
            sub = sub[[s, "spread"]].dropna()
            if len(sub) < 30:
                r[e] = np.nan
                continue
            q = pd.qcut(sub[s], 3, labels=False, duplicates="drop")
            r[e] = sub.spread[q == 2].mean() - sub.spread[q == 0].mean()
        rows.append(r)
    t = pd.DataFrame(rows)
    t["all_same_sign"] = [abs(sum(np.sign(v) for v in row[1:4])) == 3
                          for row in t.itertuples(index=False)]
    print(t.to_string(index=False, formatters={c: "{:+.4f}".format
          for c in list(core.ERAS) + ["ALL"]}))
    pooled.to_pickle("a2_pooled.pkl")


if __name__ == "__main__":
    main()
