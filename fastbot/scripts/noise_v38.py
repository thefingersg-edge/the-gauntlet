#!/usr/bin/env python3
"""PREREGISTRATION_v38 -- the frozen v36 noise-band rule on five index CFDs
this project has never tested it on, each in its own cash session.

A  UK100 DE30 EU50 JP225 AU200, OANDA 5m bid/ask (data/v38).
   G1 gross replication, G2 net of the quoted spread.
B  (reported, reuses seen years) v36 rule on SPX/NAS/US30 only on days after
   the VIX futures curve was inverted (VX1 > VX2 at the prior close).
C  (reported) volatility-scaled size for A: risk / trailing 20-day sigma.
Gate 0: the generalised rule, run on SPX500 with the US session, must
reproduce momentum_v36.noise_rows() exactly.
"""
from __future__ import annotations
import argparse, csv, datetime as dt, hashlib, math, os, statistics as st, sys
from zoneinfo import ZoneInfo
import numpy as np

from reactive import net_open_to_close, gross_open_to_close
from timeline_v37 import cl_t

VERSION = "1.0"
DOC = ("PREREGISTRATION_v38.md", "9311b00c51d0682627e1e4bdbbdacd517505a617b404cd7debd0db894d1c8cd3")
SESS = {  # stem: (tz, open, close) -- cash sessions, local time
    "uk100gbp": ("Europe/London", "08:00", "16:30"),
    "de30eur": ("Europe/Berlin", "09:00", "17:30"),
    "eu50eur": ("Europe/Berlin", "09:00", "17:30"),
    "jp225usd": ("Asia/Tokyo", "09:00", "15:00"),
    "au200aud": ("Australia/Sydney", "10:00", "16:00"),
    "spx500usd": ("America/New_York", "09:30", "16:00"),
}
LOOKBACK, END = 14, dt.date(2026, 9, 25)
ERAS = ((2013, 2017), (2018, 2021), (2022, 2026))
T_GATE, T_REPL = 2.0, 1.64


def mins(hm): return int(hm[:2]) * 60 + int(hm[3:])
def hmf(m): return f"{m // 60:02d}:{m % 60:02d}"


def plan(stem):
    tz, o, c = SESS[stem]
    O, C = mins(o), mins(c)
    bars = [hmf(m) for m in range(O, C, 5)]
    checks = tuple(hmf(m - 5) for m in range(O + 30, C, 30))      # bars CLOSING at open+30 .. close-30
    return tz, bars, checks


def load(data_dir, stem):
    tz, want, _ = plan(stem)
    Z = ZoneInfo(tz); wantset = set(want)
    ask = {}
    with open(os.path.join(data_dir, f"{stem}_ask_5m.csv")) as fh:
        rd = csv.reader(fh); next(rd)
        for r in rd:
            ask[r[0]] = tuple(float(x) for x in r[1:5])
    days, off = {}, {}
    with open(os.path.join(data_dir, f"{stem}_bid_5m.csv")) as fh:
        rd = csv.reader(fh); next(rd)
        for r in rd:
            if r[0] not in ask:
                continue
            u = dt.datetime.fromisoformat(r[0])
            k = (u.date(), u.hour)
            if k not in off:
                off[k] = u.replace(tzinfo=dt.timezone.utc).astimezone(Z).utcoffset()
            e = u + off[k]
            hm = e.strftime("%H:%M")
            if hm not in wantset:
                continue
            b = tuple(float(x) for x in r[1:5]); a = ask[r[0]]
            m = tuple((b[i] + a[i]) / 2 for i in range(4))
            days.setdefault(e.date(), {})[hm] = m + (b[0], a[0], b[3], a[3])
    need = int(0.9 * len(want))
    return {d: v for d, v in days.items() if len(v) >= need and d <= END}


def twap(bars, upto):
    xs = [(v[1] + v[2] + v[3]) / 3 for k, v in bars.items() if k <= upto]
    return sum(xs) / len(xs) if xs else None


def as_close(bar):
    return (bar[0], bar[1], bar[2], bar[0], bar[4], bar[5], bar[4], bar[5])


def day_trades(bars, prev_close, sig, first, last, checks):
    op = bars[first][0]; ur, dr = max(op, prev_close), min(op, prev_close)
    side, ent, out = 0, None, []
    for k in checks:
        nxt = hmf(mins(k) + 5)
        if k not in bars or nxt not in bars or sig.get(k) is None:
            continue
        c = bars[k][3]; U, L = ur * (1 + sig[k]), dr * (1 - sig[k]); vw = twap(bars, k)
        if side == 1 and c < max(U, vw):
            out.append((1, gross_open_to_close(ent, as_close(bars[nxt]), 1), net_open_to_close(ent, as_close(bars[nxt]), 1))); side = 0
        elif side == -1 and c > min(L, vw):
            out.append((-1, gross_open_to_close(ent, as_close(bars[nxt]), -1), net_open_to_close(ent, as_close(bars[nxt]), -1))); side = 0
        if side == 0:
            if c > U: side, ent = 1, bars[nxt]
            elif c < L: side, ent = -1, bars[nxt]
    if side:
        out.append((side, gross_open_to_close(ent, bars[last], side), net_open_to_close(ent, bars[last], side)))
    return out


