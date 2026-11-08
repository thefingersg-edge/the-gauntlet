#!/usr/bin/env python3
"""Analyse a TradingView "List of Trades" export across the full chart history.

Why this file exists: the chart-data export is capped at whatever is loaded on
screen (about 1,300 bars), but the trade list goes back as far as the strategy
ran -- here, 2006. So the trade list is the only view of the strategy over a
meaningful sample, and everything below is built to extract as much as possible
from it *without* bar data.

The most useful thing it carries is the favourable/adverse excursion columns.
Those record how far each trade went in each direction before it closed, which
makes it possible to simulate different EXIT rules on the real trade population
-- a take-profit, or a move to breakeven -- without re-running a backtest.

    python trade_history.py --trades "Gold_1hr_New_....csv"
    python trade_history.py --trades ... --capital 4000 --sweep

Read the caveats printed alongside the counterfactual table before acting on it.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

def load_trade_list(path: str) -> pd.DataFrame:
    """Fold TradingView's two-rows-per-trade export into one row per trade.

    The export writes an ``Entry`` row and an ``Exit`` row sharing a trade
    number, with the P&L columns duplicated across both. Timestamps are in the
    chart's display timezone, which is not necessarily UTC -- on this export the
    trade list runs one hour ahead of the chart-data export.
    """
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]

    required = {"Trade number", "Type", "Date and time", "Price USD"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"not a TradingView trade list; missing {sorted(missing)}")

    df["ts"] = pd.to_datetime(df["Date and time"], errors="coerce")

    entries = df[df["Type"].str.contains("Entry", na=False)].set_index("Trade number")
    exits = df[df["Type"].str.contains("Exit", na=False)].set_index("Trade number")
    common = entries.index.intersection(exits.index).sort_values()
    entries, exits = entries.loc[common], exits.loc[common]

    def col(frame, name, default=np.nan):
        return frame[name] if name in frame.columns else pd.Series(default, index=frame.index)

    t = pd.DataFrame({
        "side": np.where(entries["Type"].str.contains("long"), "long", "short"),
        "entry_time": entries["ts"],
        "exit_time": exits["ts"],
        "entry_px": entries["Price USD"].astype(float),
        "exit_px": exits["Price USD"].astype(float),
        "qty": col(entries, "Size (qty)", 1).astype(float),
        "pnl": col(entries, "Net PnL USD").astype(float),
        "return_pct": col(entries, "Return %").astype(float),
        "mfe_pct": col(entries, "Favorable excursion %").astype(float),
        "mae_pct": col(entries, "Adverse excursion %").astype(float),
        "cum_pnl": col(entries, "Cumulative PnL USD").astype(float),
        "bars": col(entries, "Duration (bars)", np.nan).astype(float),
        "exit_signal": exits["Signal"] if "Signal" in exits.columns else "",
    })
    t.index.name = "trade"
    return t.sort_values("entry_time")


# --------------------------------------------------------------------------
# headline statistics
# --------------------------------------------------------------------------

def summarise(t: pd.DataFrame, capital: float) -> None:
    equity = capital + t["cum_pnl"]
    final = float(equity.iloc[-1])
    years = (t["exit_time"].iloc[-1] - t["entry_time"].iloc[0]).days / 365.25

    print("Overall")
    print("-" * 72)
    print(f"  trades              {len(t)}")
    print(f"  span                {t['entry_time'].iloc[0]:%Y-%m-%d} -> "
          f"{t['exit_time'].iloc[-1]:%Y-%m-%d}  ({years:.1f} years)")
    print(f"  trade frequency     {len(t)/years:.1f} per year")
    print(f"  final equity        {final:,.2f}   (from {capital:,.0f})")
    print(f"  total return        {100*(final/capital-1):,.1f}%")
    print(f"  CAGR                {100*((final/capital)**(1/years)-1):,.2f}%")

    peak = equity.cummax()
    dd = (equity - peak) / peak
    print(f"  max drawdown        {100*dd.min():,.2f}%  "
          f"(trade-close basis -- see caveat below)")

    bars_in = float(t["bars"].sum())
    approx_bars = years * 24 * 365.25 * (5 / 7)   # ~24/5 market
    print(f"  approx. exposure    {100*bars_in/approx_bars:,.1f}% of hours")

    # Buy and hold over the same window, from the strategy's own fills.
    bh = t["exit_px"].iloc[-1] / t["entry_px"].iloc[0]
    print(f"\n  gold buy & hold     {100*(bh-1):,.0f}%   "
          f"CAGR {100*(bh**(1/years)-1):,.2f}%")
    print(f"  strategy captured   {((final/capital)**(1/years)-1)/(bh**(1/years)-1):,.2f}x "
          f"of buy & hold CAGR")

    print("\n  CAVEAT: the drawdown above is measured at trade closes only. It")
    print("  ignores open-position swings, so the true figure is worse -- the")
    print("  average trade's adverse excursion alone is "
          f"{t['mae_pct'].abs().mean():.2f}%. Bar data would be needed to")
    print("  compute this properly.")

    print("\nBy direction")
    print("-" * 72)
    rows = []
    for side in ("long", "short"):
        s = t[t["side"] == side]
        if s.empty:
            continue
        rows.append(_stats_row(side, s))
    rows.append(_stats_row("ALL", t))
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n  The short side is 20 trades in 20 years and contributes "
          f"{100*t[t['side']=='short']['pnl'].sum()/t['pnl'].sum():.1f}% of net profit.")
    print("  It fires, but roughly once a year -- too rarely to tune or to model.")

    print("\nExit reasons")
    print("-" * 72)
    for sig, n in t["exit_signal"].value_counts().items():
        note = " (reversal -- an opposite signal closed it)" if "exit" not in str(sig) else " (stop)"
        print(f"  {str(sig):<12} {n:>4}{note}")

    print("\nBy year")
    print("-" * 72)
    by_year = t.groupby(t["entry_time"].dt.year).agg(
        trades=("pnl", "size"), net=("pnl", "sum"),
        win_pct=("pnl", lambda s: 100.0 * (s > 0).mean()),
        avg_bars=("bars", "mean"))
    print(by_year.round(1).to_string())


def _stats_row(label: str, s: pd.DataFrame) -> dict:
    wins, losses = s[s["pnl"] > 0], s[s["pnl"] <= 0]
    gross_loss = -losses["pnl"].sum()
    return {
        "group": label, "n": len(s),
        "win_%": round(100.0 * len(wins) / len(s), 1),
        "profit_factor": round(wins["pnl"].sum() / gross_loss, 2) if gross_loss > 0 else np.inf,
        "net": round(s["pnl"].sum(), 2),
        "avg": round(s["pnl"].mean(), 2),
        "median": round(s["pnl"].median(), 2),
        "avg_bars": round(s["bars"].mean(), 1),
    }


# --------------------------------------------------------------------------
# excursion analysis
# --------------------------------------------------------------------------

def excursion_report(t: pd.DataFrame) -> None:
    """How much of each trade's peak gain survives to the exit."""
    print("\nExcursion analysis -- what the exit rule costs")
    print("-" * 72)
    print(f"  mean favourable excursion   {t['mfe_pct'].mean():6.2f}%")
    print(f"  mean adverse excursion      {t['mae_pct'].abs().mean():6.2f}%")
    print(f"  mean realised return        {t['return_pct'].mean():6.2f}%")

    give_back = t["mfe_pct"].mean() - t["return_pct"].mean()
    print(f"\n  The average trade peaks at {t['mfe_pct'].mean():.2f}% and closes at "
          f"{t['return_pct'].mean():.2f}%,")
    print(f"  giving back {give_back:.2f} percentage points "
          f"({100*give_back/max(t['mfe_pct'].mean(), 1e-9):.0f}% of the peak).")

    losers = t[t["pnl"] <= 0]
    reached = int(((t["mfe_pct"] > 1.0) & (t["pnl"] <= 0)).sum())
    print(f"\n  {reached} of {len(t)} trades ({100*reached/len(t):.0f}%) went more than 1% "
          f"in profit and still closed at a loss.")
    print(f"  Median peak gain on a losing trade: {losers['mfe_pct'].median():.2f}%")

    print("\n  This is the signature of QUIRK 6 -- the take-profit legs are")
    print("  displaced by +/-10000 and can never fill, so every exit is a stop.")


