#!/usr/bin/env python3
"""Phase 0 gate: does a strategy produce the same trades on two data feeds?

This is the test that should run FIRST, before any performance number is
computed. On the RSI Boll Squeeze it was run last, and it invalidated weeks of
comparison work in an afternoon: only 43% of long trades and roughly 0% of short
trades survived moving between two feeds of the same instrument.

The logic is simple and the consequence is not. If a strategy's trades cannot be
reproduced on a second vendor's bars, they will not be reproduced by your
broker's fills either -- a broker's feed is a third feed. Any performance
statistic measured to a precision finer than the disagreement between feeds is
measuring the vendor, not the strategy.

    python feed_compare.py --a xauusd_1h.csv --b xauusd_oanda_h1.csv
    python feed_compare.py --a xauusd_1h.csv --b xauusd_oanda_h1.csv --config v3
    python feed_compare.py --self-test

PASS/FAIL, fixed in advance:
    >= 80% of trades reproduced  -> robust enough to evaluate
    60-80%                       -> marginal; treat all statistics as noisy
    <  60%                       -> reject; you are measuring the data vendor
"""

from __future__ import annotations

import argparse
import json
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
from strategy import Params, run_strategy           # noqa: E402

PASS, MARGINAL = 80.0, 60.0

CONFIGS = {
    "v1": dict(fix_keltner_range=True, fix_long_stop_ratchet=True),
    "faithful": dict(),
}


