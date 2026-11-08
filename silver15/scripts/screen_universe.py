#!/usr/bin/env python3
"""Rank candidate pairs on AFFORDABILITY and SAMPLE. Never on returns.

This file deliberately does not compute P&L, win rates, or anything that could
rank a pair by how well it performed. That is not an oversight -- it is the
control. Choosing an instrument because it is cheap and well-sampled is a
legitimate design decision made before the experiment. Choosing one because it
backtested well is how this project ended up on copper/palladium, whose
apparent edge turned out to be 80% a hedging artefact.

What it reports, per pair:

  cost/vol      round-trip spread divided by the residual's per-bar volatility.
                This is the number that killed every previous test. Below ~0.15
                is comfortable; above ~0.35 the barrier cannot be reached.
  break-even    the win rate needed at barriers +/-3.0, given that cost.
  beta / bind   the hedge ratio and how often the clip bites. A pair whose clip
                binds heavily is not hedged at all.
  trades/yr     independent (non-overlapping) entries available.
  min edge      smallest edge detectable at 3 sd given the sample.

    python screen_universe.py --data ../data_universe
"""

from __future__ import annotations

import argparse
import itertools
import os
import sys

VERSION = "1.0"

# MEASURED round-trip spreads, fraction of price (oanda_intraday --sides,
# 2026-06 -> 2026-08). Metals carried over for comparison.
SPREAD_REL = {
    "spx500usd": 0.50 / 7502.80,   "nas100usd": 2.80 / 29509.20,
    "de30eur":   3.00 / 25023.60,  "us2000usd": 0.40 / 2965.77,
    "eu50eur":   1.40 / 6273.10,
    "usdcad":  0.00018 / 1.41,     "eurusd":  0.00016 / 1.14,
    "gbpusd":  0.00019 / 1.34,     "eurgbp":  0.00014 / 0.86,
    "audusd":  0.00013 / 0.70,     "audnzd":  0.00026 / 1.21,
    "nzdusd":  0.00015 / 0.58,
    "bcousd":     0.040 / 85.60,   "wticousd":   0.040 / 79.89,
    # second batch, measured 2026-06 -> 2026-08
    "us30usd":   3.50 / 52219.00,  "uk100gbp":  1.80 / 10509.30,
    "nl25eur":   0.30 / 1081.74,   "ch20chf":   2.50 / 14241.50,
    "jp225usd": 22.00 / 67193.20,  "hk33hkd":   6.00 / 24673.60,
    "eurjpy":   0.02700 / 185.26,  "gbpjpy":   0.03300 / 215.06,
    "eurchf":   0.00016 / 0.92,    "usdchf":   0.00015 / 0.81,
    "euraud":   0.00036 / 1.64,    "nzdcad":   0.00027 / 0.82,
    "fr40eur":   1.40 / 8380.40,   "au200aud":  3.20 / 8815.20,
}
LABEL = {
    "spx500usd": "SPX500", "nas100usd": "NAS100", "us2000usd": "US2000",
    "de30eur": "DAX", "eu50eur": "EU50", "usdcad": "USDCAD",
    "eurusd": "EURUSD", "gbpusd": "GBPUSD", "eurgbp": "EURGBP",
    "audusd": "AUDUSD", "audnzd": "AUDNZD", "nzdusd": "NZDUSD",
    "bcousd": "Brent", "wticousd": "WTI",
    "us30usd": "US30", "uk100gbp": "UK100", "nl25eur": "AEX",
    "ch20chf": "SMI", "jp225usd": "JP225", "hk33hkd": "HK33",
    "eurjpy": "EURJPY", "gbpjpy": "GBPJPY", "eurchf": "EURCHF",
    "usdchf": "USDCHF", "euraud": "EURAUD", "nzdcad": "NZDCAD",
    "fr40eur": "FR40", "au200aud": "AU200",
}

