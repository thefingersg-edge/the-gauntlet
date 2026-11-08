#!/usr/bin/env python3
"""PREREGISTRATION_v31 -- can public data call the market move before 08:30?

Written after fred_fetch_v31.py, against the frozen document, having seen
file layouts only. Q1 calls the PRINT (positive control), Q2 calls the
08:30 MOVE (gated, two-sided, |t| >= 2.4), Q3 the bounce (reported).

    python3 premarket_public.py --self-test
    python3 premarket_public.py
"""
from __future__ import annotations

import argparse, bisect, csv, datetime as dt, hashlib, math, os, re, statistics as st, sys
import numpy as np

from premarket_event import load_events
from premarket_factor import morning, trailing_sigma, regress, tstat
from premarket_participation import read_marks_vol, stem

VERSION = "1.0"
DOC = ("PREREGISTRATION_v31.md",
       "0dbbd8fd36e3f8c5f416162adee74a562c7d46f5fcf8cfddf3315ad5ebe18965")
INSTRUMENTS = ("SPX500_USD", "NAS100_USD", "US30_USD", "DE30_EUR", "EUR_USD", "XAU_USD")
FORWARD_START = dt.date(2026, 9, 18)
T_GATE, PRIOR = 2.4, 12
V31 = "../data/v31"
_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)


def month_key(d):
    return (d.year, d.month)


def prev_month(ym, k=1):
    y, m = ym
    for _ in range(k):
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return (y, m)


def petrol_accel(gas_by_month, ref):
    """P = g(M) - g(M-1), g = change in ln monthly mean petrol."""
    need = [ref, prev_month(ref), prev_month(ref, 2)]
    if any(k not in gas_by_month for k in need):
        return None
    a, b, c = (math.log(st.mean(gas_by_month[k])) for k in need)
    return (a - b) - (b - c)


def claims_trend(vals):
    """C = last published week - mean of the four weeks before it."""
    return None if len(vals) < 5 else vals[-1] - st.mean(vals[-5:-1])


def ols_t(x, y):
    n = len(x); mx, my = st.mean(x), st.mean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx
    res = [c - my - b * (a - mx) for a, c in zip(x, y)]
    se = math.sqrt(sum(r * r for r in res) / (n - 2) / sxx)
    return b, b / se


def _guard(names):
    bad = [n for n in names if _FORBIDDEN.search(n)]
    if bad:
        raise SystemExit(f"namespace guard: {bad}")


_guard(list(globals()))


