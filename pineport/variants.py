"""Ablation study: change one thing at a time and see what it costs.

The faithful port is the reference. Every variant below flips exactly one
switch, so the difference in the results table is attributable to that switch
and nothing else. Turning several on at once first, then trying to reason
backwards about which mattered, is how people convince themselves a broken
filter was load-bearing.

    python variants.py --csv data.csv
    python variants.py --ticker GC=F --period 730d
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from broker import BrokerConfig                     # noqa: E402
from data import load_ohlcv                         # noqa: E402
from metrics import compute_metrics                 # noqa: E402
from strategy import Params, run_strategy           # noqa: E402


def build_variants(base: Params | None = None) -> dict[str, Params]:
    """Name -> Params, each differing from the baseline in one respect."""
    b = base or Params()
    return {
        "faithful (as written)": b,

        # --- individual repairs -------------------------------------------
        "fix: Keltner uses true range": b.with_(fix_keltner_range=True),
        "fix: long stop ratchets from prev": b.with_(fix_long_stop_ratchet=True),
        "fix: take-profit actually armed": b.with_(enable_take_profit=True),
        "fix: drop duplicate RSI trigger": b.with_(drop_duplicate_long_trigger=True),

        # --- filter removals, to see which gates bind ----------------------
        "no squeeze filter": b.with_(use_squeeze_filter=False),
        "no macro (4H) filter": b.with_(use_macro_filter=False),
        "no ADX filter": b.with_(use_adx_filter=False),
        "no volatility filter": b.with_(use_volatility_filter=False),
        "no filters at all": b.with_(use_squeeze_filter=False, use_macro_filter=False,
                                     use_adx_filter=False, use_volatility_filter=False),

        # --- direction isolation ------------------------------------------
        "longs only": b.with_(allow_shorts=False),
        "shorts only": b.with_(allow_longs=False),

        # --- everything repaired ------------------------------------------
        "all repairs together": b.with_(
            fix_keltner_range=True, fix_long_stop_ratchet=True,
            enable_take_profit=True, drop_duplicate_long_trigger=True),
    }


def run_all(df: pd.DataFrame, cfg: BrokerConfig,
            base: Params | None = None) -> pd.DataFrame:
    rows = []
    benchmark = df["close"]
    for name, p in build_variants(base).items():
        res = run_strategy(df, p, cfg)
        m = compute_metrics(res.equity, res.trades, cfg.initial_capital, benchmark)
        rows.append({
            "variant": name,
            "trades": m.get("trades", 0),
            "return_%": m.get("return_pct", np.nan),
            "sharpe": m.get("sharpe", np.nan),
            "max_dd_%": m.get("max_drawdown_pct", np.nan),
            "win_%": m.get("win_rate_pct", np.nan),
            "pf": m.get("profit_factor", np.nan),
            "avg_bars": m.get("avg_bars_held", np.nan),
            "expo_%": m.get("exposure_pct", np.nan),
        })
    out = pd.DataFrame(rows)
    bh = compute_metrics(df["close"] / df["close"].iloc[0] * cfg.initial_capital,
                         pd.DataFrame(), cfg.initial_capital)
    out.attrs["buy_hold_return"] = bh.get("return_pct", np.nan)
    out.attrs["buy_hold_sharpe"] = bh.get("sharpe", np.nan)
    out.attrs["buy_hold_dd"] = bh.get("max_drawdown_pct", np.nan)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ticker", default="GC=F")
    ap.add_argument("--period", default="730d")
    ap.add_argument("--interval", default="1h")
    ap.add_argument("--csv", default=None)
    ap.add_argument("--capital", type=float, default=4000.0)
    ap.add_argument("--point-value", type=float, default=1.0)
    ap.add_argument("--commission-pct", type=float, default=0.0)
    ap.add_argument("--slippage", type=float, default=0.0)
    args = ap.parse_args()

    df, info = load_ohlcv(ticker=args.ticker, period=args.period,
                          interval=args.interval, csv_path=args.csv)
    print(f"data: {info.describe()}\n")

    cfg = BrokerConfig(initial_capital=args.capital, point_value=args.point_value,
                       commission_pct=args.commission_pct,
                       slippage_points=args.slippage)
    table = run_all(df, cfg)

    with pd.option_context("display.width", 200, "display.max_columns", 20,
                           "display.float_format", lambda v: f"{v:,.2f}"):
        print(table.to_string(index=False))

    print(f"\nbuy & hold: return {table.attrs['buy_hold_return']:,.2f}%  "
          f"sharpe {table.attrs['buy_hold_sharpe']:,.2f}  "
          f"max dd {table.attrs['buy_hold_dd']:,.2f}%")

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(out_dir, exist_ok=True)
    table.to_csv(os.path.join(out_dir, "variants.csv"), index=False)
    print(f"\nwrote {os.path.join(out_dir, 'variants.csv')}")

    n = int(table.loc[table["variant"] == "faithful (as written)", "trades"].iloc[0])
    if n < 30:
        print(f"\nWARNING: the faithful strategy produced {n} trades over this\n"
              f"sample. Below roughly 30-50 trades, none of the ratios above are\n"
              f"statistically meaningful, and there is not enough data to fit or\n"
              f"validate a machine learning filter on top. Raising the trade count\n"
              f"has to come before any modelling work.")


if __name__ == "__main__":
    main()
