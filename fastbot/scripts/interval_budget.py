#!/usr/bin/env python3
"""Interval budget: at what holding period does OANDA's spread stop dominating?

WHY THIS EXISTS
---------------
The stated goal is a bot on a 1-5 minute interval that nets a profit after
costs and financing. Before any signal is hypothesised, one number decides
whether that is arithmetically possible:

    cost/vol(H) = round-trip spread / (per-minute vol * sqrt(H))

This is the fraction of the typical H-minute price move that is handed to the
broker on every round trip. screen_universe.py already fixed the thresholds
used by this project:

    <= 0.15   comfortable
    <= 0.35   the barrier is at least reachable
    >  0.35   the cost swamps the move; no signal can repair it

Rearranged, that gives the number this file exists to report:

    H_min = (spread_rel / (threshold * sigma_1min))^2      minutes

the SHORTEST hold at which a strategy on that instrument is not already
dominated by the spread. If H_min lands far above 5 minutes, a 1-5m bot on
that instrument is closed by arithmetic, and no amount of backtesting,
filtering or parameter search changes it.

NO RETURNS ARE COMPUTED HERE. Everything is measured from bid/ask quotes and
realised volatility. Nothing in this file can rank an instrument by how well
it performed, because nothing in this file knows.

FINANCING
---------
OANDA charges financing only on positions open past the daily rollover. A bot
that is flat overnight pays none. That is a genuine structural advantage of
short intervals and it is why financing does not appear in the arithmetic
above -- but it is only earned if the hold stays inside a session, which is
itself a constraint on H. Reported separately as `intraday_ok`.

    python interval_budget.py --data ../data
    python interval_budget.py --self-test
"""

from __future__ import annotations

import argparse
import glob
import math
import os
import sys

VERSION = "1.0"

BAR_SECONDS = 900               # the staged bid/ask files are M15
COMFORT, CEILING = 0.15, 0.35   # thresholds, inherited from screen_universe.py

# Detectability. silver15 established required_annual_Sharpe = k / sqrt(years).
K_SIGMA = 2.0


# ----------------------------------------------------------------- loading

def _read(path):
    import pandas as pd
    d = pd.read_csv(path)
    t = d.columns[0]
    d[t] = pd.to_datetime(d[t], utc=True)
    return d.set_index(t).sort_index()


def instruments(data_dir):
    """Stems that have all three of mid/bid/ask at the staged granularity."""
    stems = set()
    for p in glob.glob(os.path.join(data_dir, "*_mid_15m.csv")):
        s = os.path.basename(p)[: -len("_mid_15m.csv")]
        if all(os.path.exists(os.path.join(data_dir, f"{s}_{k}_15m.csv"))
               for k in ("bid", "ask")):
            stems.add(s)
    return sorted(stems)


# ----------------------------------------------------------------- measures

def spread_rel(data_dir, stem):
    """Round-trip spread as a fraction of price, measured from quotes.

    Buy at ask, sell at bid, so one round trip costs (ask - bid) once.
    Reported as the MEDIAN across bars: the mean is dominated by the handful
    of illiquid rollover bars a real bot would not trade through anyway, and
    inflating cost is as much an error as understating it.
    """
    import numpy as np
    bid = _read(os.path.join(data_dir, f"{stem}_bid_15m.csv"))["close"]
    ask = _read(os.path.join(data_dir, f"{stem}_ask_15m.csv"))["close"]
    idx = bid.index.intersection(ask.index)
    b, a = bid.loc[idx].to_numpy(float), ask.loc[idx].to_numpy(float)
    mid = 0.5 * (a + b)
    rel = (a - b) / mid
    rel = rel[np.isfinite(rel) & (rel >= 0)]
    if rel.size == 0:
        return None, None, 0
    return float(np.median(rel)), float(np.percentile(rel, 90)), int(rel.size)


