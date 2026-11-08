#!/usr/bin/env python3
"""Does the VIX term structure pay a premium, or just forecast VIX? FREE DATA.

WHY THIS EXISTS
---------------
RESULT_VRP.md measured the variance premium and found it real (10 sigma) but,
unhedged, worse than equity beta -- and said the hedged version needs a paid
option surface. That is still true for the OPTIONS route. It is not true for
the whole idea.

The VIX futures curve is a second, more accessible expression of the same
premium, and it is measurable from two free CBOE series. The question is the
one every carry trade has to answer:

    the curve is usually upward sloping. Is that a PREMIUM you collect,
    or an accurate FORECAST of VIX rising, which you collect nothing for?

Under the expectations hypothesis the slope is a forecast: VIX rises by
roughly the slope and a short position earns nothing. If VIX rises by LESS
than the slope predicted, the difference is a term premium and it is
harvestable.

    slope(t)   = VIX3M(t) - VIX(t)                what the curve implies
    actual(t)  = VIX(t+21) - VIX(t)               what happened
    premium    = slope - actual                   what a short roll collects

This is the same shape as vrp_budget.py: an implied quantity against its own
subsequent realisation. Nothing here is a strategy.

NO POSITION, NO SIZING, NO P&L. The output is the premium and its tail.

    python vix_curve_budget.py --self-test
    python vix_curve_budget.py
    python vix_curve_budget.py --vx1 VX1.csv --vx2 VX2.csv   # TradingView
"""

from __future__ import annotations

import argparse
import math
import os
import sys

VERSION = "1.1"
MIN_MONTHS = 24            # refuse to report on less; see _guard()
HORIZON = 21                       # trading days
ERAS = [(2002, 2009), (2010, 2017), (2018, 2026)]

CBOE = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{}_History.csv"


def _get(url):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read()


def _parse(raw, label):
    import io, pandas as pd
    if b"," not in raw.split(b"\n")[0]:
        raise ValueError(f"{label}: not a CSV -- "
                         f"{raw[:70].decode('utf-8','replace').strip()!r}")
    d = pd.read_csv(io.BytesIO(raw))
    d.columns = [c.strip().upper() for c in d.columns]
    dcol = next(c for c in d.columns if "DATE" in c)
    ccol = "CLOSE" if "CLOSE" in d.columns else d.columns[-1]
    d[dcol] = pd.to_datetime(d[dcol])
    return d.set_index(dcol)[ccol].astype(float).sort_index()


def fetch_indices(names=("VIX", "VIX3M")):
    out = {}
    for n in names:
        try:
            out[n] = _parse(_get(CBOE.format(n)), n)
            print(f"  {n:<6} {len(out[n]):,} rows  "
                  f"{out[n].index[0]:%Y-%m-%d} -> {out[n].index[-1]:%Y-%m-%d}")
        except Exception as e:                                  # noqa: BLE001
            print(f"  {n:<6} FAILED: {type(e).__name__}: {e}")
    return out


def _session_dates(t):
    """Map TradingView daily bars to the SESSION DATE they belong to.

    A TradingView daily futures bar is stamped at the moment the session
    OPENS, which for CBOE is 17:00 America/Chicago on the PREVIOUS calendar
    day. Dropping the timezone and keeping the date therefore labels every
    bar one day early -- and because the stamp is 23:00 UTC in winter and
    22:00 UTC in summer, the size of the error is not even constant.

    Verified on VX1!: all 5,636 bars sit at exactly 17:00 Chicago, and the
    +17.60 point bar stamped 2018-02-04 23:00 UTC is the 2018-02-05
    session -- the day XIV collapsed.

    Bars already stamped at midnight are left alone, so this is safe for
    exports that carry plain dates.
    """
    import pandas as pd
    if getattr(t.dt, "tz", None) is None:
        t = t.dt.tz_localize("UTC")
    ch = t.dt.tz_convert("America/Chicago")
    #: evening stamp = the session that ENDS the next calendar day
    shift = pd.to_timedelta((ch.dt.hour >= 16).astype(int), unit="D")
    return (ch + shift).dt.normalize().dt.tz_localize(None)


