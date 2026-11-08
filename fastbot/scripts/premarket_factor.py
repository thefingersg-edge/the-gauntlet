#!/usr/bin/env python3
"""PREREGISTRATION_v28 (amended by v28.1) -- which PART of the release
move comes back?

Six instruments react to the same release on the same morning. Split
each instrument's 08:30 bar move into the part the pack shared and the
part it made alone, and ask which part the next hour hands back.

    bE > 0, bC ~ 0   the fade is paid for ABSORPTION
    bC > 0, bE ~ 0   the fade is paid for the market MISREADING the data

Both registrations are pinned by sha256 and checked at run time. No
loadings are fitted; the pack is a median of the other three equity
indices, fixed in section 2 of the document.

    python3 premarket_factor.py --self-test
    python3 premarket_factor.py --data-dir ../data/v24
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import math
import os
import re
import statistics as st
import sys
from zoneinfo import ZoneInfo

import numpy as np

from premarket_event import load_events

VERSION = "1.0"
DOCS = (("PREREGISTRATION_v28.md",
         "ec0c61390151e950da1f2ef17258ae48"
         "b94401679c81eccfe0a96a92cf6dbe15"),
        ("PREREGISTRATION_v28.1.md",
         "b003eed58377c45cf23958dfe0a9dab7"
         "e0a3ff61aba64d7740059ddd061904d8"))

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
EQUITY = ("SPX500_USD", "NAS100_USD", "US30_USD", "DE30_EUR")   # section 2
OTHER = ("EUR_USD", "XAU_USD")                                  # reported
SIG, ENTRY, H0, CLOSE = "08:30", "08:45", "09:45", "15:45"
WANT_ET = (SIG, ENTRY, H0, CLOSE)
KEEP_UTC = {"12:30", "13:30", "12:45", "13:45", "14:45", "19:45", "20:45"}
FORWARD_START = dt.date(2026, 9, 18)
VOL_WINDOW = 24                      # section 2: prior events only
T_GATE = 2.24                        # section 4, Bonferroni for two
V27_FILE = "../data/horizon_v27_trades.csv"      # Gate 0, v28.1

_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)


def _guard(names):
    bad = sorted(n for n in names if _FORBIDDEN.search(n))
    if bad:
        raise SystemExit(f"namespace guard: this file must not define {bad}")


def stem(instrument):
    return instrument.replace("_", "").lower()


def read_marks(path):
    out = {}
    with open(path, newline="") as fh:
        rd = csv.reader(fh)
        head = next(rd)
        ix = [head.index(k) for k in ("time", "open", "high", "low", "close")]
        for row in rd:
            s = row[ix[0]]
            if s[11:16] not in KEEP_UTC:
                continue
            e = dt.datetime.fromisoformat(s).replace(tzinfo=UTC).astimezone(ET)
            hm = e.strftime("%H:%M")
            if hm in WANT_ET:
                out[(e.date(), hm)] = tuple(float(row[i]) for i in ix[1:])
    return out


def morning(b, a, d):
    """(move bp, fade P&L at 09:45, at 15:45) for one morning, or None."""
    if any((d, hm) not in b or (d, hm) not in a for hm in WANT_ET):
        return None
    o = (b[(d, SIG)][0] + a[(d, SIG)][0]) / 2.0
    c = (b[(d, SIG)][3] + a[(d, SIG)][3]) / 2.0
    if c == o or o <= 0:
        return None
    m = (c / o - 1.0) * 1e4
    direction = -1 if c > o else 1
    me = (b[(d, ENTRY)][0] + a[(d, ENTRY)][0]) / 2.0
    if me <= 0:
        return None
    out = [m]
    for hm in (H0, CLOSE):
        mx = (b[(d, hm)][0] + a[(d, hm)][0]) / 2.0
        out.append(direction * (mx / me - 1.0) * 1e4)
    return tuple(out)


def trailing_sigma(moves):
    """sigma for each event from the PRIOR VOL_WINDOW moves only.

    A window that includes the morning being measured is look-ahead, and
    it would flatter exactly the coefficient this run is about
    (v28 section 7).
    """
    out = []
    for i, _ in enumerate(moves):
        prior = moves[max(0, i - VOL_WINDOW):i]
        out.append(st.stdev(prior) if len(prior) >= VOL_WINDOW else None)
    return out


def decompose(m_i, sigma_i, z_others):
    """(C, E) -- the pack's share of this move, and this instrument's own."""
    med = st.median(z_others)
    c = sigma_i * med
    e = m_i - c
    sgn = 1.0 if m_i > 0 else -1.0
    return c * sgn, e * sgn


def regress(y, X, clusters):
    """OLS with a cluster-robust covariance matrix."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    xtx_inv = np.linalg.inv(X.T @ X)
    beta = xtx_inv @ (X.T @ y)
    u = y - X @ beta
    groups = {}
    for i, g in enumerate(clusters):
        groups.setdefault(g, []).append(i)
    meat = np.zeros((X.shape[1], X.shape[1]))
    for rows in groups.values():
        s = X[rows].T @ u[rows]
        meat += np.outer(s, s)
    n, k = X.shape
    G = len(groups)
    V = xtx_inv @ meat @ xtx_inv * (G / (G - 1)) * ((n - 1) / (n - k))
    return beta, V


