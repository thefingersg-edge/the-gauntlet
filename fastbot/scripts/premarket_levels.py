#!/usr/bin/env python3
"""PREREGISTRATION_v33 -- two lenses from the TradingView survey.

A. LEVEL MAGNETS. Is the release fade heading back to a price level the
   market marked out before 08:30? Three levels, all from bars that
   closed before the release:
       VWAP  overnight volume-weighted price, 18:00 ET (prior day) -> 08:30
       POC   overnight volume point-of-control, 2 bp bins
       GAP   the 08:15 bar's extreme on the side the release move left
   D = distance from the 08:45 entry to the level, in bp, POSITIVE when
   the level lies in the direction the fade trades.
       fade = a + b*D + c*|move|        b > 0 is the magnet

B. RULE OF 16. Is the release move large or small against what the
   options market priced? I = prior-day VIX close x 6.25 bp (VIX/16 %).
       fade / I = a + b*(|move| / I)    b > 0: surprises to options fade more

Gates, samples and thresholds are frozen in PREREGISTRATION_v33.md, whose
sha256 is checked before any fade is computed.

    python3 premarket_levels.py --self-test
    python3 premarket_levels.py --budget      # regressors only, no fades
    python3 premarket_levels.py
"""

from __future__ import annotations

import argparse
import bisect
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
from premarket_factor import (read_marks, morning, regress, tstat, stem,
                              SIG, ENTRY, H0, FORWARD_START)

VERSION = "1.0"
DOC = ("PREREGISTRATION_v33.md", "a730ea5eb462c49ff5b0e527587e6c85c377012ed6b4f30d09af907b82401c59")

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
INSTR = ("SPX500_USD", "NAS100_USD", "US30_USD", "DE30_EUR",
         "EUR_USD", "XAU_USD")                       # v27's six, section 2
LEVELS = ("VWAP", "POC", "GAP")
BIN_BP = 2.0                                          # section 3
MIN_ON_BARS = 20                                      # section 3
T_GATE = 2.39                                         # section 5: 3 tests
GATED = ("VWAP", "POC")                               # section 4; GAP reported
T_REPL = 1.64                                         # section 5
EXCL_YEARS = (2020, 2021)                             # section 5
V27_FILE = "../data/horizon_v27_trades.csv"
VIX_FILE = "../data/VIXCLS.csv"
PATH_HM = ("08:45", "09:00", "09:15", "09:30")        # bars inside the hour

_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)


def _guard(names):
    bad = sorted(n for n in names if _FORBIDDEN.search(n))
    if bad:
        raise SystemExit(f"namespace guard: this file must not define {bad}")


# ---------------------------------------------------------------- data
_OFF = {}


def to_et(s):
    """'YYYY-mm-dd HH:MM:SS' UTC -> naive ET datetime (cached offsets)."""
    u = dt.datetime.fromisoformat(s)
    k = (u.date(), u.hour)
    if k not in _OFF:
        _OFF[k] = u.replace(tzinfo=UTC).astimezone(ET).utcoffset()
    return u + _OFF[k]


def session_of(e):
    """ET bar start -> (date whose 08:30 it precedes, 'ON') or (date, 'HM')."""
    t = e.time()
    if t >= dt.time(18, 0):
        return (e.date() + dt.timedelta(days=1), "ON")
    if t < dt.time(8, 30):
        return (e.date(), "ON")
    return (e.date(), e.strftime("%H:%M"))


def read_bars(pb, pa):
    """Mid bars grouped: on[d] = [(h,l,c,v)...] for the overnight before
    d's 08:30, mk[(d,'HH:MM')] = (o,h,l,c) for 08:15 and the hour after."""
    want = {"08:15"} | set(PATH_HM)
    ask = {}
    with open(pa, newline="") as fh:
        rd = csv.reader(fh)
        next(rd)
        for r in rd:
            h = int(r[0][11:13])
            if 15 <= h <= 21:
                continue
            ask[r[0]] = (float(r[1]), float(r[2]), float(r[3]), float(r[4]))
    on, mk = {}, {}
    with open(pb, newline="") as fh:
        rd = csv.reader(fh)
        next(rd)
        for r in rd:
            h = int(r[0][11:13])
            if 15 <= h <= 21 or r[0] not in ask:
                continue
            b = (float(r[1]), float(r[2]), float(r[3]), float(r[4]))
            a = ask[r[0]]
            o, hi, lo, c = ((b[i] + a[i]) / 2.0 for i in range(4))
            e = to_et(r[0])
            d, tag = session_of(e)
            if tag == "ON":
                if e.time() >= dt.time(8, 30) and e.time() < dt.time(18, 0):
                    continue
                on.setdefault(d, []).append((hi, lo, c, float(r[5]), e))
                if tag == "ON" and e.strftime("%H:%M") == "08:15":
                    mk[(d, "08:15")] = (o, hi, lo, c)
            elif tag in want:
                mk[(d, tag)] = (o, hi, lo, c)
    return on, mk


