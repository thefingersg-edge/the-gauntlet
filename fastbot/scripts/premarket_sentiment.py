#!/usr/bin/env python3
"""PREREGISTRATION_v30 -- does anyone call it, and does the crowd matter?

Written after sentiment_fetch.py, against the frozen document, having
looked at column names and layouts only -- no value joined to a trade.

G1  leveraged money's (gold: managed money's) change in net/OI over the
    week into the release predicts the release-bar direction  b>0 t>=2.4
G2  the same for asset managers (TFF markets)                  b>0 t>=2.4
G3  crowding against the move changes the bounce              |t|>=2.4
Reported only: AAII, put/call, SKEW, Kalshi's call on the print.

    python3 premarket_sentiment.py --self-test
    python3 premarket_sentiment.py
"""
from __future__ import annotations

import argparse, bisect, csv, datetime as dt, hashlib, json, glob, math, os, re
import statistics as st, sys
import numpy as np

from premarket_event import load_events
from premarket_factor import morning, trailing_sigma, regress, tstat
from premarket_participation import read_marks_vol, stem

VERSION = "1.0"
DOC = ("PREREGISTRATION_v30.md",
       "c4d0ee10717d5405fdcbea48b221aad9f98971b742359bc753aacd0236dbd137")
INSTRUMENTS = ("SPX500_USD", "NAS100_USD", "US30_USD",
               "DE30_EUR", "EUR_USD", "XAU_USD")
COT_INS = ("SPX500_USD", "NAS100_USD", "US30_USD", "EUR_USD", "XAU_USD")
TFF_INS = ("SPX500_USD", "NAS100_USD", "US30_USD", "EUR_USD")
FORWARD_START = dt.date(2026, 9, 18)
T_GATE, BASE = 2.4, 52
PUBLISH_LAG = 3                          # Tuesday as-of, Friday published
SENT = "../data/sentiment"
_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)


def usable_reports(dates, release):
    """COT report dates whose publication (date + 3 days) is BEFORE release."""
    return [d for d in dates if d + dt.timedelta(days=PUBLISH_LAG) < release]


def z_prior(series, i, base=BASE):
    """z of series[i] against series[i-base:i] -- prior values only."""
    if i < base:
        return None
    prior = series[i - base:i]
    s = st.stdev(prior)
    return None if s == 0 else (series[i] - st.mean(prior)) / s


def implied_median(pairs):
    """pairs = [(strike, P(value > strike))]. Where P crosses 0.5."""
    pts = sorted(p for p in pairs if p[1] is not None)
    if len(pts) < 2:
        return None
    for (x0, p0), (x1, p1) in zip(pts, pts[1:]):
        if p0 >= 0.5 >= p1 and p0 != p1:
            return x0 + (p0 - 0.5) / (p0 - p1) * (x1 - x0)
    return None


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
    print(f"premarket_sentiment.py v{VERSION} self-test\n")
    tue = dt.date(2020, 6, 9)
    #: PLANTED: a Tuesday report is published Friday afternoon. A payrolls
    #: release on that same Friday morning must NOT see it.
    check("a report is unusable for a release on its publication day",
          usable_reports([tue], dt.date(2020, 6, 12)) == [])
    check("and usable for a release the Monday after",
          usable_reports([tue], dt.date(2020, 6, 15)) == [tue])
    xs = [1.0] * 52 + [5.0]
    check("the z-score looks backwards only", z_prior(xs, 52) is None
          and z_prior([float(i % 2) for i in range(52)] + [1.0], 52) is not None)
    #: P(>0.1)=0.9, P(>0.2)=0.7, P(>0.3)=0.3 -> median 0.25
    check("implied median interpolates where P(>x) crosses one half",
          abs(implied_median([(0.1, .9), (0.2, .7), (0.3, .3)]) - 0.25) < 1e-12)
    check("three gates at 2.4, 52-report baseline, forward sample out",
          T_GATE == 2.4 and BASE == 52 and FORWARD_START == dt.date(2026, 9, 18))
    check("five CFTC instruments, DE30 not among them",
          "DE30_EUR" not in COT_INS and len(COT_INS) == 5)
    check("no order, execute, submit or position name in this file",
          not [n for n in globals() if _FORBIDDEN.search(n)])
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def load_cot():
    """{instrument: {'dates': [...], 'lev': [...], 'am': [...]}} net/OI."""
    raw = {}
    for r in csv.DictReader(open(f"{SENT}/cftc_positions.csv")):
        oi = float(r["oi"] or 0)
        if oi <= 0:
            continue
        d = dt.date.fromisoformat(r["report_date"])
        if r["report"] == "tff":
            lev = (float(r["lev_l"]) - float(r["lev_s"])) / oi
            am = (float(r["am_l"]) - float(r["am_s"])) / oi
        else:
            lev = (float(r["mm_l"]) - float(r["mm_s"])) / oi
            am = None
        raw[(r["instrument"], d)] = (lev, am)
    out = {}
    for (ins, d), v in sorted(raw.items()):
        o = out.setdefault(ins, {"dates": [], "lev": [], "am": []})
        o["dates"].append(d); o["lev"].append(v[0]); o["am"].append(v[1])
    return out


