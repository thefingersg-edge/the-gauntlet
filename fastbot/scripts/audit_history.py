#!/usr/bin/env python3
"""Is the deep history REAL 1-minute data, or coarse data dressed up as it?

WHY THIS EXISTS
---------------
The probe reported 21.6 years of M1 on the US index CFDs. That is a much
better answer than expected, and this project's own rule is that a pass is
distrusted far more than a failure. Two specific ways this could be flattering:

1. **The early history may be interpolated.** OANDA's index CFDs did not
   exist as products in 2005 in the form they trade now. If early "M1" bars
   are resampled or forward-filled from a coarser source, a 1-minute strategy
   tested on them is trading an artefact. The signature is unmistakable once
   looked for: a high share of bars where open == high == low == close, price
   moving on a coarse grid, or volume flat/absent.

2. **The spread is not constant across 21 years.** COST_BUDGET.md measured
   0.44bp on NAS100 in 2026. In 2008 it was certainly wider. Backtesting two
   decades at today's spread would understate cost by a large and unknown
   factor -- and cost is the entire reason NAS100 was selected. Because the
   pull fetches bid AND ask, the historical spread can be MEASURED per year
   rather than assumed. That turns the biggest remaining assumption in the
   budget into a number.

Neither question is answerable from row counts or date ranges, which is what
`--verify` checks. This is a different job: verify checks the file is
well-formed, this checks the DATA IS WHAT IT CLAIMS TO BE.

NO RETURNS ARE COMPUTED HERE.

    python audit_history.py --instruments NAS100_USD --granularity M5
    python audit_history.py --self-test
"""

from __future__ import annotations

import argparse
import os
import sys

VERSION = "1.0"

PRICE_LABEL = {"B": "bid", "A": "ask", "M": "mid"}
TF_SUFFIX = {"M1": "1m", "M5": "5m", "M15": "15m"}
CHUNK = 500_000

#: Above this share of zero-range bars, treat the year as suspect. Real
#: 1-minute index data has some flat bars overnight; interpolated data has
#: many, and resampled-from-hourly data has almost nothing BUT flat bars.
FLAT_WARN = 0.35


def path_for(data_dir, instrument, price, gran):
    stem = instrument.replace("_", "").lower()
    return os.path.join(
        data_dir, f"{stem}_{PRICE_LABEL[price]}_{TF_SUFFIX[gran]}.csv")


def scan(path, tz=None, session=None):
    """One chunked pass. Per calendar year, the things that betray a fake.

    `session` restricts the scan to the hours a strategy would actually trade.
    This matters more than it looks: an index CFD's overnight book is thin and
    genuinely produces zero-range 5-minute bars, so scanning 24 hours mixes a
    real feed artefact (interpolated history) with a real market fact (nobody
    is trading at 3am). SPX500 2014/2015/2017 flag FLAT on a 24-hour scan and
    that is what prompted this option -- a flag that fires for a benign reason
    is as useless as one that never fires.
    """
    import numpy as np, pandas as pd

    acc = {}
    for ch in pd.read_csv(path, chunksize=CHUNK):
        t = pd.to_datetime(ch[ch.columns[0]], utc=True)
        if tz:
            t = t.dt.tz_convert(tz)
        if session:
            keep = (t.dt.hour >= session[0]) & (t.dt.hour < session[1])
            ch, t = ch[keep], t[keep]
            if ch.empty:
                continue
        yr = t.dt.year.to_numpy()
        o = ch["open"].to_numpy(float)
        h = ch["high"].to_numpy(float)
        lo = ch["low"].to_numpy(float)
        c = ch["close"].to_numpy(float)
        v = ch["volume"].to_numpy(float)

        flat = (h == lo)                       # zero-range bar
        rng = (h - lo) / np.where(c > 0, c, np.nan)
        day = t.dt.floor("D").to_numpy()

        for y in np.unique(yr):
            m = yr == y
            a = acc.setdefault(int(y), dict(
                n=0, flat=0, zerovol=0, rng=[], px=[], days=set(),
                lastdec=[]))
            a["n"] += int(m.sum())
            a["flat"] += int(flat[m].sum())
            a["zerovol"] += int((v[m] == 0).sum())
            r = rng[m]
            a["rng"].append(r[np.isfinite(r)])
            a["px"].append(c[m][:2000])
            a["days"].update(np.unique(day[m]).tolist())
    return acc


