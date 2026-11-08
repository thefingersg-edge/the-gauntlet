#!/usr/bin/env python3
"""Power budget for DIRECTIONAL families (trend / breakout / momentum).

Run before any hypothesis. NO RETURNS ARE COMPUTED IN THIS FILE.

WHY DIRECTIONAL MIGHT ESCAPE THE FLOOR THAT CLOSED PAIRS
--------------------------------------------------------
The residual family died on an irreducible floor of 4.7pp:

    required(H) = C/(2 x 0.75 x sqrt(H))  +  k x sqrt(H)

with C = round-trip cost divided by per-bar volatility. Pairs were punished
twice over on that C:

  * they pay TWO spreads (own leg plus beta x hedge leg), and
  * they earn on the RESIDUAL, whose volatility is much smaller than either
    leg's -- that is the entire point of hedging.

So the pair's C is roughly (2 x spread) / (small vol). A directional trade on
one instrument pays ONE spread and earns on the instrument's FULL volatility.
If that halves C, the floor falls by sqrt(2); if it cuts C by 4x, the floor
halves. Whether it is enough is an empirical question, answered below.

Against that, directional signals have their own problems, which this budget
does NOT resolve and which no amount of sample will fix:

  * trend edges are widely known and heavily traded;
  * they are strongly correlated ACROSS instruments (everything trends at
    once), so 28 instruments is nowhere near 28 independent experiments --
    far worse on this axis than pairs were;
  * they have fat left tails that a win-rate framework understates.

    python directional_budget.py --data ../data_universe
"""

from __future__ import annotations

import argparse
import os
import sys

VERSION = "1.0"
N0, SD0, TARGET_SD = 165, 0.0340, 3.0
BARRIER_FRAC = 0.75


def main():
    import numpy as np, pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data_universe")
    a = ap.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import screen_universe as U

    print(f"directional_budget.py v{VERSION}   NO RETURNS COMPUTED\n")
    s = U.load(a.data)
    print(f"  {len(s)} instruments, H4\n")

    # ---- 1. cost/vol per instrument, vs the pair equivalent ---------------
    print("COST / VOLATILITY  (the term that set the pair floor)")
    print("=" * 70)
    print(f"  {'instrument':<12}{'spread%':>9}{'per-bar vol':>13}{'cost/vol':>10}")
    cv, rets = {}, {}
    for k, v in s.items():
        r = pd.Series(np.log(v.to_numpy(float)), index=v.index).diff()
        vol = float(r.rolling(14).std().median())
        c = U.SPREAD_REL[k] / vol           # round trip / per-bar vol
        cv[k] = c
        rets[k] = r
        print(f"  {U.LABEL[k]:<12}{U.SPREAD_REL[k]*100:>8.4f}%{vol*100:>12.3f}%"
              f"{c:>10.3f}")
    med = float(np.median(list(cv.values())))
    print(f"\n  median directional cost/vol : {med:.3f}")
    print(f"  pair (residual) cost/vol    : 0.146")
    print(f"  improvement                 : {0.146/med:.2f}x cheaper")

    # ---- 2. how independent are instruments from each other? -------------
    R = pd.DataFrame(rets).dropna()
    C = R.corr().to_numpy()
    rho = float(np.mean(np.abs(C[~np.eye(len(C), dtype=bool)])))
    print(f"\nCROSS-INSTRUMENT CORRELATION")
    print("=" * 70)
    print(f"  mean |correlation| of raw returns : {rho:.3f}")
    print(f"  (pair residuals were 0.123 -- hedging REMOVES common factors,")
    print(f"   which is exactly what directional trading re-introduces)")
    m = len(s)
    print(f"  {m} instruments discount to an effective {m/(1+(m-1)*rho):.1f}")

    # ---- 3. the floor ----------------------------------------------------
    print(f"\nTHE FLOOR FOR A DIRECTIONAL FAMILY")
    print("=" * 70)
    bars_per_year = 365.25 * 6 * 5 / 7
    years = float(np.median([(v.index[-1] - v.index[0]).days / 365.25
                             for v in s.values()]))
    print(f"  {years:.1f} years, ~{bars_per_year:,.0f} H4 bars/year/instrument")
    print(f"\n  {'hold':>6}{'days':>7}{'barrier':>9}{'break-even':>12}"
          f"{'indep n':>10}{'min edge':>10}{'required':>11}")
    best = None
    for hold in (4, 8, 17, 30, 60, 120, 250):
        B = BARRIER_FRAC * np.sqrt(hold)
        be = 0.5 + med / (2 * B)
        # one non-overlapping trade per hold, per instrument, discounted for
        # cross-instrument correlation
        raw = m * years * bars_per_year / hold
        eff = raw / (1 + (m - 1) * rho)
        mde = np.sqrt(N0 / eff) * SD0 * TARGET_SD
        req = (be - 0.5) + mde
        print(f"  {hold:>6}{hold*4/24:>7.1f}{B:>9.2f}{be*100:>11.1f}%"
              f"{eff:>10,.0f}{mde*100:>9.2f}pp{req*100:>10.2f}pp")
        if best is None or req < best[1]:
            best = (hold, req, be, eff, mde)

    hold, req, be, eff, mde = best
    print(f"\n  Best: hold {hold} bars ({hold*4/24:.1f} days) -> "
          f"required edge {req*100:.2f}pp")
    print(f"    break-even {be*100:.1f}%   independent n {eff:,.0f}   "
          f"detectable {mde*100:.2f}pp")
    print(f"\n  Pair family floor was 4.73pp. Plausible edge 3-4pp.")
    if req <= 0.03:
        print(f"  => {req*100:.2f}pp is BELOW the plausible edge. A directional")
        print(f"     test is worth pre-registering.")
    elif req <= 0.04:
        print(f"  => {req*100:.2f}pp is INSIDE the plausible 3-4pp band. Testable,")
        print(f"     but the margin is thin -- expect a marginal answer.")
    else:
        print(f"  => {req*100:.2f}pp still exceeds the plausible edge.")

    print(f"\n  CAVEAT THIS BUDGET CANNOT ADDRESS: cross-instrument correlation")
    print(f"  of {rho:.2f} means the {m} instruments behave like "
          f"{m/(1+(m-1)*rho):.0f} independent ones.")
    print(f"  Directional strategies fail TOGETHER -- a drawdown hits every")
    print(f"  instrument at once. The win-rate framework above does not price")
    print(f"  that, and it is the main risk this family carries.")


if __name__ == "__main__":
    main()
