#!/usr/bin/env python3
"""PHASE 0 for PREREGISTRATION_v6 -- what does equity beta cost at OANDA?

WHY THIS EXISTS
---------------
Twenty-two investigations have been benchmarked against "equity beta at
0.4-0.5 Sharpe" and not one of them asked what holding equity beta THROUGH
THE ACCOUNTS ACTUALLY AVAILABLE costs.

An OANDA index CFD is not an index fund. It charges daily financing on the
full notional, because a CFD is a fully funded position. The same identity
that decomposed FX financing applies, and for an index it simplifies:

    long an index CFD  =  borrow cash, hold the index
    longRate  = -(r + m)        shortRate = +(r - m)
    D = (longRate - shortRate)/2 = -r       m = -(longRate + shortRate)/2

so |D| recovers the funding rate and m the markup, and

    cost of being long  =  |D| + m

NOTHING NEW IS FETCHED. The manifest fx_carry_probe already wrote contains
all 123 instruments, including the 55 non-FX rows the carry gate excluded.

WHAT IT DECIDES (PREREGISTRATION_v6 section 4)
----------------------------------------------
If financing consumes more than half the equity premium, that is the
headline finding and every "beats equity beta" comparison in this project
was made against a benchmark that could not be bought at the assumed price.
It does NOT stop the run -- whether vol targeting works is worth knowing
either way -- but it stops the answer being quoted as if it were reachable.

    python equity_cost.py --self-test
    python equity_cost.py --manifest ../data/fx_carry.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

VERSION = "1.0"

#: Declared, not tuned. Long-run US equity TOTAL return and the dividend
#: component of it. Both are shown separately below because the venue's
#: dividend treatment decides which one applies.
EQUITY_TOTAL = 0.095
EQUITY_DIV = 0.019
HALF = 0.50                       # section 4's threshold

INDICES = ["SPX500_USD", "US30_USD", "NAS100_USD"]


def decompose(long_rate, short_rate):
    return (long_rate - short_rate) / 2.0, -(long_rate + short_rate) / 2.0


def long_cost(long_rate, short_rate):
    """Annual cost of holding a long index CFD: funding plus markup.

    Equals -longRate by construction. Computed the long way round so the
    two components can be reported separately, and cross-checked against
    -longRate in the self-test -- if those disagree, the model of OANDA's
    formula is wrong and the split is meaningless.
    """
    D, m = decompose(long_rate, short_rate)
    return abs(D) + m, abs(D), m


def premium_left(cost, total=EQUITY_TOTAL, div=EQUITY_DIV):
    """What survives, under both dividend treatments.

    An index CFD tracks a PRICE index. Whether the venue credits dividend
    adjustments to a long position is a contract term, not a market fact,
    and it is worth roughly two points a year -- which against a four to
    five point financing charge is the difference between a thin result
    and no result at all. Both are reported; neither is assumed.
    """
    with_div = total - cost
    without_div = (total - div) - cost
    return with_div, without_div


def verdict(cost, total=EQUITY_TOTAL):
    """Does financing eat more than half the premium?"""
    share = cost / total if total else float("inf")
    return share, share > HALF


def report(rows):
    print(f"\n  assuming a long-run equity TOTAL return of "
          f"{EQUITY_TOTAL*100:.1f}%/yr, of which "
          f"{EQUITY_DIV*100:.1f} points is dividends")
    print(f"\n  {'instrument':<14}{'funding':>10}{'markup':>9}"
          f"{'long cost':>11}{'left w/ div':>13}{'left w/o':>10}"
          f"{'eaten':>8}")
    print("  " + "-" * 75)
    worst = None
    for r in rows:
        c, D, m = long_cost(r["longRate"], r["shortRate"])
        wd, wo = premium_left(c)
        share, _ = verdict(c)
        worst = share if worst is None else max(worst, share)
        print(f"  {r['instrument']:<14}{D*100:>9.2f}%{m*100:>8.2f}%"
              f"{c*100:>10.2f}%{wd*100:>12.2f}%{wo*100:>9.2f}%"
              f"{share*100:>7.0f}%")
    if worst is None:
        print("    no index instruments found in the manifest")
        return None
    print(f"\n  PHASE 0 -- PREREGISTRATION_v6 section 4")
    if worst > HALF:
        print(f"    [FINDING] financing consumes {worst*100:.0f}% of the "
              f"equity premium")
        print("    Every 'beats equity beta' comparison in this project "
              "was made against")
        print("    a benchmark that cannot be bought at the assumed price "
              "THROUGH THIS")
        print("    VENUE. The comparison is still fair against an index "
              "fund, which")
        print("    anyone can hold; it is not fair against a CFD.")
    else:
        print(f"    financing consumes {worst*100:.0f}% of the premium, "
              f"under the half-premium threshold")
    print("\n  VERIFY WITH THE BROKER BEFORE BELIEVING ANY OF IT")
    print("    Whether dividend adjustments are credited to a long index "
          "CFD is a")
    print("    contract term worth ~2 points a year. The 'left w/ div' and")
    print("    'left w/o' columns are the two answers; the venue decides "
          "which.")
    return worst


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"equity_cost.py v{VERSION} self-test\n")

    print("the index decomposition recovers what was planted")
    r, m = 0.038, 0.0105
    lr, sr = -(r + m), (r - m)
    D2, m2 = decompose(lr, sr)
    check("funding rate recovered", abs(abs(D2) - r) < 1e-12,
          f"{abs(D2)*100:.3f}% vs {r*100:.3f}%")
    check("markup recovered", abs(m2 - m) < 1e-12,
          f"{m2*100:.3f}% vs {m*100:.3f}%")
    c, _, _ = long_cost(lr, sr)
    #: the cross-check that matters: cost must equal -longRate exactly, or
    #: the model of OANDA's formula is wrong and the split is meaningless
    check("long cost equals -longRate exactly", abs(c - (-lr)) < 1e-12,
          f"{c*100:.3f}% vs {-lr*100:.3f}%")
    check("and it is funding PLUS markup, not minus",
          abs(c - (r + m)) < 1e-12, f"{c*100:.3f}%")

    print("\nthe dividend treatment is worth about two points")
    wd, wo = premium_left(0.0485)
    check("with dividends credited", abs(wd - (EQUITY_TOTAL - 0.0485)) < 1e-12,
          f"{wd*100:.2f}%")
    check("without, it is lower by exactly the dividend yield",
          abs((wd - wo) - EQUITY_DIV) < 1e-12,
          f"{wd*100:.2f}% vs {wo*100:.2f}%")
    check("and without dividends a 4.85% charge leaves under 3 points",
          wo < 0.03, f"{wo*100:.2f}%")

    print("\nthe half-premium gate, either side")
    share, over = verdict(0.0485)
    check("a 4.85% charge against 9.5% trips it", over,
          f"{share*100:.0f}%")
    share2, over2 = verdict(0.040)
    check("a 4.0% charge does not", not over2, f"{share2*100:.0f}%")
    #: the boundary is a STRICT inequality, and saying so beats discovering
    #: it. Exactly half does not trip; a hair over does.
    share3, over3 = verdict(EQUITY_TOTAL * HALF)
    check("exactly half does NOT trip -- the test is strictly greater",
          not over3 and abs(share3 - HALF) < 1e-12, f"{share3*100:.4f}%")
    share4, over4 = verdict(EQUITY_TOTAL * HALF * 1.0001)
    check("a hair over does", over4, f"{share4*100:.4f}%")

    print("\nan index CFD costs money to hold LONG, unlike an index fund")
    #: planted: the sign convention. If longRate were read as a credit
    #: rather than a charge, the cost would come out negative and the
    #: instrument would look like it pays you to own equities.
    c2, _, _ = long_cost(-0.0485, 0.0275)
    check("the cost is positive, i.e. you pay", c2 > 0, f"{c2*100:+.2f}%")
    check("a sign error would have made it look free",
          -c2 < 0, "reading longRate as a credit gives a negative cost")

    print("\nreal-shaped rows produce a finding, not a crash")
    rows = [dict(instrument="SPX500_USD", longRate=-0.0485,
                 shortRate=0.0275),
            dict(instrument="US30_USD", longRate=-0.0490,
                 shortRate=0.0280)]
    w = report(rows)
    check("the worst share is reported", w is not None and w > 0.5,
          f"{w*100:.0f}%")
    check("an empty manifest returns None, not zero", report([]) is None)

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="../data/fx_carry.json")
    ap.add_argument("--instruments", default=",".join(INDICES))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"equity_cost.py v{VERSION}   PHASE 0 -- WHAT EQUITY BETA COSTS "
          f"HERE\n")
    man = json.load(open(os.path.expanduser(a.manifest)))
    want = [s.strip().upper() for s in a.instruments.split(",")]
    rows = [r for r in man["rows"] if r["instrument"].upper() in want]
    missing = [w for w in want
               if not any(r["instrument"].upper() == w for r in rows)]
    print(f"  {len(rows)} of {len(want)} requested instruments in the "
          f"manifest"
          + (f"   (missing: {', '.join(missing)})" if missing else ""))
    report(rows)


if __name__ == "__main__":
    main()