def self_test():
    ok = True
    def check(n, c, d=""):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}" + (f"   {d}" if d else ""))
    print(f"premarket_public.py v{VERSION} self-test\n")
    g = {(2020, 1): [2.0], (2020, 2): [2.2], (2020, 3): [2.2]}
    #: PLANTED: petrol rose 10% in Feb then flat in March -> March's
    #: headline should fall back against February's: P < 0.
    p = petrol_accel(g, (2020, 3))
    check("a flat month after a rise gives NEGATIVE acceleration",
          abs(p - (0 - math.log(1.1))) < 1e-12, f"{p:+.4f}")
    check("a missing month gives None", petrol_accel(g, (2020, 4)) is None)
    check("claims trend is last minus the mean of the four before",
          claims_trend([200, 210, 220, 230, 250]) == 250 - 215)
    check("January's previous month is December", prev_month((2020, 1)) == (2019, 12))
    x = [float(i) for i in range(100)]; y = [2 * v + (1 if i % 2 else -1) for i, v in enumerate(x)]
    check("OLS helper recovers a slope", abs(ols_t(x, y)[0] - 2) < 1e-3)
    check("gate 2.4, 12 prior releases, forward sample out",
          T_GATE == 2.4 and PRIOR == 12 and FORWARD_START == dt.date(2026, 9, 18))
    check("no order, execute, submit or position name in this file",
          not [n for n in globals() if _FORBIDDEN.search(n)])
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def read_series(path):
    out = []
    for r in csv.DictReader(open(path)):
        try:
            out.append((dt.date.fromisoformat(r["date"]), float(r.get("value") or r.get("vix"))))
        except (TypeError, ValueError):
            pass
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="../data/v24")
    ap.add_argument("--events", default="../data/events_v2.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    print(f"premarket_public.py v{VERSION}   PREREGISTRATION_v31\n")
    print("  I am not a financial adviser. This is a measurement, not a")
    print("  recommendation to take a position.\n")
    here = os.path.dirname(os.path.abspath(__file__))
    got = hashlib.sha256(open(os.path.join(here, "..", DOC[0]), "rb").read()).hexdigest()
    if got != DOC[1]:
        print("  registration changed since frozen. Refused."); sys.exit(2)
    print(f"  {DOC[0]} sha256 {got[:16]}... matches\n")

    pre, _ = load_events(a.events, from_year=1900)
    cpi_d = {d for d, e in pre.items() if "CPI" in e}
    nfp_d = {d for d, e in pre.items() if "NFP" in e}
    clm_d = {d for d, e in pre.items() if "CLAIMS" in e} - cpi_d - nfp_d
    s1 = cpi_d | nfp_d

    # --- trades, as v28-v30 -----------------------------------------------
    recs, over = [], {}
    for ins in INSTRUMENTS:
        b, _v = read_marks_vol(os.path.join(a.data_dir, f"{stem(ins)}_bid_15m.csv"))
        ask, _ = read_marks_vol(os.path.join(a.data_dir, f"{stem(ins)}_ask_15m.csv"))
        closes = sorted((d, (b[(d, "15:45")][0] + ask[(d, "15:45")][0]) / 2)
                        for (d, hm) in b if hm == "15:45" and (d, hm) in ask)
        cd = [x[0] for x in closes]
        rows = {"S1": [], "S2": [], "S3": []}
        for d in sorted({x for (x, hm) in b if hm == "08:30"}):
            if d >= FORWARD_START:
                continue
            m = morning(b, ask, d)
            if m is None:
                continue
            k = bisect.bisect_left(cd, d)
            o830 = (b[(d, "08:30")][0] + ask[(d, "08:30")][0]) / 2
            ovn = math.log(o830 / closes[k - 1][1]) * 1e4 if k > 0 and (d - cd[k - 1]).days <= 4 else None
            rows["S1" if d in s1 else "S2" if d in clm_d else "S3"].append((d, m[0], m[1], ovn))
        for cls, rr in rows.items():
            for (d, mv, y0, ovn), s in zip(rr, trailing_sigma([r[1] for r in rr])):
                if s and s > 0:
                    recs.append(dict(cls=cls, ins=ins, date=d, m=mv, y0=y0, sigma=s, ovn=ovn))
    v27 = {(r["instrument"], r["date"]): float(r["gross_H0"])
           for r in csv.DictReader(open(os.path.join(here, "../data/horizon_v27_trades.csv"))) if r["gross_H0"]}
    diffs = [abs(r["y0"] - v27[(r["ins"], r["date"].isoformat())]) for r in recs
             if (r["ins"], r["date"].isoformat()) in v27]
    g0 = len(diffs) > 1000 and max(diffs) < 1e-6
    print(f"  GATE 0  {len(diffs):,} trades matched v27, max |diff| {max(diffs):.1e}   [{'PASS' if g0 else 'FAIL'}]")
    if not g0:
        sys.exit(3)

    # --- predictors and their print targets, one per release date -------
    gas = read_series(f"{V31}/GASREGW.csv")
    gm = {}
    for d, v in gas:
        gm.setdefault(month_key(d), []).append(v)
    rc = {}
    for r in csv.DictReader(open("../data/release_content.csv")):
        if r["vintage_ok"] == "1":
            rc[(r["series"], r["event_date"])] = (float(r["prev_value"]), float(r["last_value"]))
    pred, target = {}, {}
    # CPI
    prev_mm = None
    for d in sorted(cpi_d):
        f = rc.get(("CPIAUCSL", d.isoformat()))
        if not f:
            prev_mm = None; continue
        mm = f[1] / f[0] - 1
        P = petrol_accel(gm, prev_month(month_key(d)))
        if P is not None:
            pred[("CPI", d)] = P
            if prev_mm is not None:
                target[("CPI", d)] = mm - prev_mm
        prev_mm = mm
    # payrolls: ADP as published, and the v29 headline surprise
    vint = {}
    for r in csv.DictReader(open(f"{V31}/vintages.csv")):
        if r["status"] == "ok":
            vint.setdefault((r["series"], r["event_date"], r["vintage_date"]), []).append(
                (r["obs_date"], float(r["value"])))
    adp_hist, nfp_hist, adp_bad = [], [], 0
    for d in sorted(nfp_d):
        k = ("NPPTTL", d.isoformat(), (d - dt.timedelta(days=1)).isoformat())
        o = sorted(vint.get(k, []))
        exp = prev_month(month_key(d))
        if len(o) == 2 and month_key(dt.date.fromisoformat(o[1][0])) == exp:
            ch = o[1][1] - o[0][1]
            if len(adp_hist) >= PRIOR:
                pred[("NFP", d)] = ch - st.median(adp_hist[-PRIOR:])
            adp_hist.append(ch)
        elif o:
            adp_bad += 1
        f = rc.get(("PAYEMS", d.isoformat()))
        if f:
            ch = f[1] - f[0]
            if len(nfp_hist) >= PRIOR and ("NFP", d) in pred:
                target[("NFP", d)] = ch - st.median(nfp_hist[-PRIOR:])
            nfp_hist.append(ch)
    # claims
    clm_bad = 0
    for d in sorted(clm_d):
        before = sorted(vint.get(("ICSA", d.isoformat(), (d - dt.timedelta(days=1)).isoformat()), []))
        onday = sorted(vint.get(("ICSA", d.isoformat(), d.isoformat()), []))
        C = claims_trend([v for _, v in before])
        if C is None:
            continue
        if not onday or onday[-1][0] <= before[-1][0]:
            clm_bad += 1      # no new print that day: a vintage date, not a release
            continue
        pred[("CLM", d)] = C
        target[("CLM", d)] = onday[-1][1] - before[-1][1]
    n_by = {k: sum(1 for x in pred if x[0] == k) for k in ("CPI", "NFP", "CLM")}
    print(f"  predictors: CPI {n_by['CPI']} releases, payrolls (ADP as published, "
          f"2011-2023) {n_by['NFP']}, claims {n_by['CLM']}")
    print(f"  dropped: ADP vintage month mismatch {adp_bad}; claims dates with no new "
          f"print that day {clm_bad}\n")

    # --- Q1: does it call the print? ---------------------------------------
    print("  Q1 -- does it call the PRINT?  (positive control, one per release)")
    for kind, nm in (("CPI", "petrol accel -> CPI m/m change"),
                     ("NFP", "ADP surprise -> payrolls surprise"),
                     ("CLM", "claims trend -> claims change")):
        ks = [k for k in target if k[0] == kind and k in pred]
        x = [pred[k] for k in ks]; y = [target[k] for k in ks]
        b, t = ols_t(x, y)
        hit = sum(1 for p_, q in zip(x, y) if p_ * q > 0) / max(1, sum(1 for p_, q in zip(x, y) if p_ * q != 0))
        print(f"    {nm:<36} n {len(ks):>4}   t {t:+6.2f}   same sign {hit:.0%}")

    # --- Q2 and Q3 ----------------------------------------------------------
    def zmap(kind):
        vals = [v for k, v in pred.items() if k[0] == kind]
        sd = st.stdev(vals)
        return {k[1]: v / sd for k, v in pred.items() if k[0] == kind}

    def fit(rows, xs, ykey):
        rows = [r for r in rows if r["date"] in xs]
        if len(rows) < 50:
            return None
        y = [(r["m"] if ykey == "move" else r["y0"]) / r["sigma"] for r in rows]
        x = [xs[r["date"]] if ykey == "move" else abs(xs[r["date"]]) for r in rows]
        bb, V = regress(y, np.column_stack([np.ones(len(rows)), x]), [r["date"] for r in rows])
        return len(rows), bb[1], tstat(bb, V, 1)

    print("\n  Q2 -- does it call the 08:30 MOVE?  move/sigma on z(predictor), six pooled")
    gates = {}
    for gid, kind, cls, nm in (("G1", "CPI", "S1", "CPI / petrol"),
                               ("G2", "NFP", "S1", "payrolls / ADP"),
                               ("G3", "CLM", "S2", "claims / trend")):
        xs = zmap(kind)
        rows = [r for r in recs if r["cls"] == cls]
        n, bq, tq = fit(rows, xs, "move")
        dates = sorted(xs)
        cut = dates[len(dates) // 2]
        h1 = fit([r for r in rows if r["date"] < cut], xs, "move")
        h2 = fit([r for r in rows if r["date"] >= cut], xs, "move")
        q3 = fit(rows, xs, "fade")
        gates[gid] = (bq, tq, n)
        print(f"    {nm:<18} n {n:>5}   b {bq:+.3f}  t {tq:+.2f}   halves "
              f"{h1[1]:+.3f} (t {h1[2]:+.2f}) / {h2[1]:+.3f} (t {h2[2]:+.2f})   "
              f"Q3 bounce b {q3[1]:+.3f} t {q3[2]:+.2f}")
        per = []
        for ins in INSTRUMENTS:
            f = fit([r for r in rows if r["ins"] == ins], xs, "move")
            per.append(f"{ins[:6]} {f[2]:+.1f}" if f else f"{ins[:6]} --")
        print(f"      per instrument t: " + "  ".join(per))

    # --- backdrop, reported --------------------------------------------------
    vix = read_series("../data/VIXCLS.csv")
    dgs2 = read_series(f"{V31}/DGS2.csv")
    usd = read_series(f"{V31}/DTWEXBGS.csv")

    def last_before(s, d, back=0):
        ds = [x[0] for x in s]
        k = bisect.bisect_left(ds, d) - 1 - back
        return s[k][1] if k >= 0 and (d - s[k][0]).days <= 10 + back * 3 else None

    bd = {}
    for d in {r["date"] for r in recs if r["cls"] in ("S1", "S2")}:
        v = last_before(vix, d)
        y0, y5 = last_before(dgs2, d), last_before(dgs2, d, 5)
        u0, u5 = last_before(usd, d), last_before(usd, d, 5)
        bd[d] = dict(vix=v, dgs2=None if y0 is None or y5 is None else y0 - y5,
                     usd=None if not u0 or not u5 else math.log(u0 / u5))
    print("\n  BACKDROP -- reported, gating nothing  (t: vs direction / vs bounce)")
    for key, nm in (("vix", "VIX level"), ("dgs2", "2y yield, 5-day change"),
                    ("usd", "dollar, 5-day change"), ("ovn", "own move since prior 15:45")):
        cells = []
        for cls, lab in (("S1", "CPI+payrolls"), ("S2", "claims")):
            rows = [r for r in recs if r["cls"] == cls]
            if key == "ovn":
                vals = {(r["ins"], r["date"]): r["ovn"] for r in rows if r["ovn"] is not None}
            else:
                vals = {(r["ins"], r["date"]): bd[r["date"]][key] for r in rows
                        if r["date"] in bd and bd[r["date"]][key] is not None}
            sd = st.stdev(vals.values()); mu = st.mean(vals.values())
            rr = [dict(r, _z=(vals[(r["ins"], r["date"])] - mu) / sd) for r in rows
                  if (r["ins"], r["date"]) in vals]
            out = []
            for yk in ("m", "y0"):
                y = [r[yk] / r["sigma"] for r in rr]
                x = [r["_z"] for r in rr]     # backdrop: raw z for both
                bb, V = regress(y, np.column_stack([np.ones(len(rr)), x]), [r["date"] for r in rr])
                out.append(tstat(bb, V, 1))
            cells.append(f"{lab} {out[0]:+.2f} / {out[1]:+.2f}")
        print(f"    {nm:<28}" + "     ".join(cells))

    print(f"\n  GATES -- frozen in PREREGISTRATION_v31 (two-sided, |t| >= {T_GATE})")
    for gid, (bq, tq, n) in gates.items():
        print(f"    [{'PASS' if abs(tq) >= T_GATE else 'FAIL'}] {gid}  b {bq:+.3f}  t {tq:+.2f}  n {n}")


if __name__ == "__main__":
    main()
