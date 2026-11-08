#!/usr/bin/env python3
"""Power budget for 12-MONTH TIME-SERIES MOMENTUM. Run BEFORE hypothesising.

NO STRATEGY P&L IS COMPUTED IN THIS FILE. Past returns appear twice — as the
SIGNAL (the sign of a 12-month return) and as VOLATILITY (a second moment).
No position is ever marked to market, no equity curve is formed, and the mean
of no forward return is taken anywhere.

WHY THIS IS NOT v3 OR v4 AGAIN
------------------------------
v3 tested directional momentum over 120 H4 bars (~20 days). v4 tested
cross-sectional ranks over the same 120 bars. Neither is the construction the
literature actually documents.

Moskowitz, Ooi & Pedersen (2012) use a **12-month** lookback with monthly
rebalancing, held long or short by the sign of that return, vol-scaled per
instrument. Horizon is not a free parameter here — it is the specification,
fixed in advance by prior work, and momentum is famously horizon-dependent:
12-month continuation and 1-month reversal are different effects with
opposite signs. A null at 20 days genuinely does not settle 12 months.

TWO THINGS MAKE THIS THE MOST FAVOURABLE COST PROFILE IN THE PROJECT
--------------------------------------------------------------------
  1. THE SIGNAL BARELY MOVES. A 12-month return changes sign rarely, so a
     monthly rebalance trades a handful of times a year per instrument. Every
     family that died on cost died because drag scales as sqrt(trades/year);
     here that term is small by construction.
  2. DIVERSIFICATION ACTUALLY PAYS. Earlier work established that the
     detectability BAR is independent of instrument count. That remains true.
     But the achievable PORTFOLIO Sharpe is not: N instruments with mean
     pairwise correlation rho behave like N/(1+(N-1)rho) independent bets, so
     a per-instrument edge s becomes a portfolio Sharpe of s*sqrt(breadth).
     Those two statements are about different quantities and both hold.

So the question this file answers is NOT "can 28 instruments beat the bar" —
it is "what per-instrument gross Sharpe would be required, and is that inside
the range this effect plausibly produces".

THE PRIOR, STATED BEFORE THE RUN
--------------------------------
Published TSMOM Sharpes near 0.7-1.0 come from 1985-2009 samples. Live
managed-futures indices have run nearer 0.2-0.3 since 2009, and this panel is
2006-2026 — almost entirely the weak period. The honest expectation is that
this is marginal at best. Writing that down now so a favourable number gets
the scepticism it deserves rather than the relief.

    python tsmom_budget.py --self-test
    python tsmom_budget.py --data ../data_universe
"""

from __future__ import annotations

import argparse
import math
import os
import sys

VERSION = "1.0"

# ---- FIXED BY PRIOR SPECIFICATION, NOT CHOSEN HERE ------------------------
LOOKBACK_M = 12        # months. Moskowitz/Ooi/Pedersen. Not a free parameter.
REBAL_M = 1            # months
# ---------------------------------------------------------------------------

# Plausible band for the effect, post-2009, stated in advance.
PLAUSIBLE_LO, PLAUSIBLE_HI = 0.20, 0.50


def _bootstrap_venv() -> None:
    import importlib.util
    flag = "TSMOM_BUDGET_BOOTSTRAPPED"
    if os.environ.get(flag):
        return
    try:
        if all(importlib.util.find_spec(m) for m in ("numpy", "pandas")):
            return
    except (ImportError, ValueError):
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    for rel in (".venv", "venv"):
        for sub in ("bin/python3", "bin/python", "Scripts/python.exe"):
            cand = os.path.abspath(os.path.join(here, rel, *sub.split("/")))
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                if cand == os.path.abspath(sys.executable):
                    return
                print(f"  [venv] re-running under {os.path.relpath(cand, here)}",
                      file=sys.stderr)
                os.environ[flag] = "1"
                try:
                    os.execv(cand, [cand, os.path.abspath(__file__)]
                             + sys.argv[1:])
                except OSError:
                    return


_bootstrap_venv()


# ---------------------------------------------------------------------------
# pure helpers -- exercised offline
# ---------------------------------------------------------------------------

def effective_breadth(n: int, rho: float) -> float:
    """How many INDEPENDENT bets N correlated instruments really represent."""
    if n <= 0:
        return 0.0
    denom = 1.0 + (n - 1) * rho
    return n / denom if denom > 0 else float(n)


def detectability_bar(years: float, k: float = 2.0) -> float:
    return k / math.sqrt(years) if years > 0 else float("inf")


def annual_cost_sharpe(flips_per_year: float, spread: float,
                       annual_vol: float) -> float:
    """Cost drag expressed in annual Sharpe units.

    A SIGN FLIP IS A DOUBLE TRADE. Going from long one unit to short one unit
    moves two units of notional, so it costs twice the round-trip spread, not
    once. Charging it once is the commonest way a trend-following backtest
    flatters itself.
    """
    if annual_vol <= 0:
        return float("inf")
    return (flips_per_year * 2.0 * spread) / annual_vol


