#!/usr/bin/env python3
"""tl_build3 -- the v37 timeline (tl_build2) plus a MARKET INTERNALS family,
for PREREGISTRATION_v54. Follows fastbot/TIMELINE_LIVING.md: every new event is
stamped with the moment it was known, and a self-test fails if one is early.

HOW IT EXTENDS WITHOUT TOUCHING THE OLD TIMELINE
------------------------------------------------
tl_build2.build() runs unchanged; the new features are ADDED to each decision
point afterwards. The new events never feed tl_build2's own events, so the 125
original features are byte-identical by construction -- and Gate 0 checks it
on the full SPX matrix anyway. tl_build2.py and tl_build.py are not edited
(v40 and the live v41 recorder depend on them).

THE NEW FAMILY (data/tv/, pulled through the TradingView connector, tv_series.py)
------------------------------------------------------------------------------
put/call  USI:PCC (Cboe total put/call, TradingView's series; NOT the Cboe file,
          which stopped on 2019-10-04 -- see tv_series / v54 for the comparison)
          values outside [0.3, 3.0] are dropped as bad prints
            pcc_x1_up / pcc_x1_dn     crosses 1.0               known 18:00 ET
            state pcc, pcc_z          level; z vs prior 252 obs
VIX term  CBOE:VIX / CBOE:VIX3M -- the roll-free version of vx_ratio
            vts_inv / vts_norm         ratio crosses above / below 1   16:15 ET
            state vts
breadth   INDEX:S5FI (% of S&P 500 above 50-day), INDEX:S5TH (above 200-day)
            s5fi_x20_dn / s5fi_x20_up / s5fi_x80_up / s5fi_x80_dn          18:00 ET
            s5th_x50_up / s5th_x50_dn
            state s5fi, s5th
NYSE A/D  USI:ADD (advances - declines), USI:ADV, USI:DECL
            add_thrust / add_washout   ADD z vs prior 252 obs > +2 / < -2   18:00 ET
            zweig_thrust               10-day EMA of ADV/(ADV+DECL) closes above
                                       0.615 having been below 0.40 within the
                                       previous 10 sessions (Zweig 1986)
            state add_z, adr10
Thresholds are the conventional round numbers, fixed before any outcome.

    python3 tl_build3.py --self-test
"""
from __future__ import annotations

import bisect, datetime as dt, math, os, statistics as st, sys
import numpy as np

import tl_build2 as T2, tl_build as T1, tv_series as TV

VERSION = "3.0"
NEW_EVENTS = ["pcc_x1_up", "pcc_x1_dn", "vts_inv", "vts_norm",
              "s5fi_x20_dn", "s5fi_x20_up", "s5fi_x80_up", "s5fi_x80_dn",
              "s5th_x50_up", "s5th_x50_dn", "add_thrust", "add_washout", "zweig_thrust"]
NEW_STATES = ["pcc", "pcc_z", "vts", "s5fi", "s5th", "add_z", "adr10"]
BASE_NAMES = [f"ms_{e}" for e in T1.EVENTS] + [f"n60_{e}" for e in T1.INTRADAY] + T1.STATES
NEW_NAMES = [f"ms_{e}" for e in NEW_EVENTS] + NEW_STATES
NAMES = BASE_NAMES + NEW_NAMES
CAP_MIN = T2.CAP_MIN


def _z(vals, i, n=252):
    if i < n:
        return None
    base = vals[i - n:i]
    sd = st.pstdev(base)
    return None if sd == 0 else (vals[i] - st.fmean(base)) / sd


def internal_events(tv_dir=TV.TV_DIR):
    """[(stamp_et, event)], {state: [(stamp_et, value)]}. Every stamp comes from
    TV.avail(name, trade_date) -- never earlier than that series' close."""
    ev, ser = [], {}
    S = lambda name, d: TV.avail(name, d)
    # put/call
    pc = [(d, v) for d, v in TV.read("PCC", tv_dir) if 0.3 <= v <= 3.0]
    vals = [v for _, v in pc]
    ser["pcc"] = [(S("PCC", d), v) for d, v in pc]
    ser["pcc_z"] = [(S("PCC", pc[i][0]), z) for i in range(len(pc)) if (z := _z(vals, i)) is not None]
    for (a, x), (b, y) in zip(pc, pc[1:]):
        if x < 1.0 <= y: ev.append((S("PCC", b), "pcc_x1_up"))
        if x >= 1.0 > y: ev.append((S("PCC", b), "pcc_x1_dn"))
    # VIX / VIX3M
    v, v3 = dict(TV.read("VIX", tv_dir)), dict(TV.read("VIX3M", tv_dir))
    ds = sorted(set(v) & set(v3))
    r = [(d, v[d] / v3[d]) for d in ds if v3[d] > 0]
    ser["vts"] = [(S("VIX3M", d), x) for d, x in r]
    for (a, x), (b, y) in zip(r, r[1:]):
        if x <= 1.0 < y: ev.append((S("VIX3M", b), "vts_inv"))
        if x > 1.0 >= y: ev.append((S("VIX3M", b), "vts_norm"))
    # breadth
    for name, key, crosses in (("S5FI", "s5fi", (20, 80)), ("S5TH", "s5th", (50,))):
        s = TV.read(name, tv_dir)
        ser[key] = [(S(name, d), x) for d, x in s]
        for (a, x), (b, y) in zip(s, s[1:]):
            for c in crosses:
                if x < c <= y: ev.append((S(name, b), f"{key}_x{c}_up"))
                if x >= c > y: ev.append((S(name, b), f"{key}_x{c}_dn"))
    # NYSE advance/decline
    add = TV.read("ADD", tv_dir)
    av = [x for _, x in add]
    zs = [(add[i][0], _z(av, i)) for i in range(len(add))]
    ser["add_z"] = [(S("ADD", d), z) for d, z in zs if z is not None]
    for d, z in zs:
        if z is None:
            continue
        if z > 2: ev.append((S("ADD", d), "add_thrust"))
        if z < -2: ev.append((S("ADD", d), "add_washout"))
    adv, dec = dict(TV.read("ADV", tv_dir)), dict(TV.read("DECL", tv_dir))
    ds = sorted(d for d in set(adv) & set(dec) if adv[d] + dec[d] > 0)
    ema, em = None, []
    for d in ds:
        x = adv[d] / (adv[d] + dec[d])
        ema = x if ema is None else ema + (2 / 11) * (x - ema)
        em.append((d, ema))
    ser["adr10"] = [(S("ADV", d), x) for d, x in em]
    for i in range(10, len(em)):
        d, x = em[i]
        if x > 0.615 and em[i - 1][1] <= 0.615 and min(y for _, y in em[i - 10:i]) < 0.40:
            ev.append((S("ADV", d), "zweig_thrust"))
    names = set(e for _, e in ev)
    assert names <= set(NEW_EVENTS), names - set(NEW_EVENTS)
    return sorted(ev), ser