# Pairs with a stated structural mechanism. Anything not on this list is
# reported but flagged: a cheap pair with no reason to cointegrate is a
# data-mining opportunity, not a strategy.
MECHANISM = {
    ("bcousd", "wticousd"): "same crude, different delivery point; physical arbitrage",
    ("spx500usd", "nas100usd"): "overlapping constituents, one economy",
    ("spx500usd", "us2000usd"): "same economy, different market cap",
    ("nas100usd", "us2000usd"): "same economy, growth vs small-cap",
    ("de30eur", "eu50eur"): "DAX names are a large part of EU50",
    ("audusd", "nzdusd"): "adjacent commodity exporters, correlated policy",
    ("eurusd", "gbpusd"): "both vs USD; EURGBP is the residual by construction",
    ("usdcad", "wticousd"): "Canadian terms of trade run through crude",
    ("usdcad", "bcousd"): "Canadian terms of trade run through crude",
    # --- US index complex: same economy, overlapping constituents ---
    ("us30usd", "spx500usd"): "Dow names are all in the S&P 500",
    ("us30usd", "nas100usd"): "same economy, industrials vs tech",
    ("us30usd", "us2000usd"): "same economy, mega vs small cap",
    # --- European index complex ---
    ("uk100gbp", "eu50eur"): "adjacent European economies, shared macro",
    ("nl25eur", "eu50eur"): "AEX names sit inside EU50",
    ("ch20chf", "eu50eur"): "adjacent European economies, shared macro",
    ("de30eur", "uk100gbp"): "adjacent European economies, shared macro",
    ("de30eur", "nl25eur"): "adjacent European economies, shared macro",
    # --- Asian ---
    ("jp225usd", "hk33hkd"): "Asian session risk appetite, shared regional flow",
    # --- FX crosses sharing a leg: the shared currency IS the mechanism ---
    ("eurjpy", "gbpjpy"): "share the JPY leg; EURGBP is the residual",
    ("eurchf", "usdchf"): "share the CHF leg; EURUSD is the residual",
    ("euraud", "audusd"): "share the AUD leg",
    ("nzdcad", "usdcad"): "share the CAD leg",
    ("eurjpy", "eurusd"): "share the EUR leg; USDJPY is the residual",
    ("fr40eur", "de30eur"): "core euro-area equity, shared currency and macro",
    ("fr40eur", "eu50eur"): "CAC names sit inside EU50",
    ("fr40eur", "nl25eur"): "core euro-area equity, shared currency and macro",
    ("au200aud", "hk33hkd"): "Asian session, shared regional risk appetite",
    ("au200aud", "jp225usd"): "Asian session, shared regional risk appetite",
}

BETA_WINDOW, RESID_WINDOW, Z_WINDOW = 120, 30, 120
# A ZERO floor silently destroys every inversely-correlated pair. USD/CAD vs
# crude has a raw beta of -1.24 (oil up -> CAD strengthens -> USDCAD falls);
# clipping that to 0 removes the hedge entirely and the pair then looks cheap
# because only one leg's spread is being paid. The floor must admit negative
# betas -- an inverse hedge is a hedge. bind% below is the check.
BETA_LO, BETA_HI = -6.0, 6.0
ENTRY_Z, MAX_HOLD, VOL_WINDOW, TP = 2.0, 8, 14, 3.0


def load(data_dir):
    import pandas as pd
    out = {}
    for stem in SPREAD_REL:
        p = os.path.join(data_dir, f"{stem}_4h.csv")
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p)
        t = d.columns[0]
        d[t] = pd.to_datetime(d[t], utc=True)
        out[stem] = d.set_index(t).sort_index()["close"]
    return out


def stats(a, b, sa, sb):
    import numpy as np, pandas as pd
    idx = a.index.intersection(b.index)
    if len(idx) < 2000:
        return None
    ra = pd.Series(np.log(a.loc[idx].to_numpy(float)), index=idx).diff()
    rb = pd.Series(np.log(b.loc[idx].to_numpy(float)), index=idx).diff()
    raw = (ra.rolling(BETA_WINDOW).cov(rb)
           / rb.rolling(BETA_WINDOW).var().replace(0, np.nan))
    beta = raw.clip(BETA_LO, BETA_HI)
    bind = float(((raw <= BETA_LO) | (raw >= BETA_HI)).mean())
    resid = ra - beta * rb
    svol = resid.rolling(VOL_WINDOW).std()
    cum = resid.rolling(RESID_WINDOW).sum()
    z = (cum - cum.rolling(Z_WINDOW).mean()) / cum.rolling(Z_WINDOW).std()

    cost = 2 * (sa / 2 + beta.abs() * sb / 2)
    ratio = float((cost / svol).replace([np.inf, -np.inf], np.nan).median())

    fired = (z.abs() >= ENTRY_Z).to_numpy()
    kept, last = [], -10**9
    for i in np.flatnonzero(fired):
        if i - last >= MAX_HOLD:
            kept.append(i); last = i
    years = (idx[-1] - idx[0]).days / 365.25
    return dict(cost_ratio=ratio, beta=float(raw.median()), bind=bind,
                n=len(kept), per_year=len(kept)/years, years=years)


