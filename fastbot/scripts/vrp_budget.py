#!/usr/bin/env python3
"""Is the variance risk premium still there, and how big? MEASUREMENT ONLY.

WHY THIS EXISTS
---------------
ASSESSMENT.md put the variance risk premium at the top of the unexplored
space, on the grounds that it is a PREMIUM rather than a PREDICTION -- you are
paid to bear something (crash risk) rather than paid for being right.

Before any strategy, the same question this project always asks first: is the
thing there, how big is it, and has it changed? That is answerable from two
free series and needs no broker, no options chain and no strategy code.

    IV(t)  = VIX on day t / 100          the 30-day implied vol
    RV(t)  = annualised realised vol of SPX over the NEXT 21 trading days
    VRP    = IV - RV        (vol points, intuitive)
           = IV^2 - RV^2    (variance points, the actual swap payoff)

VIX^2 is approximately the fair strike of a 30-day variance swap, so a seller
of variance receives IV^2 - RV^2. Measuring that distribution measures the
strategy's return distribution WITHOUT simulating a single option.

NO STRATEGY IS BACKTESTED HERE. No position sizing, no entry rule, no exit.
The output is the premium itself and its tail.

THE FORWARD LOOK IS THE POINT, NOT A BUG. RV is measured over the month AFTER
t because that is the month the seller is exposed to. The decision is made at
t using IV alone.

    python vrp_budget.py --self-test
    python vrp_budget.py                 # downloads VIX and SPX, needs network
"""

from __future__ import annotations

import argparse
import math
import os
import sys

VERSION = "1.0"
WINDOW = 21                 # trading days ~ 30 calendar days
ERAS = [(1990, 1999), (2000, 2009), (2010, 2017), (2018, 2026)]


def fetch():
    """VIX and SPX daily closes. Tries a couple of free sources."""
    import pandas as pd
    import urllib.request

    def get(url):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        return urllib.request.urlopen(req, timeout=60).read()

    import io
    vix = None
    for u in ("https://cdn.cboe.com/api/global/us_indices/daily_prices/"
              "VIX_History.csv",
              "https://stooq.com/q/d/l/?s=%5Evix&i=d"):
        try:
            d = pd.read_csv(io.BytesIO(get(u)))
            d.columns = [c.strip().upper() for c in d.columns]
            dt = "DATE"
            d[dt] = pd.to_datetime(d[dt])
            col = "CLOSE" if "CLOSE" in d.columns else d.columns[-1]
            vix = d.set_index(dt)[col].astype(float).sort_index()
            print(f"  VIX from {u.split('/')[2]}: {len(vix):,} rows "
                  f"{vix.index[0]:%Y-%m-%d} -> {vix.index[-1]:%Y-%m-%d}")
            break
        except Exception as e:                                  # noqa: BLE001
            print(f"  VIX source failed ({u.split('/')[2]}): "
                  f"{type(e).__name__}")
    spx = None
    # Stooq rate-limits and returns a plain-text error with no CSV columns,
    # which surfaced as a bare KeyError. Report what actually came back, and
    # try more than one source.
    for label, u in (("stooq ^spx", "https://stooq.com/q/d/l/?s=%5Espx&i=d"),
                     ("stooq spy.us",
                      "https://stooq.com/q/d/l/?s=spy.us&i=d")):
        try:
            raw = get(u)
            if b"," not in raw.split(b"\n")[0]:
                print(f"  SPX source {label} returned no CSV: "
                      f"{raw[:80].decode('utf-8','replace').strip()!r}")
                continue
            d = pd.read_csv(io.BytesIO(raw))
            d.columns = [c.strip().upper() for c in d.columns]
            if "DATE" not in d.columns or "CLOSE" not in d.columns:
                print(f"  SPX source {label} gave columns {list(d.columns)}")
                continue
            d["DATE"] = pd.to_datetime(d["DATE"])
            spx = d.set_index("DATE")["CLOSE"].astype(float).sort_index()
            print(f"  SPX from {label}: {len(spx):,} rows "
                  f"{spx.index[0]:%Y-%m-%d} -> {spx.index[-1]:%Y-%m-%d}")
            break
        except Exception as e:                                  # noqa: BLE001
            print(f"  SPX source {label} failed: {type(e).__name__}: {e}")

    if spx is None:
        try:
            import yfinance as yf
            h = yf.Ticker("^GSPC").history(period="max", auto_adjust=False)
            spx = h["Close"].astype(float)
            spx.index = pd.to_datetime(spx.index).tz_localize(None)
            print(f"  SPX from yfinance: {len(spx):,} rows "
                  f"{spx.index[0]:%Y-%m-%d} -> {spx.index[-1]:%Y-%m-%d}")
        except Exception as e:                                  # noqa: BLE001
            print(f"  yfinance unavailable: {type(e).__name__} "
                  f"(pip install yfinance)")
    if vix is None or spx is None:
        raise SystemExit(
            "\n  Could not download SPX. Three ways forward:\n"
            "    1. pip install yfinance   then rerun (easiest)\n"
            "    2. --spx-from-oanda       uses the spx500usd M5 file already\n"
            "       on disk: 2005-2026, covers 2008, 2018 and 2020\n"
            "    3. save the CSV by hand and pass --vix and --spx")
    return vix, spx


