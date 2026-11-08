#!/usr/bin/env python3
"""PREREGISTRATION_v16 / v16.1 -- has the reachable carry spread ever
cleared 2.0 %/yr?

RESULT_FXCARRY reduced the question to one number. Each leg is held
against USD, so the USD cancels and the book earns

    r_top - r_bottom - s_long - s_short

With today's measured tolls that is 5.22 - 3.86 = +1.36, and the family
needs about **5.9 points of cross-country dispersion** to clear a 2.0%
bar. This asks how often it has.

WHAT IS INHERITED, NOT RE-CHOSEN
--------------------------------
  quintile size   k = n // 5, minimum 1          (v15, via v16 s3)
  USD excluded    it is the vehicle for BOTH legs, so "long USD against
                  USD" is nothing. v15's book ranked 17 of 18 for the
                  same reason and got k=3; this ranks 15 of 16 and gets
                  k=3 as well.
  markups         per currency, measured 2026-09-04, from
                  fx_carry_access.json -- not an average, so a
                  high-markup currency entering a quintile carries its
                  own toll.

**NO RETURN SERIES IS COMPUTED ANYWHERE IN THIS FILE.** v16 section 9
forbids it: this measures a toll against a dispersion, and turning that
into a P&L is a separate pre-registration.

STDLIB ONLY.

    python3 carry_dispersion.py --self-test
    python3 carry_dispersion.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics as st
import sys

VERSION = "1.1"

#: v1.1 -- THE KILL WAS SCOPED WRONG.
#:
#: v1.0 computed all 968 months, applied v16 s9's 25% kill to every one,
#: and only then applied v16.1's window. So it stopped on AUD = 42.50 in
#: 1980-06 -- a month the study explicitly excludes and no mean ever
#: touches. s9 says "investigated before it enters a mean"; a datum that
#: enters no mean cannot corrupt one.
#:
#: v1.1 applies the kill to the months actually used. In the PRIMARY
#: window this changes nothing whatever -- there are ZERO months over
#: the threshold there -- so the gated result is untouched by the
#: narrowing. In the SECONDARY window the 24 offending months are
#: EXCLUDED and counted rather than silently averaged in.
#:
#: What they are, checked individually rather than assumed:
#:   AUD 42.50 (1980-06)  neighbours 11.0 and 13.5 -- a spike
#:   NZD 54.30 (1985-02)  deregulation
#:   SEK 40.00 (1992-09)  the krona defence; the marginal rate hit 500%
#:   PLN 31.00 (1994-06)  post-communist transition
#: Emergency and transition rates, none of them tradeable carry -- which
#: independently supports v16.1's choice of 2000-08 as the primary
#: window, made before any of this was visible.

#: ---- FROZEN IN v16 SECTION 6 ----
BAR = 2.0                    # %/yr the book must clear
GATE_A_MIN_FRACTION = 0.25
GATE_B_MIN_RUN = 24          # contiguous months
GATE_C_SCALES = (0.5, 1.0, 1.5)
#: ---- FROZEN IN v16.1 SECTION 11.2 ----
PRIMARY_FROM, PRIMARY_TO = "2000-08", "2026-08"
SECONDARY_FROM = "1986-03"
#: ---- v16 SECTION 9 ----
MAX_PLAUSIBLE_GROSS = 25.0
VEHICLE = "USD"


def quintile_k(n):
    """v15's rule, inherited verbatim."""
    return max(1, n // 5)


def load_rates(path):
    """{month: {currency: rate}}"""
    out = {}
    for r in csv.DictReader(open(path)):
        out.setdefault(r["month"], {})[r["currency"]] = float(r["rate_pct"])
    return out


def load_markups(path):
    """{currency: s in %/yr}, from the pair quoted against the vehicle."""
    j = json.load(open(path))
    out = {}
    for name, r in j.get("pairs", {}).items():
        parts = name.split("_")
        if len(parts) != 2 or not all(len(p) == 3 for p in parts):
            continue
        a, b = parts
        if b == VEHICLE:
            out[a] = r["s"] * 100.0
        elif a == VEHICLE:
            out[b] = r["s"] * 100.0
    return out


def month_spread(rates, markups):
    """(gross, net, longs, shorts, n) for one month, or None.

    The vehicle currency is not rankable: both legs are held against it.
    """
    avail = {c: v for c, v in rates.items()
             if c != VEHICLE and c in markups}
    n = len(avail)
    if n < 2:
        return None
    k = quintile_k(n)
    order = sorted(avail, key=lambda c: -avail[c])
    longs, shorts = order[:k], order[-k:]
    if set(longs) & set(shorts):
        return None                        # too few to form two quintiles
    gross = (st.mean(avail[c] for c in longs)
             - st.mean(avail[c] for c in shorts))
    sl = st.mean(markups[c] for c in longs)
    ss = st.mean(markups[c] for c in shorts)
    return gross, gross - sl - ss, longs, shorts, n


def longest_run(flags):
    """Longest contiguous True run. v16 Gate B."""
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return best


def score(months, series, scale=1.0):
    """(fraction clearing, longest run, n) at a markup scale."""
    vals = []
    for m in months:
        g, net, L, S, n = series[m]
        sl_ss = g - net                    # the toll at scale 1.0
        vals.append(g - sl_ss * scale)
    flags = [v >= BAR for v in vals]
    return (sum(flags) / len(flags) if flags else 0.0,
            longest_run(flags), len(flags), vals)


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"carry_dispersion.py v{VERSION} self-test\n")

    print("the quintile rule is v15's, unchanged")
    check("15 rankable gives k=3, as v15's book did",
          quintile_k(15) == 3, f"{quintile_k(15)}")
    check("14 gives k=2 -- so losing JPY changes the CONSTRUCTION",
          quintile_k(14) == 2, f"{quintile_k(14)}")
    check("17 gives k=3, matching v15's own output", quintile_k(17) == 3)
    check("a tiny universe floors at 1, it does not crash",
          quintile_k(3) == 1 and quintile_k(0) == 1)

    print("\nthe vehicle currency is not rankable")
    #: PLANTED: USD has the HIGHEST rate here. If it is ranked it lands
    #: in the top quintile and the book tries to hold USD against USD,
    #: which is nothing -- and the spread comes out wrong.
    rates = {"USD": 9.0, "AAA": 8.0, "BBB": 7.0, "CCC": 6.0,
             "DDD": 2.0, "EEE": 1.0}
    mk = {c: 1.0 for c in rates}
    g, net, L, S, n = month_spread(rates, mk)
    check("USD is excluded from the ranking", VEHICLE not in L + S,
          f"long {L} short {S}")
    check("so n counts only the rankable five", n == 5, f"{n}")
    check("k = 1 on five rankable", len(L) == 1 and len(S) == 1)
    check("the top is AAA (8.0), not USD (9.0)", L == ["AAA"], f"{L}")
    check("gross is 8.0 - 1.0 = 7.0", abs(g - 7.0) < 1e-12, f"{g}")
    check("net subtracts BOTH tolls: 7.0 - 1.0 - 1.0 = 5.0",
          abs(net - 5.0) < 1e-12, f"{net}")

    print("\nper-currency tolls, not an average")
    #: PLANTED: an expensive top quintile and a cheap bottom one. Using
    #: a single average toll would give the same answer for both and
    #: hide that the high-carry currencies cost more -- which is exactly
    #: what RESULT_FXCARRY measured (ZAR 2.4%, TRY 7.4%, majors 1.0%).
    mk2 = {"AAA": 3.0, "BBB": 1.0, "CCC": 1.0, "DDD": 1.0, "EEE": 0.5,
           "USD": 1.0}
    g2, net2, L2, S2, _ = month_spread(rates, mk2)
    check("the toll follows the members, not the mean",
          abs(net2 - (7.0 - 3.0 - 0.5)) < 1e-12, f"{net2}")
    check("and it differs from the flat-toll answer",
          abs(net2 - net) > 1e-9)

    print("\nGate B is contiguity, not a count")
    #: PLANTED: twelve clearing months that never run consecutively.
    #: A fraction test passes on this; Gate B must not.
    scattered = [True, False] * 12
    check("24 scattered months give a longest run of 1",
          longest_run(scattered) == 1, f"{longest_run(scattered)}")
    check("24 consecutive give 24",
          longest_run([True] * 24) == 24)
    check("and that is the frozen threshold", GATE_B_MIN_RUN == 24)
    check("an empty history gives 0", longest_run([]) == 0)
    check("a run at the very end is still found",
          longest_run([False] * 5 + [True] * 7) == 7)

    print("\nthe markup scaling moves the toll, never the rates")
    series = {"2020-01": (6.0, 6.0 - 3.86, ["A"], ["B"], 15)}
    f1, r1, n1, v1 = score(["2020-01"], series, 1.0)
    f05, _, _, v05 = score(["2020-01"], series, 0.5)
    f15, _, _, v15_ = score(["2020-01"], series, 1.5)
    check("at x1.0 the net is gross minus the toll",
          abs(v1[0] - (6.0 - 3.86)) < 1e-12, f"{v1[0]:.2f}")
    check("at x0.5 the toll halves", abs(v05[0] - (6.0 - 1.93)) < 1e-12,
          f"{v05[0]:.2f}")
    check("at x1.5 it rises by half", abs(v15_[0] - (6.0 - 5.79)) < 1e-12,
          f"{v15_[0]:.2f}")
    #: PLANTED: this month clears at x0.5 and x1.0 but not at x1.5 --
    #: exactly the sensitivity Gate C exists to catch.
    check("and the verdict genuinely flips across the band",
          f05 == 1.0 and f1 == 1.0 and f15 == 0.0,
          f"{f05:.0f} {f1:.0f} {f15:.0f}")

    print("\nthe windows are v16.1's, and pre-1986 is excluded")
    check("primary starts when all sixteen are present",
          PRIMARY_FROM == "2000-08")
    check("secondary starts where k >= 2", SECONDARY_FROM == "1986-03")
    check("the bar and Gate A fraction are v16's",
          BAR == 2.0 and GATE_A_MIN_FRACTION == 0.25)

    print("\na month with too few currencies is refused, not fudged")
    check("one rankable currency returns nothing",
          month_spread({"USD": 5.0, "AAA": 4.0}, {"AAA": 1.0,
                                                  "USD": 1.0}) is None)
    check("a currency with no measured toll is not ranked",
          month_spread(rates, {"AAA": 1.0, "EEE": 1.0, "USD": 1.0})[4] == 2)

    print("\nthe unit kill is scoped to the months actually used (v1.1)")
    #: PLANTED: one absurd month INSIDE the primary window and one
    #: OUTSIDE it. v1.0 stopped on the outside one, which no mean
    #: touches. The inside one must still stop the run.
    hot_out, hot_in = "1980-06", "2010-06"
    ser = {hot_out: (39.5, 35.6, ["AUD"], ["CHF"], 6),
           hot_in: (39.5, 35.6, ["ZAR"], ["JPY"], 15),
           "2011-01": (5.2, 1.3, ["ZAR"], ["JPY"], 15)}
    prim = sorted(m for m in ser if PRIMARY_FROM <= m <= PRIMARY_TO)
    hot = {m for m, r in ser.items() if abs(r[0]) > MAX_PLAUSIBLE_GROSS}
    check("both absurd months are detected", hot == {hot_out, hot_in})
    check("the pre-1986 one is NOT in the primary window",
          hot_out not in prim, f"primary={prim}")
    check("but the in-window one IS, and must stop the run",
          sorted(hot & set(prim)) == [hot_in])
    #: PLANTED: with only the out-of-window anomaly, the run proceeds.
    ser2 = {k: v for k, v in ser.items() if k != hot_in}
    prim2 = sorted(m for m in ser2 if PRIMARY_FROM <= m <= PRIMARY_TO)
    hot2 = {m for m, r in ser2.items() if abs(r[0]) > MAX_PLAUSIBLE_GROSS}
    check("a purely out-of-window anomaly does not stop the study",
          hot2 & set(prim2) == set(), f"{hot2 & set(prim2)}")
    check("and it is still reported rather than hidden", hot2 != set())

    print("\nthis file computes no return series")
    import carry_dispersion as _self
    banned = ("pnl", "backtest", "equity", "drawdown", "sharpe", "order",
              "position", "signal", "optimi", "sweep")
    off = [x for x in dir(_self) if not x.startswith("_")
           and any(w in x.lower() for w in banned)]
    check("no P&L, equity curve or position function exists", off == [],
          f"{off}")

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rates", default="../data/policy_rates.csv")
    ap.add_argument("--markups", default="../data/fx_carry_access.json")
    ap.add_argument("--dump", default="../data/carry_dispersion.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"carry_dispersion.py v{VERSION}   PREREGISTRATION_v16 / v16.1\n")
    rates = load_rates(a.rates)
    markups = load_markups(a.markups)
    print(f"  months of rates: {len(rates):,}")
    print(f"  tolls measured for {len(markups)} currencies "
          f"(median {st.median(markups.values()):.2f} %/yr per side)")

    #: Any of the universe with no measured toll is silently unrankable,
    #: so it is named. A silent drop is how a cross-section quietly
    #: becomes a different cross-section.
    universe = {c for row in rates.values() for c in row} - {VEHICLE}
    untolled = sorted(universe - set(markups))
    if untolled:
        print(f"  NO MEASURED TOLL, so not rankable: {untolled}")

    series, skipped = {}, 0
    for m, row in rates.items():
        r = month_spread(row, markups)
        if r is None:
            skipped += 1
            continue
        series[m] = r
    print(f"  months with a computable spread: {len(series):,} "
          f"({skipped} skipped)\n")

    #: v1.1: window FIRST, then apply v16 s9's kill to what is used.
    hot = {m for m, r in series.items()
           if abs(r[0]) > MAX_PLAUSIBLE_GROSS}
    primary = sorted(m for m in series if PRIMARY_FROM <= m <= PRIMARY_TO)
    secondary = sorted(m for m in series if SECONDARY_FROM <= m)
    if not primary:
        raise SystemExit("no months in the primary window")

    hot_primary = sorted(hot & set(primary))
    if hot_primary:
        print(f"  KILL: {len(hot_primary)} PRIMARY months exceed "
              f"{MAX_PLAUSIBLE_GROSS}%/yr gross -- v16 section 9.")
        for m in hot_primary[:5]:
            g, _, L, S, _ = series[m]
            print(f"    {m}  gross {g:+.2f}  top {L}  bottom {S}")
        sys.exit(3)
    print(f"  v16 s9 unit kill: 0 of {len(primary)} primary months over "
          f"{MAX_PLAUSIBLE_GROSS:.0f}%/yr gross")
    hot_secondary = sorted(hot & set(secondary))
    if hot_secondary:
        print(f"  {len(hot_secondary)} SECONDARY months excluded as "
              f"emergency/transition rates:")
        worst = sorted(hot_secondary, key=lambda m: -series[m][0])[:4]
        for m in worst:
            g, _, L, S, _ = series[m]
            print(f"    {m}  gross {g:+6.2f}  top {L[0]}  bottom {S[-1]}")
        secondary = [m for m in secondary if m not in hot]
    out_of_window = sorted(hot - set(secondary) - set(primary))
    if out_of_window:
        print(f"  {len(out_of_window)} more before {SECONDARY_FROM}, "
              f"outside every window (v16.1 s11.2): "
              f"{', '.join(out_of_window[:4])}"
              + (" ..." if len(out_of_window) > 4 else ""))
    print()

    ks = {len(series[m][2]) for m in primary}
    print(f"  PRIMARY  {primary[0]} .. {primary[-1]}   "
          f"{len(primary)} months, k in {sorted(ks)}")
    print(f"  today's reference: gross 5.22, toll 3.86, net +1.36\n")

    fA, runA, nA, vals = score(primary, series)
    ga = fA >= GATE_A_MIN_FRACTION
    gb = runA >= GATE_B_MIN_RUN
    print(f"  {'scale':<8}{'clears':>9}{'fraction':>11}{'longest run':>13}"
          f"{'median net':>12}")
    verdicts = {}
    for sc in GATE_C_SCALES:
        f, run, n, v = score(primary, series, sc)
        verdicts[sc] = (f >= GATE_A_MIN_FRACTION, run >= GATE_B_MIN_RUN)
        mark = "  <- as measured" if sc == 1.0 else ""
        print(f"  x{sc:<7.1f}{sum(1 for x in v if x >= BAR):>9}"
              f"{f*100:>10.1f}%{run:>13}{st.median(v):>+12.2f}{mark}")
    gc = len(set(verdicts.values())) == 1

    print(f"\n  VERDICT -- gates frozen in v16 section 6")
    print(f"    [{'PASS' if ga else 'FAIL'}] Gate A  {fA*100:.1f}% of "
          f"months clear {BAR:.1f}%/yr (need "
          f"{GATE_A_MIN_FRACTION*100:.0f}%)")
    print(f"    [{'PASS' if gb else 'FAIL'}] Gate B  longest contiguous "
          f"run {runA} months (need {GATE_B_MIN_RUN})")
    print(f"    [{'PASS' if gc else 'FAIL'}] Gate C  the verdict is "
          f"{'STABLE' if gc else 'NOT stable'} across markup "
          f"x0.5 / x1.0 / x1.5")
    if not gc:
        print(f"           {verdicts} -- so the answer is a statement")
        print(f"           about the unmeasured markup, not the market.")
    allp = ga and gb and gc
    if allp:
        overall = "PROCEED"
    elif ga and gb and not gc:
        overall = "UNDETERMINED"
    else:
        overall = "FAIL"
    print(f"\n    {overall}")

    #: v16.1 section 11.3 -- mandatory, so the bias is visible.
    print(f"\n  JPY DIAGNOSTIC -- v16.1 section 11.3")
    withj = [m for m in primary if "JPY" in rates[m]]
    without = [m for m in primary if "JPY" not in rates[m]]
    for lab, ms in (("JPY present", withj), ("JPY absent", without)):
        if len(ms) < 2:
            print(f"    {lab:<14}n={len(ms)}")
            continue
        f, run, n, v = score(ms, series)
        print(f"    {lab:<14}n={len(ms):>4}  median net {st.median(v):+7.2f}"
              f"  clears {f*100:5.1f}%  k in "
              f"{sorted({len(series[m][2]) for m in ms})}")
    if len(without) >= 2 and len(withj) >= 2:
        _, _, _, vw = score(withj, series)
        _, _, _, vo = score(without, series)
        d = st.median(vo) - st.median(vw)
        print(f"    difference {d:+.2f} %/yr. v16.1 predicted the spread "
              f"is UNDERSTATED\n    when JPY is absent, so a negative "
              f"number here is the expected sign.")

    print(f"\n  BY ERA -- v16 section 7 predicted by these periods")
    for lo, hi in ((2000, 2002), (2003, 2008), (2009, 2015),
                   (2016, 2021), (2022, 2026)):
        ms = [m for m in primary if lo <= int(m[:4]) <= hi]
        if len(ms) < 2:
            continue
        f, run, n, v = score(ms, series)
        print(f"    {lo}-{hi}  n={len(ms):>4}  median gross "
              f"{st.median([series[m][0] for m in ms]):5.2f}  "
              f"median net {st.median(v):+6.2f}  clears {f*100:5.1f}%")

    print(f"\n  SECONDARY (not gated) -- {secondary[0]} .. {secondary[-1]}, "
          f"a GROWING universe")
    fs, runs_, ns, vs = score(secondary, series)
    print(f"    n={ns}  clears {fs*100:.1f}%  longest run {runs_}  "
          f"median net {st.median(vs):+.2f}")
    print(f"    k ranges {sorted({len(series[m][2]) for m in secondary})} "
          f"-- read as a changing cross-section, not a stable one.")

    if a.dump:
        with open(a.dump, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["month", "n", "k", "gross", "toll", "net",
                        "longs", "shorts", "jpy_present"])
            for m in sorted(series):
                g, net, L, S, n = series[m]
                w.writerow([m, n, len(L), f"{g:.4f}", f"{g-net:.4f}",
                            f"{net:.4f}", "|".join(L), "|".join(S),
                            int("JPY" in rates[m])])
        print(f"\n  written to {a.dump}")
    print(f"\n  No return series was computed. v16 section 9.")


if __name__ == "__main__":
    main()
