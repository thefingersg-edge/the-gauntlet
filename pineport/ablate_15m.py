#!/usr/bin/env python3
"""Which of the 15m additions actually earn their place?

Each row removes exactly ONE addition and re-measures. A filter that helps
should make the numbers WORSE when removed -- on the unseen window, not the
one it was fitted on. Anything that only looks good in the training column
is a fitting artefact.

    python ablate_15m.py > results/ablate_15m.txt
"""
from __future__ import annotations

import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from broker import BrokerConfig                    # noqa: E402
from data import _normalise, _read_csv             # noqa: E402
from metrics import compute_metrics                # noqa: E402
from null_test import run_null                     # noqa: E402
from strategy import Params, run_strategy          # noqa: E402
import fetch_fred                                  # noqa: E402

TRIALS = 500
CAPITAL = 6000.0

ABLATIONS = [
    ("as written",            {}),
    ("- rate filter (FRED)",  {"use_macro_filter": False, "rate_filter_mode": "off"}),
    ("- vol gate LONG",       {"use_volatility_filter": False}),
    ("- vol gate SHORT",      {"use_volatility_filter_short": False}),
    ("- ADX long",            {"use_adx_filter": False}),
    ("- ADX short",           {"use_adx_filter_short": False}),
    ("- squeeze",             {"use_squeeze_filter": False}),
    ("- profit ladder",       {"use_ladder": False}),
    ("- shorts entirely",     {"allow_shorts": False}),
]


def main() -> None:
    df = _normalise(_read_csv("xauusd_oanda_m15.csv"))
    rates = fetch_fred.load_daily_series("dfii10.csv")
    base = json.load(open("/tmp/v15m.json"))
    cfg = BrokerConfig(CAPITAL, 1.0)

    windows = [("TRAIN 2013-2023", df["2013-01-01":"2023-12-31"]),
               ("UNSEEN 2006-2012", df["2006-01-01":"2012-12-31"])]

    print("ABLATION -- each row removes ONE addition")
    print("=" * 100)
    hdr = f"{'variant':<24}"
    for name, _ in windows:
        hdr += f"{name:>38}"
    print(hdr)
    sub = f"{'':<24}"
    for _ in windows:
        sub += f"{'trades':>9}{'CAGR%':>9}{'PF':>8}{'pctile':>12}"
    print(sub)
    print("-" * 100)

    for label, override in ABLATIONS:
        params = Params(**{**base, **override})
        row = f"{label:<24}"
        for _, window in windows:
            try:
                res = run_strategy(window, params, cfg, rates=rates)
                met = compute_metrics(res.equity, res.trades, CAPITAL)
                if met["trades"] < 3:
                    row += f"{met['trades']:>9}{'--':>9}{'--':>8}{'--':>12}"
                    continue
                null = run_null(window, params, cfg, TRIALS, 0, rates=rates)
                row += (f"{met['trades']:>9}{met['cagr_pct']:>9.2f}"
                        f"{met['profit_factor']:>8.2f}{null['percentile']:>12.1f}")
            except SystemExit:
                row += f"{0:>9}{'--':>9}{'--':>8}{'--':>12}"
        print(row, flush=True)

    print()
    print("COST SENSITIVITY  (full sample)")
    print("=" * 100)
    params = Params(**base)
    for slip in (0.0, 0.20, 0.35, 0.60, 1.00):
        c = BrokerConfig(CAPITAL, 1.0, slippage_points=slip)
        res = run_strategy(df, params, c, rates=rates)
        met = compute_metrics(res.equity, res.trades, CAPITAL)
        print(f"  slippage {slip:>4.2f} pts   CAGR {met['cagr_pct']:>6.2f}%   "
              f"PF {met['profit_factor']:>5.2f}   Sharpe {met['sharpe']:>5.2f}",
              flush=True)


if __name__ == "__main__":
    main()