def _timestamps(col, label):
    """Parse a time column and PROVE the result is plausible.

    v1.0 shipped a silent catastrophe here. TradingView exports unix SECONDS
    as integers; pandas, given integers and no unit, reads them as
    NANOSECONDS -- so 1704153600 becomes 1970-01-01. It does not raise and it
    does not produce NaT, so the isna() fallback never fired. Every row in a
    2,586-row export collapsed to the epoch and the report ran on it.

    The fix is not just trying units in order. It is REFUSING to return dates
    that cannot be right.
    """
    import pandas as pd
    s = pd.Series(col)

    if pd.api.types.is_numeric_dtype(s):
        for unit in ("s", "ms", "us", "ns"):
            t = pd.to_datetime(s, unit=unit, errors="coerce", utc=True)
            if (t.notna().mean() > 0.9
                    and t.dt.year.between(1990, 2100).mean() > 0.9):
                return t
        raise SystemExit(
            f"  {label}: numeric time column but no unit (s/ms/us/ns) gives\n"
            f"  plausible dates. First values: {list(s.head(3))}")

    t = pd.to_datetime(s, errors="coerce", utc=True, format="mixed")
    ok = t.notna().mean()
    if ok < 0.9:
        raise SystemExit(f"  {label}: only {ok*100:.0f}% of the time column "
                         f"parsed. First values: {list(s.head(3))}")
    yr = t.dt.year.between(1990, 2100).mean()
    if yr < 0.9:
        raise SystemExit(
            f"  {label}: parsed dates are implausible "
            f"({t.min():%Y-%m-%d} to {t.max():%Y-%m-%d}).\n"
            f"  First raw values: {list(s.head(3))}")
    return t


def _guard(df, label):
    """Refuse to report on a sample too small to mean anything.

    v1.0 printed beta, a decomposition and a 'five worst months' table from
    ONE observation, with nan for every dispersion statistic. A reader
    skimming it would have seen '78% from the slope' and concluded the real
    futures showed carry. Silence beats a confident nan.
    """
    m = monthly(df)
    if len(m) < MIN_MONTHS:
        raise SystemExit(
            f"\n  {label}: only {len(m)} non-overlapping month(s) after "
            f"parsing -- refusing to report.\n"
            f"  Need at least {MIN_MONTHS}. Date range read as "
            f"{df.index.min():%Y-%m-%d} to {df.index.max():%Y-%m-%d}.\n"
            f"  If that range looks wrong, the time column was misparsed.")
    return m


def load_csv(path, label):
    """A TradingView CSV export. Finds the time and close columns itself."""
    import glob, pandas as pd
    if not os.path.exists(path):
        hits = []
        for d_ in (os.path.expanduser("~/Downloads"), os.getcwd(),
                   os.path.expanduser("~")):
            hits += glob.glob(os.path.join(d_, f"*{label}*.csv"))
            hits += glob.glob(os.path.join(d_, f"*{label.lower()}*.csv"))
        raise SystemExit(
            f"\n  {path} not found.\n"
            f"  TradingView names its exports like\n"
            f"    'CBOE_DL_VX1!, 1D.csv'  in ~/Downloads\n"
            f"  Pass the full path, quoted:\n"
            f"    --vx1 \"$HOME/Downloads/CBOE_DL_VX1!, 1D.csv\"\n"
            + (f"\n  Candidates found:\n" +
               "\n".join(f"    {h}" for h in sorted(set(hits))[:8])
               if hits else ""))
    d = pd.read_csv(path)
    d.columns = [c.strip().upper() for c in d.columns]
    dcol = next((c for c in d.columns if c in ("TIME", "DATE", "DATETIME")),
                d.columns[0])
    ccol = next((c for c in d.columns if c == "CLOSE"), d.columns[-1])
    t = _session_dates(_timestamps(d[dcol], label))
    s = pd.Series(d[ccol].astype(float).to_numpy(),
                  index=t.values).sort_index()
    s = s[~s.index.duplicated(keep="last")].dropna()
    print(f"  {label:<6} {len(s):,} rows  {s.index[0]:%Y-%m-%d} -> "
          f"{s.index[-1]:%Y-%m-%d}   (local file)")
    return s


