#!/usr/bin/env python3
"""tl_build4 -- the v37 timeline (tl_build2) plus a SLOW-MACRO family, for PREREGISTRATION_v59.
Follows fastbot/TIMELINE_LIVING.md: every new value is stamped with the moment it was known, and a self-test fails if one is early.
Same construction as tl_build3: tl_build2.build() runs unchanged and the new features are ADDED afterwards, so the 125 base
features are identical by construction (Gate 0 checks it on the full SPX matrix).

THE NEW FAMILY (data/v59/fred/, pulled by fred_v59_pull.py; revision-safe series only)
  credit      DBAA - DAAA (daily)        stamp: 18:00 ET on the NEXT business day
                cs_up20 / cs_dn20 : 20-obs change >= +0.20 / <= -0.20 pp (fires every day it holds)   states cs, cs_chg20
  curve       T10Y3M (daily)             stamp: 18:00 ET next business day
                yc_inv / yc_uninv : crosses below 0 / above 0                                        states yc, yc_chg20
  policy      DFF (daily)                stamp: 18:00 ET next business day
                fed_up / fed_dn : DFF - DFF 5 obs earlier >= +0.20 / <= -0.20                        state dff_chg60
  oil         DCOILWTICO (daily)         stamp: 18:00 ET next business day
                oil_up10 / oil_dn10 : 20-obs return >= +10% / <= -10%                                 state oil_ret20
  conditions  NFCI (weekly, dated Friday) stamp: the following Wednesday 08:30 ET
                nfci_x0_up / nfci_x0_dn : crosses above / below 0                                     state nfci
  claims      ICSA (weekly, dated Saturday) stamp: the following Thursday 08:30 ET
                claims_up15 : 4-week avg >= 1.15 x its lowest over the prior 26 weeks
                claims_dn15 : 4-week avg <= 0.85 x its highest over the prior 26 weeks                state claims_z (4-wk avg z vs prior 52)
  -> 12 events + 8 states = 20 new features (the spec's table; its summary line says "9 states, 21" -- a typo, the table governs).

    python3 tl_build4.py --self-test
"""
from __future__ import annotations
import bisect, csv, datetime as dt, math, os, statistics as st, sys
import numpy as np
import tl_build2 as T2, tl_build as T1

VERSION = "4.0"
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "v59", "fred")
NEW_EVENTS = ["cs_up20", "cs_dn20", "yc_inv", "yc_uninv", "fed_up", "fed_dn", "oil_up10", "oil_dn10",
              "nfci_x0_up", "nfci_x0_dn", "claims_up15", "claims_dn15"]
NEW_STATES = ["cs", "cs_chg20", "yc", "yc_chg20", "dff_chg60", "oil_ret20", "nfci", "claims_z"]
BASE_NAMES = [f"ms_{e}" for e in T1.EVENTS] + [f"n60_{e}" for e in T1.INTRADAY] + T1.STATES
NEW_NAMES = [f"ms_{e}" for e in NEW_EVENTS] + NEW_STATES
NAMES = BASE_NAMES + NEW_NAMES
CAP_MIN = T2.CAP_MIN


def read(sid):
    out = []
    for r in csv.DictReader(open(os.path.join(FD, f"{sid}.csv"))):
        try: out.append((dt.date.fromisoformat(r["date"]), float(r["value"])))
        except (ValueError, TypeError): pass
    return sorted(out)


def next_bday(d):
    d = d + dt.timedelta(days=1)
    while d.weekday() >= 5: d += dt.timedelta(days=1)
    return d


def daily_stamp(d): return dt.datetime.combine(next_bday(d), dt.time(18, 0))
def nfci_stamp(d): return dt.datetime.combine(d + dt.timedelta(days=5), dt.time(8, 30))      # Friday -> Wednesday
def icsa_stamp(d): return dt.datetime.combine(d + dt.timedelta(days=5), dt.time(8, 30))      # Saturday -> Thursday


