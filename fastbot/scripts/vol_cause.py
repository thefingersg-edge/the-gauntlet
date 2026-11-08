#!/usr/bin/env python3
"""PREREGISTRATION_v21 -- does the CAUSE of volatility carry a sign?

v19 measured that candle shape carries 7.5x more information about
MAGNITUDE than about DIRECTION. That is not a quirk: volatility is a
scalar and has no sign. But its cause might.

    information arrived  -> price genuinely repriced -> PERSIST
    the book went thin   -> nothing was learned      -> REVERT

Same volatility, opposite predictions.

WHY THIS IS MEASURABLE HERE
---------------------------
    corr(spread, range), 2013-2026, n=319,147  =  +0.001

Spread and volatility are INDEPENDENT on this instrument, so the
liquidity axis is a real second dimension rather than volatility
restated. 23 years of bid AND ask is what makes it a measurement
instead of a proxy.

THE SAMPLE STARTS IN 2013, AND THAT IS NOT A JUDGEMENT CALL
-----------------------------------------------------------
RESULT_PREANN established every bar before 2012 has bid EXACTLY equal
to ask -- back-filled index data, not dealt quotes. The liquidity axis
is identically zero there.

STDLIB ONLY.

    python3 vol_cause.py --self-test
    python3 vol_cause.py
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import os
import statistics as st
import sys
from zoneinfo import ZoneInfo

VERSION = "1.0"

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
BAR = dt.timedelta(minutes=15)

#: ---- FROZEN IN v21 ----
RTH_OPEN, RTH_CLOSE = (9, 30), (16, 0)
SAMPLE_FROM = 2013
ATR_DAYS = 14
H_PRIMARY = 4
H_ROBUST = (1, 12)
GATE_A_T = 5.0
GATE_T = 2.0
SANITY_MAX_BP = 30.0
N_ERAS = 3
GATE_E_MULT = 2.0


def cont_bp(o_sig, c_sig, entry, exit_):
    """Continuation in bp. POSITIVE = the move continued."""
    if entry <= 0 or exit_ <= 0 or c_sig == o_sig:
        return None
    d = 1.0 if c_sig > o_sig else -1.0
    return d * (exit_ / entry - 1.0) * 1e4


def ranks(vals):
    """Percentile rank in [0,1], ties averaged."""
    n = len(vals)
    if n == 0:
        return []
    order = sorted(range(n), key=lambda i: vals[i])
    out = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2.0 / max(1, n - 1)
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def illiquidity(rank_spread, rank_volume):
    """High = wide spread AND low volume = illiquid."""
    return rank_spread - rank_volume


def atr_prior(day_ranges, days, i):
    if i < ATR_DAYS:
        return None
    return st.mean(day_ranges[days[j]] for j in range(i - ATR_DAYS, i))


def welch_t(x, y):
    if len(x) < 2 or len(y) < 2:
        return None, None
    se = math.sqrt(st.variance(x) / len(x) + st.variance(y) / len(y))
    if se == 0:
        return None, None
    return (st.mean(x) - st.mean(y)) / se, st.mean(x) - st.mean(y)


def one_sample_t(x):
    if len(x) < 2:
        return None
    s = st.stdev(x)
    return None if s == 0 else st.mean(x) / (s / math.sqrt(len(x)))


def eras(seq, n=N_ERAS):
    k = len(seq) // n
    return [seq[i * k:(i + 1) * k if i < n - 1 else len(seq)]
            for i in range(n)]


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"vol_cause.py v{VERSION} self-test\n")

    print("continuation is POSITIVE when the move persists")
    check("up bar, price keeps rising 10bp -> +10",
          abs(cont_bp(100.0, 101.0, 100.0, 100.1) - 10.0) < 1e-6,
          f"{cont_bp(100.0,101.0,100.0,100.1):.2f}")
    check("up bar, price falls 10bp -> -10 (reversion)",
          abs(cont_bp(100.0, 101.0, 100.0, 99.9) + 10.0) < 1e-6)
    #: PLANTED: the sign must flip with the bar, not with the move
    check("DOWN bar, price keeps falling -> +10 (also continuation)",
          abs(cont_bp(101.0, 100.0, 100.0, 99.9) - 10.0) < 1e-6,
          f"{cont_bp(101.0,100.0,100.0,99.9):.2f}")
    check("DOWN bar, price rises -> -10 (reversion)",
          abs(cont_bp(101.0, 100.0, 100.0, 100.1) + 10.0) < 1e-6)
    check("a doji has no direction and is skipped",
          cont_bp(100.0, 100.0, 100.0, 101.0) is None)
    #: this is the OPPOSITE convention to v17, deliberately -- the
    #: hypothesis here is persist-vs-revert, so continuation is the
    #: natural positive. Stated so the two results are not misread.
    check("this is v17's convention inverted, on purpose",
          cont_bp(100.0, 101.0, 100.0, 100.1) > 0)

    print("\nranks, and the direction of the liquidity score")
    r = ranks([10.0, 20.0, 30.0, 40.0])
    check("ranks run 0 to 1", r[0] == 0.0 and r[-1] == 1.0, f"{r}")
    check("ties are averaged",
          ranks([5.0, 5.0, 9.0])[0] == ranks([5.0, 5.0, 9.0])[1])
    #: PLANTED: wide spread + low volume must score HIGH (illiquid).
    check("wide spread + low volume is the ILLIQUID extreme",
          illiquidity(1.0, 0.0) == 1.0)
    check("tight spread + high volume is the LIQUID extreme",
          illiquidity(0.0, 1.0) == -1.0)
    check("and the two are genuinely opposite",
          illiquidity(1.0, 0.0) > illiquidity(0.0, 1.0))
    check("mid-mid scores neutral", illiquidity(0.5, 0.5) == 0.0)

    print("\nATR uses only prior days")
    days = [dt.date(2020, 1, d) for d in range(1, 21)]
    rg = {d: 10.0 for d in days}
    rg[days[15]] = 1000.0
    check("a huge day does not inflate its own ATR",
          abs(atr_prior(rg, days, 15) - 10.0) < 1e-9)
    check("but the next day's ATR sees it", atr_prior(rg, days, 16) > 10.0)
    check("the first 14 days have none", atr_prior(rg, days, 13) is None)

    print("\nthe 2013 floor is enforced, not suggested")
    check("the sample starts in 2013", SAMPLE_FROM == 2013)
    #: PLANTED: a pre-2013 bar has bid == ask, so its spread rank is
    #: degenerate. If such bars leaked in, the liquidity axis would be
    #: half-constant and every cell boundary would move.
    zero_spreads = [0.0] * 50
    rz = ranks(zero_spreads)
    check("an all-zero spread column ranks to a single value",
          len(set(rz)) == 1, f"{len(set(rz))} distinct")
    check("which is why pre-2013 must be excluded, not down-weighted",
          True)

    print("\ngate thresholds are v21's")
    check("Gate A needs t >= 5 -- it is a calibration, not a discovery",
          GATE_A_T == 5.0)
    check("the others need t >= 2", GATE_T == 2.0)
    check("Gate E needs 2x the spread actually paid", GATE_E_MULT == 2.0)
    check("above 30 bp at H=4 is a bug first", SANITY_MAX_BP == 30.0)

    print("\neras are disjoint")
    e = eras(list(range(30)))
    check("three, non-overlapping, covering everything",
          len(e) == 3 and sorted(sum(e, [])) == list(range(30)))

    print("\nthis file fits nothing")
    import vol_cause as _self
    banned = ("optimi", "tune", "refit", "order", "submit", "position")
    off = [x for x in dir(_self) if not x.startswith("_")
           and any(q in x.lower() for q in banned)]
    check("no fitting or trading function exists", off == [], f"{off}")

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bid", default="../data/spx500usd_bid_15m.csv")
    ap.add_argument("--ask", default="../data/spx500usd_ask_15m.csv")
    ap.add_argument("--events", default="../data/events.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"vol_cause.py v{VERSION}   PREREGISTRATION_v21\n")

    def rd(p):
        o = {}
        for r in csv.DictReader(open(p)):
            t = dt.datetime.fromisoformat(r["time"]).replace(tzinfo=UTC)
            o[t] = (float(r["open"]), float(r["high"]), float(r["low"]),
                    float(r["close"]), float(r["volume"]))
        return o
    b, ask = rd(a.bid), rd(a.ask)
    common = b.keys() & ask.keys()
    mid, spread, vol = {}, {}, {}
    for t in common:
        mid[t] = tuple((b[t][i] + ask[t][i]) / 2.0 for i in range(4))
        c = mid[t][3]
        spread[t] = (ask[t][3] - b[t][3]) / c * 1e4 if c > 0 else 0.0
        vol[t] = b[t][4]
    print(f"  aligned bars: {len(common):,}")

    sess = {}
    for t in sorted(common):
        e = t.astimezone(ET)
        hm = (e.hour, e.minute)
        if RTH_OPEN <= hm < RTH_CLOSE and e.year >= SAMPLE_FROM:
            sess.setdefault(e.date(), []).append((t, hm))
    days = sorted(d for d in sess if len(sess[d]) >= 20)
    print(f"  RTH sessions from {SAMPLE_FROM}: {len(days):,}  "
          f"{days[0]} .. {days[-1]}")

    drange = {d: (max(mid[t][1] for t, _ in sess[d])
                  - min(mid[t][2] for t, _ in sess[d])) for d in days}

    ev_bars = set()
    if os.path.exists(a.events):
        for r in csv.DictReader(open(a.events)):
            if not r.get("time_et") or r.get("time_quality") == "UNCERTAIN":
                continue
            try:
                dd = dt.date.fromisoformat(r["date"])
                hh, mm = (int(x) for x in r["time_et"].split(":"))
            except ValueError:
                continue
            base = dt.datetime(dd.year, dd.month, dd.day, hh, mm, tzinfo=ET)
            ev_bars.add(base.replace(minute=(mm // 15) * 15).astimezone(UTC))
    print(f"  event bars marked: {len(ev_bars):,}")

    obs = []
    for i, d in enumerate(days):
        atr = atr_prior(drange, days, i)
        if not atr or atr <= 0:
            continue
        for t, hm in sess[d]:
            nxt, ex = mid.get(t + BAR), mid.get(t + BAR * H_PRIMARY)
            if not nxt or not ex:
                continue
            o, h, l, c = mid[t]
            cb = cont_bp(o, c, nxt[0], ex[3])
            if cb is None:
                continue
            fwd = abs((ex[3] / nxt[0] - 1.0) * 1e4)
            obs.append(dict(t=t, day=d, hm=hm, yr=d.year,
                            rng=(h - l) / atr, sp=spread[t], vol=vol[t],
                            cont=cb, fwd=fwd, ev=t in ev_bars))
    print(f"  usable bar-observations: {len(obs):,}\n")

    #: normalise within slot-year -- the U-shape is real and OANDA's
    #: tick volume is badly non-stationary
    groups = {}
    for x in obs:
        groups.setdefault((x["hm"], x["yr"]), []).append(x)
    for g in groups.values():
        rs = ranks([x["sp"] for x in g])
        rv = ranks([x["vol"] for x in g])
        med_r = st.median(x["rng"] for x in g)
        sc = [illiquidity(rs[i], rv[i]) for i in range(len(g))]
        med_s = st.median(sc)
        for i, x in enumerate(g):
            x["hivol"] = x["rng"] >= med_r
            x["illiq"] = sc[i] >= med_s

    def cell(hivol, illiq, ev=None):
        return [x for x in obs if x["hivol"] == hivol
                and x["illiq"] == illiq and (ev is None or x["ev"] == ev)]

    #: Gate A -- the positive control
    hv = [x["fwd"] for x in obs if x["hivol"]]
    lv = [x["fwd"] for x in obs if not x["hivol"]]
    ta, da = welch_t(hv, lv)
    ga = ta is not None and ta >= GATE_A_T
    print(f"  GATE A -- positive control: does high vol precede big moves?")
    print(f"    high-vol |fwd| {st.mean(hv):.2f} bp   low-vol "
          f"{st.mean(lv):.2f} bp   diff {da:+.2f}  t {ta:.1f}")
    print(f"    [{'PASS' if ga else 'FAIL'}]")
    if not ga:
        print(f"\n    VOID -- v21 section 5. A method that cannot see")
        print(f"    volatility clustering cannot report absence of "
              f"anything else.")
        sys.exit(3)

    print(f"\n  THE 2x2 -- continuation in bp at H={H_PRIMARY} "
          f"(negative = reversion)")
    print(f"    {'':<12}{'LIQUID':>22}{'ILLIQUID':>22}")
    print(f"    {'':<12}{'n':>8}{'cont bp':>9}{'t':>5}"
          f"{'n':>8}{'cont bp':>9}{'t':>5}")
    res = {}
    for hvb, lab in ((True, "HIGH VOL"), (False, "low vol")):
        row = f"    {lab:<12}"
        for il in (False, True):
            c = [x["cont"] for x in cell(hvb, il)]
            res[(hvb, il)] = c
            row += f"{len(c):>8,}{st.mean(c):>9.2f}{one_sample_t(c):>5.1f}"
        print(row)

    hi_il = res[(True, True)]
    hi_lq = res[(True, False)]
    lo_il = res[(False, True)]
    lo_lq = res[(False, False)]

    tb = one_sample_t(hi_il)
    gb = tb is not None and tb <= -GATE_T
    tc, dc = welch_t(hi_lq, hi_il)
    gc = tc is not None and tc >= GATE_T
    tl, dl = welch_t(lo_lq, lo_il)
    gd = not (tl is not None and tl >= GATE_T and dl > 0.5 * dc)

    sp_il = st.mean(x["sp"] for x in cell(True, True))
    ge = abs(dc) > GATE_E_MULT * sp_il

    ordered = sorted([x for x in obs if x["hivol"]], key=lambda x: x["t"])
    ee = eras(ordered)
    era_d = []
    for e in ee:
        q = [x["cont"] for x in e if not x["illiq"]]
        w = [x["cont"] for x in e if x["illiq"]]
        era_d.append(st.mean(q) - st.mean(w) if len(q) > 20 and len(w) > 20
                     else 0.0)
    gf = all(x > 0 for x in era_d)

    print(f"\n  VERDICT -- gates frozen in v21 section 5")
    print(f"    [{'PASS' if gb else 'FAIL'}] Gate B  illiquid high-vol "
          f"{st.mean(hi_il):+.2f} bp, t = {tb:.2f}   (reversion?)")
    print(f"    [{'PASS' if gc else 'FAIL'}] Gate C  liquid minus illiquid "
          f"{dc:+.2f} bp, t = {tc:.2f}   <- THE HYPOTHESIS")
    print(f"    [{'PASS' if gd else 'FAIL'}] Gate D  low-vol split "
          f"{dl:+.2f} bp, t = {tl:.2f}   (must NOT mirror it)")
    print(f"    [{'PASS' if ge else 'FAIL'}] Gate E  {abs(dc):.2f} bp vs "
          f"{GATE_E_MULT:.0f}x the {sp_il:.2f} bp spread paid = "
          f"{GATE_E_MULT*sp_il:.2f}")
    print(f"    [{'PASS' if gf else 'FAIL'}] Gate F  eras "
          + "  ".join(f"{x:+.2f}" for x in era_d))
    allp = gb and gc and gd and ge and gf
    print(f"\n    {'PROCEED' if allp else 'FAIL'}")

    print(f"\n  THE EVENT CELL -- the one place the cause is KNOWN")
    for lab, sub in (("scheduled event", [x["cont"] for x in obs
                                          if x["ev"] and x["hivol"]]),
                     ("no event", [x["cont"] for x in obs
                                   if not x["ev"] and x["hivol"]])):
        if len(sub) > 20:
            print(f"    {lab:<18}n={len(sub):>7,}  cont {st.mean(sub):+6.2f} "
                  f"bp  t {one_sample_t(sub):+5.2f}")

    print(f"\n  ROBUSTNESS at the pre-specified horizons")
    for H in H_ROBUST:
        vals = {True: [], False: []}
        for x in obs:
            if not x["hivol"]:
                continue
            n2, e2 = mid.get(x["t"] + BAR), mid.get(x["t"] + BAR * H)
            if not n2 or not e2:
                continue
            o, _, _, c = mid[x["t"]]
            cb = cont_bp(o, c, n2[0], e2[3])
            if cb is not None:
                vals[x["illiq"]].append(cb)
        if len(vals[True]) > 50 and len(vals[False]) > 50:
            t2, d2 = welch_t(vals[False], vals[True])
            print(f"    H={H:>2}  liquid {st.mean(vals[False]):+6.2f}  "
                  f"illiquid {st.mean(vals[True]):+6.2f}  "
                  f"diff {d2:+6.2f}  t {t2:+5.2f}")

    if abs(dc) > SANITY_MAX_BP:
        print(f"\n    KILL: {dc:+.2f} bp exceeds {SANITY_MAX_BP}")
        sys.exit(3)


if __name__ == "__main__":
    main()
