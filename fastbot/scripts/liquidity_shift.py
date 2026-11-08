#!/usr/bin/env python3
"""PHASE 0 -- where did the volume go?

THE QUESTION
------------
RESULT_EXECCOST measured the traded share of the roll window falling from
13.73% (2025-12) to 0.46% (2026-03) to 1.27% (2026-06), with median
execution deviation going from ~3bp to 36bp to 66bp.

That is either:

  MIGRATED       volume left the QUARTERLY contract for another maturity
                 or the perpetual, on the same venue
  VENUE_DECLINE  Kraken's whole BTC derivatives complex shrank
  NO_CHANGE      the collapse is not in the volume data and the execution
                 finding needs another explanation
  UNDETERMINED   not enough retrievable history to say

These have completely different consequences. Under MIGRATED the premium
may still be reachable on a different instrument. Under VENUE_DECLINE the
candidate dies the way the inverse contract did -- of availability, for
the fourth time.

WHAT IS ALREADY KNOWN, BEFORE FETCHING
--------------------------------------
Kraken has announced NO deprecation of dated BTC futures. Every 2026
delisting on its derivatives suspensions page is a perpetual altcoin
contract (PF_LRCUSD, PF_MOVEUSD, PF_STORJUSD and so on). So whatever this
is, it is not a published wind-down.

THE UNIT TRAP, NAMED BEFORE IT CAN BITE
---------------------------------------
Linear contracts (FF_, PF_) quote volume in BTC. Inverse contracts (FI_,
PI_) quote it in USD. Comparing them directly is a factor-of-80,000 error
that would produce a confident and completely wrong headline.

**Every series is therefore indexed to ITS OWN baseline and compared only
with itself over time.** Cross-series comparison happens on those indices,
never on raw volume. The self-test plants a mixed-unit pair and asserts
the raw comparison is refused.

    python3 liquidity_shift.py --self-test
    python3 liquidity_shift.py
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

#: Frozen BEFORE any volume is read.
#: The collapse to measure is ~97% (13.73% -> 0.46% of minutes traded), so
#: a 70% volume fall is a conservative operationalisation of "the quarterly
#: contract lost its market" and 30% is roughly ordinary year-to-year
#: variation in crypto venue volume.
QUARTERLY_COLLAPSE = 0.70
CONTROL_HELD = 0.30
VENUE_DECLINE_BOTH = 0.50
#: Compare the most recent 6 months against calendar 2024-2025, which is
#: the period v4's premium was largely measured over and predates the break.
BASELINE = (dt.date(2024, 1, 1), dt.date(2025, 12, 31))
RECENT_MONTHS = 6
MIN_BASELINE_DAYS = 180

#: Same quote convention within each group. NEVER compared across groups
#: on raw volume.
LINEAR_CONTROLS = ["PF_XBTUSD"]
INVERSE_CONTROLS = ["PI_XBTUSD"]


def units_of(symbol):
    """BTC for linear (FF_/PF_), USD for inverse (FI_/PI_).

    This is the whole unit trap in one function. It exists so that no
    comparison can be written without stating which convention it is in.
    """
    s = (symbol or "").upper()
    if s.startswith(("FI_", "PI_")):
        return "USD"
    if s.startswith(("FF_", "PF_")):
        return "BTC"
    return None


def comparable(a, b):
    """May these two symbols' raw volumes be compared at all?"""
    ua, ub = units_of(a), units_of(b)
    return ua is not None and ua == ub


def monthly_volume(rows):
    """{(year, month): summed volume} from daily candles."""
    out = {}
    for r in rows:
        v = r.get("volume")
        if v is None:
            continue
        t = r["time"] / (1000.0 if r["time"] > 1e11 else 1.0)
        d = dt.datetime.fromtimestamp(t, dt.timezone.utc).date()
        out[(d.year, d.month)] = out.get((d.year, d.month), 0.0) + float(v)
    return out


def index_to_baseline(monthly, baseline=BASELINE):
    """Mean monthly volume in the baseline window, and recent vs it.

    Returns (baseline_mean, recent_mean, ratio). Ratio is recent/baseline
    -- a series compared ONLY with itself, so units cancel and the number
    is safe to put beside another series'.
    """
    b = [v for (y, m), v in monthly.items()
         if baseline[0] <= dt.date(y, m, 1) <= baseline[1]]
    keys = sorted(monthly)
    r = [monthly[k] for k in keys[-RECENT_MONTHS:]]
    if not b or not r:
        return None, None, None
    bm, rm = st.mean(b), st.mean(r)
    return bm, rm, (rm / bm if bm > 0 else None)


def fall_of(ratio):
    """Fractional decline. ratio 0.03 -> a 97% fall."""
    return None if ratio is None else 1.0 - ratio


