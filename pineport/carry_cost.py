#!/usr/bin/env python3
"""Price the cost of carry on a strategy that holds positions overnight.

Registration: PREREGISTRATION_SPX500_H4_CARRY.md

WHY THIS EXISTS

Every backtest in this tree charges the SPREAD and nothing else. That is right
for a strategy that is flat overnight and wrong for one that is not. The SPX500
H4 config holds a CFD position ~51% of the time for a median 3.5-5.3 days, and
its pre-2009 window earns only +1.32%/yr -- so financing is plausibly larger
than the spread there and has never been computed.

The precedent is gold 15m: Sharpe 0.86 became 2.93%/yr after ETF costs, and on
a CFD at rf+2.5% it was WORSE THAN CASH, break-even carry 4.35%. Standing rule
6 -- costs are the usual killer, price the vehicle early.

THE CHARGE, as OANDA publishes it for index CFDs

    long:   notional x (benchmark + markup) x days/365     debited
    short:  notional x (benchmark - markup) x days/365     credited

notional = position size x price. Accrual is per CALENDAR day, which carries
weekends automatically (the broker's "three days on Friday" convention).

    python carry_cost.py --results results/spx500usd_oanda_h4_H4_... \\
        --csv spx500usd_oanda_h4.csv

Reports the break-even markup per window -- the markup at which the window's
net return reaches zero -- against the 2.5% OANDA publishes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np                                   # noqa: E402
import pandas as pd                                  # noqa: E402

from broker import BrokerConfig                      # noqa: E402
from data import _normalise, _read_csv               # noqa: E402
from metrics import compute_metrics                  # noqa: E402
from strategy import Params, run_strategy            # noqa: E402

#: Registered windows, from PREREGISTRATION_SPX500_timeframes.md section 3.
WINDOWS = [("2005-2008", "2005-01-01", "2008-12-31"),
           ("2023-2026", "2023-01-01", "2026-08-14")]
MARKUPS = [1.0, 2.5, 4.0, 6.0]          # registered sweep; 2.5 is OANDA's
OANDA_MARKUP = 2.5
BASIS = 365.0


def load_benchmark(path: str, lag_days: int = 1) -> pd.Series:
    """Daily short rate in percent, forward-filled, lagged for publication.

    The lag is not cosmetic. A rate describing day D is published after D, so
    using it to charge a position on D is lookahead -- the subtle kind, because
    the series looks perfectly aligned. fetch_fred.py documents this and leaves
    the shift to load time; this is that shift.
    """
    df = pd.read_csv(path)
    dcol, vcol = df.columns[0], df.columns[1]
    df[dcol] = pd.to_datetime(df[dcol], errors="coerce", utc=True)
    s = (df.dropna(subset=[dcol])
           .set_index(dcol)[vcol]
           .apply(pd.to_numeric, errors="coerce")
           .dropna()
           .sort_index())
    s = s[~s.index.duplicated(keep="last")]
    # business-day lag, then daily grid so weekends inherit Friday's rate
    s.index = s.index + pd.Timedelta(days=lag_days)
    return s.resample("1D").ffill()


def load_policy(path: str) -> pd.Series:
    """USD monthly policy rate, as the registered cross-check benchmark."""
    df = pd.read_csv(path)
    df = df[df["currency"] == "USD"].copy()
    df["month"] = pd.to_datetime(df["month"], errors="coerce", utc=True)
    s = (df.dropna(subset=["month"]).set_index("month")["rate_pct"]
           .sort_index())
    s = s[~s.index.duplicated(keep="last")]
    return s.resample("1D").ffill()


def carry_for_trades(trades: pd.DataFrame, bench: pd.Series,
                     markup: float) -> pd.Series:
    """Financing cost per trade, in account currency.

    Positive = a cost to the strategy. Shorts come out negative (a credit)
    whenever benchmark > markup, which is the published behaviour.
    """
    out = np.zeros(len(trades))
    for i, t in enumerate(trades.itertuples()):
        ent, ext = t.entry_time, t.exit_time
        if pd.isna(ent) or pd.isna(ext):
            continue
        days = (ext - ent).total_seconds() / 86400.0
        if days <= 0:
            continue
        # average benchmark over the holding period, per calendar day
        seg = bench.loc[(bench.index >= ent.normalize())
                        & (bench.index <= ext.normalize())]
        rate = float(seg.mean()) if len(seg) else float(bench.asof(ent) or 0.0)
        if not np.isfinite(rate):
            rate = 0.0
        notional = abs(t.qty) * t.entry_price
        eff = (rate + markup) if t.direction > 0 else (rate - markup)
        out[i] = notional * (eff / 100.0) * (days / BASIS)
    return pd.Series(out, index=trades.index)


def rebuild_equity(equity: pd.Series, trades: pd.DataFrame,
                   carry: pd.Series, start_equity: float) -> pd.Series:
    """Subtract each trade's financing at its exit, and compound from there.

    Applying carry at exit rather than daily slightly flatters the drawdown
    path, but the terminal value and the per-trade accounting are exact, and
    those are what the kill conditions are written on.
    """
    adj = pd.Series(0.0, index=equity.index)
    for t, c in zip(trades.itertuples(), carry):
        ts = t.exit_time
        if pd.isna(ts):
            continue
        pos = adj.index.searchsorted(ts)
        if pos >= len(adj):
            pos = len(adj) - 1
        adj.iloc[pos] += c
    return equity - adj.cumsum()


def breakeven_markup(trades: pd.DataFrame, equity: pd.Series,
                     bench: pd.Series, start_equity: float,
                     hi: float = 40.0, tol: float = 0.01) -> float:
    """Markup at which the window's net return hits zero. 0.0 if already
    negative with no financing at all."""
    def net(m: float) -> float:
        c = carry_for_trades(trades, bench, m)
        return rebuild_equity(equity, trades, c, start_equity).iloc[-1] / start_equity - 1.0

    if net(0.0) <= 0:
        return 0.0
    if net(hi) > 0:
        return hi
    lo = 0.0
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if net(mid) > 0:
            lo = mid
        else:
            hi = mid
    return lo


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--benchmark", default="../fastbot/data/DGS3MO.csv",
                    help="daily short rate, 2 columns: date, percent")
    ap.add_argument("--policy", default="../fastbot/data/policy_rates.csv",
                    help="registered cross-check benchmark")
    ap.add_argument("--slippage", type=float, default=0.25)
    ap.add_argument("--equity", type=float, default=100000.0)
    a = ap.parse_args()

    cfg = json.load(open(os.path.join(a.results, "config.json")))
    p = Params(**{k: v for k, v in cfg.items()
                  if k in Params.__dataclass_fields__})
    full = _normalise(_read_csv(a.csv))

    # Label from the filename, not hardcoded. A first version always printed
    # "DGS3MO" whatever --benchmark pointed at, which mislabels every number in
    # a cost table -- the sort of thing that gets misquoted three weeks later.
    bname = os.path.splitext(os.path.basename(a.benchmark))[0].upper()
    benches = {bname: load_benchmark(a.benchmark)}
    if os.path.exists(a.policy):
        benches["policy"] = load_policy(a.policy)

    print(f"\n{'='*86}")
    print("COST OF CARRY -- PREREGISTRATION_SPX500_H4_CARRY.md")
    print(f"  config {a.results}")
    print(f"  charge: long notional x (bench + markup) x days/365, "
          f"short credited at (bench - markup)")
    for k, s in benches.items():
        print(f"  benchmark {k:<8} {s.index[0].date()} -> {s.index[-1].date()}  "
              f"mean {s.mean():.2f}%")
    print(f"{'='*86}")

    results = {}
    for name, s, e in WINDOWS:
        d = full[s:e]
        r = run_strategy(d, p, BrokerConfig(a.equity, 1.0,
                                            slippage_points=a.slippage))
        t = r.trades
        yrs = (d.index[-1] - d.index[0]).days / 365.25
        gross_net = r.equity.iloc[-1] / a.equity - 1.0

        print(f"\n--- {name} --- {len(t)} trades, {yrs:.1f}y, "
              f"spread-only net {100*gross_net:+.1f}% "
              f"({100*((1+gross_net)**(1/yrs)-1):+.2f}%/yr)")

        for bname, bench in benches.items():
            seg = bench.loc[(bench.index >= d.index[0]) & (bench.index <= d.index[-1])]
            print(f"\n  benchmark {bname} (mean {seg.mean():.2f}% over the window)")
            print(f"    {'markup':>8}{'carry $':>11}{'carry %/yr':>12}"
                  f"{'net %':>9}{'net %/yr':>10}{'Sharpe':>8}")
            print("    " + "-" * 58)
            for m in MARKUPS:
                c = carry_for_trades(t, bench, m)
                eq2 = rebuild_equity(r.equity, t, c, a.equity)
                n2 = eq2.iloc[-1] / a.equity - 1.0
                m2 = compute_metrics(eq2, t, a.equity)
                flag = "  <-- OANDA" if m == OANDA_MARKUP else ""
                print(f"    {m:>8.1f}{c.sum():>11,.0f}"
                      f"{100*c.sum()/a.equity/yrs:>11.2f}%"
                      f"{100*n2:>9.1f}{100*((1+n2)**(1/yrs)-1):>9.2f}%"
                      f"{m2['sharpe']:>8.2f}{flag}")
            be = breakeven_markup(t, r.equity, bench, a.equity)
            print(f"    break-even markup: {be:.2f} points"
                  f"   (OANDA charges {OANDA_MARKUP})")
            # the figures conditions 2 and 3 are written on, at OANDA's markup
            c_o = carry_for_trades(t, bench, OANDA_MARKUP)
            eq_o = rebuild_equity(r.equity, t, c_o, a.equity)
            n_o = eq_o.iloc[-1] / a.equity - 1.0
            results[(name, bname)] = {
                "be": be, "yrs": yrs,
                "net_at_oanda": n_o,
                "cagr_at_oanda": (1 + n_o) ** (1 / yrs) - 1,
                "carry_at_oanda": c_o.sum(),
                "bench_mean": float(seg.mean()),
            }
        # spread cost, for prediction 4: is carry the larger charge?
        spread_cost = len(t) * 2 * a.slippage * float(t["qty"].median())
        results[(name, "_spread")] = {"spread_cost": spread_cost}
        print(f"\n  spread cost for comparison: {len(t)} trades x 2 fills x "
              f"{a.slippage} pts x {t['qty'].median():.0f} units = "
              f"${spread_cost:,.0f}")

    # ---- kill conditions, registration section 4 ---------------------------
    print(f"\n{'='*86}")
    print(f"{'KILL CONDITIONS (registration section 4)':<70}{'verdict':>12}")
    print("-" * 86)
    fails: list[str] = []

    def line(n: int, text: str, failed: bool, note: str = "") -> None:
        if failed:
            fails.append(str(n))
        print(f"  {n}. {text:<66}{'FAIL' if failed else 'pass':>12}")
        if note:
            print(f"      {note}")

    # condition 1 -- break-even markup >= 2.5 on both windows, both benchmarks
    bad, disagree = [], []
    for name, _, _ in WINDOWS:
        verdicts = {b: results[(name, b)]["be"] >= OANDA_MARKUP
                    for b in benches}
        if len(set(verdicts.values())) > 1:
            disagree.append(name)
        elif not all(verdicts.values()):
            bad.append(f"{name} be="
                       + "/".join(f"{results[(name,b)]['be']:.2f}" for b in benches))
    line(1, f"break-even markup >= {OANDA_MARKUP} points on both windows",
         bool(bad), "; ".join(bad))
    if disagree:
        print(f"      INCONCLUSIVE on {', '.join(disagree)} -- the two benchmarks "
              f"disagree, so per the registration this is not resolved by picking one")

    # condition 2 -- 2005-2008 must not go negative at OANDA markup
    neg = [b for b in benches
           if results[("2005-2008", b)]["net_at_oanda"] <= 0]
    line(2, f"2005-2008 still positive at a {OANDA_MARKUP}-point markup", bool(neg),
         "; ".join(f"{b}: {100*results[('2005-2008',b)]['net_at_oanda']:+.1f}%"
                   for b in benches))

    # condition 3 -- post-carry return >= 2.0%/yr on BOTH windows
    FLOOR = 0.02
    thin = []
    for name, _, _ in WINDOWS:
        for b in benches:
            if results[(name, b)]["cagr_at_oanda"] < FLOOR:
                thin.append(f"{name}/{b} = "
                            f"{100*results[(name,b)]['cagr_at_oanda']:+.2f}%/yr")
    line(3, "post-carry return >= 2.0%/yr on both windows", bool(thin),
         "; ".join(thin))

    # context the conditions do not capture: the risk-free rate itself
    print()
    for name, _, _ in WINDOWS:
        b = list(benches)[0]
        rr = results[(name, b)]
        print(f"  {name}: post-carry {100*rr['cagr_at_oanda']:+.2f}%/yr vs "
              f"risk-free {rr['bench_mean']:.2f}%/yr over the same window "
              f"-> {'BELOW CASH' if rr['cagr_at_oanda']*100 < rr['bench_mean'] else 'above cash'}")

    # prediction 4 -- is carry a larger charge than spread?
    print()
    for name, _, _ in WINDOWS:
        b = list(benches)[0]
        sc = results[(name, "_spread")]["spread_cost"]
        cc = results[(name, b)]["carry_at_oanda"]
        print(f"  {name}: carry ${cc:,.0f} vs spread ${sc:,.0f}"
              f"  -> carry is {cc/sc:.1f}x the spread charge"
              if sc else f"  {name}: no spread cost")

    print(f"\n{'='*86}")
    print(("CARRY KILLS IT -- conditions " + ", ".join(fails) + " fired.")
          if fails else "Survives carry at the published markup.")
    print("Either way the timeframes registration's verdict on H4 is unchanged:")
    print("it failed conditions 1 and 4 there and remains closed.")
    print(f"{'='*86}\n")


if __name__ == "__main__":
    main()