def decimals(px):
    """Effective price granularity: how many distinct last-digit values occur.

    Genuine tick data uses the full grid. Data resampled from a coarser feed,
    or rounded on the way in, collapses onto a few values -- which is visible
    here without needing to know the instrument's real tick size.
    """
    import numpy as np
    if len(px) == 0:
        return 0
    scaled = np.round(px * 100).astype(np.int64)
    return int(len(np.unique(scaled % 100)))


def report(acc, label):
    """Flag years that differ from the instrument's OWN recent behaviour.

    v1.0 compared the price grid against an absolute threshold and flagged
    every year of real NAS100 data, 2026 included. The cause was mine: NAS100
    quotes to one decimal, so `px*100 % 100` can only take 10 values, and the
    synthetic control used a continuous price where it takes 100. The control
    could not tell "coarse because interpolated" from "coarse because that is
    the tick size", so the gate fired on everything -- which is exactly as
    useless as a gate that fires on nothing.

    Every test here is now RELATIVE: each year is compared against the modal
    behaviour of the same instrument in its cleanest years. An absolute
    threshold cannot know an instrument's tick size; a within-instrument
    comparison does not need to.
    """
    import numpy as np
    rows = []
    for y in sorted(acc):
        a = acc[y]
        rng = np.concatenate(a["rng"]) if a["rng"] else np.array([])
        px = np.concatenate(a["px"]) if a["px"] else np.array([])
        rows.append(dict(
            y=y, n=a["n"], bpd=a["n"] / max(len(a["days"]), 1),
            flat=a["flat"] / max(a["n"], 1),
            zv=a["zerovol"] / max(a["n"], 1),
            rng=float(np.median(rng)) if rng.size else 0.0,
            grid=decimals(px)))

    # Baselines from the most recent third of the sample, which is the part
    # least likely to be reconstructed.
    tail = rows[-max(len(rows) // 3, 1):]
    base_grid = max(r["grid"] for r in tail)
    base_bpd = float(np.median([r["bpd"] for r in tail]))
    base_flat = float(np.median([r["flat"] for r in tail]))

    print(f"\n{label}")
    print(f"  baseline from {tail[0]['y']}-{tail[-1]['y']}: "
          f"{base_bpd:.0f} bars/day, {base_flat*100:.2f}% flat, "
          f"price grid {base_grid}")
    print(f"{'year':>6}{'bars':>11}{'bars/day':>10}{'flat%':>8}{'zerovol%':>10}"
          f"{'med range':>11}{'px grid':>9}  flag")
    print("-" * 78)
    suspect = []
    for r in rows:
        flags = []
        # Zero-range bars far above the instrument's own floor.
        #
        # This previously read max(FLAT_WARN, 20*base_flat, 0.02) with
        # FLAT_WARN = 0.35, and the absolute constant swallowed the relative
        # test: NAS100 2005 has 26.5% zero-range bars against a 0.01%
        # baseline -- a 2,650x departure -- and did not flag, because 26.5%
        # is below 35%. Exactly the bug just fixed in the price-grid test,
        # one layer down: an absolute threshold overriding a within-
        # instrument comparison. FLAT_WARN is now only a backstop for a
        # degenerate baseline, never a floor.
        thresh = max(20 * base_flat, 0.02)
        if base_flat >= FLAT_WARN:              # baseline itself suspect
            thresh = FLAT_WARN
        if r["flat"] > thresh:
            flags.append("FLAT")
        if r["zv"] > 0.5:
            flags.append("NOVOL")
        # Coarser than this instrument's own grid, not than some constant.
        if base_grid >= 4 and r["grid"] < 0.6 * base_grid:
            flags.append("COARSE-GRID")
        # Materially fewer bars per day than the same instrument now.
        if r["bpd"] < 0.85 * base_bpd:
            flags.append("THIN")
        if flags:
            suspect.append(r["y"])
        print(f"{r['y']:>6}{r['n']:>11,}{r['bpd']:>10.0f}{r['flat']*100:>7.1f}%"
              f"{r['zv']*100:>9.1f}%{r['rng']*1e4:>10.2f}bp{r['grid']:>9}"
              f"  {' '.join(flags)}")
    return suspect


def spread_by_year(data_dir, instrument, gran, tz=None, session=None):
    """Measured round-trip spread per year. The number the budget assumed."""
    import numpy as np, pandas as pd

    pb, pa = (path_for(data_dir, instrument, s, gran) for s in ("B", "A"))
    if not (os.path.exists(pb) and os.path.exists(pa)):
        return None

    out = {}
    itb = pd.read_csv(pb, usecols=[0, 4], chunksize=CHUNK)
    ita = pd.read_csv(pa, usecols=[0, 4], chunksize=CHUNK)
    for cb, ca in zip(itb, ita):
        cb.columns = ["t", "close"]
        ca.columns = ["t", "close"]
        j = cb.merge(ca, on="t", suffixes=("_b", "_a"))
        if j.empty:
            continue
        t = pd.to_datetime(j["t"], utc=True)
        if tz:
            t = t.dt.tz_convert(tz)
        if session:
            keep = ((t.dt.hour >= session[0]) & (t.dt.hour < session[1])
                    ).to_numpy()
            j, t = j[keep], t[keep]
            if j.empty:
                continue
        b, k = j["close_b"].to_numpy(float), j["close_a"].to_numpy(float)
        mid = 0.5 * (b + k)
        rel = np.where(mid > 0, (k - b) / mid, np.nan)
        hr = t.dt.hour.to_numpy()
        for y in np.unique(t.dt.year.to_numpy()):
            m = (t.dt.year.to_numpy() == y) & np.isfinite(rel)
            if not m.any():
                continue
            a = out.setdefault(int(y), [[], []])
            a[0].append(rel[m][:200_000])
            ses = m & (hr >= 13) & (hr < 20)
            if ses.any():
                a[1].append(rel[ses][:200_000])
    return out


def report_spread(sp, budget_bp=0.44, tolerance=2.0):
    """Measured spread per year, and which years have no spread data at all.

    A year whose median ask minus bid is exactly zero does NOT mean trading
    was free -- it means the feed served the same series twice and the spread
    is MISSING. Reporting that as "0.0x the budget" is the most dangerous
    possible framing: a backtest charging the measured per-bar spread would
    trade those years at no cost and report a spectacular result.

    This is the silver15 failure mode in its purest form -- an absent input
    that looks like a favourable measurement. Zero-spread years are therefore
    reported as UNUSABLE and excluded from the tradeable window, not scored.
    """
    import numpy as np
    print(f"\nMEASURED round-trip spread by year "
          f"(COST_BUDGET.md assumed {budget_bp}bp in-session)")
    print(f"{'year':>6}{'all hours':>13}{'13-20 UTC':>13}{'vs budget':>12}"
          f"   status")
    print("-" * 72)
    worst, dead, costly, usable = 0.0, [], [], []
    for y in sorted(sp):
        allh = np.concatenate(sp[y][0]) if sp[y][0] else np.array([])
        ses = np.concatenate(sp[y][1]) if sp[y][1] else np.array([])
        a = float(np.median(allh)) * 1e4 if allh.size else float("nan")
        s = float(np.median(ses)) * 1e4 if ses.size else float("nan")
        zero_share = float((allh <= 0).mean()) if allh.size else 1.0

        if not (s == s) or s <= 0 or zero_share > 0.5:
            dead.append(y)
            note = "UNUSABLE - no spread in feed"
            ratio = float("nan")
        else:
            ratio = s / budget_bp
            worst = max(worst, ratio)
            if ratio > tolerance:
                costly.append(y)
                note = f"costly ({ratio:.1f}x)"
            else:
                usable.append(y)
                note = "usable"
        rtxt = "     --  " if ratio != ratio else f"{ratio:>10.1f}x"
        print(f"{y:>6}{a:>12.2f}bp{s:>12.2f}bp{rtxt}   {note}")

    if dead:
        print(f"\n  !! {len(dead)} years carry NO spread data: "
              f"{dead[0]}-{dead[-1]}")
        print(f"     ask == bid on every bar. This is a MISSING input, not a")
        print(f"     zero cost. A backtest charging measured spread would")
        print(f"     trade these years free and report a fiction. Exclude "
              f"them.")
    if costly:
        print(f"\n  {len(costly)} years above {tolerance:.0f}x the budget "
              f"spread: {costly[0]}-{costly[-1]}")
        print(f"     Usable only if the backtest charges the spread that")
        print(f"     applied at the time, per bar, not a single constant.")
    # Two different questions, deliberately reported separately. "Cheap" is
    # not the same as "valid": a year with a real but wide spread is perfectly
    # usable IF the backtest charges that spread, and throwing it away buys
    # cost realism at the price of sample -- which raises the detectability
    # bar, the one term more history is the only cure for.
    valid = sorted(set(usable) | set(costly))
    if usable:
        n = len(usable)
        print(f"\n  CHEAP WINDOW (spread within {tolerance:.0f}x budget): "
              f"{usable[0]}-{usable[-1]}  ({n} years, bar "
              f"{2/max(n,1)**0.5:.2f})")
    if valid:
        n = len(valid)
        print(f"  VALID WINDOW (spread present, charged per bar): "
              f"{valid[0]}-{valid[-1]}  ({n} years, bar "
              f"{2/max(n,1)**0.5:.2f})")
        print(f"\n     Prefer the VALID window and charge the spread that")
        print(f"     applied at the time. Truncating to the cheap years costs")
        print(f"     {2/max(len(usable),1)**0.5 - 2/max(n,1)**0.5:+.2f} on the"
              f" detectability bar, which no amount of\n     strategy work "
              f"recovers -- only more history moves that term.")
    if dead:
        print(f"\n     Excluded entirely: {dead[0]}-{dead[-1]} "
              f"({len(dead)} years, no spread in feed).")
    return worst, dead, usable


def self_test():
    import numpy as np, pandas as pd
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" +
              (f"   {detail}" if detail else ""))

    print(f"audit_history.py v{VERSION} self-test\n")
    tmp = "/tmp/_audit_test"
    os.makedirs(tmp, exist_ok=True)
    rng = np.random.default_rng(3)
    n = 60_000

    # --- a GENUINE-looking year: full price grid, real ranges, volume
    t = pd.date_range("2020-01-01", periods=n, freq="1min", tz="UTC")
    px = 10000 + np.cumsum(rng.normal(0, 1.0, n))
    hi = px + np.abs(rng.normal(0, 0.6, n))
    lo = px - np.abs(rng.normal(0, 0.6, n))
    real = pd.DataFrame({"time": t, "open": px, "high": hi, "low": lo,
                         "close": px, "volume": rng.integers(1, 500, n)})
    real.to_csv(os.path.join(tmp, "realusd_bid_1m.csv"), index=False)

    # --- a FAKE year: hourly data forward-filled to 1m
    px2 = np.repeat(np.round(10000 + np.cumsum(
        rng.normal(0, 5.0, n // 60)), 1), 60)[:n]
    fake = pd.DataFrame({"time": t, "open": px2, "high": px2, "low": px2,
                         "close": px2, "volume": 0.0})
    fake.to_csv(os.path.join(tmp, "fakeusd_bid_1m.csv"), index=False)

    print("the audit separates real from interpolated")
    ar = scan(os.path.join(tmp, "realusd_bid_1m.csv"))
    af = scan(os.path.join(tmp, "fakeusd_bid_1m.csv"))
    sr = report(ar, "REAL (control)")
    sf = report(af, "FORWARD-FILLED FROM HOURLY (control)")
    check("genuine data raises no flags", sr == [], f"{sr}")
    check("forward-filled data IS flagged -- the gate fires", sf != [],
          f"{sf}")

    y = sorted(af)[0]
    check("fake year is >99% zero-range bars",
          af[y]["flat"] / af[y]["n"] > 0.98,
          f"{af[y]['flat']/af[y]['n']*100:.1f}%")
    yr_ = sorted(ar)[0]
    check("real year is mostly non-flat",
          ar[yr_]["flat"] / ar[yr_]["n"] < 0.05,
          f"{ar[yr_]['flat']/ar[yr_]['n']*100:.1f}%")
    check("price-grid test separates them",
          decimals(np.concatenate(af[y]["px"])) <
          decimals(np.concatenate(ar[yr_]["px"])),
          f"fake {decimals(np.concatenate(af[y]['px']))} vs real "
          f"{decimals(np.concatenate(ar[yr_]['px']))}")

    print("\na MODERATE flat share against a clean baseline must flag")
    # The case that slipped through v1.0: NAS100 2005 had 26.5% zero-range
    # bars against a 0.01% baseline and did not flag, because an absolute
    # 35% floor sat in a max() ahead of the relative test. Any control that
    # only ever planted 100% flat bars could not catch that.
    yrs_t, frames = [2019, 2020, 2021, 2022, 2023, 2024], []
    for i, yy in enumerate(yrs_t):
        m = 20_000
        tt_ = pd.date_range(f"{yy}-01-01", periods=m, freq="5min", tz="UTC")
        p_ = 10000 + np.cumsum(rng.normal(0, 1.0, m))
        h_ = p_ + np.abs(rng.normal(0, 0.6, m))
        l_ = p_ - np.abs(rng.normal(0, 0.6, m))
        if yy == 2019:                       # 25% of bars frozen
            frozen = rng.random(m) < 0.25
            h_ = np.where(frozen, p_, h_)
            l_ = np.where(frozen, p_, l_)
        frames.append(pd.DataFrame({"time": tt_, "open": p_, "high": h_,
                                    "low": l_, "close": p_,
                                    "volume": rng.integers(1, 500, m)}))
    pd.concat(frames).to_csv(
        os.path.join(tmp, "modusd_bid_5m.csv"), index=False)
    am = scan(os.path.join(tmp, "modusd_bid_5m.csv"))
    sm = report(am, "25% FLAT IN ONE YEAR, CLEAN BASELINE (control)")
    check("the moderately-flat year IS flagged", 2019 in sm, f"{sm}")
    check("the clean years are NOT flagged", set(sm) == {2019}, f"{sm}")

    print("\nthe session filter separates a quiet night from a fake feed")
    # A year that is CLEAN in session but flat overnight must pass when the
    # scan is restricted, and flag when it is not. If the filter cannot flip
    # a verdict it is not doing anything.
    m2 = 24 * 12 * 300
    t4 = pd.date_range("2019-01-01", periods=m2, freq="5min", tz="UTC")
    p4 = 10000 + np.cumsum(rng.normal(0, 1.0, m2))
    h4 = p4 + np.abs(rng.normal(0, 0.6, m2))
    l4 = p4 - np.abs(rng.normal(0, 0.6, m2))
    night = (t4.hour < 13) | (t4.hour >= 20)
    h4 = np.where(night, p4, h4)          # every overnight bar frozen
    l4 = np.where(night, p4, l4)
    pd.DataFrame({"time": t4, "open": p4, "high": h4, "low": l4,
                  "close": p4, "volume": rng.integers(1, 500, m2)}).to_csv(
        os.path.join(tmp, "nightusd_bid_5m.csv"), index=False)
    a24 = report(scan(os.path.join(tmp, "nightusd_bid_5m.csv")),
                 "24-HOUR SCAN (control)")
    ases = report(scan(os.path.join(tmp, "nightusd_bid_5m.csv"),
                       "UTC", (13, 20)), "SESSION-ONLY SCAN (control)")
    check("the 24-hour scan flags it", a24 != [], f"{a24}")
    check("the session-only scan does NOT -- the filter flips the verdict",
          ases == [], f"{ases}")

    print("\nspread measurement recovers a planted widening")
    # Plant a constant RELATIVE spread, which is what the tool measures. A
    # constant spread in price units drifts in relative terms as the price
    # moves, so asserting against it would be testing the fixture, not the
    # code -- the first version of this control did exactly that and "failed"
    # at 4.92bp against a planted 5.00bp purely because the price rose 1.6%.
    t2 = pd.date_range("2020-01-01", periods=n, freq="1min", tz="UTC")
    t3 = pd.date_range("2021-01-01", periods=n, freq="1min", tz="UTC")
    tt = t2.append(t3)
    base = np.concatenate([px, px])
    halves = base * np.concatenate([np.full(n, 5e-4 / 2),
                                    np.full(n, 1e-4 / 2)])
    for side, sign in (("bid", -1), ("ask", +1)):
        v = base + sign * halves
        pd.DataFrame({"time": tt, "open": v, "high": v, "low": v,
                      "close": v, "volume": 1.0}).to_csv(
            os.path.join(tmp, f"spusd_{side}_1m.csv"), index=False)
    sp = spread_by_year(tmp, "SP_USD", "M1")
    m20 = float(np.median(np.concatenate(sp[2020][0]))) * 1e4
    m21 = float(np.median(np.concatenate(sp[2021][0]))) * 1e4
    check("2020 spread recovered as 5bp", abs(m20 - 5.0) < 0.05, f"{m20:.2f}bp")
    check("2021 spread recovered as 1bp", abs(m21 - 1.0) < 0.05, f"{m21:.2f}bp")
    check("the widening is detected as a ratio > 2",
          report_spread(sp, budget_bp=1.0)[0] > 2)
    check("a flat-spread history does NOT trigger it -- gate discriminates",
          report_spread({2020: [[np.full(100, 1e-4)], [np.full(100, 1e-4)]]},
                        budget_bp=1.0)[0] <= 2)

    print("\nan ABSENT spread is called missing, not free")
    zero = {2007: [[np.zeros(500)], [np.zeros(500)]],
            2020: [[np.full(500, 1e-4)], [np.full(500, 1e-4)]]}
    _w, dead, usable = report_spread(zero, budget_bp=1.0)
    check("the zero-spread year is marked UNUSABLE", dead == [2007], f"{dead}")
    check("it is NOT counted as a cheap year", 2007 not in usable)
    check("the real year still counts as usable", usable == [2020], f"{usable}")

    print("\nmissing input is refused, not guessed")
    check("spread_by_year returns None when a side is absent",
          spread_by_year(tmp, "NOPE_USD", "M1") is None)

    print(f"\n{'ALL PASS' if ok else 'FAILURES ABOVE'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "data")))
    ap.add_argument("--instruments", default="NAS100_USD")
    ap.add_argument("--granularity", default="M5", choices=["M1", "M5", "M15"])
    ap.add_argument("--budget-bp", type=float, default=0.44)
    ap.add_argument("--tz", default=None,
                    help="e.g. America/New_York, to bucket by exchange time")
    ap.add_argument("--session", default=None,
                    help="OPEN,CLOSE hours in --tz; restricts the scan to "
                         "the bars a strategy would actually trade")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        sys.exit(self_test())

    print(f"audit_history.py v{VERSION}   NO RETURNS COMPUTED")
    print("  asking whether the deep history is real 1-minute data\n")

    bad = False
    for ins in [x.strip().upper() for x in a.instruments.split(",")]:
        p = path_for(a.data_dir, ins, "B", a.granularity)
        if not os.path.exists(p):
            print(f"{ins}: {os.path.basename(p)} not found -- pull it first")
            continue
        ses = tuple(int(x) for x in a.session.split(",")) if a.session \
            else None
        if ses:
            print(f"  scanning {ses[0]:02d}:00-{ses[1]:02d}:00 "
                  f"{a.tz or 'UTC'} only\n")
        suspect = report(scan(p, a.tz, ses), f"{ins} {a.granularity} bid")
        if suspect:
            bad = True
            print(f"\n  !! SUSPECT YEARS: {suspect}")
            print(f"     Treat these as unusable for a 1-minute strategy "
                  f"until explained.\n     Truncate the sample rather than "
                  f"averaging them in.")
        else:
            print(f"\n  no year flagged -- the history behaves like genuine "
                  f"{a.granularity} data")

        sp = spread_by_year(a.data_dir, ins, a.granularity, a.tz, ses)
        if sp:
            _w, dead, usable = report_spread(sp, a.budget_bp)
            if dead or _w > 2:
                bad = True
        else:
            print("\n  bid/ask not both present -- cannot measure historical "
                  "spread")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