def measure(near, far, horizon=HORIZON):
    """Slope now, versus what the near leg actually did over `horizon`.

    `near`/`far` are VIX and VIX3M, or VX1! and VX2!. The arithmetic is the
    same either way: an upward slope is a forecast of the near leg rising,
    and the premium is however much it does not.
    """
    import numpy as np, pandas as pd
    idx = near.index.intersection(far.index)
    n, f = near.loc[idx].sort_index(), far.loc[idx].sort_index()

    slope = f - n                                   # implied rise, vol points
    actual = n.shift(-horizon) - n                  # what the near leg did
    df = pd.DataFrame({"near": n, "far": f, "slope": slope,
                       "actual": actual}).dropna()
    df["premium"] = df["slope"] - df["actual"]
    df["contango"] = df["slope"] > 0
    return df


def monthly(df):
    """Non-overlapping. Overlapping 21-day windows inflate every t by ~sqrt(21)."""
    return df.resample("ME").first().dropna()


def report(df, label):
    import numpy as np
    m = monthly(df)
    p = m["premium"].to_numpy()
    s = m["slope"].to_numpy()
    a = m["actual"].to_numpy()

    print(f"\n{label}")
    print(f"  {len(m):,} non-overlapping months  "
          f"({m.index[0]:%Y-%m} -> {m.index[-1]:%Y-%m})")
    print(f"\n  curve in contango on {float(m['contango'].mean())*100:.0f}% "
          f"of months   mean slope {np.mean(s):+.2f} vol pts")
    print(f"  the near leg actually moved {np.mean(a):+.2f} vol pts on "
          f"average")
    print(f"  PREMIUM (slope - actual)   mean {np.mean(p):+.2f}  "
          f"median {np.median(p):+.2f}  positive "
          f"{float((p > 0).mean())*100:.0f}% of months")

    sd = float(np.std(p, ddof=1))
    sh = float(np.mean(p) / sd * math.sqrt(12)) if sd else float("nan")
    z = float(np.mean(p) / (sd / math.sqrt(len(p)))) if sd else float("nan")
    print(f"  sd {sd:.2f}   implied Sharpe {sh:+.2f}   t {z:+.2f}")
    sk = float(((p - np.mean(p)) ** 3).mean() / sd ** 3) if sd else 0
    print(f"  skew {sk:+.2f}   worst month {np.min(p):+.2f} vol pts "
          f"({m['premium'].idxmin():%Y-%m}) = "
          f"{abs(np.min(p))/sd:.1f} sd")

    print(f"\n  IS THE SLOPE A FORECAST OR A PREMIUM?")
    b, alpha = (float(x) for x in np.polyfit(s, a, 1))
    print(f"    regress actual move on slope:  beta {b:+.2f}  "
          f"alpha {alpha:+.2f}")
    print(f"    beta 1.0 = pure forecast, you collect nothing")
    print(f"    beta 0.0 = pure premium, you collect the whole slope")
    print(f"    CAVEAT: any measurement noise in the slope attenuates beta")
    print(f"      toward zero (errors-in-variables), which makes the premium")
    print(f"      look larger than it is. A low beta is NOT by itself")
    print(f"      evidence of a premium. This bites hardest on the VIX3M")
    print(f"      proxy and least on real VX1!/VX2! futures.")
    # WHERE THE PREMIUM ACTUALLY COMES FROM.
    #
    # premium = slope - actual = -alpha + (1-beta)*slope. Reporting beta
    # alone hides the decomposition, and on the VIX3M proxy the whole
    # premium turned out to be the INTERCEPT -- i.e. VIX falling regardless
    # of the curve, which is mean reversion, not carry.
    from_intercept = -alpha
    from_slope = (1 - b) * float(np.mean(s))
    tot = from_intercept + from_slope
    print(f"\n    DECOMPOSITION  premium = -alpha + (1-beta)*slope")
    print(f"      from the intercept (VIX drifts down):  {from_intercept:+.2f}"
          f"  ({from_intercept/tot*100:>5.0f}%)")
    print(f"      from the SLOPE (actual carry):         {from_slope:+.2f}"
          f"  ({from_slope/tot*100:>5.0f}%)")
    if from_slope <= 0.2 * abs(tot):
        print(f"      => the term structure contributes ~nothing. What is")
        print(f"         being measured is VIX MEAN REVERSION over this")
        print(f"         sample, which is a different and far more fragile")
        print(f"         thing to be short of.")

    # Mean reversion leaves a fingerprint: the premium should rise with the
    # LEVEL of VIX, not with the slope.
    lv = float(np.corrcoef(m["near"].to_numpy(), p)[0, 1])
    sl = float(np.corrcoef(s, p)[0, 1])
    print(f"\n    premium correlates with VIX LEVEL  {lv:+.2f}"
          f"   with SLOPE {sl:+.2f}")
    print(f"      carry story -> slope matters.  mean-reversion story -> "
          f"level matters.")

    cs = m[m["contango"]]["premium"].to_numpy()
    bk = m[~m["contango"]]["premium"].to_numpy()
    if len(cs) > 5:
        print(f"    in contango  ({len(cs):>3} months): premium "
              f"{np.mean(cs):+.2f} vol pts")
    if len(bk) > 5:
        print(f"    in backwardation ({len(bk):>3} months): premium "
              f"{np.mean(bk):+.2f} vol pts")

    print(f"\n  by era")
    print(f"  {'era':>12}{'n':>6}{'% contango':>12}{'mean prem':>11}"
          f"{'Sharpe':>9}{'worst':>9}")
    print("  " + "-" * 59)
    for lo, hi in ERAS:
        w = m[(m.index.year >= lo) & (m.index.year <= hi)]
        if len(w) < 12:
            continue
        q = w["premium"].to_numpy()
        sdq = float(np.std(q, ddof=1))
        print(f"  {f'{lo}-{hi}':>12}{len(w):>6}"
              f"{float(w['contango'].mean())*100:>11.0f}%{np.mean(q):>11.2f}"
              f"{(np.mean(q)/sdq*math.sqrt(12) if sdq else 0):>9.2f}"
              f"{np.min(q):>9.2f}")

    print(f"\n  five worst months -- what you are being paid for")
    for d, row in m.nsmallest(5, "premium").iterrows():
        print(f"    {d:%Y-%m}  slope {row['slope']:+6.2f}  "
              f"actual {row['actual']:+7.2f}  premium {row['premium']:+7.2f}")
    return m


