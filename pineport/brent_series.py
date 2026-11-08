#!/usr/bin/env python3
"""What does OANDA's BCO_USD price series represent?

Implements PREREGISTRATION_BRENT_SERIES.md (registered 2026-10-11 20:19 UTC)
literally. Inputs: TradingView daily JSON in data/brent_series/raw/ and the
on-disk OANDA feed bcousd_oanda_h4.csv. Writes data/brent_series/aligned.csv
and prints every registered statistic.

Alignment detail (an implementation of "aligned on calendar date"): each bar is
stamped with its trade date = (open time UTC + 4 h).date(). OANDA daily bars open
at 17:00 New York (21:00/22:00 UTC) the evening before; ICE bars are stamped
00:00/01:00 UTC on the trade date. Both map to the trade date this way.
"""
import csv, json, math, os, statistics as st, sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "brent_series", "raw")
CARD_BENCHMARK = -46.10  # %/yr, OANDA rate card, measured 2026-10-11


def load_tv(name):
    d = json.load(open(os.path.join(RAW, name)))
    out = {}
    for b in d["bars"]:
        t = datetime.fromtimestamp(b["t"], timezone.utc)
        out[(t + timedelta(hours=4)).date()] = (t, float(b["c"]))
    return d["symbol"], out


def mad(x):
    m = st.median(x)
    return st.median(abs(v - m) for v in x)


def ols(x, y):
    n = len(x); mx = sum(x) / n; my = sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x); sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    b = sxy / sxx; a = my - b * mx
    res = [yy - a - b * xx for xx, yy in zip(x, y)]
    se = math.sqrt(sum(r * r for r in res) / (n - 2) / sxx)
    r2 = 1 - sum(r * r for r in res) / sum((v - my) ** 2 for v in y)
    return a, b, se, r2


