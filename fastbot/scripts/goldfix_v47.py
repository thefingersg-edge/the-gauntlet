#!/usr/bin/env python3
"""PREREGISTRATION_v47 -- the London gold fix. XAU/USD OANDA 15m bid/ask (data/v24),
London time. PM window 14:45 bar open -> 15:00 bar close; AM window 10:15 -> 10:30 bar close."""
import csv, datetime as dt, hashlib, sys
from zoneinfo import ZoneInfo
import numpy as np
from timeline_v37 import cl_t

VERSION = "1.0"
DOC = ("PREREGISTRATION_v47.md", "47a5d6eb384a5839bb425d28d036cf7c74517adc3f9294c0fcacd3c9ca724951")
REFORM, END = dt.date(2015, 3, 20), dt.date(2026, 9, 25)
L = ZoneInfo("Europe/London")


def bars():
    b, a = {}, {}
    for fn, dst in (("../data/v24/xauusd_bid_15m.csv", b), ("../data/v24/xauusd_ask_15m.csv", a)):
        for r in csv.reader(open(fn)):
            if r[0] != "time":
                dst[r[0]] = tuple(float(x) for x in r[1:5])
    out = {}
    for k, v in b.items():
        if k not in a:
            continue
        t = dt.datetime.fromisoformat(k).replace(tzinfo=dt.timezone.utc).astimezone(L)
        out[(t.date(), t.strftime("%H:%M"))] = (v, a[k])
    return out


def window(B, d, first, last):
    if (d, first) not in B or (d, last) not in B:
        return None
    (b0, a0), (b1, a1) = B[(d, first)], B[(d, last)]
    o, c = (b0[0] + a0[0]) / 2, (b1[3] + a1[3]) / 2
    spread = (a0[0] / b0[0] - 1) * 1e4 + (a1[3] / b1[3] - 1) * 1e4      # half in + half out, x2 = full at each end
    return (c / o - 1) * 1e4, spread / 2


def main():
    if hashlib.sha256(open("../" + DOC[0], "rb").read()).hexdigest() != DOC[1]:
        sys.exit("PREREGISTRATION_v47.md changed -- refused")
    print(f"goldfix_v47.py v{VERSION}   PREREGISTRATION_v47 (sha {DOC[1][:8]}… matches)\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    B = bars(); days = sorted({d for d, _ in B if d <= END and d.weekday() < 5})
    rows = []
    for d in days:
        pm, am, rv = window(B, d, "14:45", "15:00"), window(B, d, "10:15", "10:30"), window(B, d, "15:15", "16:00")
        if pm:
            rows.append(dict(d=d, pm=pm[0], sp=pm[1], am=am[0] if am else None, rev=rv[0] if rv else None))
    pre = [r for r in rows if r["d"] < REFORM]; post = [r for r in rows if r["d"] >= REFORM]
    def t_of(rs, k):
        x = np.array([r[k] for r in rs if r[k] is not None]); dd = np.array([r["d"].isoformat() for r in rs if r[k] is not None])
        return (*cl_t(dd, x), len(x))
    m1, t1, n1 = t_of(pre, "pm")
    g1 = m1 < 0 and t1 <= -2.0
    print(f"  G1 pre-reform PM window (2006-03 -> 2015-03-19): {m1:+.2f} bp  t {t1:+.2f}  n {n1}  -> {'PASS' if g1 else 'FAIL'}")
    m2, t2, n2 = t_of(post, "pm")
    net = np.array([-r["pm"] - r["sp"] for r in post]); spr = np.median([r["sp"] for r in post])
    mn, tn = cl_t(np.array([r["d"].isoformat() for r in post]), net)
    g2 = m2 < 0 and t2 <= -2.24 and mn > 0
    print(f"  G2 post-reform PM window (2015-03-20 -> 2026-09): {m2:+.2f} bp  t {t2:+.2f}  n {n2};  short net {mn:+.2f} bp (t {tn:+.2f}; median spread {spr:.2f})  -> {'PASS' if g2 else 'FAIL'}")
    for lab, rs in (("pre", pre), ("post", post)):
        a = t_of(rs, "am"); v = t_of(rs, "rev")
        print(f"    reported {lab:<4}: AM window {a[0]:+.2f} bp (t {a[1]:+.2f})   after-fix 15:15-16:15 {v[0]:+.2f} bp (t {v[1]:+.2f})")
    print("    reported by year (PM window mean bp): " + "  ".join(
        f"{y}:{np.mean([r['pm'] for r in rows if r['d'].year == y]):+.1f}" for y in range(2006, 2027)))
    print(f"\n  VERDICTS  G1 {'PASS' if g1 else 'FAIL'}   G2 {'PASS' if g2 else 'FAIL'}")


if __name__ == "__main__":
    main()
