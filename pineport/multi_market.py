#!/usr/bin/env python3
"""Test 4: does the entry logic work across markets when volatility-scaled?

Design fixed in PREREGISTRATION.md before any of this data was fetched.

The claim under test is narrow and specific: the entry rule carries timing
information in markets other than gold, PROVIDED the stop is expressed in the
instrument's own volatility units rather than in gold's. That qualifier is the
whole point -- an earlier run applied gold's 2.7% stop to EURUSD (half gold's
volatility) and concluded the logic failed there. Scaled properly it reached the
89th percentile.

Scoring counts ONLY the seven markets never previously examined. Gold, silver
and EURUSD are shown for continuity and carry no evidential weight: their
results are already known and cannot confirm a hypothesis derived from them.

    >= 6 of 7 at the 80th percentile  -> real, worth building on
       4-5 of 7                       -> weak, not tradeable alone
    <= 3 of 7                         -> reject

    python multi_market.py --run
    python multi_market.py --self-test
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

_cfg_path = os.environ.get("MM_CONFIG")
CONFIG = (json.load(open(_cfg_path)) if _cfg_path else
          dict(fix_keltner_range=True, fix_long_stop_ratchet=True))
CONFIG = {**CONFIG, "allow_shorts": False}
_BASE_STOP = float(os.environ.get("MM_BASE_STOP", "2.7"))

REFERENCE = os.environ.get("MM_REF", "xauusd_1h.csv")

#: (file, label, counts_toward_the_verdict). Fixed in PREREGISTRATION.md.
MARKETS = [
    (os.environ.get("MM_GOLD",   "xauusd_1h.csv"),       "GOLD",   False),
    (os.environ.get("MM_SILVER", "xagusd_1h.csv"),       "SILVER", False),
    (os.environ.get("MM_EUR",    "eurusd_1h.csv"),       "EURUSD", False),
    (os.environ.get("MM_GBP",    "gbpusd_1h.csv"),       "GBPUSD", True),
    (os.environ.get("MM_JPY",    "usdjpy_1h.csv"),       "USDJPY", True),
    (os.environ.get("MM_AUD",    "audusd_1h.csv"),       "AUDUSD", True),
    (os.environ.get("MM_SPX",    "usa500idxusd_1h.csv"), "S&P500", True),
    (os.environ.get("MM_DAX",    "deuidxeur_1h.csv"),    "DAX",    True),
    (os.environ.get("MM_BRENT",  "brentcmdusd_1h.csv"),  "BRENT",  True),
    (os.environ.get("MM_COPPER", "coppercmdusd_1h.csv"), "COPPER", True),
]

PASS_PERCENTILE = 80.0
MIN_TRADES = 40          # below this the percentile is noise -> inconclusive


def atr_pct(df: pd.DataFrame) -> float:
    """Median ATR(14) as a fraction of price -- the scale-free volatility measure."""
    return float((ta.atr(df["high"], df["low"], df["close"], 14) / df["close"]).median())


def scaled_stop(df: pd.DataFrame, ref_atr: float, base: float = 2.7) -> float:
    """Gold's stop expressed in this instrument's volatility units.

    One deterministic number per market. No search, no per-market tuning --
    that is what makes this a test rather than a fit.
    """
    return base * (atr_pct(df) / ref_atr)


def evaluate(path: str, ref_atr: float, trials: int, capital: float) -> dict:
    df = _normalise(_read_csv(path))
    cfg = BrokerConfig(initial_capital=capital, point_value=1.0)
    sl = scaled_stop(df, ref_atr, _BASE_STOP)
    params = Params(**{**CONFIG, "sl_percent_long": sl})

    null = run_null(df, params, cfg, trials, seed=0)
    res = run_strategy(df, params, cfg)
    m = compute_metrics(res.equity, res.trades, capital)

    yrs = (df.index[-1] - df.index[0]).days / 365.25
    drift = 100 * ((df["close"].iloc[-1] / df["close"].iloc[0]) ** (1 / yrs) - 1)

    # Per-trade percentage returns: the only cross-market comparable P&L, since
    # the ceil(equity/5000) sizing rule is calibrated to gold's price level.
    t = res.trades
    ret = (100 * t["pnl"] / (t["entry_price"] * t["qty"])) if len(t) else pd.Series(dtype=float)

    return {"path": path, "bars": len(df), "years": yrs, "stop": sl,
            "vol_ratio": atr_pct(df) / ref_atr, "drift": drift,
            "trades": null["trades"], "exposure": null["real_exposure"],
            "percentile": null["percentile"],
            "strategy_ret": null["real_total_return"],
            "random_ret": null["null_mean"],
            "mean_trade_pct": float(ret.mean()) if len(ret) else np.nan,
            "sharpe": m.get("sharpe", np.nan),
            "equity": res.equity, "trades_df": t}


def report(results: list[dict]) -> None:
    print("\nRESULTS  (vol-scaled stop, nothing else tuned per market)")
    print("=" * 104)
    print(f"{'market':<9}{'years':>6}{'vol':>6}{'stop%':>7}{'trades':>8}{'expo%':>7}"
          f"{'strategy%':>11}{'random%':>10}{'pctile':>8}{'drift%':>8}{'counts':>8}")
    print("-" * 104)
    for r in results:
        label = r["label"]
        flag = "" if r["counts"] else "  (known)"
        thin = " THIN" if r["trades"] < MIN_TRADES else ""
        print(f"{label:<9}{r['years']:>6.1f}{r['vol_ratio']:>6.2f}{r['stop']:>7.2f}"
              f"{r['trades']:>8}{r['exposure']:>7.1f}{r['strategy_ret']:>11.1f}"
              f"{r['random_ret']:>10.1f}{r['percentile']:>8.1f}{r['drift']:>8.2f}"
              f"{flag}{thin}")

    scored = [r for r in results if r["counts"]]
    usable = [r for r in scored if r["trades"] >= MIN_TRADES]
    inconclusive = [r for r in scored if r["trades"] < MIN_TRADES]
    passed = [r for r in usable if r["percentile"] >= PASS_PERCENTILE]

    print("\nAGAINST THE PRE-REGISTERED CRITERION")
    print("=" * 104)
    print(f"  never-tested markets scored : {len(scored)}")
    if inconclusive:
        print(f"  inconclusive (<{MIN_TRADES} trades) : "
              f"{', '.join(r['label'] for r in inconclusive)}")
    print(f"  clearing the {PASS_PERCENTILE:.0f}th percentile : "
          f"{len(passed)} / {len(usable)}"
          f"   [{', '.join(r['label'] for r in passed) or 'none'}]")

    n = len(usable)
    if n and len(passed) >= max(6 * n / 7, n - 1):
        v = ("REAL. The edge appears across markets, not just gold. Worth "
             "building a portfolio on.")
    elif n and len(passed) >= 4 * n / 7:
        v = ("WEAK and inconsistent. Not tradeable on its own; the vol-scaling "
             "may be doing part of the work.")
    else:
        v = ("REJECT. Gold and EURUSD were luck. The honest reading is that the "
             "vol-scaling was fitted to them.")
    print(f"\n  VERDICT: {v}")

    # Correlation: seven markets sharing a USD leg are not seven independent tests.
    curves = {r["label"]: r["equity"].pct_change().fillna(0)
              for r in results if r["counts"]}
    if len(curves) > 1:
        c = pd.concat(curves, axis=1).corr()
        off = c.to_numpy()[np.triu_indices(len(c), k=1)]
        print(f"\n  mean pairwise correlation of strategy returns: "
              f"{np.nanmean(off):.3f}")
        print("  (pre-registered caveat: shared USD legs and correlated indices")
        print("   mean the effective number of independent tests is below "
              f"{len(curves)})")


def self_test() -> int:
    from synth import make_bars
    fails = []

    def check(n, c, d=""):
        print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"  {d}" if not c else ""))
        if not c:
            fails.append(n)

    a = make_bars(4000, seed=1)
    b = a.copy()
    mid = (b["high"] + b["low"]) / 2
    for col in ("open", "high", "low", "close"):
        b[col] = mid + (b[col] - mid) * 2.0

    ref = atr_pct(a)
    check("identical market gets the base stop", abs(scaled_stop(a, ref) - 2.7) < 0.05,
          f"{scaled_stop(a, ref):.3f}")
    check("2x volatility roughly doubles the stop", 4.6 < scaled_stop(b, ref) < 6.0,
          f"{scaled_stop(b, ref):.3f}")
    check("scoring set is the 7 never-tested markets",
          sum(1 for _, _, c in MARKETS if c) == 7)
    check("held markets excluded from scoring",
          {lab for _, lab, c in MARKETS if not c} == {"GOLD", "SILVER", "EURUSD"})

    print("\n" + "=" * 56)
    if fails:
        print(f"{len(fails)} FAILED: {', '.join(fails)}")
        return 1
    print("all checks passed")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--trials", type=int, default=1500)
    ap.add_argument("--capital", type=float, default=4000.0)
    ap.add_argument("--only", default=None, help="comma-separated labels, for resuming")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())
    if not args.run:
        raise SystemExit("pass --run (or --self-test)")

    if not os.path.exists(REFERENCE):
        raise SystemExit(f"reference {REFERENCE} not found")
    ref_atr = atr_pct(_normalise(_read_csv(REFERENCE)))
    print(f"reference volatility (gold, median ATR% of price): {100*ref_atr:.4f}%")

    wanted = {s.strip().upper() for s in args.only.split(",")} if args.only else None
    results, missing = [], []
    for path, label, counts in MARKETS:
        if wanted and label.upper() not in wanted:
            continue
        if not os.path.exists(path):
            missing.append(label)
            continue
        r = evaluate(path, ref_atr, args.trials, args.capital)
        r["label"], r["counts"] = label, counts
        results.append(r)
        print(f"  {label:<9} done  ({r['trades']} trades, "
              f"percentile {r['percentile']:.1f})")

    if missing:
        print(f"\nmissing files, dropped (NOT substituted, per pre-registration): "
              f"{', '.join(missing)}")
    if results:
        report(results)
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
        os.makedirs(out, exist_ok=True)
        pd.DataFrame([{k: v for k, v in r.items()
                       if k not in ("equity", "trades_df")} for r in results]
                     ).to_csv(os.path.join(out, "multi_market.csv"), index=False)
        print(f"\nwrote multi_market.csv to {out}")


if __name__ == "__main__":
    main()
