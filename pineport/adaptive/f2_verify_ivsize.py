"""
F2 — the two gates F1 left open, plus the forecast comparison stated cleanly.

GATE 7 (shared term).  In F1 the position is re-sized every day, so by day k of
a 21-day block the RV forecast already contains k-1 bars OF THAT BLOCK. That
helps the RV rule, but it means the metric and the forecast share bars. Here the
forecast is FROZEN at the last bar before each block and scored against that
block's realised volatility, so neither rule sees a single bar of what it is
predicting.

GATE 5 (plateau).  Sweep the causal rescaling window and the leverage cap.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import core
from e1_vrp import PAIRS
from f1_ivsize import forecasts, position, realised_block_vol, stats, TARGET, BLOCK


def frozen_test():
    print("=" * 96)
    print("GATE 7 — forecast frozen at the block boundary; no shared bars with the target")
    print("=" * 96)
    rows = []
    for iv_name, mkt in PAIRS.items():
        df = core.load(mkt)
        fc = forecasts(df, iv_name)
        common = fc["IV"].dropna().index
        d = df.loc[common]
        ret = d["ret"]
        g = np.arange(len(ret)) // BLOCK
        fwd = ret.groupby(g).std() * np.sqrt(core.ppy(ret))   # what happens in the block
        keep = ret.groupby(g).size() >= BLOCK - 3
        r = {"market": mkt, "n": int(keep.sum())}
        for k in ("RV", "IV", "BLEND"):
            f = fc[k].loc[common]
            frozen = f.groupby(g).first().shift(1)          # last known before the block
            m = keep & frozen.notna() & fwd.notna()
            a, b = np.log(frozen[m]), np.log(fwd[m])
            r[f"{k}_rho"] = core.spearman(a, b)
            r[f"{k}_rmse"] = float(np.sqrt(((a - b) ** 2).mean()))
        rows.append(r)
    t = pd.DataFrame(rows)
    print(t.to_string(index=False, formatters={c: "{:.4f}".format
          for c in t.columns if c not in ("market", "n")}))
    print(f"\n  IV beats RV on rank correlation in "
          f"{int((t.IV_rho > t.RV_rho).sum())}/4, on error in "
          f"{int((t.IV_rmse < t.RV_rmse).sum())}/4   [gate 7: must survive]")
    print(f"  BLEND beats IV on error in {int((t.BLEND_rmse < t.IV_rmse).sum())}/4")
    t.to_csv("f2_frozen_forecast.csv", index=False)


def plateau():
    print("\n" + "=" * 96)
    print("GATE 5 — plateau across the causal rescaling window and the leverage cap")
    print("=" * 96)
    rows = []
    for win in (126, 252, 504, 1008):
        r = {"rescale_win": win}
        for cap in (2.0, 3.0, 5.0, 99.0):
            disps = []
            for iv_name, mkt in PAIRS.items():
                df = core.load(mkt)
                fc = forecasts(df, iv_name, rescale_win=win)
                common = fc["IV"].dropna().index
                d = df.loc[common]
                bv = realised_block_vol(position(d, fc["IV"].loc[common], cap=cap),
                                        d["ret"]).dropna()
                disps.append((bv / TARGET).std())
            r[f"cap{cap:g}"] = float(np.mean(disps))
        rows.append(r)
    t = pd.DataFrame(rows)
    print("  mean dispersion of realised vol around target (lower is better)")
    print(t.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    v = t[[c for c in t.columns if c.startswith("cap")]].values
    print(f"\n  spread across all 16 settings: {v.min():.4f} to {v.max():.4f} "
          f"(range {v.max()-v.min():.4f})")
    t.to_csv("f2_plateau.csv", index=False)


def lookahead():
    print("\n" + "=" * 96)
    print("GATE 2.5 — lookahead audit on the sized rule")
    print("=" * 96)
    for iv_name, mkt in PAIRS.items():
        df = core.load(mkt)
        fc = forecasts(df, iv_name)
        common = fc["IV"].dropna().index
        d = df.loc[common]
        p = position(d, fc["IV"].loc[common])
        a, b = core.sharpe(stats(p, d["ret"])), core.sharpe(stats(p.shift(1), d["ret"]))
        bv = realised_block_vol(p.shift(1), d["ret"]).dropna()
        print(f"  {mkt:<10} sharpe {a:+.3f} -> {b:+.3f}   "
              f"calibration dispersion with a day's delay {(bv/TARGET).std():.4f}")


if __name__ == "__main__":
    frozen_test()
    plateau()
    lookahead()