def fetch_vix_only():
    """VIX alone -- CBOE works reliably where the equity sources do not."""
    import io, urllib.request, pandas as pd
    u = ("https://cdn.cboe.com/api/global/us_indices/daily_prices/"
         "VIX_History.csv")
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    d = pd.read_csv(io.BytesIO(urllib.request.urlopen(req, timeout=60).read()))
    d.columns = [c.strip().upper() for c in d.columns]
    d["DATE"] = pd.to_datetime(d["DATE"])
    v = d.set_index("DATE")["CLOSE"].astype(float).sort_index()
    print(f"  VIX from cboe: {len(v):,} rows {v.index[0]:%Y-%m-%d} -> "
          f"{v.index[-1]:%Y-%m-%d}")
    return v, None


def oanda_daily(data_dir, stem="spx500usd"):
    """Daily closes from the M5 CFD file already on disk.

    Uses the last bar at or before 16:00 America/New_York, i.e. the cash
    close, so realised vol is measured on the same clock the index uses.
    Starts 2005 rather than 1990, but covers 2008, 2018 and 2020 -- which is
    where the whole question about this premium lives.

    The CFD is not the index. It tracks it closely enough for a REALISED
    VOLATILITY estimate, which is all this needs, and the difference is
    recorded rather than assumed away.
    """
    import pandas as pd
    p = os.path.join(data_dir, f"{stem}_mid_5m.csv")
    if not os.path.exists(p):
        raise SystemExit(f"  {os.path.basename(p)} not found in {data_dir}")
    d = pd.read_csv(p, usecols=[0, 4])
    d.columns = ["t", "close"]
    t = pd.to_datetime(d["t"], utc=True).dt.tz_convert("America/New_York")
    keep = (t.dt.hour < 16) & (t.dt.hour >= 9)
    d, t = d[keep], t[keep]
    out = (d.assign(day=t.dt.normalize().dt.tz_localize(None))
             .groupby("day")["close"].last().sort_index())
    print(f"  SPX proxy from OANDA spx500usd M5: {len(out):,} daily closes "
          f"{out.index[0]:%Y-%m-%d} -> {out.index[-1]:%Y-%m-%d}")
    return out


def measure(vix, spx, window=WINDOW):
    """Forward realised vol and the premium. No strategy, no sizing."""
    import numpy as np, pandas as pd

    idx = vix.index.intersection(spx.index)
    vix, spx = vix.loc[idx].sort_index(), spx.loc[idx].sort_index()
    r = np.log(spx).diff()

    # realised vol over the NEXT `window` days, annualised.
    # shift(-window) so the value at t covers t+1 .. t+window.
    fwd = (r.rolling(window).std().shift(-window) * math.sqrt(252))
    iv = vix / 100.0

    df = pd.DataFrame({"iv": iv, "rv": fwd}).dropna()
    df["vrp_vol"] = df["iv"] - df["rv"]
    df["vrp_var"] = df["iv"] ** 2 - df["rv"] ** 2
    return df


def monthly(df):
    """One non-overlapping observation per month -- overlapping daily windows
    would inflate every t-statistic by ~sqrt(21)."""
    return df.resample("ME").first().dropna()


