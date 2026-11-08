#!/usr/bin/env python3
"""tsyfut.py -- FLOWS-17, implements PREREGISTRATION_TSYFUT.md: the Treasury auction concession on ZN/ZB futures.
    python3 tsyfut.py --self-test        synthetic books, planted effects; reads no market data
    python3 tsyfut.py --check-inputs     pins, files, hashes, coverage -- computes NO returns
    python3 tsyfut.py --run              the registered test. Run once.
Measurement, not a recommendation. Not financial advice.
"""
from __future__ import annotations
import io, json, math, os, sys
import numpy as np
import pandas as pd
import common as C

NAME = "TSYFUT"
VERSION = "1.0"
TD = os.path.join(C.FDATA, "tsyfut")
START, END = pd.Timestamp("2010-06-07"), pd.Timestamp("2026-08-31")
ERAS = (("E1", "2010-06-07", "2012-03-31"), ("E2", "2012-04-01", "2019-06-30"), ("E3", "2019-07-01", "2026-08-31"))
ROBECO = pd.Timestamp("2025-04-01")
COMM_USD, MULT, TSTAT = 2.0, 1000.0, 2.13
LAG_NS, MAXAGE_NS = 60 * 10**9, 600 * 10**9          # book = latest record with ts <= t - 60 s, no older than 10 min before that
MAX_SPREAD = 0.005                                     # ask/bid - 1 above 50 bp is unusable
TICK = {"ZN": 1 / 64, "ZB": 1 / 32}


# ------------------------------------------------------------------ book
class Book:
    def __init__(self, ts_ns, iid, bid, ask):
        o = np.argsort(ts_ns, kind="stable")
        self.ts, self.iid, self.bid, self.ask = ts_ns[o], iid[o], bid[o], ask[o]

    def at(self, t_ns):
        """(bid, ask, iid) for each target time, NaN/-1 where missing or unusable."""
        t = np.asarray(t_ns, dtype="int64") - LAG_NS
        i = np.searchsorted(self.ts, t, side="right") - 1
        ok = i >= 0
        j = np.where(ok, i, 0)
        ok &= (t - self.ts[j]) <= MAXAGE_NS
        b, a = self.bid[j], self.ask[j]
        ok &= (b > 0) & (a > b) & (a / np.where(b > 0, b, 1) - 1 <= MAX_SPREAD)
        return np.where(ok, b, np.nan), np.where(ok, a, np.nan), np.where(ok, self.iid[j], -1)


def load_book(sym):
    p = os.path.join(TD, f"{sym}_v_0.csv")
    hdr = pd.read_csv(p, nrows=0).columns
    tcol = "ts_recv" if "ts_recv" in hdr else "ts_event"
    df = pd.read_csv(p, usecols=[tcol, "instrument_id", "bid_px_00", "ask_px_00"])
    ts = pd.to_datetime(df[tcol], utc=True).astype("int64").to_numpy()
    return Book(ts, df["instrument_id"].to_numpy("int64"), df["bid_px_00"].to_numpy(float), df["ask_px_00"].to_numpy(float))


# ------------------------------------------------------------------ events
def parse_close(s):
    """'01:00 PM' -> (13, 0); blank -> (13, 0). Minute precision (FLOWS-17 s.2)."""
    if not isinstance(s, str) or not s.strip():
        return (13, 0)
    hm, ap = s.strip().split()
    h, m = (int(x) for x in hm.split(":"))
    if ap.upper() == "PM" and h != 12: h += 12
    if ap.upper() == "AM" and h == 12: h = 0
    return (h, m)


def load_events(path=None):
    if path is None:
        C.check_pin("AUCTION_EVENTS"); path = os.path.join(C.FDATA, "auction_events.csv")
    ev = pd.read_csv(path, parse_dates=["date"])
    ev = ev[(ev["date"] >= START) & (ev["date"] <= END)]
    return ev


def auction_days(ev):
    g = ev.sort_values("years").groupby("date").agg(years=("years", "max"), close=("close_competitive", "first"))
    return g


def ny(d, hm):
    return pd.Timestamp(d.year, d.month, d.day, hm[0], hm[1], tz=C.NY).tz_convert("UTC").value


def comm_bp(mid):
    return COMM_USD / (mid * MULT) * 1e4


def era(d):
    for n, a, b in ERAS:
        if pd.Timestamp(a) <= d <= pd.Timestamp(b): return n
    return ""