def macro_events():
    ev, ser = [], {}
    a, b = dict(read("DBAA")), dict(read("DAAA"))
    cs = [(d, a[d] - b[d]) for d in sorted(set(a) & set(b))]
    ser["cs"] = [(daily_stamp(d), v) for d, v in cs]
    ser["cs_chg20"] = []
    for i in range(20, len(cs)):
        d, ch = cs[i][0], cs[i][1] - cs[i - 20][1]; s = daily_stamp(d); ser["cs_chg20"].append((s, ch))
        if ch >= 0.20: ev.append((s, "cs_up20"))
        if ch <= -0.20: ev.append((s, "cs_dn20"))
    yc = read("T10Y3M")
    ser["yc"] = [(daily_stamp(d), v) for d, v in yc]
    ser["yc_chg20"] = [(daily_stamp(yc[i][0]), yc[i][1] - yc[i - 20][1]) for i in range(20, len(yc))]
    for (p, x), (d, y) in zip(yc, yc[1:]):
        if x >= 0 > y: ev.append((daily_stamp(d), "yc_inv"))
        if x < 0 <= y: ev.append((daily_stamp(d), "yc_uninv"))
    ff = read("DFF")
    ser["dff_chg60"] = [(daily_stamp(ff[i][0]), ff[i][1] - ff[i - 60][1]) for i in range(60, len(ff))]
    for i in range(5, len(ff)):
        ch = ff[i][1] - ff[i - 5][1]
        if ch >= 0.20: ev.append((daily_stamp(ff[i][0]), "fed_up"))
        if ch <= -0.20: ev.append((daily_stamp(ff[i][0]), "fed_dn"))
    oil = [(d, v) for d, v in read("DCOILWTICO")]
    ser["oil_ret20"] = []
    for i in range(20, len(oil)):
        if oil[i - 20][1] <= 0: continue
        r = oil[i][1] / oil[i - 20][1] - 1; s = daily_stamp(oil[i][0]); ser["oil_ret20"].append((s, r))
        if r >= 0.10: ev.append((s, "oil_up10"))
        if r <= -0.10: ev.append((s, "oil_dn10"))
    nf = read("NFCI")
    ser["nfci"] = [(nfci_stamp(d), v) for d, v in nf]
    for (p, x), (d, y) in zip(nf, nf[1:]):
        if x <= 0 < y: ev.append((nfci_stamp(d), "nfci_x0_up"))
        if x > 0 >= y: ev.append((nfci_stamp(d), "nfci_x0_dn"))
    ic = read("ICSA")
    a4 = [(ic[i][0], st.fmean(v for _, v in ic[i - 3:i + 1])) for i in range(3, len(ic))]
    vals = [v for _, v in a4]; ser["claims_z"] = []
    for i in range(len(a4)):
        d, v = a4[i]; s = icsa_stamp(d)
        if i >= 52:
            base = vals[i - 52:i]; sd = st.pstdev(base)
            if sd > 0: ser["claims_z"].append((s, (v - st.fmean(base)) / sd))
        if i >= 26:
            if v >= 1.15 * min(vals[i - 26:i]): ev.append((s, "claims_up15"))
            if v <= 0.85 * max(vals[i - 26:i]): ev.append((s, "claims_dn15"))
    assert {e for _, e in ev} <= set(NEW_EVENTS)
    return sorted(ev), ser


def augment(rows, feats, sess=None):
    sess = sess or T2.US
    ev, ser = macro_events()
    ev = T2.to_local(ev, sess.tz); ser = {k: T2.prep(T2.to_local(v, sess.tz)) for k, v in ser.items()}
    stamps = {e: [] for e in NEW_EVENTS}
    for s, e in ev: stamps[e].append(s)
    for f, r in zip(feats, rows):
        t = T2._dt(r["date"], r["hm"]) + dt.timedelta(minutes=5)
        for e in NEW_EVENTS:
            L = stamps[e]; j = bisect.bisect_right(L, t) - 1
            f["ms_" + e] = math.log1p(min(CAP_MIN, (t - L[j]).total_seconds() / 60)) if j >= 0 else math.log1p(CAP_MIN)
        for k in NEW_STATES: f[k] = T2.asof(ser[k], t)
    return rows, feats