def align(a: pd.DataFrame, b: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Restrict both feeds to the bars they share.

    Comparing over different spans would confound a feed disagreement with
    simply having more history on one side.
    """
    common = a.index.intersection(b.index)
    info = {"a_bars": len(a), "b_bars": len(b), "common": len(common),
            "a_only": len(a) - len(common), "b_only": len(b) - len(common)}
    return a.loc[common], b.loc[common], info


def price_agreement(a: pd.DataFrame, b: pd.DataFrame) -> dict:
    d = (a["close"] - b["close"]).abs()
    return {"mean_abs": float(d.mean()), "max_abs": float(d.max()),
            "mean_pct": float(100 * (d / a["close"]).mean()),
            "return_corr": float(np.corrcoef(
                a["close"].pct_change().fillna(0),
                b["close"].pct_change().fillna(0))[0, 1])}


def match_trades(ta: pd.DataFrame, tb: pd.DataFrame,
                 tol_hours: int = 2) -> dict:
    """Fraction of feed-A trades with a feed-B trade at the same entry bar."""
    if ta.empty or tb.empty:
        return {"a": len(ta), "b": len(tb), "matched": 0, "pct": 0.0}
    ea = pd.to_datetime(ta["entry_time"], utc=True).sort_values()
    eb = pd.to_datetime(tb["entry_time"], utc=True).sort_values()
    tol = pd.Timedelta(hours=tol_hours)
    matched = sum(1 for t in ea if (eb - t).abs().min() <= tol)
    return {"a": len(ea), "b": len(eb), "matched": matched,
            "pct": 100.0 * matched / len(ea)}


def compare(a: pd.DataFrame, b: pd.DataFrame, params: Params,
            cfg: BrokerConfig, label_a: str, label_b: str) -> float:
    a, b, info = align(a, b)
    print(f"\nBars: {label_a} {info['a_bars']:,}  {label_b} {info['b_bars']:,}  "
          f"overlapping {info['common']:,}")
    if info["common"] < 2000:
        print("  WARNING: fewer than 2,000 shared bars; the result will be noisy")

    p = price_agreement(a, b)
    print(f"\nPrices        mean abs diff {p['mean_abs']:.4f} "
          f"({p['mean_pct']:.4f}% of price)   max {p['max_abs']:.3f}")
    print(f"              return correlation {p['return_corr']:.5f}")

    # Load the FRED series if the config needs it. Without this, any config
    # with use_macro_filter / rate_filter_mode='replace' crashes here -- which
    # is every one of the live gold configs.
    rates = None
    if getattr(params, "use_macro_filter", False) or \
            getattr(params, "rate_filter_mode", "off") != "off":
        import fetch_fred
        if os.path.exists("dfii10.csv"):
            rates = fetch_fred.load_daily_series("dfii10.csv")
        else:
            raise SystemExit(
                "this config uses the FRED real-yield filter but dfii10.csv is "
                "missing.\n  python fetch_fred.py --series DFII10 --out dfii10.csv")

    ra = run_strategy(a, params, cfg, rates=rates)
    rb = run_strategy(b, params, cfg, rates=rates)
    ma = compute_metrics(ra.equity, ra.trades, cfg.initial_capital)
    mb = compute_metrics(rb.equity, rb.trades, cfg.initial_capital)

    print(f"\n{'':<22}{label_a:>16}{label_b:>16}")
    print("-" * 54)
    for lab, k, f in [("trades", "trades", "{:,.0f}"),
                      ("win rate %", "win_rate_pct", "{:.1f}"),
                      ("profit factor", "profit_factor", "{:.2f}"),
                      ("CAGR %", "cagr_pct", "{:.2f}"),
                      ("Sharpe", "sharpe", "{:.2f}"),
                      ("max drawdown %", "max_drawdown_pct", "{:.2f}")]:
        va, vb = ma.get(k, np.nan), mb.get(k, np.nan)
        print(f"{lab:<22}{f.format(va):>16}{f.format(vb):>16}")

    fwd = match_trades(ra.trades, rb.trades)
    rev = match_trades(rb.trades, ra.trades)
    pct = (fwd["pct"] + rev["pct"]) / 2

    print(f"\nTRADE REPRODUCIBILITY")
    print("-" * 54)
    print(f"  {label_a} trades found in {label_b}: {fwd['matched']}/{fwd['a']} "
          f"({fwd['pct']:.1f}%)")
    print(f"  {label_b} trades found in {label_a}: {rev['matched']}/{rev['a']} "
          f"({rev['pct']:.1f}%)")
    print(f"  symmetric score: {pct:.1f}%")

    print(f"\nVERDICT")
    print("-" * 54)
    if pct >= PASS:
        print(f"  PASS ({pct:.1f}% >= {PASS:.0f}%). Trades survive a change of")
        print("  data vendor. Performance statistics are worth computing.")
    elif pct >= MARGINAL:
        print(f"  MARGINAL ({pct:.1f}%). Roughly a third of trades depend on")
        print("  which vendor you used. Treat differences between strategy")
        print("  variants smaller than the feed gap as noise.")
    else:
        print(f"  FAIL ({pct:.1f}% < {MARGINAL:.0f}%). Most trades do not survive")
        print("  a change of feed, so they will not survive live execution")
        print("  either. Fix the signal before measuring anything else:")
        print("    - avoid triggers on rare tail excursions (2-sigma bands etc)")
        print("    - reduce the number of simultaneous knife-edge conditions")
        print("    - prefer conditions true over a range, not at an instant")
    return pct


def self_test() -> int:
    from synth import make_bars
    fails = []

    def check(n, c, d=""):
        print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"  {d}" if not c else ""))
        if not c:
            fails.append(n)

    a = make_bars(6000, seed=4)
    # A "second feed" perturbed by the magnitude measured between OANDA and
    # Dukascopy (~0.009% of price).
    #
    # The noise must be INDEPENDENT per bar and per field. An earlier version
    # scaled every price on a bar by one common factor, which reproduced 100%
    # of trades -- because a band computed from those same prices moves with
    # them, so the crossover is undisturbed. Real feeds disagree quote by
    # quote, which changes bar SHAPE, and that is what flips a crossover.
    rng = np.random.default_rng(0)
    b = a.copy()
    for c in ("open", "high", "low", "close"):
        b[c] = b[c] * (1 + rng.normal(0, 0.00009, len(a)))
    b["high"] = b[["open", "high", "low", "close"]].max(axis=1)
    b["low"] = b[["open", "high", "low", "close"]].min(axis=1)

    aa, bb, info = align(a, b)
    check("alignment keeps all shared bars", info["common"] == len(a))
    p = price_agreement(aa, bb)
    check("perturbation is small", p["mean_pct"] < 0.05, f"{p['mean_pct']:.4f}%")
    check("returns still highly correlated", p["return_corr"] > 0.99,
          f"{p['return_corr']:.5f}")

    cfg = BrokerConfig(4000, 1)
    par = Params(**CONFIGS["v1"])
    ra, rb = run_strategy(aa, par, cfg), run_strategy(bb, par, cfg)
    m = match_trades(ra.trades, rb.trades)
    check("identical feeds would match perfectly",
          match_trades(ra.trades, ra.trades)["pct"] == 100.0)
    check("perturbed feed loses some trades", m["pct"] < 100.0,
          f"{m['pct']:.1f}%")
    print(f"        (a 0.009% price perturbation reproduced {m['pct']:.0f}% "
          f"of trades)")
    check("empty trade lists handled",
          match_trades(pd.DataFrame(), pd.DataFrame())["pct"] == 0.0)

    print("\n" + "=" * 58)
    if fails:
        print(f"{len(fails)} FAILED: {', '.join(fails)}")
        return 1
    print("all checks passed")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a"); ap.add_argument("--b")
    ap.add_argument("--config", default="v1",
                    help=f"one of {sorted(CONFIGS)}, or a JSON file of Params")
    ap.add_argument("--capital", type=float, default=4000.0)
    ap.add_argument("--point-value", type=float, default=1.0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())
    if not args.a or not args.b:
        raise SystemExit("need --a and --b (or --self-test)")

    if args.config in CONFIGS:
        cfgd = CONFIGS[args.config]
    elif os.path.exists(args.config):
        cfgd = json.load(open(args.config))
    else:
        raise SystemExit(f"unknown config {args.config!r}")

    a = _normalise(_read_csv(args.a))
    b = _normalise(_read_csv(args.b))
    pct = compare(a, b, Params(**cfgd),
                  BrokerConfig(initial_capital=args.capital,
                               point_value=args.point_value),
                  os.path.basename(args.a)[:14], os.path.basename(args.b)[:14])
    sys.exit(0 if pct >= MARGINAL else 1)


if __name__ == "__main__":
    main()
