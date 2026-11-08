#!/usr/bin/env python3
"""Pre-registered multi-market gauntlet for the scale-free 15m strategy.

CRITERION, FIXED BEFORE RUNNING (do not edit after seeing results):

    pass on a market = >= 80th percentile against random entry at MATCHED
                       EXPOSURE, with >= 40 trades (below that the percentile
                       is noise and the market scores as inconclusive)

    >= 6 of 9 non-gold markets pass  -> REAL
       4-5 of 9                      -> WEAK, not tradeable alone
    <= 3 of 9                        -> REJECT

Gold is shown for continuity and carries NO evidential weight: it is where the
strategy was built and tuned, so it cannot confirm a hypothesis derived from it.

The stop is expressed in each instrument's OWN volatility units rather than
gold's -- one deterministic number per market, no search. That qualifier is the
whole test: an earlier version of this applied gold's stop to EURUSD (half the
volatility) and wrongly concluded the logic failed there.

Checkpoints per market, because a 500k-bar run plus a null test is minutes of
compute and losing it to a timeout is avoidable.

    python mm15.py --market XAGUSD
    python mm15.py --all
    python mm15.py --summary
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
from null_test import run_null                      # noqa: E402
from strategy import Params, run_strategy           # noqa: E402
import pine_ta as ta                                # noqa: E402

CFG = os.environ.get("MM_CFG", "configs/gold_15m_scalefree.json")
OUT = os.environ.get("MM_OUT", "results/mm15")
CAPITAL = 6000.0
TRIALS = 400
PASS_PCT = 80.0
MIN_TRADES = 40

REFERENCE = "xauusd"
MARKETS = ["xauusd", "xagusd", "xcuusd", "bcousd", "spx500usd",
           "de30eur", "eurusd", "gbpusd", "usdjpy", "audusd"]
SCORED = [m for m in MARKETS if m != REFERENCE]


def atr_pct(df: pd.DataFrame) -> float:
    return float((ta.atr(df["high"], df["low"], df["close"], 14)
                  / df["close"]).median())


def run_market(stub: str) -> dict:
    os.makedirs(OUT, exist_ok=True)
    path = f"{OUT}/{stub}.json"
    if os.path.exists(path):
        return json.load(open(path))

    base = json.load(open(CFG))
    ref = _normalise(_read_csv(f"{REFERENCE}_oanda_m15.csv"))
    ref_atr = atr_pct(ref)

    df = _normalise(_read_csv(f"{stub}_oanda_m15.csv"))
    ratio = atr_pct(df) / ref_atr
    p = Params(**{**base,
                  "sl_percent_long": base["sl_percent_long"] * ratio,
                  "sl_percent_short": base["sl_percent_short"] * ratio})
    cfg = BrokerConfig(CAPITAL, 1.0)

    import fetch_fred
    rates = (fetch_fred.load_daily_series("dfii10.csv")
             if os.path.exists("dfii10.csv") else None)
    res = run_strategy(df, p, cfg, rates=rates)
    m = compute_metrics(res.equity, res.trades, CAPITAL)
    try:
        null = run_null(df, p, cfg, TRIALS, 0, rates=rates)
        pct, expo = null["percentile"], null["real_exposure"]
    except SystemExit:
        pct, expo = float("nan"), float("nan")

    row = {"market": stub.upper(), "vol_ratio": ratio,
           "stop": p.sl_percent_long, "trades": m["trades"],
           "cagr": m["cagr_pct"], "sharpe": m["sharpe"],
           "maxdd": m["max_drawdown_pct"], "pf": m["profit_factor"],
           "exposure": expo, "percentile": pct}
    json.dump(row, open(path, "w"), indent=2)
    print(f"  {stub.upper():<10}vol {ratio:>4.2f}x  stop {p.sl_percent_long:>5.2f}%  "
          f"{m['trades']:>4} trades  CAGR {m['cagr_pct']:>6.2f}%  "
          f"pctile {pct:>5.1f}")
    return row


def summarise() -> None:
    rows = [json.load(open(f"{OUT}/{s}.json"))
            for s in MARKETS if os.path.exists(f"{OUT}/{s}.json")]
    if not rows:
        raise SystemExit("no markets run yet")
    r = pd.DataFrame(rows)
    r.to_csv(f"{OUT}/mm15.csv", index=False)
    print("\nRESULTS  (vol-scaled stop, nothing else tuned per market)")
    print("=" * 96)
    print(f"{'market':<11}{'vol':>6}{'stop%':>7}{'trades':>8}{'expo%':>7}"
          f"{'CAGR%':>8}{'Sharpe':>8}{'maxDD%':>9}{'PF':>7}{'pctile':>8}")
    print("-" * 96)
    for _, x in r.iterrows():
        tag = "  (known)" if x["market"] == REFERENCE.upper() else ""
        thin = " THIN" if x["trades"] < MIN_TRADES else ""
        print(f"{x['market']:<11}{x['vol_ratio']:>6.2f}{x['stop']:>7.2f}"
              f"{x['trades']:>8.0f}{x['exposure']:>7.1f}{x['cagr']:>8.2f}"
              f"{x['sharpe']:>8.2f}{x['maxdd']:>9.2f}{x['pf']:>7.2f}"
              f"{x['percentile']:>8.1f}{tag}{thin}")

    sc = r[r["market"] != REFERENCE.upper()]
    usable = sc[sc["trades"] >= MIN_TRADES]
    passed = usable[usable["percentile"] >= PASS_PCT]
    print("\nAGAINST THE PRE-REGISTERED CRITERION")
    print("=" * 96)
    print(f"  scored markets            : {len(sc)}")
    if len(sc) > len(usable):
        thin = ", ".join(sc[sc['trades'] < MIN_TRADES]['market'])
        print(f"  inconclusive (<{MIN_TRADES} trades): {thin}")
    print(f"  clearing the {PASS_PCT:.0f}th percentile: {len(passed)}/{len(usable)}"
          f"   [{', '.join(passed['market']) or 'none'}]")
    n = len(usable)
    if n and len(passed) >= 6:
        v = "REAL. The edge appears across markets, not just gold."
    elif n and len(passed) >= 4:
        v = "WEAK and inconsistent. Not tradeable on its own."
    else:
        v = "REJECT. Gold was where it was built; it does not transfer."
    print(f"\n  VERDICT: {v}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--market")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    if a.summary:
        summarise()
    elif a.market:
        run_market(a.market.lower())
    elif a.all:
        for s in MARKETS:
            run_market(s)
        summarise()
    else:
        raise SystemExit("pass --market NAME, --all or --summary")


if __name__ == "__main__":
    main()
