"""Performance statistics, computed the way TradingView computes them.

Two deliberate choices worth knowing about:

* Sharpe and Sortino are computed from the **bar-level equity curve**, not from
  per-trade returns. Trade-level Sharpe is not comparable across strategies with
  different holding periods and tends to flatter low-frequency systems.
* Annualisation uses the actual observed bar spacing rather than an assumed 252
  days, because gold trades close to 24/5 and a 1H series has roughly 6000 bars
  per year, not 1638.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _bars_per_year(index: pd.DatetimeIndex) -> float:
    if len(index) < 3:
        return 252.0
    span_years = (index[-1] - index[0]).total_seconds() / (365.25 * 24 * 3600)
    if span_years <= 0:
        return 252.0
    return len(index) / span_years


def max_drawdown(equity: pd.Series) -> tuple[float, float, pd.Timestamp | None]:
    """Return (max drawdown in currency, max drawdown as a fraction, trough date)."""
    if equity.empty:
        return 0.0, 0.0, None
    peak = equity.cummax()
    dd = equity - peak
    dd_pct = dd / peak.replace(0, np.nan)
    i = dd_pct.idxmin() if dd_pct.notna().any() else None
    return float(dd.min()), float(dd_pct.min() if i is not None else 0.0), i


def compute_metrics(equity: pd.Series, trades: pd.DataFrame,
                    initial_capital: float,
                    benchmark: pd.Series | None = None) -> dict:
    """Summarise a run. Returns a flat dict so results tabulate easily."""
    m: dict[str, float | int | str] = {}

    equity = equity.dropna()
    if equity.empty:
        return {"trades": 0, "note": "no equity curve"}

    final = float(equity.iloc[-1])
    m["initial_capital"] = initial_capital
    m["final_equity"] = final
    m["net_profit"] = final - initial_capital
    m["return_pct"] = 100.0 * (final / initial_capital - 1.0)

    bpy = _bars_per_year(equity.index)
    m["bars"] = int(len(equity))
    m["years"] = len(equity) / bpy

    rets = equity.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    if len(rets) > 2 and rets.std(ddof=1) > 0:
        m["sharpe"] = float(rets.mean() / rets.std(ddof=1) * np.sqrt(bpy))
        downside = rets[rets < 0]
        ds = downside.std(ddof=1) if len(downside) > 1 else np.nan
        m["sortino"] = float(rets.mean() / ds * np.sqrt(bpy)) if ds and ds > 0 else np.nan
    else:
        m["sharpe"] = np.nan
        m["sortino"] = np.nan

    if m["years"] > 0 and final > 0:
        m["cagr_pct"] = 100.0 * ((final / initial_capital) ** (1.0 / m["years"]) - 1.0)
    else:
        m["cagr_pct"] = np.nan

    dd_abs, dd_frac, dd_at = max_drawdown(equity)
    m["max_drawdown"] = dd_abs
    m["max_drawdown_pct"] = 100.0 * dd_frac
    m["max_drawdown_at"] = str(dd_at) if dd_at is not None else ""
    m["calmar"] = (m["cagr_pct"] / abs(m["max_drawdown_pct"])
                   if m["max_drawdown_pct"] else np.nan)

    # -- trade statistics --------------------------------------------------
    n = len(trades)
    m["trades"] = int(n)
    if n:
        pnl = trades["pnl"].astype(float)
        wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
        gross_win, gross_loss = float(wins.sum()), float(-losses.sum())

        m["win_rate_pct"] = 100.0 * len(wins) / n
        m["profit_factor"] = gross_win / gross_loss if gross_loss > 0 else np.inf
        m["avg_trade"] = float(pnl.mean())
        m["avg_win"] = float(wins.mean()) if len(wins) else 0.0
        m["avg_loss"] = float(losses.mean()) if len(losses) else 0.0
        m["payoff_ratio"] = (abs(m["avg_win"] / m["avg_loss"])
                             if m["avg_loss"] else np.inf)
        m["expectancy"] = float(pnl.mean())
        m["largest_win"] = float(pnl.max())
        m["largest_loss"] = float(pnl.min())
        m["avg_bars_held"] = float(trades["bars_held"].mean())
        m["longs"] = int((trades["direction"] == 1).sum())
        m["shorts"] = int((trades["direction"] == -1).sum())
        m["max_consecutive_losses"] = _max_streak(pnl <= 0)
        if "exit_reason" in trades:
            for reason, count in trades["exit_reason"].value_counts().items():
                m[f"exit_{reason}"] = int(count)
        exposure_bars = float(trades["bars_held"].sum())
        m["exposure_pct"] = 100.0 * exposure_bars / len(equity)
    else:
        for k in ("win_rate_pct", "profit_factor", "avg_trade", "avg_win",
                  "avg_loss", "payoff_ratio", "expectancy", "largest_win",
                  "largest_loss", "avg_bars_held", "exposure_pct"):
            m[k] = np.nan
        m["longs"] = m["shorts"] = m["max_consecutive_losses"] = 0

    # -- benchmark ---------------------------------------------------------
    if benchmark is not None and len(benchmark.dropna()) > 1:
        b = benchmark.dropna()
        bh_return = 100.0 * (b.iloc[-1] / b.iloc[0] - 1.0)
        m["buy_hold_return_pct"] = float(bh_return)
        m["excess_vs_buy_hold_pct"] = float(m["return_pct"] - bh_return)
        b_rets = b.pct_change().dropna()
        if b_rets.std(ddof=1) > 0:
            m["buy_hold_sharpe"] = float(
                b_rets.mean() / b_rets.std(ddof=1) * np.sqrt(_bars_per_year(b.index)))
        bh_curve = initial_capital * (b / b.iloc[0])
        _, bh_dd, _ = max_drawdown(bh_curve)
        m["buy_hold_max_drawdown_pct"] = 100.0 * bh_dd

    return m


def _max_streak(flags: pd.Series) -> int:
    best = cur = 0
    for f in flags.to_numpy(bool):
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return int(best)


def format_metrics(m: dict, title: str = "Results") -> str:
    """Render a metrics dict as an aligned plain-text block."""
    order = [
        ("Net profit", "net_profit", "{:,.2f}"),
        ("Return", "return_pct", "{:,.2f}%"),
        ("Buy & hold return", "buy_hold_return_pct", "{:,.2f}%"),
        ("CAGR", "cagr_pct", "{:,.2f}%"),
        ("Sharpe", "sharpe", "{:,.3f}"),
        ("Sortino", "sortino", "{:,.3f}"),
        ("Max drawdown", "max_drawdown_pct", "{:,.2f}%"),
        ("Calmar", "calmar", "{:,.3f}"),
        ("Trades", "trades", "{:,.0f}"),
        ("  long / short", None, None),
        ("Win rate", "win_rate_pct", "{:,.2f}%"),
        ("Profit factor", "profit_factor", "{:,.3f}"),
        ("Payoff ratio", "payoff_ratio", "{:,.3f}"),
        ("Avg trade", "avg_trade", "{:,.2f}"),
        ("Largest win", "largest_win", "{:,.2f}"),
        ("Largest loss", "largest_loss", "{:,.2f}"),
        ("Max consec. losses", "max_consecutive_losses", "{:,.0f}"),
        ("Avg bars held", "avg_bars_held", "{:,.1f}"),
        ("Exposure", "exposure_pct", "{:,.2f}%"),
    ]
    lines = [title, "=" * len(title)]
    for label, key, fmt in order:
        if key is None:
            lines.append(f"{label:<22}{m.get('longs', 0)} / {m.get('shorts', 0)}")
            continue
        if key not in m:
            continue
        v = m[key]
        if v is None or (isinstance(v, float) and not np.isfinite(v)):
            lines.append(f"{label:<22}n/a")
        else:
            lines.append(f"{label:<22}{fmt.format(v)}")
    reasons = {k: v for k, v in m.items() if k.startswith("exit_")}
    if reasons:
        lines.append("Exits by reason       " + ", ".join(
            f"{k[5:]}={v}" for k, v in sorted(reasons.items())))
    return "\n".join(lines)