def report(df):
    import numpy as np
    m = monthly(df)
    print(f"\n  non-overlapping monthly observations: {len(m):,}  "
          f"({m.index[0]:%Y-%m} -> {m.index[-1]:%Y-%m})")

    v = m["vrp_vol"].to_numpy()
    q = m["vrp_var"].to_numpy()
    sh = float(np.mean(q) / np.std(q, ddof=1) * math.sqrt(12))
    print(f"\n  VRP in VOL points   mean {np.mean(v)*100:+.2f}  "
          f"median {np.median(v)*100:+.2f}  positive "
          f"{float((v>0).mean())*100:.0f}% of months")
    print(f"  VRP in VAR points   mean {np.mean(q):+.5f}  "
          f"sd {np.std(q, ddof=1):.5f}")
    print(f"  implied Sharpe of selling variance, unhedged, unlevered: "
          f"{sh:+.2f}")
    print(f"  skew {float(((q-np.mean(q))**3).mean()/np.std(q)**3):+.2f}   "
          f"worst month {np.min(q):+.5f} "
          f"({m['vrp_var'].idxmin():%Y-%m})")
    print(f"  worst month is {abs(np.min(q))/np.std(q, ddof=1):.1f} sd  "
          f"-- a symmetric distribution would put that at ~3")

    print(f"\n  by era (has it compressed?)")
    print(f"  {'era':>12}{'n':>6}{'mean vol pts':>14}{'% positive':>12}"
          f"{'Sharpe':>9}{'worst':>10}")
    print("  " + "-" * 63)
    for a, b in ERAS:
        s = m[(m.index.year >= a) & (m.index.year <= b)]
        if len(s) < 12:
            continue
        qq = s["vrp_var"].to_numpy()
        print(f"  {f'{a}-{b}':>12}{len(s):>6}"
              f"{s['vrp_vol'].mean()*100:>13.2f}"
              f"{float((s['vrp_vol']>0).mean())*100:>11.0f}%"
              f"{float(np.mean(qq)/np.std(qq, ddof=1)*math.sqrt(12)):>9.2f}"
              f"{np.min(qq):>10.4f}")

    print(f"\n  the five worst months -- this is what you are being paid for")
    for d, row in m.nsmallest(5, "vrp_var").iterrows():
        print(f"    {d:%Y-%m}   IV {row['iv']*100:5.1f}  "
              f"RV {row['rv']*100:5.1f}  "
              f"VRP {row['vrp_vol']*100:+6.1f} vol pts")
    return m


