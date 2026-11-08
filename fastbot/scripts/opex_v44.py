#!/usr/bin/env python3
"""PREREGISTRATION_v44 -- options-expiry week (IN) and the week after (OUT).
H1 direction (OUT vs other weeks), H2 volatility log(RV_OUT/RV_IN).
SPX500, NAS100 OANDA 5m; 2011-05 -> 2026-08-14; GEX prior-day for reporting.
Interpretation fixed here, before the run: H1 passes only if
(mean OUT - mean reference) < 0 with t <= -2.24 AND a short over OUT is net
positive after one round-trip quoted spread."""
import csv, datetime as dt, hashlib, math, os, sys, bisect
import numpy as np
from reactive import load
from premarket_factor import regress, tstat

VERSION = "1.0"
DOC = ("PREREGISTRATION_v44.md", "7917ad0e7892da64df1c7d57f7e9051f1fa41f236b5cec9e250bb9fdc4189ab0")
START, END = dt.date(2011, 5, 2), dt.date(2026, 8, 14)
ERAS = ((2011, 2016), (2017, 2021), (2022, 2026))
T = 2.24


def third_friday(y, m):
    d = dt.date(y, m, 15); return d + dt.timedelta(days=(4 - d.weekday()) % 7)


def expiries(sessions):
    s = set(sessions); out = []
    for y in range(2011, 2027):
        for m in range(1, 13):
            f = third_friday(y, m)
            for back in range(0, 3):
                c = f - dt.timedelta(days=back)
                if c in s:
                    out.append(c); break
    return sorted(e for e in out if START <= e <= END)


def per_instrument(ins):
    days = load("../data", ins)
    ses = sorted(d for d in days if "15:55" in days[d] and START - dt.timedelta(days=15) <= d <= END + dt.timedelta(days=15))
    idx = {d: i for i, d in enumerate(ses)}
    close = [days[d]["15:55"][3] for d in ses]
    spr = [(days[d]["15:55"][7] / days[d]["15:55"][6] - 1) * 1e4 for d in ses]
    def rv(d):
        b = days[d]; ks = sorted(b); c = [b[k][3] for k in ks]
        return float(np.sum(np.diff(np.log(c)) ** 2))
    RV = [rv(d) for d in ses]
    ex = [e for e in expiries(ses) if e in idx and idx[e] >= 5 and idx[e] + 5 < len(ses)]
    cyc = []
    for e in ex:
        i = idx[e]
        cyc.append(dict(ins=ins, exp=e,
                        IN=(close[i] / close[i - 5] - 1) * 1e4, OUT=(close[i + 5] / close[i] - 1) * 1e4,
                        spread=spr[i], rvin=math.sqrt(sum(RV[i - 4:i + 1])), rvout=math.sqrt(sum(RV[i + 1:i + 6]))))
    blocked = set()
    for e in ex:
        i = idx[e]; blocked |= set(range(i - 5, i + 6))
    ref = []
    fr = [i for i, d in enumerate(ses) if d.weekday() == 4 and i >= 5 and START <= ses[i] <= END]
    for i in fr:
        w = set(range(i - 5, i + 1))
        if ses[i - 4].weekday() != 0 or w & blocked:     # a clean Mon..Fri week, no overlap with IN/OUT
            continue
        ref.append(dict(ins=ins, date=ses[i], R=(close[i] / close[i - 5] - 1) * 1e4))
    return cyc, ref


def gex_prior(d):
    ds, gs = [], []
    for r in csv.DictReader(open("../data/gex/DIX.csv")):
        ds.append(dt.date.fromisoformat(r["date"])); gs.append(float(r["gex"]))
    i = bisect.bisect_left(ds, d) - 1
    return gs[i] if i >= 0 else None


def main():
    if hashlib.sha256(open("../" + DOC[0], "rb").read()).hexdigest() != DOC[1]:
        sys.exit("PREREGISTRATION_v44.md changed -- refused")
    print(f"opex_v44.py v{VERSION}   PREREGISTRATION_v44 (sha {DOC[1][:8]}… matches)\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    C, R = [], []
    for ins in ("spx500usd", "nas100usd"):
        c, r = per_instrument(ins); C += c; R += r
        print(f"  {ins}: {len(c)} expiry cycles, {len(r)} clean reference weeks")
    # H1
    y = np.array([c["OUT"] for c in C] + [r["R"] for r in R])
    X = np.column_stack([np.ones(len(y)), [1.0] * len(C) + [0.0] * len(R)])
    cl = [c["exp"].isoformat() for c in C] + [r["date"].isoformat() for r in R]
    b, V = regress(y, X, cl); t1 = tstat(b, V, 1)
    short_net = np.array([-c["OUT"] - c["spread"] for c in C])
    h1 = b[1] < 0 and t1 <= -T and short_net.mean() > 0
    print(f"\n  H1 direction: OUT mean {np.mean([c['OUT'] for c in C]):+.1f} bp vs reference {np.mean([r['R'] for r in R]):+.1f} bp;"
          f" difference {b[1]:+.1f} bp  t {t1:+.2f};  short-OUT net {short_net.mean():+.1f} bp  -> {'PASS' if h1 else 'FAIL'}")
    # H2
    lr = np.array([math.log(c["rvout"] / c["rvin"]) for c in C]); cc = [c["exp"].isoformat() for c in C]
    b2, V2 = regress(lr, np.ones((len(lr), 1)), cc); t2 = tstat(b2, V2, 0)
    eras = [lr[[lo <= c["exp"].year <= hi for c in C]].mean() for lo, hi in ERAS]
    h2 = b2[0] > 0 and t2 >= T and all(e > 0 for e in eras)
    print(f"  H2 volatility: mean log(RV_OUT/RV_IN) {b2[0]:+.3f} (x{math.exp(b2[0]):.2f})  t {t2:+.2f}   eras "
          + " ".join(f"{e:+.3f}" for e in eras) + f"  -> {'PASS' if h2 else 'FAIL'}")
    # reported
    g = np.array([gex_prior(c["exp"]) for c in C], float)
    q1, q2 = np.nanquantile(g, [1 / 3, 2 / 3])
    for nm, m in (("low GEX", g <= q1), ("mid GEX", (g > q1) & (g <= q2)), ("high GEX", g > q2)):
        print(f"    reported: {nm:<8} H2 {lr[m].mean():+.3f} (n {m.sum()})   OUT {np.array([c['OUT'] for c in C])[m].mean():+.1f} bp")
    for ins in ("spx500usd", "nas100usd"):
        m = np.array([c["ins"] == ins for c in C])
        print(f"    reported: {ins:<9} OUT {np.array([c['OUT'] for c in C])[m].mean():+.1f} bp   IN {np.array([c['IN'] for c in C])[m].mean():+.1f} bp   H2 {lr[m].mean():+.3f}")
    print(f"\n  VERDICTS  H1 {'PASS' if h1 else 'FAIL'}   H2 {'PASS' if h2 else 'FAIL'}")


if __name__ == "__main__":
    main()
