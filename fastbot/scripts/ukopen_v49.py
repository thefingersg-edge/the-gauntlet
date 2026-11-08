#!/usr/bin/env python3
"""PREREGISTRATION_v49 -- does the FTSE open under-react to overnight US / European moves?

Interpretations fixed here, BEFORE the run:
 * Times are London (Europe/London); OANDA timestamps are UTC bar starts; mid = (bid+ask)/2.
 * UK_on  = UK100 close of prior session's 16:25 bar -> close of today's 07:55 bar.
 * US_on  = SPX500 15m: close of the last bar closing <= prior-session 16:30 London
            -> close of the last bar closing <= today 07:55 London.
 * EU_pre = DE30 open of 07:00 bar -> close of 07:55 bar.
 * beta   = OLS slope of US_on on UK_on over the prior 250 usable days (today excluded).
 * FH     = UK100 open of 08:00 bar -> close of 08:55 bar.  Spread = ask_o/bid_o - 1 at 08:00.
 * Sample from 2013-01-01 (as written); first 250 days are beta warm-up.
 * G2: |R| > 80th percentile of the prior 250 |R| values (so a further 250-day warm-up);
   trade sign(R)*FH - spread; t on trade days; eras by calendar year.
I am not a financial adviser. This is a measurement, not a recommendation."""
import csv, datetime as dt, hashlib, sys, bisect
from zoneinfo import ZoneInfo
import numpy as np
from premarket_factor import regress, tstat

VERSION = "1.0"
DOC = ("PREREGISTRATION_v49.md", "6a612316c5d96570518f426110d06950f378d7b358976fefc1243d263d082bc7")
L = ZoneInfo("Europe/London"); UTC = dt.timezone.utc
START, END = dt.date(2013, 1, 1), dt.date(2026, 9, 25)
T = 2.24; ERAS = ((2013, 2017), (2018, 2021), (2022, 2026))


def read(stem, folder, step, keep=None):
    ask = {}
    for r in csv.reader(open(f"../data/{folder}/{stem}_ask_{step}.csv")):
        if r[0] != "time": ask[r[0]] = (float(r[1]), float(r[4]))
    out = {}
    for r in csv.reader(open(f"../data/{folder}/{stem}_bid_{step}.csv")):
        if r[0] == "time" or r[0] not in ask or r[0] < "2011": continue
        u = dt.datetime.fromisoformat(r[0]).replace(tzinfo=UTC); t = u.astimezone(L)
        hm = t.strftime("%H:%M")
        if keep is not None and hm not in keep: continue
        bo, bc = float(r[1]), float(r[4]); ao, ac = ask[r[0]]
        out[(t.date(), hm) if keep is not None else u] = ((bo + ao) / 2, (bc + ac) / 2, bo, ao)
    return out