# -------------------------------------------------------------- levels
def vwap(bars):
    sv = sum(v for _, _, _, v, *_ in bars)
    if sv <= 0:
        return None
    return sum((h + l + c) / 3.0 * v for h, l, c, v, *_ in bars) / sv


def poc(bars, ref):
    """Volume spread evenly over each bar's range in BIN_BP bins around
    `ref`; the busiest bin's centre. Ties go to the bin nearest ref."""
    w = BIN_BP * 1e-4 * ref
    vol = {}
    for h, l, c, v, *_ in bars:
        if v <= 0:
            continue
        i0, i1 = math.floor((l - ref) / w), math.floor((h - ref) / w)
        n = i1 - i0 + 1
        for i in range(i0, i1 + 1):
            vol[i] = vol.get(i, 0.0) + v / n
    if not vol:
        return None
    top = max(vol.values())
    best = min((i for i, x in vol.items() if x == top),
               key=lambda i: (abs(i + 0.5), i))
    return ref + (best + 0.5) * w


def dist_bp(level, entry, direction):
    """Signed bp from entry to level; + when the level is where the fade goes."""
    return direction * (level / entry - 1.0) * 1e4


def levels_for(on_bars, bar0815, move_up, entry):
    if len(on_bars) < MIN_ON_BARS or bar0815 is None:
        return None
    direction = -1 if move_up else 1
    L = dict(VWAP=vwap(on_bars), POC=poc(on_bars, entry),
             GAP=bar0815[1] if move_up else bar0815[2])
    if any(v is None for v in L.values()):
        return None
    return {k: dist_bp(v, entry, direction) for k, v in L.items()}, L


# ----------------------------------------------------------------- VIX
def read_vix(path):
    out = []
    for r in csv.DictReader(open(path)):
        try:
            out.append((dt.date.fromisoformat(r["date"]), float(r["vix"])))
        except (ValueError, KeyError):
            continue
    out.sort()
    return out


def vix_before(series, d):
    """The last VIX close strictly BEFORE d -- the release is at 08:30,
    d's own close does not exist yet."""
    ds = [x for x, _ in series]
    i = bisect.bisect_left(ds, d) - 1
    return None if i < 0 else series[i][1]


# ---------------------------------------------------------------- gates
def fit(rows, ykey, xkeys):
    y = [r[ykey] for r in rows]
    X = [[1.0] + [r[k] for k in xkeys] for r in rows]
    beta, V = regress(y, X, [r["date"] for r in rows])
    return beta[1], tstat(beta, V, 1), len(rows)


def verdict(t_s1, b_s1, t_s2, b_s2, t_ex, b_ex):
    """Section 5: PASS needs all three. Anything less is not a finding."""
    main = b_s1 > 0 and t_s1 is not None and t_s1 >= T_GATE
    repl = b_s2 > 0 and t_s2 is not None and t_s2 >= T_REPL
    exc = b_ex > 0 and t_ex is not None and t_ex >= T_REPL
    if main and repl and exc:
        return "PASS"
    if main:
        return "S1 ONLY -- not a finding"
    return "FAIL"


_guard(list(globals()))


