#!/usr/bin/env python3
"""PREREGISTRATION_v46 -- turn of the month (TOM), SPX500 / NAS100 / UK100.

Interpretations fixed here, BEFORE the run (the pre-reg leaves them open):
 * Trading days come from each instrument's own session list (days with the
   cash-close bar: US 15:55 bar, UK 16:25 bar). Day -1 = last session of month.
 * TOM = close of day -2 -> close of day +3 (sessions -1, +1, +2, +3).
 * Reference = all remaining sessions between consecutive TOM windows, cut
   into non-overlapping 4-session blocks from the start of each gap
   (leftover <4 sessions dropped). Etula window is part of the reference.
 * Cost per TOM trade = quoted spread at the entry close bar (ask_c/bid_c-1)
   + financing (DGS3MO + 2.5%)/365 per calendar night held (Fri->Mon = 3).
   Dates before 2013-01-01, or spread <= 0, use that instrument's 2013 median.
   DGS3MO is applied to UK100 too, as written (blind spot: not SONIA).
 * G1 (literal, stricter reading): TOM NET minus reference GROSS mean, pooled,
   OLS dummy, SEs clustered by calendar month of the window's end/turn.
   Net-vs-net difference is REPORTED, not gated.
 * G2: pooled TOM net mean > 0 in 2005-12, 2013-19, 2020-26 (year of day -1).
 * G3: equal-weight portfolio of available indices' TOM net per month (0 if
   none), Sharpe = mean/sd * sqrt(12) >= 0.46.
 * Reported: per index; Etula pre-turn = close day -7 -> close day -3 (gross).
I am not a financial adviser. This is a measurement, not a recommendation."""
import csv, datetime as dt, hashlib, math, sys
import numpy as np
import reactive, noise_v38
from premarket_factor import regress, tstat

VERSION = "1.0"
DOC = ("PREREGISTRATION_v46.md", "86d564dc80bcd5dcf2eb0b338285c9b64c78f37b39abe7bd4995ac2e3f49aba9")
START = dt.date(2005, 1, 1)
ERAS = ((2005, 2012), (2013, 2019), (2020, 2026))
INS = (("spx500usd", "../data", "15:55", reactive.load),
       ("nas100usd", "../data", "15:55", reactive.load),
       ("uk100gbp", "../data/v38", "16:25", noise_v38.load))


def rates():
    d, r = [], []
    for row in csv.DictReader(open("../data/DGS3MO.csv")):
        try:
            v = float(row["DGS3MO"])
        except ValueError:
            continue
        d.append(dt.date.fromisoformat(row["observation_date"])); r.append(v)
    return d, r


def rate_on(RT, day):
    import bisect
    i = bisect.bisect_right(RT[0], day) - 1
    return RT[1][max(i, 0)]


def build(ins, ddir, bar, loader, RT):
    days = loader(ddir, ins)
    ses = sorted(d for d in days if bar in days[d] and d >= START)
    close = [days[d][bar][3] for d in ses]
    spr = [(days[d][bar][7] / days[d][bar][6] - 1) * 1e4 for d in ses]
    s13 = [s for d, s in zip(ses, spr) if d.year == 2013 and s > 0]
    med13 = float(np.median(s13))
    spr = [med13 if (d < dt.date(2013, 1, 1) or s <= 0) else s for d, s in zip(ses, spr)]
    last = [i for i in range(len(ses) - 1) if ses[i + 1].month != ses[i].month]   # day -1 indices
    def ret(a, b): return (close[b] / close[a] - 1) * 1e4
    def fin(a, b):
        n = (ses[b] - ses[a]).days
        return n * (rate_on(RT, ses[a]) + 2.5) / 100 / 365 * 1e4
    tom, ref, etula = [], [], []
    for L in last:
        a, b = L - 1, L + 3
        if a < 0 or b >= len(ses):
            continue
        g = ret(a, b)
        tom.append(dict(ins=ins, d=ses[L], a=a, b=b, g=g, cost=spr[a] + fin(a, b), net=g - spr[a] - fin(a, b),
                        cl=ses[L].strftime("%Y-%m")))
        if L - 7 >= 0:
            etula.append(dict(ins=ins, d=ses[L], g=ret(L - 6, L - 2), net=ret(L - 6, L - 2) - spr[L - 6] - fin(L - 6, L - 2)))
    for x, y in zip(tom, tom[1:]):
        i = x["b"]
        while i + 4 <= y["a"]:
            ref.append(dict(ins=ins, d=ses[i + 4], g=ret(i, i + 4), net=ret(i, i + 4) - spr[i] - fin(i, i + 4),
                            cl=ses[i + 4].strftime("%Y-%m")))
            i += 4
    return tom, ref, etula, med13, ses[0], ses[-1]


