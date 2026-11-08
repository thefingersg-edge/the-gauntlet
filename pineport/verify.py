#!/usr/bin/env python3
"""Verify the Python port against TradingView, bar by bar.

The single most important thing this does is run the port on **TradingView's own
exported bars** rather than on yfinance data. Your chart is OANDA:XAUUSD (spot
CFD); yfinance's nearest equivalents are a different instrument with different
sessions, closes and gaps. Comparing across two data feeds means every
divergence is ambiguous -- data or logic? Feeding TradingView's bars back in
removes the data variable entirely, so anything that differs is logic, and can
be fixed.

Once the port is verified on those bars, you can point it at any feed you like
for research. Verification and research are different jobs.

Usage
-----
    python verify.py --tv-chart chart_export.csv
    python verify.py --tv-chart chart_export.csv --tv-trades list_of_trades.csv

Getting the exports out of TradingView
--------------------------------------
*Chart data* (this is the valuable one -- it carries every plotted series):
    chart toolbar -> the "..." menu (top right of the chart) -> Export chart
    data... -> tick "Include plotted values" -> Export.

*List of Trades*:
    Strategy Tester panel -> List of Trades tab -> the export/download icon
    (top right of that panel) -> CSV.

Make sure the strategy's Properties tab matches what you pass here: initial
capital 4000, order size as-is, pyramiding 0, commission 0, slippage 0.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from broker import BrokerConfig                     # noqa: E402
from data import _normalise, _read_csv              # noqa: E402
from metrics import compute_metrics, format_metrics  # noqa: E402
from strategy import Params, run_strategy           # noqa: E402


# --------------------------------------------------------------------------
# column mapping
# --------------------------------------------------------------------------

def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


#: TradingView plot title (normalised) -> (occurrence index, our series name,
#: where it lives). The occurrence index matters because the original script
#: titles *fifteen* different plots "SL Long"; TradingView exports them in
#: plot order, so P1 is the first "SL Long", P5 the second, P6 the third.
PLOT_MAP: list[tuple[str, int, str, str]] = [
    ("bollinger_bands_sma_basis_line", 0, "bb_basis_long", "ind"),
    ("bollinger_bands_lower_line",     0, "bb_lower",      "ind"),
    ("bollinger_bands_upper_line",     0, "bb_upper",      "ind"),
    ("sl_long",    0, "price_stop_long",        "diag"),   # P1
    ("target_long", 0, "target_long",           "diag"),   # P2
    ("sl_short",   0, "price_stop_short",       "diag"),   # P3
    ("target_short", 0, "target_short",         "diag"),   # P4
    ("sl_long",    1, "profit_lockin_up_plot",  "diag"),   # P5
    ("sl_long",    2, "profit_lockin_down_plot", "diag"),  # P6
]


def group_duplicate_columns(columns) -> dict[str, list[str]]:
    """Group columns by plot title, undoing pandas' duplicate-name mangling.

    A CSV with fifteen columns literally named "SL Long" is read back by pandas
    as ``SL Long``, ``SL Long.1``, ``SL Long.2``... A numeric suffix is only
    treated as mangling when the unsuffixed name is also present, so a genuine
    plot called "Level 1" is left alone.
    """
    normalised = [_norm(c) for c in columns]
    plain = set(normalised)

    groups: dict[str, dict[int, str]] = {}
    for col, norm in zip(columns, normalised):
        m = re.match(r"^(?P<base>.+?)_(?P<n>\d+)$", norm)
        if m and m.group("base") in plain:
            base, order = m.group("base"), int(m.group("n"))
        else:
            base, order = norm, 0
        groups.setdefault(base, {})[order] = col

    return {base: [members[k] for k in sorted(members)]
            for base, members in groups.items()}


def find_columns(df: pd.DataFrame) -> dict[str, str]:
    """Resolve TradingView plot columns to port series names."""
    groups = group_duplicate_columns(list(df.columns))
    resolved: dict[str, str] = {}
    for tv_name, occurrence, ours, _where in PLOT_MAP:
        cols = groups.get(tv_name, [])
        if len(cols) > occurrence:
            resolved[ours] = cols[occurrence]
    return resolved


# --------------------------------------------------------------------------
# comparison
# --------------------------------------------------------------------------

def apply_plot_mask(name: str, series: pd.Series, diag: pd.DataFrame) -> pd.Series:
    """Blank out the bars where the original's plot() draws `na`.

    The script plots e.g. ``price_stop_long > 0 ? price_stop_long : na``, so
    TradingView writes an empty cell outside positions while the port carries
    the sentinel 0.0. Masking to match makes the ``py_only`` count meaningful:
    a non-zero ``py_only`` then says "the port holds a position on bars where
    TradingView holds none", which is exactly the divergence worth chasing.
    """
    s = series.copy()
    if name in ("price_stop_long", "target_long"):
        return s.where(diag["price_stop_long"] > 0)
    if name in ("price_stop_short", "target_short"):
        return s.where(diag["price_stop_short"] < 10_000_000.0)
    if name == "profit_lockin_up_plot":
        return s.where(diag["position"] > 0)
    if name == "profit_lockin_down_plot":
        return s.where(diag["position"] < 0)
    return s


def compare_series(tv: pd.Series, py: pd.Series, tol: float,
                   name: str) -> dict:
    """Diff one series, reporting where it first goes wrong.

    Both sides are compared only where TradingView has a value, because the
    script plots `na` outside positions and TradingView writes those as blanks.
    """
    a = pd.to_numeric(tv, errors="coerce").to_numpy(dtype=float)
    b = pd.to_numeric(py, errors="coerce").to_numpy(dtype=float)
    n = min(a.size, b.size)
    a, b = a[:n], b[:n]

    both = ~np.isnan(a) & ~np.isnan(b)
    tv_only = ~np.isnan(a) & np.isnan(b)
    py_only = np.isnan(a) & ~np.isnan(b)

    row = {"series": name, "compared": int(both.sum()),
           "tv_only": int(tv_only.sum()), "py_only": int(py_only.sum())}

    if not both.any():
        row.update({"max_abs_diff": np.nan, "max_rel_diff": np.nan,
                    "n_mismatch": 0, "first_bad_bar": -1, "verdict": "no overlap"})
        return row

    diff = np.abs(a - b)
    scale = np.maximum(np.abs(a), 1e-9)
    rel = diff / scale

    bad = both & (diff > tol) & (rel > 1e-6)
    row["max_abs_diff"] = float(diff[both].max())
    row["max_rel_diff"] = float(rel[both].max())
    row["n_mismatch"] = int(bad.sum())
    row["first_bad_bar"] = int(np.argmax(bad)) if bad.any() else -1
    row["verdict"] = "OK" if not bad.any() else "MISMATCH"
    return row


def compare_position(tv_chars: pd.Series, position: pd.Series,
                     index: pd.DatetimeIndex, max_runs: int = 12) -> pd.DataFrame:
    """Compare in-position state bar by bar, using the exported `Chars` column.

    The original ends with ``plotchar(strategy.opentrades)``, so the export
    carries TradingView's open-trade count on **every bar**. That is far more
    informative than a trade list: it says exactly which bars TradingView held a
    position, so a divergence can be located to the bar rather than to the trade.

    Returns one row per contiguous run of disagreement.
    """
    tv_in = pd.to_numeric(tv_chars, errors="coerce").fillna(0).to_numpy() > 0
    py_in = position.to_numpy() != 0
    n = min(tv_in.size, py_in.size)
    tv_in, py_in = tv_in[:n], py_in[:n]

    agree = tv_in == py_in
    print(f"  bars: {n}   TradingView in-position {int(tv_in.sum())}   "
          f"port in-position {int(py_in.sum())}")
    print(f"  agreement: {100.0 * agree.mean():.2f}% "
          f"({int((~agree).sum())} bars differ)")

    runs = []
    i = 0
    while i < n:
        if agree[i]:
            i += 1
            continue
        j = i
        while j < n and not agree[j]:
            j += 1
        runs.append({
            "from_bar": i, "to_bar": j - 1, "bars": j - i,
            "from_time": index[i], "to_time": index[j - 1],
            "who": "tradingview only" if tv_in[i] else "port only",
        })
        i = j

    if runs:
        print(f"\n  {len(runs)} disagreement run(s); first {min(len(runs), max_runs)}:")
        for r in runs[:max_runs]:
            print(f"    bars {r['from_bar']:>5}-{r['to_bar']:<5} "
                  f"({r['bars']:>4} bars)  {r['who']:<17} "
                  f"{r['from_time']:%Y-%m-%d %H:%M} -> {r['to_time']:%Y-%m-%d %H:%M}")
    else:
        print("  position state matches on every bar")
    return pd.DataFrame(runs)


def warmup_report(df: pd.DataFrame, ind: pd.DataFrame, tv_chars: pd.Series) -> int:
    """Warn when the export is shorter than the strategy's own warm-up.

    TradingView computes on all the history it has loaded, but "Export chart
    data" only writes the visible window. If that window is shorter than the
    longest lookback in the script (here `lengthKCS = 942`), TradingView's
    values are warm on bar 0 while the port's are still NaN, and the two cannot
    agree over the early part of the file no matter how correct the port is.
    """
    longest = 942
    first_valid = int(ind["val_s"].notna().to_numpy().argmax()) if ind["val_s"].notna().any() else len(df)

    tv_in = pd.to_numeric(tv_chars, errors="coerce").fillna(0).to_numpy() > 0
    early = int(tv_in[:first_valid].sum()) if first_valid < len(tv_in) else int(tv_in.sum())

    print(f"  export length      : {len(df)} bars")
    print(f"  longest lookback   : {longest} bars (lengthKCS)")
    print(f"  port warm from bar : {first_valid}")
    if first_valid > 0:
        print(f"  TradingView held a position on {early} bars inside that "
              f"warm-up region")
    if first_valid >= len(df):
        print("\n  The export is shorter than the 942-bar lookback, so the squeeze\n"
              "  series never warms up at all in the port.")
    elif early > 0:
        print("\n  Bars before the warm-up point cannot match, because TradingView\n"
              "  computed them from history that is not in this file. Either export\n"
              "  a longer window (scroll left to load more bars first), or compare\n"
              "  with the squeeze filter disabled -- which is informative in its own\n"
              "  right, since QUIRK 2 says that filter never rejects anything.")
    return first_valid


def compare_trades(tv_path: str, py: pd.DataFrame, tolerance: str) -> None:
    try:
        tv = pd.read_csv(tv_path)
    except Exception as exc:
        print(f"  could not read {tv_path}: {exc}")
        print("  expected a Strategy Tester -> List of Trades CSV export")
        return
    if tv.empty:
        print(f"  {tv_path} has no rows")
        return
    tv.columns = [_norm(c) for c in tv.columns]

    date_col = next((c for c in tv.columns if "date" in c or "time" in c), None)
    type_col = next((c for c in tv.columns if "type" in c or "signal" in c), None)
    if date_col is None:
        print("  could not find a date column; comparing counts only")
        print(f"  python trades {len(py)}  vs  tradingview rows {len(tv)}")
        return

    tv[date_col] = pd.to_datetime(tv[date_col], errors="coerce", utc=True)
    tv = tv.dropna(subset=[date_col])

    # TradingView writes one row per fill (entry and exit), so entries are the
    # rows whose type mentions "entry" when that column exists.
    if type_col is not None:
        entries = tv[tv[type_col].astype(str).str.contains("entry", case=False, na=False)]
        if entries.empty:
            entries = tv
    else:
        entries = tv

    tv_times = entries[date_col].sort_values().reset_index(drop=True)
    py_times = pd.to_datetime(py["entry_time"], utc=True).sort_values().reset_index(drop=True)

    print(f"  entries -- tradingview {len(tv_times)}   python {len(py_times)}")

    tol = pd.Timedelta(tolerance)
    matched, unmatched = 0, []
    for t in py_times:
        if len(tv_times) and (tv_times - t).abs().min() <= tol:
            matched += 1
        else:
            unmatched.append(t)
    print(f"  matched within {tolerance}: {matched} / {len(py_times)}")

    missing = [t for t in tv_times
               if len(py_times) == 0 or (py_times - t).abs().min() > tol]
    if unmatched:
        print("  python-only entries (first 10):")
        for t in unmatched[:10]:
            print(f"    {t}")
    if missing:
        print("  tradingview-only entries (first 10):")
        for t in missing[:10]:
            print(f"    {t}")
    if not unmatched and not missing:
        print("  trade lists agree")


# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tv-chart", required=True,
                    help="TradingView 'Export chart data' CSV, with plotted values")
    ap.add_argument("--tv-trades", default=None,
                    help="TradingView 'List of Trades' CSV")
    ap.add_argument("--capital", type=float, default=4000.0)
    ap.add_argument("--point-value", type=float, default=1.0,
                    help="1 for OANDA:XAUUSD and other spot CFDs; 100 for COMEX GC")
    ap.add_argument("--commission-pct", type=float, default=0.0)
    ap.add_argument("--slippage", type=float, default=0.0)
    ap.add_argument("--tolerance", type=float, default=0.01,
                    help="absolute price tolerance, in points, for a series match")
    ap.add_argument("--trade-tolerance", default="2h")
    ap.add_argument("--no-squeeze", action="store_true",
                    help="disable the squeeze filter entirely, including the "
                         "live valL > 0 test. Blunt; prefer --assume-squeeze-on.")
    ap.add_argument("--assume-squeeze-on", action="store_true",
                    help="treat sqzOn as True (it is, on every warmed-up bar) "
                         "while keeping the valL/valS tests. Drops the long "
                         "side's warm-up from 942 bars to 76, so a short chart "
                         "export can still be verified.")
    args = ap.parse_args()

    # ---- load TradingView's bars ----------------------------------------
    raw = _read_csv(args.tv_chart)
    df = _normalise(raw)
    print(f"TradingView bars: {len(df)}  "
          f"{df.index[0]:%Y-%m-%d %H:%M} -> {df.index[-1]:%Y-%m-%d %H:%M}")

    if float(np.nansum(df["volume"].to_numpy())) <= 0:
        print("\nWARNING: the export has no volume. Every ta.vwma() in this\n"
              "strategy divides by volume, so the port cannot reproduce the\n"
              "chart. Re-export with the volume column included.")

    # ---- resolve plot columns -------------------------------------------
    raw.columns = [str(c) for c in raw.columns]
    resolved = find_columns(raw)
    print(f"\nmatched {len(resolved)} of {len(PLOT_MAP)} plotted series:")
    for ours, tvcol in resolved.items():
        print(f"  {ours:<26} <- {tvcol!r}")
    unmatched_plots = [m[2] for m in PLOT_MAP if m[2] not in resolved]
    if unmatched_plots:
        print(f"  not found: {', '.join(unmatched_plots)}")
        print("  (re-export with 'Include plotted values' ticked if these are missing)")

    # ---- run the port on those exact bars --------------------------------
    cfg = BrokerConfig(initial_capital=args.capital, point_value=args.point_value,
                       commission_pct=args.commission_pct,
                       slippage_points=args.slippage)
    params = Params(use_squeeze_filter=not args.no_squeeze,
                    assume_squeeze_on=args.assume_squeeze_on)
    if args.no_squeeze:
        print("\n(running with the squeeze filter disabled entirely)")
    elif args.assume_squeeze_on:
        print("\n(running with sqzOn assumed True; valL/valS tests still active)")
    res = run_strategy(df, params, cfg)

    # ---- warm-up and position state --------------------------------------
    chars_col = next((c for c in raw.columns if _norm(c) == "chars"), None)

    print("\nWarm-up")
    print("-" * 100)
    warmup_report(df, res.indicators,
                  raw[chars_col] if chars_col else pd.Series(dtype=float))

    if chars_col is not None:
        print("\nPosition state (from the exported `Chars` = strategy.opentrades)")
        print("-" * 100)
        runs = compare_position(raw[chars_col].reset_index(drop=True),
                               res.diagnostics["position"].reset_index(drop=True),
                               df.index)
    else:
        runs = pd.DataFrame()
        print("\nNo `Chars` column found. The original ends with "
              "`plotchar(strategy.opentrades)`,\nwhich exports per-bar position "
              "state -- the most useful column for this job.")

    # ---- series diff -----------------------------------------------------
    rows = []
    for tv_name, occurrence, ours, where in PLOT_MAP:
        if ours not in resolved:
            continue
        src = res.indicators if where == "ind" else res.diagnostics
        if ours not in src.columns:
            continue
        masked = apply_plot_mask(ours, src[ours], res.diagnostics)
        rows.append(compare_series(raw[resolved[ours]].reset_index(drop=True),
                                   masked.reset_index(drop=True),
                                   args.tolerance, ours))

    if rows:
        table = pd.DataFrame(rows)
        print("\nSeries comparison")
        print("-" * 100)
        with pd.option_context("display.width", 200, "display.max_columns", 20):
            print(table.to_string(index=False))

        bad = table[table["verdict"] == "MISMATCH"]
        if not bad.empty:
            first = bad.sort_values("first_bad_bar").iloc[0]
            bar = int(first["first_bad_bar"])
            print(f"\nFirst divergence: {first['series']} at bar {bar} "
                  f"({df.index[bar]})")
            print("Context around it:")
            lo, hi = max(0, bar - 3), min(len(df), bar + 4)
            ours = first["series"]
            src = (res.indicators if ours in res.indicators.columns
                   else res.diagnostics)
            ctx = pd.DataFrame({
                "close": df["close"].iloc[lo:hi].to_numpy(),
                "tradingview": pd.to_numeric(
                    raw[resolved[ours]], errors="coerce").to_numpy()[lo:hi],
                "python": src[ours].to_numpy()[lo:hi],
            }, index=df.index[lo:hi])
            ctx["diff"] = ctx["tradingview"] - ctx["python"]
            with pd.option_context("display.float_format", lambda v: f"{v:,.5f}"):
                print(ctx.to_string())
            print("\nFix the earliest divergence first -- later ones are usually\n"
                  "downstream of it, not independent bugs.")

    # ---- trade diff ------------------------------------------------------
    print("\nTrade comparison")
    print("-" * 100)
    if args.tv_trades:
        compare_trades(args.tv_trades, res.trades, args.trade_tolerance)
    else:
        print(f"  python trades: {len(res.trades)} "
              f"(pass --tv-trades to compare against the Strategy Tester)")

    m = compute_metrics(res.equity, res.trades, args.capital, df["close"])
    print()
    print(format_metrics(m, "Port results on TradingView's own bars"))

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(out_dir, exist_ok=True)
    res.trades.to_csv(os.path.join(out_dir, "verify_trades.csv"), index=False)
    res.diagnostics.to_csv(os.path.join(out_dir, "verify_diagnostics.csv"))
    if rows:
        pd.DataFrame(rows).to_csv(os.path.join(out_dir, "verify_series.csv"), index=False)
    if not runs.empty:
        runs.to_csv(os.path.join(out_dir, "verify_position_runs.csv"), index=False)
    print(f"\nwrote verify_*.csv to {out_dir}")


if __name__ == "__main__":
    main()
