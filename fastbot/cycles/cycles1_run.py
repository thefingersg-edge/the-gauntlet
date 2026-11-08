#!/usr/bin/env python3
"""CYCLES1 (DEFINITION_CYCLES1.md): date bull and bear markets with the 20% rule and measure how late the label arrives.
python3 cycles1_run.py        -> data/cycles/phases_monthly.csv, phases_daily.csv, data/cycles/run_cycles1.log
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, hashlib, math
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, os.path.join(FB, "scripts"))
OUT = os.path.join(FB, "data", "cycles")
PIN = {os.path.join(FB, "DEFINITION_CYCLES1.md"): "fa06a3ff268a75f2bf19fafed1cc115da665a942821a9aff7b5672529b162436"}
END = pd.Timestamp("2026-09-26")
# NBER US business-cycle peak / trough months (published NBER chronology; verify against FRED USREC on the next FRED pull)
NBER = [("1869-06", "1870-12"), ("1873-10", "1879-03"), ("1882-03", "1885-05"), ("1887-03", "1888-04"), ("1890-07", "1891-05"),
        ("1893-01", "1894-06"), ("1895-12", "1897-06"), ("1899-06", "1900-12"), ("1902-09", "1904-08"), ("1907-05", "1908-06"),
        ("1910-01", "1912-01"), ("1913-01", "1914-12"), ("1918-08", "1919-03"), ("1920-01", "1921-07"), ("1923-05", "1924-07"),
        ("1926-10", "1927-11"), ("1929-08", "1933-03"), ("1937-05", "1938-06"), ("1945-02", "1945-10"), ("1948-11", "1949-10"),
        ("1953-07", "1954-05"), ("1957-08", "1958-04"), ("1960-04", "1961-02"), ("1969-12", "1970-11"), ("1973-11", "1975-03"),
        ("1980-01", "1980-07"), ("1981-07", "1982-11"), ("1990-07", "1991-03"), ("2001-03", "2001-11"), ("2007-12", "2009-06"),
        ("2020-02", "2020-04")]


def pin():
    for f, h in PIN.items():
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} changed -- refused")


def date_phases(x, thr=0.20):
    """20% rule on closes x (np array). Returns phases [dict(kind, start, end, confirm, open)] by index, and corrections."""
    n = len(x); state = None; hi = lo = x[0]; hi_i = lo_i = 0; ph = []; corr = []; start = None; conf = None
    clow, clow_i = None, None                     # lowest close since the current bull high (for corrections)
    for i in range(1, n):
        v = x[i]
        if state is None:
            if v > hi: hi, hi_i = v, i
            if v < lo: lo, lo_i = v, i
            if v <= (1 - thr) * hi: state, start, conf, lo, lo_i = "bear", hi_i, i, v, i
            elif v >= (1 + thr) * lo: state, start, conf, hi, hi_i, clow, clow_i = "bull", lo_i, i, v, i, v, i
            continue
        if state == "bull":
            if v > hi:
                if clow is not None and 1 - clow / hi >= 0.10: corr.append((hi_i, clow_i, 1 - clow / hi))
                hi, hi_i, clow, clow_i = v, i, v, i
            elif v < clow: clow, clow_i = v, i
            if v <= (1 - thr) * hi:
                ph.append(dict(kind="bull", start=start, end=hi_i, confirm=conf, open=False))
                state, start, conf, lo, lo_i = "bear", hi_i, i, v, i
        else:
            if v < lo: lo, lo_i = v, i
            if v >= (1 + thr) * lo:
                ph.append(dict(kind="bear", start=start, end=lo_i, confirm=conf, open=False))
                state, start, conf, hi, hi_i, clow, clow_i = "bull", lo_i, i, v, i, v, i
    if state: ph.append(dict(kind=state, start=start, end=(hi_i if state == "bull" else lo_i), confirm=conf, open=True))
    return ph, corr


def self_test():
    x = np.array([100, 110, 120, 100, 95, 90, 100, 115, 130, 125, 140, 105, 100, 125.0])
    ph, corr = date_phases(x)
    kinds = [(p["kind"], p["start"], p["end"], p["confirm"]) for p in ph]
    want = [("bull", 0, 2, 2), ("bear", 2, 5, 4), ("bull", 5, 10, 7), ("bear", 10, 12, 11), ("bull", 12, 13, 13)]
    ok = kinds == want and len(corr) == 0
    x2 = np.array([100, 125, 110, 130, 100.0]); _, c2 = date_phases(x2); ok &= len(c2) == 1 and abs(c2[0][2] - 0.12) < 1e-9
    print(f"  self-test: planted path dated {'OK' if ok else 'BROKEN'}")
    if not ok: sys.exit("self-test broken")


def describe(dates, x, ph, unit):
    rows = []
    for p in ph:
        s, e, c = p["start"], p["end"], p["confirm"]
        move = x[e] / x[s] - 1; lg = math.log(x[e] / x[s]); gone = math.log(x[c] / x[s]) / lg if lg != 0 and c <= e else float("nan")
        lag = (dates[c] - dates[s]).days if unit == "d" else (dates[c].year - dates[s].year) * 12 + dates[c].month - dates[s].month
        dur = (dates[e] - dates[s]).days if unit == "d" else (dates[e].year - dates[s].year) * 12 + dates[e].month - dates[s].month
        rows.append(dict(kind=p["kind"], start=str(dates[s].date()), end=str(dates[e].date()), confirm=str(dates[c].date()), open=p["open"],
                         move_pct=round(100 * move, 1), duration=dur, lag_to_confirm=lag, share_gone_at_confirm=round(gone, 2) if c <= e else None,
                         rest_after_confirm_pct=round(100 * (x[e] / x[c] - 1), 1) if c <= e else None))
    return rows


def detector(dates, x, sig, ph, horizon_days):
    """sig: bool array (True = 'bear' signal). Episodes = runs of True. Catch / false alarm / lag vs bears."""
    st = np.flatnonzero(sig & ~np.r_[False, sig[:-1]])
    bears = [p for p in ph if p["kind"] == "bear"]
    caught, lags, gone = 0, [], []
    for b in bears:
        f = [i for i in st if b["start"] <= i <= b["end"]] or ([b["start"]] if sig[b["start"]] else [])
        if f:
            caught += 1; i = f[0]; lags.append((dates[i] - dates[b["start"]]).days)
            gone.append(math.log(x[i] / x[b["start"]]) / math.log(x[b["end"]] / x[b["start"]]))
    inb = np.zeros(len(x), bool)
    for b in bears: inb[b["start"]:b["end"] + 1] = True
    conf = [dates[b["confirm"]] for b in bears]
    fa = sum(1 for i in st if not inb[i] and not any(dates[i] < c <= dates[i] + pd.Timedelta(days=horizon_days) for c in conf))
    return len(bears), caught, fa, len(st), (np.median(lags) if lags else float("nan")), (np.median(gone) if gone else float("nan"))


def main():
    pin(); self_test(); os.makedirs(OUT, exist_ok=True)
    L = ["CYCLES1 -- bull and bear markets by the 20% rule (DEFINITION_CYCLES1.md sha fa06a3ff…)",
         "  I am not a financial adviser. This is a measurement, not a recommendation.", ""]
    # ---------------- monthly S&P 1871 -> 2026
    S = pd.read_csv(os.path.join(OUT, "shiller_monthly.csv"), parse_dates=["Date"]); S = S[S["SP500"] > 0].reset_index(drop=True)
    d, x = list(S["Date"]), S["SP500"].to_numpy(float)
    ph, corr = date_phases(x); R = describe(d, x, ph, "m")
    nb = [(pd.Timestamp(a), pd.Timestamp(b)) for a, b in NBER]
    def ctx(r):
        s, e = pd.Timestamp(r["start"]), pd.Timestamp(r["end"]); i, j = S.index[S["Date"] == s][0], S.index[S["Date"] == e][0]
        rec = any(s - pd.DateOffset(months=12) <= a <= e for a, b in nb)
        cape = S["PE10"][i] if S["PE10"][i] > 0 else float("nan")
        re_ = S["Real Earnings"][j] / S["Real Earnings"][i] - 1 if S["Real Earnings"][i] > 0 and S["Real Earnings"][j] > 0 else float("nan")
        lr = S["Long Interest Rate"][j] - S["Long Interest Rate"][i] if S["Long Interest Rate"][j] > 0 else float("nan")
        cpi = S["Consumer Price Index"][i] / S["Consumer Price Index"][i - 12] - 1 if i >= 12 and S["Consumer Price Index"][i] > 0 else float("nan")
        return rec, cape, re_, lr, cpi
    L.append("  MONTHLY S&P Composite (Shiller monthly averages), 1871-01 -> 2026-09")
    L.append(f"    {'kind':<5}{'peak/trough':>12}{'end':>12}{'confirmed':>12}{'move %':>8}{'months':>7}{'lag m':>6}{'gone@conf':>10}{'rest %':>8}"
             f"   recession  CAPE@peak  real EPS chg  long-rate chg  CPI yoy@peak")
    for r in R:
        rec, cape, re_, lr, cpi = ctx(r) if r["kind"] == "bear" else (None,) * 5
        r.update(recession=rec, cape_at_peak=cape, real_eps_chg=re_, long_rate_chg=lr, cpi_yoy_at_peak=cpi)
        extra = (f"   {'yes' if rec else 'no':>9}  {cape:9.1f}  {100 * re_:+11.0f}%  {lr:+12.2f}  {100 * cpi:+11.1f}%" if r["kind"] == "bear" else "")
        L.append(f"    {r['kind']:<5}{r['start']:>12}{r['end']:>12}{r['confirm']:>12}{r['move_pct']:+8.1f}{r['duration']:>7}{r['lag_to_confirm']:>6}"
                 f"{(r['share_gone_at_confirm'] if r['share_gone_at_confirm'] is not None else float('nan')):>10.2f}"
                 f"{(r['rest_after_confirm_pct'] if r['rest_after_confirm_pct'] is not None else float('nan')):+8.1f}{'  (open)' if r['open'] else ''}{extra}")
    bears = [r for r in R if r["kind"] == "bear" and not r["open"]]; bulls = [r for r in R if r["kind"] == "bull" and not r["open"]]
    L.append(f"\n    {len(bears)} completed bears, {len(bulls)} completed bulls; {len(corr)} corrections (10-20%) inside bulls")
    L.append(f"    bears: median depth {np.median([r['move_pct'] for r in bears]):+.1f}%, median length {np.median([r['duration'] for r in bears]):.0f} months, "
             f"median lag peak->confirmation {np.median([r['lag_to_confirm'] for r in bears]):.0f} months, "
             f"median share of the fall already gone at confirmation {np.median([r['share_gone_at_confirm'] for r in bears]):.0%}")
    L.append(f"    bulls: median gain {np.median([r['move_pct'] for r in bulls]):+.0f}%, median length {np.median([r['duration'] for r in bulls]):.0f} months, "
             f"median share of the rise already gone at confirmation {np.median([r['share_gone_at_confirm'] for r in bulls]):.0%}")
    L.append(f"    bears overlapping an NBER recession: {sum(r['recession'] for r in bears)} of {len(bears)}")
    recs_hit = sum(any(pd.Timestamp(b['start']) - pd.DateOffset(months=12) <= a <= pd.Timestamp(b['end']) for b in bears) for a, _ in nb if a >= d[0])
    L.append(f"    NBER recessions since 1871 with a bear around them: {recs_hit} of {sum(1 for a, _ in nb if a >= d[0])}")
    sma10 = pd.Series(x).rolling(10).mean().to_numpy(); sig = np.where(np.isnan(sma10), False, x < sma10)
    nbr, c_, fa, eps, lag, gone = detector(d, x, sig, ph, 183)
    L.append(f"    detector: monthly close < 10-month SMA -> caught {c_} of {nbr} bears, median first signal {lag:.0f} days after the peak "
             f"({gone:.0%} of the fall gone); {eps} signal episodes, {fa} false alarms")
    with open(os.path.join(OUT, "phases_monthly.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(R[0].keys()) + [k for k in ("recession", "cape_at_peak", "real_eps_chg", "long_rate_chg", "cpi_yoy_at_peak") if k not in R[0]])
        w.writeheader(); [w.writerow(r) for r in R]
    with open(os.path.join(OUT, "corrections_monthly.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["high", "low", "depth_pct"]); [w.writerow([str(d[a].date()), str(d[b].date()), round(100 * c, 1)]) for a, b, c in corr]
    # ---------------- daily 2005 -> 2026
    from daily_close import daily
    allrows = []
    for stem in ("spx500usd", "nas100usd", "uk100gbp", "xauusd"):
        dd = daily(stem); ks = sorted(k for k in dd if pd.Timestamp(k) < END); dts = [pd.Timestamp(k) for k in ks]; xx = np.array([dd[k][0] for k in ks])
        ph, corr = date_phases(xx); R = describe(dts, xx, ph, "d")
        L.append(f"\n  DAILY {stem} cash closes {dts[0].date()} -> {dts[-1].date()}")
        L.append(f"    {'kind':<5}{'peak/trough':>12}{'end':>12}{'confirmed':>12}{'move %':>8}{'days':>6}{'lag d':>6}{'gone@conf':>10}{'rest %':>8}")
        for r in R:
            r["instrument"] = stem; allrows.append(r)
            L.append(f"    {r['kind']:<5}{r['start']:>12}{r['end']:>12}{r['confirm']:>12}{r['move_pct']:+8.1f}{r['duration']:>6}{r['lag_to_confirm']:>6}"
                     f"{(r['share_gone_at_confirm'] if r['share_gone_at_confirm'] is not None else float('nan')):>10.2f}"
                     f"{(r['rest_after_confirm_pct'] if r['rest_after_confirm_pct'] is not None else float('nan')):+8.1f}{'  (open; first phase starts mid-move)' if r['open'] or r is R[0] else ''}")
        L.append(f"    corrections (10-20%) inside bulls: {len(corr)}  -> " + ", ".join(f"{dts[a].date()} {-100 * c:.0f}%" for a, b, c in corr))
        sma = pd.Series(xx).rolling(200).mean().to_numpy(); sig = np.where(np.isnan(sma), False, xx < sma)
        nbr, c_, fa, eps, lag, gone = detector(dts, xx, sig, ph, 183)
        L.append(f"    detector: close < 200-day SMA -> caught {c_} of {nbr} bears, median first signal {lag:.0f} days after the peak "
                 f"({gone:.0%} of the fall gone); {eps} signal episodes, {fa} false alarms")
    with open(os.path.join(OUT, "phases_daily.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["instrument"] + [k for k in allrows[0] if k != "instrument"]); w.writeheader(); [w.writerow(r) for r in allrows]
    open(os.path.join(OUT, "run_cycles1.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