def cot_features(c, release):
    """(X_lev, X_am, L) for one instrument and release date, or Nones."""
    k = bisect.bisect_left(c["dates"], release - dt.timedelta(days=PUBLISH_LAG))
    k -= 1                                   # latest usable index
    while k >= 0 and not (c["dates"][k] + dt.timedelta(days=PUBLISH_LAG) < release):
        k -= 1
    if k < BASE + 1:
        return None, None, None
    out = []
    for key in ("lev", "am"):
        s = c[key]
        if s[k] is None or s[k - 1] is None:
            out.append(None); continue
        chg = [s[j] - s[j - 1] for j in range(k - BASE, k + 1)
               if s[j] is not None and s[j - 1] is not None]
        base = chg[:-1]
        sd = st.stdev(base) if len(base) > 2 else 0
        out.append(None if sd == 0 else (s[k] - s[k - 1]) / sd)
    L = z_prior(c["lev"], k)
    return out[0], out[1], L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="../data/v24")
    ap.add_argument("--events", default="../data/events_v2.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    print(f"premarket_sentiment.py v{VERSION}   PREREGISTRATION_v30\n")
    print("  I am not a financial adviser. This is a measurement, not a")
    print("  recommendation to take a position.\n")
    here = os.path.dirname(os.path.abspath(__file__))
    got = hashlib.sha256(open(os.path.join(here, "..", DOC[0]), "rb").read()).hexdigest()
    if got != DOC[1]:
        print("  registration changed since frozen. Refused."); sys.exit(2)
    print(f"  {DOC[0]} sha256 {got[:16]}... matches\n")

    pre, _ = load_events(a.events, from_year=1900)
    s1 = {d for d, e in pre.items() if {"CPI", "NFP"} & e}
    s2 = {d for d, e in pre.items() if "CLAIMS" in e} - s1
    cot = load_cot()

    # --- the trades: m, sigma, fade, exactly as v28/v29 ---------------
    recs = []
    for ins in INSTRUMENTS:
        b, _v = read_marks_vol(os.path.join(a.data_dir, f"{stem(ins)}_bid_15m.csv"))
        ask, _ = read_marks_vol(os.path.join(a.data_dir, f"{stem(ins)}_ask_15m.csv"))
        rows = {"S1": [], "S2": [], "S3": []}
        for d in sorted({x for (x, hm) in b if hm == "08:30"}):
            if d >= FORWARD_START:
                continue
            m = morning(b, ask, d)
            if m is not None:
                rows["S1" if d in s1 else "S2" if d in s2 else "S3"].append((d,) + m)
        for cls, rr in rows.items():
            for (d, mv, y0, y1), s in zip(rr, trailing_sigma([r[1] for r in rr])):
                if s and s > 0:
                    recs.append(dict(cls=cls, ins=ins, date=d, m=mv, y0=y0, sigma=s))
    v27 = {(r["instrument"], r["date"]): float(r["gross_H0"])
           for r in csv.DictReader(open(os.path.join(here, "../data/horizon_v27_trades.csv")))
           if r["gross_H0"]}
    diffs = [abs(r["y0"] - v27[(r["ins"], r["date"].isoformat())]) for r in recs
             if (r["ins"], r["date"].isoformat()) in v27]
    g0 = len(diffs) > 1000 and max(diffs) < 1e-6
    print(f"  GATE 0  {len(diffs):,} trades matched v27, max |diff| {max(diffs):.1e}"
          f"   [{'PASS' if g0 else 'FAIL'}]")
    if not g0:
        sys.exit(3)

    for r in recs:
        if r["ins"] in cot:
            r["xl"], r["xa"], r["L"] = cot_features(cot[r["ins"]], r["date"])

    def fit(rows, xkey, ykey):
        #: v1.0 bug fixed before any G3 number was printed: A is built from L,
        #: so filtering on a key named "A" dropped every row.
        rows = [r for r in rows if r.get("L" if xkey == "A" else xkey) is not None]
        if len(rows) < 50:
            return None
        y = [(r["m"] if ykey == "move" else r["y0"]) / r["sigma"] for r in rows]
        x = [r[xkey] if xkey != "A" else math.copysign(1, r["m"]) * r["L"] for r in rows]
        b, V = regress(y, np.column_stack([np.ones(len(rows)), x]), [r["date"] for r in rows])
        return len(rows), b[1], tstat(b, V, 1), min(r["date"] for r in rows)

    print(f"\n  QUESTION A -- does anyone call the direction?  Y = move/sigma")
    print(f"    {'':<30}{'n':>6}{'b':>9}{'t':>8}   from")
    res = {}
    for key, nm, pool in (("xl", "Leveraged money (gold: MM)", COT_INS),
                          ("xa", "Asset managers", TFF_INS)):
        for cls in ("S1", "S2", "S3"):
            out = fit([r for r in recs if r["cls"] == cls and r["ins"] in pool],
                      key, "move")
            res[(key, cls)] = out
            if out:
                print(f"    {nm + ' ' + cls:<30}{out[0]:>6}{out[1]:>+9.3f}{out[2]:>+8.2f}   {out[3]}")
    print(f"\n  QUESTION B -- crowding and the bounce.  fade/sigma on A = sign(m) x L")
    for cls in ("S1", "S2", "S3"):
        out = fit([r for r in recs if r["cls"] == cls and r.get("L") is not None],
                  "A", "fade")
        res[("A", cls)] = out
        print(f"    {'crowding ' + cls:<30}{out[0]:>6}{out[1]:>+9.3f}{out[2]:>+8.2f}   {out[3]}")

    # --- reported: AAII, put/call, SKEW ------------------------------
    import xlrd
    wb = xlrd.open_workbook(f"{SENT}/aaii_sentiment.csv")
    sh = wb.sheet_by_index(0)
    aaii = []
    for i in range(sh.nrows):
        v = sh.row_values(i)
        if isinstance(v[0], float) and v[0] > 30000 and v[1] != "" and v[3] != "":
            aaii.append((xlrd.xldate_as_datetime(v[0], wb.datemode).date(),
                         float(v[1]) - float(v[3])))
    aaii.sort()
    skew = sorted((dt.datetime.strptime(r["DATE"], "%m/%d/%Y").date(), float(r["SKEW"]))
                  for r in csv.DictReader(open(f"{SENT}/cboe_skew.csv")))
    pc = []
    for line in list(open(f"{SENT}/cboe_equitypc.csv"))[3:]:
        p = [x.strip() for x in line.split(",")]
        try:
            pc.append((dt.datetime.strptime(p[0], "%m/%d/%Y").date(), float(p[4])))
        except (ValueError, IndexError):
            pass
    pc.sort()

    def before(series, d, n=1):
        k = bisect.bisect_left([x[0] for x in series], d)
        if k < n:
            return None
        if series[k - 1][0] < d - dt.timedelta(days=10):
            return None
        return st.mean(x[1] for x in series[k - n:k])

    for r in recs:
        r["aaii"] = before(aaii, r["date"])
        r["skew"] = before(skew, r["date"])
        r["pc"] = before(pc, r["date"], 5)
    print(f"\n  REPORTED, gating nothing -- sentiment going in (six instruments, S1)")
    print(f"    {'':<22}{'vs direction: n':>16}{'b':>8}{'t':>7}{'vs bounce: b':>15}{'t':>7}")
    s1r = [r for r in recs if r["cls"] == "S1"]
    for key, nm in (("aaii", "AAII bull-bear"), ("pc", "put/call 5d (to 2019)"),
                    ("skew", "SKEW")):
        rows = [r for r in s1r if r[key] is not None]
        xs = [r[key] for r in rows]
        mu, sd = st.mean(xs), st.stdev(xs)
        for r in rows:
            r["_z"] = (r[key] - mu) / sd
        a_ = fit(rows, "_z", "move"); b_ = fit(rows, "_z", "fade")
        print(f"    {nm:<22}{a_[0]:>16}{a_[1]:>+8.3f}{a_[2]:>+7.2f}{b_[1]:>+15.3f}{b_[2]:>+7.2f}")

    # --- Kalshi, descriptive ----------------------------------------
    print(f"\n  KALSHI -- the crowd's call on the print. Descriptive, no verdict.")
    fred = {}
    for r in csv.DictReader(open("../data/release_content.csv")):
        if r["vintage_ok"] == "1":
            fred[(r["series"], r["event_date"])] = (float(r["prev_value"]), float(r["last_value"]))
    def actual(series, d):
        k = d.isoformat()
        if series in ("KXCPI", "KXCPICORE"):
            f = fred.get(("CPIAUCSL" if series == "KXCPI" else "CPILFESL", k))
            return None if not f else (round((f[1] / f[0] - 1) * 100, 1), None)
        if series == "KXPAYROLLS":
            f = fred.get(("PAYEMS", k))
            return None if not f else ((f[1] - f[0]) * 1000, None)
        f = fred.get(("UNRATE", k))
        return None if not f else (f[1], f[0])
    et = __import__("zoneinfo").ZoneInfo("America/New_York")
    calls = []
    for s in ("KXCPI", "KXCPICORE", "KXPAYROLLS", "KXU3"):
        mk = json.load(open(f"{SENT}/kalshi/{s}_markets.json"))
        ev = {}
        for m in mk:
            st_ = m.get("strike_type")
            if st_ not in ("greater", None) or m.get("floor_strike") is None \
                    or m.get("cap_strike") is not None:
                continue
            p = f"{SENT}/kalshi/{m['ticker']}_candles.json"
            if not os.path.exists(p):
                continue
            cs = json.load(open(p)).get("candlesticks", [])
            ct = dt.datetime.fromisoformat(m["close_time"].replace("Z", "+00:00"))
            cs = [c for c in cs if c["end_period_ts"] <= ct.timestamp()]
            if not cs:
                continue
            c = cs[-1]
            def val(side):
                x = c.get(side) or {}
                v = x.get("close", x.get("close_dollars"))
                return None if v in (None, "") else float(v)
            bid, ask = val("yes_bid"), val("yes_ask")
            prob = (bid + ask) / 2 if bid is not None and ask is not None else None
            ev.setdefault((m["event_ticker"], ct.astimezone(et).date()), []).append(
                (float(m["floor_strike"]), prob))
        prev_act = None
        for (evt, d), pairs in sorted(ev.items(), key=lambda kv: kv[0][1]):
            med = implied_median(pairs)
            act = actual(s, d)
            if med is None or act is None:
                continue
            a_now = act[0]
            prev = act[1] if act[1] is not None else prev_act
            prev_act = a_now
            if prev is None or d not in s1:
                continue
            calls.append(dict(series=s, date=d, med=med, act=a_now, prev=prev))
    print(f"    {'series':<12}{'n':>4}{'called direction vs previous print':>38}{'crowd error |median-actual|':>30}")
    for s in ("KXCPI", "KXCPICORE", "KXPAYROLLS", "KXU3"):
        cc = [c for c in calls if c["series"] == s and c["act"] != c["prev"]
              and c["med"] != c["prev"]]
        if not cc:
            print(f"    {s:<12}   0"); continue
        hit = sum(1 for c in cc if (c["med"] > c["prev"]) == (c["act"] > c["prev"]))
        err = st.median(abs(c["med"] - c["act"]) for c in [x for x in calls if x["series"] == s])
        print(f"    {s:<12}{len(cc):>4}{hit:>20} of {len(cc):<3} = {hit / len(cc):>4.0%}{err:>24.3g}")
    # fade when the crowd was wrong (print on the other side of the median)
    by_date = {}
    for c in calls:
        by_date.setdefault(c["date"], []).append(abs(c["act"] - c["med"]) /
                                                 max(1e-9, abs(c["med"]) + 1e-9))
    fade_s1 = {}
    for r in s1r:
        fade_s1.setdefault(r["date"], []).append(r["y0"])
    kd = sorted(d for d in by_date if d in fade_s1)
    print(f"    release dates with a Kalshi call and a fade: {len(kd)}, "
          f"{kd[0] if kd else '--'} .. {kd[-1] if kd else '--'}")
    if len(kd) >= 6:
        miss = {d: max(by_date[d]) for d in kd}
        med_m = st.median(miss.values())
        big = [x for d in kd if miss[d] > med_m for x in fade_s1[d]]
        small = [x for d in kd if miss[d] <= med_m for x in fade_s1[d]]
        print(f"    fade on days the crowd missed by MORE than median {st.mean(big):+.2f} bp"
              f" (n {len(big)}), by LESS {st.mean(small):+.2f} bp (n {len(small)})")

    print(f"\n  GATES -- frozen in PREREGISTRATION_v30")
    for gid, key, cond in (("G1", ("xl", "S1"), "pos"), ("G2", ("xa", "S1"), "pos"),
                           ("G3", ("A", "S1"), "two")):
        n, b, t, _ = res[key]
        ok = (b > 0 and t >= T_GATE) if cond == "pos" else abs(t) >= T_GATE
        print(f"    [{'PASS' if ok else 'FAIL'}] {gid}  b {b:+.3f}  t {t:+.2f}  n {n}")


if __name__ == "__main__":
    main()