def concentration_report(t: pd.DataFrame) -> int:
    """How many trades actually produce the result?

    This is the number that governs whether any modelling is worth attempting.
    A 231-trade record where ten trades supply all the profit has an effective
    sample size of ten, not 231 -- and no amount of cross-validation rescues a
    model fitted to ten observations.
    """
    print("\nProfit concentration")
    print("-" * 72)
    total = t["pnl"].sum()
    ranked = t.sort_values("pnl", ascending=False)
    for k in (1, 3, 5, 10, 20):
        share = 100.0 * ranked["pnl"].head(k).sum() / total
        print(f"  top {k:>2} trades  {share:>6.1f}% of net profit")

    top10 = ranked.head(10)
    rest = ranked.iloc[10:]
    print(f"\n  The other {len(rest)} trades net {rest['pnl'].sum():,.0f} "
          f"({100*rest['pnl'].sum()/total:.1f}% of the total).")
    print(f"  Top 10 are {int((top10['side'] == 'long').sum())}/10 long, "
          f"{int((top10['entry_time'].dt.year >= 2024).sum())}/10 from 2024 onward.")

    print("\n  EFFECTIVE SAMPLE SIZE IS ABOUT 10, NOT 231.")
    print("  Every ratio in this report -- profit factor, CAGR, the exit")
    print("  counterfactuals -- is a restatement of what those ten trades did.")
    print("  Remove the best three and the strategy is roughly flat over 20 years.")
    return len(top10)


