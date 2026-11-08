#!/usr/bin/env python3
"""Does the entry logic beat random entry at the same exposure?

This is the test that decides whether there is anything to model.

A long-only strategy in a rising market makes money whether or not its entry
rule works, simply by being in the market some of the time. Comparing it to
buy-and-hold does not separate those two effects, because buy-and-hold is in the
market 100% of the time and the strategy is not.

The right null hypothesis is: **random entries, same number of trades, same
holding-period distribution, same instrument, same period.** If the real
strategy does not land in the tail of that distribution, its entry signal is
not adding information -- the returns come from exposure to gold, not from
timing.

The holding periods are resampled from the strategy's own trades, so the null
inherits its exposure profile and its exit behaviour. Only the *entry timing* is
randomised. That isolates exactly the thing under test.

    python null_test.py --csv xauusd_1h.csv --trials 2000
    python null_test.py --csv xauusd_1h.csv --start 2006 --end 2022
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from broker import BrokerConfig                    # noqa: E402
from data import _normalise, _read_csv             # noqa: E402
from strategy import Params, run_strategy          # noqa: E402


def random_entry_returns(close: np.ndarray, n_trades: int,
                         holding: np.ndarray, rng: np.random.Generator,
                         direction: int = 1,
                         return_stats: bool = False):
    """Total compounded return of `n_trades` randomly-timed, non-overlapping trades.

    Non-overlap is enforced the same way the real engine enforces it, so the
    null cannot cheat by holding several positions at once.
    """
    n = close.size
    log_growth = 0.0
    cursor = 0
    placed = 0
    bars_held = 0
    mean_hold = float(holding.mean())
    # Space entries so n_trades non-overlapping holds of the observed length
    # distribution fit inside the sample, giving the null the SAME exposure as
    # the strategy. Without this the null would be under-invested and would
    # lose by construction.
    room = max(1, int((n - n_trades * mean_hold) // max(n_trades, 1)))

    while placed < n_trades and cursor < n - 2:
        gap = int(rng.integers(0, max(2 * room, 2)))
        entry = cursor + gap
        if entry >= n - 2:
            break
        hold = int(holding[rng.integers(0, holding.size)])
        exit_i = min(entry + max(hold, 1), n - 1)
        r = (close[exit_i] - close[entry]) / close[entry] * direction
        log_growth += np.log1p(max(r, -0.99))
        bars_held += exit_i - entry
        cursor = exit_i + 1
        placed += 1

    total = float(np.expm1(log_growth)) if placed else 0.0
    if return_stats:
        return total, placed, bars_held
    return total


def run_null(df: pd.DataFrame, params: Params, cfg: BrokerConfig,
             trials: int, seed: int = 0, rates=None) -> dict:
    res = run_strategy(df, params, cfg, rates=rates)
    trades = res.trades
    if trades.empty:
        raise SystemExit("the strategy produced no trades over this period")

    # Compounded return of the real strategy, trade by trade, so the null and
    # the real number are computed the same way.
    real_ret = trades["pnl"] / (trades["entry_price"] * trades["qty"])
    real_total = float(np.expm1(np.log1p(real_ret.clip(lower=-0.99)).sum()))

    holding = trades["bars_held"].to_numpy()
    holding = holding[holding > 0]
    close = df["close"].to_numpy(float)

    rng = np.random.default_rng(seed)
    results = [random_entry_returns(close, len(trades), holding, rng,
                                    return_stats=True)
               for _ in range(trials)]
    draws = np.array([r[0] for r in results])
    null_trades = np.array([r[1] for r in results])
    null_bars = np.array([r[2] for r in results])

    pct = float((draws < real_total).mean() * 100.0)
    return {
        "trades": len(trades),
        "null_trades": float(null_trades.mean()),
        "real_exposure": 100.0 * float(holding.sum()) / len(df),
        "null_exposure": 100.0 * float(null_bars.mean()) / len(df),
        "real_total_return": 100.0 * real_total,
        "null_mean": 100.0 * float(draws.mean()),
        "null_median": 100.0 * float(np.median(draws)),
        "null_p05": 100.0 * float(np.percentile(draws, 5)),
        "null_p95": 100.0 * float(np.percentile(draws, 95)),
        "percentile": pct,
        "mean_hold": float(holding.mean()),
        "draws": draws,
    }


def report(label: str, r: dict) -> None:
    print(f"\n{label}")
    print("-" * 70)
    print(f"  strategy trades            {r['trades']}"
          f"   (null placed {r['null_trades']:.0f} on average)")
    print(f"  mean holding period        {r['mean_hold']:.0f} bars")
    print(f"  exposure  strategy {r['real_exposure']:.1f}%"
          f"   null {r['null_exposure']:.1f}%"
          f"   {'MATCHED' if abs(r['real_exposure']-r['null_exposure']) < 3 else 'MISMATCH -- comparison is unfair'}")
    print(f"  strategy total return      {r['real_total_return']:>9,.1f}%")
    print(f"  random-entry mean          {r['null_mean']:>9,.1f}%")
    print(f"  random-entry median        {r['null_median']:>9,.1f}%")
    print(f"  random-entry 5th-95th pct  {r['null_p05']:>9,.1f}%  to {r['null_p95']:>8,.1f}%")
    print(f"\n  the strategy beat {r['percentile']:.1f}% of random-entry runs")

    p = r["percentile"]
    if p >= 95:
        print("  -> outside the top 5% of the null. The entry timing is doing")
        print("     real work; there is something for a model to learn from.")
    elif p >= 80:
        print("  -> better than most random entries but inside the null's range.")
        print("     Suggestive, not established.")
    else:
        print("  -> INSIDE the random-entry distribution. At this exposure and")
        print("     holding period, the entry signal is not distinguishable from")
        print("     picking dates out of a hat. The returns come from being long")
        print("     gold part of the time, not from the timing rule.")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--trials", type=int, default=2000)
    ap.add_argument("--capital", type=float, default=4000.0)
    ap.add_argument("--point-value", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--keltner-fix", action="store_true",
                    help="test the repaired variant instead of the original")
    args = ap.parse_args()

    df = _normalise(_read_csv(args.csv))
    cfg = BrokerConfig(initial_capital=args.capital, point_value=args.point_value)
    params = Params(fix_keltner_range=args.keltner_fix)

    print(f"data: {len(df):,} bars  {df.index[0]:%Y-%m-%d} -> {df.index[-1]:%Y-%m-%d}")
    print(f"testing: {'Keltner-repaired' if args.keltner_fix else 'faithful'} "
          f"variant, {args.trials:,} random-entry trials")

    for label, a, b in [("FULL 2006-2026", None, None),
                        ("OUT-OF-SAMPLE 2006-2022", "2006-01-01", "2022-12-31"),
                        ("TUNED REGIME 2023-2026", "2021-06-01", "2026-12-31")]:
        sub = df if a is None else df[a:b]
        report(label, run_null(sub, params, cfg, args.trials, args.seed))


if __name__ == "__main__":
    main()