def build(data_dir, here, days=None, sess=T2.US, verbose=False):
    rows, feats, evlog = T2.build(data_dir, here, days=days, sess=sess, verbose=verbose)
    augment(rows, feats, sess); return rows, feats, evlog


def to_matrix(rows, feats):
    X = np.array([[np.nan if f.get(n) is None else f[n] for n in NAMES] for f in feats], dtype=np.float32)
    return dict(X=X, names=np.array(NAMES), date=np.array([r["date"].isoformat() for r in rows]), hm=np.array([r["hm"] for r in rows]),
                yl=np.array([r["yl"] for r in rows], np.int8), ys=np.array([r["ys"] for r in rows], np.int8),
                gl=np.array([r["gl"] for r in rows], np.float32), gs=np.array([r["gs"] for r in rows], np.float32),
                b_bp=np.array([r["b_bp"] for r in rows], np.float32), spread=np.array([r["spread"] for r in rows], np.float32))


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"tl_build4.py v{VERSION} self-test\n")
    ev, ser = macro_events()
    check("every new event type is declared", {e for _, e in ev} <= set(NEW_EVENTS))
    check("every new event type fires at least once", {e for _, e in ev} == set(NEW_EVENTS))
    check("daily-series stamps are never on the observation's own date", all(s.date() > d for d, _ in read("DBAA") for s in [daily_stamp(d)]))
    # planted 1: Thursday 2020-03-19 13:45 sees the claims print released that morning (week ending Sat 14 Mar), not 26 Mar
    ic = dict(read("ICSA"))
    rows, feats = [dict(date=dt.date(2020, 3, 19), hm="13:40")], [{}]
    augment(rows, feats)
    zs = dict((s, v) for s, v in ser["claims_z"])
    want = zs.get(dt.datetime(2020, 3, 19, 8, 30)); nxt = zs.get(dt.datetime(2020, 3, 26, 8, 30))
    check("PLANTED: a 13:45 decision on 2020-03-19 sees the 19-Mar claims print and not the 26-Mar one",
          want is not None and feats[0]["claims_z"] == want and feats[0]["claims_z"] != nxt)
    # planted 2: Tuesday 2020-03-17 13:45 sees the DBAA-DAAA value of Fri 13 Mar, not Mon 16 Mar
    a, b = dict(read("DBAA")), dict(read("DAAA"))
    rows, feats = [dict(date=dt.date(2020, 3, 17), hm="13:40")], [{}]
    augment(rows, feats)
    check("PLANTED: a 13:45 decision on 2020-03-17 sees the 13-Mar credit spread, not the 16-Mar one",
          abs(feats[0]["cs"] - (a[dt.date(2020, 3, 13)] - b[dt.date(2020, 3, 13)])) < 1e-9 and
          abs(feats[0]["cs"] - (a[dt.date(2020, 3, 16)] - b[dt.date(2020, 3, 16)])) > 1e-9)
    here = os.path.dirname(os.path.abspath(__file__))
    rows, feats, _ = T2.build("../data", here, limit_days=80, verbose=False)
    before = [dict(f) for f in feats]; augment(rows, feats)
    check("augment leaves all 125 base features of an 80-session build untouched",
          all(all((b_.get(k) == f.get(k)) or (b_.get(k) != b_.get(k)) for k in b_) for b_, f in zip(before, feats)))
    check("145 features, names unique", len(NAMES) == 145 and len(set(NAMES)) == 145)
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE")); return 0 if ok else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]: sys.exit(self_test())
    raise SystemExit("tl_build4 is a library for macro_v59.py")
