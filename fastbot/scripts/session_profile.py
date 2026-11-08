#!/usr/bin/env python3
"""Cost/vol by hour of day. The 24-hour median hides the only viable window.

WHY THIS EXISTS
---------------
interval_budget.py reports one cost/vol number per instrument, taken over all
quoted hours. For an instrument that trades 24h but only has a *cash session*
-- every index CFD here -- that median is a blend of two different markets:

    cash session      tight spread, high volatility   -> cost/vol LOW
    overnight         wide spread, low volatility     -> cost/vol HIGH

A bot on a 1-5 minute bar does not have to trade both. If the viable window is
three hours a day, that is a constraint on the strategy, not a reason to
reject the instrument -- but it has to be measured before it can be used, and
a 24-hour average will systematically understate the best instrument and
overstate the worst.

Both terms move together and in the same direction, so the effect on the ratio
compounds. That makes this the single highest-leverage cut in the budget.

NO RETURNS ARE COMPUTED HERE.

    python session_profile.py --data ../data --instruments nas100usd,spx500usd
    python session_profile.py --self-test
"""

from __future__ import annotations

import argparse
import math
import os
import sys

VERSION = "1.0"
BAR_SECONDS = 900
COMFORT, CEILING = 0.15, 0.35
MIN_BARS_PER_HOUR = 40          # below this the hourly estimate is not trusted


def _read(path):
    import pandas as pd
    d = pd.read_csv(path)
    t = d.columns[0]
    d[t] = pd.to_datetime(d[t], utc=True)
    return d.set_index(t).sort_index()


def hourly(data_dir, stem):
    """Per-UTC-hour spread, per-minute vol, and their ratio.

    Volatility uses only bar pairs that are BOTH consecutive and inside the
    same hour, so a session-open gap is never counted as a tradeable move.
    """
    import numpy as np, pandas as pd

    mid = _read(os.path.join(data_dir, f"{stem}_mid_15m.csv"))["close"]
    bid = _read(os.path.join(data_dir, f"{stem}_bid_15m.csv"))["close"]
    ask = _read(os.path.join(data_dir, f"{stem}_ask_15m.csv"))["close"]

    idx = mid.index.intersection(bid.index).intersection(ask.index)
    mid, bid, ask = mid.loc[idx], bid.loc[idx], ask.loc[idx]

    m = mid.to_numpy(float)
    rel = (ask.to_numpy(float) - bid.to_numpy(float)) / m
    t = idx.to_numpy()
    hr = idx.hour.to_numpy()

    dt = (t[1:] - t[:-1]) / np.timedelta64(1, "s")
    consec = (dt == BAR_SECONDS) & (m[:-1] > 0) & (m[1:] > 0)
    r = np.where(consec, np.log(np.maximum(m[1:], 1e-12) /
                                np.maximum(m[:-1], 1e-12)), np.nan)
    r_hr = hr[1:]                      # attribute the return to its END bar

    rows = []
    for h in range(24):
        sm = rel[(hr == h) & np.isfinite(rel) & (rel >= 0)]
        rm = r[(r_hr == h) & np.isfinite(r)]
        if sm.size < MIN_BARS_PER_HOUR or rm.size < MIN_BARS_PER_HOUR:
            continue
        s_med = float(np.median(sm))
        s_p90 = float(np.percentile(sm, 90))
        mad = float(np.median(np.abs(rm - np.median(rm))))
        sd15 = 1.4826 * mad
        sig1 = sd15 / math.sqrt(15.0)
        if sig1 <= 0:
            continue
        rows.append(dict(hour=h, n=int(rm.size), s=s_med, s90=s_p90, sig=sig1,
                         cv1=s_med / sig1,
                         cv5=s_med / (sig1 * math.sqrt(5)),
                         cv5_p90=s_p90 / (sig1 * math.sqrt(5)),
                         hmin15=(s_med / (COMFORT * sig1)) ** 2,
                         hmin35=(s_med / (CEILING * sig1)) ** 2))
    return pd.DataFrame(rows)