# ------------------------------------------------------------------ part A / B
def intraday(book, days, closes):
    """One row per day: pre, post, R (bp), netA, netB, spread at T-3h; NaN rows dropped and counted."""
    T = np.array([ny(d, hm) for d, hm in zip(days, closes)], dtype="int64")
    H3 = 3 * 3600 * 10**9
    b0, a0, i0 = book.at(T - H3); b1, a1, i1 = book.at(T); b2, a2, i2 = book.at(T + H3)
    m0, m1, m2 = (b0 + a0) / 2, (b1 + a1) / 2, (b2 + a2) / 2
    valid = np.isfinite(m0) & np.isfinite(m1) & np.isfinite(m2)
    sameid = (i0 == i1) & (i1 == i2)
    cm = comm_bp(m1)
    df = pd.DataFrame({
        "pre": (m1 / m0 - 1) * 1e4, "post": (m2 / m1 - 1) * 1e4,
        "netA": ((1 - a1 / b0) + (b2 / a1 - 1)) * 1e4 - 4 * cm,
        "netB": (1 - a1 / b0) * 1e4 - 2 * cm,
        "spread_bp": (a0 / b0 - 1) * 1e4, "spread_px": a0 - b0, "mid": m1}, index=pd.DatetimeIndex(days))
    df["R"] = df["post"] - df["pre"]
    skipped = {"missing book": int((~valid).sum()), "roll inside window": int((valid & ~sameid).sum())}
    return df[valid & sameid], skipped


# ------------------------------------------------------------------ part C
def sessions_1500(book, d0, d1):
    days = pd.bdate_range(d0, d1)
    b, a, i = book.at(np.array([ny(d, (15, 0)) for d in days], dtype="int64"))
    ok = np.isfinite(b)
    return pd.DatetimeIndex(days[ok]), dict(zip(days[ok], zip(b[ok], a[ok], i[ok])))


def multiday(book, days, closes, sess, s15, k=5):
    """C legs per event; non-overlap rule: an event whose pre-entry is on/before the previous used exit is skipped."""
    rows, skip, last_exit = [], {"no 5 sessions / missing book": 0, "roll inside a leg": 0, "overlap": 0}, None
    for d, hm in zip(days, closes):
        p = sess.searchsorted(d)                       # first session >= d
        if p - k < 0:
            skip["no 5 sessions / missing book"] += 1; continue
        entry = sess[p - k]
        q = p + (1 if (p < len(sess) and sess[p] == d) else 0)
        if q + k - 1 >= len(sess):
            skip["no 5 sessions / missing book"] += 1; continue
        exit_ = sess[q + k - 1]
        if last_exit is not None and entry <= last_exit:
            skip["overlap"] += 1; continue
        bT, aT, iT = (x[0] for x in book.at(np.array([ny(d, hm)], dtype="int64")))
        if not np.isfinite(bT):
            skip["no 5 sessions / missing book"] += 1; continue
        be, ae, ie = s15[entry]; bx, ax, ix = s15[exit_]
        if not (ie == iT == ix):
            skip["roll inside a leg"] += 1; continue
        me, mT, mx = (be + ae) / 2, (bT + aT) / 2, (bx + ax) / 2
        cm = comm_bp(mT)
        rows.append(dict(date=d, entry=entry, exit=exit_,
                         gross=(-(mT / me - 1) + (mx / mT - 1)) * 1e4,
                         net=((1 - aT / be) + (bx / aT - 1)) * 1e4 - 4 * cm))
        last_exit = exit_
    return pd.DataFrame(rows).set_index("date") if rows else pd.DataFrame(columns=["gross", "net"]), skip


# ------------------------------------------------------------------ stats
def nw_mean(x, lags=5):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    b, se, t, n = C.ols_nw(x, np.ones((len(x), 1)), lags)
    return float(b[0]), float(t[0]), int(n)


def by_era(s):
    return {n: (float(s[(s.index >= a) & (s.index <= b)].mean()) if ((s.index >= a) & (s.index <= b)).any() else float("nan"))
            for n, a, b in ERAS}


