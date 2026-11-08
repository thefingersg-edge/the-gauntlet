#!/usr/bin/env python3
"""Cost/vol by YEAR and by HOUR, from the real M5 file. Replaces two guesses.

WHY THIS EXISTS
---------------
COST_BUDGET.md rested on two things it could not measure at the time:

  1. per-minute volatility, scaled from M15 by sqrt-of-time
  2. one spread, measured over nine weeks in 2026

The audit showed the second was a 2019-onwards number -- 8.5x wider in 2012 --
and that the median 5-minute bar range swings between 3.13bp and 10.68bp
across years, so volatility is no more constant than spread was. Both terms of
cost/vol therefore move, and they do NOT move together: 2020 and 2022 were
high-volatility years with a narrow spread, 2012-13 the reverse.

With bid, ask and mid M5 on disk, both terms are now measurable directly. This
file recomputes the budget's central number per year and per hour with no
scaling assumption anywhere.

    cost/vol(H) = measured spread / (measured per-minute vol * sqrt(H))

NO RETURNS ARE COMPUTED HERE.

    python regime_profile.py --instrument NAS100_USD --granularity M5
    python regime_profile.py --self-test
"""

from __future__ import annotations

import argparse
import math
import os
import sys

VERSION = "1.0"

PRICE_LABEL = {"B": "bid", "A": "ask", "M": "mid"}
TF_SUFFIX = {"M1": "1m", "M5": "5m", "M15": "15m"}
BAR_SECONDS = {"M1": 60, "M5": 300, "M15": 900}
COMFORT, CEILING = 0.15, 0.35
SESSION = (13, 20)              # overridden by --session; see main()
CHUNK = 400_000


def path_for(data_dir, instrument, price, gran):
    stem = instrument.replace("_", "").lower()
    return os.path.join(
        data_dir, f"{stem}_{PRICE_LABEL[price]}_{TF_SUFFIX[gran]}.csv")


def load(data_dir, instrument, gran, tz="UTC"):
    """Streamed join of bid/ask/mid into per-bar spread and log return.

    Returns arrays only, never a P&L. Volatility uses CONSECUTIVE in-window
    bars, so a session boundary is never counted as a move the bot could have
    traded -- the single most common way an intraday vol estimate is inflated.
    """
    import numpy as np, pandas as pd

    step = BAR_SECONDS[gran]
    pb, pa = (path_for(data_dir, instrument, s, gran) for s in ("B", "A"))
    for p in (pb, pa):
        if not os.path.exists(p):
            raise SystemExit(f"missing {os.path.basename(p)} -- pull it first")

    # Read in chunks for I/O, but concatenate BEFORE differencing. The first
    # version differenced per chunk and carried the boundary bar across, which
    # left the return array one element shorter than the spread array on the
    # first chunk only -- so every downstream boolean mask was silently
    # misaligned by one bar. It raised an IndexError here; on a different
    # chunk size it would have run and quietly shifted every measurement.
    tt, mm, ss = [], [], []
    itb = pd.read_csv(pb, usecols=[0, 4], chunksize=CHUNK)
    ita = pd.read_csv(pa, usecols=[0, 4], chunksize=CHUNK)
    for cb, ca in zip(itb, ita):
        cb.columns, ca.columns = ["t", "c"], ["t", "c"]
        j = cb.merge(ca, on="t", suffixes=("_b", "_a"))
        if j.empty:
            continue
        t = pd.to_datetime(j["t"], utc=True)
        b, k = j["c_b"].to_numpy(float), j["c_a"].to_numpy(float)
        mid = 0.5 * (b + k)
        ok = (mid > 0) & np.isfinite(mid) & (k >= b)
        if not ok.any():
            continue
        tt.append(t[ok].to_numpy())
        mm.append(mid[ok])
        ss.append((k[ok] - b[ok]) / mid[ok])

    if not tt:
        raise SystemExit("no aligned bid/ask bars")

    t = np.concatenate(tt)
    mid = np.concatenate(mm)
    spread = np.concatenate(ss)
    order = np.argsort(t, kind="stable")
    t, mid, spread = t[order], mid[order], spread[order]

    # ret[i] is the return INTO bar i, defined only when bar i-1 is the
    # immediately preceding bar on the grid. Same length as everything else.
    ret = np.full(mid.shape, np.nan)
    dt = (t[1:] - t[:-1]) / np.timedelta64(1, "s")
    good = dt == step
    ret[1:][good] = np.log(mid[1:][good] / mid[:-1][good])

    ts = pd.DatetimeIndex(t)
    if tz and tz.upper() != "UTC":
        # Bucket by EXCHANGE-LOCAL hour, not UTC.
        #
        # The US cash session moves by one hour in UTC terms twice a year, so
        # a UTC hour bucket at the session edge blends in-session with
        # out-of-session bars. On this data that showed up as 13:00 UTC
        # reading 1.07bp against 0.44bp at 14:00 -- not a real cost gradient,
        # just DST averaging. GOLD_V6_OOS.md hit the same thing from the
        # other direction: "TradingView's chart grid does not shift on US DST
        # the way the OANDA session does". Same trap, different project.
        ts = ts.tz_convert(tz)
    assert len(spread) == len(ret) == len(mid) == len(ts)
    return spread, ret, ts.hour.to_numpy(), ts.year.to_numpy()


