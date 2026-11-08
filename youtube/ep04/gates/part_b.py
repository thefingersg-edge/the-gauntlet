#!/usr/bin/env python3
"""ARM F, Part B — overnight hold. From run1_armF.md section B, verbatim.

Session handling is explicit: hourly bars are UTC-stamped by bar open
(verified in verify_h1.py against the daily bars, 100% of high/low/close).
Entry and exit hours are local-clock with DST, so the UTC hour moves twice
a year and is never hard-coded.
"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
import engine
from engine import Trade

H1 = os.path.expanduser("~/mnt/Claude/pineport")

SPEC = {
    "nas100usd": dict(zone="America/New_York", enter=16, exit=9),
    "de30eur":   dict(zone="Europe/Berlin",    enter=17, exit=9),
}
SMA_TREND = 200

_h1: dict[str, pd.DataFrame] = {}

def load_h1(mkt: str) -> pd.DataFrame:
    if mkt not in _h1:
        df = pd.read_csv(f"{H1}/{mkt}_oanda_h1.csv")
        # DATA DEFECT, 2026-11-06: the hourly files are not internally
        # consistent. nas100usd is naive throughout; de30eur carries +00:00
        # throughout; spx500usd carries +00:00 for 129,175 rows and then
        # switches to NAIVE for its last 907 (from 2026-08-07 15:00 to
        # 2026-10-02). Checked rather than assumed: prices are continuous
        # across the boundary (7756.4 -> 7756.3) and the hours run
        # sequentially, so the naive tail is UTC like the rest. Had it been
        # local time instead, every session boundary after that date would
        # have been wrong by four or five hours and nothing would have
        # flagged it. ISO8601 + utc=True normalises all three cases.
        df["time"] = pd.to_datetime(df["time"], format="ISO8601", utc=True)
        _h1[mkt] = df.set_index("time").sort_index()
    return _h1[mkt]


def session_closes(mkt: str) -> pd.Series:
    """UTC timestamp at which each daily bar actually closed (17:00 New York),
    derived from the hourly bars rather than assumed."""
    h = load_h1(mkt)
    ny = h.index.tz_convert("America/New_York")
    lbl = (ny + pd.Timedelta(hours=7)).normalize().tz_localize(None)
    last = pd.Series(h.index, index=lbl).groupby(level=0).last()
    last.index = last.index.tz_localize("UTC")
    return last + pd.Timedelta(hours=1)


def run_market(mkt: str, p: dict = None) -> list[Trade]:
    p = {**SPEC[mkt], **(p or {})}
    h = load_h1(mkt)
    loc = h.index.tz_convert(p["zone"])
    o = h["open"].to_numpy()
    idx = h.index

    d = engine.load(mkt)
    sma = d["close"].rolling(SMA_TREND).mean()
    ok_daily = (d["close"] > sma)                 # filter, per completed daily bar
    closes_at = session_closes(mkt).reindex(d.index).dropna()
    ok = ok_daily.reindex(closes_at.index)
    # a filter value becomes usable only once its bar has closed
    filt = pd.Series(ok.to_numpy(), index=closes_at.to_numpy()).sort_index()

    ent = np.flatnonzero(loc.hour == p["enter"])
    ext = np.flatnonzero(loc.hour == p["exit"])
    trades: list[Trade] = []
    for i in ent:
        t_in = idx[i]
        sub = filt.loc[:t_in]
        if sub.empty or not bool(sub.iloc[-1]):
            continue                               # trend filter off, or no completed bar
        j = ext[np.searchsorted(ext, i, side="right")] if np.searchsorted(ext, i, side="right") < len(ext) else None
        if j is None:
            continue
        t_out = idx[j]
        if (t_out - t_in) > pd.Timedelta(days=4):  # market never reopened; no trade
            continue
        trades.append(Trade(mkt, +1, t_in, t_out, float(o[i]), float(o[j]), "overnight"))
    return trades


def run(p: dict = None) -> list[Trade]:
    out = []
    for m in SPEC:
        out += run_market(m, p)
    return out


if __name__ == "__main__":
    ts = run()
    print(f"ARM F part B — {len(ts)} overnight trades")
    for m in SPEC:
        s = [t for t in ts if t.market == m]
        if not s: continue
        nets = [t.net for t in s]
        print(f"  {m:<11} {len(s):>5} trades  mean net {np.mean(nets):+.3%}  "
              f"gross {np.mean([t.gross for t in s]):+.3%}  "
              f"cost {np.mean([t.cost() for t in s]):.3%}  "
              f"span {s[0].entry_date.date()} .. {s[-1].entry_date.date()}")
    nets = [t.net for t in ts]
    print(f"\n  all: mean net {np.mean(nets):+.4%} per trade over {len(ts)} trades")