# ------------------------------------------------------------------ run
def check_inputs():
    print(f"prereg {C.check_pin(NAME)[:16]} OK; auctions {C.check_pin('AUCTION_EVENTS')[:16]} OK")
    meta = json.load(open(os.path.join(TD, "tsyfut.meta.json")))
    for f, m in meta["files"].items():
        p = os.path.join(TD, f)
        import hashlib
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for blk in iter(lambda: fh.read(1 << 20), b""): h.update(blk)
        ok = h.hexdigest() == m["sha256"]
        hdr = list(pd.read_csv(p, nrows=0).columns)
        print(f"  {f}: sha {'OK' if ok else 'MISMATCH'}; columns {hdr}")
        if not ok: raise SystemExit("STOP: data file changed since fetch")
    for sym in ("ZN", "ZB"):
        bk = load_book(sym)
        t = pd.to_datetime(bk.ts[[0, -1]], utc=True)
        print(f"  {sym}: {len(bk.ts):,} records, {t[0]} -> {t[1]}, {len(np.unique(bk.iid))} contracts")
    ev = load_events(); g = auction_days(ev)
    print(f"  auction days in sample {len(g)}; 10-year auctions {int(((ev['years'] > 9.5) & (ev['years'] <= 10)).sum())}; 30-year {int((ev['years'] > 29.5).sum())}")
    print("  no returns computed.")
    return 0