def robust_sd(x):
    import numpy as np
    x = x[np.isfinite(x)]
    if x.size < 200:
        return float("nan")
    return 1.4826 * float(np.median(np.abs(x - np.median(x))))


def by_year(spread, ret, hrs, yrs, gran):
    import numpy as np
    step_min = BAR_SECONDS[gran] / 60.0
    ses = (hrs >= SESSION[0]) & (hrs < SESSION[1])
    out = []
    for y in sorted(set(int(v) for v in yrs)):
        m = (yrs == y) & ses
        if m.sum() < 500:
            continue
        s = float(np.median(spread[m]))
        sd_bar = robust_sd(ret[m])
        if not (sd_bar == sd_bar) or sd_bar <= 0 or s <= 0:
            out.append(dict(y=y, s=s, sig=float("nan"), dead=True))
            continue
        sig1 = sd_bar / math.sqrt(step_min)
        out.append(dict(
            y=y, s=s, sig=sig1, dead=False,
            cv5=s / (sig1 * math.sqrt(5)),
            cv15=s / (sig1 * math.sqrt(15)),
            cv60=s / (sig1 * math.sqrt(60)),
            hmin=(s / (COMFORT * sig1)) ** 2,
            ann=sig1 * math.sqrt((SESSION[1] - SESSION[0]) * 60 * 252)))
    return out


def report_years(rows, gran):
    print(f"\ncost/vol inside {SESSION[0]:02d}:00-{SESSION[1]:02d}:00 local, "
          f"measured from {gran} -- no scaling assumption")
    print(f"{'year':>6}{'spread':>10}{'vol/min':>10}{'ann vol':>9}"
          f"{'@5m':>8}{'@15m':>8}{'@60m':>8}{'H_min':>9}   verdict")
    print("-" * 82)
    ok_years = []
    for r in rows:
        if r["dead"]:
            print(f"{r['y']:>6}{r['s']*1e4:>9.2f}bp{'':>10}{'':>9}"
                  f"{'':>24}         no spread in feed")
            continue
        v = ("comfortable at 5m" if r["cv5"] <= COMFORT else
             "reachable at 5m" if r["cv5"] <= CEILING else
             "reachable at 15m" if r["cv15"] <= CEILING else
             "60m+ only" if r["cv60"] <= CEILING else "closed")
        if r["cv5"] <= CEILING:
            ok_years.append(r["y"])
        print(f"{r['y']:>6}{r['s']*1e4:>9.2f}bp{r['sig']*1e4:>9.2f}bp"
              f"{r['ann']*100:>8.1f}%{r['cv5']:>8.2f}{r['cv15']:>8.2f}"
              f"{r['cv60']:>8.2f}{r['hmin']:>8,.0f}m   {v}")
    return ok_years


def report_hours(spread, ret, hrs, yrs, gran, since):
    import numpy as np
    step_min = BAR_SECONDS[gran] / 60.0
    print(f"\ncost/vol by LOCAL hour, {since}-onwards only")
    print(f"{'UTC':>5}{'spread':>10}{'vol/min':>10}{'@5m':>8}{'@15m':>8}"
          f"{'@60m':>8}   ")
    print("-" * 56)
    good = []
    for h in range(24):
        m = (hrs == h) & (yrs >= since)
        if m.sum() < 500:
            continue
        s = float(np.median(spread[m]))
        sd = robust_sd(ret[m])
        if not (sd == sd) or sd <= 0 or s <= 0:
            continue
        sig = sd / math.sqrt(step_min)
        cv5 = s / (sig * math.sqrt(5))
        flag = ("  <-- comfortable" if cv5 <= COMFORT else
                "  <-- reachable" if cv5 <= CEILING else "")
        if cv5 <= COMFORT:
            good.append(h)
        print(f"{h:>5}{s*1e4:>9.2f}bp{sig*1e4:>9.2f}bp{cv5:>8.2f}"
              f"{s/(sig*math.sqrt(15)):>8.2f}{s/(sig*math.sqrt(60)):>8.2f}"
              f"{flag}")
    if good:
        runs, start = [], good[0]
        for i in range(1, len(good) + 1):
            if i == len(good) or good[i] != good[i - 1] + 1:
                runs.append(f"{start:02d}-{good[i-1]+1:02d}")
                if i < len(good):
                    start = good[i]
        print(f"\n  comfortable window: {','.join(runs)} local "
              f"({len(good)} hours/day)")
    return good