def augment(rows, feats, sess=None, tv_dir=TV.TV_DIR):
    """Add NEW_NAMES to every decision point, using only what was known at the
    decision bar's CLOSE (tl_build2's t = bar time + 5 min). Base keys untouched."""
    sess = sess or T2.US
    ev, ser = internal_events(tv_dir)
    ev = T2.to_local(ev, sess.tz)
    ser = {k: T2.prep(T2.to_local(v, sess.tz)) for k, v in ser.items()}
    stamps = {e: [] for e in NEW_EVENTS}
    for s, e in ev:
        stamps[e].append(s)
    for f, r in zip(feats, rows):
        t = T2._dt(r["date"], r["hm"]) + dt.timedelta(minutes=5)
        for e in NEW_EVENTS:
            L = stamps[e]
            j = bisect.bisect_right(L, t) - 1
            f["ms_" + e] = math.log1p(min(CAP_MIN, (t - L[j]).total_seconds() / 60)) if j >= 0 else math.log1p(CAP_MIN)
        for k in NEW_STATES:
            f[k] = T2.asof(ser[k], t)
    return rows, feats


def build(data_dir, here, days=None, sess=T2.US, verbose=False, tv_dir=TV.TV_DIR):
    rows, feats, evlog = T2.build(data_dir, here, days=days, sess=sess, verbose=verbose)
    augment(rows, feats, sess, tv_dir)
    return rows, feats, evlog


def to_matrix(rows, feats):
    X = np.array([[np.nan if f.get(n) is None else f[n] for n in NAMES] for f in feats], dtype=np.float32)
    return dict(X=X, names=np.array(NAMES),
                date=np.array([r["date"].isoformat() for r in rows]), hm=np.array([r["hm"] for r in rows]),
                yl=np.array([r["yl"] for r in rows], np.int8), ys=np.array([r["ys"] for r in rows], np.int8),
                gl=np.array([r["gl"] for r in rows], np.float32), gs=np.array([r["gs"] for r in rows], np.float32),
                b_bp=np.array([r["b_bp"] for r in rows], np.float32), spread=np.array([r["spread"] for r in rows], np.float32))


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"tl_build3.py v{VERSION} self-test\n")
    ev, ser = internal_events()
    check("every new event type is declared", {e for _, e in ev} <= set(NEW_EVENTS))
    check("every new event type fires at least once in 2007-2026", {e for _, e in ev} == set(NEW_EVENTS))
    early = [(s, e) for s, e in ev if s.time() < dt.time(16, 0)]
    check("NO new event is stamped before the 16:00 ET close of its own day", not early)
    check("NO state value is stamped before the 16:00 ET close", all(s.time() >= dt.time(16, 0) for v in ser.values() for s, _ in v))
    # planted: a decision at 13:45 cannot see that afternoon's breadth
    d = dt.date(2020, 3, 16)
    rows = [dict(date=d, hm="13:40")]
    feats = [{}]
    augment(rows, feats)
    s5 = dict(TV.read("S5FI"))
    check("PLANTED: a 13:45 decision sees the PREVIOUS day's S5FI, never the same day's",
          feats[0]["s5fi"] == s5[dt.date(2020, 3, 13)] and feats[0]["s5fi"] != s5[d])
    # augment must not alter base features
    here = os.path.dirname(os.path.abspath(__file__))
    rows, feats, _ = T2.build("../data", here, limit_days=80, verbose=False)
    before = [dict(f) for f in feats]
    augment(rows, feats)
    check("augment leaves all 125 base features of an 80-session build untouched",
          all(all((b.get(k) == f.get(k)) or (b.get(k) != b.get(k)) for k in b) for b, f in zip(before, feats)))
    check("145 features, names unique", len(NAMES) == 145 and len(set(NAMES)) == 145)
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    raise SystemExit("tl_build3 is a library for internals_v54.py")
