#!/usr/bin/env python3
"""Test the pre-registered gold-in-EUR confirmation hypothesis.

Reads PREREGISTRATION.md's fixed design:

    H0  current logic, macro filter on XAUUSD only        (control)
    H1  macro filter computed on XAUEUR instead           (swap)
    H2  require macro bullish on BOTH series              (intersection)

Nothing is tuned. `bullish_sma` stays at 20 for both series. Every window is
out-of-sample because the configurations are fixed in advance, so this is a
paired comparison across six windows rather than a search.

Success criterion, fixed before the data was fetched:
    >= 5/6 windows beating H0  -> real improvement
       4/6                     -> NOT evidence (chance produces this here)
    <= 3/6                     -> reject

    python cross_market_test.py --csv xauusd_1h.csv --aux xaueur_1h.csv
    python cross_market_test.py --csv xauusd_1h.csv --derive-from eurusd_1h.csv
    python cross_market_test.py --self-test
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

from broker import BrokerConfig                         # noqa: E402
from data import _normalise, _read_csv                  # noqa: E402
from metrics import compute_metrics                     # noqa: E402
from strategy import Params, run_strategy               # noqa: E402
from optimise import make_folds                         # noqa: E402

BASE = dict(fix_keltner_range=True, fix_long_stop_ratchet=True, allow_shorts=False)

HYPOTHESES = {
    "H0 control (XAUUSD macro)": dict(cross_market_mode="off"),
    "H1 swap (XAUEUR macro)":    dict(cross_market_mode="replace"),
    "H2 both (USD and EUR)":     dict(cross_market_mode="both"),
}

#: Test 2 -- real-yield regime filter. Same structure, different driver.
RATE_HYPOTHESES = {
    "H0 control (XAUUSD macro)":  dict(rate_filter_mode="off"),
    "H1 swap (real yield)":       dict(rate_filter_mode="replace"),
    "H2 both (price and yield)":  dict(rate_filter_mode="both"),
}


def derive_xaueur(xauusd: pd.DataFrame, eurusd: pd.DataFrame,
                  min_overlap: int = 1000) -> pd.DataFrame:
    """XAUEUR = XAUUSD / EURUSD, on the intersection of both bar sets.

    Only bars present in both feeds are used -- forward-filling one series onto
    the other's timestamps would invent prices that never traded.
    """
    common = xauusd.index.intersection(eurusd.index)
    if len(common) < min_overlap:
        raise SystemExit(f"only {len(common)} overlapping bars "
                         f"(need {min_overlap}); check the feeds")
    a, b = xauusd.loc[common], eurusd.loc[common]
    out = pd.DataFrame(index=common)
    out["open"] = a["open"] / b["open"]
    out["close"] = a["close"] / b["close"]
    # A ratio's extremes are not the ratio of the extremes; bound them safely.
    hi = pd.concat([a["high"] / b["low"], a["high"] / b["high"],
                    a["low"] / b["low"]], axis=1).max(axis=1)
    lo = pd.concat([a["low"] / b["high"], a["low"] / b["low"],
                    a["high"] / b["high"]], axis=1).min(axis=1)
    out["high"] = pd.concat([hi, out["open"], out["close"]], axis=1).max(axis=1)
    out["low"] = pd.concat([lo, out["open"], out["close"]], axis=1).min(axis=1)
    out["volume"] = a["volume"]
    return out


def evaluate_window(df, aux, params, cfg, test_start, rates=None):
    res = run_strategy(df, params, cfg, aux=aux, rates=rates)
    eq = res.equity[res.equity.index >= test_start]
    if len(eq) < 10:
        return {"calmar": np.nan, "trades": 0, "cagr_pct": np.nan,
                "max_drawdown_pct": np.nan, "sharpe": np.nan}
    eq = eq / eq.iloc[0] * cfg.initial_capital
    tr = res.trades
    if not tr.empty:
        tr = tr[pd.to_datetime(tr["entry_time"], utc=True) >= test_start]
    return compute_metrics(eq, tr, cfg.initial_capital)


def usable_folds(df: pd.DataFrame, aux: pd.DataFrame, folds: list,
                 min_coverage: float = 0.98) -> tuple[list, list]:
    """Keep only folds whose TEST window is fully covered by the auxiliary series.

    Where the auxiliary series has no data the filter evaluates to False, which
    blocks entries -- for a reason that has nothing to do with the hypothesis.
    Scoring such a window would make H1/H2 look worse purely because the data
    ran out, so those folds are dropped and reported rather than silently
    included.

    Note this is why a short XAUEUR history is not fatal: the train portion of
    each fold only warms up indicators on the PRIMARY series, so the auxiliary
    feed is needed across test windows only.
    """
    keep, dropped = [], []
    for a, b, c in folds:
        want = df.loc[b:c].index
        have = want.intersection(aux.index)
        cov = len(have) / max(len(want), 1)
        (keep if cov >= min_coverage else dropped).append(((a, b, c), cov))
    return [f for f, _ in keep], dropped


def run(df: pd.DataFrame, aux: pd.DataFrame, cfg: BrokerConfig,
        hypotheses: dict | None = None, rates=None) -> pd.DataFrame:
    hypotheses = hypotheses or HYPOTHESES
    folds = make_folds(df, 6, 6.0, 2.5)
    folds, dropped = (usable_folds(df, aux, folds) if aux is not None
                      else (folds, []))
    if dropped:
        print(f"\n{len(dropped)} fold(s) dropped -- auxiliary series does not "
              f"cover the test window:")
        for (a, b, c), cov in dropped:
            print(f"  {b:%Y-%m}..{c:%Y-%m}   coverage {100*cov:5.1f}%")
        print("  (these are excluded rather than scored, because missing aux")
        print("   data blocks entries for a reason unrelated to the hypothesis)")
    if not folds:
        raise SystemExit(
            "\nNo fold has full auxiliary coverage. Fetch XAUEUR from at least "
            "2011-06\nonward -- the test windows begin 2012-01.")
    if len(folds) < 5:
        print(f"\n  NOTE: only {len(folds)} usable folds. The pre-registered "
              f"criterion was\n  >=5/6; with fewer windows the bar should be "
              f"read as 'wins nearly all',\n  and the result is weaker evidence "
              f"either way.")
    rows = []
    print(f"\n{'test window':<22}" + "".join(f"{k[:22]:>24}" for k in hypotheses))
    print("-" * (22 + 24 * len(hypotheses)))
    for a, b, c in folds:
        line = f"{b:%Y-%m}..{c:%Y-%m}".ljust(22)
        row = {"window": f"{b:%Y-%m}..{c:%Y-%m}"}
        for name, kw in hypotheses.items():
            m = evaluate_window(df[a:c], aux, Params(**BASE, **kw), cfg, b,
                                rates=rates)
            row[name] = m["calmar"]
            row[name + "_trades"] = m["trades"]
            v = m["calmar"]
            line += (f"{v:>17.3f}({m['trades']:>2}t)" if np.isfinite(v)
                     else f"{'n/a':>24}")
        rows.append(row)
        print(line)
    return pd.DataFrame(rows)


def verdict(res: pd.DataFrame, hypotheses: dict | None = None) -> None:
    hypotheses = hypotheses or HYPOTHESES
    ctrl_name = list(hypotheses)[0]
    ctrl = res[ctrl_name].to_numpy(float)
    print("-" * (22 + 24 * len(hypotheses)))
    print(f"\n{'hypothesis':<28}{'mean':>9}{'median':>9}{'avg trades':>12}"
          f"{'beats H0':>11}")
    for name in hypotheses:
        v = res[name].to_numpy(float)
        ok = ~np.isnan(v) & ~np.isnan(ctrl)
        wins = int((v[ok] > ctrl[ok]).sum())
        n_tr = res[name + "_trades"].mean()
        tag = "" if name == ctrl_name else f"{wins}/{int(ok.sum())}"
        print(f"{name:<28}{np.nanmean(v):>9.3f}{np.nanmedian(v):>9.3f}"
              f"{n_tr:>12.1f}{tag:>11}")

    print("\nAgainst the pre-registered criterion")
    print("-" * 62)
    for name in list(hypotheses)[1:]:
        v = res[name].to_numpy(float)
        ok = ~np.isnan(v) & ~np.isnan(ctrl)
        wins, n = int((v[ok] > ctrl[ok]).sum()), int(ok.sum())
        thin = res[name + "_trades"].mean() < 10
        if wins >= 5:
            note = "REAL IMPROVEMENT (>=5/6, clears the bar)"
        elif wins == 4:
            note = "NOT EVIDENCE (4/6 is what chance produces here)"
        else:
            note = "REJECTED (<=3/6)"
        print(f"  {name:<28} {wins}/{n}  {note}")
        if thin:
            print(f"    caveat: averages {res[name+'_trades'].mean():.1f} trades "
                  f"per window -- below ~10 the ratios are noise, so treat this "
                  f"as inconclusive rather than negative")


def self_test() -> int:
    """Prove the plumbing on synthetic data, before any real aux series exists."""
    from synth import make_bars
    fails = []

    def check(n, c, d=""):
        print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"  {d}" if not c else ""))
        if not c:
            fails.append(n)

    print("cross-market filter plumbing")
    df = make_bars(6000, seed=3)
    cfg = BrokerConfig(4000, 1)

    # An aux series identical to the primary must reproduce the control exactly.
    r0 = run_strategy(df, Params(**BASE, cross_market_mode="off"), cfg)
    r1 = run_strategy(df, Params(**BASE, cross_market_mode="replace"), cfg, aux=df)
    r2 = run_strategy(df, Params(**BASE, cross_market_mode="both"), cfg, aux=df)
    check("identical aux reproduces control (replace)", len(r0.trades) == len(r1.trades),
          f"{len(r0.trades)} vs {len(r1.trades)}")
    check("identical aux reproduces control (both)", len(r0.trades) == len(r2.trades),
          f"{len(r0.trades)} vs {len(r2.trades)}")

    # An always-falling aux must block every trade under both modes.
    bear = df.copy()
    falling = np.linspace(3000, 1000, len(df))
    for c in ("open", "high", "low", "close"):
        bear[c] = falling
    rb = run_strategy(df, Params(**BASE, cross_market_mode="replace"), cfg, aux=bear)
    check("falling aux blocks all entries", len(rb.trades) == 0, f"{len(rb.trades)}")

    rboth = run_strategy(df, Params(**BASE, cross_market_mode="both"), cfg, aux=bear)
    check("'both' is a subset of control", len(rboth.trades) <= len(r0.trades))

    check("missing aux raises rather than silently passing",
          _raises(lambda: run_strategy(df, Params(**BASE, cross_market_mode="replace"), cfg)))
    check("unknown mode rejected",
          _raises(lambda: run_strategy(df, Params(**BASE, cross_market_mode="nonsense"), cfg, aux=df)))

    print("\nderived XAUEUR arithmetic")
    idx = pd.date_range("2024-01-01", periods=200, freq="1h", tz="UTC")
    xau = pd.DataFrame({"open": 2000.0, "high": 2010.0, "low": 1990.0,
                        "close": 2005.0, "volume": 1.0}, index=idx)
    eur = pd.DataFrame({"open": 1.10, "high": 1.11, "low": 1.09,
                        "close": 1.105, "volume": 1.0}, index=idx)
    d = derive_xaueur(xau, eur, min_overlap=100)
    check("close ratio correct", abs(d["close"].iloc[0] - 2005.0 / 1.105) < 1e-9)
    check("high >= max(open, close)",
          bool((d["high"] >= d[["open", "close"]].max(axis=1) - 1e-9).all()))
    check("low <= min(open, close)",
          bool((d["low"] <= d[["open", "close"]].min(axis=1) + 1e-9).all()))
    check("high >= low", bool((d["high"] >= d["low"]).all()))

    print("\n" + "=" * 56)
    if fails:
        print(f"{len(fails)} FAILED: {', '.join(fails)}")
        return 1
    print("all checks passed")
    return 0


def _raises(fn) -> bool:
    try:
        fn()
        return False
    except Exception:
        return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", help="XAUUSD hourly csv")
    ap.add_argument("--aux", help="XAUEUR hourly csv")
    ap.add_argument("--derive-from", help="EURUSD csv; XAUEUR computed as XAUUSD/EURUSD")
    ap.add_argument("--rates", help="FRED csv from fetch_fred.py (runs TEST 2)")
    ap.add_argument("--rate-lag-days", type=int, default=1,
                    help="publication lag applied to the FRED series")
    ap.add_argument("--capital", type=float, default=4000.0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())

    # ---- Test 2: real-yield regime filter --------------------------------
    if args.rates:
        if not args.csv:
            raise SystemExit("--rates also needs --csv")
        from fetch_fred import load_daily_series
        df = _normalise(_read_csv(args.csv))
        rates = load_daily_series(args.rates, lag_days=args.rate_lag_days)
        print(f"primary : {len(df):,} bars  {df.index[0]:%Y-%m-%d} -> "
              f"{df.index[-1]:%Y-%m-%d}")
        print(f"rates   : {len(rates):,} obs   {rates.index[0]:%Y-%m-%d} -> "
              f"{rates.index[-1]:%Y-%m-%d}   "
              f"range {rates.min():.3f} to {rates.max():.3f}")
        print(f"  publication lag applied: {args.rate_lag_days} business day(s)")
        if rates.index[0] > df.index[0]:
            print(f"  NOTE: rates start after the price series; bars before "
                  f"{rates.index[0]:%Y-%m-%d}\n  evaluate the filter as False.")
        cfg = BrokerConfig(initial_capital=args.capital, point_value=1.0)
        res = run(df, None, cfg, hypotheses=RATE_HYPOTHESES, rates=rates)
        verdict(res, RATE_HYPOTHESES)

        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
        os.makedirs(out, exist_ok=True)
        res.to_csv(os.path.join(out, "rate_filter_test.csv"), index=False)
        print(f"\nwrote rate_filter_test.csv to {out}")
        return

    if not args.csv or not (args.aux or args.derive_from):
        raise SystemExit("need --csv and one of --aux / --derive-from / --rates "
                         "(or --self-test)")

    df = _normalise(_read_csv(args.csv))
    if args.aux:
        aux = _normalise(_read_csv(args.aux))
        label = os.path.basename(args.aux)
    else:
        aux = derive_xaueur(df, _normalise(_read_csv(args.derive_from)))
        label = f"derived from {os.path.basename(args.derive_from)}"

    print(f"primary : {len(df):,} bars  {df.index[0]:%Y-%m-%d} -> {df.index[-1]:%Y-%m-%d}")
    print(f"auxiliary ({label}): {len(aux):,} bars  "
          f"{aux.index[0]:%Y-%m-%d} -> {aux.index[-1]:%Y-%m-%d}")
    overlap = df.index.intersection(aux.index)
    print(f"overlapping bars: {len(overlap):,} "
          f"({100*len(overlap)/len(df):.1f}% of the primary series)")
    print("  (full overlap is NOT required -- folds whose test window the")
    print("   auxiliary series does not cover are dropped automatically)")

    cfg = BrokerConfig(initial_capital=args.capital, point_value=1.0)
    res = run(df, aux, cfg)
    verdict(res)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(out, exist_ok=True)
    res.to_csv(os.path.join(out, "cross_market_test.csv"), index=False)
    print(f"\nwrote cross_market_test.csv to {out}")


if __name__ == "__main__":
    main()