# ------------------------------------------------------------ self-test
def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, np.bool_)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"premarket_levels.py v{VERSION} self-test\n")
    E = dt.datetime(2020, 1, 1)
    bars = [(101.0, 99.0, 100.0, 1.0, E), (104.0, 102.0, 103.0, 3.0, E)]
    check("VWAP weights typical price by volume",
          abs(vwap(bars) - (100.0 * 1 + 103.0 * 3) / 4) < 1e-12)
    check("VWAP of zero volume is None", vwap([(1.0, 1.0, 1.0, 0.0, E)]) is None)
    #: PLANTED: one bar holding nearly all the volume must own the POC
    heavy = [(100.1, 100.1, 100.1, 1000.0, E), (101.0, 99.0, 100.0, 5.0, E)]
    p = poc(heavy, 100.0)
    check("a heavy bar owns the POC", abs(p - 100.1) < 100.0 * BIN_BP * 1e-4,
          f"POC {p:.4f}")
    check("the POC is NOT the VWAP (planted distinct)",
          abs(poc(bars, 100.0) - vwap(bars)) > 1e-6)
    check("up move, level below entry: D > 0 (short fade walks to it)",
          dist_bp(99.0, 100.0, -1) > 0)
    check("up move, level ABOVE entry: D < 0",
          dist_bp(101.0, 100.0, -1) < 0)
    check("down move, level above entry: D > 0", dist_bp(101.0, 100.0, 1) > 0)
    print("\nno look-ahead")
    check("the 08:30 bar is not overnight",
          session_of(dt.datetime(2020, 1, 2, 8, 30)) == (dt.date(2020, 1, 2), "08:30"))
    check("08:15 is overnight", session_of(dt.datetime(2020, 1, 2, 8, 15))[1] == "ON")
    check("18:00 belongs to the NEXT morning",
          session_of(dt.datetime(2020, 1, 1, 18, 0)) == (dt.date(2020, 1, 2), "ON"))
    vx = [(dt.date(2020, 1, 1), 15.0), (dt.date(2020, 1, 2), 999.0)]
    check("VIX is the prior day's close, never the same day's",
          vix_before(vx, dt.date(2020, 1, 2)) == 15.0)
    check("no VIX before the series starts", vix_before(vx, dt.date(2019, 1, 1)) is None)
    check("too few overnight bars drops the morning",
          levels_for(bars, (100, 101, 99, 100), True, 100.0) is None)
    print("\nthe gates can fail")
    rng = np.random.default_rng(7)
    rows = []
    for i in range(1500):
        D = float(rng.normal(0, 20))
        rows.append(dict(date=i // 3, D=D, m=abs(float(rng.normal(0, 30))),
                         y=0.3 * D + float(rng.normal(0, 30)),
                         z=float(rng.normal(0, 30))))
    b, t, _ = fit(rows, "y", ["D", "m"])
    check("a planted magnet (b = 0.3) is found", b > 0 and t >= T_GATE,
          f"b {b:+.3f} t {t:+.2f}")
    b0, t0, _ = fit(rows, "z", ["D", "m"])
    check("PLANTED FAIL: pure noise does not pass the gate",
          not (b0 > 0 and t0 >= T_GATE), f"b {b0:+.3f} t {t0:+.2f}")
    check("verdict: S1 passes, S2 fails -> not a finding",
          verdict(3.0, 0.3, 0.5, 0.1, 2.0, 0.2) != "PASS")
    check("verdict: S1 passes, ex-2020/21 fails -> not a finding",
          verdict(3.0, 0.3, 2.0, 0.1, 1.0, 0.2) != "PASS")
    check("verdict: negative b never passes", verdict(-3.0, -0.3, 2, 0.1, 2, 0.1) == "FAIL")
    check("verdict: all three -> PASS", verdict(3.0, 0.3, 2.0, 0.1, 2.0, 0.1) == "PASS")
    check("frozen constants", GATED == ("VWAP", "POC") and T_GATE == 2.39 and T_REPL == 1.64 and BIN_BP == 2.0
          and MIN_ON_BARS == 20 and FORWARD_START == dt.date(2026, 9, 18))
    check("no order/execute/submit/position name in this file",
          not [n for n in globals() if _FORBIDDEN.search(n)])
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


