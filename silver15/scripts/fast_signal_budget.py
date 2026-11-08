#!/usr/bin/env python3
"""Power budget for a FAST-decorrelating residual signal. Run before hypothesising.

WHY THIS EXISTS
---------------
The slow signal (30-bar cumulative residual) hit a hard ceiling: it produces
one independent observation per ~30 bars per pair, so 27 pairs over 20 years
gives ~1,880 independent trades against the ~6,000 needed. More instruments
cannot fix that -- it is a property of the signal's construction.

A faster signal decorrelates sooner and yields more independent trades. But it
is not free, and the trade-off is the whole question:

    slow signal   long hold   -> residual travels far  -> BIG barrier
                              -> low break-even, FEW independent trades
    fast signal   short hold  -> residual travels less -> SMALL barrier
                              -> HIGH break-even, many independent trades

Cost is fixed per round trip. Break-even is 0.5 + C/(2B), so halving the
barrier doubles the cost penalty. Meanwhile a random walk travels ~sqrt(H)
volatility units in H bars, so the largest barrier plausibly reachable scales
as sqrt(hold).

This tool finds whether ANY point on that curve is simultaneously affordable
and testable. If none is, that is the answer and no pre-registration follows.

NO RETURNS ARE COMPUTED HERE. Everything below is measured from price
volatility, spreads, and autocorrelation only.

    python fast_signal_budget.py --data ../data_universe
"""

from __future__ import annotations

import argparse
import os
import sys

VERSION = "1.0"

# Calibration from the metals test: 165 independent trades gave a
# randomised-side null standard deviation of 3.40pp on the win rate.
N0, SD0 = 165, 0.0340
TARGET_SD = 3.0

# Barrier reachability. A driftless walk covers ~sqrt(H) vol units in H bars;
# setting the barrier at the full sqrt(H) means roughly half of trades never
# reach it. 0.75 keeps most trades resolving at a barrier rather than on time.
BARRIER_FRAC = 0.75


def measure(data_dir, resid_windows):
    """For each candidate signal speed: autocorrelation decay and trade counts."""
    import numpy as np, pandas as pd
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import screen_universe as U

    s = U.load(data_dir)
    pairs = [(x, y) for (x, y) in U.MECHANISM if x in s and y in s]
    out = {}

    for rw in resid_windows:
        zw = max(4 * rw, 40)               # z-window scales with the signal
        acs, counts, costs, resids = [], [], [], {}
        for x, y in pairs:
            idx = s[x].index.intersection(s[y].index)
            if len(idx) < 2000:
                continue
            ra = pd.Series(np.log(s[x].loc[idx].to_numpy(float)), index=idx).diff()
            rb = pd.Series(np.log(s[y].loc[idx].to_numpy(float)), index=idx).diff()
            raw = (ra.rolling(U.BETA_WINDOW).cov(rb)
                   / rb.rolling(U.BETA_WINDOW).var().replace(0, np.nan))
            beta = raw.clip(U.BETA_LO, U.BETA_HI)
            if float(((raw <= U.BETA_LO) | (raw >= U.BETA_HI)).mean()) > 0.05:
                continue
            resid = ra - beta * rb
            svol = resid.rolling(14).std()
            cum = resid.rolling(rw).sum()
            z = (cum - cum.rolling(zw).mean()) / cum.rolling(zw).std()

            cost = 2 * (U.SPREAD_REL[x] / 2 + beta.abs() * U.SPREAD_REL[y] / 2)
            costs.append(float((cost / svol).replace(
                [np.inf, -np.inf], np.nan).median()))

            zc = z.dropna()
            # decorrelation lag: first lag where |autocorr| falls below 0.2
            lag = None
            for L in range(1, 4 * rw + 30):
                if abs(zc.autocorr(L)) < 0.2:
                    lag = L
                    break
            acs.append(lag if lag else 4 * rw + 30)

            fired = (z.abs() >= 2.0).to_numpy()
            counts.append((fired, idx))
            resids[f"{U.LABEL[x]}/{U.LABEL[y]}"] = resid

        R = pd.DataFrame(resids).dropna()
        C = R.corr().to_numpy()
        rho = float(np.mean(np.abs(C[~np.eye(len(C), dtype=bool)])))
        dec = int(np.median(acs))

        # one trade per decorrelation window -> genuinely independent draws
        total = 0
        for fired, idx in counts:
            last, k = -10**9, 0
            for i in np.flatnonzero(fired):
                if i - last >= dec:
                    k += 1; last = i
            total += k
        m = len(counts)
        eff = total / (1 + (m - 1) * rho)
        out[rw] = dict(dec=dec, raw=total, eff=eff, rho=rho, m=m,
                       cost=float(np.median(costs)))
    return out


def main():
    import numpy as np
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data_universe")
    a = ap.parse_args()

    print(f"fast_signal_budget.py v{VERSION}   NO RETURNS COMPUTED")
    print("  searching for a signal speed that is BOTH affordable and testable\n")

    res = measure(a.data, [2, 3, 5, 8, 12, 20, 30])

    print(f"{'resid':>6}{'decorr':>8}{'hold':>6}{'barrier':>9}{'cost/vol':>10}"
          f"{'break-even':>12}{'indep n':>9}{'min edge':>10}{'need':>10}")
    print("=" * 82)
    best = None
    for rw, r in res.items():
        hold = r["dec"]                       # hold to the decorrelation time
        B = BARRIER_FRAC * np.sqrt(hold)      # largest reachable barrier
        be = 0.5 + r["cost"] / (2 * B)
        mde = np.sqrt(N0 / r["eff"]) * SD0 * TARGET_SD if r["eff"] > 0 else np.inf
        need = (be - 0.5) + mde               # true edge required to prove profit
        row = dict(rw=rw, hold=hold, B=B, be=be, mde=mde, need=need, **r)
        print(f"{rw:>6}{r['dec']:>8}{hold:>6}{B:>9.2f}{r['cost']:>10.3f}"
              f"{be*100:>11.1f}%{r['eff']:>9,.0f}{mde*100:>9.1f}pp"
              f"{need*100:>9.1f}pp")
        if best is None or row["need"] < best["need"]:
            best = row

    print("\n  'need' = break-even edge + smallest detectable excess.")
    print("  The true edge must EXCEED it for a test to prove profitability.")
    print(f"\n  Best speed: {best['rw']}-bar residual, decorrelates in "
          f"{best['dec']} bars")
    print(f"    barrier {best['B']:.2f} vol   break-even {best['be']*100:.1f}%"
          f"   independent n {best['eff']:,.0f}")
    print(f"    requires a true edge above {best['need']*100:.1f}pp")
    print(f"\n  For comparison, the 30-bar slow signal required 5.3pp and the")
    print(f"  metals basket 9.3pp. Evidence from the 15m work puts the real")
    print(f"  edge at roughly 3-4pp.")
    if best["need"] <= 0.04:
        print("\n  => A test IS worth pre-registering at this speed.")
    else:
        print(f"\n  => Still above the plausible edge. Faster signals buy sample")
        print(f"     but pay for it in break-even, and the exchange rate is bad.")


if __name__ == "__main__":
    main()
