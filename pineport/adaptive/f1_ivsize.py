"""
F1 — sizing off implied volatility instead of trailing realised volatility.

Held to ../GAUNTLET.md and PREREGISTRATION_IVSIZE.md.

    position = sign(A) * clip(target / vol_forecast, 0, cap)

Direction is identical across all rules; only the forecast in the denominator
changes. Implied vol is rescaled by an EXPANDING mean ratio so the two rules
carry the same average exposure and differ only in timing (GAUNTLET 1.4).

PRIMARY claim is calibration. SECONDARY is Sharpe. Stated in that order before
the run, and reported in that order whatever happens.
"""
from __future__ import annotations
import os, sys
import numpy as np
import pandas as pd
import core
from c1_agreement import agreement
from e1_vrp import iv_on, PAIRS

TARGET = 0.10
CAP = 3.0
RV_WIN = 60
BLOCK = 21              # calibration measured on non-overlapping 21-day blocks
NULL_LAG = 750


def forecasts(df: pd.DataFrame, iv_name: str, rescale_win: int = 252):
    ret = df["ret"]
    rv = ret.rolling(RV_WIN).std() * np.sqrt(core.ppy(ret))
    iv = iv_on(iv_name, df.index) / 100.0
    # causal debiasing: expanding mean ratio, known only from the past
    ratio = (rv.expanding(rescale_win).mean() / iv.expanding(rescale_win).mean()).shift(1)
    iv_s = iv * ratio
    return dict(
        RV=rv,
        IV=iv_s,
        BLEND=0.5 * rv + 0.5 * iv_s,
        NULL=iv_s.shift(NULL_LAG),          # same distribution, timing destroyed
    )


def position(df, fc, target=TARGET, cap=CAP):
    sA = np.sign(agreement(df["close"])).astype(float)
    return (sA * (target / fc).clip(upper=cap)).astype(float)


def realised_block_vol(pos: pd.Series, ret: pd.Series) -> pd.Series:
    """annualised vol of the SIZED position, on non-overlapping BLOCK windows."""
    r = (pos.shift(1) * ret).dropna()
    g = np.arange(len(r)) // BLOCK
    v = r.groupby(g).std() * np.sqrt(core.ppy(r))
    n = r.groupby(g).size()
    idx = r.index[[i * BLOCK for i in v.index if i * BLOCK < len(r)]]
    v = v.iloc[:len(idx)]
    v.index = idx
    return v[n.iloc[:len(idx)].values >= BLOCK - 3]


def stats(pos, ret, cost_bps=1.0):
    p = pos.shift(1)
    turn = p.diff().abs().fillna(0.0)
    return (p * ret - turn * cost_bps / 1e4).dropna()


def main():
    rows_cal, rows_sharpe, per_era = [], [], []
    for iv_name, mkt in PAIRS.items():
        df = core.load(mkt)
        fc = forecasts(df, iv_name)
        common = fc["IV"].dropna().index
        df2 = df.loc[common]
        r = {"market": mkt, "n_blocks": None}
        s = {"market": mkt}
        for k in ("RV", "IV", "BLEND", "NULL"):
            pos = position(df2, fc[k].loc[common])
            bv = realised_block_vol(pos, df2["ret"]).dropna()
            r[f"{k}_bias"] = (bv - TARGET).abs().mean()
            r[f"{k}_disp"] = (bv / TARGET).std()
            r["n_blocks"] = len(bv)
            s[f"{k}_sharpe"] = core.sharpe(stats(pos, df2["ret"]))
            s[f"{k}_sharpe5"] = core.sharpe(stats(pos, df2["ret"], 5.0))
            s[f"{k}_expo"] = pos.abs().mean()
            if k in ("RV", "IV"):
                era = core.era_of(bv.index)
                for e in core.ERAS:
                    m = (era == e).values
                    if m.sum() >= 10:
                        per_era.append(dict(market=mkt, era=e, rule=k,
                                            bias=(bv[m] - TARGET).abs().mean(),
                                            disp=(bv[m] / TARGET).std()))
        rows_cal.append(r)
        rows_sharpe.append(s)

    cal = pd.DataFrame(rows_cal)
    print("=" * 100)
    print("PRIMARY — calibration.  Realised vol of the sized position vs the 10% target,")
    print("          on non-overlapping 21-day blocks.  Lower is better on both columns.")
    print("=" * 100)
    cols = ["market", "n_blocks"] + [f"{k}_{m}" for k in ("RV", "IV", "BLEND", "NULL")
                                     for m in ("bias", "disp")]
    print(cal[cols].to_string(index=False, formatters={c: "{:.4f}".format
          for c in cols if c not in ("market", "n_blocks")}))
    for m in ("bias", "disp"):
        w = int((cal[f"IV_{m}"] < cal[f"RV_{m}"]).sum())
        wn = int((cal[f"IV_{m}"] < cal[f"NULL_{m}"]).sum())
        wb = int((cal[f"BLEND_{m}"] < cal[f"IV_{m}"]).sum())
        print(f"  {m}: IV beats RV on {w}/4  [gate: >=3/4] · "
              f"IV beats destroyed-timing null on {wn}/4  [gate: >=3/4] · "
              f"BLEND beats IV on {wb}/4")

    print("\n" + "=" * 100)
    print("Gate 3 — does it hold in every era?")
    print("=" * 100)
    pe = pd.DataFrame(per_era)
    piv = pe.pivot_table(index=["market", "era"], columns="rule", values=["bias", "disp"])
    print(piv.to_string(float_format=lambda x: f"{x:.4f}"))
    won = piv[("bias", "IV")] < piv[("bias", "RV")]
    print(f"\n  IV better on bias in {int(won.sum())}/{len(won)} market-era cells")

    print("\n" + "=" * 100)
    print("SECONDARY — Sharpe.  Underpowered by pre-registration (effective N ~ 2).")
    print("=" * 100)
    sh = pd.DataFrame(rows_sharpe)
    print(sh.to_string(index=False, formatters={c: "{:+.3f}".format
          for c in sh.columns if c != "market"}))
    for c, lbl in (("sharpe", "1bp"), ("sharpe5", "5bp")):
        print(f"  {lbl}: IV beats RV on {int((sh[f'IV_{c}'] > sh[f'RV_{c}']).sum())}/4")
    cal.to_csv("f1_calibration.csv", index=False)
    sh.to_csv("f1_sharpe.csv", index=False)


if __name__ == "__main__":
    main()
