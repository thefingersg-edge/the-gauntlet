#!/usr/bin/env python3
"""Do any COMBINATIONS of the signals we tested work, where the singles did not?

Three ways of combining, all of which you suggested:

    AND        trade X only when Y also agrees          (confirmation)
    FLIP       trade X when Y is true, the OPPOSITE of X when Y is false
               (regime switching -- trend in one state, fade in the other)
    VOTE       majority of three signals

THE TRAP THIS IS BUILT TO AVOID

Combining n signals produces n^2-ish candidates. Testing ~100 combinations at a
5% false-pass rate yields ~5 winners from pure noise, and they will look
excellent. So this reports two numbers together:

    observed  -- how many combinations pass the era-consistency bar
    null      -- how many pass when the SAME test is run on time-shuffled
                 versions of the same signals, which have identical marginal
                 frequencies and zero real information

If observed is not clearly above null, the passes are noise and nothing has
been found. That comparison is the entire point of the module.

    python combine_test.py --horizon 63
"""
from __future__ import annotations

import argparse
import itertools
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import _normalise, _read_csv            # noqa: E402

ERAS = [("2006-12", "2006-01-01", "2012-12-31"),
        ("2013-19", "2013-01-01", "2019-12-31"),
        ("2020-26", "2020-01-01", None)]

MARKETS = ["xauusd", "xagusd", "xcuusd", "spx500usd",
           "eurusd", "gbpusd", "usdjpy", "audusd"]


def base_signals(stub: str) -> tuple[pd.DataFrame, pd.Series]:
    d = _normalise(_read_csv(f"{stub}_oanda_h1.csv")).resample("1D").agg(
        {"high": "max", "low": "min", "close": "last"}).dropna()
    d.index = d.index.tz_localize(None)
    c = d["close"]
    ret = c.pct_change()

    cot_path = f"cot/{stub}_cot.csv"
    if os.path.exists(cot_path):
        cot = pd.read_csv(cot_path, parse_dates=["available_from"]) \
                .set_index("available_from").sort_index()
        z = cot["net_spec_z156"].reindex(d.index, method="ffill")
    else:
        z = pd.Series(np.nan, index=d.index)

    rv = ret.rolling(60).std()
    sig = pd.DataFrame({
        "trend200":    c > c.rolling(200).mean(),
        "mom12m":      c > c.shift(252),
        "cot_long":    z > 0,
        "cot_sqz":     z < -1,               # crowded short
        "lowvol":      rv < rv.rolling(500).median(),
        "above_mid":   c > (d["high"].rolling(200).max()
                            + d["low"].rolling(200).min()) / 2,
    }, index=d.index).fillna(False)
    return sig, c


def edge(cond: pd.Series, fwd: pd.Series) -> list:
    out = []
    for _, a, b in ERAS:
        ss, ff = cond[a:b].fillna(False), fwd[a:b]
        out.append(ff[ss].mean() - ff[~ss].mean()
                   if ss.sum() > 30 and (~ss).sum() > 30 else np.nan)
    return out


def consistent(e: list) -> bool:
    return all(np.isfinite(x) for x in e) and len({np.sign(x) for x in e}) == 1


def build_combos(sig: pd.DataFrame) -> dict:
    names = list(sig.columns)
    out = {}
    for a, b in itertools.combinations(names, 2):
        out[f"{a} AND {b}"] = sig[a] & sig[b]
        out[f"{a} FLIP on {b}"] = (sig[a] & sig[b]) | (~sig[a] & ~sig[b])
    for trio in itertools.combinations(names, 3):
        out["VOTE " + "+".join(trio)] = sig[list(trio)].sum(axis=1) >= 2
    return out


def run(horizon: int, shuffle_seed: int | None) -> tuple[int, int, list]:
    """Return (passes, total, detail). shuffle_seed != None -> the null."""
    tally: dict[str, int] = {}
    total_combos = 0
    for stub in MARKETS:
        if not os.path.exists(f"{stub}_oanda_h1.csv"):
            continue
        sig, c = base_signals(stub)
        if shuffle_seed is not None:
            rng = np.random.default_rng(shuffle_seed + hash(stub) % 1000)
            # Preserve each signal's marginal frequency, destroy its timing.
            sig = pd.DataFrame({k: rng.permutation(v.to_numpy())
                                for k, v in sig.items()}, index=sig.index)
        fwd = (c.shift(-horizon) / c - 1) * 100
        combos = build_combos(sig)
        total_combos = len(combos)
        for name, cond in combos.items():
            if consistent(edge(cond, fwd)):
                tally[name] = tally.get(name, 0) + 1
    detail = sorted(tally.items(), key=lambda x: -x[1])
    passes = sum(1 for _, n in detail if n >= 6)
    return passes, total_combos, detail


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--horizon", type=int, default=63)
    ap.add_argument("--null-runs", type=int, default=3)
    args = ap.parse_args()

    obs, n_combos, detail = run(args.horizon, None)
    print(f"COMBINATION TEST -- {n_combos} combinations x {len(MARKETS)} markets, "
          f"{args.horizon}-day horizon")
    print("  pass = sign-consistent across all 3 eras in >=6 of 8 markets")
    print("=" * 84)
    print(f"\n  OBSERVED: {obs} combinations pass\n")
    print(f"  {'combination':<44}{'markets consistent':>20}")
    print("  " + "-" * 66)
    for name, n in detail[:14]:
        flag = "  <- PASS" if n >= 6 else ""
        print(f"  {name:<44}{n:>12}/8{flag}")

    nulls = []
    for s in range(args.null_runs):
        p, _, _ = run(args.horizon, 1000 + s)
        nulls.append(p)
    print(f"\n  NULL (same test, signals time-shuffled): {nulls}  "
          f"mean {np.mean(nulls):.1f}")
    print()
    if obs > np.mean(nulls) + 2:
        print("  -> observed clearly exceeds the null. Worth a closer look.")
    else:
        print("  -> observed is within noise of the null. The passes are what")
        print("     random signals of the same frequency produce. Nothing found.")


if __name__ == "__main__":
    main()