def gates(T, R, verbose=True):
    y = np.array([t["net"] for t in T] + [r["g"] for r in R])
    X = np.column_stack([np.ones(len(y)), [1.0] * len(T) + [0.0] * len(R)])
    b, V = regress(y, X, [t["cl"] for t in T] + [r["cl"] for r in R]); t1 = tstat(b, V, 1)
    g1 = b[1] > 0 and t1 >= 2.0
    eras = []
    for lo, hi in ERAS:
        v = [t["net"] for t in T if lo <= t["d"].year <= hi]
        eras.append((np.mean(v), len(v)))
    g2 = all(e[0] > 0 for e in eras)
    months = {}
    for t in T:
        months.setdefault(t["cl"], []).append(t["net"])
    lo_m = min(months); hi_m = max(months)
    y0, m0 = map(int, lo_m.split("-")); ser = []
    while f"{y0:04d}-{m0:02d}" <= hi_m:
        k = f"{y0:04d}-{m0:02d}"; ser.append(np.mean(months[k]) if k in months else 0.0)
        m0 += 1
        if m0 == 13: y0, m0 = y0 + 1, 1
    ser = np.array(ser) / 1e4
    sh = ser.mean() / ser.std(ddof=1) * math.sqrt(12)
    g3 = sh >= 0.46
    return dict(b=b[1], t=t1, g1=g1, eras=eras, g2=g2, sh=sh, g3=g3, n_m=len(ser))


def self_test(T, R):
    import copy
    up = copy.deepcopy(T)
    for t in up: t["net"] += 150.0
    flat = copy.deepcopy(T); mref = np.mean([r["g"] for r in R])
    for t in flat: t["net"] = mref - t["cost"]
    ok = gates(up, R)["g1"] and not gates(flat, R)["g1"]
    print(f"  self-test: planted +150 bp -> G1 PASS expected; planted zero-edge -> G1 FAIL expected: {'OK' if ok else 'BROKEN'}")
    return ok


def main():
    if hashlib.sha256(open("../" + DOC[0], "rb").read()).hexdigest() != DOC[1]:
        sys.exit("PREREGISTRATION_v46.md changed -- refused")
    print(f"tom_v46.py v{VERSION}   PREREGISTRATION_v46 (sha {DOC[1][:8]}… matches)\n"
          "  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    RT = rates(); T, R, E = [], [], []
    for ins, ddir, bar, ld in INS:
        t, r, e, m13, s0, s1 = build(ins, ddir, bar, ld, RT)
        T += t; R += r; E += e
        print(f"  {ins:<9} sessions {s0}..{s1}  TOM windows {len(t)}  reference blocks {len(r)}  2013 median spread {m13:.2f} bp")
    if not self_test(T, R):
        sys.exit("self-test broken -- no verdict")
    G = gates(T, R)
    mg = np.mean([t['g'] for t in T]); mn = np.mean([t['net'] for t in T]); mc = np.mean([t['cost'] for t in T])
    mr = np.mean([r['g'] for r in R]); mrn = np.mean([r['net'] for r in R])
    print(f"\n  pooled: TOM gross {mg:+.1f} bp, cost {mc:.1f} bp, net {mn:+.1f} bp;  reference gross {mr:+.1f} bp (net {mrn:+.1f})")
    print(f"  G1 TOM net - reference gross {G['b']:+.1f} bp  t {G['t']:+.2f}  -> {'PASS' if G['g1'] else 'FAIL'}")
    print("  G2 TOM net by era " + "  ".join(f"{lo}-{hi % 100:02d} {m:+.1f} (n {n})" for (lo, hi), (m, n) in zip(ERAS, G['eras']))
          + f"  -> {'PASS' if G['g2'] else 'FAIL'}")
    print(f"  G3 TOM-only Sharpe {G['sh']:.2f} over {G['n_m']} months (bar 0.46)  -> {'PASS' if G['g3'] else 'FAIL'}")
    # reported
    y = np.array([t["net"] for t in T] + [r["net"] for r in R])
    X = np.column_stack([np.ones(len(y)), [1.0] * len(T) + [0.0] * len(R)])
    b, V = regress(y, X, [t["cl"] for t in T] + [r["cl"] for r in R])
    print(f"\n    reported: net-vs-net difference {b[1]:+.1f} bp  t {tstat(b, V, 1):+.2f}")
    print(f"    reported: gross-vs-gross difference {mg - mr:+.1f} bp")
    for ins, *_ in INS:
        tt = [t for t in T if t["ins"] == ins]; rr = [r for r in R if r["ins"] == ins]
        ee = [e for e in E if e["ins"] == ins]
        print(f"    reported: {ins:<9} TOM gross {np.mean([t['g'] for t in tt]):+6.1f}  net {np.mean([t['net'] for t in tt]):+6.1f}"
              f"  ref gross {np.mean([r['g'] for r in rr]):+5.1f}   Etula -6..-3 gross {np.mean([e['g'] for e in ee]):+5.1f}"
              + "   eras net " + " ".join(f"{np.mean([t['net'] for t in tt if lo <= t['d'].year <= hi]):+6.1f}" for lo, hi in ERAS))
    print(f"    reported: Etula -6..-3 pooled gross {np.mean([e['g'] for e in E]):+.1f} bp vs reference {mr:+.1f}  (eras "
          + " ".join(f"{np.mean([e['g'] for e in E if lo <= e['d'].year <= hi]):+.1f}" for lo, hi in ERAS) + ")")
    with open("../data/tom_v46_trades.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["ins", "turn_day", "gross_bp", "cost_bp", "net_bp"])
        for t in T: w.writerow([t["ins"], t["d"], f"{t['g']:.2f}", f"{t['cost']:.2f}", f"{t['net']:.2f}"])
    print(f"\n  VERDICTS  G1 {'PASS' if G['g1'] else 'FAIL'}   G2 {'PASS' if G['g2'] else 'FAIL'}   G3 {'PASS' if G['g3'] else 'FAIL'}"
          f"   -> overall {'PASS' if G['g1'] and G['g2'] and G['g3'] else 'FAIL'}")


if __name__ == "__main__":
    main()
