#!/usr/bin/env python3
"""PREREGISTRATION_v58 -- do currencies earn a premium against the dollar on FOMC days?
(Mueller, Tahbaz-Salehi & Vedolin, JF 2017.) A measurement (fastbot Rule 1), one run.

    python3 fomcfx_v58.py --self-test
    python3 fomcfx_v58.py --check-inputs     # files and FOMC table only, NO returns
    python3 fomcfx_v58.py
"""
from __future__ import annotations

import argparse, csv, datetime as dt, hashlib, math, os, sys
from zoneinfo import ZoneInfo
import numpy as np

VERSION = "1.0"
DOC = "../PREREGISTRATION_v58.md"
DOC_SHA = "229ba641d869aaca062ff969125deb82256f8036074ec95417dab59acba4745f"
NY, UTC = ZoneInfo("America/New_York"), dt.timezone.utc
FL = "../../flows/data"
#        currency  file stem  directory      sign (+1: XXXUSD, long foreign = +dln)
PAIRS = {"EUR": ("eurusd", "../data/v24", +1), "GBP": ("gbpusd", FL, +1), "AUD": ("audusd", FL, +1),
         "NZD": ("nzdusd", FL, +1), "CAD": ("usdcad", FL, -1), "CHF": ("usdchf", FL, -1),
         "JPY": ("usdjpy", FL, -1), "NOK": ("usdnok", FL, -1), "SEK": ("usdsek", FL, -1)}
MIN_CCY = 7
FIRST, LAST = dt.date(2005, 1, 1), dt.date(2026, 9, 30)
PRIMARY = (dt.date(2011, 1, 1), LAST)
ERAS = ((dt.date(2011, 1, 1), dt.date(2018, 12, 31)), (dt.date(2019, 1, 1), LAST))
REPL = (dt.date(2005, 1, 1), dt.date(2010, 12, 31))
N_PERM, SEED = 2000, 58


def fomc_days(path="../data/events.csv"):
    raw = sorted({dt.date.fromisoformat(r["date"]) for r in csv.DictReader(open(path)) if r["event"] == "FOMC"})
    keep = [d for d in raw if (d + dt.timedelta(days=1)) not in raw]        # consecutive pair -> keep the later
    return [d for d in keep if FIRST <= d <= LAST]


def read_pair(stem, d):
    """{date: {'1345': (bid_c, ask_c), '1545': (bid_c, ask_c)}} at NY bar-start 13:45 / 15:45."""
    out = {}
    for side, k in (("bid", 0), ("ask", 1)):
        with open(os.path.join(d, f"{stem}_{side}_15m.csv")) as fh:
            r = csv.reader(fh); next(r)
            for row in r:
                t = dt.datetime.fromisoformat(row[0]).replace(tzinfo=UTC).astimezone(NY)
                hm = t.strftime("%H%M")
                if hm in ("1345", "1545") and t.weekday() < 5:
                    out.setdefault(t.date(), {}).setdefault(hm, [None, None])[k] = float(row[4])
    return out


def pair_returns(bars, sign):
    """{d: (r_full, r_pre, r_post, cost)} in bp, long foreign vs USD."""
    mid = lambda ba: (ba[0] + ba[1]) / 2
    ok = lambda x: x is not None and None not in x
    ds = sorted(d for d in bars if ok(bars[d].get("1545")))
    out = {}
    for p, d in zip(ds, ds[1:]):
        if (d - p).days > 4:
            continue
        m0, m1 = mid(bars[p]["1545"]), mid(bars[d]["1545"])
        sp0 = (bars[p]["1545"][1] - bars[p]["1545"][0]) / m0 * 1e4
        sp1 = (bars[d]["1545"][1] - bars[d]["1545"][0]) / m1 * 1e4
        full = sign * math.log(m1 / m0) * 1e4
        pre = post = float("nan")
        if ok(bars[d].get("1345")):
            mm = mid(bars[d]["1345"])
            pre, post = sign * math.log(mm / m0) * 1e4, sign * math.log(m1 / mm) * 1e4
        out[d] = (full, pre, post, sp0 / 2 + sp1 / 2)
    return out


def ols_hc1(y, x):
    y = np.asarray(y, float); X = np.column_stack([np.ones(len(y)), np.asarray(x, float)])
    XtXi = np.linalg.inv(X.T @ X); b = XtXi @ X.T @ y; u = y - X @ b
    n, k = X.shape
    V = XtXi @ (X.T * u ** 2) @ X @ XtXi * n / (n - k)
    return b, b / np.sqrt(np.diag(V))


