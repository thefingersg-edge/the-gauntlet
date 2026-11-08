#!/usr/bin/env python3
"""PREREGISTRATION_v23 -- does the payrolls reversion reproduce out of sample?

v22's registered breakdown produced one positive line (NFP, +4.55 bp
gross) and v22 section 5 said in advance that a stratum passing when the
pooled result failed is a finding needing its own confirmation. This is
that confirmation, on SPX500_USD 2003-2012 -- ~120 payrolls releases
never used for this question.

EVERYTHING MEASURED HERE IS IMPORTED, NOT REIMPLEMENTED
-------------------------------------------------------
cont_bp, load_events and the test statistics come from
premarket_event.py, which carries its own self-test. A confirmation that
rewrites the thing it is confirming is testing two things at once, and
when they disagree you cannot tell which one moved.

    python3 premarket_confirm.py --self-test
    python3 premarket_confirm.py
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import statistics as st
import sys
from zoneinfo import ZoneInfo

from premarket_event import (BAR, SLOT, H_PRIMARY, cont_bp, load_events,
                             one_sample_t, welch_t)

VERSION = "1.0"

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc

#: ---- FROZEN IN v23 ----
FROM_YEAR, TO_YEAR = 2003, 2012      # section 2: the held-out window
HALVES = ((2003, 2007), (2008, 2012))  # section 4, Gate C
PRIMARY = "NFP"                      # section 1
SECONDARY = "CPI"                    # section 4, Gate D -- reported, not gated
GATE_A_T = 5.0                       # section 4
GATE_B_BP = 2.0                      # section 4: half the modern +4.55
GATE_B_T = 2.0
SANITY_MAX_BP = 30.0                 # section 6
#: the number this run is trying to reproduce, from RESULT_PREMARKET
MODERN_NFP_GROSS = 4.55


def fade_bp(o_sig, c_sig, entry, exit_):
    """Gross bp from FADING the signal bar. v23 section 3.

    The sign is fixed here and nowhere else: fading is the NEGATIVE of
    continuation, and cont_bp is imported rather than re-derived so the
    two documents cannot drift apart.
    """
    c = cont_bp(o_sig, c_sig, entry, exit_)
    return None if c is None else -c


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"premarket_confirm.py v{VERSION} self-test\n")

    print("fading is the negative of continuation, and is imported")
    #: PLANTED: the one sign this file owns. An UP bar that keeps rising
    #: is continuation (positive) and therefore a LOSS to the fader.
    check("an UP bar that keeps rising LOSES money for the fader",
          fade_bp(100.0, 101.0, 101.0, 102.0) < 0,
          f"{fade_bp(100.0, 101.0, 101.0, 102.0):+.1f} bp")
    check("an UP bar that falls back PAYS the fader",
          fade_bp(100.0, 101.0, 101.0, 100.0) > 0)
    check("a DOWN bar that rebounds pays the fader too",
          fade_bp(100.0, 99.0, 99.0, 100.0) > 0)
    check("and it is exactly minus cont_bp, never re-derived",
          fade_bp(100.0, 101.0, 101.0, 102.0)
          == -cont_bp(100.0, 101.0, 101.0, 102.0))
    check("a doji still returns None", fade_bp(1.0, 1.0, 1.0, 2.0) is None)

    print("\nthe held-out window is the one v22 did NOT use")
    check("it ends before v22 begins", TO_YEAR < 2013)
    check("and the halves tile it exactly, no gap and no overlap",
          HALVES[0][0] == FROM_YEAR and HALVES[1][1] == TO_YEAR
          and HALVES[1][0] == HALVES[0][1] + 1, f"{HALVES}")
    #: PLANTED: the crisis must be INSIDE the window. Excluding 2008
    #: after seeing a result is the selection this run exists to test.
    check("2008 is inside the window, not excluded",
          FROM_YEAR <= 2008 <= TO_YEAR)

    print("\nthe gate thresholds are the ones v23 section 4 fixed")
    check("Gate B asks for half the modern estimate or better",
          abs(GATE_B_BP - MODERN_NFP_GROSS / 2.0) < 0.3,
          f"{GATE_B_BP} bp against a modern {MODERN_NFP_GROSS} bp")
    check("the primary is payrolls, and CPI is not a second chance",
          PRIMARY == "NFP" and SECONDARY == "CPI")

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

    print(f"premarket_confirm.py v{VERSION}   PREREGISTRATION_v23\n")
    print("  I am not a financial adviser. This is a measurement, not a")
    print("  recommendation to take a position.\n")

    def rd(p):
        o = {}
        for r in csv.DictReader(open(p)):
            t = dt.datetime.fromisoformat(r["time"]).replace(tzinfo=UTC)
            o[t] = (float(r["open"]), float(r["high"]), float(r["low"]),
                    float(r["close"]))
        return o

    b, ask = rd(a.bid), rd(a.ask)
    common = b.keys() & ask.keys()
    mid = {t: tuple((b[t][i] + ask[t][i]) / 2.0 for i in range(4))
           for t in common}

    slot_bar = {}
    for t in common:
        e = t.astimezone(ET)
        if FROM_YEAR <= e.year <= TO_YEAR and (e.hour, e.minute) == SLOT:
            slot_bar[e.date()] = t
    print(f"  08:30 ET bars {FROM_YEAR}-{TO_YEAR}: {len(slot_bar):,}")

    pre_ev, _ = load_events(a.events, from_year=FROM_YEAR)
    pre_ev = {d: n for d, n in pre_ev.items() if d.year <= TO_YEAR}

    def observe(days):
        out = []
        for d in days:
            t = slot_bar.get(d)
            if t is None:
                continue
            tn, tx = t + BAR, t + BAR * H_PRIMARY
            if tn not in common or tx not in common:
                continue
            o, h, l, c = mid[t]
            f = fade_bp(o, c, mid[tn][0], mid[tx][3])
            if f is None:
                continue
            out.append(dict(d=d, fade=f, move=abs(c / o - 1.0) * 1e4))
        return out

    nfp_days = sorted(d for d in pre_ev if PRIMARY in pre_ev[d])
    cpi_days = sorted(d for d in pre_ev if SECONDARY in pre_ev[d])
    ctl_days = sorted(d for d in slot_bar if d not in pre_ev)
    nfp, cpi, ctl = observe(nfp_days), observe(cpi_days), observe(ctl_days)
    print(f"  payrolls {len(nfp):,}   CPI {len(cpi):,}   "
          f"control {len(ctl):,}\n")

    #: ---- GATE A -- positive control, and the data's own viability ----
    ta, da = welch_t([x["move"] for x in nfp], [x["move"] for x in ctl])
    ga = ta is not None and ta >= GATE_A_T
    print(f"  GATE A -- do the pre-2012 bars respond to payrolls at all?")
    print(f"    payrolls |move| {st.mean(x['move'] for x in nfp):6.2f} bp"
          f"    control {st.mean(x['move'] for x in ctl):6.2f} bp")
    print(f"    diff {da:+.2f} bp   t = {ta:.1f}   "
          f"[{'PASS' if ga else 'FAIL'}]")
    if not ga:
        print(f"\n    VOID -- v23 section 6. A back-filled mid series that")
        print(f"    does not move on payrolls is not a sample, and this is")
        print(f"    a finding about the DATA, not about the market.")
        sys.exit(3)

    #: ---- GATE B -- the confirmation ----
    f = [x["fade"] for x in nfp]
    tb = one_sample_t(f)
    gb = st.mean(f) >= GATE_B_BP and tb is not None and tb >= GATE_B_T

    #: ---- GATE C -- both halves ----
    half = []
    for lo, hi in HALVES:
        s = [x["fade"] for x in nfp if lo <= x["d"].year <= hi]
        half.append((f"{lo}-{hi}", len(s), st.mean(s) if s else 0.0,
                     one_sample_t(s) if len(s) > 1 else 0.0))
    gc = all(h[2] > 0 for h in half)

    print(f"\n  THE CONFIRMATION -- gross bp from fading, H={H_PRIMARY}")
    print(f"    {'':<12}{'n':>6}{'gross bp':>11}{'t':>8}")
    print(f"    {'payrolls':<12}{len(f):>6}{st.mean(f):>11.2f}{tb:>8.2f}")
    print(f"    {'CPI':<12}{len(cpi):>6}"
          f"{st.mean(x['fade'] for x in cpi):>11.2f}"
          f"{one_sample_t([x['fade'] for x in cpi]):>8.2f}   "
          f"(Gate D -- reported, not gated)")
    print(f"    {'control':<12}{len(ctl):>6}"
          f"{st.mean(x['fade'] for x in ctl):>11.2f}"
          f"{one_sample_t([x['fade'] for x in ctl]):>8.2f}")

    print(f"\n  VERDICT -- gates frozen in PREREGISTRATION_v23 section 4")
    print(f"    [{'PASS' if ga else 'FAIL'}] Gate A  payrolls move the "
          f"pre-2012 tape, t = {ta:.1f}")
    print(f"    [{'PASS' if gb else 'FAIL'}] Gate B  {st.mean(f):+.2f} bp "
          f"vs the {GATE_B_BP:+.1f} bp bar, t = {tb:.2f}   "
          f"<- THE CONFIRMATION")
    print(f"    [{'PASS' if gc else 'FAIL'}] Gate C  " + "   ".join(
        f"{lab} {m:+.2f} (n={n})" for lab, n, m, _ in half))

    print(f"\n  AGAINST THE NUMBER IT IS TRYING TO REPRODUCE")
    print(f"    modern   2013-2026   n=162   {MODERN_NFP_GROSS:+.2f} bp")
    print(f"    held out {FROM_YEAR}-{TO_YEAR}   n={len(f):<5} "
          f"{st.mean(f):+.2f} bp")
    ratio = st.mean(f) / MODERN_NFP_GROSS if MODERN_NFP_GROSS else 0.0
    print(f"    the held-out sample is {ratio:.2f}x the modern estimate")

    if gb and gc:
        print(f"\n    CONFIRMED. v23 section 5 registered a failure here, so")
        print(f"    this is my prediction being wrong, and the next step is")
        print(f"    STRATEGY section 5b -- other instruments, real quotes,")
        print(f"    fetched fresh. Not a position.")
    else:
        print(f"\n    NOT CONFIRMED. v22's payrolls line does not reproduce")
        print(f"    on held-out data, which is what STRATEGY section 3")
        print(f"    predicted from the selection signature alone.")

    if abs(st.mean(f)) > SANITY_MAX_BP:
        print(f"\n    KILL: {st.mean(f):+.2f} bp exceeds {SANITY_MAX_BP}")
        sys.exit(3)


if __name__ == "__main__":
    main()
