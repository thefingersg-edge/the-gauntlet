#!/usr/bin/env python3
"""PREREGISTRATION_v29 Part 2 -- when the headline and the internals
disagree, does the market walk more of the first move back?

Reads release_content.csv (fetched locally by release_content.py) and
v27's per-trade file for the fade. G3: mean fade on MIXED releases minus
CLEAN releases > 0 at clustered t >= 2.4, six instruments pooled.

    python3 premarket_content.py --self-test
    python3 premarket_content.py
"""
from __future__ import annotations

import argparse, csv, datetime as dt, hashlib, math, os, re, statistics as st, sys

VERSION = "1.0"
DOC = ("PREREGISTRATION_v29.md",
       "8feb1816d22b098f2773ab1e8d9b7d15fe2224b8f4e7f382d77fe9490635c5e3")
T_GATE = 2.4
PRIOR = 12
FORWARD_START = dt.date(2026, 9, 18)
_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)


def classify_nfp(d_payems, prior_changes, d_unrate):
    """MIXED / CLEAN / None per v29 section 4."""
    if len(prior_changes) < PRIOR:
        return None, None
    h = d_payems - st.median(prior_changes[-PRIOR:])
    if h == 0 or d_unrate == 0:
        return None, h
    return ("MIXED" if (h > 0) == (d_unrate > 0) else "CLEAN"), h


def classify_cpi(head_mm, prior_head, core_mm, prior_core):
    if len(prior_head) < PRIOR or len(prior_core) < PRIOR:
        return None, None
    hh = head_mm - st.median(prior_head[-PRIOR:])
    cc = core_mm - st.median(prior_core[-PRIOR:])
    if hh == 0 or cc == 0:
        return None, hh
    return ("MIXED" if (hh > 0) != (cc > 0) else "CLEAN"), hh


def diff_t(xa, ga, xb, gb):
    """mean(a) - mean(b), clustered by date via the influence function."""
    ma, mb = st.mean(xa), st.mean(xb)
    s = {}
    for x, g in zip(xa, ga):
        s[g] = s.get(g, 0.0) + (x - ma) / len(xa)
    for x, g in zip(xb, gb):
        s[g] = s.get(g, 0.0) - (x - mb) / len(xb)
    G = len(s)
    v = G / (G - 1) * sum(z * z for z in s.values())
    return ma - mb, (ma - mb) / math.sqrt(v)


def slope_t(x, y, g):
    """OLS slope of y on x with a date-clustered t (two parameters)."""
    n = len(x); mx, my = st.mean(x), st.mean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx
    a0 = my - b * mx
    s = {}
    for xi, yi, gi in zip(x, y, g):
        s[gi] = s.get(gi, 0.0) + (xi - mx) * (yi - a0 - b * xi)
    G = len(s)
    v = G / (G - 1) * (n - 1) / (n - 2) * sum(z * z for z in s.values()) / sxx ** 2
    return b, b / math.sqrt(v)


def _guard(names):
    bad = [n for n in names if _FORBIDDEN.search(n)]
    if bad:
        raise SystemExit(f"namespace guard: {bad}")


_guard(list(globals()))