def main():
    import numpy as np
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data_universe")
    a = ap.parse_args()

    print(f"screen_universe.py v{VERSION}   NO RETURNS ARE COMPUTED IN THIS FILE")
    s = load(a.data)
    print(f"  {len(s)} instruments\n")

    print("MEASURED SPREADS (round trip, % of price)")
    print("=" * 78)
    for k, v in sorted(SPREAD_REL.items(), key=lambda kv: kv[1]):
        if k in s:
            print(f"  {LABEL[k]:<10} {v*100:.4f}%")
    print(f"  {'-- gold':<10} 0.0151%   {'-- silver':<10} 0.0600%   "
          f"{'-- palladium':<12} 0.2367%   (metals, for comparison)")

    rows = []
    for x, y in itertools.combinations(sorted(s), 2):
        st = stats(s[x], s[y], SPREAD_REL[x], SPREAD_REL[y])
        if not st:
            continue
        mech = MECHANISM.get((x, y)) or MECHANISM.get((y, x))
        st.update(pair=f"{LABEL[x]}/{LABEL[y]}", mech=mech)
        # break-even win rate at symmetric barriers +/-TP
        st["be"] = 0.5 + st["cost_ratio"] / (2 * TP)
        st["edge"] = st["be"] - 0.5
        st["need"] = 165 * (0.0340 / (st["edge"] / 3.0)) ** 2 if st["edge"] > 0 else np.inf
        rows.append(st)

    rows.sort(key=lambda r: r["cost_ratio"])
    print("\nPAIRS WITH A STATED MECHANISM  (ranked by cost/vol -- lower is better)")
    print("=" * 78)
    hdr = (f"  {'pair':<18}{'cost/vol':>9}{'break-even':>11}{'beta':>7}"
           f"{'bind':>7}{'trades/y':>9}{'n':>7}")
    print(hdr)
    for r in [r for r in rows if r["mech"]]:
        print(f"  {r['pair']:<18}{r['cost_ratio']:>9.3f}{r['be']:>10.1%}"
              f"{r['beta']:>7.2f}{r['bind']:>7.1%}{r['per_year']:>9.1f}{r['n']:>7,}")
        print(f"    {r['mech']}")

    print("\nCHEAPEST PAIRS WITHOUT A STATED MECHANISM (report only -- do NOT")
    print("pick from here; a cheap pair with no reason to cointegrate is a")
    print("data-mining opportunity)")
    print("=" * 78)
    print(hdr)
    for r in [r for r in rows if not r["mech"]][:5]:
        print(f"  {r['pair']:<18}{r['cost_ratio']:>9.3f}{r['be']:>10.1%}"
              f"{r['beta']:>7.2f}{r['bind']:>7.1%}{r['per_year']:>9.1f}{r['n']:>7,}")

    print("\nFOR REFERENCE, THE PAIRS THAT FAILED")
    print("=" * 78)
    print(f"  {'silver/gold':<18}{0.222:>9.3f}{0.5+0.222/6:>10.1%}"
          f"{1.43:>7.2f}{0.0:>7.1%}{'~33':>9}{'674':>7}")
    print(f"  {'copper/palladium':<18}{0.260:>9.3f}{0.5+0.260/6:>10.1%}"
          f"{0.17:>7.2f}{11.3:>7.1f}{'~31':>9}{'631':>7}")

    best = [r for r in rows if r["mech"]][:1]
    if best:
        b = best[0]
        print(f"\n  Cheapest pair with a mechanism: {b['pair']} at cost/vol "
              f"{b['cost_ratio']:.3f}")
        print(f"  It needs a {b['edge']*100:.1f}pp edge to break even, versus "
              f"4.3pp for the metals.")
        print(f"  {b['need']:,.0f} independent trades would establish that at 3 sd; "
              f"{b['n']:,} available.")


if __name__ == "__main__":
    main()
