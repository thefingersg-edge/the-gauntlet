#!/usr/bin/env python3
"""Gate 7 — daily marked-to-market equity, from each arm's OWN sizing rules.

Built so the drawdown is measured at daily resolution whatever resolution
the strategy chose to report at. Positions are marked every day they are
open, including open losers, so nothing hides between trades.
"""
from __future__ import annotations
import numpy as np, pandas as pd, engine


def simulate(trades, sizing, start_equity=10000.0, margin_cap=0.8,
             leverage=20.0, notional_cap=3.0):
    """sizing(trade, atr, E, V) -> units.  Returns (equity series, log)."""
    ts = sorted(trades, key=lambda t: t.entry_date)
    dates = sorted({d for t in ts for d in (t.entry_date, t.exit_date)})
    all_dates = sorted(set().union(*[set(engine.load(m).index)
                                    for m in {t.market for t in ts}]))
    all_dates = [d for d in all_dates if d >= ts[0].entry_date and d <= ts[-1].exit_date]

    closes = {m: engine.load(m)["close"] for m in {t.market for t in ts}}
    eur = engine.load("eurusd")["close"]

    E = start_equity
    cash = start_equity
    open_pos = []          # dicts: market, units, V, entry_px, last_px, entry_date, exit_date
    pending = {d: [] for d in all_dates}
    for t in ts:
        pending.setdefault(t.entry_date, []).append(t)

    eq, skipped = [], 0
    for d in all_dates:
        # 1. mark open positions to today's close
        for p in open_pos:
            px = float(closes[p["market"]].get(d, p["last_px"]))
            cash += p["units"] * (px - p["last_px"]) * p["V"]
            p["last_px"] = px
        # 2. financing on every open position, per calendar night
        for p in open_pos:
            notional = abs(p["units"] * p["last_px"] * p["V"])
            cash -= notional * engine.FINANCING_ANNUAL / 365.0
        # 3. close anything exiting today
        still = []
        for p in open_pos:
            if p["exit_date"] == d:
                cash += p["units"] * (p["exit_px"] - p["last_px"]) * p["V"]
                cash -= abs(p["units"] * p["exit_px"] * p["V"]) * engine.SPREAD_RT[p["market"]] / 2
            else:
                still.append(p)
        open_pos = still
        E = cash + sum(0.0 for _ in open_pos)      # cash already includes marks
        # 4. open anything entering today
        for t in pending.get(d, []):
            df = engine.load(t.market)
            i = df.index.get_loc(t.entry_date)
            atr = float(engine_atr(df, i))
            V = 1.0 if t.market != "de30eur" else float(eur.asof(t.entry_date))
            units = sizing(t, atr, E, V)
            notional = abs(units * t.entry_px * V)
            if notional > notional_cap * E:
                units = (notional_cap * E) / (t.entry_px * V)
                notional = notional_cap * E
            used = sum(abs(p["units"] * p["last_px"] * p["V"]) for p in open_pos) / leverage
            if (used + notional / leverage) > margin_cap * E:
                skipped += 1
                continue
            units = np.floor(units * 100) / 100.0
            if units <= 0:
                skipped += 1
                continue
            cash -= abs(units * t.entry_px * V) * engine.SPREAD_RT[t.market] / 2
            pos = dict(market=t.market, units=units, V=V,
                       entry_px=t.entry_px, last_px=t.entry_px,
                       exit_px=t.exit_px, entry_date=t.entry_date,
                       exit_date=t.exit_date)
            if t.exit_date == d:
                # BUG FIX 2026-11-02: a stop hit on the entry bar exits the
                # same day. Step 3 has already run, so such a position was
                # never closed and marked to market forever -- which produced
                # phantom index exposure and wrecked every volatile year.
                cash += pos["units"] * (pos["exit_px"] - pos["last_px"]) * pos["V"]
                cash -= abs(pos["units"] * pos["exit_px"] * pos["V"]) * engine.SPREAD_RT[t.market] / 2
            else:
                open_pos.append(pos)
        eq.append((d, cash))
    s = pd.Series([v for _, v in eq], index=[d for d, _ in eq])
    return s, {"skipped_margin_or_size": skipped}


def engine_atr(df, i, n=20):
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean().iloc[i]


def max_drawdown(eq: pd.Series) -> float:
    peak = eq.cummax()
    return float(((eq - peak) / peak).min())


def g7_daily_risk(eq: pd.Series, claimed: float | None, tol: float = 0.25) -> dict:
    dd = max_drawdown(eq)
    out = {"gate": "7 DAILY RISK",
           "measured_daily_max_dd": f"{dd:.1%}",
           "claimed_by_strategy": (f"{claimed:.1%}" if claimed is not None else "no claim made"),
           "resolution": "daily close, open positions marked"}
    if claimed is None:
        out["pass"] = True
        out["note"] = "nothing was concealed because nothing was claimed"
    else:
        out["pass"] = bool(abs(dd) <= abs(claimed) * (1 + tol))
        out["tolerance"] = f"claim may understate by at most {tol:.0%}"
    return out
