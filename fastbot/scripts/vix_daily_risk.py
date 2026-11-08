#!/usr/bin/env python3
"""How much of the short-VIX risk does a MONTHLY measurement fail to see?

WHY THIS EXISTS
---------------
vix_carry_budget.py sized the trade off a monthly premium series and its own
closing section says the answer depends on something it cannot observe:

    "No slippage beyond the quoted spread, and the quoted spread is widest
     in exactly the months that produce the worst runs."

and, more seriously, a monthly series cannot see the PATH inside a month.
That matters here more than almost anywhere else, because the single event
that destroyed the retail short-volatility industry -- 5 February 2018 --
happened inside one session, and February 2018 does not appear anywhere in
the monthly measure's five worst drawdowns.

A margin call is triggered by the path, not by the month-end mark.

WHAT THIS DOES
--------------
Reconstructs the DAILY mark-to-market of a systematic short front-month VX
position, rolled at expiry, from the same VX1!/VX2! exports, and reports the
drawdown at daily resolution against the monthly figure.

THE ROLL IS THE WHOLE DIFFICULTY. TradingView's VX1! is a continuous front
month: on the day after expiry it jumps to a different contract, and the
naive -diff(VX1) charges that jump to the position as a loss it never took.
In contango the jump is upward, so the naive series destroys exactly the
carry the strategy exists to collect. On a roll day today's front month is
yesterday's SECOND month, so the correct daily P&L is

    non-roll day:   -(VX1_t - VX1_{t-1})
    roll day:       -(VX1_t - VX2_{t-1})

Roll days come from the published VX contract calendar -- Wednesday 30 days
before the third Friday of the following month -- and are then CHECKED
against the data rather than trusted.

STILL INVISIBLE AFTER THIS: intraday. On 5 Feb 2018 VIX futures moved far
further intraday and in the aftermarket than any close-to-close figure
shows. Daily is better than monthly; it is not the truth.

NO STRATEGY IS OPTIMISED. This measures the risk of a fixed rule.

    python vix_daily_risk.py --self-test
    python vix_daily_risk.py --tv-dir ~/Downloads --account 10000
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vix_curve_budget as VC                            # noqa: E402
import vix_carry_budget as CB                            # noqa: E402

VERSION = "1.2"

#: On roll days the continuous front month must step up by roughly one
#: slope, and it must do so far too consistently to be chance. Both are
#: required: a big t on a small step would mean the calendar found SOME
#: systematic day, not the right one.
ROLL_STEP_T_MIN = 4.0
ROLL_STEP_RATIO = (0.40, 1.60)
ROLLS_PER_YEAR = 12

#: Wide enough to contain a volume-based roll, which switches ~a week
#: before expiry rather than on it. The first version used 4 and therefore
#: could not see the answer at -6 no matter what the data said.
SCAN_SPAN = 14


def vx_expiries(first, last):
    """Published VX settlement dates: the Wednesday 30 days before the third
    Friday of the FOLLOWING month. Exchange holidays shift settlement to the
    preceding business day; that is handled downstream by snapping to the
    last trading day present in the data.
    """
    import pandas as pd
    out = []
    y0, y1 = first.year - 1, last.year + 1
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            nxt = pd.Timestamp(year=y, month=m, day=1) + pd.DateOffset(
                months=1)
            fri = pd.date_range(nxt, nxt + pd.offsets.MonthEnd(0),
                                freq="W-FRI")
            if len(fri) < 3:
                continue
            out.append(fri[2] - pd.Timedelta(days=30))
    return [d for d in sorted(out) if first <= d <= last]


def roll_days(idx, expiries, offset=0):
    """Trading day on which the continuous series switches contract.

    offset 0  = first trading day strictly AFTER the settlement date
    offset -1 = the settlement date itself

    Which of these is right is a fact about the data vendor, not something
    to assume. VX settles at the OPEN on expiry Wednesday, so the expiring
    contract may already be gone from a front-month series by that day's
    close -- but whether a given export behaves that way is measurable, and
    scan_offsets() below measures it instead of guessing.
    """
    import numpy as np
    pos = np.searchsorted(idx.values, np.array(
        [e.to_datetime64() for e in expiries]), side="right") + offset
    return sorted({idx[p] for p in pos if 0 < p < len(idx)})


def scan_offsets(vx1, vx2, expiries, span=SCAN_SPAN):
    """Which trading day actually carries the roll?

    This is an IDENTIFICATION, not a search for the best-looking answer.
    The contract switches on exactly one day; if the data says so, exactly
    one offset shows a full one-slope step at high significance and every
    rival shows almost nothing. If several look alike, the series is not
    what this file assumes and no offset should be used -- that is a
    failure, not a menu.

    Two things here were got wrong first time and are worth keeping named.

    SPAN. It defaulted to 4, chosen for no reason. A vendor that rolls a
    continuous contract on VOLUME rather than on expiry switches roughly a
    week early, so the true answer sat outside the window and the scan
    could not have found it whatever the data said. An arbitrary search
    window is an assumption in disguise.

    RANKING. Candidates were ranked by |t|, which treats a large NEGATIVE
    step as a strong rival. A contract switch can only step UP, by the
    slope: the outgoing front month is replaced by a dearer contract. A
    negative step is not a weaker version of a roll, it is a different
    thing, and letting it compete for the runner-up slot rejected a
    correctly identified roll on the strength of noise pointing the wrong
    way.
    """
    lo_r, hi_r = ROLL_STEP_RATIO
    rows = []
    for off in range(-span, span + 1):
        r = roll_days(vx1.index, expiries, off)
        ratio, t, n, hit = roll_check(vx1, vx2, r)
        rows.append(dict(offset=off, ratio=ratio, t=t, n=n, hit=hit))
    #: only an upward step is a candidate roll at all
    cands = sorted([r for r in rows if r["ratio"] > 0],
                   key=lambda x: -x["t"])
    if not cands:
        return rows, max(rows, key=lambda x: x["t"]), None, False
    best = cands[0]
    second = cands[1] if len(cands) > 1 else None
    clean = (best["t"] >= ROLL_STEP_T_MIN
             and lo_r <= best["ratio"] <= hi_r
             and (second is None or second["t"] < 0.5 * best["t"]))
    return rows, best, second, clean


def daily_pnl(vx1, vx2, rolls):
    """Daily mark-to-market of SHORT one front-month contract, vol points.

    Positive = the short made money.
    """
    import pandas as pd
    idx = vx1.index
    prev_near = vx1.shift(1)
    prev_far = vx2.shift(1)
    is_roll = pd.Series(False, index=idx)
    is_roll.loc[[d for d in rolls if d in idx]] = True
    #: on a roll day the contract we hold today was the SECOND month
    #: yesterday, so yesterday's mark for it is VX2, not VX1
    ref = prev_near.where(~is_roll, prev_far)
    return -(vx1 - ref).dropna(), is_roll


def roll_check(vx1, vx2, rolls):
    """Does the calendar actually line up with the data?

    The obvious test -- count the days where |VX1_t - VX2_{t-1}| is smaller
    than |VX1_t - VX1_{t-1}| -- is too weak to use. On a true roll day the
    wrong reading is the right one plus the slope, and with VX1's daily
    change (~0.55) of the same order as the slope (~0.7), even a PERFECT
    calendar only wins that comparison about three times in four. A 70%
    pass mark sits just under its own ceiling, which is not a test.

    So test the MEAN instead. On roll days the continuous series steps up
    by the slope; on every other day it does not. With ~268 rolls the
    difference in means is enormously significant if the calendar is right
    and vanishes if it is not.

    Returns (ratio of the step to the typical slope, t statistic, n, sign
    hit rate kept only as description).
    """
    import numpy as np, pandas as pd
    d = pd.DataFrame({"n": vx1, "pn": vx1.shift(1),
                      "pf": vx2.shift(1), "slope": vx2 - vx1}).dropna()
    on = d.index.isin(set(rolls))
    r, o = d.loc[on], d.loc[~on]
    if len(r) < 12 or len(o) < 12:
        return 0.0, 0.0, len(r), 0.0
    a = (r["n"] - r["pn"]).to_numpy()               # step on roll days
    b = (o["n"] - o["pn"]).to_numpy()               # drift on other days
    slope = float(d["slope"].median())
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    t = float((a.mean() - b.mean()) / se) if se > 0 else 0.0
    ratio = float((a.mean() - b.mean()) / slope) if slope else 0.0
    hit = float(((r["n"] - r["pf"]).abs()
                 < (r["n"] - r["pn"]).abs()).mean())
    return ratio, t, len(r), hit


def curve(pnl, rolls, roll_ticks, commission, mult, tick):
    """Cumulative vol points, net of the cost charged on each roll day."""
    import pandas as pd
    cost = roll_ticks * tick + 2.0 * commission / mult
    charge = pd.Series(0.0, index=pnl.index)
    hits = [d for d in rolls if d in pnl.index]
    charge.loc[hits] = cost
    return (pnl - charge).cumsum(), len(hits), cost


def report(vx1, vx2, a):
    import numpy as np, pandas as pd

    idx = vx1.index
    exps = vx_expiries(idx[0], idx[-1])

    rows, best, second, clean = scan_offsets(vx1, vx2, exps)
    print(f"\n  WHICH DAY CARRIES THE ROLL -- identified, not assumed")
    print(f"    {'offset':>7}{'step/slope':>13}{'t':>8}{'sign':>8}")
    print("    " + "-" * 36)
    for r_ in rows:
        mark = "  <-- switch" if r_["offset"] == best["offset"] else ""
        print(f"    {r_['offset']:>7}{r_['ratio']:>13.2f}{r_['t']:>8.1f}"
              f"{r_['hit']*100:>7.0f}%{mark}")
    if not clean:
        raise SystemExit(
            f"\n  REFUSING TO CONTINUE. No single day carries the roll.\n"
            f"  Best offset {best['offset']} at t={best['t']:.1f}, "
            f"{best['ratio']:.2f}x slope; runner-up t={second['t']:.1f}.\n"
            f"  One contract switch happens on ONE day. If the step is "
            f"smeared across\n  several, this export does not roll the way "
            f"this file assumes, and picking\n  the best-looking offset "
            f"would be fitting the calendar to the data.")
    where = {-1: "the settlement date itself",
             0: "the first trading day after settlement"}.get(
                 best["offset"], f"{best['offset']:+d} trading days from "
                                 f"settlement")
    print(f"    -> the switch lands on {where}, "
          f"{best['ratio']:.2f}x slope at t={best['t']:.1f}")
    print(f"       runner-up t={second['t']:.1f}, so the day is identified "
          f"rather than chosen")

    rolls = roll_days(idx, exps, best["offset"])
    ratio, t, n_cand, hit = roll_check(vx1, vx2, rolls)
    yrs = (idx[-1] - idx[0]).days / 365.25
    lo_r, hi_r = ROLL_STEP_RATIO
    good = t >= ROLL_STEP_T_MIN and lo_r <= ratio <= hi_r

    #: A RAW front month is a volatility level: bounded, positive, centred
    #: near VIX's own long-run mean. A BACK-ADJUSTED series has 22 years of
    #: roll adjustments baked into the level and drifts far outside that
    #: range -- and for an adjusted series the naive difference is ALREADY
    #: the correct P&L, so this file's correction would double-count it.
    lo, hi, mu = float(vx1.min()), float(vx1.max()), float(vx1.mean())
    looks_raw = lo > 5.0 and hi < 120.0 and 12.0 < mu < 32.0
    print(f"\n  ROLL CALENDAR -- checked against the data, not assumed")
    print(f"    {len(rolls)} rolls over {yrs:.1f} years "
          f"= {len(rolls)/yrs:.1f}/yr (expect {ROLLS_PER_YEAR})")
    print(f"    level min {lo:.1f}  max {hi:.1f}  mean {mu:.1f}  -> "
          f"{'RAW front month' if looks_raw else 'BACK-ADJUSTED'}")
    print(f"    roll-day step = {ratio:.2f} x the typical slope, "
          f"t = {t:.1f}   (sign test {hit*100:.0f}%,")
    print(f"    kept as description only: its ceiling is ~75% even with a "
          f"perfect calendar)")
    if not good:
        raise SystemExit(
            f"\n  REFUSING TO CONTINUE. Step {ratio:.2f}x slope at t={t:.1f}"
            f"; need {lo_r}-{hi_r}x at t>={ROLL_STEP_T_MIN}.\n" + (
                "  The level looks like a raw front month, so the roll "
                "calendar is the\n  suspect: every P&L below would charge "
                "fake jumps to the position.\n"
                if looks_raw else
                "  The level looks BACK-ADJUSTED. Such a series already "
                "contains the roll,\n  so the naive difference is the "
                "correct P&L and this file's correction\n  would "
                "double-count it. Re-export VX1!/VX2! unadjusted.\n") +
            "  Nothing is printed from here rather than printing something "
            "wrong.")

    pnl, is_roll = daily_pnl(vx1, vx2, rolls)
    C = CB.CONTRACTS[a.contract]
    mult, tick = C["mult"], C["tick"]
    eq, n_hit, cost = curve(pnl, rolls, a.roll_ticks, a.commission, mult, tick)

    #: The naive series, kept visible rather than described. This is the
    #: number someone gets by differencing a continuous contract.
    naive = (-(vx1.diff())).dropna().cumsum()

    print(f"\n  WHAT THE ROLL CORRECTION IS WORTH")
    print(f"    corrected, net of cost   {eq.iloc[-1]:+8.1f} vol pts over "
          f"{yrs:.1f} years")
    print(f"    naive -diff(VX1!)        {naive.iloc[-1]:+8.1f} vol pts")
    print(f"    difference               {eq.iloc[-1]-naive.iloc[-1]:+8.1f} "
          f"= the carry the naive series throws away")
    print(f"    per month, corrected     {eq.iloc[-1]/(yrs*12):+8.2f} vol pts")

    print(f"\n  DAILY RISK vs THE MONTHLY MEASURE")
    dd = eq - eq.cummax().clip(lower=0.0)
    worst_d = float(dd.min())
    when = dd.idxmin()
    peak_at = eq.loc[:when].idxmax()
    rec = eq.loc[when:]
    back = rec[rec >= float(eq.loc[:when].max())]
    print(f"    worst DAILY drawdown     {worst_d:8.2f} vol pts "
          f"({peak_at:%Y-%m-%d} -> {when:%Y-%m-%d})")
    if len(back):
        print(f"      recovered {back.index[0]:%Y-%m-%d}, "
              f"{(back.index[0]-peak_at).days} days peak to peak")
    else:
        print(f"      NOT RECOVERED by the end of the sample")
    print(f"    worst single DAY         {float(pnl.min()):8.2f} vol pts "
          f"({pnl.idxmin():%Y-%m-%d})")
    print(f"    worst 5 days in a row    "
          f"{float(pnl.rolling(5).sum().min()):8.2f} vol pts")

    m = eq.resample("ME").last().dropna()
    mdd = float((m - m.cummax().clip(lower=0.0)).min())
    print(f"    same curve, MONTH ENDS   {mdd:8.2f} vol pts")
    if mdd:
        print(f"    -> the daily drawdown is {worst_d/mdd:.2f}x the "
              f"month-end one: month-end marks")
        print(f"       understate the loss actually carried by "
              f"{(worst_d/mdd-1)*100:.0f}%")

    print(f"\n  FEBRUARY 2018 -- absent from the monthly worst five")
    feb = pnl.loc["2018-01-25":"2018-02-28"]
    if len(feb):
        w = feb.idxmin()
        print(f"    worst day {w:%Y-%m-%d}  {float(feb.min()):+.2f} vol pts "
              f"= ${float(feb.min())*mult:+,.0f} per contract")
        print(f"    Jan 25 -> Feb 28 total   {float(feb.sum()):+.2f} vol pts")
        print(f"    peak-to-trough in window "
              f"{float((feb.cumsum() - feb.cumsum().cummax()).min()):+.2f}")
    print(f"    Close-to-close only. Intraday on 2018-02-05 was far worse,")
    print(f"    and a margin call does not wait for the settlement print.")

    print(f"\n  WHAT THIS DOES TO THE SIZE ({C['name']}, ${a.account:,.0f})")
    for label, d_ in (("monthly measure", a.monthly_dd),
                      ("daily measure", worst_d)):
        if not d_:
            continue
        n_dd = a.max_dd * a.account / (abs(d_) * mult)
        n_hold = a.account / (abs(d_) * mult + a.margin * (mult / 100.0)
                              * a.stress_mult)
        print(f"    {label:<18} drawdown {abs(d_):6.2f} vol pts  "
              f"-> {min(n_dd, n_hold):5.2f} contracts")
    print(f"    The minimum tradeable position is 1.")

    return dict(worst_daily=worst_d, worst_monthly=mdd,
                net_total=float(eq.iloc[-1]), rolls=len(rolls), hit=hit)


def self_test():
    import numpy as np, pandas as pd
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" +
              (f"   {detail}" if detail else ""))

    print(f"vix_daily_risk.py v{VERSION} self-test\n")

    print("the expiry calendar")
    exps = vx_expiries(pd.Timestamp("2018-01-01"), pd.Timestamp("2018-12-31"))
    check("twelve settlements in a year", len(exps) == 12, f"{len(exps)}")
    check("all fall on a Wednesday",
          all(e.dayofweek == 2 for e in exps),
          f"{sorted({e.day_name() for e in exps})}")
    #: 2018 January VX settled 2018-01-17. Third Friday of February 2018 was
    #: the 16th; 30 days before is the 17th, a Wednesday.
    check("the January 2018 settlement is 2018-01-17",
          exps[0] == pd.Timestamp("2018-01-17"), f"{exps[0]:%Y-%m-%d}")

    print("\na synthetic curve with KNOWN rolls, and the naive error it hides")
    #: contango: the front month sits 1.0 below the second and converges to
    #: an unchanging spot. A short front month should earn on every roll and
    #: nothing else. Any other answer is a reconstruction error.
    per, cycles, slope = 21, 24, 1.0
    days = pd.bdate_range("2010-01-04", periods=per * cycles)
    pos = np.arange(len(days)) % per                # days since last roll
    near = 20.0 + slope * (per - 1 - pos) / (per - 1)  # 21 -> 20, repeat
    n = pd.Series(near, index=days)
    f = n + slope
    rolls = [days[i] for i in range(len(days)) if pos[i] == 0 and i > 0]
    pnl, is_roll = daily_pnl(n, f, rolls)
    naive = float((-(n.diff())).dropna().sum())
    #: Assert the INVARIANT, not a hand-counted total. The first attempt
    #: asserted len(rolls) * slope and failed by 0.8 because the sample
    #: ended mid-cycle -- the arithmetic was right and the expectation was
    #: sloppy. corrected - naive == rolls x slope holds at any end point.
    check("corrected minus naive is exactly one slope per roll",
          abs((float(pnl.sum()) - naive) - len(rolls) * slope) < 1e-9,
          f"{float(pnl.sum())-naive:.3f} vs {len(rolls)*slope:.3f}")
    check("a short front month earns the roll-down and nothing else",
          abs(float(pnl.sum()) - cycles * slope) < 1e-9,
          f"{float(pnl.sum()):.3f} over {cycles} cycles")
    check("the NAIVE series throws that carry away",
          abs(naive - slope) < 1e-9 and float(pnl.sum()) > 20 * naive,
          f"naive {naive:+.3f} vs corrected {float(pnl.sum()):+.3f}")
    check("every roll day is flagged, and only those",
          int(is_roll.sum()) == len(rolls), f"{int(is_roll.sum())}")

    print("\nthe roll check can FAIL, and does when the calendar is wrong")
    #: NOISY sawtooth: a clean one makes any test look good. Daily noise is
    #: set at 0.55, the same order as the 1.0 slope, which is the regime
    #: that made the sign test useless.
    rng = np.random.default_rng(7)
    noise = pd.Series(np.cumsum(rng.normal(0, 0.55, len(days))), index=days)
    nn, ff = n + noise, f + noise
    lo_r, hi_r = ROLL_STEP_RATIO
    g_ratio, g_t, _, g_hit = roll_check(nn, ff, rolls)
    bad_days = [days[i] for i in range(len(days)) if pos[i] == 3 and i > 3]
    b_ratio, b_t, _, b_hit = roll_check(nn, ff, bad_days)
    check("the true calendar shows a one-slope step at high t",
          lo_r <= g_ratio <= hi_r and g_t >= ROLL_STEP_T_MIN,
          f"{g_ratio:.2f}x at t={g_t:.1f}")
    check("a calendar shifted three days shows no step",
          not (lo_r <= b_ratio <= hi_r and b_t >= ROLL_STEP_T_MIN),
          f"{b_ratio:.2f}x at t={b_t:.1f}")
    #: This is why the sign test was replaced. Record the ceiling rather
    #: than assert a threshold under it.
    check("the OLD sign test could not have separated them safely",
          g_hit < 0.85, f"perfect calendar scores only {g_hit*100:.0f}%")

    print("\nthe offset scan identifies the switch day, and can refuse")
    #: Build a series whose contract switches on the SETTLEMENT DATE
    #: (offset -1), not the day after, and check the scan recovers -1
    #: without being told. This is the case the real data appears to be.
    dd = pd.bdate_range("2006-01-03", "2016-12-30")
    ex = vx_expiries(dd[0], dd[-1])
    rng2 = np.random.default_rng(11)
    spot = pd.Series(np.cumsum(rng2.normal(0, 0.5, len(dd))) + 20.0,
                     index=dd)
    truth = roll_days(dd, ex, -1)
    tset, frac, k = set(truth), [], 0
    for ts in dd:
        if ts in tset:
            k = 0
        frac.append(max(0.0, 1.0 - k / 21.0))
        k += 1
    fr = pd.Series(frac, index=dd)
    n2 = spot + 1.0 * fr
    f2 = spot + 1.0 * (1.0 + fr)
    rows, best, second, clean = scan_offsets(n2, f2, ex)
    check("the scan finds the planted switch day without being told",
          clean and best["offset"] == -1,
          f"offset {best['offset']:+d} at t={best['t']:.1f}, "
          f"runner-up t={second['t']:.1f}")
    check("the neighbouring day does not look like a switch",
          abs(second["t"]) < 0.5 * best["t"],
          f"{abs(second['t']):.1f} vs half of {best['t']:.1f}")
    #: A VOLUME-based roll switches about a week early. Plant one at -6 --
    #: the offset the real export turned out to use -- and check the scan
    #: finds it, and that the old span of 4 could not have.
    truth6 = roll_days(dd, ex, -6)
    t6, frac6, k = set(truth6), [], 0
    for ts in dd:
        if ts in t6:
            k = 0
        frac6.append(max(0.0, 1.0 - k / 21.0))
        k += 1
    fr6 = pd.Series(frac6, index=dd)
    n6, f6 = spot + 1.0 * fr6, spot + 1.0 * (1.0 + fr6)
    _, b6, s6, c6 = scan_offsets(n6, f6, ex)
    check("a roll six days early is found with the default span",
          c6 and b6["offset"] == -6,
          f"offset {b6['offset']:+d} at t={b6['t']:.1f}")
    _, b4, s4, c4 = scan_offsets(n6, f6, ex, span=4)
    check("a span of 4 CANNOT see it, and refuses rather than guessing",
          not c4, f"best {b4['offset']:+d} at t={b4['t']:.1f}")
    #: Ranking by |t| let a large NEGATIVE step act as runner-up and veto a
    #: correctly identified roll. A switch can only step UP.
    rows6, _b, _s, _c = scan_offsets(n6, f6, ex)
    worst_neg = min(r["t"] for r in rows6)
    check("negative-step offsets are excluded from the runner-up slot",
          s6 is None or s6["ratio"] > 0,
          f"most negative rival t={worst_neg:.1f}, runner-up "
          f"ratio={s6['ratio']:.2f}" if s6 else "no rival")

    #: Smear the switch across three days: no single day carries it, and
    #: the scan must REFUSE rather than hand back the best-looking offset.
    sm = spot.copy()
    for ts in truth:
        p = dd.get_loc(ts)
        for j in range(3):
            if p + j < len(dd):
                sm.iloc[p + j:] += 0.333
    rows2, best2, second2, clean2 = scan_offsets(sm, sm + 1.0, ex)
    check("a switch smeared over three days is REFUSED, not fitted",
          not clean2,
          f"best offset {best2['offset']:+d} t={best2['t']:.1f}, "
          f"runner-up t={second2['t']:.1f}")

    print("\ncost is charged per roll, not per day")
    eq, n_hit, cost = curve(pnl, rolls, 2.0, 1.50, 100.0, 0.05)
    gross = float(pnl.sum())
    check("exactly one charge per roll", n_hit == len(rolls), f"{n_hit}")
    check("total cost is rolls x per-roll cost",
          abs(gross - float(eq.iloc[-1]) - len(rolls) * cost) < 1e-9,
          f"{gross - float(eq.iloc[-1]):.3f} vs "
          f"{len(rolls)*cost:.3f}")
    _, _, cost_vx = curve(pnl, rolls, 2.0, 1.50, 1000.0, 0.05)
    check("the flat commission costs the mini more in vol points",
          cost > cost_vx, f"{cost:.4f} vs {cost_vx:.4f}")

    print("\na daily path is never gentler than its own month ends")
    #: planted: a spike that fully round-trips inside one month is INVISIBLE
    #: at month-end and must not be invisible here
    d2 = pd.bdate_range("2020-01-01", periods=60)
    v = np.zeros(60)
    v[20] = -18.0
    v[21] = +18.0                       # fully recovered before month end
    s = pd.Series(v, index=d2)
    e = s.cumsum()
    daily_dd = float((e - e.cummax().clip(lower=0.0)).min())
    mm = e.resample("ME").last().dropna()
    month_dd = float((mm - mm.cummax().clip(lower=0.0)).min())
    check("an intramonth round trip is visible daily", daily_dd <= -18.0 + 1e-9,
          f"{daily_dd:.1f}")
    check("and invisible at month ends", month_dd == 0.0, f"{month_dd:.1f}")

    print("\nno strategy is optimised")
    import vix_daily_risk as _self
    bad_n = [x for x in dir(_self) if not x.startswith("_") and any(
        w in x.lower() for w in ("optimi", "sweep", "best_", "tune"))]
    check("no optimiser / sweep / tuner", bad_n == [], f"{bad_n}")

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vx1")
    ap.add_argument("--vx2")
    ap.add_argument("--tv-dir", nargs="?", const="~/Downloads")
    ap.add_argument("--account", type=float, default=10_000.0)
    ap.add_argument("--contract", default="VXM", choices=("VXM", "VX"))
    ap.add_argument("--roll-ticks", type=float, default=2.0)
    ap.add_argument("--commission", type=float, default=1.50)
    ap.add_argument("--margin", type=float, default=CB.MARGIN_NORMAL_VXM)
    ap.add_argument("--stress-mult", type=float,
                    default=CB.MARGIN_STRESS_MULT)
    ap.add_argument("--max-dd", type=float, default=CB.MAX_DD)
    ap.add_argument("--monthly-dd", type=float, default=-47.57,
                    help="the monthly-measure drawdown, for comparison")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    if a.tv_dir:
        import glob
        base = os.path.expanduser(a.tv_dir)

        def find(tag):
            hits = [h for h in glob.glob(os.path.join(base, "*.csv"))
                    if tag.lower() in os.path.basename(h).lower()]
            if not hits:
                raise SystemExit(f"  no *{tag}*.csv in {base}")
            return max(hits, key=os.path.getmtime)
        a.vx1, a.vx2 = find("VX1"), find("VX2")
    if not (a.vx1 and a.vx2):
        raise SystemExit("  need --vx1/--vx2 or --tv-dir")

    print(f"vix_daily_risk.py v{VERSION}   "
          f"DAILY RESOLUTION, NO STRATEGY OPTIMISED\n")
    vx1, vx2 = VC.load_csv(a.vx1, "VX1"), VC.load_csv(a.vx2, "VX2")
    i = vx1.index.intersection(vx2.index)
    vx1, vx2 = vx1.loc[i].sort_index(), vx2.loc[i].sort_index()
    print(f"  {len(i):,} common trading days "
          f"{i[0]:%Y-%m-%d} -> {i[-1]:%Y-%m-%d}")
    report(vx1, vx2, a)

    print("\n  STILL INVISIBLE")
    print("    Intraday. On 2018-02-05 VIX futures traded far beyond the")
    print("      settlement print, and margin is called on the path.")
    print("    The bid-ask on a roll day in a stressed market, which is")
    print("      wider than the 2 ticks charged here.")
    print("    Whether the broker raises margin mid-episode, which is the")
    print("      documented mechanism for being closed at the low.")


if __name__ == "__main__":
    main()