def rows_for(days, stem):
    tz, want, checks = plan(stem)
    first, last = want[0], want[-1]
    ds, hist, out = sorted(days), [], []
    closes = []
    for i in range(1, len(ds)):
        d, bars, prev = ds[i], days[ds[i]], days[ds[i - 1]]
        mv = {k: abs(bars[k][3] / bars[first][0] - 1) for k in checks if k in bars} if first in bars else {}
        if len(hist) >= LOOKBACK and last in prev and first in bars and last in bars:
            sig = {}
            for k in checks:
                xs = [h[k] for h in hist[-LOOKBACK:] if k in h]
                sig[k] = st.mean(xs) if len(xs) >= 10 else None
            tr = day_trades(bars, prev[last][3], sig, first, last, checks)
            if tr:
                sd20 = st.pstdev(closes[-20:]) if len(closes) >= 20 else None
                out.append(dict(ins=stem, date=d, n=len(tr), g=sum(x[1] for x in tr), net=sum(x[2] for x in tr),
                                spread=st.median([(bars[k][5] / bars[k][4] - 1) * 1e4 for k in checks if k in bars]),
                                sd20=sd20))
        if last in bars and last in prev:
            closes.append(bars[last][3] / prev[last][3] - 1)
        if mv:
            hist.append(mv)
    return out


def gate(rows, key, from_date):
    hs = [r for r in rows if r["date"] >= from_date]
    dd = np.array([r["date"].isoformat() for r in hs]); x = np.array([r[key] for r in hs])
    mu, t = cl_t(dd, x)
    eras = []
    for lo, hi in ERAS:
        m = np.array([lo <= r["date"].year <= hi for r in hs])
        eras.append(x[m].mean() if m.sum() else float("nan"))
    m = np.array([r["date"].year not in (2020, 2021) for r in hs])
    mux, tx = cl_t(dd[m], x[m])
    ok = mu > 0 and t >= T_GATE and all(e > 0 for e in eras) and mux > 0 and tx >= T_REPL
    return mu, t, len(x), eras, (mux, tx), ok


