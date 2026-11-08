#!/usr/bin/env python3
"""PREREGISTRATION_v24 -- does the 30-minute signal bar survive new instruments?

WRITTEN BEFORE THE DATA EXISTED. v24 section 7: "the measurement code is
written against this document, not against a first look at the data." If
this file is edited after the first run, that edit is the run.

THE CLAIM UNDER TEST
--------------------
On SPX500_USD, deciding the release fade at 09:00 (a 30-minute signal
bar) instead of 08:45 lifted the Sharpe from 0.34 to 0.54. The
improvement is +0.20 Sharpe against a standard error of 0.21, and paired
it is +2.69 bp at t = 1.63 -- one standard error, chosen as the best of
four variants, on the sample that produced it. That is exactly what
picking the maximum of four draws buys for free.

    python3 premarket_instruments.py --self-test
    python3 premarket_instruments.py --data-dir ../data/v24
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

from premarket_event import load_events, one_sample_t

VERSION = "1.1"

#: v1.1 -- PREREGISTRATION_v24.1. Gate A was mis-specified: it used the
#: release-fade base effect -- t = 2.77 on the instrument it was
#: DISCOVERED on -- as a positive control. That is not a control, it is
#: the hypothesis wearing a control's name, and a marginal effect
#: failing to clear t = 2.0 elsewhere says nothing about the pipeline.
#:
#: Replaced with v22's Gate A: do the event timestamps land on bars that
#: MOVE? Near-certain, and it tests what a control is for. The original
#: is still computed and still printed, labelled as what it actually is.
#:
#: v24.1 section 3, the safeguard: this amendment may ONLY license
#: reading a NULL. If Gate B or Gate C passes, the void STANDS and fresh
#: data is required. That asymmetry is enforced in code below, not left
#: to judgement on the day.
AMENDED_GATE_A_T = 5.0


def welch_t(x, y):
    if len(x) < 2 or len(y) < 2:
        return None
    se = math.sqrt(st.variance(x) / len(x) + st.variance(y) / len(y))
    return None if se == 0 else (st.mean(x) - st.mean(y)) / se

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
BAR = dt.timedelta(minutes=15)

#: ---- FROZEN IN v24 ----
SLOT = (8, 30)                          # section 4
RELEASES = ("CPI", "NFP")               # section 4 -- CLAIMS excluded, declared
MIN_EVENTS = 150                        # section 4 -- set before the fetch
GATE_A_T = 2.0                          # section 5
GATE_T = 2.0
SANITY_MAX_BP = 30.0                    # section 7
#: section 3. The groups are fixed here; adding an instrument after a
#: result is the kill condition in section 7.
NEAR_CLONES = ("NAS100_USD", "US30_USD")
CROSS_MARKET = ("EUR_USD", "XAU_USD")
OFFSET = ("DE30_EUR",)
ALL_INSTRUMENTS = NEAR_CLONES + CROSS_MARKET + OFFSET
#: section 4. (signal bars, entry offset, exit offset) in 15-minute bars
#: from the 08:30 bar. Both hold one hour from entry.
VARIANT_A = (1, 1, 5)                   # 08:30-08:45, in 08:45, out 09:45
VARIANT_C = (2, 2, 6)                   # 08:30-09:00, in 09:00, out 10:00


def stem(instrument):
    return instrument.replace("_", "").lower()


def read_side(path):
    o = {}
    with open(path) as fh:
        for r in csv.DictReader(fh):
            t = dt.datetime.fromisoformat(r["time"]).replace(tzinfo=UTC)
            o[t] = (float(r["open"]), float(r["high"]), float(r["low"]),
                    float(r["close"]))
    return o


def signal_dir(bid, ask, t, nbars):
    """FADE direction from a signal bar spanning `nbars` 15-minute bars.

    The 30-minute signal opens where the 15-minute one does and closes
    one bar later. Returning None on a doji keeps the two variants
    comparable -- a bar with no direction is not a trade in either.
    """
    t_end = t + BAR * (nbars - 1)
    if t not in bid or t_end not in bid or t not in ask or t_end not in ask:
        return None
    o = (bid[t][0] + ask[t][0]) / 2.0
    c = (bid[t_end][3] + ask[t_end][3]) / 2.0
    if c == o:
        return None
    return -1 if c > o else 1


def trade(bid, ask, t, variant):
    """(gross_bp, net_bp) for one fade, or None.

    gross is mid to mid. net takes the side actually dealt -- sell the
    bid and buy the ask -- so the cost is this instrument's own, measured
    per trade rather than borrowed from SPX500. v24 section 7 makes that
    a kill condition, because borrowing 1.77 bp would assume Gate E.
    """
    nbars, eo, xo = variant
    d = signal_dir(bid, ask, t, nbars)
    if d is None:
        return None
    te, tx = t + BAR * eo, t + BAR * xo
    if te not in bid or tx not in bid or te not in ask or tx not in ask:
        return None
    me, mx = (bid[te][0] + ask[te][0]) / 2.0, (bid[tx][0] + ask[tx][0]) / 2.0
    if me <= 0 or mx <= 0:
        return None
    gross = d * (mx / me - 1.0) * 1e4
    if d == 1:                       # long the fade: in at ask, out at bid
        net = (bid[tx][0] / ask[te][0] - 1.0) * 1e4
    else:
        #: short: sell the bid at entry, buy the ask at exit. The return
        #: is on the ENTRY notional -- (Pe - Px)/Pe -- and writing it as
        #: Pe/Px - 1 divides by the wrong price. The self-test caught
        #: that: with bid == ask the cost must be exactly zero, and the
        #: wrong form leaves a residue of (Pe/Px - 1) x gross. On a 10 bp
        #: move that is 0.01 bp, small enough to hide forever in a result
        #: and wrong in every one of them.
        net = (1.0 - ask[tx][0] / bid[te][0]) * 1e4
    return gross, net


def era_halves(pairs):
    """[(label, values)] for the first and second half by date."""
    if len(pairs) < 4:
        return []
    ds = sorted(pairs)
    cut = ds[len(ds) // 2]
    a = [v for d, v in pairs.items() if d < cut]
    b = [v for d, v in pairs.items() if d >= cut]
    return [(f"{ds[0].year}-{cut.year}", a), (f"{cut.year}-{ds[-1].year}", b)]


def sign_flips(halves):
    """Gate F. True when the two halves disagree in sign."""
    if len(halves) != 2 or not halves[0][1] or not halves[1][1]:
        return False
    return st.mean(halves[0][1]) * st.mean(halves[1][1]) < 0


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"premarket_instruments.py v{VERSION} self-test\n")

    T0 = dt.datetime(2020, 6, 5, 12, 30, tzinfo=UTC)   # 08:30 ET, a Friday

    def synth(seq, spread=0.0):
        """seq is [(open, close)] per 15-minute bar from T0."""
        bid, ask = {}, {}
        for i, (o, c) in enumerate(seq):
            t = T0 + BAR * i
            bid[t] = (o - spread / 2, max(o, c), min(o, c), c - spread / 2)
            ask[t] = (o + spread / 2, max(o, c), min(o, c), c + spread / 2)
        return bid, ask

    print("the two variants read DIFFERENT signal bars")
    #: PLANTED: the 15-minute bar rises and the 30-minute bar falls. This
    #: is the whole claim under test -- if the two variants cannot take
    #: opposite sides here, they are not measuring different things.
    seq = [(100.0, 101.0), (101.0, 99.0)] + [(99.0, 99.0)] * 8
    b, a = synth(seq)
    check("the 15m bar closed UP, so variant A fades SHORT",
          signal_dir(b, a, T0, 1) == -1)
    check("the 30m bar closed DOWN, so variant C fades LONG",
          signal_dir(b, a, T0, 2) == 1,
          "opposite sides on the same morning")
    check("a doji has no direction in either",
          signal_dir(*synth([(100.0, 100.0), (100.0, 100.0)]), T0, 1) is None
          and signal_dir(*synth([(100.0, 100.0), (100.0, 100.0)]),
                         T0, 2) is None)

    print("\nthe offsets are the ones v24 section 4 froze")
    check("A signals on 1 bar, enters at +1, exits at +5", VARIANT_A == (1, 1, 5))
    check("C signals on 2 bars, enters at +2, exits at +6", VARIANT_C == (2, 2, 6))
    #: PLANTED: both hold exactly one hour from entry. If the hold
    #: differed, this would be v22's D-vs-C confound all over again and
    #: the comparison would not isolate the signal bar.
    check("BOTH hold 4 bars from entry -- the hold is not the variable",
          VARIANT_A[2] - VARIANT_A[1] == VARIANT_C[2] - VARIANT_C[1] == 4,
          "the confound this whole run exists to avoid")

    print("\nentry and exit land where the offsets say")
    #: a clean +1% continuation after an up signal bar: fading loses
    up = [(100.0, 101.0), (101.0, 101.0), (101.0, 101.0), (101.0, 101.0),
          (101.0, 101.0), (102.0, 102.0), (102.0, 102.0)]
    b, a = synth(up)
    g, n = trade(b, a, T0, VARIANT_A)
    check("A fades an UP bar and LOSES when price keeps rising", g < 0,
          f"{g:+.1f} bp")
    check("and it entered at the 08:45 open, not the signal close",
          abs(g - (-1.0 * (102.0 / 101.0 - 1.0) * 1e4)) < 1e-6)

    print("\ncost is this instrument's own, measured per trade")
    b2, a2 = synth(up, spread=0.10)          # ~10 bp on a price of 101
    g2, n2 = trade(b2, a2, T0, VARIANT_A)
    check("net is worse than gross once a spread exists", n2 < g2,
          f"gross {g2:+.1f}  net {n2:+.1f}  cost {g2 - n2:.1f} bp")
    #: PLANTED: cost must be the AVERAGE spread crossed, not zero and not
    #: double. A 0.10 spread on ~101 is ~9.9 bp.
    check("and the cost is one spread, not zero and not two",
          8.0 < (g2 - n2) < 12.0, f"{g2 - n2:.2f} bp")
    b3, a3 = synth(up, spread=0.0)
    g3, n3 = trade(b3, a3, T0, VARIANT_A)
    check("with bid == ask the cost is exactly zero",
          abs(g3 - n3) < 1e-9,
          "which is why such an instrument drops to sign-only, v24 s7")

    print("\nGate F sees a sign flip, and only a real one")
    d1, d2 = dt.date(2010, 1, 1), dt.date(2020, 1, 1)
    #: PLANTED: v22's variant B failed exactly this, +5.44 then +10.97 --
    #: which is NOT a flip. Same sign, bigger. The gate must not fire.
    same = {d1: 5.44, d1 + dt.timedelta(1): 5.44,
            d2: 10.97, d2 + dt.timedelta(1): 10.97}
    check("a doubling with the SAME sign is not a flip",
          not sign_flips(era_halves(same)), "+5.44 then +10.97")
    flip = {d1: 4.0, d1 + dt.timedelta(1): 4.0,
            d2: -3.0, d2 + dt.timedelta(1): -3.0}
    check("an actual sign change IS a flip", sign_flips(era_halves(flip)))
    check("and the halves split by DATE, not by arrival order",
          [lab for lab, _ in era_halves(same)] == ["2010-2020", "2020-2020"],
          f"{[lab for lab, _ in era_halves(same)]}")

    print("\nthe groups and the floor were fixed before the fetch")
    check("five instruments in three groups, no overlap",
          len(set(ALL_INSTRUMENTS)) == 5
          and not (set(NEAR_CLONES) & set(CROSS_MARKET)))
    check("the near-clones are the POSITIVE CONTROL, not the evidence",
          NEAR_CLONES == ("NAS100_USD", "US30_USD"))
    check("the event floor is 150 and is not derived from any data",
          MIN_EVENTS == 150)
    check("claims is excluded, as v24 section 4 declares",
          RELEASES == ("CPI", "NFP"))
    check("filenames follow the existing convention",
          stem("NAS100_USD") == "nas100usd" and stem("EUR_USD") == "eurusd")

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="../data/v24")
    ap.add_argument("--events", default="../data/events_v2.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"premarket_instruments.py v{VERSION}   PREREGISTRATION_v24\n")
    print("  I am not a financial adviser. This is a measurement, not a")
    print("  recommendation to take a position.\n")

    pre, _ = load_events(a.events, from_year=1900)
    ev_days = sorted(d for d in pre
                     if any(r in pre[d] for r in RELEASES))
    print(f"  CPI + payrolls at 08:30 ET in the table: {len(ev_days):,}\n")

    res = {}
    for ins in ALL_INSTRUMENTS:
        pb = os.path.join(a.data_dir, f"{stem(ins)}_bid_15m.csv")
        pa = os.path.join(a.data_dir, f"{stem(ins)}_ask_15m.csv")
        if not (os.path.exists(pb) and os.path.exists(pa)):
            print(f"  {ins:<12} NO DATA -- {os.path.basename(pb)} missing")
            continue
        bid, ask = read_side(pb), read_side(pa)
        common = bid.keys() & ask.keys()
        slot = {}
        for t in common:
            e = t.astimezone(ET)
            if (e.hour, e.minute) == SLOT:
                slot[e.date()] = t
        #: v24 section 7: bid == ask means cost is unmeasurable, and the
        #: instrument drops to sign-only automatically rather than by
        #: judgement on the day. This is the SPX500 pre-2012 failure.
        zero = sum(1 for t in common if ask[t][3] == bid[t][3])
        flat = zero / max(1, len(common)) > 0.5

        rows = {}
        for d in ev_days:
            t = slot.get(d)
            if t is None:
                continue
            ta, tc = trade(bid, ask, t, VARIANT_A), trade(bid, ask, t, VARIANT_C)
            if ta is None or tc is None:
                continue
            rows[d] = (ta, tc)
        #: v24.1 -- the AMENDED Gate A's statistic. Does the event table
        #: land on bars that move? Collected here so the control set is
        #: the same 08:30 slot on days the table says are quiet.
        ev_set = set(ev_days)
        mv_rel, mv_ctl = [], []
        for d, t in slot.items():
            o = (bid[t][0] + ask[t][0]) / 2.0
            c = (bid[t][3] + ask[t][3]) / 2.0
            if o <= 0:
                continue
            m = abs(c / o - 1.0) * 1e4
            (mv_rel if d in ev_set else mv_ctl).append(m)
        res[ins] = dict(rows=rows, flat=flat, bars=len(common),
                        mv_rel=mv_rel, mv_ctl=mv_ctl,
                        span=(min(slot), max(slot)) if slot else None)
        span = res[ins]["span"]
        print(f"  {ins:<12} {len(common):>8,} bars   {len(rows):>4} events   "
              f"{span[0]} .. {span[1]}"
              + ("   BID==ASK, sign only" if flat else ""))

    def pooled(instruments, pick):
        out = []
        for ins in instruments:
            r = res.get(ins)
            if not r or len(r["rows"]) < MIN_EVENTS:
                continue
            out += [pick(v) for v in r["rows"].values()]
        return out

    gA = lambda v: v[0][0]          # variant A, gross
    nA = lambda v: v[0][1]          # variant A, net
    gC = lambda v: v[1][0]
    nC = lambda v: v[1][1]
    dCA = lambda v: v[1][0] - v[0][0]

    print(f"\n  PER INSTRUMENT -- gross bp, and C minus A paired")
    print(f"    {'instrument':<12}{'n':>5}{'A gross':>9}{'t':>6}"
          f"{'C gross':>9}{'t':>6}{'C-A':>8}{'t':>7}{'cost':>7}")
    for ins in ALL_INSTRUMENTS:
        r = res.get(ins)
        if not r or not r["rows"]:
            continue
        v = list(r["rows"].values())
        ga, gc = [gA(x) for x in v], [gC(x) for x in v]
        dd = [dCA(x) for x in v]
        cost = st.mean(gC(x) - nC(x) for x in v)
        gate = "" if len(v) >= MIN_EVENTS else "  (under 150, not gated)"
        print(f"    {ins:<12}{len(v):>5}{st.mean(ga):>+9.2f}"
              f"{one_sample_t(ga):>+6.2f}{st.mean(gc):>+9.2f}"
              f"{one_sample_t(gc):>+6.2f}{st.mean(dd):>+8.2f}"
              f"{one_sample_t(dd):>+7.2f}{cost:>7.2f}{gate}")

    #: ---- GATE A, AMENDED by v24.1 -- voids the run ----
    print(f"\n  GATE A (v24.1) -- do the event timestamps land on bars "
          f"that MOVE?")
    print(f"    {'instrument':<12}{'release':>10}{'control':>10}{'ratio':>8}"
          f"{'t':>8}")
    ga_ok = True
    for ins in ALL_INSTRUMENTS:
        r = res.get(ins)
        if not r or len(r["mv_rel"]) < 2 or len(r["mv_ctl"]) < 2:
            print(f"    {ins:<12} INSUFFICIENT DATA")
            ga_ok = False
            continue
        t = welch_t(r["mv_rel"], r["mv_ctl"])
        good = t is not None and t >= AMENDED_GATE_A_T
        ga_ok &= good
        print(f"    {ins:<12}{st.mean(r['mv_rel']):>9.2f}"
              f"{st.mean(r['mv_ctl']):>10.2f}"
              f"{st.mean(r['mv_rel']) / st.mean(r['mv_ctl']):>7.2f}x"
              f"{t:>8.1f}   [{'PASS' if good else 'FAIL'}]")
    if not ga_ok:
        print(f"\n    VOID -- v24.1 section 2. A scheduled release moves the")
        print(f"    market. Failing THIS means the fetch, the timestamps or")
        print(f"    this code is wrong, and it is a finding about the")
        print(f"    pipeline rather than about the market.")
        sys.exit(3)

    #: ---- the ORIGINAL Gate A, computed and reported as what it is ----
    print(f"\n  the ORIGINAL v24 Gate A, reported as a second reading of")
    print(f"  the HYPOTHESIS rather than as a control (v24.1 section 1)")
    for ins in NEAR_CLONES:
        r = res.get(ins)
        if not r or len(r["rows"]) < MIN_EVENTS:
            continue
        v = [gA(x) for x in r["rows"].values()]
        t = one_sample_t(v)
        print(f"    {ins:<12}{st.mean(v):>+8.2f} bp   t {t:>+5.2f}   "
              f"{'clears' if t >= GATE_A_T else 'does NOT clear'} the old "
              f"t >= {GATE_A_T} bar")

    dB = pooled(ALL_INSTRUMENTS, dCA)
    dC = pooled(NEAR_CLONES, dCA)
    tB, tC = one_sample_t(dB), one_sample_t(dC)
    gb = bool(dB) and tB is not None and st.mean(dB) > 0 and tB >= GATE_T
    gc = bool(dC) and tC is not None and st.mean(dC) > 0 and tC >= GATE_T

    nc_net = pooled(NEAR_CLONES, nC)
    ge = bool(nc_net) and st.mean(nc_net) > 0

    print(f"\n  VERDICT -- gates frozen in PREREGISTRATION_v24 section 5")
    print(f"    [PASS] Gate A  positive control")
    if dB:
        print(f"    [{'PASS' if gb else 'FAIL'}] Gate B  C-A pooled over all "
              f"{st.mean(dB):+.2f} bp, t = {tB:.2f}   n={len(dB)}")
    if dC:
        print(f"    [{'PASS' if gc else 'FAIL'}] Gate C  C-A near-clones "
              f"{st.mean(dC):+.2f} bp, t = {tC:.2f}   n={len(dC)}"
              f"   <- THE CLAIM")
    if nc_net:
        print(f"    [{'PASS' if ge else 'FAIL'}] Gate E  variant C net on the "
              f"near-clones {st.mean(nc_net):+.2f} bp")

    print(f"\n    [Gate F] sign stability of C-A, by era")
    for ins in ALL_INSTRUMENTS:
        r = res.get(ins)
        if not r or len(r["rows"]) < MIN_EVENTS:
            continue
        h = era_halves({d: dCA(v) for d, v in r["rows"].items()})
        flip = sign_flips(h)
        print(f"      {ins:<12}" + "   ".join(
            f"{lab} {st.mean(vals):+6.2f}" for lab, vals in h)
            + ("   FLIPS" if flip else ""))

    #: ---- GATE D -- the mechanism, reported and NOT gated ----
    print(f"\n  GATE D -- the mechanism test, reported and not gated")
    print(f"    EUR_USD and XAU_USD have no 09:30 equity open. A base")
    print(f"    effect here favours information absorption; its absence")
    print(f"    favours the open doing the correcting.")
    for ins in CROSS_MARKET + OFFSET:
        r = res.get(ins)
        if not r or not r["rows"]:
            continue
        v = list(r["rows"].values())
        ga_ = [gA(x) for x in v]
        print(f"      {ins:<12}n={len(v):>4}  A gross {st.mean(ga_):+6.2f} "
              f"t {one_sample_t(ga_):+5.2f}   C-A "
              f"{st.mean([dCA(x) for x in v]):+6.2f}")

    #: ---- v24.1 section 3 -- the asymmetry, enforced HERE rather than
    #: ---- left to judgement on the day. The amendment was written after
    #: ---- I had seen these figures, so it is allowed to license a null
    #: ---- and nothing else. A pass re-voids the run.
    if gb or gc:
        print(f"\n  ================= THE VOID STANDS =================")
        print(f"  Gate {'B' if gb else ''}{' and ' if gb and gc else ''}"
              f"{'C' if gc else ''} PASSED.")
        print(f"\n  PREREGISTRATION_v24.1 section 3: this amendment may only")
        print(f"  license reading a NULL. It was written after the")
        print(f"  hypothesis-gate figures had been seen, so a positive")
        print(f"  result read through it would be a gate moved until a")
        print(f"  finding appeared -- which is the one failure mode")
        print(f"  pre-registration exists to prevent.")
        print(f"\n  This pass is NOT a finding. The v24 void stands, and a")
        print(f"  confirmation needs data that does not yet exist.")
        sys.exit(4)

    print(f"\n  {'CONFIRMED' if gc else 'NOT CONFIRMED'} -- v24 section 6 "
          f"registered Gate C failing.")
    print(f"  The 30-minute signal bar was +1 standard error on the")
    print(f"  sample that chose it, and it does not survive new ones.")

    for lab, vals in (("Gate B", dB), ("Gate C", dC)):
        if vals and abs(st.mean(vals)) > SANITY_MAX_BP:
            print(f"\n    KILL: {lab} {st.mean(vals):+.2f} bp exceeds "
                  f"{SANITY_MAX_BP} (v24 section 7)")
            sys.exit(3)


if __name__ == "__main__":
    main()
