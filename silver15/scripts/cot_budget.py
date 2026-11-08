#!/usr/bin/env python3
"""Power budget for a COT positioning signal. Run BEFORE hypothesising.

NO RETURNS ARE COMPUTED IN THIS FILE. Everything comes from persistence,
cross-market correlation, release timing and span — never from P&L.

WHY THIS ONE IS DIFFERENT FROM EVERY EARLIER BUDGET
---------------------------------------------------
Six families have now failed, all reading the same price series. COT is the
first genuinely NON-PRICE input this project has had with usable history:
what market participants actually hold, published weekly by the CFTC, back
to 1986. It is not a transform of the data already shown to be directionless.

WHAT THIS FILE CHECKS
---------------------
  1. RELEASE TIMING. CFTC publishes Friday for TUESDAY's positions. Using the
     value on its plotted date can read days into the future. The lag must be
     explicit and the update weekday must be verified.
  2. PERSISTENCE. Positioning barely changes week to week. The raw level
     autocorrelates ~0.98, so 1,900 weekly rows are NOT 1,900 observations.
     The transform decides the sample: level, z-score, COT index or change.
  3. CROSS-MARKET INDEPENDENCE. Six markets pooled is only six experiments if
     their positioning is uncorrelated. Metals move together.
  4. THE BAR. 2/sqrt(years), which span alone sets.

A NOTE ON TRANSFORM SELECTION
-----------------------------
Choosing the transform on AUTOCORRELATION is a power decision, not a return
decision, and this file computes no returns. But it is still a choice made
across several candidates, so it must be frozen in the pre-registration
before any P&L is looked at — the same discipline applied to hold length in
the H4 work.

    python cot_budget.py --data ../data_cot
"""

from __future__ import annotations

import argparse
import glob
import os
import re

VERSION = "1.0"
MARKETS = {"088691": "gold", "084691": "silver", "085692": "copper",
           "067651": "wti", "002602": "corn", "099741": "usdx"}


def load(data_dir):
    import numpy as np, pandas as pd
    out = {}
    for f in sorted(glob.glob(os.path.join(data_dir, "cot_*_*.csv"))):
        code = re.search(r"_(\d{6})\.csv$", f)
        if not code:
            continue
        code = code.group(1)
        d = pd.read_csv(f)
        d["t"] = pd.to_datetime(d["time"], unit="s", utc=True)
        d = d.set_index("t").sort_index()
        cols = [c for c in d.columns
                if c not in ("time", "open", "high", "low", "close", "Volume")]
        for c in cols:
            d[c] = pd.to_numeric(d[c], errors="coerce")
        d = d.dropna(subset=cols, how="all")
        out[MARKETS.get(code, code)] = d
    return out


def weekly(d, cols):
    """One row per genuine COT update."""
    upd = d[cols].diff().abs().sum(axis=1) > 1e-9
    return d[upd]


def main():
    import numpy as np, pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data_cot")
    a = ap.parse_args()

    print(f"cot_budget.py v{VERSION}   NO RETURNS COMPUTED\n")
    S = load(a.data)
    print(f"  {len(S)} markets: {', '.join(sorted(S))}\n")

    # ---- 1. release timing -------------------------------------------
    print("1. RELEASE TIMING (CFTC: Friday release for Tuesday positions)")
    print("=" * 74)
    for k, d in sorted(S.items()):
        cols = [c for c in d.columns if "Commercials" in c]
        w = weekly(d, cols)
        wd = pd.Series(w.index).dt.day_name().value_counts()
        top = wd.index[0]
        print(f"  {k:<8} {len(w):>5,} updates, {wd.iloc[0]/len(w):>5.1%} on {top}")
    print("  -> values appear on the RELEASE date. A 1-bar lag is the minimum")
    print("     safe treatment; the pre-registration must state it explicitly.")

    # ---- 2. persistence, by transform --------------------------------
    print("\n2. PERSISTENCE: which transform yields independent observations?")
    print("=" * 74)
    yrs = {k: (d.index.max() - d.index.min()).days / 365.25 for k, d in S.items()}
    print(f"  {'transform':<22}" + "".join(f"{k[:6]:>9}" for k in sorted(S))
          + f"{'mean n_eff':>12}")
    tf = {}
    for name in ("level", "z26", "z52", "index52", "change"):
        neffs, row = [], ""
        for k in sorted(S):
            d = S[k]
            col = "Commercials net"
            w = weekly(d, [c for c in d.columns if "Commercials" in c])[col].dropna()
            if name == "level":
                x = w
            elif name == "z26":
                x = (w - w.rolling(26).mean()) / w.rolling(26).std()
            elif name == "z52":
                x = (w - w.rolling(52).mean()) / w.rolling(52).std()
            elif name == "index52":
                x = w.rolling(52).apply(
                    lambda v: (v.iloc[-1] - v.min()) / (v.max() - v.min())
                    if v.max() > v.min() else 0.5, raw=False)
            else:
                x = w.diff()
            x = x.dropna()
            a1 = x.autocorr(1)
            ne = len(x) * (1 - a1) / (1 + a1) if a1 > -1 else len(x)
            neffs.append(ne)
            row += f"{ne:>9,.0f}"
        tf[name] = float(np.mean(neffs))
        print(f"  {name:<22}{row}{tf[name]:>12,.0f}")

    best_tf = max(tf, key=tf.get)
    print(f"\n  best on independence: '{best_tf}' at {tf[best_tf]:,.0f} mean n_eff")
    print("  NOTE low autocorrelation is necessary, not sufficient. The most")
    print("  independent transform is often the noisiest.")

    # ---- 3. cross-market independence --------------------------------
    print("\n3. ARE THE SIX MARKETS INDEPENDENT?")
    print("=" * 74)
    frames = {}
    for k, d in sorted(S.items()):
        w = weekly(d, [c for c in d.columns if "Commercials" in c])["Commercials net"]
        frames[k] = w.diff() if best_tf == "change" else w
    W = pd.DataFrame(frames).dropna()
    C = W.corr()
    off = C.to_numpy()[~np.eye(len(C), dtype=bool)]
    rho = float(np.mean(np.abs(off)))
    print(C.round(2).to_string())
    m = len(C)
    print(f"\n  mean |correlation| {rho:.3f}  ->  {m} markets behave like "
          f"{m/(1+(m-1)*rho):.1f} independent")

    # ---- 4. the bar ---------------------------------------------------
    print("\n4. THE DETECTABILITY BAR")
    print("=" * 74)
    span = float(np.mean(list(yrs.values())))
    raw_n = sum(len(weekly(d, [c for c in d.columns if "Commercials" in c]))
                for d in S.values())
    eff = tf[best_tf] * m / (1 + (m - 1) * rho)
    print(f"  mean span {span:.1f} years  ->  2-sigma bar "
          f"{2/np.sqrt(span):.2f} annual Sharpe")
    print(f"  raw weekly rows across markets  {raw_n:,}")
    print(f"  effective independent observations  {eff:,.0f}")
    print(f"\n  project comparison:")
    print(f"    price panel (v4)   20.4y  bar 0.44   258 rebalances")
    print(f"    directional (v3)   20.4y  bar 0.44   12,721 trades")
    print(f"    COT                {span:.1f}y  bar {2/np.sqrt(span):.2f}   "
          f"{eff:,.0f} effective")
    if 2/np.sqrt(span) <= 0.40 and eff >= 500:
        print("\n  => lowest bar AND adequate sample. Worth pre-registering.")
    else:
        print("\n  => check both numbers before proceeding.")


if __name__ == "__main__":
    main()