def self_test():
    import numpy as np, pandas as pd
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" +
              (f"   {detail}" if detail else ""))

    print(f"regime_profile.py v{VERSION} self-test\n")
    tmp = "/tmp/_regime_test"
    os.makedirs(tmp, exist_ok=True)
    rng = np.random.default_rng(11)

    # Two planted years, chosen so spread and vol move in OPPOSITE directions
    # -- the case that makes a single blended number misleading, and the case
    # the real NAS100 data actually shows.
    #   2015: spread 4bp, per-5m sd 4bp   -> cost/vol@5m = 4/(4/sqrt(5)*sqrt(5)) = 1.00
    #   2022: spread 1bp, per-5m sd 8bp   -> 0.125
    plan = {2015: (4e-4, 4e-4), 2022: (1e-4, 8e-4)}
    tb, ta = [], []
    for y, (sp, sd) in plan.items():
        n = 60_000
        t = pd.date_range(f"{y}-01-01", periods=n, freq="5min", tz="UTC")
        r = rng.normal(0, sd, n)
        mid = 10000 * np.exp(np.cumsum(r))
        half = mid * sp / 2
        tb.append(pd.DataFrame({"time": t, "open": mid, "high": mid,
                                "low": mid, "close": mid - half,
                                "volume": 1.0}))
        ta.append(pd.DataFrame({"time": t, "open": mid, "high": mid,
                                "low": mid, "close": mid + half,
                                "volume": 1.0}))
    pd.concat(tb).to_csv(os.path.join(tmp, "synusd_bid_5m.csv"), index=False)
    pd.concat(ta).to_csv(os.path.join(tmp, "synusd_ask_5m.csv"), index=False)

    sp, ret, hrs, yrs = load(tmp, "SYN_USD", "M5")
    rows = {r["y"]: r for r in by_year(sp, ret, hrs, yrs, "M5")}

    print("recovers both planted terms independently")
    check("2015 spread recovered as 4bp",
          abs(rows[2015]["s"] * 1e4 - 4.0) < 0.05,
          f"{rows[2015]['s']*1e4:.2f}bp")
    check("2022 spread recovered as 1bp",
          abs(rows[2022]["s"] * 1e4 - 1.0) < 0.05,
          f"{rows[2022]['s']*1e4:.2f}bp")
    check("2015 per-5m vol recovered as 4bp",
          abs(rows[2015]["sig"] * math.sqrt(5) * 1e4 - 4.0) < 0.2,
          f"{rows[2015]['sig']*math.sqrt(5)*1e4:.2f}bp")
    check("2022 per-5m vol recovered as 8bp",
          abs(rows[2022]["sig"] * math.sqrt(5) * 1e4 - 8.0) < 0.3,
          f"{rows[2022]['sig']*math.sqrt(5)*1e4:.2f}bp")

    print("\nthe ratio, which is the number that decides everything")
    check("2015 cost/vol@5m is ~1.00 -- closed",
          abs(rows[2015]["cv5"] - 1.0) < 0.06, f"{rows[2015]['cv5']:.3f}")
    check("2022 cost/vol@5m is ~0.125 -- comfortable",
          abs(rows[2022]["cv5"] - 0.125) < 0.01, f"{rows[2022]['cv5']:.3f}")
    check("the verdicts differ, so the gate discriminates",
          (rows[2015]["cv5"] > CEILING) and (rows[2022]["cv5"] <= COMFORT))
    check("a blended average would hide it",
          abs((rows[2015]['cv5'] + rows[2022]['cv5']) / 2 - 0.56) < 0.05,
          "blend 0.56 sits between 'closed' and 'comfortable'")

    print("\nlonger holds always help, and by the sqrt")
    check("cost/vol falls as sqrt of hold",
          abs(rows[2022]["cv5"] / rows[2022]["cv60"] - math.sqrt(12)) < 0.01)
    check("H_min inverts the comfort threshold exactly",
          abs(rows[2015]["s"] /
              (rows[2015]["sig"] * math.sqrt(rows[2015]["hmin"]))
              - COMFORT) < 1e-9)

    print("\nsession boundaries are not counted as moves")
    n = 30_000
    t = pd.date_range("2023-01-02 13:00", periods=n, freq="5min", tz="UTC")
    t = t[(t.hour >= 13) & (t.hour < 20)]          # gaps every night
    r_in = rng.normal(0, 2e-4, len(t))
    # A large overnight jump at each session boundary. Without one, filtering
    # gap returns out would change nothing and the control could not fail --
    # which is the whole point of having it.
    newday = np.concatenate([[False], t.date[1:] != t.date[:-1]])
    r_in = np.where(newday, rng.normal(0, 40e-4, len(t)), r_in)
    mid = 10000 * np.exp(np.cumsum(r_in))
    half = mid * 1e-4 / 2
    pd.DataFrame({"time": t, "open": mid, "high": mid, "low": mid,
                  "close": mid - half, "volume": 1.0}).to_csv(
        os.path.join(tmp, "gapusd_bid_5m.csv"), index=False)
    pd.DataFrame({"time": t, "open": mid, "high": mid, "low": mid,
                  "close": mid + half, "volume": 1.0}).to_csv(
        os.path.join(tmp, "gapusd_ask_5m.csv"), index=False)
    sp2, ret2, hrs2, yrs2 = load(tmp, "GAP_USD", "M5")
    got = robust_sd(ret2) * 1e4
    check("vol recovered as 2bp despite nightly gaps",
          abs(got - 2.0) < 0.15, f"{got:.2f}bp per 5m")
    naive = float(np.nanstd(np.diff(np.log(mid)))) * 1e4
    check("and the gap-blind estimate really would have been wrong",
          naive > 2.2, f"naive {naive:.2f}bp")

    print("\ntimezone bucketing actually shifts the hour labels")
    _s, _r, h_utc, _y = load(tmp, "GAP_USD", "M5", "UTC")
    _s2, _r2, h_ny, _y2 = load(tmp, "GAP_USD", "M5", "America/New_York")
    check("same number of bars either way", len(h_utc) == len(h_ny))
    check("the hour labels differ -- tz is applied, not ignored",
          not (h_utc == h_ny).all(),
          f"UTC {sorted(set(h_utc))[:3]} vs NY {sorted(set(h_ny))[:3]}")
    check("the shift is 4 or 5 hours, i.e. real US offsets",
          set(((h_utc - h_ny) % 24).tolist()) <= {4, 5},
          f"offsets {sorted(set(((h_utc-h_ny)%24).tolist()))}")
    check("an unknown timezone is refused, not silently ignored",
          _tz_raises(tmp))

    print(f"\n{'ALL PASS' if ok else 'FAILURES ABOVE'}")
    return 0 if ok else 1


