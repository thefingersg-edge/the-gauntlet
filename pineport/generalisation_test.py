#!/usr/bin/env python3
"""Test 3: does the gold-derived strategy generalise to another instrument?

The design is fixed in PREREGISTRATION.md. Nothing is tuned here — the exact
configuration developed on gold is applied to a market that has never been
looked at.

Primary metric: percentile against random entry at matched exposure and holding
periods. On gold that was 99.5th (full sample) and 86.7th (out-of-sample).

Criterion, fixed before the data was fetched:
    >= 95th  generalises
    80-95th  weak generalisation
    <  80th  does NOT generalise -- the gold results are instrument-specific

    python generalisation_test.py --csv xagusd_1h.csv --reference xauusd_1h.csv
    python generalisation_test.py --self-test
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

from broker import BrokerConfig                      # noqa: E402
from data import _normalise, _read_csv               # noqa: E402
from metrics import compute_metrics                  # noqa: E402
from strategy import Params, run_strategy            # noqa: E402
from null_test import run_null, report               # noqa: E402
import pine_ta as ta                                 # noqa: E402

#: The exact gold configuration. Not re-fitted for the new instrument.
GOLD_CONFIG = dict(fix_keltner_range=True, fix_long_stop_ratchet=True,
                   allow_shorts=False)


def volatility_ratio(target: pd.DataFrame, reference: pd.DataFrame) -> float:
    """Median ATR as a percentage of price, target vs reference.

    A single deterministic number used to scale the stop for the secondary run.
    No search: it is measured once and applied.
    """
    def atr_pct(df):
        a = ta.atr(df["high"], df["low"], df["close"], 14)
        return float((a / df["close"]).median())
    return atr_pct(target) / atr_pct(reference)


def summarise(df: pd.DataFrame, params: Params, cfg: BrokerConfig,
              label: str) -> dict:
    res = run_strategy(df, params, cfg)
    m = compute_metrics(res.equity, res.trades, cfg.initial_capital, df["close"])
    yrs = (df.index[-1] - df.index[0]).days / 365.25
    bh = 100 * ((df["close"].iloc[-1] / df["close"].iloc[0]) ** (1 / yrs) - 1)
    print(f"{label:<30}{m['trades']:>7}{m['cagr_pct']:>9.2f}{m['sharpe']:>8.2f}"
          f"{m['max_drawdown_pct']:>10.2f}{m['calmar']:>8.3f}"
          f"{m['exposure_pct']:>8.1f}{bh:>12.2f}")
    return m


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", help="the NEW instrument (e.g. xagusd_1h.csv)")
    ap.add_argument("--reference", help="the instrument it was developed on")
    ap.add_argument("--trials", type=int, default=2000)
    ap.add_argument("--capital", type=float, default=4000.0)
    ap.add_argument("--point-value", type=float, default=1.0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        from synth import make_bars
        # synth's GARCH recursion converges to its own stationary volatility, so
        # changing its vol seed does NOT produce a more volatile series. Build
        # the comparison explicitly instead: same path, bar ranges scaled.
        def with_vol(seed: int, mult: float) -> pd.DataFrame:
            d = make_bars(4000, seed=seed).copy()
            mid = (d["high"] + d["low"]) / 2
            for col in ("open", "high", "low", "close"):
                d[col] = mid + (d[col] - mid) * mult
            return d

        fails = []
        for mult, lo, hi in ((2.0, 1.7, 2.3), (1.0, 0.9, 1.1), (0.5, 0.4, 0.6)):
            r = volatility_ratio(with_vol(2, mult), with_vol(1, 1.0))
            ok = lo < r < hi
            fails.append(ok)
            print(f"  {'PASS' if ok else 'FAIL'}  {mult}x range -> ratio "
                  f"{r:.2f} (expected {lo}-{hi})")

        cfg = BrokerConfig(4000, 1)
        base = make_bars(6000, seed=1)
        res = run_strategy(base, Params(**GOLD_CONFIG), cfg)
        print(f"  PASS  gold config runs unmodified ({len(res.trades)} trades)")
        print("\nall checks passed" if all(fails) else "\nFAILED")
        sys.exit(0 if all(fails) else 1)

    if not args.csv:
        raise SystemExit("need --csv (or --self-test)")

    new = _normalise(_read_csv(args.csv))
    cfg = BrokerConfig(initial_capital=args.capital, point_value=args.point_value)
    name = os.path.basename(args.csv).split("_")[0].upper()

    print(f"instrument: {name}   {len(new):,} bars   "
          f"{new.index[0]:%Y-%m-%d} -> {new.index[-1]:%Y-%m-%d}")
    print(f"price range {new['close'].min():,.2f} to {new['close'].max():,.2f}")

    scaled_stop = None
    if args.reference:
        ref = _normalise(_read_csv(args.reference))
        vr = volatility_ratio(new, ref)
        base_stop = Params(**GOLD_CONFIG).sl_percent_long
        scaled_stop = base_stop * vr
        print(f"\nvolatility vs reference: {vr:.2f}x "
              f"(median ATR as % of price)")
        print(f"  the {base_stop}% stop chosen for the reference corresponds to "
              f"{scaled_stop:.2f}% here")

    print("\nPERFORMANCE (gold configuration applied unchanged)")
    print("-" * 92)
    print(f"{'':<30}{'trades':>7}{'CAGR%':>9}{'sharpe':>8}{'maxDD%':>10}"
          f"{'calmar':>8}{'expo%':>8}{'buy&hold%':>12}")
    summarise(new, Params(**GOLD_CONFIG), cfg, "PRIMARY: identical params")
    if scaled_stop:
        summarise(new, Params(**GOLD_CONFIG, sl_percent_long=scaled_stop), cfg,
                  f"secondary: stop -> {scaled_stop:.2f}%")

    print("\nPRIMARY METRIC: entry timing vs random entry at matched exposure")
    print("=" * 92)
    for label, a, b in [("FULL SAMPLE", None, None),
                        ("OUT-OF-SAMPLE 2006-2022", "2006-01-01", "2022-12-31")]:
        sub = new if a is None else new[a:b]
        if len(sub) < 5000:
            continue
        r = run_null(sub, Params(**GOLD_CONFIG), cfg, args.trials, 0)
        report(f"{name} — {label}", r)
        if label == "FULL SAMPLE":
            p = r["percentile"]
            print("\n  AGAINST THE PRE-REGISTERED CRITERION")
            print("  " + "-" * 58)
            if p >= 95:
                print(f"  {p:.1f}th >= 95th -> GENERALISES. The edge is a market")
                print("  behaviour, not a gold artefact.")
            elif p >= 80:
                print(f"  {p:.1f}th, in the 80-95 band -> WEAK generalisation.")
                print("  Consistent with a small real effect, not proof of one.")
            else:
                print(f"  {p:.1f}th < 80th -> DOES NOT GENERALISE. The gold")
                print("  results should be treated as instrument-specific.")


if __name__ == "__main__":
    main()