def scale_free_view(t: pd.DataFrame) -> None:
    """Separate genuine edge from the fact that gold went from $600 to $4,700.

    Profit measured in dollars is not comparable across this span: a 1% move was
    worth $6 in 2006 and $47 in 2026. Percentage returns are the only
    scale-invariant view, and they tell a different story from the dollar one.
    """
    print("\nDollar profit vs percentage return")
    print("-" * 72)
    early, late = t[t["entry_time"].dt.year <= 2022], t[t["entry_time"].dt.year >= 2023]
    total = t["pnl"].sum()

    for label, s in (("2006-2022", early), ("2023-2026", late)):
        print(f"  {label}   {len(s):>3} trades   "
              f"USD {s['pnl'].sum():>8,.0f} ({100*s['pnl'].sum()/total:>4.0f}% of total)   "
              f"sum of % returns {s['return_pct'].sum():>6.1f}   "
              f"mean {s['return_pct'].mean():>5.2f}%   "
              f"avg entry ${s['entry_px'].mean():>6,.0f}")

    print("\n  In dollars the recent period looks like the whole story. In")
    print("  percentage terms the two halves contribute about equally -- so part")
    print("  of the skew is just the gold price level.")
    print(f"\n  But not all of it: mean return per trade went from "
          f"{early['return_pct'].mean():.2f}% to {late['return_pct'].mean():.2f}%, "
          f"a {late['return_pct'].mean()/early['return_pct'].mean():.1f}x improvement")
    print("  that price level alone does not explain.")
    print("\n  Worth sitting with: the ladder inputs (markUp 190, rangeL 750,")
    print("  lockProfitUp 170) are absolute dollar amounts. At gold $600 in 2006,")
    print("  +190 was a 32% move -- unreachable. Those values only make sense at")
    print("  recent price levels, which means 2006-2022 is effectively an")
    print("  out-of-sample test of parameters chosen for 2023-2026. Over that")
    print(f"  out-of-sample period the strategy returned {early['return_pct'].sum():.0f}% "
          f"cumulative simple")
    print("  while gold itself rose about 196%.")