def main():
    if hashlib.sha256(open("../" + DOC[0], "rb").read()).hexdigest() != DOC[1]:
        sys.exit("PREREGISTRATION_v49.md changed -- refused")
    print(f"ukopen_v49.py v{VERSION}   PREREGISTRATION_v49 (sha {DOC[1][:8]}… matches)\n"
          "  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    UK = read("uk100gbp", "v38", "5m", {"16:25", "07:55", "08:00", "08:55"})
    DE = read("de30eur", "v38", "5m", {"07:00", "07:55"})
    SP = read("spx500usd", "v24", "15m")
    st = sorted(SP); sc = [u + dt.timedelta(minutes=15) for u in st]; sv = [SP[u][1] for u in st]
    def spx_at(local_dt):
        i = bisect.bisect_right(sc, local_dt.astimezone(UTC)) - 1
        return (sv[i], sc[i]) if i >= 0 else (None, None)
    closes = sorted(d for (d, hm) in UK if hm == "16:25")
    rows = []
    for d in sorted({d for (d, hm) in UK if START <= d <= END}):
        if not all((d, h) in UK for h in ("07:55", "08:00", "08:55")) or not all((d, h) in DE for h in ("07:00", "07:55")):
            continue
        k = bisect.bisect_left(closes, d) - 1
        if k < 0 or (d - closes[k]).days > 5: continue
        p = closes[k]
        uk_on = (UK[(d, "07:55")][1] / UK[(p, "16:25")][1] - 1) * 1e4
        a, ta = spx_at(dt.datetime.combine(p, dt.time(16, 30), L))
        b, tb = spx_at(dt.datetime.combine(d, dt.time(7, 55), L))
        if a is None or tb <= ta or (dt.datetime.combine(p, dt.time(16, 30), L) - ta) > dt.timedelta(hours=1): continue
        us_on = (b / a - 1) * 1e4
        eu = (DE[(d, "07:55")][1] / DE[(d, "07:00")][0] - 1) * 1e4
        o = UK[(d, "08:00")]; fh = (UK[(d, "08:55")][1] / o[0] - 1) * 1e4
        rows.append(dict(d=d, uk=uk_on, us=us_on, eu=eu, fh=fh, sp=(o[3] / o[2] - 1) * 1e4))
    # rolling beta and residual
    for i, r in enumerate(rows):
        if i < 250: r["R"] = None; continue
        x = np.array([q["uk"] for q in rows[i - 250:i]]); y = np.array([q["us"] for q in rows[i - 250:i]])
        beta = np.cov(x, y, ddof=1)[0, 1] / np.var(x, ddof=1); r["beta"] = beta
        r["R"] = r["us"] - beta * r["uk"]
    S = [r for r in rows if r["R"] is not None]
    for j, r in enumerate(S):
        r["top"] = None if j < 250 else abs(r["R"]) > np.quantile([abs(q["R"]) for q in S[j - 250:j]], 0.8)
    print(f"  usable days {len(rows)} ({rows[0]['d']}..{rows[-1]['d']});  with residual {len(S)};  "
          f"median beta {np.median([r['beta'] for r in S]):.2f};  median 08:00 spread {np.median([r['sp'] for r in S]):.2f} bp")
    print(f"  RMS: FH {np.sqrt(np.mean([r['fh']**2 for r in S])):.1f}  R {np.sqrt(np.mean([r['R']**2 for r in S])):.1f}"
          f"  EU_pre {np.sqrt(np.mean([r['eu']**2 for r in S])):.1f}  UK_on {np.sqrt(np.mean([r['uk']**2 for r in S])):.1f}")

    def g1(rs):
        y = np.array([r["fh"] for r in rs]); X = np.column_stack([np.ones(len(y)), [r["R"] for r in rs], [r["eu"] for r in rs]])
        b, V = regress(y, X, [r["d"].isoformat() for r in rs]); return b, V
    def g2(rs):
        tr = [r for r in rs if r["top"]]
        n = np.array([np.sign(r["R"]) * r["fh"] - r["sp"] for r in tr]); g = np.array([np.sign(r["R"]) * r["fh"] for r in tr])
        t = n.mean() / (n.std(ddof=1) / np.sqrt(len(n)))
        er = [n[[lo <= r["d"].year <= hi for r in tr]].mean() for lo, hi in ERAS]
        return dict(n=len(n), net=n.mean(), gross=g.mean(), t=t, er=er, ok=n.mean() > 0 and t >= T and all(e > 0 for e in er), hit=np.mean(n > 0))
    # self-test
    import copy
    P = copy.deepcopy(S); M = copy.deepcopy(S)
    for r in P: r["fh"] += 0.3 * r["R"]
    for r in M: r["fh"] -= 0.3 * r["R"]
    bp, Vp = g1(P); bm, Vm = g1(M)
    ok = (bp[1] > 0 and tstat(bp, Vp, 1) >= T) and not (bm[1] > 0 and tstat(bm, Vm, 1) >= T) and g2(P)["t"] > g2(M)["t"]
    print(f"  self-test: planted under-reaction -> G1 PASS, planted over-reaction -> G1 FAIL: {'OK' if ok else 'BROKEN'}")
    if not ok: sys.exit("self-test broken -- no verdict")

    b, V = g1(S); t1, t2 = tstat(b, V, 1), tstat(b, V, 2)
    G1 = b[1] > 0 and t1 >= T
    print(f"\n  G1 First hour = a + b1*R + b2*EU_pre:  b1 {b[1]:+.4f}  t {t1:+.2f}   -> {'PASS' if G1 else 'FAIL'}")
    G = g2(S)
    print(f"  G2 top-fifth |R| days, trade sign(R): n {G['n']}  gross {G['gross']:+.2f}  net {G['net']:+.2f} bp  t {G['t']:+.2f}  hit {G['hit']:.0%}"
          f"   eras " + " ".join(f"{e:+.2f}" for e in G["er"]) + f"   -> {'PASS' if G['ok'] else 'FAIL'}")
    print(f"\n    reported: b2 (European pre-open) {b[2]:+.4f}  t {t2:+.2f}")
    print(f"    reported: reverse sign (over-reaction): b1 {'<0' if b[1] < 0 else '>=0'}, t {t1:+.2f}; fade top-fifth net {-G['gross'] - (G['gross'] - G['net']):+.2f} bp")
    for lab, key in (("UK_on", "uk"), ("US_on", "us")):
        y = np.array([r["fh"] for r in S]); X = np.column_stack([np.ones(len(y)), [r[key] for r in S]])
        bb, VV = regress(y, X, [r["d"].isoformat() for r in S])
        print(f"    reported: FH on {lab} alone  slope {bb[1]:+.4f}  t {tstat(bb, VV, 1):+.2f}")
    for lo, hi in ERAS:
        rs = [r for r in S if lo <= r["d"].year <= hi]; bb, VV = g1(rs)
        print(f"    reported: {lo}-{hi}  b1 {bb[1]:+.4f} (t {tstat(bb, VV, 1):+.2f})  b2 {bb[2]:+.4f} (t {tstat(bb, VV, 2):+.2f})  n {len(rs)}")
    print(f"\n  VERDICTS  G1 {'PASS' if G1 else 'FAIL'}   G2 {'PASS' if G['ok'] else 'FAIL'}")


if __name__ == "__main__":
    main()