def vol_per_minute(data_dir, stem):
    """Per-minute log-return sd, from CONSECUTIVE bars only.

    Session and weekend gaps are excluded rather than averaged in: a gap is
    not a move the bot could have traded, and including them inflates vol,
    which would flatter every cost ratio below.

    Robust sd via the median absolute deviation. A handful of news bars would
    otherwise dominate the plain sd and, again, flatter the cost ratio.
    """
    import numpy as np
    mid = _read(os.path.join(data_dir, f"{stem}_mid_15m.csv"))["close"]
    t = mid.index.to_numpy()
    px = mid.to_numpy(float)
    dt = (t[1:] - t[:-1]) / np.timedelta64(1, "s")
    ok = (dt == BAR_SECONDS) & (px[:-1] > 0) & (px[1:] > 0)
    r = np.log(px[1:][ok] / px[:-1][ok])
    if r.size < 500:
        return None, None, 0
    mad = float(np.median(np.abs(r - np.median(r))))
    sd_robust = 1.4826 * mad
    bars_per_min = BAR_SECONDS / 60.0
    # sqrt-of-time scaling from 15m down to 1m. Measured 1m vol is HIGHER than
    # this because of bid-ask bounce, but bounce is not tradeable movement, so
    # this is the conservative estimate of the move a strategy can capture.
    return (sd_robust / math.sqrt(bars_per_min),
            float(np.std(r, ddof=1)) / math.sqrt(bars_per_min),
            int(r.size))


def tradeable_minutes_per_year(data_dir, stem):
    """Minutes the instrument actually quotes, annualised from the sample."""
    import numpy as np
    mid = _read(os.path.join(data_dir, f"{stem}_mid_15m.csv"))
    span_days = (mid.index[-1] - mid.index[0]).total_seconds() / 86400.0
    if span_days <= 0:
        return None
    minutes = len(mid) * BAR_SECONDS / 60.0
    return float(minutes * 365.25 / span_days)


# ----------------------------------------------------------------- the sums

def h_min(s_rel, sigma_1m, threshold):
    """Shortest hold, in minutes, at which cost/vol <= threshold."""
    if sigma_1m is None or sigma_1m <= 0:
        return float("inf")
    return (s_rel / (threshold * sigma_1m)) ** 2


def cost_over_vol(s_rel, sigma_1m, hold_min):
    return s_rel / (sigma_1m * math.sqrt(hold_min))


def cost_sharpe(s_rel, sigma_1m, hold_min, trades_yr):
    """Annualised Sharpe handed to the broker at this trading frequency.

        net SR = (g - c)/s * sqrt(T)  =  gross SR - (c/s) * sqrt(T)

    so the drag is (cost per trade / per-trade return sd) * sqrt(trades/yr),
    and `cost per trade / per-trade sd` IS cost/vol at the hold. Hence:

        drag = cost/vol(H) * sqrt(trades per year)

    ---------------------------------------------------------------------
    CORRECTED 2026-08-17, before any backtest was run.

    A previous version divided the annual cost by the ASSET's annualised
    session volatility:  drag = trades/yr * spread / ann_vol. That is only
    right for a strategy in the market every minute of the session. A bot at
    4 round trips/day holding 30 minutes is exposed ~2 hours of 7, so its own
    volatility is far below the session's, and dividing by the session figure
    understated the drag by ~1.9x.

    It also made the drag scale LINEARLY in trade count. It does not: more
    trades buy more cost and more exposure together, so the drag grows as
    sqrt(N). silver15's FINDINGS.md states exactly this -- "cost drag adds on
    top and scales as sqrt(trades per year)" -- and the first version of this
    file had it right before an edit broke it.
    ---------------------------------------------------------------------
    """
    return cost_over_vol(s_rel, sigma_1m, hold_min) * math.sqrt(trades_yr)


def detect_bar(years):
    return K_SIGMA / math.sqrt(years)


# ----------------------------------------------------------------- self-test