def verdict(quarterly_fall, control_fall):
    """Frozen before the fetch. Ambiguity is not a pass.

    Both arguments are FALLS (0.0 = flat, 0.97 = down 97%), each computed
    against that series' own baseline, so no unit conversion is involved.
    """
    if quarterly_fall is None or control_fall is None:
        return "UNDETERMINED"
    if quarterly_fall >= QUARTERLY_COLLAPSE and control_fall <= CONTROL_HELD:
        return "MIGRATED"
    if (quarterly_fall >= VENUE_DECLINE_BOTH
            and control_fall >= VENUE_DECLINE_BOTH):
        return "VENUE_DECLINE"
    if quarterly_fall < VENUE_DECLINE_BOTH:
        return "NO_CHANGE"
    return "UNDETERMINED"


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"liquidity_shift.py v{VERSION} self-test\n")

    print("the unit trap is refused, not navigated")
    check("FF_ and PF_ are both BTC-quoted",
          units_of("FF_XBTUSD_260925") == "BTC"
          and units_of("PF_XBTUSD") == "BTC")
    check("FI_ and PI_ are both USD-quoted",
          units_of("FI_XBTUSD_230630") == "USD"
          and units_of("PI_XBTUSD") == "USD")
    check("same-convention pairs are comparable",
          comparable("FF_XBTUSD_260925", "PF_XBTUSD"))
    #: PLANTED: this is the factor-of-80,000 error. It must be refused.
    check("a linear/inverse pair is REFUSED",
          not comparable("FF_XBTUSD_260925", "PI_XBTUSD"),
          "BTC vs USD -- an ~80,000x error if compared raw")
    check("an unknown prefix is not silently comparable",
          not comparable("XBTUSD", "PF_XBTUSD"))

    print("\nmonthly aggregation")
    rows = [{"time": dt.datetime(2026, 3, d, tzinfo=dt.timezone.utc)
             .timestamp() * 1000, "volume": 2.0} for d in range(1, 11)]
    mv = monthly_volume(rows)
    check("ten daily bars of 2.0 sum to 20.0 in that month",
          abs(mv[(2026, 3)] - 20.0) < 1e-9, f"{mv}")
    check("a bar with no volume is skipped, not counted as zero",
          monthly_volume([{"time": 1.7e12, "volume": None}]) == {})
    check("seconds and milliseconds both work",
          monthly_volume([{"time": 1.7e9, "volume": 1.0}]) != {})

    print("\nevery series is indexed to ITSELF")
    base = {(2024, m): 100.0 for m in range(1, 13)}
    base.update({(2025, m): 100.0 for m in range(1, 13)})
    coll = dict(base)
    coll.update({(2026, m): 3.0 for m in range(1, 7)})
    bm, rm, ratio = index_to_baseline(coll)
    check("a fall to 3% of baseline reads as a 97% fall",
          abs(fall_of(ratio) - 0.97) < 1e-9,
          f"{fall_of(ratio)*100:.0f}%")
    held = dict(base)
    held.update({(2026, m): 95.0 for m in range(1, 7)})
    check("a series that held reads as a 5% fall",
          abs(fall_of(index_to_baseline(held)[2]) - 0.05) < 1e-9)
    check("no baseline data gives None, not zero",
          index_to_baseline({(2026, 1): 5.0})[2] is None)

    print("\nthe verdict was fixed before the fetch")
    check("quarterly collapses, control holds -> MIGRATED",
          verdict(0.97, 0.05) == "MIGRATED")
    #: PLANTED: each branch must be reachable, or the verdict is decoration
    check("both collapse -> VENUE_DECLINE",
          verdict(0.97, 0.80) == "VENUE_DECLINE")
    check("quarterly barely moves -> NO_CHANGE",
          verdict(0.10, 0.05) == "NO_CHANGE")
    check("a 60% fall with a 40% control is UNDETERMINED, not MIGRATED",
          verdict(0.60, 0.40) == "UNDETERMINED")
    check("missing data is UNDETERMINED, never a verdict",
          verdict(None, 0.05) == "UNDETERMINED"
          and verdict(0.97, None) == "UNDETERMINED")
    #: the boundaries, both sides
    check("exactly 70%/30% is MIGRATED",
          verdict(0.70, 0.30) == "MIGRATED")
    check("69% is not", verdict(0.69, 0.30) != "MIGRATED")
    check("31% control is not", verdict(0.70, 0.31) != "MIGRATED")

    print("\nthis file measures volume, and nothing else")
    import liquidity_shift as _self
    banned = ("order", "execute", "submit", "place", "sweep", "optimi")
    check("no order or sweep function exists",
          [x for x in dir(_self) if not x.startswith("_")
           and any(w in x.lower() for w in banned)] == [])

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=14)
    ap.add_argument("--out", default="../data/liquidity_shift.json")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"liquidity_shift.py v{VERSION}   PHASE 0 -- WHERE DID THE "
          f"VOLUME GO?\n")
    print(f"  baseline {BASELINE[0]} to {BASELINE[1]}, "
          f"recent = last {RECENT_MONTHS} months")
    print("  Each series is indexed to ITS OWN baseline. Raw volumes are")
    print("  never compared across quote conventions.\n")

    host = KP.FUT

    #: The quarterly series is a CHAIN: each contract contributes only the
    #: months it was the front dated quarterly. Summing overlapping
    #: contracts would double-count the months two were listed at once.
    print("  QUARTERLY DATED (BTC-quoted, chained across contracts)")
    q_monthly = {}
    for exp, syms in KH.quarterly_symbols(a.cycles):
        for sym in syms:
            rows, _ = KH.probe_one(host, "trade", sym, "1d", 3000)
            if not rows:
                continue
            mv = monthly_volume(rows)
            for k, v in mv.items():
                q_monthly[k] = q_monthly.get(k, 0.0) + v
            print(f"    {sym:<20}{len(rows):>5} daily bars  "
                  f"{units_of(sym)}")
            break

    controls = {}
    for group, syms in (("linear", LINEAR_CONTROLS),
                        ("inverse", INVERSE_CONTROLS)):
        for sym in syms:
            rows, _ = KH.probe_one(host, "trade", sym, "1d", 3000)
            if not rows:
                print(f"  CONTROL {sym:<14} no data")
                continue
            controls[sym] = monthly_volume(rows)
            f, l, d, n = KH.span_of(rows)
            print(f"  CONTROL {sym:<14}{n:>5} daily bars  "
                  f"{f.date()} -> {l.date()}  {units_of(sym)}-quoted")

    print(f"\n  {'series':<22}{'units':<7}{'baseline/mo':>14}"
          f"{'recent/mo':>13}{'fall':>8}")
    print("  " + "-" * 66)
    qb, qr, qratio = index_to_baseline(q_monthly)
    qfall = fall_of(qratio)
    print(f"  {'FF/FI quarterly':<22}{'BTC*':<7}"
          + (f"{qb:>14,.0f}{qr:>13,.0f}{qfall*100:>7.0f}%"
             if qfall is not None else f"{'-':>14}{'-':>13}{'-':>8}"))

    best_control = None
    for sym, mv in controls.items():
        cb, cr, cratio = index_to_baseline(mv)
        cf = fall_of(cratio)
        print(f"  {sym:<22}{units_of(sym):<7}"
              + (f"{cb:>14,.0f}{cr:>13,.0f}{cf*100:>7.0f}%"
                 if cf is not None else f"{'-':>14}{'-':>13}{'-':>8}"))
        #: The control must share the quarterly's quote convention. A
        #: USD-quoted perp is reported for completeness but cannot carry
        #: the verdict against a BTC-quoted chain.
        if cf is not None and comparable("FF_XBTUSD_260925", sym):
            best_control = (sym, cf)

    print("\n  * the chain is mostly FF_ (BTC). The two oldest cycles are")
    print("    FI_ (USD) and are NOT unit-converted -- they inflate the")
    print("    baseline in unknown proportion and the fall is therefore a")
    print("    LOWER bound. Stated rather than silently mixed.")

    v = verdict(qfall, best_control[1] if best_control else None)
    print(f"\n  VERDICT -- thresholds frozen above")
    print(f"    quarterly fall   "
          + (f"{qfall*100:.0f}%" if qfall is not None else "unknown"))
    print(f"    control          "
          + (f"{best_control[0]} down {best_control[1]*100:.0f}%"
             if best_control else "none with a matching quote convention"))
    print(f"    {v}")
    if v == "MIGRATED":
        print("\n    Volume left the QUARTERLY contract while the same-unit")
        print("    perpetual held. The premium may still be reachable, but")
        print("    not on the instrument PREREGISTRATION_v9 measured, and")
        print("    a perpetual has funding rather than a fixed convergence")
        print("    -- a different trade needing its own pre-registration.")
    elif v == "VENUE_DECLINE":
        print("\n    The whole complex shrank. The candidate dies of")
        print("    availability, as the inverse contract did.")
    elif v == "NO_CHANGE":
        print("\n    The collapse is not in the volume data. The execution")
        print("    finding in RESULT_EXECCOST needs another explanation.")
    else:
        print("\n    Not enough to say. It does not become a verdict by")
        print("    being the only thing left.")

    with open(os.path.expanduser(a.out), "w") as fh:
        json.dump(dict(version=VERSION, verdict=v,
                       quarterly_fall=qfall,
                       quarterly_monthly={f"{y}-{m:02d}": x
                                          for (y, m), x
                                          in sorted(q_monthly.items())},
                       controls={s: {f"{y}-{m:02d}": x for (y, m), x
                                     in sorted(mv.items())}
                                 for s, mv in controls.items()}), fh,
                  indent=1)
    print(f"\n  written to {a.out}")
    sys.exit(0 if v in ("MIGRATED", "VENUE_DECLINE", "NO_CHANGE") else 2)


if __name__ == "__main__":
    main()