def contrast(beta, V, a=(0.0, -1.0, 1.0)):
    a = np.asarray(a, float)
    est = float(a @ beta)
    se = float(math.sqrt(a @ V @ a))
    return est, (None if se == 0 else est / se)


def tstat(beta, V, j):
    se = math.sqrt(V[j, j])
    return None if se == 0 else beta[j] / se


def fmt(x, w=6, p=3):
    return " " * w if x is None else f"{x:+{w}.{p}f}"


_guard(list(globals()))


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int, np.bool_)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"premarket_factor.py v{VERSION} self-test\n")

    print("the decomposition is an identity, and the pack is a median")
    C, E = decompose(10.0, 5.0, [1.0, 2.0, 3.0])
    check("C + E = |m|, always", abs((C + E) - 10.0) < 1e-12,
          f"C {C:+.2f}  E {E:+.2f}")
    check("the pack is the MEDIAN of the others, not the mean",
          abs(C - 5.0 * 2.0) < 1e-12, "median(1,2,3) = 2, x sigma 5 = 10")
    #: PLANTED: a move AGAINST the pack must give a NEGATIVE C and an E
    #: bigger than the move itself. A file that takes absolute values
    #: here would hide exactly the case the test is about.
    C2, E2 = decompose(-10.0, 5.0, [1.0, 2.0, 3.0])
    check("a move against the pack gives C < 0 and E > |m|",
          C2 < 0 < 10.0 < E2 and abs((C2 + E2) - 10.0) < 1e-12,
          f"C {C2:+.2f}  E {E2:+.2f}")

    print("\nsigma looks BACKWARDS only")
    moves = [1.0] * VOL_WINDOW + [100.0, 1.0]
    sig = trailing_sigma(moves)
    check("the first 24 events have no sigma and are dropped",
          all(s is None for s in sig[:VOL_WINDOW]) and sig[VOL_WINDOW] is not None)
    check("a flat history gives sigma 0 before the shock arrives",
          abs(sig[VOL_WINDOW]) < 1e-12, f"{sig[VOL_WINDOW]}")
    #: PLANTED: the 100 must not be inside its own sigma. If it were,
    #: the huge move would be scaled down by itself.
    check("the shock is NOT in its own window, but is in the next one",
          sig[VOL_WINDOW + 1] > 1.0, f"{sig[VOL_WINDOW + 1]:.2f}")

    print("\nthe regression, on planted data")
    rng = np.random.default_rng(4)
    n, G = 2000, 400
    cl = [i % G for i in range(n)]
    c_x = rng.normal(0, 1, n)
    e_x = rng.normal(0, 1, n)
    #: PLANTED: only the IDIOSYNCRATIC part predicts the reversion.
    y = 0.5 * e_x + rng.normal(0, 1, n)
    X = np.column_stack([np.ones(n), c_x, e_x])
    beta, V = regress(y, X, cl)
    est, t = contrast(beta, V)
    check("bE recovers +0.5 and bC is flat",
          abs(beta[2] - 0.5) < 0.1 and abs(beta[1]) < 0.1,
          f"bC {beta[1]:+.3f}  bE {beta[2]:+.3f}")
    check("and the contrast bE - bC is positive and significant",
          est > 0 and t > T_GATE, f"{est:+.3f} at t {t:+.2f}")
    #: PLANTED: the mirror. If the SHARED part is what reverts, the same
    #: code must produce a negative contrast, or the test is one-sided
    #: by construction.
    y2 = 0.5 * c_x + rng.normal(0, 1, n)
    b2, V2 = regress(y2, X, cl)
    e2, t2 = contrast(b2, V2)
    check("the mirror case gives a NEGATIVE contrast",
          e2 < 0 and t2 < -T_GATE, f"{e2:+.3f} at t {t2:+.2f}")
    #: PLANTED: six instruments on one date are one observation's worth.
    per_date = list(rng.normal(0.4, 1.0, 300))
    yy = [v for v in per_date for _ in range(6)]
    gg = [i for i in range(300) for _ in range(6)]
    b3, V3 = regress(yy, np.ones((len(yy), 1)), gg)
    plain = st.mean(per_date) / (st.stdev(per_date) / math.sqrt(300))
    naive = st.mean(yy) / (st.stdev(yy) / math.sqrt(len(yy)))
    check("clustering by date undoes the six-fold count",
          abs(tstat(b3, V3, 0) - plain) < 0.02,
          f"clustered {tstat(b3, V3, 0):+.2f}  one-per-date {plain:+.2f}  "
          f"naive {naive:+.2f}")

    print("\nthe morning, end to end")
    d = dt.date(2026, 3, 11)

    def synth(vals, spread=0.0):
        b, a = {}, {}
        for hm, (o, c) in vals.items():
            b[(d, hm)] = (o - spread / 2, o, o, c - spread / 2)
            a[(d, hm)] = (o + spread / 2, o, o, c + spread / 2)
        return b, a
    b, a = synth({SIG: (100.0, 101.0), ENTRY: (101.0, 101.0),
                  H0: (100.5, 100.5), CLOSE: (100.0, 100.0)})
    m, y0, y1 = morning(b, a, d)
    check("the move is the 08:30 bar, open to close",
          abs(m - (101.0 / 100.0 - 1) * 1e4) < 1e-9, f"{m:+.1f} bp")
    check("an up bar is faded short, and a fall is a profit",
          y0 > 0 and abs(y0 - (1 - 100.5 / 101.0) * 1e4) < 1e-9,
          f"{y0:+.1f} bp at 09:45")
    check("15:45 is measured from the same 08:45 entry",
          abs(y1 - (1 - 100.0 / 101.0) * 1e4) < 1e-9, f"{y1:+.1f} bp")
    check("a doji 08:30 bar is not a morning",
          morning(*synth({SIG: (100.0, 100.0), ENTRY: (100.0, 100.0),
                          H0: (100.0, 100.0), CLOSE: (100.0, 100.0)}),
                  d) is None)
    b2, a2 = synth({SIG: (100.0, 101.0), ENTRY: (101.0, 101.0),
                    H0: (100.5, 100.5), CLOSE: (100.0, 100.0)})
    del b2[(d, CLOSE)]
    check("a missing bar drops the morning", morning(b2, a2, d) is None)

    print("\nthe frozen constants")
    check("four equity indices are the pack; gold and EUR report only",
          EQUITY == ("SPX500_USD", "NAS100_USD", "US30_USD", "DE30_EUR")
          and OTHER == ("EUR_USD", "XAU_USD"))
    check("24 prior events for sigma, gate at 2.24, forward sample out",
          VOL_WINDOW == 24 and T_GATE == 2.24
          and FORWARD_START == dt.date(2026, 9, 18))
    check("both documents are pinned", len(DOCS) == 2
          and all(len(h) == 64 for _, h in DOCS))
    check("no order, execute, submit or position name in this file",
          not [n for n in globals() if _FORBIDDEN.search(n)])

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="../data/v24")
    ap.add_argument("--events", default="../data/events_v2.csv")
    ap.add_argument("--out", default="../data/factor_v28_trades.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"premarket_factor.py v{VERSION}   PREREGISTRATION_v28 + v28.1\n")
    print("  I am not a financial adviser. This is a measurement, not a")
    print("  recommendation to take a position.\n")
    here = os.path.dirname(os.path.abspath(__file__))
    for doc, want in DOCS:
        got = hashlib.sha256(
            open(os.path.join(here, "..", doc), "rb").read()).hexdigest()
        if got != want:
            print(f"  {doc} changed since it was frozen ({got[:12]}). Refused.")
            sys.exit(2)
        print(f"  {doc} sha256 {got[:16]}... matches the frozen copy")

    pre, _ = load_events(a.events, from_year=1900)
    s1 = {d for d, e in pre.items() if {"CPI", "NFP"} & e}
    s2 = {d for d, e in pre.items() if "CLAIMS" in e} - s1
    print(f"\n  CPI/payrolls {len(s1):,} dates   claims-only {len(s2):,}   "
          f"control: every other morning\n")

    raw = {}
    for ins in EQUITY + OTHER:
        pb = os.path.join(a.data_dir, f"{stem(ins)}_bid_15m.csv")
        pa = os.path.join(a.data_dir, f"{stem(ins)}_ask_15m.csv")
        if not (os.path.exists(pb) and os.path.exists(pa)):
            print(f"  {ins:<12} NO DATA")
            continue
        b, ask = read_marks(pb), read_marks(pa)
        rows = {"S1": [], "S2": [], "S3": []}
        for d in sorted({x for (x, hm) in b if hm == SIG}):
            if d >= FORWARD_START:
                continue
            got = morning(b, ask, d)
            if got is None:
                continue
            rows["S1" if d in s1 else ("S2" if d in s2 else "S3")].append(
                (d,) + got)
        for cls in rows:
            sig = trailing_sigma([r[1] for r in rows[cls]])
            rows[cls] = [(d, m, y0, y1, s)
                         for (d, m, y0, y1), s in zip(rows[cls], sig)
                         if s is not None and s > 0]
        raw[ins] = rows
        print(f"  {ins:<12} S1 {len(rows['S1']):>4}   S2 {len(rows['S2']):>4}"
              f"   S3 {len(rows['S3']):>5}   (first {VOL_WINDOW} of each "
              f"dropped: no prior sigma)")

    # ---- build the decomposed rows ------------------------------------
    recs = {"S1": [], "S2": [], "S3": []}
    for cls in ("S1", "S2", "S3"):
        by_date = {}
        for ins in raw:
            for d, m, y0, y1, s in raw[ins][cls]:
                by_date.setdefault(d, {})[ins] = (m, y0, y1, s)
        for d, got in sorted(by_date.items()):
            if any(i not in got for i in EQUITY):
                continue
            z = {i: got[i][0] / got[i][3] for i in got}
            for ins in EQUITY + OTHER:
                if ins not in got:
                    continue
                m, y0, y1, s = got[ins]
                others = ([z[j] for j in EQUITY if j != ins] if ins in EQUITY
                          else [z[j] for j in EQUITY])
                C, E = decompose(m, s, others)
                assert abs((C + E) - abs(m)) < 1e-6
                recs[cls].append(dict(cls=cls, date=d, ins=ins, m=m, sigma=s,
                                      y0=y0, y1=y1, C=C, E=E))

    with open(a.out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sample", "instrument", "date", "move_bp", "sigma_bp",
                    "C_bp", "E_bp", "fade_0945", "fade_1545"])
        for cls in ("S1", "S2", "S3"):
            for r in recs[cls]:
                w.writerow([cls, r["ins"], r["date"].isoformat(),
                            f"{r['m']:.6f}", f"{r['sigma']:.6f}",
                            f"{r['C']:.6f}", f"{r['E']:.6f}",
                            f"{r['y0']:.6f}", f"{r['y1']:.6f}"])
    print(f"\n  per-trade decomposition written to {a.out}")

    # ---- Gate 0, as amended by v28.1 -----------------------------------
    v27 = {}
    p27 = os.path.join(here, V27_FILE)
    if os.path.exists(p27):
        for r in csv.DictReader(open(p27)):
            if r["gross_H0"]:
                v27[(r["instrument"], r["date"])] = float(r["gross_H0"])
    matched, worst = 0, 0.0
    for cls in recs:
        for r in recs[cls]:
            k = (r["ins"], r["date"].isoformat())
            if k in v27:
                matched += 1
                worst = max(worst, abs(r["y0"] - v27[k]))
    eq1 = [r["y0"] for r in recs["S1"] if r["ins"] in EQUITY]
    print(f"\n  GATE 0 (v28.1)  {matched:,} trades matched against v27's "
          f"file, max |difference| {worst:.1e} bp   "
          f"[{'PASS' if matched > 1000 and worst < 1e-6 else 'FAIL'}]")
    print(f"    reported, no threshold: the four-equity mean fade at 09:45 "
          f"is {st.mean(eq1):+.2f} bp beside v27's six-instrument +3.61")
    if not (matched > 1000 and worst < 1e-6):
        print("    VOID -- this file does not read the bars the way v27 did.")
        sys.exit(3)

    # ---- the regression -------------------------------------------------
    def run(cls, name, group, horizon="y0"):
        rows = [r for r in recs[cls] if r["ins"] in group]
        if len(rows) < 100:
            print(f"    {name:<26} too few rows ({len(rows)})")
            return None
        y = [r[horizon] / r["sigma"] for r in rows]
        X = [[1.0, r["C"] / r["sigma"], r["E"] / r["sigma"]] for r in rows]
        beta, V = regress(y, X, [r["date"] for r in rows])
        est, t = contrast(beta, V)
        print(f"    {name:<26}{len(rows):>7}{fmt(beta[1])}{fmt(tstat(beta, V, 1), 7, 2)}"
              f"{fmt(beta[2])}{fmt(tstat(beta, V, 2), 7, 2)}"
              f"{fmt(est)}{fmt(t, 7, 2)}")
        return dict(n=len(rows), bC=beta[1], bE=beta[2], est=est, t=t,
                    tC=tstat(beta, V, 1), tE=tstat(beta, V, 2), rows=rows)

    print(f"\n  THE REGRESSION -- fade at 09:45 on the pack's share (C) and "
          f"this instrument's own (E), all in sigma units")
    print(f"    {'sample':<26}{'n':>7}{'bC':>7}{'t':>7}{'bE':>7}{'t':>7}"
          f"{'bE-bC':>7}{'t':>7}")
    r1 = run("S1", "S1 CPI+payrolls, equity", EQUITY)
    r2 = run("S2", "S2 claims, equity", EQUITY)
    r3 = run("S3", "S3 control, equity", EQUITY)
    print(f"\n    reported, gating nothing (v28 section 2):")
    for ins in OTHER:
        run("S1", f"   S1 {ins}", (ins,))
    print(f"\n    the same regression at 15:45 -- DESCRIPTIVE ONLY, every")
    print(f"    sample here is spent for horizon questions (v28 section 5):")
    for cls, nm in (("S1", "S1 CPI+payrolls, equity"),
                    ("S2", "S2 claims, equity"),
                    ("S3", "S3 control, equity")):
        run(cls, f"   {nm}", EQUITY, horizon="y1")

    print(f"\n  BY THIRDS of the idiosyncratic share |E| / (|E| + |C|) -- "
          f"reported, gating nothing")
    print(f"    {'sample':<26}{'low third':>12}{'middle':>10}{'high third':>12}"
          f"{'high - low':>12}")
    for cls, nm, rr in (("S1", "S1 CPI+payrolls", r1), ("S2", "S2 claims", r2),
                        ("S3", "S3 control", r3)):
        if not rr:
            continue
        rows = sorted(rr["rows"],
                      key=lambda r: abs(r["E"]) / max(1e-9, abs(r["E"]) + abs(r["C"])))
        k = len(rows) // 3
        lo, mid, hi = rows[:k], rows[k:2 * k], rows[2 * k:]
        print(f"    {nm:<26}{st.mean(r['y0'] for r in lo):>+12.2f}"
              f"{st.mean(r['y0'] for r in mid):>+10.2f}"
              f"{st.mean(r['y0'] for r in hi):>+12.2f}"
              f"{st.mean(r['y0'] for r in hi) - st.mean(r['y0'] for r in lo):>+12.2f}")

    print(f"\n  GATES -- frozen in PREREGISTRATION_v28 section 4")
    g1 = bool(r1) and r1["est"] > 0 and r1["t"] is not None and r1["t"] >= T_GATE
    g2 = bool(r2) and r2["est"] > 0 and r2["t"] is not None and r2["t"] >= T_GATE
    print(f"    [{'PASS' if g1 else 'FAIL'}] G1 CPI+payrolls  bE - bC "
          f"{r1['est']:+.3f}  t {r1['t']:+.2f}" if r1 else "    G1 no data")
    print(f"    [{'PASS' if g2 else 'FAIL'}] G2 claims        bE - bC "
          f"{r2['est']:+.3f}  t {r2['t']:+.2f}" if r2 else "    G2 no data")
    if r3:
        hot = r3["t"] is not None and r3["t"] >= T_GATE and r3["est"] > 0
        if g1 and hot:
            msg = ("GENERAL ABSORPTION -- the same split works on ordinary "
                   "mornings; releases only supply bigger idiosyncratic moves")
        elif g1:
            msg = "RELEASE-SPECIFIC absorption -- the split works only on releases"
        elif hot:
            msg = ("on ordinary mornings but NOT on releases -- the "
                   "decomposition is not describing the release fade")
        else:
            msg = ("nowhere -- the decomposition explains nothing, and "
                   "absorption joins the other three dead explanations")
        print(f"    [ G3 ] control mornings  bE - bC {r3['est']:+.3f}  "
              f"t {r3['t']:+.2f}")
        print(f"           {msg}")


if __name__ == "__main__":
    main()
