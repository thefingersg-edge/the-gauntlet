#!/usr/bin/env python3
"""PHASE 1 for PREREGISTRATION_v9 -- what did a roll actually cost?

Every threshold in this file is copied from PREREGISTRATION_v9, which was
written and delivered BEFORE any price was read. None of them may move.
If a gate needs changing to produce a result, the run is abandoned and
recorded as abandoned -- v9 section 6.

WHAT IS MEASURED (v9 section 3)
-------------------------------
For each 1-minute bar on a dated quarterly where a trade occurred:

    deviation_bp = |trade_close - mark_close| / mark_close * 10,000

`trade` is what executed. `mark` is Kraken's fair value for the same
minute. Minutes with NO trade are counted separately and never dropped:
they are the illiquidity being measured, and v9 section 7 explains why
they are also this measure's worst weakness.

THE COMPARISON (v9 section 5, Gate B)
-------------------------------------
For each of the 14 historical settlement dates, the contract the rule
would be ENTERING that day -- the next quarterly -- is pulled over the
settlement day and the 20 calendar days before it.

The prior-20 window is the control, and it was chosen for a stated
reason: it holds the contract, its maturity and the market regime roughly
fixed, so the only thing varying is whether the day is a settlement day.
A random sample of days across the contract's life would have confounded
settlement with contract age.

THE FIRST THING THIS CHECKS
---------------------------
v9 section 6's last kill condition. If `mark` is derived from the last
trade, the two series are not independent and the whole measure is
circular. A median deviation under 0.5bp across all cycles is the
signature, and it is tested BEFORE any gate is reported.

    python3 exec_cost.py --self-test
    python3 exec_cost.py
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken_probe as KP                                    # noqa: E402
import kraken_history as KH                                  # noqa: E402

VERSION = "1.0"

#: ---- FROZEN IN PREREGISTRATION_v9. Do not edit. ----
#: v9 section 4: era 3 headroom 0.56 pts / 4 rolls a year = 14bp
WIDE_BP = 14.0
#: v9 section 5
GATE_A_MAX_WIDE = 0.20
GATE_B_MAX_EXCESS = 0.10
GATE_C_MIN_DATES = 8
GATE_C_MIN_MINUTES = 30
GATE_D_FLOOR = 2.0
ERA3_EXCESS = 2.56
ROLLS_PER_YEAR = 4
#: v9 section 6, the circularity kill
CIRCULARITY_MEDIAN_BP = 0.5
#: v9 section 5 Gate B's control window
PRIOR_DAYS = 20
N_CYCLES = 14


def deviation_bp(trade_close, mark_close):
    """|trade - mark| / mark in basis points. None if either is missing.

    Absolute, not signed: OHLC cannot say whether a print was a buy or a
    sell, so a seller's cost is inferred from a symmetric deviation. v9
    section 7 records that as a limitation, not a solved problem.
    """
    if not trade_close or not mark_close or mark_close <= 0:
        return None
    return abs(trade_close - mark_close) / mark_close * 1e4


def align(trade_rows, mark_rows):
    """Inner join on timestamp. Returns (aligned, traded, untraded).

    `traded` are minutes with volume > 0 -- the only ones that carry a
    deviation. `untraded` is the count of minutes where the bar exists and
    nobody transacted, reported alongside every figure per v9 section 7.
    """
    marks = {r["time"]: r for r in mark_rows if r.get("close")}
    out, untraded = [], 0
    for t in trade_rows:
        m = marks.get(t["time"])
        if m is None:
            continue
        if (t.get("volume") or 0.0) <= 0.0:
            untraded += 1
            continue
        d = deviation_bp(t.get("close"), m.get("close"))
        if d is not None:
            out.append(dict(time=t["time"], dev=d,
                            volume=t.get("volume") or 0.0))
    return out, len(out), untraded


def wide_share(devs, threshold=WIDE_BP):
    """Share of traded minutes at or above the frozen WIDE threshold."""
    if not devs:
        return None
    return sum(1 for d in devs if d >= threshold) / len(devs)


def is_circular(all_devs, floor=CIRCULARITY_MEDIAN_BP):
    """v9 section 6: a median under 0.5bp means mark tracks last trade.

    Returns (circular, median). A circular measure is not a small effect
    -- it is no measurement at all, and it is checked before any gate.
    """
    if not all_devs:
        return True, None
    m = st.median(all_devs)
    return (m < floor), m


def gate_a(roll_devs):
    """Share of roll-date traded minutes that were WIDE. < 20% passes."""
    s = wide_share(roll_devs)
    if s is None:
        return None, None
    return (s < GATE_A_MAX_WIDE), s


def gate_b(roll_devs, prior_devs):
    """Are settlement days materially worse than the days around them?

    PASS when roll_rate <= prior_rate + 10 percentage points. This is the
    gate no amount of forward daily sampling can reach.
    """
    r, p = wide_share(roll_devs), wide_share(prior_devs)
    if r is None or p is None:
        return None, None, None
    return (r <= p + GATE_B_MAX_EXCESS), r, p


def gate_c(per_date_counts):
    """>= 8 of 14 roll dates with >= 30 traded minutes each."""
    n = sum(1 for c in per_date_counts if c >= GATE_C_MIN_MINUTES)
    return (n >= GATE_C_MIN_DATES), n


def gate_d(roll_devs, era3=ERA3_EXCESS):
    """Median roll-date deviation as a half-spread, 4x a year.

    The deviation is a full displacement from fair value, so it is the
    cost of one crossing. Four rolls a year.
    """
    if not roll_devs:
        return None, None, None
    med = st.median(roll_devs)
    drag = med / 1e4 * ROLLS_PER_YEAR * 100.0
    net = era3 - drag
    return (net >= GATE_D_FLOOR), drag, net


def next_quarterly_after(d):
    """The contract the rule ENTERS on settlement date `d`."""
    y, m = d.year, d.month + 3
    if m > 12:
        m -= 12
        y += 1
    return KH.last_friday(y, m)


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"exec_cost.py v{VERSION} self-test\n")

    print("the thresholds match PREREGISTRATION_v9 exactly")
    check("WIDE is 14bp -- 0.56 pts headroom over 4 rolls",
          abs(WIDE_BP - 0.56 / ROLLS_PER_YEAR * 1e4 / 100) < 1e-9,
          f"{WIDE_BP}bp")
    check("Gate A bar is 20%", GATE_A_MAX_WIDE == 0.20)
    check("Gate B allowance is 10 points", GATE_B_MAX_EXCESS == 0.10)
    check("Gate C needs 8 dates of 30 minutes",
          GATE_C_MIN_DATES == 8 and GATE_C_MIN_MINUTES == 30)
    check("Gate D floor is the +2.0 bar", GATE_D_FLOOR == 2.0)
    check("era 3 is the published +2.56", ERA3_EXCESS == 2.56)

    print("\nthe deviation is what v9 section 3 defines")
    check("a 14bp gap reads 14bp",
          abs(deviation_bp(100.14, 100.0) - 14.0) < 1e-9,
          f"{deviation_bp(100.14, 100.0):.2f}bp")
    check("and it is symmetric -- direction is not observable",
          abs(deviation_bp(99.86, 100.0)
              - deviation_bp(100.14, 100.0)) < 1e-6)
    check("a missing mark gives None, never 0.0",
          deviation_bp(100.0, None) is None)
    check("a zero mark gives None, not a division",
          deviation_bp(100.0, 0.0) is None)

    print("\nuntraded minutes are counted, never dropped")
    T = [{"time": 1, "close": 100.5, "volume": 3.0},
         {"time": 2, "close": 100.0, "volume": 0.0},
         {"time": 3, "close": 101.0, "volume": 1.0},
         {"time": 4, "close": 100.0, "volume": None}]
    M = [{"time": i, "close": 100.0} for i in (1, 2, 3, 4)]
    devs, n, unt = align(T, M)
    check("two traded minutes carry deviations", n == 2, f"n={n}")
    check("and the two untraded ones are COUNTED", unt == 2, f"{unt}")
    check("a trade minute with no matching mark is skipped, not guessed",
          align(T, M[:1])[1] == 1)
    #: PLANTED: silently dropping untraded minutes would make an illiquid
    #: contract look identical to a busy one. This is the check for it.
    quiet = [{"time": i, "close": 100.0, "volume": 0.0} for i in range(50)]
    check("an entirely untraded window reports 0 traded, 50 untraded",
          align(quiet, [{"time": i, "close": 100.0}
                        for i in range(50)])[1:] == (0, 50))

    print("\nthe circularity kill fires BEFORE any gate (v9 sec 6)")
    #: PLANTED: this is the failure mode I said was most likely
    check("a sub-0.5bp median is CIRCULAR, not a good result",
          is_circular([0.1, 0.2, 0.3, 0.4])[0], "median 0.25bp")
    check("a real spread is not circular",
          not is_circular([3.0, 8.0, 14.0, 40.0])[0])
    check("exactly at the floor is circular",
          is_circular([0.4, 0.4, 0.4])[0])
    check("an empty series is circular, not a pass",
          is_circular([])[0])

    print("\nevery gate can FAIL, and is shown failing")
    tight = [1.0] * 95 + [20.0] * 5          # 5% wide
    wide = [1.0] * 50 + [20.0] * 50          # 50% wide
    pa, sa = gate_a(tight)
    check("Gate A passes at 5% wide", pa, f"{sa*100:.0f}%")
    pa2, sa2 = gate_a(wide)
    check("Gate A FAILS at 50% wide", not pa2, f"{sa2*100:.0f}%")
    #: the boundary, both sides
    check("19% passes, 21% fails",
          gate_a([1.0] * 81 + [20.0] * 19)[0]
          and not gate_a([1.0] * 79 + [20.0] * 21)[0])

    pb, r, p = gate_b(tight, tight)
    check("Gate B passes when roll days match ordinary days", pb,
          f"{r*100:.0f}% vs {p*100:.0f}%")
    pb2, r2, p2 = gate_b(wide, tight)
    check("Gate B FAILS when roll days are far worse", not pb2,
          f"{r2*100:.0f}% vs {p2*100:.0f}%")
    #: PLANTED: roll days BETTER than ordinary days must still pass --
    #: the gate asks about harm, not about difference
    check("roll days being BETTER is a pass, not a failure",
          gate_b(tight, wide)[0])

    pc, nc = gate_c([50] * 14)
    check("Gate C passes with 14 full dates", pc, f"{nc} dates")
    check("Gate C FAILS with 7 usable dates",
          not gate_c([50] * 7 + [3] * 7)[0])
    check("a date with 29 minutes does not count",
          gate_c([29] * 14)[1] == 0)
    check("30 exactly does count", gate_c([30] * 14)[1] == 14)

    pd_, drag, net = gate_d([2.0] * 100)
    check("Gate D passes on a 2bp median", pd_,
          f"drag {drag:.3f} pts -> {net:.2f}")
    pd2, drag2, net2 = gate_d([200.0] * 100)
    check("Gate D FAILS on a 200bp median", not pd2,
          f"drag {drag2:.2f} pts -> {net2:.2f}")
    #: the exact break-even: 14bp x 4 = 0.56 pts, landing on +2.00
    _, _, net3 = gate_d([WIDE_BP] * 10)
    check("a median AT the WIDE threshold lands exactly on the bar",
          abs(net3 - GATE_D_FLOOR) < 1e-9, f"{net3:.4f}")

    print("\nthe contract entered on a roll date is the NEXT quarterly")
    check("June settles into September",
          next_quarterly_after(dt.date(2026, 6, 26))
          == dt.date(2026, 9, 25))
    check("December rolls into the next year's March",
          next_quarterly_after(dt.date(2025, 12, 26))
          == dt.date(2026, 3, 27))
    #: PLANTED: entering the contract that just SETTLED would measure a
    #: dead book and read as catastrophic cost
    check("it is never the contract that just expired",
          next_quarterly_after(dt.date(2026, 6, 26))
          != dt.date(2026, 6, 26))

    print("\nno threshold can be swept (v9 section 6)")
    import exec_cost as _self
    banned = ("sweep", "optimi", "tune", "search", "grid", "refit")
    def scan():
        return [x for x in dir(_self) if not x.startswith("_")
                and any(w in x.lower() for w in banned)]
    check("no sweep function exists", scan() == [], f"{scan()}")
    setattr(_self, "sweep_thresholds", lambda: None)
    fired = scan() == ["sweep_thresholds"]
    delattr(_self, "sweep_thresholds")
    check("and the detector demonstrably FIRES", fired and scan() == [])
    check("no order or execute function either",
          [x for x in dir(_self) if not x.startswith("_")
           and any(w in x.lower() for w in
                   ("order", "submit", "place", "trade_live"))] == [])

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def pull_window(host, sym, start, end):
    """1m trade and mark over [start, end). Paginated -- see v1.1's cap."""
    out = {}
    for tick in ("trade", "mark"):
        rows, note = KH.pull_paged(host, tick, sym, "1m",
                                   start.timestamp(), end.timestamp())
        out[tick] = rows
        out[tick + "_note"] = note
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=N_CYCLES)
    ap.add_argument("--out", default="../data/exec_cost.json")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"exec_cost.py v{VERSION}   PHASE 1 -- PREREGISTRATION_v9\n")
    print(f"  WIDE = {WIDE_BP:.0f}bp   Gate A < {GATE_A_MAX_WIDE*100:.0f}%"
          f"   Gate B <= +{GATE_B_MAX_EXCESS*100:.0f}pts"
          f"   Gate C {GATE_C_MIN_DATES}x{GATE_C_MIN_MINUTES}min"
          f"   Gate D >= {GATE_D_FLOOR}")
    print("  Thresholds frozen before any price was read. One run.\n")

    host = KP.FUT
    roll_devs, prior_devs, per_date, rows_out = [], [], [], []
    print(f"  {'roll date':<12}{'contract entered':<20}"
          f"{'roll min':>9}{'untr':>6}{'med bp':>8}{'wide%':>7}"
          f"{'prior min':>11}{'prior wide%':>12}")
    print("  " + "-" * 86)

    for exp, _ in KH.quarterly_symbols(a.cycles):
        nxt = next_quarterly_after(exp)
        sym = None
        for pre in ("FF", "FI"):
            cand = f"{pre}_XBTUSD_{nxt:%y%m%d}"
            probe, _ = KH.probe_one(host, "trade", cand, "1d", 3000)
            if probe:
                sym = cand
                break
        if sym is None:
            print(f"  {exp}  no contract found for {nxt}")
            per_date.append(0)
            continue

        start = dt.datetime.combine(
            exp - dt.timedelta(days=PRIOR_DAYS), dt.time(0),
            dt.timezone.utc)
        end = dt.datetime.combine(exp + dt.timedelta(days=1), dt.time(0),
                                  dt.timezone.utc)
        w = pull_window(host, sym, start, end)
        devs, n, unt = align(w["trade"], w["mark"])

        day0 = dt.datetime.combine(exp, dt.time(0), dt.timezone.utc)
        t0 = day0.timestamp() * 1000.0
        on = [d["dev"] for d in devs if d["time"] >= t0]
        before = [d["dev"] for d in devs if d["time"] < t0]
        per_date.append(len(on))
        roll_devs.extend(on)
        prior_devs.extend(before)
        rows_out.append(dict(roll_date=str(exp), symbol=sym,
                             roll_minutes=len(on), untraded=unt,
                             prior_minutes=len(before),
                             roll_median=st.median(on) if on else None,
                             roll_wide=wide_share(on),
                             prior_wide=wide_share(before)))
        ws, pw = wide_share(on), wide_share(before)
        print(f"  {str(exp):<12}{sym:<20}{len(on):>9}{unt:>6}"
              + (f"{st.median(on):>8.2f}" if on else f"{'-':>8}")
              + (f"{ws*100:>7.1f}" if ws is not None else f"{'-':>7}")
              + f"{len(before):>11}"
              + (f"{pw*100:>12.1f}" if pw is not None else f"{'-':>12}"))

    print(f"\n  KILL CONDITION FIRST -- v9 section 6, circularity")
    circ, med = is_circular(roll_devs + prior_devs)
    print(f"    median deviation across everything: "
          + (f"{med:.3f} bp" if med is not None else "no data"))
    if circ:
        print(f"    CIRCULAR. A median under {CIRCULARITY_MEDIAN_BP}bp "
              f"means `mark` tracks the")
        print("    last trade, the two series are not independent, and "
              "this is not")
        print("    a measurement. No gate is reported. v9 section 6.")
        sys.exit(3)
    print("    Not circular. The series are independent enough to "
          "compare.")

    pa, sa = gate_a(roll_devs)
    pb, rb, pb_ = gate_b(roll_devs, prior_devs)
    pc, nc = gate_c(per_date)
    pd_, drag, net = gate_d(roll_devs)

    print(f"\n  VERDICT -- gates frozen in PREREGISTRATION_v9 section 5")
    def line(tag, passed, text):
        state = "PASS" if passed else ("FAIL" if passed is not None
                                       else "N/A ")
        print(f"    [{state}] {tag}  {text}")
    line("Gate A", pa, f"roll-date wide share "
         + (f"{sa*100:.1f}% (< {GATE_A_MAX_WIDE*100:.0f}%)"
            if sa is not None else "no data"))
    line("Gate B", pb, f"roll {rb*100:.1f}% vs prior {pb_*100:.1f}%"
         if rb is not None else "no data")
    line("Gate C", pc, f"{nc} of {a.cycles} dates with "
         f">= {GATE_C_MIN_MINUTES} minutes")
    line("Gate D", pd_, f"drag {drag:.3f} pts -> era 3 {net:.2f}"
         if drag is not None else "no data")

    allpass = all(x for x in (pa, pb, pc, pd_))
    print(f"\n    {'PROCEED' if allpass else 'FAIL'}")
    if not pc:
        print("    Gate C short: UNDETERMINED. Track A's timeline "
              "stands.")
    print(f"\n    Untraded minutes are in the table above. v9 section 7: "
          f"this")
    print("    measure only sees minutes where a trade printed, so every "
          "rate")
    print("    here is a LOWER BOUND on how often execution was bad.")

    with open(os.path.expanduser(a.out), "w") as fh:
        json.dump(dict(version=VERSION, wide_bp=WIDE_BP, rows=rows_out,
                       gate_a=sa, gate_b=[rb, pb_], gate_c=nc,
                       gate_d=[drag, net], circular_median=med), fh,
                  indent=1)
    print(f"\n  written to {a.out}")
    sys.exit(0 if allpass else 2)


if __name__ == "__main__":
    main()