def main():
    _, bco = load_tv("OANDA_BCOUSD_1D.json")
    _, m1 = load_tv("ICEEUR_BRN1_1D.json")
    _, m2 = load_tv("ICEEUR_BRN2_1D.json")

    # ---- gate 0: TV OANDA:BCOUSD vs on-disk OANDA H4 feed ----
    h4 = {}
    with open(os.path.join(HERE, "bcousd_oanda_h4.csv")) as f:
        for r in csv.DictReader(f):
            t = datetime.fromisoformat(r["time"])
            h4[t + timedelta(hours=4)] = float(r["close"])   # keyed by bar CLOSE time
    h4_closes = sorted(h4)
    diffs = []
    import bisect
    for day, (t_open, c) in bco.items():
        close_t = t_open + timedelta(hours=24)
        if close_t > h4_closes[-1] + timedelta(hours=1):
            continue
        i = bisect.bisect_right(h4_closes, close_t) - 1
        if i < 0 or close_t - h4_closes[i] > timedelta(hours=4):
            continue
        diffs.append(abs(c - h4[h4_closes[i]]))
    g0 = st.median(diffs) if diffs else float("nan")
    print(f"GATE 0  overlap days {len(diffs)}  median |TV - disk| = {g0:.4f} USD  "
          f"(p90 {sorted(diffs)[int(0.9*len(diffs))]:.4f})  -> {'PASS' if g0 <= 0.10 else 'FAIL'}")
    if not (g0 <= 0.10):
        print("Gate 0 failed: run stops here, per section 5."); return 1

    # ---- align ----
    days = sorted(set(bco) & set(m1) & set(m2))
    dropped = len(set(bco) | set(m1) | set(m2)) - len(days)
    rows = [dict(day=d, bco=bco[d][1], m1=m1[d][1], m2=m2[d][1]) for d in days]
    for r in rows:
        r["s"] = r["m2"] - r["m1"]; r["d1"] = r["bco"] - r["m1"]; r["d2"] = r["bco"] - r["m2"]
    print(f"aligned days {len(rows)}  ({days[0]} .. {days[-1]}), dropped {dropped} non-common dates")

    # ---- roll detection ----
    roll = [False] * len(rows)
    for i in range(1, len(rows)):
        p, c = rows[i - 1], rows[i]
        if abs(c["m1"] - p["m2"]) < abs(c["m1"] - p["m1"]) and abs(p["s"]) > 0.05:
            roll[i] = True
    years = (days[-1] - days[0]).days / 365.25
    nroll = sum(roll); per_year = nroll / years
    print(f"roll days detected {nroll} over {years:.2f} y = {per_year:.1f}/yr  "
          f"-> detector {'OK' if 10 <= per_year <= 14 else 'FAILED (use ICE expiry rule)'}")
    detector_ok = 10 <= per_year <= 14
    if not detector_ok:
        # Section 2 fallback: ICE expiry rule. Brent expires on the last business
        # day of the second month before delivery, i.e. at every month-end, so
        # BRN1 switches contract on the first trading day of each calendar month.
        roll = [False] * len(rows)
        for i in range(1, len(rows)):
            if rows[i]["day"].month != rows[i - 1]["day"].month:
                roll[i] = True
        nroll = sum(roll)
        print(f"  FALLBACK (ICE expiry rule): {nroll} roll days = {nroll/years:.1f}/yr")
        # diagnostic only: does BRN1 actually switch there? jump in s across the roll
        js = [rows[i]["s"] - rows[i-1]["s"] for i in range(1, len(rows)) if roll[i]]
        jn = [rows[i]["s"] - rows[i-1]["s"] for i in range(1, len(rows)) if not roll[i]]
        print(f"  diagnostic: median |ds| on fallback roll days {st.median(abs(v) for v in js):.3f} "
              f"vs other days {st.median(abs(v) for v in jn):.3f}")
    print("  roll dates used:", " ".join(str(rows[i]["day"]) for i in range(len(rows)) if roll[i]))

    # ---- medians ----
    med_s = st.median(abs(r["s"]) for r in rows)
    med_d1 = st.median(abs(r["d1"]) for r in rows)
    med_d2 = st.median(abs(r["d2"]) for r in rows)
    print(f"median |s| {med_s:.3f}   median |d1| {med_d1:.3f} ({med_d1/med_s:.2f}x)   "
          f"median |d2| {med_d2:.3f} ({med_d2/med_s:.2f}x)   [H-front/H-second bar: < 0.25x]")
    print(f"mean d1 {st.mean(r['d1'] for r in rows):+.3f}   mean s {st.mean(r['s'] for r in rows):+.3f}")

    # ---- roll-day regression: dd1 = a + b*(-g) ----
    x, y = [], []
    for i in range(1, len(rows)):
        if roll[i]:
            x.append(-rows[i - 1]["s"]); y.append(rows[i]["d1"] - rows[i - 1]["d1"])
    a, b, se, r2 = ols(x, y)
    print(f"roll-day regression  n={len(x)}  a={a:+.3f}  b={b:.3f} (se {se:.3f})  R2={r2:.3f}")
    print(f"  mean roll gap -g {st.mean(x):+.3f}; mean dd1 on roll days {st.mean(y):+.3f}")

    # ---- non-roll-day outliers (H-own-roll) ----
    dd = [rows[i]["d1"] - rows[i - 1]["d1"] for i in range(1, len(rows)) if not roll[i]]
    ddi = [i for i in range(1, len(rows)) if not roll[i]]
    m, M = st.median(dd), mad(dd)
    out = [ddi[k] for k, v in enumerate(dd) if abs(v - m) > 4 * M]
    p_tail = math.erfc(4 * 0.6745 / math.sqrt(2))
    exp = len(dd) * p_tail
    print(f"non-roll |dd1| > 4 MAD: {len(out)} of {len(dd)}  (normal expects {exp:.1f}; 3x = {3*exp:.1f})")
    print("  outlier dates:", " ".join(f"{rows[i]['day']}({rows[i]['d1']-rows[i-1]['d1']:+.2f})" for i in out))

    # ---- curve check ----
    last5 = rows[-5:]
    ry = 12 * st.mean(r["s"] / r["m1"] for r in last5) * 100
    print(f"curve check  last 5 days {last5[0]['day']}..{last5[-1]['day']}: "
          f"annualised M1->M2 = {ry:+.1f}%/yr vs card {CARD_BENCHMARK:+.2f}%  "
          f"diff {ry-CARD_BENCHMARK:+.1f} pp -> {'SUPPORTED' if abs(ry-CARD_BENCHMARK) <= 12 else 'NOT SUPPORTED'}")

    # ---- verdicts ----
    H = {
        "H-front": med_d1 < 0.25 * med_s and -0.3 <= b <= 0.3,
        "H-second": med_d2 < 0.25 * med_s,
        "H-synthetic": 0.7 <= b <= 1.3,
        "H-own-roll(count part)": len(out) > 3 * exp,
    }
    print("HYPOTHESES:", ", ".join(f"{k}={'holds' if v else 'no'}" for k, v in H.items()))
    if not detector_ok:
        print("NOTE: registered detector failed its sanity range; roll days above are the ICE-expiry fallback (section 2).")

    diagnostic_tv_roll(rows)

    with open(os.path.join(HERE, "data", "brent_series", "aligned.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["day", "bco", "brn1", "brn2", "s", "d1", "d2", "roll"])
        for r, rl in zip(rows, roll):
            w.writerow([r["day"], r["bco"], r["m1"], r["m2"], f"{r['s']:.3f}", f"{r['d1']:.3f}", f"{r['d2']:.3f}", int(rl)])
    return 0


# ---------------------------------------------------------------------------
# DIAGNOSTIC -- NOT REGISTERED. Added 2026-10-11 after the registered run.
# Both registered roll calendars were wrong about TradingView's BRN1!: checked
# against the individual contracts BRNM2024, BRNV2026, BRNX2026, BRN1! is
# unadjusted and switches on the 5th-from-last UK business day of the month
# (ICE expiry being the last). Roll days below come from that calendar and the
# futures series only; BCO is never used to place them. Thresholds are the
# registered ones, applied unchanged.
UK_HOLIDAYS = {  # England & Wales bank holidays on weekdays in the sample
    "2023-12-25", "2023-12-26", "2024-01-01", "2024-03-29", "2024-04-01", "2024-05-06",
    "2024-05-27", "2024-08-26", "2024-12-25", "2024-12-26", "2025-01-01", "2025-04-18",
    "2025-04-21", "2025-05-05", "2025-05-26", "2025-08-25", "2025-12-25", "2025-12-26",
    "2026-01-01", "2026-04-03", "2026-04-06", "2026-05-04", "2026-05-25", "2026-08-31",
}


def diagnostic_tv_roll(rows):
    from collections import defaultdict
    bymonth = defaultdict(list)
    for i, r in enumerate(rows):
        if str(r["day"]) not in UK_HOLIDAYS:
            bymonth[(r["day"].year, r["day"].month)].append(i)
    keys = sorted(bymonth)
    roll = set()
    for k in keys[1:-1]:          # skip partial first month and the live month
        idx = bymonth[k]
        if len(idx) >= 5:
            roll.add(idx[-5])
    # the live month (Oct 2026) has not reached its roll yet: nothing to add
    print("\nDIAGNOSTIC (not registered): TradingView roll calendar = 5th-from-last UK business day")
    print(f"  roll days {len(roll)}:", " ".join(str(rows[i]["day"]) for i in sorted(roll)))
    x, y = [], []
    for i in sorted(roll):
        x.append(-rows[i - 1]["s"]); y.append(rows[i]["d1"] - rows[i - 1]["d1"])
    a, b, se, r2 = ols(x, y)
    print(f"  roll-day regression  n={len(x)}  a={a:+.3f}  b={b:.3f} (se {se:.3f})  R2={r2:.3f}")
    print(f"  -> H-front {'holds' if -0.3 <= b <= 0.3 else 'no'} (also needs median |d1| < 0.25|s|), "
          f"H-synthetic {'holds' if 0.7 <= b <= 1.3 else 'no'}")
    # residual check: BCO also jumping on TradingView's roll days would show as dbco - dm2 != 0
    dbco_dm2 = [(rows[i]["bco"] - rows[i-1]["bco"]) - (rows[i]["m1"] - rows[i-1]["m2"]) for i in sorted(roll)]
    print(f"  on roll days, dBCO vs the NEW front contract's own move: median |diff| {st.median(abs(v) for v in dbco_dm2):.3f}")
    # H-own-roll redone with TradingView rolls removed
    dd = [(i, rows[i]["d1"] - rows[i - 1]["d1"]) for i in range(1, len(rows)) if i not in roll]
    vals = [v for _, v in dd]; m, M = st.median(vals), mad(vals)
    out = [i for i, v in dd if abs(v - m) > 4 * M]
    exp = len(vals) * math.erfc(4 * 0.6745 / math.sqrt(2))
    months = sorted({(rows[i]["day"].year, rows[i]["day"].month) for i in out})
    print(f"  non-roll |dd1| > 4 MAD: {len(out)} of {len(vals)} (normal expects {exp:.1f}); "
          f"they fall in {len(months)} distinct months")
    hv = [i for i in out if (2026, 3) <= (rows[i]["day"].year, rows[i]["day"].month) <= (2026, 5)]
    print(f"  of which {len(hv)} in Mar-May 2026 (the high-volatility episode)")
    # position of remaining outliers within the month: a rolling series of its own would pile up
    pos = defaultdict(int)
    for i in out:
        idx = bymonth.get((rows[i]["day"].year, rows[i]["day"].month), [])
        if i in idx: pos[len(idx) - idx.index(i)] += 1
    print("  remaining outliers by trading-days-before-month-end:", dict(sorted(pos.items())))


if __name__ == "__main__":
    sys.exit(main())