def self_test():
    """Every gate below is shown to FAIL on a case constructed to fail it.

    silver15's dominant bug, seen five times, was a gate that could not fire.
    A control that only ever passes has validated nothing.
    """
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" +
              (f"   {detail}" if detail else ""))

    print(f"interval_budget.py v{VERSION} self-test\n")

    print("closed form")
    # sigma_1m = 1e-4, spread = 1e-4 -> cost/vol = 1.0 at H=1, 0.15 at H=44.4
    s, sig = 1e-4, 1e-4
    check("cost/vol is 1.0 at H=1 when spread == 1-minute vol",
          abs(cost_over_vol(s, sig, 1) - 1.0) < 1e-12)
    check("cost/vol halves when H quadruples",
          abs(cost_over_vol(s, sig, 4) - 0.5) < 1e-12)
    hm = h_min(s, sig, COMFORT)
    check("H_min inverts cost/vol exactly",
          abs(cost_over_vol(s, sig, hm) - COMFORT) < 1e-12, f"H_min={hm:.1f}m")

    print("\ngates can fail")
    cheap = h_min(1e-6, 1e-4, COMFORT)       # very tight spread
    dear = h_min(1e-2, 1e-4, COMFORT)        # very wide spread
    check("a cheap instrument clears the comfort bar inside 5 minutes",
          cheap <= 5, f"H_min={cheap:.3f}m")
    check("an expensive instrument does NOT -- the gate fires",
          dear > 5, f"H_min={dear:,.0f}m")
    check("zero spread gives H_min of zero", h_min(0.0, 1e-4, COMFORT) == 0.0)
    check("zero vol is rejected rather than dividing by zero",
          h_min(1e-4, 0.0, COMFORT) == float("inf"))

    print("\nmonotonicity")
    check("looser threshold never requires a longer hold",
          h_min(s, sig, CEILING) < h_min(s, sig, COMFORT))
    check("cost Sharpe falls when trading less often",
          cost_sharpe(s, sig, 30, 260) < cost_sharpe(s, sig, 30, 6240))
    check("cost Sharpe rises with a wider spread",
          cost_sharpe(2 * s, sig, 30, 260) > cost_sharpe(s, sig, 30, 260))
    check("cost Sharpe scales as SQRT of trade count, not linearly",
          abs(cost_sharpe(s, sig, 30, 4 * 252) /
              cost_sharpe(s, sig, 30, 252) - 2.0) < 1e-9,
          "4x the trades is 2x the drag")
    check("drag is cost/vol times sqrt(trades)",
          abs(cost_sharpe(s, sig, 30, 900)
              - cost_over_vol(s, sig, 30) * 30) < 1e-12)
    check("a longer hold lowers the drag at equal trade count",
          cost_sharpe(s, sig, 120, 500) < cost_sharpe(s, sig, 30, 500))

    print("\ndetectability")
    check("the bar loosens with more history",
          detect_bar(20) < detect_bar(2))
    check("2 sigma on 20.4 years reproduces silver15's 0.44",
          abs(detect_bar(20.4) - 0.443) < 0.002, f"{detect_bar(20.4):.3f}")

    print("\nvol estimator")
    import numpy as np
    rng = np.random.default_rng(0)
    r = rng.normal(0, 0.001, 200_000)
    mad = 1.4826 * float(np.median(np.abs(r - np.median(r))))
    check("MAD recovers a known sd within 1%", abs(mad / 0.001 - 1) < 0.01,
          f"{mad:.6f}")
    r2 = r.copy()
    r2[:200] = 0.5                       # 0.1% of bars are 500-sigma news
    mad2 = 1.4826 * float(np.median(np.abs(r2 - np.median(r2))))
    check("MAD is unmoved by outliers where plain sd is not",
          abs(mad2 / mad - 1) < 0.01 and np.std(r2, ddof=1) / np.std(r, ddof=1) > 5,
          f"sd inflated {np.std(r2, ddof=1)/np.std(r, ddof=1):.1f}x")

    print(f"\n{'ALL PASS' if ok else 'FAILURES ABOVE'}")
    return 0 if ok else 1


