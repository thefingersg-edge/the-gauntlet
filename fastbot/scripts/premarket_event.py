#!/usr/bin/env python3
"""PREREGISTRATION_v22 -- does volatility whose CAUSE IS KNOWN carry a sign?

RESULT_VOLCAUSE section 5 named this follow-up and this file is it. v21
asked whether the cause of volatility carries a sign, answered with
spread-and-volume PROXIES, and found nothing -- while the one cell where
the cause is actually known held 108 observations, because CPI, payrolls
and claims all release at 08:30 ET, an hour before the RTH open v21
sampled.

This is that cell with 1,059 observations instead of 108.

WHAT IS FROZEN, AND WHERE
-------------------------
Everything measured here was fixed in PREREGISTRATION_v22 before a
forward return touched a pre-market bar. Section numbers below refer to
that document. Nothing in this file chooses a horizon, a slot, a
stratum or a sign -- if it is a choice, v22 already made it.

    python3 premarket_event.py --self-test
    python3 premarket_event.py
"""

from __future__ import annotations

import argparse
import collections
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

#: ---- FROZEN IN v22. Every one of these is in the document. ----
SAMPLE_FROM = 2013           # section 2: bid == ask everywhere before 2012
SLOT = (8, 30)               # section 2: the 08:30 ET release bar
FOMC_SLOT = (14, 0)          # section 5: v21's original cell, carried on
H_PRIMARY = 4                # section 3: 08:45 -> 09:45, crossing the open
H_ROBUST = (1, 12)           # section 3: reported together, never swapped
GATE_A_T = 5.0               # section 4
GATE_T = 2.0                 # section 4
GATE_E_MULT = 2.0            # section 4
SANITY_MAX_BP = 30.0         # section 7: a bug until proven otherwise
N_ERAS = 3                   # section 4, Gate F
PRE_RELEASES = ("CLAIMS", "CPI", "NFP")


def cont_bp(o_sig, c_sig, entry, exit_):
    """Continuation in bp. POSITIVE = the move continued. v22 section 3.

    `entry` is the NEXT bar's open and is passed in by the caller, which
    is the only reason this function cannot be given the signal bar's
    close by accident -- the v18 bug, where an entry that carried no
    stop risk turned -0.136 R into +0.032 R and made a losing rule look
    like it beat its own control.
    """
    if entry <= 0 or exit_ <= 0 or c_sig == o_sig:
        return None
    d = 1.0 if c_sig > o_sig else -1.0
    return d * (exit_ / entry - 1.0) * 1e4


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


