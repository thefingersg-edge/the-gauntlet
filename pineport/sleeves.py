#!/usr/bin/env python3
"""Raise participation by running the strategy as K independent sleeves.

WHY THIS, AND NOT A NEW SIGNAL
------------------------------
Three findings from POSTMORTEM.md drive this design, and none of them is "the
entry rule needs improving":

  1. The long entry beats random entry at matched exposure -- 99.5th percentile
     full sample, 86.7th out-of-sample. There IS timing information.
  2. It is invested only 27% of the time. Beating random by 2.2x on a quarter of
     the exposure still loses to buy-and-hold at 100%.
  3. `pyramiding = 0` rejects 19 of every 24 signals. A signal arriving while a
     position is open is simply discarded.

So the binding constraint is participation, not selectivity. This does not try
to find a better entry; it deploys the existing one more of the time.

HOW
---
Instead of rewriting the broker for concurrent positions -- which would mean
re-implementing the stop ladder for N simultaneous trades and re-testing all of
it -- the same effect is achieved by running the *existing, verified*
single-position engine K times:

    sleeve 1  takes the signals the current strategy takes
    sleeve 2  takes signals that fired while sleeve 1 was in a position
    sleeve 3  takes signals that fired while both 1 and 2 were busy
    ...

This is exactly equivalent to K concurrent positions allocated first-free-first,
each carrying its own independent trailing stop from its own entry. Every piece
of tested logic is reused unchanged, which matters given how much of this
project's value came from the engine being verifiably correct.

Capital is split evenly: each sleeve gets 1/K, so total capital at risk is
unchanged and the comparison against K=1 is like-for-like. Raising exposure by
levering up would be a different (and much easier) claim.

WHAT WOULD MAKE THIS FAIL
-------------------------
* **Clustering.** If signals arrive in bursts, sleeves fill simultaneously and
  hold correlated positions -- more exposure but not more diversification. The
  report measures how correlated the sleeve returns actually are.
* **Later sleeves are worse.** Sleeve 2 takes signals sleeve 1 declined *because
  it was busy*, which is not random -- it correlates with recent signal
  frequency. If per-sleeve returns decay sharply with K, the extra participation
  is buying worse trades.
* **Concentration may not improve.** The point is partly to fix "10 trades are
  92% of profit". If concentration stays extreme, this has not helped.

    python sleeves.py --csv xauusd_1h.csv --max-sleeves 6
    python sleeves.py --csv xauusd_1h.csv --csv2 xagusd_1h.csv --csv3 eurusd_1h.csv
    python sleeves.py --self-test
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

from broker import BrokerConfig                     # noqa: E402
from data import _normalise, _read_csv              # noqa: E402
from metrics import compute_metrics                 # noqa: E402
from strategy import Params, compute_indicators, run_strategy   # noqa: E402

BASE = dict(fix_keltner_range=True, fix_long_stop_ratchet=True, allow_shorts=False)


def run_sleeves(df: pd.DataFrame, params: Params, cfg: BrokerConfig,
                max_sleeves: int = 6) -> dict:
    """Allocate signals across K sleeves, first-free-first.

    Returns the combined equity curve, the per-sleeve results, and enough
    diagnostics to tell whether the extra sleeves are doing anything useful.
    """
    ind = compute_indicators(df, params)
    available = ind["long_signal"].to_numpy(bool).copy()
    n = len(df)

    per_sleeve_capital = cfg.initial_capital / max_sleeves
    sleeve_cfg = BrokerConfig(
        initial_capital=per_sleeve_capital, point_value=cfg.point_value,
        commission_per_contract=cfg.commission_per_contract,
        commission_pct=cfg.commission_pct, slippage_points=cfg.slippage_points)

    sleeves, curves = [], []
    for k in range(max_sleeves):
        if not available.any():
            break
        res = run_strategy(df, params, sleeve_cfg, indicators=ind,
                           signal_filter=available)
        if res.trades.empty:
            break

        # A signal was CONSUMED if this sleeve opened a trade on the next bar.
        consumed = np.zeros(n, dtype=bool)
        for entry_bar in res.trades["entry_bar"].to_numpy(int):
            if entry_bar - 1 >= 0:
                consumed[entry_bar - 1] = True

        sleeves.append(res)
        curves.append(res.equity)
        available = available & ~consumed

    if not sleeves:
        raise SystemExit("no trades in any sleeve")

    # Idle sleeves still hold their cash, so the portfolio is the sum of all K
    # allocations whether or not every sleeve traded.
    combined = pd.Series(0.0, index=df.index)
    for c in curves:
        combined = combined.add(c.reindex(df.index, method="ffill"), fill_value=0.0)
    idle = max_sleeves - len(curves)
    combined = combined + idle * per_sleeve_capital

    all_trades = pd.concat([s.trades for s in sleeves], ignore_index=True)
    return {"combined": combined, "sleeves": sleeves, "trades": all_trades,
            "n_used": len(sleeves), "per_sleeve_capital": per_sleeve_capital}


def analyse(df: pd.DataFrame, cfg: BrokerConfig, max_sleeves: int,
            label: str) -> pd.DataFrame:
    params = Params(**BASE)
    rows = []
    print(f"\n{label}")
    print("-" * 96)
    print(f"{'sleeves':>8}{'trades':>8}{'CAGR%':>8}{'sharpe':>8}{'maxDD%':>9}"
          f"{'calmar':>8}{'PF':>7}{'expo%':>8}{'top10 %PnL':>12}{'vs B&H':>9}")

    yrs = (df.index[-1] - df.index[0]).days / 365.25
    bh = 100 * ((df["close"].iloc[-1] / df["close"].iloc[0]) ** (1 / yrs) - 1)

    for k in range(1, max_sleeves + 1):
        r = run_sleeves(df, params, cfg, k)
        m = compute_metrics(r["combined"], r["trades"], cfg.initial_capital)
        t = r["trades"].sort_values("pnl", ascending=False)
        tot = t["pnl"].sum()
        top10 = 100 * t["pnl"].head(10).sum() / tot if tot > 0 else np.nan
        # Exposure: bars held summed across sleeves, capped at 100%.
        expo = 100 * t["bars_held"].sum() / (len(df) * k)
        rows.append({"sleeves": k, **m, "top10_pct": top10, "exposure": expo})
        print(f"{k:>8}{m['trades']:>8}{m['cagr_pct']:>8.2f}{m['sharpe']:>8.2f}"
              f"{m['max_drawdown_pct']:>9.2f}{m['calmar']:>8.3f}"
              f"{m['profit_factor']:>7.2f}{expo:>8.1f}{top10:>11.0f}%"
              f"{m['cagr_pct'] - bh:>9.2f}")
    print(f"{'buy&hold':>8}{'-':>8}{bh:>8.2f}")
    return pd.DataFrame(rows)


def sleeve_diagnostics(df: pd.DataFrame, cfg: BrokerConfig, k: int) -> None:
    """Are the later sleeves taking worse trades, and are they correlated?"""
    r = run_sleeves(df, Params(**BASE), cfg, k)
    print(f"\nPer-sleeve quality  (are later sleeves worse?)")
    print("-" * 62)
    print(f"{'sleeve':>7}{'trades':>8}{'mean ret%':>11}{'win%':>8}{'PF':>7}")
    rets = []
    for i, s in enumerate(r["sleeves"], 1):
        t = s.trades
        ret = 100 * t["pnl"] / (t["entry_price"] * t["qty"])
        rets.append(s.equity.pct_change().fillna(0))
        w = t[t["pnl"] > 0]
        gl = -t[t["pnl"] <= 0]["pnl"].sum()
        pf = w["pnl"].sum() / gl if gl > 0 else np.inf
        print(f"{i:>7}{len(t):>8}{ret.mean():>11.2f}{100*len(w)/len(t):>8.1f}{pf:>7.2f}")

    if len(rets) > 1:
        c = pd.concat(rets, axis=1).corr().to_numpy()
        off = c[np.triu_indices_from(c, k=1)]
        print(f"\n  mean pairwise correlation of sleeve returns: {np.nanmean(off):.3f}")
        print("  (near 1.0 would mean the sleeves hold the same trade at the")
        print("   same time -- more exposure but no diversification)")


def self_test() -> int:
    from synth import make_bars
    fails = []

    def check(n, c, d=""):
        print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"  {d}" if not c else ""))
        if not c:
            fails.append(n)

    df = make_bars(8000, seed=5)
    cfg = BrokerConfig(4000, 1)
    p = Params(**BASE)

    r1 = run_sleeves(df, p, cfg, 1)
    base = run_strategy(df, p, BrokerConfig(4000, 1))
    check("K=1 reproduces the ordinary strategy",
          len(r1["trades"]) == len(base.trades),
          f"{len(r1['trades'])} vs {len(base.trades)}")

    r3 = run_sleeves(df, p, cfg, 3)
    check("more sleeves take at least as many trades",
          len(r3["trades"]) >= len(r1["trades"]),
          f"{len(r3['trades'])} vs {len(r1['trades'])}")

    # No signal may be used twice.
    ent = r3["trades"]["entry_bar"].to_numpy()
    check("no signal consumed by two sleeves", len(ent) == len(set(ent.tolist())))

    # Capital must be conserved: K sleeves of capital/K start at capital.
    check("combined curve starts at full capital",
          abs(r3["combined"].iloc[0] - 4000) < 1e-6,
          f"{r3['combined'].iloc[0]:.2f}")

    ind = compute_indicators(df, p)
    check("cannot consume more signals than exist",
          len(r3["trades"]) <= int(ind["long_signal"].sum()))

    print("\n" + "=" * 56)
    if fails:
        print(f"{len(fails)} FAILED: {', '.join(fails)}")
        return 1
    print("all checks passed")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv")
    ap.add_argument("--csv2", help="second market, validated with the same config")
    ap.add_argument("--csv3", help="third market")
    ap.add_argument("--max-sleeves", type=int, default=6)
    ap.add_argument("--capital", type=float, default=4000.0)
    ap.add_argument("--point-value", type=float, default=1.0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())
    if not args.csv:
        raise SystemExit("need --csv (or --self-test)")

    cfg = BrokerConfig(initial_capital=args.capital, point_value=args.point_value)
    for path in [p for p in (args.csv, args.csv2, args.csv3) if p]:
        df = _normalise(_read_csv(path))
        name = os.path.basename(path).split("_")[0].upper()
        analyse(df, cfg, args.max_sleeves, f"{name}  ({len(df):,} bars, "
                f"{df.index[0]:%Y-%m} to {df.index[-1]:%Y-%m})")
        if path == args.csv:
            sleeve_diagnostics(df, cfg, args.max_sleeves)


if __name__ == "__main__":
    main()