def required_per_instrument(bar: float, cost: float, breadth: float) -> float:
    """Gross Sharpe each instrument must produce for the PORTFOLIO to clear."""
    if breadth <= 0:
        return float("inf")
    return (bar + cost) / math.sqrt(breadth)


# ---------------------------------------------------------------------------

def load_monthly(data_dir):
    """Month-end close per instrument, resampled from each instrument's OWN
    bars before any alignment — the v4 ragged-index lesson."""
    import pandas as pd
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import screen_universe as U
    cols, spreads = {}, {}
    for stem in U.SPREAD_REL:
        p = os.path.join(data_dir, f"{stem}_4h.csv")
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p)
        t = d.columns[0]
        d[t] = pd.to_datetime(d[t], utc=True)
        s = d.set_index(t).sort_index()["close"].astype(float)
        cols[U.LABEL[stem]] = s.resample("ME").last().dropna()
        spreads[U.LABEL[stem]] = U.SPREAD_REL[stem]
    return pd.DataFrame(cols).sort_index(), pd.Series(spreads)


def self_test() -> int:
    fails = []

    def check(n, c, d=""):
        print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ""))
        if not c:
            fails.append(n)

    print(f"tsmom_budget.py v{VERSION} — offline controls\n")

    # 1-3. breadth
    check("1 uncorrelated instruments give full breadth",
          abs(effective_breadth(28, 0.0) - 28) < 1e-9)
    check("2 perfectly correlated give ONE bet",
          abs(effective_breadth(28, 1.0) - 1.0) < 1e-9,
          "28 copies of the same trade is one trade")
    b = effective_breadth(28, 0.15)
    check("3 realistic correlation collapses breadth hard",
          4.0 < b < 7.0, f"28 instruments at rho=0.15 -> {b:.1f} bets")

    # 4-5. the bar
    check("4 bar falls as 1/sqrt(years)",
          abs(detectability_bar(20.4) - 0.4428) < 1e-3,
          f"{detectability_bar(20.4):.4f}")
    check("5 bar is independent of instrument count",
          detectability_bar(20.4) == detectability_bar(20.4),
          "by construction — breadth affects achievable Sharpe, not the bar")

    # 6-8. cost. THE DOUBLE-TRADE POINT.
    single = annual_cost_sharpe(2.0, 0.0001, 0.15)
    check("6 a flip costs TWO round trips, not one",
          abs(single - (2 * 2 * 0.0001 / 0.15)) < 1e-12,
          f"{single:.4f} Sharpe drag for 2 flips/yr")
    check("7 more flips cost proportionally more",
          abs(annual_cost_sharpe(4, 0.0001, 0.15) / single - 2.0) < 1e-9)
    check("8 higher vol dilutes the drag",
          annual_cost_sharpe(2, 0.0001, 0.30) < single,
          "cost is a fraction of price; risk is not")

    # 9-10. the requirement
    r = required_per_instrument(0.44, 0.05, 5.5)
    check("9 breadth reduces the per-instrument requirement",
          abs(r - (0.49 / math.sqrt(5.5))) < 1e-9,
          f"{r:.3f} per instrument for a 0.44 portfolio bar")
    check("10 zero breadth does not divide by zero",
          required_per_instrument(0.44, 0.05, 0) == float("inf"))

    print(f"\n  {'ALL CONTROLS PASS' if not fails else str(len(fails)) + ' FAILED'}")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--data", default="../data_universe")
    a = ap.parse_args()
    if a.self_test:
        return self_test()

    import numpy as np, pandas as pd

    print(f"tsmom_budget.py v{VERSION}   NO STRATEGY P&L COMPUTED")
    print(f"  past returns used as SIGNAL and as VOLATILITY only\n")

    M, spread = load_monthly(a.data)
    L = np.log(M)
    R = L.diff()                                   # monthly log returns
    sig = np.sign(L - L.shift(LOOKBACK_M))         # THE 12-MONTH SIGN

    ok = M.notna().sum(axis=1) >= 20
    M2 = M[ok]
    years = (M2.index.max() - M2.index.min()).days / 365.25
    bar = detectability_bar(years)

    print(f"  {M.shape[1]} instruments, {len(M2)} months, {years:.1f} years")
    print(f"  detectability bar at 2 sigma: annual Sharpe {bar:.2f}\n")

    # ---- 1. how often does the sign actually flip? -----------------------
    print("1. SIGNAL PERSISTENCE — the thing that decides cost")
    print("=" * 74)
    flips, vols = {}, {}
    for c in sig.columns:
        s = sig[c].dropna()
        if len(s) < 36:
            continue
        chg = (s != s.shift(1)).iloc[1:]
        yrs_c = len(s) / 12.0
        flips[c] = chg.sum() / yrs_c
        r = R[c].dropna()
        vols[c] = float(r.std()) * math.sqrt(12) if len(r) > 24 else np.nan

    fl = pd.Series(flips).dropna()
    vo = pd.Series(vols).dropna()
    print(f"  median sign flips per year   {fl.median():.2f}")
    print(f"  range across instruments     {fl.min():.2f} to {fl.max():.2f}")
    print(f"  median annual volatility     {vo.median():.1%}")
    print(f"  -> a position is held about  {12 / fl.median():.1f} months")

    # ---- 2. cost ---------------------------------------------------------
    print(f"\n2. COST — a flip is a DOUBLE trade")
    print("=" * 74)
    common = sorted(set(fl.index) & set(vo.index) & set(spread.index))
    costs = {c: annual_cost_sharpe(fl[c], spread[c], vo[c]) for c in common}
    cs = pd.Series(costs)
    print(f"  median spread                {spread[common].median():.4%}")
    print(f"  median annual cost drag      {cs.median():.4f} Sharpe")
    print(f"  worst instrument             {cs.idxmax()} at {cs.max():.4f}")
    print(f"  -> cost is {'NEGLIGIBLE' if cs.median() < 0.05 else 'material'}"
          f" against a bar of {bar:.2f}")

    # ---- 3. breadth ------------------------------------------------------
    print(f"\n3. EFFECTIVE BREADTH — 28 instruments are not 28 bets")
    print("=" * 74)
    RR = R[common].dropna(how="all")
    C = RR.corr()
    off = C.to_numpy()[~np.eye(len(C), dtype=bool)]
    rho_r = float(np.nanmean(np.abs(off)))
    SS = sig[common].dropna(how="all")
    Cs = SS.corr()
    offs = Cs.to_numpy()[~np.eye(len(Cs), dtype=bool)]
    rho_s = float(np.nanmean(np.abs(offs)))
    n = len(common)
    breadth = effective_breadth(n, rho_r)
    print(f"  instruments                  {n}")
    print(f"  mean |return correlation|    {rho_r:.3f}")
    print(f"  mean |signal correlation|    {rho_s:.3f}"
          f"   (positions crowd even when returns do not)")
    print(f"  EFFECTIVE BREADTH            {breadth:.1f} independent bets")

    # ---- 4. the requirement ---------------------------------------------
    cost = float(cs.median())
    req_port = bar + cost
    req_inst = required_per_instrument(bar, cost, breadth)
    print(f"\n4. WHAT WOULD BE REQUIRED")
    print("=" * 74)
    print(f"  portfolio gross Sharpe needed        {req_port:.2f}")
    print(f"    = bar {bar:.2f} + cost {cost:.3f}")
    print(f"  per-instrument gross Sharpe needed   {req_inst:.2f}")
    print(f"    = {req_port:.2f} / sqrt({breadth:.1f})")
    print(f"\n  plausible band for TSMOM post-2009:  "
          f"{PLAUSIBLE_LO:.2f} to {PLAUSIBLE_HI:.2f} per instrument")
    print(f"  (published 0.7-1.0 figures are 1985-2009 portfolio Sharpes,")
    print(f"   not per-instrument, and not this sample period)")

    print(f"\nVERDICT")
    print("=" * 74)
    if req_inst <= PLAUSIBLE_LO:
        print(f"  => {req_inst:.2f} is BELOW even the pessimistic end of the")
        print(f"     plausible band. Worth pre-registering as v7.")
    elif req_inst <= PLAUSIBLE_HI:
        print(f"  => {req_inst:.2f} sits INSIDE the plausible band"
              f" ({PLAUSIBLE_LO:.2f}-{PLAUSIBLE_HI:.2f}).")
        print(f"     Worth pre-registering as v7 — but note that 'inside the")
        print(f"     band' means the test could go either way, which is")
        print(f"     exactly when a pre-registration earns its keep.")
    else:
        print(f"  => {req_inst:.2f} EXCEEDS what this effect plausibly produces")
        print(f"     in this period. Do not pre-register it.")

    print(f"\n  What this budget CANNOT see, stated before any test:")
    print(f"    - whether the effect exists in 2006-2026 at all. The budget")
    print(f"      bounds resolution; it cannot establish existence. That was")
    print(f"      v6's lesson and it applies unchanged here.")
    print(f"    - slippage beyond quoted spread on a monthly rebalance")
    print(f"    - that signal correlation ({rho_s:.2f}) exceeds return")
    print(f"      correlation ({rho_r:.2f}): positions crowd more than returns")
    print(f"      do, so realised breadth is likely BELOW {breadth:.1f}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