def self_test():
    ok = True
    def check(n, c, d=""):
        nonlocal ok; ok &= bool(c)
        print(f"  [{'PASS' if c else 'FAIL'}] {n}" + (f"   {d}" if d else ""))
    print(f"premarket_content.py v{VERSION} self-test\n")
    prior = [150.0] * 12
    #: PLANTED: payrolls beat (h > 0) but unemployment ROSE -> mixed story
    check("payrolls beat and unemployment rose -> MIXED",
          classify_nfp(250.0, prior, +0.1)[0] == "MIXED")
    check("payrolls beat and unemployment fell -> CLEAN",
          classify_nfp(250.0, prior, -0.1)[0] == "CLEAN")
    check("payrolls missed and unemployment rose -> CLEAN",
          classify_nfp(50.0, prior, +0.1)[0] == "CLEAN")
    check("unemployment unchanged -> neither",
          classify_nfp(250.0, prior, 0.0)[0] is None)
    check("fewer than 12 priors -> neither",
          classify_nfp(250.0, prior[:11], 0.1)[0] is None)
    ph = [0.002] * 12
    check("CPI headline hot, core cool -> MIXED",
          classify_cpi(0.004, ph, 0.001, ph)[0] == "MIXED")
    check("CPI both hot -> CLEAN", classify_cpi(0.004, ph, 0.003, ph)[0] == "CLEAN")
    #: PLANTED: identical copies per date must count once
    a = [5.0, 7.0, 6.0, 8.0] * 3; ga = [i // 3 for i in range(12)]
    b = [1.0, 2.0, 0.0, 3.0] * 3; gb = [100 + i // 3 for i in range(12)]
    d, t = diff_t(a, ga, b, gb)
    check("the difference is right and the t is finite",
          abs(d - (st.mean(a) - st.mean(b))) < 1e-12 and math.isfinite(t),
          f"{d:+.2f}, t {t:+.2f}")
    x = [float(i) for i in range(200)]; y = [2 * v + (1 if i % 2 else -1)
                                            for i, v in enumerate(x)]
    bb, tt = slope_t(x, y, list(range(200)))
    check("the slope helper recovers a planted slope", abs(bb - 2) < 1e-3)
    check("gate 2.4, 12 prior prints, forward sample out",
          T_GATE == 2.4 and PRIOR == 12 and FORWARD_START == dt.date(2026, 9, 18))
    check("no order, execute, submit or position name in this file",
          not [n for n in globals() if _FORBIDDEN.search(n)])
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--content", default="../data/release_content.csv")
    ap.add_argument("--trades", default="../data/horizon_v27_trades.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    print(f"premarket_content.py v{VERSION}   PREREGISTRATION_v29 Part 2\n")
    print("  I am not a financial adviser. This is a measurement, not a")
    print("  recommendation to take a position.\n")
    here = os.path.dirname(os.path.abspath(__file__))
    got = hashlib.sha256(open(os.path.join(here, "..", DOC[0]), "rb").read()).hexdigest()
    if got != DOC[1]:
        print("  registration changed since frozen. Refused."); sys.exit(2)

    raw = {}
    for r in csv.DictReader(open(a.content)):
        raw.setdefault((r["release"], r["event_date"]), {})[r["series"]] = r
    per = {"NFP": [], "CPI": []}
    dropped = {"NFP": 0, "CPI": 0}
    for (rel, d), s in sorted(raw.items(), key=lambda kv: kv[0][1]):
        need = ("PAYEMS", "UNRATE") if rel == "NFP" else ("CPIAUCSL", "CPILFESL")
        if any(k not in s or s[k]["vintage_ok"] != "1" for k in need):
            dropped[rel] += 1
            continue
        v = {k: (float(s[k]["prev_value"]), float(s[k]["last_value"])) for k in need}
        per[rel].append((dt.date.fromisoformat(d), v))
    both = {d for d, _ in per["NFP"]} & {d for d, _ in per["CPI"]}
    cls = {}
    hist = {"dp": [], "h": [], "c": []}
    for d, v in per["NFP"]:
        dp = v["PAYEMS"][1] - v["PAYEMS"][0]
        du = v["UNRATE"][1] - v["UNRATE"][0]
        c, h = classify_nfp(dp, hist["dp"], du)
        hist["dp"].append(dp)
        if c and d not in both:
            cls[d] = ("NFP", c, abs(h))
    for d, v in per["CPI"]:
        hm = v["CPIAUCSL"][1] / v["CPIAUCSL"][0] - 1
        cm = v["CPILFESL"][1] / v["CPILFESL"][0] - 1
        c, hh = classify_cpi(hm, hist["h"], cm, hist["c"])
        hist["h"].append(hm); hist["c"].append(cm)
        if c and d not in both:
            cls[d] = ("CPI", c, abs(hh))
    tot = {k: len(per[k]) + dropped[k] for k in per}
    print(f"  releases fetched: payrolls {tot['NFP']}, CPI {tot['CPI']}")
    print(f"  dropped by the vintage check: payrolls {dropped['NFP']} "
          f"({dropped['NFP'] / max(1, tot['NFP']):.1%}), CPI {dropped['CPI']} "
          f"({dropped['CPI'] / max(1, tot['CPI']):.1%})   "
          f"same-day CPI+payrolls dropped: {len(both)}")

    tr = []
    for r in csv.DictReader(open(os.path.join(here, a.trades))):
        if r["sample"] != "S1" or not r["gross_H0"]:
            continue
        d = dt.date.fromisoformat(r["date"])
        if d in cls and d < FORWARD_START:
            tr.append((d, r["instrument"], float(r["gross_H0"]), cls[d]))
    print(f"  classified trades: {len(tr):,} on {len({t[0] for t in tr})} dates\n")

    def split(rows, lab):
        m = [t for t in rows if t[3][1] == "MIXED"]
        c = [t for t in rows if t[3][1] == "CLEAN"]
        d, t = diff_t([x[2] for x in m], [x[0] for x in m],
                      [x[2] for x in c], [x[0] for x in c])
        print(f"    {lab:<14} MIXED n {len(m):>5} {st.mean(x[2] for x in m):+6.2f} bp   "
              f"CLEAN n {len(c):>5} {st.mean(x[2] for x in c):+6.2f} bp   "
              f"difference {d:+6.2f}  t {t:+5.2f}")
        return d, t
    print("  fade at 09:45 by what the release said")
    d, t = split(tr, "both releases")
    print("    reported, gating nothing:")
    split([x for x in tr if x[3][0] == "NFP"], "  payrolls")
    split([x for x in tr if x[3][0] == "CPI"], "  CPI")
    for rel in ("NFP", "CPI"):
        rr = [x for x in tr if x[3][0] == rel]
        b, tb = slope_t([x[3][2] for x in rr], [x[2] for x in rr], [x[0] for x in rr])
        unit = "per 1k jobs of |surprise|" if rel == "NFP" else "per 1 pp of |surprise|"
        print(f"    fade vs |surprise|, {rel:<4} slope {b * (1 if rel=='NFP' else 1e-4):+.4f} bp "
              f"{unit if rel=='NFP' else 'per 0.01 pp'}   t {tb:+.2f}")
    ok = d > 0 and t >= T_GATE
    print(f"\n  GATE -- frozen in PREREGISTRATION_v29 section 4")
    print(f"    [{'PASS' if ok else 'FAIL'}] G3  MIXED - CLEAN {d:+.2f} bp  t {t:+.2f}")


if __name__ == "__main__":
    main()
