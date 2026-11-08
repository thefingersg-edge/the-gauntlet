#!/usr/bin/env python3
"""Volatility targeting on buy-and-hold gold, tested OUT OF SAMPLE.

WHAT WAS ALREADY KNOWN, AND WHY IT IS NOT ENOUGH

DESIGN_BRIEF section 1d found all six settings beating buy-and-hold on Sharpe,
with the 60-day estimation window beating the 20-day at all three target levels.
That was measured on the FULL SAMPLE. Every other full-sample result in this
project has since fallen over when a holdout was enforced -- the 4H strategy
went from PF 2.18 in-sample to 0.93 and 1.60 on unseen windows -- so the
finding does not carry until it is re-measured under the same discipline.

THE TEST, FIXED BEFORE RUNNING

Three windows, three years held out either side of the middle one:

    2006-03 .. 2009-03   UNSEEN (pre)
    2009-04 .. 2023-08   reference
    2023-09 .. 2026-08   UNSEEN (post)

Two pre-registered questions, both answerable per window:

    Q1  does vol targeting beat buy-and-hold on SHARPE?
    Q2  does the 60-day window beat the 20-day at all three targets?

Q2 is the one that matters. Q1 can be satisfied by luck in a single window;
Q2 asks whether the PLATEAU holds -- whether the parameter ordering that was
observed full-sample reproduces where it was not fitted. A plateau that
survives out of sample is a different class of evidence from a point estimate
that happened to look good.

WHAT WOULD MAKE THIS FAIL

    the ordering flips        60d loses to 20d in an unseen window
    the Sharpe gain vanishes  vol targeting <= buy-and-hold out of sample
    it only works levered     gains present at 20% target, absent at 10%
                              (that is leverage, not risk management)

NO PARAMETER IS FITTED HERE. Sizing uses only trailing realised volatility,
lagged one day so nothing is known before it happened. Leverage is capped at 3x.
The six settings are the same six from the brief, not a search.

    python vol_target.py
    python vol_target.py --csv xauusd_oanda_h4.csv --cap 3.0
"""
from __future__ import annotations

import argparse
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import _normalise, _read_csv                # noqa: E402

TARGETS = (0.10, 0.15, 0.20)
WINDOWS = (20, 60)
CAP = 3.0

WINDOWS_SPLIT = [
    ("2006-03 .. 2009-03", "2006-01-01", "2009-03-31", "UNSEEN pre"),
    ("2009-04 .. 2023-08", "2009-04-01", "2023-08-31", "reference"),
    ("2023-09 .. 2026-08", "2023-09-01", "2026-12-31", "UNSEEN post"),
]


def daily_returns(csv: str) -> pd.Series:
    """One close per calendar date, then simple returns.

    Resampled from intraday rather than fetched separately so this uses the
    exact same price series every other test in this project uses.
    """
    df = _normalise(_read_csv(csv))
    close = df["close"].groupby(df.index.normalize()).last()
    return close.pct_change().dropna()


def ann_factor(r: pd.Series) -> float:
    """Bars per year, measured rather than assumed.

    Gold quotes ~6 days a week in this feed (the Sunday session opens at 22:00
    UTC), so the textbook 252 understates it and would inflate every Sharpe by
    about 8%. Counting actual bars keeps the comparison against buy-and-hold
    internally consistent whatever the convention.
    """
    years = (r.index[-1] - r.index[0]).days / 365.25
    return len(r) / years


def stats(r: pd.Series, af: float) -> dict:
    if len(r) < 30 or r.std() == 0:
        return {k: np.nan for k in ("ret", "vol", "sharpe", "maxdd")}
    eq = (1 + r).cumprod()
    years = len(r) / af
    return {
        "ret": 100 * (eq.iloc[-1] ** (1 / years) - 1),
        "vol": 100 * r.std() * np.sqrt(af),
        "sharpe": (r.mean() / r.std()) * np.sqrt(af),
        "maxdd": 100 * ((eq / eq.cummax()) - 1).min(),
    }


def vol_target(r: pd.Series, target: float, window: int,
               af: float, cap: float = CAP) -> pd.Series:
    """Scale exposure by trailing realised vol.

    The .shift(1) is the whole ethical content of this function: today's size
    is set from volatility measured strictly before today. Without it the
    strategy sizes down INTO the crash it can already see, which backtests
    beautifully and is unimplementable.
    """
    realised = r.rolling(window).std() * np.sqrt(af)
    weight = (target / realised).shift(1).clip(upper=cap)
    return (weight * r).dropna()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default="xauusd_oanda_h4.csv")
    ap.add_argument("--cap", type=float, default=CAP)
    a = ap.parse_args()

    full = daily_returns(a.csv)
    af = ann_factor(full)
    print(f"\nVOLATILITY TARGETING, OUT OF SAMPLE   {a.csv}")
    print(f"  {full.index[0].date()} -> {full.index[-1].date()}   "
          f"{len(full):,} daily bars   {af:.1f} bars/yr   leverage cap {a.cap:g}x")

    verdicts = []
    for label, s, e, status in WINDOWS_SPLIT:
        # Sized from the FULL series then sliced, so the 60-day window at the
        # start of a segment uses real prior data instead of restarting warm-up
        # inside the test window and sizing off 3 observations.
        seg = full[s:e]
        if len(seg) < 60:
            print(f"\n  {label}  too little data ({len(seg)} bars)")
            continue
        bh = stats(seg, af)
        print(f"\n  {label}   [{status}]   {len(seg):,} bars")
        print(f"    {'setting':<22}{'ann ret%':>10}{'vol%':>8}{'Sharpe':>9}"
              f"{'maxDD%':>9}{'vs B&H':>9}")
        print("    " + "-" * 67)
        print(f"    {'buy and hold':<22}{bh['ret']:>10.2f}{bh['vol']:>8.1f}"
              f"{bh['sharpe']:>9.2f}{bh['maxdd']:>9.1f}{'--':>9}")
        got = {}
        for t in TARGETS:
            for w in WINDOWS:
                st = stats(vol_target(full, t, w, af, a.cap)[s:e], af)
                got[(t, w)] = st
                mark = "+" if st["sharpe"] > bh["sharpe"] else "-"
                print(f"    {'target %d%%, %dd' % (100 * t, w):<22}"
                      f"{st['ret']:>10.2f}{st['vol']:>8.1f}{st['sharpe']:>9.2f}"
                      f"{st['maxdd']:>9.1f}{mark:>9}")
        beat = sum(got[k]["sharpe"] > bh["sharpe"] for k in got)
        order = sum(got[(t, 60)]["sharpe"] > got[(t, 20)]["sharpe"] for t in TARGETS)
        print(f"    Q1 beat B&H on Sharpe: {beat}/6      "
              f"Q2 60d beats 20d: {order}/3")
        verdicts.append((label, status, beat, order))

    print("\n  SUMMARY")
    print("  " + "=" * 67)
    print(f"  {'window':<22}{'status':<14}{'Q1 beat B&H':>14}{'Q2 60d>20d':>14}")
    for label, status, beat, order in verdicts:
        print(f"  {label:<22}{status:<14}{str(beat) + '/6':>14}{str(order) + '/3':>14}")
    oos = [v for v in verdicts if "UNSEEN" in v[1]]
    if oos:
        ok = all(b >= 4 and o >= 2 for _, _, b, o in oos)
        print(f"\n  VERDICT: {'HOLDS out of sample.' if ok else 'DOES NOT hold out of sample.'}"
              f"  ({len(oos)} unseen window(s) checked)")


if __name__ == "__main__":
    main()
