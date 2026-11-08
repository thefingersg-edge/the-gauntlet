#!/usr/bin/env python3
"""Re-score the rolling runs against a FAIR buy-and-hold benchmark.

TWO THINGS WERE WRONG WITH THE ORIGINAL COMPARISON, AND THEY PULL OPPOSITE WAYS

1. EXPOSURE. The strategy sits in cash a lot -- 87.4% time-in-market on gold,
   56.4% on NAS100 -- while buy-and-hold is invested 100% of the time. Judging
   them on raw return asks an intermittently-invested strategy to match a
   permanently-invested one, which confuses "is the signal any good" with "is
   more exposure better". Over a rising market, more exposure is better almost
   by definition.

   Fixed by VOLATILITY MATCHING: scale the strategy's monthly returns so its
   realised volatility equals buy-and-hold's, then compare. That is the same
   as levering it to the benchmark's risk level, and it answers the question
   that matters -- per unit of risk taken, which earns more?

2. CARRY. The benchmark was frictionless. Holding a CFD for a decade costs
   overnight financing, roughly the base rate plus a broker spread, and that
   compounds against you every single day. Gold at 11.69%/yr gross is a very
   different proposition at 4% financing. Pointing that out ARGUES FOR the
   strategy, which is exactly why it belongs here.

   Fixed by subtracting financing from the benchmark -- and from the strategy
   too, in proportion to how long it actually held a position. Charging the
   benchmark and not the strategy would just swap one bias for another.

NEITHER ADJUSTMENT IS FREE OF ASSUMPTIONS, so both are swept rather than
asserted. If the ranking flips somewhere inside the plausible range, that is
the finding; if it does not, the conclusion is robust to the assumption.

    python fair_compare.py
    python fair_compare.py --rates fedfunds.csv --spread 2.5
    python fair_compare.py --gold-exposure 0.874 --nas-exposure 0.564
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

import numpy as np
import pandas as pd

#: Measured time-in-position for the trained H4 configs over the test span.
#: Used to charge the strategy its share of financing. Approximate -- the
#: rolling configs differ month to month -- so it is exposed as a flag.
DEFAULT_EXPOSURE = {"GOLD": 0.874, "NAS100": 0.564}

#: Annual financing rates to sweep, in percent. 0 is the frictionless
#: benchmark used so far; 4-6% is realistic for a USD CFD at recent rates;
#: 2% covers the 2010-2021 low-rate era.
CARRY_SWEEP = (0.0, 2.0, 4.0, 6.0)


def load_runs(tf: str = "H4") -> list[tuple[str, float, pd.DataFrame]]:
    out = []
    for d in sorted(glob.glob(f"results/*_roll_tr*y_*")):
        f = os.path.join(d, "summary.csv")
        m = re.search(r"_tr([\d.]+)y_", d)
        if not os.path.exists(f) or not m or f"_{tf}_roll" not in d:
            continue
        inst = "GOLD" if "xauusd" in d else "NAS100"
        out.append((inst, float(m.group(1)),
                    pd.read_csv(f).dropna(subset=["retrained", "buyhold"])))
    return sorted(out)


def ann(x: pd.Series) -> float:
    eq = (1 + x).cumprod()
    if eq.iloc[-1] <= 0:
        return np.nan
    return 100 * (eq.iloc[-1] ** (12 / len(x)) - 1)


def maxdd(x: pd.Series) -> float:
    eq = (1 + x).cumprod()
    return 100 * ((eq / eq.cummax()) - 1).min()


def vol_match(strat: pd.Series, bench: pd.Series) -> tuple[pd.Series, float]:
    """Lever the strategy to the benchmark's realised volatility.

    Returns the scaled series and the leverage used. A scale above 1 means the
    strategy was LESS volatile than buy-and-hold and is being levered up; below
    1 means it was riskier and is being cut back.
    """
    if strat.std() == 0:
        return strat, np.nan
    k = bench.std() / strat.std()
    return strat * k, k


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tf", default="H4")
    ap.add_argument("--rates", help="FRED csv of a short rate, e.g. fedfunds.csv")
    ap.add_argument("--spread", type=float, default=2.5,
                    help="broker markup over the base rate, %%/yr (default 2.5)")
    ap.add_argument("--gold-exposure", type=float, default=DEFAULT_EXPOSURE["GOLD"])
    ap.add_argument("--nas-exposure", type=float, default=DEFAULT_EXPOSURE["NAS100"])
    a = ap.parse_args()
    expo = {"GOLD": a.gold_exposure, "NAS100": a.nas_exposure}

    runs = load_runs(a.tf)
    if not runs:
        raise SystemExit("no rolling runs found -- run run_window_sweep.sh first")

    rate_series = None
    if a.rates and os.path.exists(a.rates):
        r = pd.read_csv(a.rates, parse_dates=[0], index_col=0)
        rate_series = r.iloc[:, 0].resample("MS").mean() + a.spread
        # Report the mean over the TEST WINDOW, not the whole file. FRED's
        # FEDFUNDS starts in 1954 and averages ~4.6% across seventy years,
        # which said "7.10% financing" for a test period that actually ran
        # near zero for half its length.
        lo = min(pd.Timestamp(r0["month"].iloc[0]) for _, _, r0 in runs)
        hi = max(pd.Timestamp(r0["month"].iloc[-1]) for _, _, r0 in runs)
        w = rate_series[lo:hi]
        print(f"\nusing {a.rates} + {a.spread:g}% spread")
        print(f"  financing over the TEST WINDOW {lo.date()}..{hi.date()}: "
              f"mean {w.mean():.2f}%/yr, range {w.min():.2f}-{w.max():.2f}%")
        print(f"  (whole-file mean would be {rate_series.mean():.2f}% -- "
              f"that series goes back to {rate_series.index[0].date()})")
    else:
        print(f"\nno --rates file given: sweeping fixed financing rates instead")

    # ---- 1. volatility-matched -------------------------------------------
    print("\n" + "=" * 100)
    print("1. VOLATILITY-MATCHED  (strategy levered to buy-and-hold's risk; "
          "answers 'per unit of risk, which wins?')")
    print("=" * 100)
    # Volatility matching equalises VOLATILITY, not DRAWDOWN -- two series can
    # share a standard deviation and have very different worst runs. Calmar is
    # reported alongside because that gap is the whole reason to prefer an
    # intermittent strategy over always being invested.
    print(f"  {'instrument':<9}{'train':>6}{'raw ann%':>10}{'lever':>7}"
          f"{'matched ann%':>13}{'B&H ann%':>10}{'matched DD%':>13}{'B&H DD%':>9}"
          f"{'matched Calmar':>16}{'B&H Calmar':>12}  wins on")
    print("  " + "-" * 112)
    vm_wins = cal_wins = 0
    for inst, y, r in runs:
        s, b = r["retrained"], r["buyhold"]
        sc, k = vol_match(s, b)
        a_s, a_b = ann(sc), ann(b)
        d_s, d_b = maxdd(sc), maxdd(b)
        c_s = a_s / abs(d_s) if d_s else np.nan
        c_b = a_b / abs(d_b) if d_b else np.nan
        won = []
        if a_s > a_b:
            won.append("return")
            vm_wins += 1
        if c_s > c_b:
            won.append("CALMAR")
            cal_wins += 1
        print(f"  {inst:<9}{y:>5.0f}y{ann(s):>10.2f}{k:>7.2f}{a_s:>13.2f}{a_b:>10.2f}"
              f"{d_s:>13.1f}{d_b:>9.1f}{c_s:>16.2f}{c_b:>12.2f}  "
              f"{', '.join(won) if won else 'neither'}")
    print(f"\n  risk-matched RETURN : strategy wins {vm_wins}/{len(runs)}")
    print(f"  risk-matched CALMAR : strategy wins {cal_wins}/{len(runs)}"
          + ("   <- same vol, smaller worst run" if cal_wins else ""))

    # ---- 2. carry-adjusted ------------------------------------------------
    print("\n" + "=" * 100)
    print("2. CARRY-ADJUSTED  (financing charged to BOTH sides -- benchmark at "
          "100% exposure,")
    print("   strategy pro-rata to time actually in a position)")
    print("=" * 100)
    cols = [f"carry {c:.0f}%" for c in CARRY_SWEEP]
    if rate_series is not None:
        cols.append("ACTUAL rate")
    print(f"  {'instrument':<9}{'train':>6}{'expo':>7}"
          + "".join(f"{c:>17}" for c in cols))
    print(f"  {'':<9}{'':>6}{'':>7}"
          + "".join(f"{'strat  vs  B&H':>17}" for _ in cols))
    print("  " + "-" * 96)
    flips = []
    for inst, y, r in runs:
        cells = []
        for c in CARRY_SWEEP:
            mo = c / 100 / 12
            s = r["retrained"] - mo * expo[inst]
            b = r["buyhold"] - mo
            cells.append(f"{ann(s):>7.1f} {ann(b):>7.1f}")
            if ann(s) > ann(b):
                flips.append((inst, y, f"{c:g}%"))
        if rate_series is not None:
            # Time-varying financing: each month charged at that month's rate,
            # which matters because the test span covers both the near-zero
            # 2015-2021 era and the 5%+ 2023-2025 one. A single average would
            # smear those together and understate the recent drag.
            idx = pd.to_datetime(r["month"])
            mo = (rate_series.reindex(idx).ffill().bfill().values / 100 / 12)
            s = pd.Series(r["retrained"].values - mo * expo[inst])
            b = pd.Series(r["buyhold"].values - mo)
            cells.append(f"{ann(s):>7.1f} {ann(b):>7.1f}")
            if ann(s) > ann(b):
                flips.append((inst, y, "actual"))
        print(f"  {inst:<9}{y:>5.0f}y{100*expo[inst]:>6.0f}%"
              + "".join(f"{c:>17}" for c in cells))

    print("\n" + "=" * 100)
    print("VERDICT")
    print("=" * 100)
    if flips:
        print(f"  The ranking FLIPS in {len(flips)} of {len(runs)*len(CARRY_SWEEP)} "
              "instrument/rate combinations:")
        for inst, y, c in flips:
            print(f"    {inst} {y:.0f}y at {c} financing -- strategy ahead")
        print("  So 'loses to buy-and-hold' depends on what you actually pay to hold.")
    else:
        print("  Buy-and-hold stays ahead at EVERY financing rate tested, on every")
        print("  run. The original conclusion survives the fair-comparison fix.")
    if vm_wins:
        print(f"\n  On risk-matched return the strategy wins {vm_wins}/{len(runs)} -- "
              "worth reading\n  alongside the raw table, which penalises it for "
              "holding cash.")
    print()


if __name__ == "__main__":
    main()