def self_test():
    import numpy as np, pandas as pd
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" +
              (f"   {detail}" if detail else ""))

    print(f"vix_curve_budget.py v{VERSION} self-test\n")
    n = 3000
    dates = pd.bdate_range("2005-01-03", periods=n)
    rng = np.random.default_rng(11)

    print("daily bars are labelled by SESSION, not by their opening stamp")
    #: TradingView stamps a daily futures bar when the session OPENS, at
    #: 17:00 Chicago the previous calendar day. 23:00 UTC in winter, 22:00
    #: in summer -- so a naive date is one day early, by a varying amount.
    ev = pd.Series(pd.to_datetime(
        ["2018-02-04 23:00", "2018-06-04 22:00"], utc=True))
    got = _session_dates(ev)
    check("a winter evening stamp becomes the next session",
          got.iloc[0] == pd.Timestamp("2018-02-05"), f"{got.iloc[0]}")
    check("a summer evening stamp does too, despite the different hour",
          got.iloc[1] == pd.Timestamp("2018-06-05"), f"{got.iloc[1]}")
    #: planted to fail a naive .dt.date, which would give 2018-02-04
    check("the naive date would have been wrong by a day",
          ev.dt.tz_convert(None).iloc[0].normalize()
          != got.iloc[0], "naive 2018-02-04 vs session 2018-02-05")
    mid = pd.Series(pd.to_datetime(["2018-02-05 00:00"], utc=True))
    check("a plain midnight date is left alone",
          _session_dates(mid).iloc[0] == pd.Timestamp("2018-02-05"),
          f"{_session_dates(mid).iloc[0]}")

    print("\na world where the slope is a PERFECT forecast pays nothing")
    vix = pd.Series(20 + np.cumsum(rng.normal(0, 0.3, n)), index=dates)
    # far leg set so slope exactly equals the realised future move
    fut = vix.shift(-HORIZON) - vix
    far = (vix + fut).dropna()
    d1 = measure(vix, far)
    check("premium is ~zero under the expectations hypothesis",
          abs(d1["premium"].mean()) < 0.05,
          f"{d1['premium'].mean():+.3f} vol pts")
    b1 = float(np.polyfit(d1["slope"], d1["actual"], 1)[0])
    check("and beta is ~1.0, i.e. pure forecast", abs(b1 - 1.0) < 0.05,
          f"beta {b1:+.3f}")

    print("\na world with a planted term premium pays exactly that")
    # Noise on the planted premium, or its variance is exactly zero and the
    # t-statistic comes out at 1e17 -- which passes the comparison while
    # telling you nothing. A fixture that cannot produce a realistic
    # statistic cannot validate one.
    far2 = (vix + fut + 2.0
            + pd.Series(rng.normal(0, 1.5, n), index=dates)).dropna()
    d2 = measure(vix, far2)
    check("planting +2.0 vol points recovers +2.0",
          abs(d2["premium"].mean() - 2.0) < 0.15,
          f"{d2['premium'].mean():+.3f}")
    check("and the forecast case did NOT show one -- discriminates",
          abs(d1["premium"].mean()) < 0.25 * abs(d2["premium"].mean()))
    b2 = float(np.polyfit(d2["slope"], d2["actual"], 1)[0])
    # Beta does NOT stay at 1.0, and that is correct. Adding noise to the
    # far leg adds noise to the REGRESSOR, and errors-in-variables attenuates
    # beta toward zero by exactly var(signal)/(var(signal)+var(noise)).
    #
    # This is not a fixture artefact -- it is the single most important
    # caveat for reading the real output. VIX3M is a NOISY proxy for the
    # futures curve, so its beta is attenuated, which makes the premium look
    # larger than it is. A low beta is not by itself evidence of a premium.
    var_sig = float(np.var(fut.dropna(), ddof=1))
    predicted = var_sig / (var_sig + 1.5 ** 2)
    check("beta is attenuated by noise in the slope, by the predicted amount",
          abs(b2 - predicted) < 0.08,
          f"beta {b2:+.3f} vs errors-in-variables prediction {predicted:.3f}")
    check("and the CLEAN slope was not attenuated -- so this is the noise, "
          "not the method", abs(b1 - 1.0) < 0.05, f"clean beta {b1:+.3f}")
    check("and the t-statistic is a realistic size, not a degenerate one",
          1 < abs(d2["premium"].mean() / d2["premium"].std(ddof=1)
                  * math.sqrt(len(d2))) < 500,
          f"t {d2['premium'].mean()/d2['premium'].std(ddof=1)*math.sqrt(len(d2)):.1f}")

    print("\na world where the slope predicts NOTHING pays the whole slope")
    far3 = vix + pd.Series(rng.uniform(0, 4, n), index=dates)
    d3 = measure(vix, far3)
    b3 = float(np.polyfit(d3["slope"], d3["actual"], 1)[0])
    check("beta collapses toward 0 when the slope has no information",
          abs(b3) < 0.35, f"beta {b3:+.3f}")
    check("and the premium is then close to the mean slope",
          abs(d3["premium"].mean() - d3["slope"].mean()) < 0.6,
          f"prem {d3['premium'].mean():+.2f} vs slope "
          f"{d3['slope'].mean():+.2f}")

    print("\nthe horizon is genuinely forward")
    v2 = vix.copy()
    v2.iloc[n // 2:] += 30                      # a spike, second half only
    d4 = measure(v2, v2 + 2.0)
    pre = d4[d4.index < dates[n // 2 - HORIZON - 5]]["premium"].mean()
    edge = d4[(d4.index >= dates[n // 2 - HORIZON])
              & (d4.index < dates[n // 2])]["premium"].mean()
    check("the premium collapses BEFORE the spike, not after",
          edge < pre - 5, f"before {pre:+.2f}, at the edge {edge:+.2f}")

    print("\nnon-overlapping sampling")
    m = monthly(d2)
    check("monthly is ~1/21 of daily", 0.02 < len(m) / len(d2) < 0.09,
          f"{len(m)}/{len(d2)}")
    td = d2["premium"].mean() / d2["premium"].std(ddof=1) * math.sqrt(len(d2))
    tm = m["premium"].mean() / m["premium"].std(ddof=1) * math.sqrt(len(m))
    check("and it lowers the t-statistic, as it must", tm < td * 0.5,
          f"daily t {td:.0f} -> monthly t {tm:.0f}")

    print("\ntimestamps are parsed AND validated")
    import tempfile
    iso = pd.date_range("2010-01-04", periods=400, freq="B")
    for lbl, timecol in (("ISO strings", iso.strftime("%Y-%m-%dT%H:%M:%SZ")),
                         # .view("int64") is NOT reliably nanoseconds --
                         # pandas 3.0 backs datetimes at MICROSECOND
                         # resolution, so it silently gave 1262563 instead of
                         # 1262563200. The same unit assumption that produced
                         # the 1970 bug, one level down, in the test written
                         # to catch it. Be explicit about the unit.
                         ("unix seconds",
                          iso.values.astype("datetime64[s]").astype("int64"))):
        with tempfile.NamedTemporaryFile("w", suffix=".csv",
                                         delete=False) as fh:
            pd.DataFrame({"time": timecol,
                          "close": np.arange(400.0)}).to_csv(fh.name,
                                                             index=False)
            got = load_csv(fh.name, "TST")
        check(f"{lbl} parse to the right decade",
              got.index.min().year == 2010 and got.index.max().year == 2011,
              f"{got.index.min():%Y-%m-%d} -> {got.index.max():%Y-%m-%d}")

    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
        pd.DataFrame({"time": np.arange(400) * 1.0,
                      "close": np.arange(400.0)}).to_csv(fh.name, index=False)
        try:
            load_csv(fh.name, "BAD")
            bad_ok = False
        except SystemExit:
            bad_ok = True
    check("a time column that cannot be a date is REFUSED, not epoched",
          bad_ok)

    print("\ntoo-small samples are refused, not reported with nan")
    tiny = measure(vix.head(60), (vix + 2.0).head(60))
    try:
        _guard(tiny, "TINY")
        guard_ok = False
    except SystemExit:
        guard_ok = True
    check(f"fewer than {MIN_MONTHS} months raises instead of printing nan",
          guard_ok, f"{len(monthly(tiny))} months")
    check("and a full sample passes the same guard",
          len(_guard(d2, "FULL")) >= MIN_MONTHS)

    print("\nno strategy is simulated")
    import vix_curve_budget as _self
    bad = [x for x in dir(_self) if not x.startswith("_") and any(
        w in x.lower() for w in ("position", "size", "pnl", "equity",
                                 "trade", "signal"))]
    check("no sizing / P&L / signal function in the module", bad == [],
          f"{bad}")
    check("output columns are a premium, not a return series",
          set(d2.columns) == {"near", "far", "slope", "actual", "premium",
                              "contango"}, f"{sorted(d2.columns)}")

    print(f"\n{'ALL PASS' if ok else 'FAILURES ABOVE'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vx1", help="TradingView CBOE:VX1! CSV export")
    ap.add_argument("--vx2", help="TradingView CBOE:VX2! CSV export")
    ap.add_argument("--tv-dir", nargs="?", const="~/Downloads",
                    help="find the VX1/VX2 exports in this directory instead "
                         "of naming them. Default ~/Downloads. Avoids "
                         "quoting a filename containing '!', which bash "
                         "treats as history expansion.")
    ap.add_argument("--horizon", type=int, default=HORIZON)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"vix_curve_budget.py v{VERSION}   MEASUREMENT ONLY, NO STRATEGY\n")

    if a.tv_dir:
        import glob
        base = os.path.expanduser(a.tv_dir)
        def find(tag):
            hits = [h for h in glob.glob(os.path.join(base, "*.csv"))
                    if tag.lower() in os.path.basename(h).lower()]
            if not hits:
                raise SystemExit(
                    f"  no *{tag}*.csv in {base}\n"
                    f"  found: " + ", ".join(
                        sorted(os.path.basename(x) for x in
                               glob.glob(os.path.join(base, '*.csv')))[:10]))
            return max(hits, key=os.path.getmtime)
        a.vx1, a.vx2 = find("VX1"), find("VX2")
        print(f"  found {os.path.basename(a.vx1)}")
        print(f"  found {os.path.basename(a.vx2)}")

    if a.vx1 and a.vx2:
        near, far = load_csv(a.vx1, "VX1"), load_csv(a.vx2, "VX2")
        label = "REAL VIX FUTURES  (VX1! front vs VX2! second)"
        note = ("  These are the actual tradeable contracts, so this is the\n"
                "  premium itself rather than an index proxy.")
    else:
        ix = fetch_indices()
        if "VIX" not in ix or "VIX3M" not in ix:
            raise SystemExit(
                "\n  Could not fetch both indices. Either rerun with network,"
                "\n  or export CBOE:VX1! and CBOE:VX2! from TradingView and"
                "\n  pass --vx1 / --vx2 (that is the better measurement).")
        near, far = ix["VIX"], ix["VIX3M"]
        label = "INDEX PROXY  (VIX 30-day vs VIX3M 3-month)"
        note = ("  PROXY, not the tradeable curve. VIX3M is today's 3-month\n"
                "  implied vol; a VIX future is the market's forecast of the\n"
                "  VIX index at expiry. Related, not identical. Export\n"
                "  CBOE:VX1! and CBOE:VX2! from TradingView for the real one.")

    df = measure(near, far, a.horizon)
    _guard(df, label)
    report(df, label)
    print(f"\n  ON THE DATA USED\n{note}")

    print("\n  WHAT THIS DOES AND DOES NOT SAY")
    print("    Does: whether the curve pays a premium above its own forecast,")
    print("      how often, and what the bad months look like.")
    print("    Does NOT: that it is harvestable net of cost. Short VIX")
    print("      futures needs a futures broker; the ETP route embeds fees")
    print("      and a 2018 product change (XIV terminated, SVXY cut to")
    print("      -0.5x). Neither is the hedged option strategy.")
    print("    A large negative skew is the product, not a defect. Feb 2018")
    print("      took VIX from ~17 to ~50 in one session.")


if __name__ == "__main__":
    main()