def self_test():
    import numpy as np, pandas as pd
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" +
              (f"   {detail}" if detail else ""))

    print(f"vrp_budget.py v{VERSION} self-test\n")
    n = 4000
    dates = pd.bdate_range("2000-01-03", periods=n)
    rng = np.random.default_rng(4)

    print("realised vol is recovered from a known input")
    true_vol = 0.20
    r = rng.normal(0, true_vol / math.sqrt(252), n)
    spx = pd.Series(100 * np.exp(np.cumsum(r)), index=dates)
    vix = pd.Series(true_vol * 100, index=dates)
    df = measure(vix, spx)
    check("forward RV recovers the planted 20% within 3%",
          abs(df["rv"].mean() / true_vol - 1) < 0.03,
          f"{df['rv'].mean()*100:.2f}%")
    check("with IV == RV the premium is ~zero",
          abs(df["vrp_vol"].mean()) < 0.01,
          f"{df['vrp_vol'].mean()*100:+.2f} vol pts")

    print("\na planted premium is recovered, and the gate can fail")
    vix2 = pd.Series((true_vol + 0.04) * 100, index=dates)
    d2 = measure(vix2, spx)
    check("planting +4 vol points recovers +4",
          abs(d2["vrp_vol"].mean() - 0.04) < 0.005,
          f"{d2['vrp_vol'].mean()*100:+.2f}")
    check("and the zero-premium case did NOT show one -- discriminates",
          abs(df["vrp_vol"].mean()) < 0.5 * abs(d2["vrp_vol"].mean()))
    vix3 = pd.Series((true_vol - 0.04) * 100, index=dates)
    check("a NEGATIVE premium is reported as negative",
          measure(vix3, spx)["vrp_vol"].mean() < -0.03)

    print("\nthe forward window is genuinely forward")
    # spike realised vol in the second half only; the premium must go negative
    # BEFORE the spike, never after it
    r2 = r.copy()
    r2[n // 2:] *= 4
    spx2 = pd.Series(100 * np.exp(np.cumsum(r2)), index=dates)
    d3 = measure(vix, spx2)
    pre = d3[d3.index < dates[n // 2 - WINDOW - 5]]["vrp_vol"].mean()
    at = d3[(d3.index >= dates[n // 2 - WINDOW])
            & (d3.index < dates[n // 2])]["vrp_vol"].mean()
    check("the premium collapses BEFORE the vol spike, not after",
          at < pre - 0.05, f"before {pre*100:+.1f}, at the edge {at*100:+.1f}")

    print("\nmonthly sampling removes the overlap inflation")
    m = monthly(d2)
    check("monthly gives ~1/21 of the daily observations",
          0.02 < len(m) / len(d2) < 0.09, f"{len(m)}/{len(d2)}")
    t_daily = (d2["vrp_var"].mean() / d2["vrp_var"].std(ddof=1)
               * math.sqrt(len(d2)))
    t_month = (m["vrp_var"].mean() / m["vrp_var"].std(ddof=1)
               * math.sqrt(len(m)))
    check("and it materially lowers the t-statistic, as it must",
          t_month < t_daily * 0.5,
          f"daily t {t_daily:.1f} -> monthly t {t_month:.1f}")

    print("\nno strategy is simulated")
    # Grepping the source for forbidden words matches the grep itself -- that
    # bug has now appeared three times in this project (patterns.py,
    # exit_shape.py, here). Inspect the module NAMESPACE instead; it cannot
    # match its own test.
    import vrp_budget as _self
    names = [x for x in dir(_self) if not x.startswith("_")]
    banned = [x for x in names if any(w in x.lower() for w in
              ("position", "size", "equity", "pnl", "trade", "signal"))]
    check("no sizing / P&L / signal function in the module", banned == [],
          f"{banned}")
    cols = set(measure(vix2, spx).columns)
    check("output columns are a premium, not a return series",
          cols == {"iv", "rv", "vrp_vol", "vrp_var"}, f"{sorted(cols)}")

    print(f"\n{'ALL PASS' if ok else 'FAILURES ABOVE'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vix", help="local VIX_History.csv if no network")
    ap.add_argument("--spx", help="local SPX daily csv if no network")
    ap.add_argument("--window", type=int, default=WINDOW)
    ap.add_argument("--spx-from-oanda", action="store_true",
                    help="build daily SPX closes from the spx500usd M5 file "
                         "already on disk -- no download, 2005-2026")
    ap.add_argument("--data-dir", default=os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "data")))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    import pandas as pd
    print(f"vrp_budget.py v{VERSION}   MEASUREMENT ONLY, NO STRATEGY\n")
    if a.vix and a.spx:
        def rd(p):
            d = pd.read_csv(p)
            d.columns = [c.strip().upper() for c in d.columns]
            dcol = [c for c in d.columns if "DATE" in c][0]
            d[dcol] = pd.to_datetime(d[dcol])
            ccol = "CLOSE" if "CLOSE" in d.columns else d.columns[-1]
            return d.set_index(dcol)[ccol].astype(float).sort_index()
        vix, spx = rd(a.vix), rd(a.spx)
        print(f"  local files: VIX {len(vix):,} rows, SPX {len(spx):,} rows")
    elif a.spx_from_oanda:
        vix, _ = fetch_vix_only()
        spx = oanda_daily(a.data_dir)
    else:
        vix, spx = fetch()

    df = measure(vix, spx, a.window)
    report(df)

    print("\n  WHAT THIS DOES AND DOES NOT SAY")
    print("    Does: whether the premium exists, its size, and its tail.")
    print("    Does NOT: that you can harvest it. Harvesting needs listed")
    print("      options, which OANDA and Kraken do not offer, and the")
    print("      realised return is below this figure after bid/ask on the")
    print("      options, margin drag and the cost of any tail hedge.")
    print("    A negative skew is not a flaw in the measurement. It is the")
    print("      product. You are selling insurance.")


if __name__ == "__main__":
    main()
