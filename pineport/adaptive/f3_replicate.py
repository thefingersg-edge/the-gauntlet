"""
F3 — replication of the implied-vol sizing result on markets it was not fitted to.

Runs the FROZEN rule from PREREGISTRATION_IVSIZE_REPLICATION.md against whatever
volatility indices are present in adaptive/macro/. Each pair is scored on its
own; there is no aggregate threshold, because the candidate markets are
near-duplicates of ones already used and an aggregate would let one carry the
other.

Nothing here is tunable. If you find yourself editing a parameter to make it
pass, that is a new candidate, not a replication.
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd
import core
from f1_ivsize import forecasts, position, realised_block_vol, stats, TARGET, BLOCK

MACRO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "macro")

#: implied-vol file stem -> (market, already tested?, correlation with a tested market)
CANDIDATES = [
    ("vxncls",   "nas100usd",  "REPLICATION", "rho 0.927 with SPX500"),
    ("vxslvcls", "xagusd",     "REPLICATION", "rho 0.801 with gold"),
    ("rvxcls",   "us2000usd",  "REPLICATION", "needs US2000_USD from OANDA"),
    ("vxdcls",   "us30usd",    "REPLICATION", "needs US30_USD from OANDA"),
    ("vixcls",   "spx500usd",  "original",    ""),
    ("gvzcls",   "xauusd",     "original",    ""),
    ("ovxcls",   "bcousd",     "original",    ""),
    ("evzcls",   "eurusd",     "original",    ""),
]


def available(stem: str, mkt: str) -> tuple[bool, str]:
    if not os.path.exists(os.path.join(MACRO, f"{stem}.csv")):
        return False, f"no macro/{stem}.csv"
    if not os.path.exists(os.path.join(core.DATA, f"{mkt}_d1.csv")):
        return False, f"no data/{mkt}_d1.csv"
    return True, ""


def score(stem: str, mkt: str) -> dict:
    df = core.load(mkt)
    fc = forecasts(df, stem)
    common = fc["IV"].dropna().index
    d = df.loc[common]
    out = {"market": mkt, "iv": stem.upper().replace("CLS", ""),
           "span": f"{d.index[0].year}-{d.index[-1].year}"}

    for k in ("RV", "IV", "NULL"):
        bv = realised_block_vol(position(d, fc[k].loc[common]), d["ret"]).dropna()
        out[f"{k}_bias"] = (bv - TARGET).abs().mean()
        out[f"{k}_disp"] = (bv / TARGET).std()
        out["n_blocks"] = len(bv)
        if k in ("RV", "IV"):
            era = core.era_of(bv.index)
            for e in core.ERAS:
                m = (era == e).values
                out[f"{k}_{e[:2]}"] = (bv[m] / TARGET).std() if m.sum() >= 10 else np.nan

    # gate 4 — forecasts frozen at the block boundary, no shared bars
    ret = d["ret"]
    g = np.arange(len(ret)) // BLOCK
    fwd = ret.groupby(g).std() * np.sqrt(core.ppy(ret))
    keep = ret.groupby(g).size() >= BLOCK - 3
    for k in ("RV", "IV"):
        frozen = fc[k].loc[common].groupby(g).first().shift(1)
        m = keep & frozen.notna() & fwd.notna()
        a, b = np.log(frozen[m]), np.log(fwd[m])
        out[f"{k}_frozen_rho"] = core.spearman(a, b)
        out[f"{k}_frozen_err"] = float(np.sqrt(((a - b) ** 2).mean()))
    return out


def verdict(r: dict) -> tuple[str, list[str]]:
    fails = []
    if not r["IV_disp"] < r["RV_disp"]:
        fails.append("gate 1 dispersion")
    if not r["IV_bias"] < r["RV_bias"]:
        fails.append("gate 2 bias")
    if not r["IV_disp"] < r["NULL_disp"]:
        fails.append("gate 3 destroyed-timing null")
    if not (r["IV_frozen_rho"] > r["RV_frozen_rho"]
            and r["IV_frozen_err"] < r["RV_frozen_err"]):
        fails.append("gate 4 frozen forecast")
    eras = [e[:2] for e in core.ERAS]
    bad = [e for e in eras
           if not (np.isnan(r.get(f"IV_{e}", np.nan))
                   or r[f"IV_{e}"] < r[f"RV_{e}"])]
    if bad:
        fails.append(f"gate 5 eras {','.join(bad)}")
    return ("PASS" if not fails else "FAIL"), fails


def main():
    rows, skipped = [], []
    for stem, mkt, kind, note in CANDIDATES:
        ok, why = available(stem, mkt)
        if not ok:
            skipped.append((stem, mkt, kind, why or note))
            continue
        r = score(stem, mkt)
        r["kind"], r["note"] = kind, note
        r["verdict"], r["fails"] = verdict(r)
        rows.append(r)

    if skipped:
        print("Not run:")
        for stem, mkt, kind, why in skipped:
            print(f"  {stem:<9} -> {mkt:<11} {kind:<12} {why}")
        print()

    t = pd.DataFrame(rows)
    if t.empty:
        print("Nothing to score yet.")
        return
    print("=" * 104)
    print("F3 — frozen rule, each pair scored on its own")
    print("=" * 104)
    cols = ["iv", "market", "kind", "span", "n_blocks", "RV_disp", "IV_disp",
            "NULL_disp", "RV_bias", "IV_bias", "verdict"]
    print(t[cols].to_string(index=False, formatters={c: "{:.4f}".format for c in
          ["RV_disp", "IV_disp", "NULL_disp", "RV_bias", "IV_bias"]}))
    print("\nfrozen-forecast check (gate 4)")
    print(t[["iv", "market", "RV_frozen_rho", "IV_frozen_rho",
             "RV_frozen_err", "IV_frozen_err"]].to_string(index=False,
          float_format=lambda x: f"{x:.4f}"))
    print("\nper-era dispersion (gate 5)")
    ecols = ["iv", "market"] + [f"{k}_{e[:2]}" for e in core.ERAS for k in ("RV", "IV")]
    print(t[ecols].to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    print("\n" + "=" * 104)
    for _, r in t[t.kind == "REPLICATION"].iterrows():
        if r.verdict == "PASS":
            print(f"  {r.market}: PASS — consistent with the original. "
                  f"Effective sample size is unchanged ({r.note}); this is not "
                  f"additional evidence.")
        else:
            print(f"  {r.market}: FAIL on {', '.join(r.fails)} — and {r.note}. "
                  f"Under the pre-registration this puts the original result for "
                  f"that market's near-twin back to candidate status.")
    if not (t.kind == "REPLICATION").any():
        print("  No replication pairs available yet — pull the volatility indices first.")
    t.to_csv("f3_replication.csv", index=False)


if __name__ == "__main__":
    main()
