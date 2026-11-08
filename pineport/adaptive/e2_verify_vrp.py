"""
E2 — the check E1's sizing result needs before it can be believed.

VRP = IV - RV. The sizing target in E1 was |forward return| / RV. RV is in BOTH,
and it enters with opposite sign: a low RV raises VRP and shrinks the
denominator. A positive correlation could therefore be pure arithmetic.

So:
  1. size the artefact directly — RV alone against the same normalised target
  2. re-run the target normalised by IV instead, which removes RV from it
  3. ask the question properly — does VRP predict FORWARD realised volatility,
     and does it add anything beyond current RV (partial correlation)?
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import core
from e1_vrp import build, PAIRS, HORIZONS, grid_rho


def partial_rho(d: pd.DataFrame, a: str, b: str, c: str) -> float:
    R = d[[a, b, c]].dropna().rank()
    if len(R) < 12:
        return np.nan
    inv = np.linalg.pinv(R.corr().values)
    return float(-inv[0, 1] / np.sqrt(inv[0, 0] * inv[1, 1]))


def main():
    tabs = {iv: build(iv, m) for iv, m in PAIRS.items()}
    for iv, m in PAIRS.items():
        t = tabs[iv]
        for h in HORIZONS:
            t[f"absIV{h}"] = t[f"fwd{h}"].abs() / (t["IV"] / 100 * np.sqrt(h / core.ppy(t)))
            t[f"fwdRV{h}"] = (t["RV"].shift(-h))

    print("=" * 100)
    print("1. Sizing the artefact — RV alone against |forward return| / RV")
    print("   (if this is strongly negative, E1's positive VRP result is arithmetic)")
    print("=" * 100)
    rows = []
    for iv, m in PAIRS.items():
        r = {"market": m}
        for h in HORIZONS:
            r[f"VRP_h{h}"] = grid_rho(tabs[iv], "VRP", f"absfwd{h}", h)[0]
            r[f"RV_h{h}"] = grid_rho(tabs[iv], "RV", f"absfwd{h}", h)[0]
        rows.append(r)
    t1 = pd.DataFrame(rows)
    print(t1.to_string(index=False, formatters={c: "{:+.3f}".format
          for c in t1.columns if c != "market"}))

    print("\n" + "=" * 100)
    print("2. Artefact removed — same target normalised by IV instead of RV")
    print("=" * 100)
    rows = []
    for iv, m in PAIRS.items():
        r = {"market": m}
        for h in HORIZONS:
            rho, stab, n = grid_rho(tabs[iv], "VRP", f"absIV{h}", h)
            r[f"h{h}"], r[f"s{h}"] = rho, stab
        rows.append(r)
    t2 = pd.DataFrame(rows)
    print(t2.to_string(index=False, formatters={f"h{h}": "{:+.3f}".format for h in HORIZONS}
          | {f"s{h}": "{:.0%}".format for h in HORIZONS}))

    print("\n" + "=" * 100)
    print("3. The question asked properly — does VRP forecast FORWARD realised vol,")
    print("   and does anything survive controlling for current realised vol?")
    print("=" * 100)
    rows = []
    for iv, m in PAIRS.items():
        t = tabs[iv]
        r = {"market": m}
        for h in HORIZONS:
            d = t[["VRP", "IV", "RV", f"fwdRV{h}"]].dropna().iloc[::h]
            r[f"RV_h{h}"] = core.spearman(d["RV"], d[f"fwdRV{h}"])
            r[f"IV_h{h}"] = core.spearman(d["IV"], d[f"fwdRV{h}"])
            r[f"IV|RV_h{h}"] = partial_rho(d, "IV", f"fwdRV{h}", "RV")
            r[f"VRP|RV_h{h}"] = partial_rho(d, "VRP", f"fwdRV{h}", "RV")
        rows.append(r)
    t3 = pd.DataFrame(rows)
    for h in HORIZONS:
        cols = ["market"] + [f"{k}_h{h}" for k in ("RV", "IV", "IV|RV", "VRP|RV")]
        print(f"\n  horizon {h} days")
        print(t3[cols].to_string(index=False, formatters={c: "{:+.3f}".format
              for c in cols[1:]}))
    print("\n  RV = persistence (expected strong).  IV|RV = does implied vol add to it.")
    print("  VRP|RV = does the PREMIUM add anything once current realised vol is held fixed.")
    t1.to_csv("e2_artifact.csv", index=False)
    t2.to_csv("e2_iv_normalised.csv", index=False)
    t3.to_csv("e2_forward_vol.csv", index=False)


if __name__ == "__main__":
    main()