def run():
    buf = io.StringIO()
    def say(*a):
        print(*a); print(*a, file=buf)
    pin, tpin = C.check_pin(NAME), C.check_pin("AUCTION_EVENTS")
    say(f"FLOWS-17 TSYFUT v{VERSION}  prereg {pin[:16]}  auctions {tpin[:16]}")
    say("Measurement, not a recommendation. Not financial advice.\n")
    ev = load_events(); g = auction_days(ev)
    zn, zb = load_book("ZN"), load_book("ZB")
    closes = [parse_close(c) for c in g["close"]]
    res = {}

    # ---- A
    A, skA = intraday(zn, g.index, closes)
    mR, tR, nR = nw_mean(A["R"]); mpre, _, _ = nw_mean(A["pre"]); mpost, _, _ = nw_mean(A["post"])
    eR = by_era(A["R"]); mN, tN, _ = nw_mean(A["netA"]); eN = by_era(A["netA"])
    wk = pd.bdate_range(START, END); plc = wk[~wk.isin(g.index)]
    P, skP = intraday(zn, plc, [(13, 0)] * len(plc))
    mP, tP, nP = nw_mean(P["R"])
    G1 = mR > 0 and tR >= 2.0
    G2 = all(eR[e] > 0 for e in eR) and eR["E3"] >= 0.5 * mR
    G3 = mpre < 0 and mpost > 0
    G4 = mN > 0 and tN >= TSTAT and eN["E3"] > 0
    G5 = tP < 2.0 and mP < mR
    say(f"PART A  ZN, all auction days (n {nR}; skipped {skA})")
    say(f"  R = POST - PRE   {mR:+.3f} bp  t {tR:+.2f}   eras " + " / ".join(f"{e} {v:+.2f}" for e, v in eR.items()) + f"   G1 {'PASS' if G1 else 'FAIL'}  G2 {'PASS' if G2 else 'FAIL'}")
    say(f"  PRE {mpre:+.3f}  POST {mpost:+.3f}   G3 {'PASS' if G3 else 'FAIL'}")
    say(f"  trade net {mN:+.3f} bp  t {tN:+.2f}  E3 {eN['E3']:+.3f}   G4 {'PASS' if G4 else 'FAIL'} (t >= {TSTAT})")
    say(f"  placebo (non-auction weekdays, n {nP}) R {mP:+.3f}  t {tP:+.2f}   G5 {'PASS' if G5 else 'FAIL'}")
    vA = G1 and G2 and G3 and G4 and G5
    say(f"  VERDICT A: {'PASS' if vA else 'FAIL'}" + ("" if vA else "  (" + " ".join(k for k, v in zip(('G1', 'G2', 'G3', 'G4', 'G5'), (G1, G2, G3, G4, G5)) if not v) + " failed)"))
    res["A"] = dict(R=mR, tR=tR, eras=eR, pre=mpre, post=mpost, net=mN, tnet=tN, net_eras=eN, placebo=mP, tplacebo=tP,
                    G=[G1, G2, G3, G4, G5], verdict=vA, n=nR, skipped=skA)

    # ---- B
    mB, tB, _ = nw_mean(A["netB"]); eB = by_era(A["netB"])
    B1 = mB > 0 and tB >= TSTAT; B2 = eB["E3"] > 0
    say(f"\nPART B  pre-auction short only: net {mB:+.3f} bp  t {tB:+.2f}  E3 {eB['E3']:+.3f}   B1 {'PASS' if B1 else 'FAIL'}  B2 {'PASS' if B2 else 'FAIL'}")
    say(f"  VERDICT B: {'PASS' if (B1 and B2) else 'FAIL'}")
    res["B"] = dict(net=mB, tnet=tB, net_eras=eB, verdict=B1 and B2)

    # ---- C
    sess, s15 = sessions_1500(zn, START - pd.Timedelta(days=14), END + pd.Timedelta(days=14))
    e10 = ev[(ev["years"] > 9.5) & (ev["years"] <= 10)].sort_values("date")      # new issues and reopenings (9-Year 10/11-Month)
    Cdf, skC = multiday(zn, list(e10["date"]), [parse_close(c) for c in e10["close_competitive"]], sess, s15)
    mCn, tCn, nC = C.mean_t(Cdf["net"]); mCg, tCg, _ = C.mean_t(Cdf["gross"])
    eCn, eCg = by_era(Cdf["net"]), by_era(Cdf["gross"])
    C1 = mCn > 0 and tCn >= TSTAT; C2 = eCn["E3"] > 0 and eCg["E3"] >= 0.5 * mCg
    say(f"\nPART C  10-year auctions, 5 sessions either side, ZN (n {nC}; skipped {skC})")
    say(f"  gross {mCg:+.2f} bp (t {tCg:+.2f})   net {mCn:+.2f} bp (t {tCn:+.2f})   E3 net {eCn['E3']:+.2f}, E3 gross {eCg['E3']:+.2f}")
    say(f"  C1 {'PASS' if C1 else 'FAIL'}  C2 {'PASS' if C2 else 'FAIL'}   VERDICT C: {'PASS' if (C1 and C2) else 'FAIL'}")
    res["C"] = dict(gross=mCg, net=mCn, tnet=tCn, n=nC, net_eras=eCn, gross_eras=eCg, verdict=C1 and C2, skipped=skC)

    v = vA or (B1 and B2) or (C1 and C2)
    say(f"\nOVERALL: {'TRADEABLE ON FUTURES (see which part)' if v else 'NOT TRADEABLE ON FUTURES at this cost'}")

    # ---- reported
    say("\nREPORTED (gating nothing)")
    e30 = g[g["years"] > 29.5]
    Z, skZ = intraday(zb, e30.index, [parse_close(c) for c in e30["close"]])
    if len(Z):
        a, t, n = nw_mean(Z["R"]); b, tb, _ = nw_mean(Z["netA"])
        say(f"  ZB, 30-year auction days (n {n}): R {a:+.2f} bp (t {t:+.2f}); trade net {b:+.2f} (t {tb:+.2f})")
    s30, sb15 = sessions_1500(zb, START - pd.Timedelta(days=14), END + pd.Timedelta(days=14))
    v30 = ev[ev["years"] > 29.5].sort_values("date")
    Cz, _ = multiday(zb, list(v30["date"]), [parse_close(c) for c in v30["close_competitive"]], s30, sb15)
    if len(Cz):
        a, t, n = C.mean_t(Cz["net"]); b, _, _ = C.mean_t(Cz["gross"])
        say(f"  ZB, 30-year auctions, C-style legs (n {n}): gross {b:+.2f}, net {a:+.2f} (t {t:+.2f})")
    tenor = g.loc[A.index, "years"]
    say("  A by longest tenor: " + ", ".join(f"{int(y)}y {A['R'][tenor == y].mean():+.2f} (n {(tenor == y).sum()})" for y in sorted(tenor.unique())))
    post = A[A.index >= ROBECO]; cpost = Cdf[Cdf.index >= ROBECO] if len(Cdf) else Cdf
    say(f"  post-Robeco 2025-04 -> 2026-08: A R {post['R'].mean():+.2f} (n {len(post)}), A net {post['netA'].mean():+.2f}, B net {post['netB'].mean():+.2f}; C net {cpost['net'].mean() if len(cpost) else float('nan'):+.2f} (n {len(cpost)})")
    say(f"  ZN entry spread: median {A['spread_px'].median() / TICK['ZN']:.2f} ticks = {A['spread_bp'].median():.2f} bp; commission {comm_bp(A['mid'].median()):.2f} bp per side")
    anchors = []
    for d in e10["date"]:
        p = sess.searchsorted(d)
        if p + 10 < len(sess): anchors.append(sess[p + 10])
    Cp, _ = multiday(zn, anchors, [(13, 0)] * len(anchors), sess, s15)
    if len(Cp):
        a, t, n = C.mean_t(Cp["net"]); b, tb, _ = C.mean_t(Cp["gross"])
        say(f"  C placebo (anchors 10 sessions after each 10-year auction, n {n}): gross {b:+.2f} (t {tb:+.2f}), net {a:+.2f}")
    say(f"  ZN notional at the median event: ${A['mid'].median() * MULT:,.0f} per contract")

    open(os.path.join(C.FDATA, "tsyfut_run.log"), "w").write(buf.getvalue())
    json.dump(res, open(os.path.join(C.FDATA, "tsyfut_result.json"), "w"), indent=1, default=float)
    return 0