# ----------------------------------------------------------------- build
def build(data_dir, events, with_fade):
    pre, _ = load_events(events, from_year=1900)
    s1 = {d for d, e in pre.items() if {"CPI", "NFP"} & e}
    s2 = {d for d, e in pre.items() if "CLAIMS" in e} - s1
    vix = read_vix(os.path.join(os.path.dirname(__file__), VIX_FILE))
    out = []
    for ins in INSTR:
        pb = os.path.join(data_dir, f"{stem(ins)}_bid_15m.csv")
        pa = os.path.join(data_dir, f"{stem(ins)}_ask_15m.csv")
        b, a = read_marks(pb), read_marks(pa)
        on, mk = read_bars(pb, pa)
        n0 = len(out)
        for d in sorted({x for (x, hm) in b if hm == SIG}):
            if d >= FORWARD_START:
                continue
            got = morning(b, a, d)
            if got is None:
                continue
            m, y0, _ = got
            entry = (b[(d, ENTRY)][0] + a[(d, ENTRY)][0]) / 2.0
            lv = levels_for(on.get(d, []), mk.get((d, "08:15")), m > 0, entry)
            v = vix_before(vix, d)
            cls = "S1" if d in s1 else ("S2" if d in s2 else "S3")
            r = dict(cls=cls, ins=ins, date=d, m=abs(m), entry=entry,
                     up=m > 0, I=None if v is None else v * 6.25)
            if lv:
                r.update({f"D_{k}": x for k, x in lv[0].items()})
                r.update({f"L_{k}": x for k, x in lv[1].items()})
            if r["I"]:
                r["mI"] = r["m"] / r["I"]
            if with_fade:
                r["y"] = y0
                if r["I"]:
                    r["yI"] = y0 / r["I"]
                r["path"] = [mk.get((d, hm)) for hm in PATH_HM]
            out.append(r)
        print(f"  {ins:<12} {len(out) - n0:>6} mornings")
    return out