def slot_of(hh, mm):
    """The 15-minute bar a release at hh:mm lands in."""
    return (hh, (mm // 15) * 15)


def load_events(path, from_year=SAMPLE_FROM):
    """{date -> set(event names)} for releases landing in the SLOT bar.

    Reads the table and nothing else. There is no hardcoded date list in
    this file, deliberately: the event table is the instrument, and an
    instrument you can edit inline is not one.
    """
    pre, fomc = collections.defaultdict(set), collections.defaultdict(set)
    if not os.path.exists(path):
        return pre, fomc
    for r in csv.DictReader(open(path)):
        if not r.get("time_et") or r.get("time_quality") == "UNCERTAIN":
            continue
        try:
            d = dt.date.fromisoformat(r["date"])
            hh, mm = (int(x) for x in r["time_et"].split(":"))
        except ValueError:
            continue
        if d.year < from_year:
            continue
        s = slot_of(hh, mm)
        if r["event"] in PRE_RELEASES and s == SLOT:
            pre[d].add(r["event"])
        elif r["event"] == "FOMC" and s == FOMC_SLOT:
            fomc[d].add("FOMC")
    return pre, fomc


def gate_d_verdict(t_placebo, d_placebo, d_hyp):
    """Gate D, v22 section 4: the placebo must NOT mirror the effect.

    Same construction as v21's Gate D -- FAIL when the placebo shows the
    same sign at significance AND at more than half the size. Written as
    its own function so the self-test can drive it with numbers rather
    than hope the branch is right.
    """
    if t_placebo is None or d_hyp is None:
        return True
    return not (t_placebo >= GATE_T and d_placebo > 0.5 * d_hyp)


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"premarket_event.py v{VERSION} self-test\n")

    print("continuation is signed the way v22 section 3 fixed it")
    check("an UP bar followed by a rise is POSITIVE",
          cont_bp(100.0, 101.0, 101.0, 102.0) > 0)
    #: PLANTED: this is the half people get wrong. A DOWN bar that keeps
    #: falling is CONTINUATION and must be positive, not negative.
    check("a DOWN bar that keeps falling is also POSITIVE",
          cont_bp(100.0, 99.0, 99.0, 98.0) > 0,
          f"{cont_bp(100.0, 99.0, 99.0, 98.0):+.1f} bp")
    check("a DOWN bar that rebounds is NEGATIVE (reversion)",
          cont_bp(100.0, 99.0, 99.0, 100.0) < 0)
    check("a doji has no direction and returns None",
          cont_bp(100.0, 100.0, 100.0, 101.0) is None)
    #: PLANTED: the v18 bug in its v22 clothes. Entry is the NEXT bar's
    #: open. If the signal close were used instead, a bar that gapped
    #: between close and next open would report a different number --
    #: and it is exactly the release bar that gaps.
    sig_close, next_open, ex = 100.0, 100.5, 101.0
    as_specified = cont_bp(99.0, sig_close, next_open, ex)
    the_bug = cont_bp(99.0, sig_close, sig_close, ex)
    check("entry at the NEXT OPEN differs from entry at the signal close",
          abs(as_specified - the_bug) > 10.0,
          f"{as_specified:+.1f} bp specified vs {the_bug:+.1f} bp if the "
          f"close were taken -- a 50 bp gap is worth 49 bp of fiction")

    print("\nthe test statistics behave")
    check("welch_t sees a real difference",
          welch_t([1.0] * 30 + [1.2] * 30, [0.0] * 30 + [0.2] * 30)[0] > 5)
    check("and reports None rather than dividing by zero",
          welch_t([1.0] * 5, [1.0] * 5) == (None, None))
    check("one_sample_t is zero on a symmetric sample",
          abs(one_sample_t([-1.0, 1.0, -1.0, 1.0])) < 1e-9)
    check("and positive on a shifted one", one_sample_t([1.0, 1.1, 0.9]) > 5)

    print("\neras partition the sample -- disjoint, and nothing dropped")
    seq = list(range(100))
    ee = eras(seq)
    check("three eras", len(ee) == 3)
    check("they cover every observation", sorted(x for e in ee for x in e)
          == seq)
    check("and share none", len({id(x) for e in ee for x in e}) == 100)
    check("the remainder lands in the last era, not the floor",
          len(ee[-1]) == 34, f"{[len(e) for e in ee]}")

    print("\na release is matched to the BAR that contains it")
    check("08:30 lands in the 08:30 bar", slot_of(8, 30) == (8, 30))
    #: PLANTED: a release at 08:31 is still the 08:30 bar. Flooring to
    #: the quarter hour is what makes the table's minute field usable.
    check("08:31 still lands in the 08:30 bar", slot_of(8, 31) == (8, 30))
    check("08:45 is a DIFFERENT bar", slot_of(8, 45) == (8, 45))
    check("14:00 is the FOMC bar", slot_of(14, 0) == FOMC_SLOT)

    print("\nthe event table is read, and read strictly")
    import tempfile
    fd, p = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["event", "date", "time_et",
                                           "time_quality", "press_conference",
                                           "pc_quality", "source", "note"])
        w.writeheader()
        for ev, d, t, q in [("CPI", "2015-03-24", "08:30", "RULE"),
                            ("CLAIMS", "2015-03-26", "08:30", "RULE"),
                            ("NFP", "2015-04-03", "08:30", "RULE"),
                            ("FOMC", "2015-03-18", "14:00", "SOURCED"),
                            #: PLANTED: pre-2013 must be excluded
                            ("CPI", "2009-03-18", "08:30", "RULE"),
                            #: PLANTED: UNCERTAIN must be excluded
                            ("FOMC", "2015-06-17", "14:00", "UNCERTAIN"),
                            #: PLANTED: a release at another hour is not
                            #: this slot's event and must not be counted
                            ("CPI", "2015-05-22", "10:00", "RULE")]:
            w.writerow(dict(event=ev, date=d, time_et=t, time_quality=q,
                            press_conference="", pc_quality="", source="x",
                            note="y"))
    pre, fomc = load_events(p)
    os.unlink(p)
    check("three 08:30 releases are found", len(pre) == 3, f"{sorted(pre)}")
    check("the 2009 row is excluded -- the sample starts 2013",
          dt.date(2009, 3, 18) not in pre)
    check("the 10:00 CPI is NOT an 08:30 event",
          dt.date(2015, 5, 22) not in pre)
    check("the SOURCED FOMC is found", len(fomc) == 1, f"{sorted(fomc)}")
    check("and the UNCERTAIN one is not",
          dt.date(2015, 6, 17) not in fomc,
          "an unknown release time is a different test wearing this one's name")
    check("each day carries which release it was",
          pre[dt.date(2015, 3, 26)] == {"CLAIMS"})

    print("\nGate D fires when the placebo MIRRORS the effect")
    #: PLANTED: the whole point of the placebo. If the day BEFORE a
    #: release shows the same thing, what was found is a property of
    #: 08:30, not of information arriving at 08:30.
    check("a placebo showing the same size and sign FAILS the gate",
          not gate_d_verdict(3.0, 4.0, 5.0),
          "t=3.0, 4.0 bp against a 5.0 bp hypothesis -- that is the effect")
    check("a placebo showing nothing PASSES",
          gate_d_verdict(0.3, 0.1, 5.0))
    check("a significant but much SMALLER placebo passes",
          gate_d_verdict(3.0, 1.0, 5.0),
          "1.0 bp against 5.0 -- real, but not the same thing")
    #: PLANTED: a gate that can only fail one way has been half tested.
    check("and the gate is not simply always-true",
          not gate_d_verdict(2.0, 3.0, 5.0))

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bid", default="../data/spx500usd_bid_15m.csv")
    ap.add_argument("--ask", default="../data/spx500usd_ask_15m.csv")
    ap.add_argument("--events", default="../data/events_v2.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"premarket_event.py v{VERSION}   PREREGISTRATION_v22\n")
    print("  I am not a financial adviser. This is a measurement, not a")
    print("  recommendation to take a position.\n")

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

    #: the SLOT bar of every day in the sample, and the FOMC bar too
    slot_bar, fomc_bar = {}, {}
    for t in common:
        e = t.astimezone(ET)
        if e.year < SAMPLE_FROM:
            continue
        if (e.hour, e.minute) == SLOT:
            slot_bar[e.date()] = t
        elif (e.hour, e.minute) == FOMC_SLOT:
            fomc_bar[e.date()] = t
    print(f"  {SLOT[0]:02d}:{SLOT[1]:02d} ET bars from {SAMPLE_FROM}: "
          f"{len(slot_bar):,}")

    pre_ev, fomc_ev = load_events(a.events)
    ev_days = sorted(d for d in pre_ev if d in slot_bar)
    ctl_days = sorted(d for d in slot_bar if d not in pre_ev)
    #: v22 section 4, Gate D: the same slot on the day BEFORE a release,
    #: unless that day is itself a release.
    plc_days = sorted({d - dt.timedelta(days=1) for d in ev_days}
                      & set(slot_bar) - set(pre_ev))
    print(f"  release days {len(ev_days):,}   control days "
          f"{len(ctl_days):,}   placebo days {len(plc_days):,}")
    #: the two sets must partition the slot's days, or one of them is
    #: quietly carrying the other's observations
    assert len(ev_days) + len(ctl_days) == len(slot_bar), "sets overlap"

    def observe(days, bars, H=H_PRIMARY):
        out = []
        for d in days:
            t = bars.get(d)
            if t is None:
                continue
            nxt, ex = mid.get(t + BAR), mid.get(t + BAR * H)
            if not nxt or not ex:
                continue
            o, h, l, c = mid[t]
            cb = cont_bp(o, c, nxt[0], ex[3])
            if cb is None:
                continue
            out.append(dict(d=d, t=t, cont=cb, sp=spread[t], vol=vol[t],
                            move=abs(c / o - 1.0) * 1e4,
                            rng=(h - l) / o * 1e4))
        return out

    ev = observe(ev_days, slot_bar)
    ctl = observe(ctl_days, slot_bar)
    plc = observe(plc_days, slot_bar)
    print(f"  usable: release {len(ev):,}   control {len(ctl):,}   "
          f"placebo {len(plc):,}\n")

    #: ---- GATE A -- the positive control, and it can void the run ----
    ta, da = welch_t([x["move"] for x in ev], [x["move"] for x in ctl])
    ga = ta is not None and ta >= GATE_A_T
    print(f"  GATE A -- positive control: does a release MOVE the bar?")
    print(f"    release  |move| {st.mean(x['move'] for x in ev):6.2f} bp"
          f"   range {st.mean(x['rng'] for x in ev):6.2f} bp"
          f"   vol {st.median(x['vol'] for x in ev):6.0f}")
    print(f"    control  |move| {st.mean(x['move'] for x in ctl):6.2f} bp"
          f"   range {st.mean(x['rng'] for x in ctl):6.2f} bp"
          f"   vol {st.median(x['vol'] for x in ctl):6.0f}")
    print(f"    diff {da:+.2f} bp   t = {ta:.1f}   "
          f"[{'PASS' if ga else 'FAIL'}]")
    if not ga:
        print(f"\n    VOID -- v22 section 4. This gate tests the EVENT")
        print(f"    TABLE as much as the market: 1,059 timestamps built")
        print(f"    from ALFRED and the Fed and never before checked")
        print(f"    against a price. Failing here means the table, not")
        print(f"    the market, is what was measured.")
        sys.exit(3)

    #: ---- the hypothesis ----
    ec = [x["cont"] for x in ev]
    cc = [x["cont"] for x in ctl]
    pc = [x["cont"] for x in plc]
    tb = one_sample_t(ec)
    gb = tb is not None and tb >= GATE_T
    tc, dc = welch_t(ec, cc)
    gc = tc is not None and tc >= GATE_T
    tp, dp = welch_t(pc, cc)
    gd = gate_d_verdict(tp, dp, dc)
    sp_ev = st.mean(x["sp"] for x in ev)
    ge = dc is not None and abs(dc) > GATE_E_MULT * sp_ev

    print(f"\n  CONTINUATION at H={H_PRIMARY} (08:45 -> 09:45 ET), "
          f"negative = reversion")
    for lab, s in (("release  ", ec), ("control  ", cc), ("placebo  ", pc)):
        print(f"    {lab}n={len(s):>6,}   cont {st.mean(s):+6.2f} bp   "
              f"t {one_sample_t(s):+6.2f}")

    #: ---- Gate F -- three disjoint eras ----
    all_days = sorted(set(ev_days) | set(ctl_days))
    era_d, era_lab = [], []
    for e in eras(all_days):
        s = set(e)
        q = [x["cont"] for x in ev if x["d"] in s]
        w = [x["cont"] for x in ctl if x["d"] in s]
        era_lab.append(f"{e[0].year}-{e[-1].year}")
        era_d.append(st.mean(q) - st.mean(w)
                     if len(q) > 20 and len(w) > 20 else 0.0)
    gf = all(x > 0 for x in era_d)

    #: ---- Gate G -- the mechanism, PAIRED on the same bars ----
    h1 = {x["d"]: x["cont"] for x in observe(ev_days, slot_bar, H=1)}
    pairs = [x["cont"] - h1[x["d"]] for x in ev if x["d"] in h1]
    tg = one_sample_t(pairs)
    gg = tg is not None and tg >= GATE_T

    print(f"\n  VERDICT -- gates frozen in PREREGISTRATION_v22 section 4")
    print(f"    [{'PASS' if gb else 'FAIL'}] Gate B  release bars "
          f"{st.mean(ec):+.2f} bp, t = {tb:.2f}   (continuation?)")
    print(f"    [{'PASS' if gc else 'FAIL'}] Gate C  release minus control "
          f"{dc:+.2f} bp, t = {tc:.2f}   <- THE HYPOTHESIS")
    print(f"    [{'PASS' if gd else 'FAIL'}] Gate D  placebo (day before) "
          f"{dp:+.2f} bp, t = {tp:.2f}   (must NOT mirror it)")
    print(f"    [{'PASS' if ge else 'FAIL'}] Gate E  {abs(dc):.2f} bp vs "
          f"{GATE_E_MULT:.0f}x the {sp_ev:.2f} bp spread paid = "
          f"{GATE_E_MULT * sp_ev:.2f}")
    print(f"    [{'PASS' if gf else 'FAIL'}] Gate F  eras  "
          + "  ".join(f"{l} {x:+.2f}" for l, x in zip(era_lab, era_d)))
    print(f"    [{'PASS' if gg else 'FAIL'}] Gate G  H=4 minus H=1, paired "
          f"{st.mean(pairs):+.2f} bp, t = {tg:.2f}   <- THE MECHANISM")
    allp = gb and gc and gd and ge and gf
    print(f"\n    {'PROCEED' if allp else 'FAIL'}")

    #: ---- the registered breakdown. v22 section 5: a BREAKDOWN, not a
    #: ---- menu. If the pooled result failed, a stratum passing here is
    #: ---- a finding needing its own confirmation run, not this result.
    print(f"\n  REGISTERED BREAKDOWN -- v22 section 5, NOT a menu")
    print(f"    {'':<9}{'n':>6}{'|move|':>9}{'cont bp':>10}{'t':>7}"
          f"{'vs control':>12}")
    for name in PRE_RELEASES:
        sub = [x for x in ev if name in pre_ev[x["d"]]]
        if len(sub) < 20:
            continue
        s = [x["cont"] for x in sub]
        t_s, d_s = welch_t(s, cc)
        print(f"    {name:<9}{len(s):>6,}"
              f"{st.mean(x['move'] for x in sub):>9.2f}"
              f"{st.mean(s):>10.2f}{one_sample_t(s):>7.2f}"
              f"{d_s:>+9.2f} t{t_s:>+5.2f}")
    fo = observe(sorted(d for d in fomc_ev if d in fomc_bar), fomc_bar)
    if len(fo) >= 20:
        s = [x["cont"] for x in fo]
        print(f"    {'FOMC':<9}{len(s):>6,}"
              f"{st.mean(x['move'] for x in fo):>9.2f}"
              f"{st.mean(s):>10.2f}{one_sample_t(s):>7.2f}"
              f"{'':>12}  14:00 RTH -- v21's cell, n was 108")

    print(f"\n  ROBUSTNESS at the pre-specified horizons "
          f"(v22 section 3, reported together)")
    for H in H_ROBUST:
        e2 = [x["cont"] for x in observe(ev_days, slot_bar, H=H)]
        c2 = [x["cont"] for x in observe(ctl_days, slot_bar, H=H)]
        if len(e2) > 50 and len(c2) > 50:
            t2, d2 = welch_t(e2, c2)
            end = "09:00 ET, still pre-market" if H == 1 else "11:45 ET, RTH"
            print(f"    H={H:>2}  release {st.mean(e2):+6.2f}  control "
                  f"{st.mean(c2):+6.2f}  diff {d2:+6.2f}  t {t2:+5.2f}"
                  f"   exit {end}")

    print(f"\n  WHAT THE CONTROL CARRIES -- named in advance, not excused")
    print(f"    v22 section 2 fixes the control as every non-release day at")
    print(f"    this slot, and that includes FOMC days and their D-1. "
          f"RESULT_PREANN")
    print(f"    measured real drift in exactly those mornings, so the "
          f"control is not")
    print(f"    inert: if anything it is biased UPWARD, which biases Gate C")
    print(f"    DOWNWARD. Reported, not corrected -- the spec was frozen.")

    if dc is not None and abs(dc) > SANITY_MAX_BP:
        print(f"\n    KILL: {dc:+.2f} bp exceeds {SANITY_MAX_BP} "
              f"(v22 section 7)")
        sys.exit(3)


if __name__ == "__main__":
    main()
