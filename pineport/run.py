#!/usr/bin/env python3
"""Command line entry point for the ported strategy.

    python run.py backtest  --ticker GC=F --period 730d --interval 1h
    python run.py diagnose  --ticker GC=F        # why signals do / don't fire
    python run.py compare   --tv-trades tv_export.csv
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from broker import BrokerConfig                      # noqa: E402
from data import load_ohlcv                          # noqa: E402
from metrics import compute_metrics, format_metrics  # noqa: E402
from strategy import Params, compute_indicators, run_strategy  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def _data_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--ticker", default="GC=F",
                    help="yfinance symbol. GC=F has real volume; XAUUSD=X does not.")
    ap.add_argument("--period", default="730d",
                    help="yfinance period. Intraday history is capped near 730d.")
    ap.add_argument("--interval", default="1h")
    ap.add_argument("--csv", default=None, help="load OHLCV from a CSV instead")
    ap.add_argument("--capital", type=float, default=4000.0)
    ap.add_argument("--point-value", type=float, default=1.0,
                    help="syminfo.pointvalue. 1 for spot XAUUSD, 100 for COMEX GC.")
    ap.add_argument("--commission-pct", type=float, default=0.0,
                    help="per-side commission as a fraction of notional, e.g. 0.0002")
    ap.add_argument("--slippage", type=float, default=0.0,
                    help="adverse price adjustment per fill, in price points")
    ap.add_argument("--no-cache", action="store_true")


def _load(args) -> tuple[pd.DataFrame, object]:
    df, info = load_ohlcv(
        ticker=args.ticker, period=args.period, interval=args.interval,
        use_cache=not args.no_cache, csv_path=args.csv,
    )
    print(f"data: {info.describe()}")
    return df, info


def _broker_cfg(args) -> BrokerConfig:
    return BrokerConfig(
        initial_capital=args.capital,
        point_value=args.point_value,
        commission_pct=args.commission_pct,
        slippage_points=args.slippage,
    )


# --------------------------------------------------------------------------

def cmd_backtest(args) -> None:
    df, _ = _load(args)
    p = Params()
    res = run_strategy(df, p, _broker_cfg(args))

    benchmark = df["close"]
    m = compute_metrics(res.equity, res.trades, args.capital, benchmark)
    print()
    print(format_metrics(m, "Faithful Pine port -- RSI Boll Squeeze"))

    os.makedirs(OUT_DIR, exist_ok=True)
    res.trades.to_csv(os.path.join(OUT_DIR, "trades.csv"), index=False)
    res.equity.to_csv(os.path.join(OUT_DIR, "equity.csv"))
    res.diagnostics.to_csv(os.path.join(OUT_DIR, "diagnostics.csv"))
    pd.Series(m).to_csv(os.path.join(OUT_DIR, "metrics.csv"))
    print(f"\nwrote trades.csv, equity.csv, diagnostics.csv, metrics.csv to {OUT_DIR}")

    if not res.trades.empty:
        cols = ["side", "entry_time", "entry_price", "exit_time", "exit_price",
                "exit_reason", "qty", "pnl", "bars_held"]
        print("\nfirst 10 trades:")
        print(res.trades[cols].head(10).to_string(index=False))


def cmd_diagnose(args) -> None:
    """Report how often each gate passes, and where the funnel collapses.

    Worth running before trusting any backtest of this strategy: several of the
    filters turn out to be no-ops, and a couple of them are the entire reason
    the trade count is what it is.
    """
    df, _ = _load(args)
    p = Params()
    ind = compute_indicators(df, p)
    n = len(df)

    gates = [
        ("RSI(1) crossover 29", "x_rsi_long"),
        ("close crosses BB lower", "x_bb_long"),
        ("SMA(1) crosses SMA(2)", "x_sma_long"),
        ("squeeze on", "sqz_on"),
        ("squeeze up (sqzOn & valL>0)", "sqz_up"),
        ("macro bullish (4H)", "macro_bullish"),
        ("ADX > 23", "trend_active"),
        ("volatility gate", "volatility_gate"),
    ]
    print("\nLONG gate pass rates")
    print("-" * 52)
    for label, key in gates:
        s = ind[key].fillna(False).astype(bool)
        print(f"{label:<32}{s.sum():>7} / {n}  ({100.0*s.mean():5.1f}%)")

    print("\nSHORT gate pass rates")
    print("-" * 52)
    for label, key in [("RSI(5) crossunder 20", "x_rsi_short"),
                       ("close crosses BB upper", "x_bb_short"),
                       ("SMA(2) crosses SMA(26)", "x_sma_short"),
                       ("squeeze down (sqzOn & valS<960)", "sqz_down")]:
        s = ind[key].fillna(False).astype(bool)
        print(f"{label:<32}{s.sum():>7} / {n}  ({100.0*s.mean():5.1f}%)")

    print("\nSignals after all gates")
    print("-" * 52)
    print(f"{'long signals':<32}{int(ind['long_signal'].sum()):>7}")
    print(f"{'short signals':<32}{int(ind['short_signal'].sum()):>7}")

    # Are the Keltner comparisons doing anything at all?
    print("\nSqueeze band sanity check (median values)")
    print("-" * 52)
    for key in ("lower_bb", "lower_kc", "upper_bb", "upper_kc", "val_l", "val_s"):
        print(f"{key:<32}{ind[key].median():>15,.2f}")
    always_on = ind["sqz_on"].fillna(False).mean()
    if always_on > 0.99:
        print("\n  NOTE: sqzOn is true on ~every bar. The Keltner channel is built\n"
              "  from price levels (range1 = high) rather than ranges, so it sits\n"
              "  thousands of points outside the Bollinger band and the squeeze\n"
              "  test can never fail. This filter is not filtering anything.")

    # Which single gate is the binding constraint?
    base = (ind["x_rsi_long"] & ind["x_bb_long"] & ind["x_sma_long"]).fillna(False)
    print(f"\nlong trigger core (3 crossovers, no filters): {int(base.sum())}")
    for label, key in [("+ squeeze", "sqz_up"), ("+ macro", "macro_bullish"),
                       ("+ adx", "trend_active"), ("+ volatility", "volatility_gate")]:
        combo = base & ind[key].fillna(False)
        print(f"  {label:<28}{int(combo.sum()):>7}")

    short_base = (ind["x_rsi_short"] & ind["x_bb_short"] & ind["x_sma_short"]).fillna(False)
    print(f"\nshort trigger core (3 crossunders, no filters): {int(short_base.sum())}")
    for a, b in [("x_rsi_short", "x_bb_short"), ("x_rsi_short", "x_sma_short"),
                 ("x_bb_short", "x_sma_short")]:
        both = (ind[a] & ind[b]).fillna(False).sum()
        print(f"  {a} AND {b}: {int(both)}")
    if short_base.sum() == 0:
        print("\n  NOTE: the three short triggers never coincide. `crossunder(close,\n"
              "  BBupper)` requires price to be falling away from the UPPER band\n"
              "  while `crossunder(rsi5, 20)` requires it to be deeply oversold.\n"
              "  Those two states are close to mutually exclusive, so the short\n"
              "  side of this strategy is structurally dead, not merely rare.")

    # Redundant conditions: gates that are the same test written two ways.
    print("\nCondition redundancy")
    print("-" * 52)
    pairs = [("x_rsi_long", "x_sma_long"), ("x_rsi_short", "x_sma_short")]
    for a, b in pairs:
        sa, sb = ind[a].fillna(False), ind[b].fillna(False)
        identical = bool((sa == sb).all())
        overlap = int((sa & sb).sum())
        print(f"{a} vs {b}: identical={identical} "
              f"(a={int(sa.sum())}, b={int(sb.sum())}, both={overlap})")
    if bool((ind["x_rsi_long"].fillna(False) == ind["x_sma_long"].fillna(False)).all()):
        print("\n  NOTE: `crossover(rsi(close,1), 29)` and `crossover(sma(close,1),\n"
              "  sma(close,2))` are the SAME test. RSI with length 1 is 100 on an\n"
              "  up bar and 0 on a down bar, so crossing 29 means 'up bar after a\n"
              "  non-up bar'. sma(close,1) crossing sma(close,2) means exactly the\n"
              "  same thing. Two of the three long triggers are one condition.")


def cmd_compare(args) -> None:
    """Compare the Python trade list against a TradingView "List of Trades" export."""
    df, _ = _load(args)
    res = run_strategy(df, Params(), _broker_cfg(args))
    py = res.trades

    tv = pd.read_csv(args.tv_trades)
    tv.columns = [c.strip().lower().replace(" ", "_").replace("/", "_")
                  for c in tv.columns]
    print(f"\nTradingView export columns: {list(tv.columns)}")

    date_col = next((c for c in tv.columns if "date" in c or "time" in c), None)
    if date_col is None:
        print("could not find a date column in the export; comparing counts only")
        print(f"python trades: {len(py)}   tradingview rows: {len(tv)}")
        return

    tv[date_col] = pd.to_datetime(tv[date_col], utc=True, errors="coerce")
    tv_entries = tv[date_col].dropna().sort_values()
    py_entries = pd.to_datetime(py["entry_time"], utc=True).sort_values()

    print(f"\npython trades: {len(py_entries)}   tradingview entries: {len(tv_entries)}")
    tol = pd.Timedelta(args.tolerance)
    matched = sum(
        1 for t in py_entries
        if (tv_entries - t).abs().min() <= tol
    ) if len(tv_entries) else 0
    print(f"matched within {args.tolerance}: {matched} "
          f"({100.0*matched/max(len(py_entries),1):.1f}% of python trades)")

    unmatched = [t for t in py_entries
                 if len(tv_entries) == 0 or (tv_entries - t).abs().min() > tol]
    if unmatched:
        print(f"\nfirst 10 python-only entries:\n  " +
              "\n  ".join(str(t) for t in unmatched[:10]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("backtest", help="run the faithful port")
    _data_args(b)
    b.set_defaults(func=cmd_backtest)

    d = sub.add_parser("diagnose", help="show gate pass rates and dead filters")
    _data_args(d)
    d.set_defaults(func=cmd_diagnose)

    c = sub.add_parser("compare", help="diff against a TradingView trade export")
    _data_args(c)
    c.add_argument("--tv-trades", required=True)
    c.add_argument("--tolerance", default="2h")
    c.set_defaults(func=cmd_compare)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