def self_test():
    """Each gate is shown failing on a case built to fail it."""
    import numpy as np, pandas as pd
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" +
              (f"   {detail}" if detail else ""))

    print(f"session_profile.py v{VERSION} self-test\n")

    tmp = "/tmp/_sp_test"
    os.makedirs(tmp, exist_ok=True)
    rng = np.random.default_rng(7)

    # Synthetic instrument with a KNOWN two-regime day:
    #   hours 13-20 -> vol 4x higher, spread 2x tighter  (cost/vol 8x better)
    n = 24 * 4 * 120                       # 120 days of M15
    t = pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC")
    live = (t.hour >= 13) & (t.hour < 21)
    sd = np.where(live, 4e-4, 1e-4)
    px = 100 * np.exp(np.cumsum(rng.normal(0, sd)))
    half = np.where(live, 100 * 0.5e-4 / 2, 100 * 1.0e-4 / 2)
    for name, arr in (("mid", px), ("bid", px - half), ("ask", px + half)):
        pd.DataFrame({"time": t, "open": arr, "high": arr, "low": arr,
                      "close": arr, "volume": 1.0}).to_csv(
            os.path.join(tmp, f"synth_{name}_15m.csv"), index=False)

    d = hourly(tmp, "synth").set_index("hour")
    print("recovers a planted two-regime day")
    check("all 24 hours estimated", len(d) == 24, f"{len(d)}")
    lo = d.loc[[14, 15, 16], "cv1"].mean()
    hi = d.loc[[2, 3, 4], "cv1"].mean()
    check("session hours are cheaper than overnight", lo < hi,
          f"{lo:.2f} vs {hi:.2f}")
    check("the planted ratio is ~8x, recovered within 15%",
          abs((hi / lo) / 8.0 - 1) < 0.15, f"recovered {hi/lo:.2f}x")
    check("planted session vol recovered within 10%",
          abs(d.loc[15, "sig"] / (4e-4 / math.sqrt(15)) - 1) < 0.10,
          f"{d.loc[15,'sig']*1e4:.3f}bp")
    check("planted session spread recovered within 5%",
          abs(d.loc[15, "s"] / 0.5e-4 - 1) < 0.05, f"{d.loc[15,'s']*1e4:.3f}bp")

    print("\nthe gate can fail")
    flat = 100 * np.exp(np.cumsum(rng.normal(0, 1e-4, n)))
    hf = np.full(n, 100 * 1.0e-4 / 2)
    for name, arr in (("mid", flat), ("bid", flat - hf), ("ask", flat + hf)):
        pd.DataFrame({"time": t, "open": arr, "high": arr, "low": arr,
                      "close": arr, "volume": 1.0}).to_csv(
            os.path.join(tmp, f"flat_{name}_15m.csv"), index=False)
    f = hourly(tmp, "flat").set_index("hour")
    spread_of_ratio = f["cv1"].max() / f["cv1"].min()
    check("a genuinely flat day shows NO session structure",
          spread_of_ratio < 1.4, f"max/min = {spread_of_ratio:.2f}")
    check("and the two-regime case does -- so the test discriminates",
          (d["cv1"].max() / d["cv1"].min()) > 4,
          f"max/min = {d['cv1'].max()/d['cv1'].min():.2f}")

    print("\nsparse hours are dropped, not guessed")
    sparse = t[(t.hour != 5) | (np.arange(n) % 97 == 0)]
    arr = 100 * np.exp(np.cumsum(rng.normal(0, 1e-4, len(sparse))))
    hs = np.full(len(sparse), 100 * 1.0e-4 / 2)
    for name, v in (("mid", arr), ("bid", arr - hs), ("ask", arr + hs)):
        pd.DataFrame({"time": sparse, "open": v, "high": v, "low": v,
                      "close": v, "volume": 1.0}).to_csv(
            os.path.join(tmp, f"sparse_{name}_15m.csv"), index=False)
    sp = hourly(tmp, "sparse")
    check("an hour with too few bars is omitted",
          5 not in set(sp["hour"]), f"hours kept: {len(sp)}")

    print(f"\n{'ALL PASS' if ok else 'FAILURES ABOVE'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data")
    ap.add_argument("--instruments",
                    default="nas100usd,spx500usd,us30usd,xauusd,de30eur,"
                            "us2000usd,eurusd")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        sys.exit(self_test())

    print(f"session_profile.py v{VERSION}   NO RETURNS COMPUTED")
    print("  cost/vol by UTC hour. Lower is better; the strategy only has to "
          "trade\n  the hours that clear the bar.\n")

    best_windows = {}
    for stem in a.instruments.split(","):
        d = hourly(a.data, stem)
        if d.empty:
            print(f"{stem}: no data\n")
            continue
        print(f"{stem}")
        print(f"{'UTC':>5}{'spread':>10}{'p90':>9}{'vol/min':>10}"
              f"{'cost/vol@1m':>13}{'@5m':>8}{'@5m p90':>10}"
              f"{'H_min .15':>11}   ")
        print("  " + "-" * 74)
        for _, r in d.iterrows():
            flag = ("  <-- comfortable at 5m" if r.cv5 <= COMFORT else
                    "  <-- reachable at 5m" if r.cv5 <= CEILING else "")
            print(f"{int(r.hour):>5}{r.s*1e4:>9.2f}bp{r.s90*1e4:>8.2f}bp"
                  f"{r.sig*1e4:>9.2f}bp{r.cv1:>13.2f}{r.cv5:>8.2f}"
                  f"{r.cv5_p90:>10.2f}{r.hmin15:>10,.0f}m{flag}")
        good = d[d.cv5 <= CEILING]
        best = d.loc[d.cv5.idxmin()]
        best_windows[stem] = (len(good), best)
        print(f"  best hour {int(best.hour):02d}:00 UTC at cost/vol "
              f"{best.cv5:.2f} on a 5m hold; "
              f"{len(good)} of {len(d)} hours reachable\n")

    print("\nsummary: hours per day where a 5-minute hold is at least "
          "reachable")
    print("=" * 78)
    for stem, (n_good, best) in sorted(best_windows.items(),
                                       key=lambda kv: -kv[1][0]):
        print(f"{stem:>11}{n_good:>4} h/day    best {int(best.hour):02d}:00 "
              f"UTC  cost/vol@5m {best.cv5:.2f}  "
              f"H_min(comfort) {best.hmin15:,.0f}m")

    # ------------------------------------------------------------------
    # The number that actually decides the project: restricted to the hours
    # that clear the COMFORT bar, what gross Sharpe must the signal produce?
    # ------------------------------------------------------------------
    import numpy as np
    print("\n\nrequired GROSS annualised Sharpe INSIDE the comfortable window")
    print("  (cost drag only -- add the detectability bar separately)")
    print("=" * 78)
    print(f"{'instrument':>11}{'window UTC':>14}{'h/day':>7}{'ann vol':>9}"
          f"{'1/day':>8}{'4/day':>8}{'12/day':>8}{'48/day':>8}")
    print("-" * 78)
    for stem in a.instruments.split(","):
        d = hourly(a.data, stem)
        if d.empty:
            continue
        good = d[d.cv5 <= COMFORT]
        if good.empty:
            print(f"{stem:>11}{'none':>14}   -- no hour clears the comfort bar")
            continue
        hrs = sorted(int(h) for h in good.hour)
        h_day = len(hrs)
        s_ses = float(np.median(good.s))
        sig_ses = float(np.median(good.sig))
        mins_day = h_day * 60
        days_yr = 252.0
        ann_vol = sig_ses * math.sqrt(mins_day * days_yr)
        cells = "".join(
            f"{(d_ * days_yr * s_ses / ann_vol):>8.2f}"
            for d_ in (1, 4, 12, 48))
        # label contiguous runs honestly -- the comfortable hours are not
        # always one block, and printing "00-20" for {0,12,13..19} would lie
        runs, start = [], hrs[0]
        for i in range(1, len(hrs) + 1):
            if i == len(hrs) or hrs[i] != hrs[i - 1] + 1:
                runs.append(f"{start:02d}-{hrs[i-1]+1:02d}")
                if i < len(hrs):
                    start = hrs[i]
        label = ",".join(runs)
        print(f"{stem:>11}{label:>14}{h_day:>7}"
              f"{ann_vol*100:>8.1f}%{cells}")
    print("\n  cost drag = round trips/yr x spread / annualised session vol.")
    print("  Add the detectability bar (2/sqrt(years)) to get the true "
          "hurdle.")
    print("  Below ~0.5 the cost is a detail; above ~1.5 it is the whole "
          "problem.")


if __name__ == "__main__":
    main()