# ----------------------------------------------------------------- report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--per-day", default="1,4,12,48",
                    help="round trips per trading day to price")
    ap.add_argument("--hold", type=float, default=30.0,
                    help="holding period in MINUTES, for the drag table")
    ap.add_argument("--years", type=float, default=2.0,
                    help="history available at 1m granularity, for the "
                         "detectability bar")
    a = ap.parse_args()

    if a.self_test:
        sys.exit(self_test())

    import numpy as np

    print(f"interval_budget.py v{VERSION}   NO RETURNS COMPUTED")
    print(f"  measured OANDA quotes; thresholds cost/vol <= {COMFORT} "
          f"(comfort) and <= {CEILING} (ceiling)\n")

    per_day = [float(x) for x in a.per_day.split(",")]
    rows = []
    for stem in instruments(a.data):
        s_med, s_p90, n_q = spread_rel(a.data, stem)
        sig, sig_plain, n_r = vol_per_minute(a.data, stem)
        if s_med is None or sig is None:
            continue
        mins = tradeable_minutes_per_year(a.data, stem)
        rows.append(dict(
            stem=stem, s=s_med, s90=s_p90, sig=sig, sig_plain=sig_plain,
            n_q=n_q, n_r=n_r, mins=mins,
            h15=h_min(s_med, sig, COMFORT), h35=h_min(s_med, sig, CEILING),
            ann_vol=sig * math.sqrt(mins),
        ))
    rows.sort(key=lambda r: r["h15"])

    print(f"{'instrument':>11}{'spread':>10}{'vol/min':>10}{'ann vol':>9}"
          f"{'cost/vol @1m':>14}{'@5m':>8}{'H_min .35':>11}{'H_min .15':>11}")
    print("=" * 84)
    for r in rows:
        print(f"{r['stem']:>11}{r['s']*1e4:>9.2f}bp{r['sig']*1e4:>9.2f}bp"
              f"{r['ann_vol']*100:>8.1f}%"
              f"{cost_over_vol(r['s'], r['sig'], 1):>14.2f}"
              f"{cost_over_vol(r['s'], r['sig'], 5):>8.2f}"
              f"{r['h35']:>10,.0f}m{r['h15']:>10,.0f}m")

    print(f"\n  spread and vol are medians over {rows[0]['n_q']:,} quoted "
          f"M15 bars.")
    print("  H_min is the SHORTEST hold at which the spread is not dominant.")

    print(f"\n\nrequired GROSS annualised Sharpe, by trading frequency"
          f"  (hold {a.hold:g}m)")
    print(f"  (cost drag + {K_SIGMA:.0f}-sigma detectability on "
          f"{a.years:g} years = {detect_bar(a.years):.2f})")
    print("=" * 84)
    hdr = "".join(f"{d:>11,.0f}/day" for d in per_day)
    print(f"{'instrument':>11}{hdr}")
    print("-" * 84)
    bar = detect_bar(a.years)
    for r in rows:
        line = f"{r['stem']:>11}"
        for d in per_day:
            cs = cost_sharpe(r["s"], r["sig"], a.hold, d * 252)
            line += f"{cs + bar:>15.1f}"
        print(line)
    print("\n  For scale: a Sharpe of 1.0 is a good systematic strategy and "
          "2.0 is exceptional.")
    print("  A 1-5 minute BAR does not force a 1-5 minute HOLD, so read the "
          "column\n  matching how often the bot would actually round-trip.")

    print("\n\nverdict at 1-5 minute holds")
    print("=" * 84)
    viable = [r for r in rows if r["h15"] <= 5]
    reach = [r for r in rows if r["h35"] <= 5]
    print(f"  instruments where a 5-minute hold is COMFORTABLE "
          f"(cost/vol <= {COMFORT}):  {len(viable)} of {len(rows)}")
    print(f"  instruments where a 5-minute hold is even REACHABLE "
          f"(cost/vol <= {CEILING}):  {len(reach)} of {len(rows)}")
    best = rows[0]
    print(f"\n  cheapest instrument on this measure: {best['stem']}")
    print(f"    needs {best['h15']:,.0f} minutes "
          f"({best['h15']/60:,.1f} hours) to reach the comfort threshold,")
    print(f"    and  {best['h35']:,.0f} minutes "
          f"({best['h35']/60:,.1f} hours) to reach the ceiling.")


if __name__ == "__main__":
    main()