# ------------------------------------------------------------------ self-test
def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"tsyfut.py v{VERSION} self-test (synthetic books)\n")
    check("close parsing: 01:00 PM, 11:30 AM, blank", parse_close("01:00 PM") == (13, 0) and parse_close("11:30 AM") == (11, 30) and parse_close(float("nan")) == (13, 0))
    # a minute book over 60 weekdays, auction every 5th day with a planted inverted V of 4 bp each side
    rng = np.random.default_rng(16)
    days = pd.bdate_range("2021-03-01", periods=60)
    auc = days[::5]
    ts, bid, ask, iid = [], [], [], []
    for d in days:
        base = 110.0 + rng.normal(0, 0.01)
        for mm in range(8 * 60, 18 * 60):
            t = pd.Timestamp(d.year, d.month, d.day, mm // 60, mm % 60, tz=C.NY).tz_convert("UTC").value
            p = base
            if d in auc:
                if 10 * 60 <= mm < 13 * 60: p = base * (1 - 4e-4 * (mm - 600) / 180)
                elif mm >= 13 * 60: p = base * (1 - 4e-4 + 4e-4 * min(1, (mm - 780) / 180))
            ts.append(t); bid.append(p - TICK["ZN"] / 2); ask.append(p + TICK["ZN"] / 2); iid.append(1 if d < days[40] else 2)
    bk = Book(np.array(ts, "int64"), np.array(iid, "int64"), np.array(bid), np.array(ask))
    A, sk = intraday(bk, auc, [(13, 0)] * len(auc))
    check("PLANTED inverted V: PRE ~ -4 bp, POST ~ +4 bp, R ~ +8 bp", abs(A["pre"].mean() + 4) < 0.3 and abs(A["post"].mean() - 4) < 0.3 and abs(A["R"].mean() - 8) < 0.5)
    exp = 8 - 2 * (TICK["ZN"] / 110 * 1e4) - 4 * comm_bp(110)
    check(f"trade net = gross - two full spreads - 4 commissions (~{exp:.2f} bp)", abs(A["netA"].mean() - exp) < 0.5)
    t = ny(days[0], (13, 0))
    b, a, _ = bk.at(np.array([t]))
    rec = bk.ts[np.searchsorted(bk.ts, t - LAG_NS, side="right") - 1]
    check("look-ahead guard: the book at 13:00 comes from a record stamped <= 12:59", rec <= t - LAG_NS)
    b, a, _ = bk.at(np.array([ny(days[0], (3, 0))]))
    check("no record within 10 minutes -> missing, not a stale price", np.isnan(b[0]))
    roll = days[40]
    Aroll, skr = intraday(bk, pd.DatetimeIndex([days[39], roll]), [(13, 0)] * 2)
    check("a window on one contract is kept", len(Aroll) == 2 and skr["roll inside window"] == 0)
    sess, s15 = sessions_1500(bk, days[0], days[-1])
    Cdf, skC = multiday(bk, list(days[10:31:10]), [(13, 0)] * 3, sess, s15)
    check("C: 5th session before and after are used", len(Cdf) >= 1 and (Cdf["entry"].iloc[0] == sess[sess.searchsorted(days[10]) - 5])
          and (Cdf["exit"].iloc[0] == sess[sess.searchsorted(days[10]) + 5]))
    Cr, skr2 = multiday(bk, [days[38]], [(13, 0)], sess, s15)
    check("C: a leg across a contract roll is skipped and counted", len(Cr) == 0 and skr2["roll inside a leg"] == 1)
    Co, sko = multiday(bk, [days[10], days[13]], [(13, 0)] * 2, sess, s15)
    check("C: overlapping events -> the later one is skipped", len(Co) == 1 and sko["overlap"] == 1)
    x = np.r_[np.ones(50), -np.ones(50)] + 0.0
    check("nw_mean of a symmetric series is ~0", abs(nw_mean(x)[0]) < 1e-12)
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--self-test" in a: sys.exit(self_test())
    if "--check-inputs" in a: sys.exit(check_inputs())
    if "--run" in a: sys.exit(run())
    print(__doc__); sys.exit(2)