def build(R, fomc):
    days = sorted(set().union(*[set(r) for r in R.values()]))
    rows = []
    for d in days:
        have = [c for c in R if d in R[c]]
        if len(have) < MIN_CCY:
            continue
        v = np.array([R[c][d] for c in have])
        rows.append((d, v[:, 0].mean(), np.nanmean(v[:, 1]) if np.isfinite(v[:, 1]).any() else np.nan,
                     np.nanmean(v[:, 2]) if np.isfinite(v[:, 2]).any() else np.nan, v[:, 3].mean(), d in fomc))
    return rows


def perm_p(rows, lo, hi, rng, n=N_PERM):
    s = [r for r in rows if lo <= r[0] <= hi]
    y = np.array([r[1] for r in s]); f = np.array([r[5] for r in s]); yr = np.array([r[0].year for r in s])
    obs = y[f].mean() - y[~f].mean()
    pools = {Y: np.where((yr == Y) & ~f)[0] for Y in set(yr)}
    cnt = {Y: int(((yr == Y) & f).sum()) for Y in set(yr)}
    st = []
    for _ in range(n):
        idx = np.concatenate([rng.choice(pools[Y], cnt[Y], replace=False) for Y in pools if cnt[Y]])
        m = np.zeros(len(y), bool); m[idx] = True
        st.append(y[m].mean() - y[~m].mean())
    return float(obs), float((np.array(st) >= obs).mean())


def check_inputs():
    fomc = fomc_days()
    yrs = {}
    for d in fomc: yrs[d.year] = yrs.get(d.year, 0) + 1
    print("  FOMC announcement days after dedup, per year: " + " ".join(f"{y}:{n}" for y, n in sorted(yrs.items())))
    print(f"  total {len(fomc)}; in primary 2011-2026: {sum(PRIMARY[0] <= d <= PRIMARY[1] for d in fomc)}")
    for c, (stem, d, _) in PAIRS.items():
        for side in ("bid", "ask"):
            p = os.path.join(d, f"{stem}_{side}_15m.csv")
            print(f"  {c} {side}: {'ok' if os.path.exists(p) else 'MISSING'} {p}")