def budget(rows):
    """No fade is read here. SE scaled from v28's published slope SE."""
    se_m = 0.057 / 1.14                      # RESULT_FACTOR, S1 raw slope
    s1 = [r for r in rows if r["cls"] == "S1"]
    sd_m = st.stdev(r["m"] for r in s1)
    k = T_GATE + 0.84
    print(f"\n  POWER BUDGET (S1, no fades read)   SD|move| {sd_m:.1f} bp,"
          f" v28 slope SE {se_m:.3f}")
    for L in LEVELS:
        xs = [r[f"D_{L}"] for r in s1 if f"D_{L}" in r]
        sd = st.stdev(xs)
        rho = float(np.corrcoef(xs, [r["m"] for r in s1 if f"D_{L}" in r])[0, 1])
        mde = k * se_m * sd_m / sd / math.sqrt(1 - rho ** 2)
        print(f"    {L:<5} n {len(xs):>5}  SD(D) {sd:6.1f} rho(D,|move|) {rho:.2f}  median D "
              f"{st.median(xs):+6.1f}  share D>0 {sum(x > 0 for x in xs) / len(xs):.2f}"
              f"   MDE b ~ {mde:.3f}  (meaningful: 0.10)")
    xs = [r for r in s1 if "mI" in r]
    Imed = st.median(r["I"] for r in xs)
    sd = st.stdev(r["mI"] for r in xs)
    mde = k * se_m * sd_m / sd / Imed
    print(f"    R16   n {len(xs):>5}  median I {Imed:.0f} bp  SD(|move|/I) "
          f"{sd:.3f}   MDE b ~ {mde:.3f}  (meaningful: 0.10)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="../data/v24")
    ap.add_argument("--events", default="../data/events_v2.csv")
    ap.add_argument("--out", default="../data/levels_v33_trades.csv")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--budget", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    here = os.path.dirname(os.path.abspath(__file__))
    print(f"premarket_levels.py v{VERSION}   PREREGISTRATION_v33\n")
    print("  I am not a financial adviser. This is a measurement, not a")
    print("  recommendation to take a position.\n")
    if a.budget:
        budget(build(a.data_dir, a.events, with_fade=False))
        return
    got = hashlib.sha256(open(os.path.join(here, "..", DOC[0]), "rb").read()).hexdigest()
    if got != DOC[1]:
        print(f"  {DOC[0]} changed since it was frozen ({got[:12]}). Refused.")
        sys.exit(2)
    print(f"  {DOC[0]} sha256 {got[:16]}... matches the frozen copy\n")
    rows = build(a.data_dir, a.events, with_fade=True)

    # Gate 0
    v27 = {(r["instrument"], r["date"]): float(r["gross_H0"])
           for r in csv.DictReader(open(os.path.join(here, V27_FILE)))
           if r["gross_H0"]}
    diffs = [abs(r["y"] - v27[(r["ins"], r["date"].isoformat())])
             for r in rows if (r["ins"], r["date"].isoformat()) in v27]
    g0 = len(diffs) > 20000 and max(diffs) < 1e-6
    print(f"\n  GATE 0  {len(diffs):,} trades matched to v27, max |diff| "
          f"{max(diffs):.1e} bp  [{'PASS' if g0 else 'FAIL'}]")
    if not g0:
        sys.exit(3)
    with open(a.out, "w", newline="") as fh:
        w = csv.writer(fh)
        cols = ["cls", "ins", "date", "m", "y", "I"] + [f"D_{k}" for k in LEVELS]
        w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c) if not isinstance(r.get(c), float)
                        else f"{r[c]:.6f}" for c in cols])
    print(f"  per-trade file: {a.out}")

    def sub(cls, need, ex=False):
        return [r for r in rows if r["cls"] == cls and all(k in r for k in need)
                and not (ex and r["date"].year in EXCL_YEARS)]

    print(f"\n  A. LEVEL MAGNETS   fade = a + b*D + c*|move|   (t gate {T_GATE})")
    print(f"    {'level':<6}{'S1 b':>8}{'t':>7}{'n':>6}{'S2 b':>9}{'t':>7}"
          f"{'ex20-21 b':>11}{'t':>7}{'S3 b':>9}{'t':>7}   verdict")
    res = {}
    for L in LEVELS:
        need = ["y", f"D_{L}"]
        f1 = fit(sub("S1", need), "y", [f"D_{L}", "m"])
        f2 = fit(sub("S2", need), "y", [f"D_{L}", "m"])
        fx = fit(sub("S1", need, ex=True), "y", [f"D_{L}", "m"])
        f3 = fit(sub("S3", need), "y", [f"D_{L}", "m"])
        v = (verdict(f1[1], f1[0], f2[1], f2[0], fx[1], fx[0]) if L in GATED
             else "reported only (budget: unresolvable)")
        if L in GATED:
            res[L] = v
        print(f"    {L:<6}{f1[0]:>+8.3f}{f1[1]:>+7.2f}{f1[2]:>6}{f2[0]:>+9.3f}"
              f"{f2[1]:>+7.2f}{fx[0]:>+11.3f}{fx[1]:>+7.2f}{f3[0]:>+9.3f}"
              f"{f3[1]:>+7.2f}   {v}")

    print(f"\n  B. RULE OF 16   fade/I = a + b*(|move|/I)   (t gate {T_GATE})")
    f1 = fit(sub("S1", ["yI"]), "yI", ["mI"])
    f2 = fit(sub("S2", ["yI"]), "yI", ["mI"])
    fx = fit(sub("S1", ["yI"], ex=True), "yI", ["mI"])
    f3 = fit(sub("S3", ["yI"]), "yI", ["mI"])
    v = verdict(f1[1], f1[0], f2[1], f2[0], fx[1], fx[0])
    res["R16"] = v
    print(f"    S1 b {f1[0]:+.4f} t {f1[1]:+.2f} n {f1[2]}   S2 b {f2[0]:+.4f} "
          f"t {f2[1]:+.2f}   ex20-21 b {fx[0]:+.4f} t {fx[1]:+.2f}   "
          f"S3 b {f3[0]:+.4f} t {f3[1]:+.2f}   {v}")
    r1 = fit(sub("S1", ["y", "I"]), "y", ["I", "m"])
    print(f"    reported, NOT BLIND (v31 saw VIX vs bounce, t +1.20): "
          f"fade = a + c*I + d*|move|   c {r1[0]:+.4f} t {r1[1]:+.2f}")

    print("\n  DESCRIPTIVE, gating nothing: take profit at the level when the")
    print("  hour touches it (fill AT the level, optimistic), else the 09:45 exit")
    print(f"    {'level':<6}{'sample':<5}{'n':>6}{'D>0':>7}{'touched':>9}"
          f"{'fixed':>8}{'level exit':>12}")
    for L in LEVELS:
        for cls in ("S1", "S3"):
            rs = [r for r in sub(cls, ["y", f"D_{L}"]) if all(r["path"])]
            fx_, lx, tch, pos = [], [], 0, 0
            for r in rs:
                fx_.append(r["y"])
                D = r[f"D_{L}"]
                if D > 0:
                    pos += 1
                    lvl = r[f"L_{L}"]
                    hit = any((p[2] <= lvl) if r["up"] else (p[1] >= lvl)
                              for p in r["path"])
                    if hit:
                        tch += 1
                        lx.append(D)
                        continue
                lx.append(r["y"])
            print(f"    {L:<6}{cls:<5}{len(rs):>6}{pos / len(rs):>7.2f}"
                  f"{tch / max(1, pos):>9.2f}{st.mean(fx_):>+8.2f}{st.mean(lx):>+12.2f}")
    print("\n  VERDICTS  " + "   ".join(f"{k}: {v}" for k, v in res.items()))


if __name__ == "__main__":
    main()