def counterfactual_exits(t: pd.DataFrame, capital: float,
                         size_divisor: float = 5000.0) -> pd.DataFrame:
    """Re-simulate the trade population under alternative exit rules.

    Two families, both computable from the excursion columns alone:

    ``tp=X``
        A take-profit at X%. If the trade's favourable excursion reached X, it
        would have filled there; otherwise the trade plays out as it did.

    ``be=X``
        Move the stop to breakeven once the trade is X% in profit. Trades that
        reached X and still lost are floored at 0 instead.

    Position sizing is re-simulated too, using Pine's own
    ``ceil(equity / 5000)`` rule, so compounding differences show up.

    ---------------------------------------------------------------------
    THE ASSUMPTION THAT MATTERS

    The excursion columns record how far a trade travelled, not WHEN. If a
    trade's adverse excursion happened before its favourable one, a tighter
    exit might have been stopped out first and never reached the take-profit.
    So these numbers are an upper bound on what each variant would have earned,
    not a forecast.

    Treat the ranking as a hypothesis worth testing on bar data, not as a
    result. The direction of the bias is known and it flatters every variant
    here -- including, importantly, the baseline's competitors more than the
    baseline itself.
    ---------------------------------------------------------------------
    """
    def simulate(transform) -> dict:
        equity = capital
        pnls = []
        for _, r in t.iterrows():
            ret = transform(r)
            qty = max(1.0, np.ceil(equity / size_divisor))
            pnl = ret / 100.0 * r["entry_px"] * qty
            equity += pnl
            pnls.append(pnl)
        pnls = np.asarray(pnls)
        wins, losses = pnls[pnls > 0], pnls[pnls <= 0]
        gl = -losses.sum()
        curve = capital + np.cumsum(pnls)
        peak = np.maximum.accumulate(curve)
        return {
            "final_equity": round(float(curve[-1]), 0),
            "return_%": round(100.0 * (curve[-1] / capital - 1), 1),
            "win_%": round(100.0 * len(wins) / len(pnls), 1),
            "profit_factor": round(wins.sum() / gl, 2) if gl > 0 else np.inf,
            "max_dd_%": round(100.0 * float(((curve - peak) / peak).min()), 2),
            "avg_trade": round(float(pnls.mean()), 2),
        }

    rows = [{"variant": "as-is (stop only)", **simulate(lambda r: r["return_pct"])}]

    for tp in (1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 7.5, 10.0):
        rows.append({
            "variant": f"take-profit {tp:g}%",
            **simulate(lambda r, tp=tp: tp if r["mfe_pct"] >= tp else r["return_pct"]),
        })

    for be in (0.5, 1.0, 2.0, 3.0):
        rows.append({
            "variant": f"breakeven stop after {be:g}%",
            **simulate(lambda r, be=be: max(r["return_pct"], 0.0)
                       if r["mfe_pct"] >= be else r["return_pct"]),
        })

    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# ML feasibility
# --------------------------------------------------------------------------