def _tz_raises(tmp):
    try:
        load(tmp, "GAP_USD", "M5", "Not/AZone")
        return False
    except Exception:
        return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "data")))
    ap.add_argument("--instrument", default="NAS100_USD")
    ap.add_argument("--granularity", default="M5", choices=["M1", "M5", "M15"])
    ap.add_argument("--hours-since", type=int, default=2019)
    ap.add_argument("--tz", default="America/New_York",
                    help="bucket hours in this timezone. Default is the "
                         "exchange's, so the session does not smear across "
                         "DST. Use UTC to reproduce the old numbers.")
    ap.add_argument("--session", default=None,
                    help="OPEN,CLOSE hours in --tz. Defaults to 9,16 for a "
                         "US exchange timezone and 13,20 for UTC.")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        sys.exit(self_test())

    print(f"regime_profile.py v{VERSION}   NO RETURNS COMPUTED")
    print(f"  {a.instrument} {a.granularity}, both terms measured\n")

    global SESSION
    if a.session:
        SESSION = tuple(int(x) for x in a.session.split(","))
    elif a.tz.upper() != "UTC":
        SESSION = (9, 16)
    print(f"  hours bucketed in {a.tz}; session "
          f"{SESSION[0]:02d}:00-{SESSION[1]:02d}:00 local\n")

    sp, ret, hrs, yrs = load(a.data_dir, a.instrument, a.granularity, a.tz)
    rows = by_year(sp, ret, hrs, yrs, a.granularity)
    ok_years = report_years(rows, a.granularity)
    report_hours(sp, ret, hrs, yrs, a.granularity, a.hours_since)

    live = [r for r in rows if not r["dead"]]
    if live:
        import numpy as np
        print(f"\nsummary")
        print("=" * 60)
        print(f"  years with a 5m hold at least reachable: "
              f"{len(ok_years)} of {len(live)}"
              + (f"  ({ok_years[0]}-{ok_years[-1]})" if ok_years else ""))
        sig = np.array([r["sig"] for r in live])
        spa = np.array([r["s"] for r in live])
        print(f"  spread across years:  {spa.min()*1e4:.2f} to "
              f"{spa.max()*1e4:.2f}bp   ({spa.max()/spa.min():.1f}x)")
        print(f"  vol/min across years: {sig.min()*1e4:.2f} to "
              f"{sig.max()*1e4:.2f}bp   ({sig.max()/sig.min():.1f}x)")
        print(f"\n  Both terms move. A single cost/vol number for the whole")
        print(f"  history would describe no year in it -- which is why the")
        print(f"  trade-only-when-spread-clears rule is a budget consequence")
        print(f"  rather than a fitted parameter.")


if __name__ == "__main__":
    main()
