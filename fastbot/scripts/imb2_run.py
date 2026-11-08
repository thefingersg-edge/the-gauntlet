#!/usr/bin/env python3
"""IMB2 analysis (PREREGISTRATION_IMB2.md): what is left of the 15:50 imbalance move after a realistic reaction delay?
python3 imb2_run.py   -> data/imb1/run_imb2.log
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, math, hashlib
from collections import defaultdict
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "..", "data", "imb1")
PIN = {os.path.join(HERE, "..", "PREREGISTRATION_IMB2.md"): "e6344bc1124aca1e81547c4176644071ca9fc8b5098e1743a2efd04fdb5aad80"}
DELAYS = [0, 50, 100, 250, 500, 1000, 2000, 5000]; PRIMARY = 1000
OFFS = [0, 50, 100, 250, 500, 1000, 2000, 5000, 15000, 60000]
ERAS = (("2019-01-01", "2020-12-31"), ("2021-01-01", "2023-12-31"), ("2024-01-01", "2026-12-31"))
COMM_SH = 0.0035; MES_FEE = 1.80


def pin():
    for f, h in PIN.items():
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} changed -- refused")


def zser(dates, S):
    z = {}
    for i in range(250, len(dates)):
        w = np.array(S[i - 250:i]); sd = w.std(ddof=1)
        if sd > 0: z[dates[i]] = (S[i] - w.mean()) / sd
    return z


def tmean(a):
    a = np.asarray(a, float)
    return (a.mean(), a.mean() / (a.std(ddof=1) / math.sqrt(len(a))), len(a)) if len(a) > 2 else (float("nan"), float("nan"), len(a))


def main():
    pin(); L = ["IMB2 -- what is left after a reaction delay (PREREGISTRATION_IMB2.md sha e6344bc1…)",
                "  I am not a financial adviser. This is a measurement, not a recommendation.", ""]
    # first message per (date, venue, symbol) with its arrival offset in ms after 15:50:00.000
    first = {}
    with open(os.path.join(D, "imb2_msgs.csv")) as fh:
        for r in csv.DictReader(fh):
            k = (r["date"], r["venue"], r["symbol"]); ms = float(r["ms"])
            if k not in first or ms < first[k][0]:
                sg = 1 if r["side"] == "B" else (-1 if r["side"] in ("A", "S") else 0)
                first[k] = (ms, sg * float(r["imb_qty"]) * float(r["ref_price"]), float(r["paired_qty"]) * float(r["ref_price"]))
    byday = defaultdict(list)
    for (d, _, _), v in first.items(): byday[d].append(v)
    dates = sorted(byday)
    arr = np.array([v[0] for d in dates for v in byday[d]])
    dollars = defaultdict(float); tot = 0.0
    for d in dates:
        for ms, s, p in byday[d]:
            tot += abs(s)
            for c in (0, 50, 100, 250, 500, 1000, 5000):
                if ms <= c: dollars[c] += abs(s)
    L.append(f"  {len(dates)} days, {len(arr):,} first messages; arrival ms after 15:50:00 -- p10 {np.percentile(arr, 10):.1f}, median {np.median(arr):.1f}, p90 {np.percentile(arr, 90):.1f}, p99 {np.percentile(arr, 99):.1f}")
    L.append("  share of imbalance $ arrived by: " + "  ".join(f"{c} ms {dollars[c] / tot:.0%}" for c in (0, 50, 100, 250, 500, 1000, 5000)) + "\n")
    # signals
    Z = {}
    for Lm in DELAYS:
        S, dd = [], []
        for d in dates:
            num = sum(s for ms, s, p in byday[d] if ms <= Lm); den = sum(p for ms, s, p in byday[d] if ms <= Lm)
            if den > 0: S.append(num / den); dd.append(d)
        Z[Lm] = zser(dd, S)
    # prices
    PX = {}
    with open(os.path.join(D, "imb2_px.csv")) as fh:
        for r in csv.DictReader(fh):
            q = {}
            for o in OFFS:
                try: q[o] = (float(r[f"b{o}"]), float(r[f"a{o}"]))
                except (ValueError, KeyError): q[o] = None
            PX[(r["date"], r["inst"])] = q

    def trades(Lm, inst, exit_o):
        rows = []
        for d, z in Z[Lm].items():
            if abs(z) < 1: continue
            q = PX.get((d, inst))
            if not q or q.get(Lm) is None or q.get(exit_o) is None: continue
            (b0, a0), (b1, a1) = q[Lm], q[exit_o]
            if min(b0, a0, b1, a1) <= 0 or a0 < b0 or a1 < b1: continue
            s = 1 if z > 0 else -1
            g = (b1 / a0 - 1) * 1e4 if s > 0 else (b0 / a1 - 1) * 1e4     # crosses the spread both ways
            mid0 = (b0 + a0) / 2
            fee = (2 * COMM_SH / mid0 * 1e4) if inst == "SPY" else (2 * MES_FEE / (5 * mid0) * 1e4)
            rows.append((d, g - fee, s * (((b1 + a1) / 2) / mid0 - 1) * 1e4))
        return rows

    L.append(f"  {'delay':>7}  {'SPY net bp (t, n) exit 15:51':>32}  {'mid move':>9}  {'exit 15:50:15':>18}  {'E-mini (MES fees) net':>24}")
    for Lm in DELAYS:
        r = trades(Lm, "SPY", 60000); m, t, n = tmean([x[1] for x in r]); mm = tmean([x[2] for x in r])[0]
        r15 = trades(Lm, "SPY", 15000); m15, t15, _ = tmean([x[1] for x in r15])
        re = trades(Lm, "ES", 60000); me, te, ne = tmean([x[1] for x in re])
        L.append(f"  {Lm:>5} ms  {m:+8.2f} (t {t:+5.2f}, n {n:4d})        {mm:+8.2f}   {m15:+7.2f} (t {t15:+5.2f})   {me:+7.2f} (t {te:+5.2f}, n {ne})"
                 + ("   <- PRIMARY" if Lm == PRIMARY else ""))
    # mid path for the primary signal
    days1 = [d for d, z in Z[PRIMARY].items() if abs(z) >= 1 and PX.get((d, "SPY"))]
    L.append("\n  SPY mid move from 15:50:00.000 on |z_1s| >= 1 days, signed by z (bp):  " + "  ".join(
        f"{o}ms {np.nanmean([np.sign(Z[PRIMARY][d]) * ((sum(PX[(d, 'SPY')][o]) / 2) / (sum(PX[(d, 'SPY')][0]) / 2) - 1) * 1e4 for d in days1 if PX[(d, 'SPY')][o] and PX[(d, 'SPY')][0]]):+.2f}"
        for o in OFFS))
    # gates
    r = trades(PRIMARY, "SPY", 60000); m, t, n = tmean([x[1] for x in r])
    era = [tmean([x[1] for x in r if a <= x[0] <= b])[0] for a, b in ERAS]
    g1 = m > 0 and t >= 2.0; g2 = all(e > 0 for e in era)
    L.append(f"\n  PRIMARY (L = 1 s, SPY, exit 15:51): net {m:+.2f} bp (t {t:+.2f}, n {n});  eras " + " / ".join(f"{e:+.2f}" for e in era))
    L.append(f"  G1 {'PASS' if g1 else 'FAIL'}   G2 {'PASS' if g2 else 'FAIL'}   -> {'PASS' if g1 and g2 else 'FAIL'}")
    open(os.path.join(D, "run_imb2.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