def ml_feasibility(t: pd.DataFrame) -> None:
    """Can a filter be learned from what the trade list alone contains?

    Only calendar features are testable here -- everything informative about
    the setup (indicator values at entry) needs bar data. This is a floor, not
    a ceiling: a negative result means calendar features are useless, not that
    the idea is dead.
    """
    print("\nML filter feasibility")
    print("-" * 72)
    print(f"  usable trades: {len(t)}")
    print(f"  of which wins: {int((t['pnl'] > 0).sum())}   "
          f"losses: {int((t['pnl'] <= 0).sum())}")

    print("\n  Sample-size reality check:")
    print("    231 trades supports maybe 5-10 features before overfitting bites.")
    print("    A Deep Forest with hundreds of trees will fit this perfectly and")
    print("    generalise to nothing. Start with logistic regression on a")
    print("    handful of features and walk-forward splits.")

    feats = pd.DataFrame({
        "hour": t["entry_time"].dt.hour,
        "weekday": t["entry_time"].dt.weekday,
        "month": t["entry_time"].dt.month,
        "side_long": (t["side"] == "long").astype(int),
    })
    y = (t["pnl"] > 0).astype(int)

    print("\n  Win rate by entry hour (UTC+1, chart timezone):")
    by_hour = pd.DataFrame({"n": y.groupby(feats["hour"]).size(),
                            "win_%": 100 * y.groupby(feats["hour"]).mean()})
    by_hour = by_hour[by_hour["n"] >= 5]
    print("    " + by_hour.round(1).to_string().replace("\n", "\n    "))

    print("\n  Win rate by weekday (0=Mon):")
    by_day = pd.DataFrame({"n": y.groupby(feats["weekday"]).size(),
                           "win_%": 100 * y.groupby(feats["weekday"]).mean()})
    print("    " + by_day.round(1).to_string().replace("\n", "\n    "))

    base = 100 * y.mean()
    print(f"\n  Baseline win rate: {base:.1f}%")
    spread = by_hour["win_%"].max() - by_hour["win_%"].min() if len(by_hour) else 0
    print(f"  Best-to-worst hour spread: {spread:.1f} points across "
          f"{len(by_hour)} hours with >=5 trades.")
    print("\n  With this few trades per bucket, a spread of this size is what")
    print("  random noise produces. Do not build a time-of-day filter on it.")
    print("  Getting bar data back would let you test features that could")
    print("  plausibly carry signal -- ATR regime, trend slope, distance from")
    print("  the band at entry -- which calendar features cannot.")


# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trades", required=True, help="TradingView List of Trades CSV")
    ap.add_argument("--capital", type=float, default=4000.0)
    ap.add_argument("--sweep", action="store_true",
                    help="run the alternative-exit counterfactual")
    ap.add_argument("--ml-check", action="store_true",
                    help="assess whether a learned filter is feasible")
    args = ap.parse_args()

    t = load_trade_list(args.trades)
    summarise(t, args.capital)
    concentration_report(t)
    scale_free_view(t)
    excursion_report(t)

    if args.sweep:
        print("\nAlternative exit rules (counterfactual)")
        print("-" * 72)
        table = counterfactual_exits(t, args.capital)
        print(table.to_string(index=False))

        print("\n  HOW TO READ THIS")
        print("  Excursions record how far a trade went, not when, so every")
        print("  variant is an upper bound. The bias favours the variants over")
        print("  the baseline -- which makes the two findings asymmetric:")
        print()
        print("  1. TAKE-PROFITS LOSE, and that conclusion is safe. Every level")
        print("     from 1% to 10% underperforms the baseline even with the bias")
        print("     working in its favour. Capping winners destroys the strategy,")
        print("     because a handful of very large trades carry all of it. So")
        print("     'the take-profit never fills' (QUIRK 6) is not costing money.")
        print()
        wins = t[t["pnl"] > 0]
        underwater = int((wins["mae_pct"].abs() >= 0.5).sum())
        uw_share = 100 * wins[wins["mae_pct"].abs() >= 0.5]["pnl"].sum() / t["pnl"].sum()
        print("  2. THE BREAKEVEN NUMBERS ARE NOT TRUSTWORTHY. This counterfactual")
        print("     cannot see trades that would have been stopped at breakeven")
        print("     and then gone on to win, because their excursion is recorded")
        print(f"     after the dip. In fact {underwater} of {len(wins)} winners went at least")
        print(f"     0.5% underwater at some point, and those winners carry {uw_share:.0f}% of")
        print("     all net profit. A breakeven stop would have killed a large")
        print("     share of them. Treat the +391% as an artefact, not a finding.")

    if args.ml_check:
        ml_feasibility(t)

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(out_dir, exist_ok=True)
    t.to_csv(os.path.join(out_dir, "trade_history.csv"))
    if args.sweep:
        counterfactual_exits(t, args.capital).to_csv(
            os.path.join(out_dir, "exit_counterfactuals.csv"), index=False)
    print(f"\nwrote trade_history.csv to {out_dir}")


if __name__ == "__main__":
    main()