def self_test(here):
    ok = True
    def check(n, c, d=""):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n} {d}")
    print(f"noise_v38.py v{VERSION} self-test\n")
    tz, want, checks = plan("spx500usd")
    import momentum_v36 as M
    check("US plan reproduces v36's checkpoints", checks == M.CHECKS, f"{checks[0]}..{checks[-1]}")
    tz, want, checks = plan("uk100gbp")
    check("UK: bars 08:00..16:25, checkpoints close 08:30..16:00", want[0] == "08:00" and want[-1] == "16:25"
          and checks[0] == "08:25" and checks[-1] == "15:55")
    tz, want, checks = plan("jp225usd")
    check("Japan: checkpoints close 09:30..14:30", checks[0] == "09:25" and checks[-1] == "14:25")
    # GATE 0 -- generalised rule on SPX must equal momentum_v36 exactly
    from reactive import load as rload
    days = rload(os.path.join(here, "../data"), "spx500usd")
    a = {r["date"]: (r["n"], r["Ng"], r["Nn"]) for r in M.noise_rows(days, "spx500usd")}
    b = {r["date"]: (r["n"], r["g"], r["net"]) for r in rows_for({d: v for d, v in days.items() if d <= END}, "spx500usd")}
    common = set(a) & set(b)
    worst = max(max(abs(a[d][1] - b[d][1]), abs(a[d][2] - b[d][2])) for d in common)
    check("GATE 0: generalised rule reproduces v36 N on SPX, day by day", len(common) > 3000 and worst < 1e-9
          and all(a[d][0] == b[d][0] for d in common) and set(a) == set(b), f"{len(common)} days, max diff {worst:.1e}")
    rng = np.random.default_rng(3)
    fake = [dict(date=dt.date(2013, 1, 1) + dt.timedelta(days=i), g=float(rng.normal(0, 50))) for i in range(4000)]
    check("PLANTED FAIL: noise does not pass the gate", not gate(fake, "g", dt.date(2013, 1, 1))[5])
    for r in fake: r["g"] += 5
    check("a planted +5 bp/day passes", gate(fake, "g", dt.date(2013, 1, 1))[5])
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--self-test", action="store_true"); ap.add_argument("--budget", action="store_true")
    a = ap.parse_args(); here = os.path.dirname(os.path.abspath(__file__))
    if a.self_test:
        sys.exit(self_test(here))
    print(f"noise_v38.py v{VERSION}   PREREGISTRATION_v38\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    if not a.budget:
        got = hashlib.sha256(open(os.path.join(here, "..", DOC[0]), "rb").read()).hexdigest()
        if got != DOC[1]:
            print("  PREREGISTRATION_v38.md changed since frozen. Refused."); sys.exit(2)
    allrows = []
    for stem in ("uk100gbp", "de30eur", "eu50eur", "jp225usd", "au200aud"):
        days = load(os.path.join(here, "../data/v38"), stem)
        rr = rows_for(days, stem)
        real = [r for r in rr if r["spread"] > 0]
        start = max(dt.date(2013, 1, 1), min(r["date"] for r in real)) if real else None
        for r in rr:
            r["gated"] = start is not None and r["date"] >= start
        allrows += rr
        print(f"  {stem:<9} {len(days):>5} sessions  {len(rr):>5} trade-days  real spreads from {start}")
    G = [r for r in allrows if r["gated"]]
    if a.budget:
        rms = math.sqrt(st.mean(r["g"] ** 2 for r in G)); nd = len({r["date"] for r in G})
        cost = st.mean(r["g"] - r["net"] for r in G)
        print(f"\n  BUDGET (gated days; RMS and cost only): {len(G):,} instrument-days on {nd:,} dates, RMS {rms:.1f} bp,"
              f" cost {cost:.2f} bp/day, trades/day {st.mean(r['n'] for r in G):.2f}, MDE ~ {(T_GATE + .84) * rms / math.sqrt(nd):.2f} bp/day")
        for stem in SESS:
            rs = [r for r in G if r["ins"] == stem]
            if rs:
                print(f"    {stem:<9} days {len(rs):>5}  cost {st.mean(r['g'] - r['net'] for r in rs):.2f} bp/day")
        return
    print("\n  A. five new indices, pooled, per instrument-day (t clustered by date)")
    for key, nm in (("g", "G1 GROSS"), ("net", "G2 NET")):
        mu, t, n, eras, ex, ok = gate(G, key, dt.date(2013, 1, 1))
        print(f"    {nm:<9} {mu:+.2f} bp/day  t {t:+.2f}  n {n}   eras " + " ".join(f"{e:+.2f}" for e in eras)
              + f"   ex-2020/21 {ex[0]:+.2f} (t {ex[1]:+.2f})  -> {'PASS' if ok else 'FAIL'}")
    for stem in ("uk100gbp", "de30eur", "eu50eur", "jp225usd", "au200aud"):
        rs = [r for r in G if r["ins"] == stem]
        dd = np.array([r["date"].isoformat() for r in rs])
        mg, tg = cl_t(dd, np.array([r["g"] for r in rs])); mn, tn = cl_t(dd, np.array([r["net"] for r in rs]))
        print(f"      {stem:<9} gross {mg:+.2f} (t {tg:+.2f})  net {mn:+.2f} (t {tn:+.2f})  n {len(rs)}")
    # C: vol sizing (reported)
    V = [r for r in G if r["sd20"]]
    med = st.median(r["sd20"] for r in V)
    eq = np.array([r["net"] for r in V]); vs = np.array([r["net"] * min(3.0, med / r["sd20"]) for r in V])
    def sharpe(x): return x.mean() / x.std() * math.sqrt(252)
    def mdd(x):
        c = np.cumsum(x); return float((np.maximum.accumulate(c) - c).max())
    print(f"\n  C. (reported) sizing, net: equal size Sharpe {sharpe(eq):+.2f} maxDD {mdd(eq):.0f} bp   "
          f"vol-scaled Sharpe {sharpe(vs):+.2f} maxDD {mdd(vs):.0f} bp")
    # B: US three, VIX-curve inverted days (reported)
    import momentum_v36 as M
    from reactive import load as rload
    from zoneinfo import ZoneInfo as Z
    def tv(fn):
        out = {}
        for r in list(csv.reader(open(os.path.join(here, "../data", fn))))[1:]:
            ch = dt.datetime.fromtimestamp(int(r[0]), Z("America/Chicago"))
            out[ch.date() + (dt.timedelta(days=1) if ch.hour >= 16 else dt.timedelta(0))] = float(r[4])
        return out
    v1, v2 = tv("CBOE_DLY_VX1!, 1D_1f2b8.csv"), tv("CBOE_DLY_VX2!, 1D_7782c.csv")
    vd = sorted(set(v1) & set(v2))
    import bisect
    def inverted(d):
        i = bisect.bisect_left(vd, d) - 1
        return i >= 0 and (d - vd[i]).days <= 5 and v1[vd[i]] > v2[vd[i]]
    US = []
    for ins in M.INSTR:
        US += [r for r in M.noise_rows(rload(os.path.join(here, "../data"), ins), ins) if r["date"] >= dt.date(2013, 1, 1)]
    for lab, sel in (("inverted-curve days", [r for r in US if inverted(r["date"])]), ("other days", [r for r in US if not inverted(r["date"])])):
        dd = np.array([r["date"].isoformat() for r in sel])
        mg, tg = cl_t(dd, np.array([r["Ng"] for r in sel])); mn, tn = cl_t(dd, np.array([r["Nn"] for r in sel]))
        print(f"  B. (reported) US three, {lab:<20} n {len(sel):>5}  gross {mg:+.2f} (t {tg:+.2f})  net {mn:+.2f} (t {tn:+.2f})")


if __name__ == "__main__":
    main()
