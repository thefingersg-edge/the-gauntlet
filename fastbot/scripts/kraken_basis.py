#!/usr/bin/env python3
"""PHASE 1 for PREREGISTRATION_v4 -- the dated BTC futures basis, measured.

FROZEN SPEC. This implements PREREGISTRATION_v4.md and nothing else. One
run. No sweeps, no sign flips, no re-specification. Every threshold below
is quoted from that document, not chosen here.

    position   long 1 BTC spot held CONTINUOUSLY,
               short the nearest dated future, rolled at expiry     (sec 5)
    measure    REALISED convergence, not the quoted basis           (sec 6)
    costs      0.05% taker per futures leg, 0.26% per spot leg,
               lowest published tier, no volume discounts assumed   (sec 7)
    benchmark  the CONTEMPORANEOUS 3-month T-bill, period-matched.
               A single remembered number is not admissible         (sec 2)

    Gate A  net excess over T-bill, on TOTAL capital, >= 2.0 points
    Gate B  net excess positive in EVERY era (three equal thirds)
    Gate C  >= 12 cycles total, >= 3 per era
    Gate D  the collateral buffer that survives the worst observed
            intra-cycle rally -- and Gate A is applied AFTER it

THE ARITHMETIC THAT MAKES THIS SIMPLE
-------------------------------------
Per cycle, holding spot and short the future:

    P&L = (S_exit - S_entry) + (F_entry - F_exit)

If the future converges perfectly to the index at expiry, F_exit = S_exit
and the whole thing collapses to F_entry - S_entry: you lock the entry
basis and nothing else matters. That is the textbook claim, and this file
does NOT assume it. It measures the convergence residual (S_exit - F_exit)
per cycle and reports it, because section 6 asks for what was realised
rather than what was quoted, and a basis that fails to converge is the
finding rather than an inconvenience.

MY PREDICTION, from section 3, recorded before running: Gate A fails, and
Gate B fails specifically in 2022.

    python kraken_basis.py --self-test
    python kraken_basis.py --manifest ../data/kraken_manifest.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken_probe as KP                                    # noqa: E402

VERSION = "1.1"

#: PREREGISTRATION_v4 sections 2, 7 and 8. Frozen.
GATE_A_EXCESS = 0.020            # 2.0 percentage points over T-bill
MIN_CYCLES = 12
MIN_PER_ERA = 3
N_ERAS = 3
FEE_FUT = 0.0005                 # 0.05% taker, per futures leg
FEE_SPOT = 0.0026                # 0.26% taker, per spot leg
TICK_USD = 1.0                   # slippage, 1 tick per leg

#: DGS3MO first, deliberately. DTB3 is quoted on a DISCOUNT basis and sits
#: a few basis points BELOW the yield an investor actually earns, so using
#: it would flatter the strategy against its own benchmark. DGS3MO is the
#: coupon-equivalent constant-maturity yield -- the thing the cash would
#: really have made. Both satisfy the pre-registration's "3-month T-bill";
#: this picks the one that makes Gate A harder.
RF_SERIES = ["DGS3MO", "DTB3"]
RF_TMPL = ("https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
           "&cosd={cosd}&coed={coed}")
#: The unbounded CSV is the full history back to 1954 and times out on a
#: 30-second read. Asking for only the window needed makes it small.
RF_TIMEOUT = 90
RF_MIN_COVERAGE = 0.90


def candles(symbol, tick, res="1d", years_back=9):
    """Daily closes for one instrument and tick type, as a date->float dict."""
    import datetime as dt
    now = int(time.time())
    frm = now - int(years_back * 365.25 * 86400)
    url = KP.CHART_TEMPLATES[0].format(tick=tick, symbol=symbol, res=res,
                                       frm=frm, to=now)
    js = json.loads(KP._get(url))
    out = {}
    for c in js.get("candles", []):
        t = int(c["time"])
        t = t // 1000 if t > 1e11 else t
        out[dt.datetime.utcfromtimestamp(t).date()] = float(c["close"])
    return out


def parse_rf(raw):
    """Two columns, date and percent. '.' means a market holiday."""
    import datetime as dt
    out = {}
    for line in raw.decode().splitlines()[1:]:
        parts = line.split(",")
        if len(parts) < 2 or parts[1].strip() in (".", ""):
            continue
        try:
            out[dt.date.fromisoformat(parts[0].strip())] = \
                float(parts[1]) / 100.0
        except ValueError:
            continue
    return out


def rf_covers(rf, first, last, min_cov=RF_MIN_COVERAGE):
    """Does the rate series actually span the cycles it will benchmark?

    A partial series does not fail loudly -- it silently returns None for
    the cycles it misses, and those cycles drop out of the weighted mean.
    That would quietly re-select the sample on data availability, which is
    the same class of error as measuring the variance premium only after
    2010. So coverage is checked, and a thin series stops the run.
    """
    import datetime as dt
    a = dt.date.fromisoformat(str(first))
    b = dt.date.fromisoformat(str(last))
    if not rf:
        return 0.0, False
    want = sum(1 for k in range((b - a).days + 1)
               if (a + dt.timedelta(days=k)).weekday() < 5)
    have = sum(1 for d in rf if a <= d <= b)
    cov = have / want if want else 0.0
    return cov, cov >= min_cov


def risk_free(first, last, path=None):
    """Contemporaneous 3-month T-bill, as a date->annual-decimal dict.

    Section 2 requires this to be period-matched. If no series can be
    retrieved the measurement STOPS rather than substituting a constant:
    the rate moved from ~0.1% to ~5% inside this window, so a single
    number would decide Gate A by itself.
    """
    import datetime as dt
    if path:
        rf = parse_rf(open(os.path.expanduser(path), "rb").read())
        cov, ok = rf_covers(rf, first, last)
        print(f"    {os.path.basename(path)}: {len(rf):,} obs, "
              f"{cov*100:.0f}% coverage")
        if not ok:
            raise SystemExit(
                f"\n  STOP: that file covers only {cov*100:.0f}% of "
                f"{first} -> {last}.\n  A partial rate series silently "
                f"drops the cycles it misses, which\n  re-selects the "
                f"sample on data availability.")
        return rf
    #: bounded request: the full series back to 1954 is what times out
    pad = dt.timedelta(days=10)
    cosd = (dt.date.fromisoformat(str(first)) - pad).isoformat()
    coed = (dt.date.fromisoformat(str(last)) + pad).isoformat()
    for sid in RF_SERIES:
        url = RF_TMPL.format(sid=sid, cosd=cosd, coed=coed)
        try:
            rf = parse_rf(KP._get(url, timeout=RF_TIMEOUT, tries=2))
        except Exception as exc:                              # noqa: BLE001
            print(f"    {sid:<8} FAIL {str(exc)[:60]}")
            continue
        cov, ok = rf_covers(rf, first, last)
        print(f"    {sid:<8} {len(rf):,} obs, {cov*100:.0f}% coverage"
              + ("" if ok else "  -- too thin, trying the next"))
        if ok:
            return rf
    raise SystemExit(
        "\n  STOP: no risk-free series with adequate coverage. Section 2 "
        "requires a\n  period-matched benchmark and forbids a single "
        "remembered number.\n"
        "  Download it by hand and pass --rf-csv:\n"
        f"    {RF_TMPL.format(sid='DGS3MO', cosd=cosd, coed=coed)}\n"
        "  Two columns, date and percent. Until then this does not "
        "happen.")


def lookup(series, day, back=7):
    """Nearest value on or before `day`, within `back` days."""
    import datetime as dt
    for k in range(back + 1):
        v = series.get(day - dt.timedelta(days=k))
        if v is not None:
            return v
    return None


def build_cycles(contracts, fut, idx):
    """One cycle per contract: held from when it becomes nearest to expiry.

    Contracts overlap -- each is listed about seven months before it
    expires -- so "the nearest dated future" is held for roughly one
    quarter, from the previous contract's expiry to its own. Using the
    full listed life instead would double-count every calendar day and
    inflate the annualised figure.
    """
    import datetime as dt
    order = sorted(contracts, key=lambda c: c["expiry"])
    cycles = []
    for i, c in enumerate(order):
        exp = dt.date.fromisoformat(c["expiry"])
        listed = dt.date.fromisoformat(c["first"])
        prev = (dt.date.fromisoformat(order[i - 1]["expiry"])
                + dt.timedelta(days=1)) if i else listed
        entry = max(listed, prev)
        if entry >= exp:
            continue
        f0 = lookup(fut.get(c["symbol"], {}), entry)
        f1 = lookup(fut.get(c["symbol"], {}), exp)
        s0 = lookup(idx.get(c["symbol"], {}), entry)
        s1 = lookup(idx.get(c["symbol"], {}), exp)
        if None in (f0, f1, s0, s1):
            continue
        #: T comes from THIS contract's own expiry. Section 11.6: a
        #: maturity taken from the wrong contract multiplies every
        #: annualised figure by the ratio of the two.
        days = (exp - entry).days
        if days < 20:
            continue
        rally = 0.0
        for d, s in idx.get(c["symbol"], {}).items():
            if entry <= d <= exp and s0:
                rally = max(rally, (s - s0) / s0)
        cycles.append(dict(symbol=c["symbol"], entry=str(entry),
                           expiry=str(exp), days=days,
                           f0=f0, f1=f1, s0=s0, s1=s1, rally=rally))
    return cycles


def measure(cycles, rf, buffer_frac, tick_usd=TICK_USD):
    """Per-cycle realised return, net of cost, in excess of the T-bill."""
    import datetime as dt
    out = []
    for c in cycles:
        s0, s1, f0, f1 = c["s0"], c["s1"], c["f0"], c["f1"]
        gross = ((s1 - s0) + (f0 - f1)) / s0          # realised, per sec 6
        quoted = (f0 / s0 - 1.0)                      # what was advertised
        resid = (s1 - f1) / s0                        # convergence failure
        #: two futures legs per cycle, plus slippage a tick per leg
        cost = 2 * FEE_FUT + 2 * tick_usd / s0
        ann = 365.0 / c["days"]
        net_notional = (gross - cost) * ann
        #: Gate D: return is earned on notional, but capital committed is
        #: notional PLUS the buffer that keeps the short alive
        net_capital = net_notional / (1.0 + buffer_frac)
        d0 = dt.date.fromisoformat(c["entry"])
        d1 = dt.date.fromisoformat(c["expiry"])
        rates = [v for d, v in rf.items() if d0 <= d <= d1]
        rate = sum(rates) / len(rates) if rates else None
        out.append(dict(**c, quoted_ann=quoted * ann, gross_ann=gross * ann,
                        net_notional=net_notional, net_capital=net_capital,
                        resid=resid, rf=rate,
                        excess=(net_capital - rate) if rate is not None
                        else None))
    return out


def eras(rows, n=N_ERAS):
    """Three equal thirds of the window, by calendar time."""
    import datetime as dt
    if not rows:
        return []
    d0 = dt.date.fromisoformat(min(r["entry"] for r in rows))
    d1 = dt.date.fromisoformat(max(r["expiry"] for r in rows))
    span = (d1 - d0).days / n
    buckets = [[] for _ in range(n)]
    for r in rows:
        k = int((dt.date.fromisoformat(r["entry"]) - d0).days / span)
        buckets[min(k, n - 1)].append(r)
    return buckets


def weighted(rows, key):
    """Time-weighted mean, so a long cycle counts more than a short one."""
    vals = [(r[key], r["days"]) for r in rows if r.get(key) is not None]
    tot = sum(w for _, w in vals)
    return (sum(v * w for v, w in vals) / tot) if tot else None


def verdict(rows, spot_cost_ann):
    """Gates A-D exactly as frozen in section 8."""
    ex = weighted(rows, "excess")
    ex = (ex - spot_cost_ann) if ex is not None else None
    bys = eras(rows)
    era_ex = [weighted(b, "excess") for b in bys]
    era_ex = [(e - spot_cost_ann) if e is not None else None for e in era_ex]
    checks = [
        (f"Gate A  net excess over T-bill >= {GATE_A_EXCESS*100:.1f} pts",
         ex is not None and ex >= GATE_A_EXCESS,
         f"{ex*100:+.2f} pts" if ex is not None else "no rate"),
        ("Gate B  positive in EVERY era",
         all(e is not None and e > 0 for e in era_ex),
         "  ".join("n/a" if e is None else f"{e*100:+.1f}" for e in era_ex)),
        (f"Gate C  >= {MIN_CYCLES} cycles, >= {MIN_PER_ERA} per era",
         len(rows) >= MIN_CYCLES and all(len(b) >= MIN_PER_ERA for b in bys),
         f"{len(rows)} cycles, per era {[len(b) for b in bys]}"),
    ]
    return all(c[1] for c in checks), checks, ex, era_ex, bys


def report(rows, buffer_frac, worst_rally, spot_cost_ann, args):
    print(f"\n  {len(rows)} quarterly cycles  "
          f"{min(r['entry'] for r in rows)} -> "
          f"{max(r['expiry'] for r in rows)}")

    print(f"\n  GATE D FIRST -- the buffer, because Gate A is applied after "
          f"it")
    print(f"    worst observed intra-cycle spot rally  "
          f"{worst_rally*100:.1f}%")
    print(f"    buffer to keep the short alive          "
          f"{buffer_frac*100:.1f}% of notional")
    print(f"    so capital committed is                 "
          f"{(1+buffer_frac):.2f}x the traded notional")
    print(f"    every return below is on TOTAL capital, not on notional")

    print(f"\n  {'cycle':<12}{'days':>5}{'quoted':>9}{'realised':>10}"
          f"{'resid':>8}{'net cap':>9}{'T-bill':>8}{'excess':>9}")
    print("  " + "-" * 70)
    for r in rows:
        print(f"  {r['expiry']:<12}{r['days']:>5}"
              f"{r['quoted_ann']*100:>8.1f}%{r['gross_ann']*100:>9.1f}%"
              f"{r['resid']*100:>7.2f}%{r['net_capital']*100:>8.1f}%"
              + (f"{r['rf']*100:>7.2f}%{r['excess']*100:>8.1f}%"
                 if r["rf"] is not None else f"{'n/a':>7}{'n/a':>8}"))

    ok, checks, ex, era_ex, bys = verdict(rows, spot_cost_ann)
    mr = max(abs(r["resid"]) for r in rows)
    print(f"\n  CONVERGENCE -- section 6 asks what was realised, not quoted")
    print(f"    largest |index - future| at expiry: {mr*100:.2f}% of spot")
    if mr > 0.01:
        print("    NOTE: convergence is NOT clean. The locked-in basis was "
              "not fully")
        print("    realised, and the realised column is the one that counts.")

    print(f"\n  spot entry/exit charged once over the window: "
          f"{spot_cost_ann*100:.2f} pts/yr")
    print(f"\n  VERDICT -- gates frozen in PREREGISTRATION_v4 section 8")
    for name, good, detail in checks:
        print(f"    [{'PASS' if good else 'FAIL'}] {name:<46} {detail}")
    print(f"\n  {'PROCEED' if ok else 'REJECTED'}")
    if not ok:
        print("  Per section 9 this stops here. No basis-threshold filter,")
        print("  no reversed trade, no ETH rescue -- each of those is a")
        print("  sweep, and a sweep is how this becomes 2021.")
    return ok, ex, era_ex


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" +
              (f"   {detail}" if detail else ""))

    import datetime as dt
    print(f"kraken_basis.py v{VERSION} self-test\n")

    def cyc(expiry, days, basis, rally=0.0, resid=0.0, s0=50000.0):
        """A cycle with a KNOWN annualised basis planted in it."""
        f0 = s0 * (1 + basis * days / 365.0)
        s1 = s0 * 1.03
        f1 = s1 - resid * s0
        return dict(symbol="X", entry=str(dt.date.fromisoformat(expiry)
                                          - dt.timedelta(days=days)),
                    expiry=expiry, days=days, f0=f0, f1=f1, s0=s0, s1=s1,
                    rally=rally)

    print("the cash-and-carry identity")
    c = cyc("2023-03-31", 91, 0.10)
    m = measure([c], {}, 0.0)[0]
    check("perfect convergence returns the entry basis",
          abs(m["gross_ann"] - 0.10) < 1e-9, f"{m['gross_ann']*100:.3f}%")
    check("and the quoted basis agrees with it",
          abs(m["quoted_ann"] - 0.10) < 1e-9)
    #: convergence failure must show up in REALISED, not be assumed away
    c2 = cyc("2023-03-31", 91, 0.10, resid=0.01)
    m2 = measure([c2], {}, 0.0)[0]
    check("a 1% convergence failure moves realised, not quoted",
          abs(m2["quoted_ann"] - 0.10) < 1e-9
          and m2["gross_ann"] > m2["quoted_ann"],
          f"quoted {m2['quoted_ann']*100:.1f}% "
          f"realised {m2['gross_ann']*100:.1f}%")

    print("\nthe maturity comes from the contract's own expiry (sec 11.6)")
    short = measure([cyc("2023-03-31", 30, 0.10)], {}, 0.0)[0]
    long_ = measure([cyc("2023-03-31", 120, 0.10)], {}, 0.0)[0]
    check("same basis over 30 or 120 days annualises the same",
          abs(short["gross_ann"] - long_["gross_ann"]) < 1e-9,
          f"{short['gross_ann']*100:.2f}% vs {long_['gross_ann']*100:.2f}%")
    #: planted: the SAME prices annualised over the wrong maturity
    wrong = dict(cyc("2023-03-31", 91, 0.10))
    wrong["days"] = 30
    w = measure([wrong], {}, 0.0)[0]
    check("using a 30-day maturity on a 91-day contract inflates it ~3x",
          abs(w["gross_ann"] / short["gross_ann"] - 3.0) < 0.35,
          f"{w['gross_ann']*100:.1f}% vs a true {0.10*100:.0f}%")

    print("\nGate A, at the threshold and just under it (sec 11.1)")
    rf = {dt.date(2023, 1, 1) + dt.timedelta(days=k): 0.04
          for k in range(-2000, 2000)}
    #: 4% T-bill + 2.0 points + the exact cost load = a bare pass
    def suite(basis, n=15, rally=0.0):
        out = []
        for i in range(n):
            e = dt.date(2021, 12, 31) + dt.timedelta(days=91 * (i + 1))
            out.append(cyc(str(e), 91, basis, rally=rally))
        return measure(out, rf, 0.0)
    hi = suite(0.10)
    okA, ch, ex, _, _ = verdict(hi, 0.0)
    check("a 10% basis against a 4% bill clears Gate A", ch[0][1],
          f"{ex*100:+.2f} pts")
    lo = suite(0.055)
    okB, ch2, ex2, _, _ = verdict(lo, 0.0)
    check("a 5.5% basis against the same bill FAILS Gate A", not ch2[0][1],
          f"{ex2*100:+.2f} pts")

    print("\nGate B, positive overall but negative in one era (sec 11.2)")
    mixed = []
    for i in range(15):
        e = dt.date(2021, 12, 31) + dt.timedelta(days=91 * (i + 1))
        #: middle third deliberately below the bill
        b = 0.005 if 5 <= i < 10 else 0.16
        mixed.append(cyc(str(e), 91, b))
    mm = measure(mixed, rf, 0.0)
    okC, ch3, ex3, era_ex, _ = verdict(mm, 0.0)
    check("the full sample still clears Gate A", ch3[0][1],
          f"{ex3*100:+.2f} pts")
    check("but Gate B FAILS on the middle era", not ch3[1][1],
          "  ".join(f"{e*100:+.1f}" for e in era_ex))
    check("and that makes the whole verdict a rejection", not okC)

    print("\nGate C, and eras that are actually populated")
    thin = measure([cyc(str(dt.date(2022, 3, 31)
                            + dt.timedelta(days=91 * i)), 91, 0.10)
                    for i in range(11)], rf, 0.0)
    _, ch4, _, _, _ = verdict(thin, 0.0)
    check("11 cycles FAILS Gate C", not ch4[2][1], ch4[2][2])
    _, ch5, _, _, bys = verdict(hi, 0.0)
    check("15 cycles split 5/5/5 passes Gate C", ch5[2][1],
          f"{[len(b) for b in bys]}")

    print("\nGate D, a rally that exhausts the buffer (sec 11.4)")
    base = verdict(suite(0.10), 0.0)[2]
    with_buf = verdict(measure(
        [cyc(str(dt.date(2021, 12, 31) + dt.timedelta(days=91 * (i + 1))),
             91, 0.10) for i in range(15)], rf, 1.0), 0.0)[2]
    check("a buffer equal to notional HALVES the return on capital",
          abs((with_buf + 0.04) / (base + 0.04) - 0.5) < 0.02,
          f"{base*100:+.1f} -> {with_buf*100:+.1f} pts excess")
    okD, chD, exD, _, _ = verdict(measure(
        [cyc(str(dt.date(2021, 12, 31) + dt.timedelta(days=91 * (i + 1))),
             91, 0.10) for i in range(15)], rf, 1.5), 0.0)
    check("and a large enough buffer turns a Gate A pass into a FAIL",
          not chD[0][1], f"{exD*100:+.2f} pts")

    print("\nthe spot leg is charged, and it matters")
    _, ch6, ex6, _, _ = verdict(suite(0.075), 0.0)
    _, ch7, ex7, _, _ = verdict(suite(0.075), 0.0052 / 4.8)
    check("charging spot entry/exit lowers the excess", ex7 < ex6,
          f"{ex6*100:+.2f} -> {ex7*100:+.2f} pts")

    print("\nthe risk-free series is period-matched, not a constant")
    varying = {}
    for k in range(-2000, 2000):
        d = dt.date(2023, 1, 1) + dt.timedelta(days=k)
        varying[d] = 0.001 if d.year <= 2022 else 0.05
    v = measure([cyc("2022-03-31", 91, 0.10), cyc("2024-03-31", 91, 0.10)],
                varying, 0.0)
    check("two identical cycles get different benchmarks",
          abs(v[0]["rf"] - 0.001) < 1e-6 and abs(v[1]["rf"] - 0.05) < 1e-6,
          f"{v[0]['rf']*100:.1f}% vs {v[1]['rf']*100:.1f}%")
    check("so their excesses differ by the rate move",
          abs((v[0]["excess"] - v[1]["excess"]) - 0.049) < 1e-6)
    nod = measure([cyc("2019-01-31", 91, 0.10)], {}, 0.0)
    check("a cycle with no rate is n/a, not silently zero",
          nod[0]["excess"] is None and nod[0]["rf"] is None)

    print("\nthe rate series must COVER the cycles it benchmarks")
    full = {}
    for k in range(-100, 1900):
        d = dt.date(2021, 8, 1) + dt.timedelta(days=k)
        if d.weekday() < 5:
            full[d] = 0.04
    cov, good = rf_covers(full, "2021-08-27", "2026-06-26")
    check("a complete weekday series covers the window", good,
          f"{cov*100:.0f}%")
    #: planted: a series that starts two years late. Left unchecked it
    #: returns None for those cycles, they drop out of the weighted mean,
    #: and the sample silently re-selects itself on data availability.
    late = {d: v for d, v in full.items() if d >= dt.date(2023, 9, 1)}
    cov2, good2 = rf_covers(late, "2021-08-27", "2026-06-26")
    check("a series starting two years late is REFUSED", not good2,
          f"{cov2*100:.0f}%")
    cov3, good3 = rf_covers({}, "2021-08-27", "2026-06-26")
    check("an empty series is refused, not treated as zero", not good3)
    #: holidays must not sink an otherwise complete series
    holey = {d: v for i, (d, v) in enumerate(sorted(full.items()))
             if i % 25}
    check("a few percent of market holidays still passes",
          rf_covers(holey, "2021-08-27", "2026-06-26")[1],
          f"{rf_covers(holey, '2021-08-27', '2026-06-26')[0]*100:.0f}%")
    check("DGS3MO is preferred over the discount-basis DTB3",
          RF_SERIES[0] == "DGS3MO", " ".join(RF_SERIES))

    print("\ncycle construction holds the NEAREST contract only")
    cs = [dict(symbol="A", expiry="2022-03-25", first="2021-08-27"),
          dict(symbol="B", expiry="2022-06-24", first="2021-11-26"),
          dict(symbol="C", expiry="2022-09-30", first="2022-02-25")]
    px = {s["symbol"]: {dt.date(2021, 8, 27) + dt.timedelta(days=k): 50000.0
                        for k in range(500)} for s in cs}
    built = build_cycles(cs, px, px)
    check("one cycle per contract", len(built) == 3, f"{len(built)}")
    check("cycles do not overlap",
          all(built[i]["expiry"] <= built[i + 1]["entry"]
              for i in range(len(built) - 1)),
          " ".join(f"{b['entry']}..{b['expiry']}" for b in built))
    check("a held cycle is about a quarter, not the 7-month listed life",
          all(60 <= b["days"] <= 130 for b in built[1:]),
          f"{[b['days'] for b in built]}")

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="../data/kraken_manifest.json")
    ap.add_argument("--rf-csv", default="")
    ap.add_argument("--buffer", type=float, default=None,
                    help="override the collateral buffer (v7 phase 1)")
    ap.add_argument("--pause", type=float, default=0.3)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"kraken_basis.py v{VERSION}   PREREGISTRATION_v4, ONE RUN\n")
    man = json.load(open(os.path.expanduser(a.manifest)))
    if not man.get("proceed"):
        raise SystemExit("  STOP: the manifest says Phase 0 did not pass.")
    use = man["usable"]
    print(f"  {len(use)} usable contracts  {man['window_first']} -> "
          f"{man['window_last']}")

    print("\n  PULLING")
    fut, idx = {}, {}
    for c in use:
        fut[c["symbol"]] = candles(c["symbol"], "trade")
        time.sleep(a.pause)
        idx[c["symbol"]] = candles(c["symbol"], "spot")
        time.sleep(a.pause)
        print(f"    {c['symbol']:<20} {len(fut[c['symbol']]):>4} future  "
              f"{len(idx[c['symbol']]):>4} index")

    print("\n  RISK-FREE")
    rf = risk_free(man["window_first"], man["window_last"],
                   a.rf_csv or None)

    cycles = build_cycles(use, fut, idx)
    if len(cycles) < MIN_CYCLES:
        raise SystemExit(f"\n  STOP: only {len(cycles)} cycles could be "
                         f"built, Gate C needs {MIN_CYCLES}.")
    worst = max(c["rally"] for c in cycles)
    #: PREREGISTRATION_v7 section 5. The buffer -- and ONLY the buffer --
    #: may be overridden, from a haircut that kraken_collateral.py read
    #: off the venue's own terms. The per-cycle returns, the window, the
    #: costs and the gates are untouched, so this re-divides an existing
    #: measurement rather than making a new one.
    buffer_frac = worst if a.buffer is None else a.buffer
    if a.buffer is not None:
        print(f"\n  BUFFER OVERRIDE  {a.buffer*100:.1f}% of notional "
              f"(v4 computed {worst*100:.1f}% from the worst rally)")
        print("  Returns, window, costs and gates are unchanged -- "
              "PREREGISTRATION_v7 section 5.")
    rows = measure(cycles, rf, buffer_frac)
    #: spot entry and exit, charged ONCE across the whole window
    import datetime as dt
    span = (dt.date.fromisoformat(max(r["expiry"] for r in rows))
            - dt.date.fromisoformat(min(r["entry"] for r in rows))).days
    spot_cost_ann = (2 * FEE_SPOT) / (span / 365.0) / (1.0 + buffer_frac)
    report(rows, buffer_frac, worst, spot_cost_ann, a)


if __name__ == "__main__":
    main()