def run():
    got = hashlib.sha256(open(DOC, "rb").read()).hexdigest()
    if got != DOC_SHA:
        sys.exit(f"{DOC} changed since frozen ({got[:12]}). Refused.")
    print(f"fomcfx_v58.py v{VERSION}\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    fomc = set(fomc_days())
    R = {}
    for c, (stem, d, sg) in PAIRS.items():
        R[c] = pair_returns(read_pair(stem, d), sg)
    rows = build(R, fomc)
    used = [r for r in rows if r[5]]
    miss = sorted(fomc - {r[0] for r in used})
    print(f"  DOL days {len(rows):,}; FOMC days with DOL {len(used)} of {len(fomc)}; missing: {[str(m) for m in miss]}")
    res = {}
    for name, (lo, hi) in (("primary 2011-2026", PRIMARY), ("era 2011-2018", ERAS[0]), ("era 2019-2026", ERAS[1]),
                           ("replication 2005-2010", REPL)):
        s = [r for r in rows if lo <= r[0] <= hi]
        y = np.array([r[1] for r in s]); f = np.array([r[5] for r in s], float)
        b, t = ols_hc1(y, f)
        res[name] = (b[1], t[1], int(f.sum()), y[f == 1].mean(), y[f == 0].mean())
        print(f"  {name:<22} FOMC n {int(f.sum()):>3}  FOMC mean {y[f == 1].mean():+6.2f} bp  other {y[f == 0].mean():+5.2f}"
              f"  diff {b[1]:+6.2f} bp (HC1 t {t[1]:+.2f})")
    bP, tP = res["primary 2011-2026"][:2]
    b1, b2 = res["era 2011-2018"][0], res["era 2019-2026"][0]
    pr = [r for r in rows if r[5] and PRIMARY[0] <= r[0] <= PRIMARY[1]]
    gross = np.mean([r[1] for r in pr]); cost = np.mean([r[4] for r in pr])
    print(f"\n  FOMC days 2011-2026: gross {gross:+.2f} bp, mean round-trip cost {cost:.2f} bp, net {gross - cost:+.2f} bp")
    g1 = bP > 0 and tP >= 2.0
    g2 = b1 > 0 and b2 > 0 and b2 >= 0.5 * bP
    g3 = gross - cost > 0
    print(f"\n  G1 FOMC premium 2011-2026, t >= 2        : {'PASS' if g1 else 'FAIL'} ({bP:+.2f} bp, t {tP:+.2f})")
    print(f"  G2 both eras > 0, 2019-26 >= half        : {'PASS' if g2 else 'FAIL'} ({b1:+.2f}, {b2:+.2f})")
    print(f"  G3 net of round-trip cost > 0            : {'PASS' if g3 else 'FAIL'} ({gross - cost:+.2f} bp)")
    print(f"\n  VERDICT: {'PASS' if (g1 and g2 and g3) else 'FAIL'}\n")
    # reported
    pre = np.nanmean([r[2] for r in pr]); post = np.nanmean([r[3] for r in pr])
    print(f"  reported  FOMC-day split 2011-2026: pre-announcement {pre:+.2f} bp, post {post:+.2f} bp")
    line = []
    for c in PAIRS:
        ds = [d for d in R[c] if PRIMARY[0] <= d <= PRIMARY[1]]
        y = np.array([R[c][d][0] for d in ds]); f = np.array([d in fomc for d in ds], float)
        b, t = ols_hc1(y, f); line.append(f"{c} {b[1]:+.1f} (t {t[1]:+.1f})")
    print("  reported  per currency 2011-2026: " + ", ".join(line))
    hl = []
    for d in sorted(fomc):
        if PRIMARY[0] <= d <= PRIMARY[1] and all(d in R[c] for c in ("AUD", "NZD", "JPY", "CHF")):
            hl.append((R["AUD"][d][0] + R["NZD"][d][0]) / 2 - (R["JPY"][d][0] + R["CHF"][d][0]) / 2)
    hl = np.array(hl)
    print(f"  reported  AUD+NZD minus JPY+CHF on FOMC days: {hl.mean():+.2f} bp (t {hl.mean() / (hl.std(ddof=1) / math.sqrt(len(hl))):+.2f}, n {len(hl)})")
    s = [r for r in rows if PRIMARY[0] <= r[0] <= PRIMARY[1]]
    print(f"  reported  DOL sd: FOMC days {np.std([r[1] for r in s if r[5]], ddof=1):.1f} bp, other days {np.std([r[1] for r in s if not r[5]], ddof=1):.1f} bp")
    obs, p = perm_p(rows, *PRIMARY, np.random.default_rng(SEED))
    print(f"  reported  within-year permutation (2,000, seed 58): diff {obs:+.2f} bp, one-sided p {p:.3f}")


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"fomcfx_v58.py v{VERSION} self-test\n")
    import tempfile
    tmp = tempfile.mkdtemp(); p = os.path.join(tmp, "e.csv")
    with open(p, "w") as fh:
        fh.write("event,date,time_et\nFOMC,2008-01-29,14:15\nFOMC,2008-01-30,14:15\nFOMC,2008-03-18,14:15\nCPI,2008-03-19,08:30\n")
    check("dedup keeps the later of a consecutive pair and ignores other events",
          fomc_days(p) == [dt.date(2008, 1, 30), dt.date(2008, 3, 18)])
    # synthetic bars: USDJPY falls 1% on day 2 -> long JPY earns +100 bp (approx log)
    d1, d2 = dt.date(2020, 1, 6), dt.date(2020, 1, 7)
    bars = {d1: {"1545": [100.0, 100.02], "1345": [100.0, 100.02]}, d2: {"1545": [99.0, 99.02], "1345": [99.5, 99.52]}}
    r = pair_returns(bars, -1)[d2]
    check("USD-base pair is sign-flipped: USDJPY down 1% = long JPY up ~100 bp", abs(r[0] - (-math.log(99.01 / 100.01) * 1e4)) < 1e-9 and r[0] > 99)
    check("pre + post equals the full-day return", abs(r[1] + r[2] - r[0]) < 1e-9)
    check("cost is half the entry spread plus half the exit spread", abs(r[3] - (0.02 / 100.01 * 1e4 / 2 + 0.02 / 99.01 * 1e4 / 2)) < 1e-9)
    bars[dt.date(2020, 1, 14)] = {"1545": [99.0, 99.02]}
    check("a gap of more than 4 calendar days gives no return", dt.date(2020, 1, 14) not in pair_returns(bars, -1))
    rng = np.random.default_rng(0); n = 4000
    f = np.zeros(n); f[rng.choice(n, 150, replace=False)] = 1
    bs = [ols_hc1(np.random.default_rng(k).normal(0, 45, n) + 12 * f, f)[0][1] for k in range(40)]
    check("PLANTED +12 bp on 150 of 4000 days: mean estimate over 40 draws within 1.5 bp of 12", abs(np.mean(bs) - 12) < 1.5)
    b, t = ols_hc1(np.random.default_rng(1).normal(0, 45, n) + 30 * f, f)
    check("PLANTED +30 bp is detected (t > 4)", t[1] > 4)
    b0, t0 = ols_hc1(rng.normal(0, 45, n), f)
    check("no planted effect: |t| < 3", abs(t0[1]) < 3)
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--self-test", action="store_true"); ap.add_argument("--check-inputs", action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else (check_inputs() or 0) if a.check_inputs else run())
