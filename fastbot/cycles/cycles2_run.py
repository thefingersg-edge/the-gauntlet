#!/usr/bin/env python3
"""CYCLES1.1 (merge bear-market rallies) and CYCLES2 Part S (bear-peak fingerprint, Shiller variables).
python3 cycles2_run.py dating     -> data/cycles/phases11_monthly.csv, phases11_daily.csv, run_cycles11.log
python3 cycles2_run.py S          -> data/cycles/run_cycles2_S.log
python3 cycles2_run.py F          -> Part F (needs data/cycles/fred/*.csv from fred_cycles_pull.py)
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, hashlib, math
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(FB, "scripts"))
from cycles1_run import date_phases, describe, NBER, END
OUT = os.path.join(FB, "data", "cycles")
PIN = {os.path.join(FB, "DEFINITION_CYCLES1.1.md"): "652048d85133d9322dbea618c7e5f4b91bb3224008498f68d623de90a50f7734",
       os.path.join(FB, "PREREGISTRATION_CYCLES2.md"): "3770e1332bf18875e197dd435568b58ecfa5183c7fa160eb5f5129f1f2a61141"}


def pin():
    for f, h in PIN.items():
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} changed -- refused")


def merge(ph, x, dates, short):
    """CYCLES1.1: a bull shorter than `short` between two bears, where the second bear's trough is lower, is a bear-market rally."""
    ph = [dict(p) for p in ph]; changed = True
    while changed:
        changed = False
        for k in range(1, len(ph) - 1):
            a, b, c = ph[k - 1], ph[k], ph[k + 1]
            if b["kind"] == "bull" and a["kind"] == "bear" and c["kind"] == "bear" and short(dates[b["start"]], dates[b["end"]]) \
                    and x[c["end"]] < x[a["end"]]:
                ph[k - 1:k + 2] = [dict(kind="bear", start=a["start"], end=c["end"], confirm=a["confirm"], open=c["open"])]
                changed = True; break
    return ph


def self_test():
    x = np.array([100, 125, 90, 70, 90, 60, 80, 100.0]); d = [pd.Timestamp("2000-01-01") + pd.DateOffset(months=i) for i in range(len(x))]
    ph, _ = date_phases(x); m = merge(ph, x, d, lambda s, e: (e - s).days < 243)
    k = [(p["kind"], p["start"], p["end"]) for p in m]
    ok = ("bear", 1, 5) in k and not any(p["kind"] == "bull" and p["start"] == 3 for p in m)
    print(f"  self-test: bear-market rally merged {'OK' if ok else 'BROKEN'}  {k}")
    if not ok: sys.exit("self-test broken")


def shiller():
    S = pd.read_csv(os.path.join(OUT, "shiller_monthly.csv"), parse_dates=["Date"]); return S[S["SP500"] > 0].reset_index(drop=True)


def dating():
    pin(); self_test(); L = ["CYCLES1.1 -- 20% rule with bear-market rallies (< 8 months, lower low after) merged",
                             "  I am not a financial adviser. This is a measurement, not a recommendation.", ""]
    S = shiller(); d, x = list(S["Date"]), S["SP500"].to_numpy(float)
    ph, _ = date_phases(x); ph11 = merge(ph, x, d, lambda s, e: (e.year - s.year) * 12 + e.month - s.month < 8)
    R = describe(d, x, ph11, "m"); old = describe(d, x, ph, "m")
    L.append(f"  MONTHLY S&P 1871-2026: CYCLES1 {sum(r['kind'] == 'bear' for r in old)} bears -> CYCLES1.1 {sum(r['kind'] == 'bear' for r in R)} bears")
    merged = [r for r in R if r["kind"] == "bear" and not any(o["kind"] == "bear" and o["start"] == r["start"] and o["end"] == r["end"] for o in old)]
    for r in merged: L.append(f"    merged: bear {r['start']} -> {r['end']}  {r['move_pct']:+.1f}%  confirmed {r['confirm']}  gone@conf {r['share_gone_at_confirm']}")
    B = [r for r in R if r["kind"] == "bear" and not r["open"]]
    L.append(f"    bears: median depth {np.median([r['move_pct'] for r in B]):+.1f}%, median length {np.median([r['duration'] for r in B]):.0f} months, "
             f"median lag {np.median([r['lag_to_confirm'] for r in B]):.0f} months, median share gone at confirmation {np.median([r['share_gone_at_confirm'] for r in B]):.0%}, "
             f"median further fall after confirmation {np.median([r['rest_after_confirm_pct'] for r in B]):+.1f}%")
    with open(os.path.join(OUT, "phases11_monthly.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(R[0].keys())); w.writeheader(); [w.writerow(r) for r in R]
    from daily_close import daily
    allr = []
    for stem in ("spx500usd", "nas100usd", "uk100gbp", "xauusd"):
        dd = daily(stem); ks = sorted(k for k in dd if pd.Timestamp(k) < END); dts = [pd.Timestamp(k) for k in ks]; xx = np.array([dd[k][0] for k in ks])
        ph, _ = date_phases(xx); p11 = merge(ph, xx, dts, lambda s, e: (e - s).days < 243); R = describe(dts, xx, p11, "d")
        L.append(f"\n  DAILY {stem}: {sum(p['kind'] == 'bear' for p in ph)} bears -> {sum(p['kind'] == 'bear' for p in p11)}")
        for r in R:
            if r["kind"] == "bear":
                r["instrument"] = stem; allr.append(r)
                L.append(f"    bear {r['start']} -> {r['end']}  {r['move_pct']:+.1f}%  {r['duration']} d  confirmed {r['confirm']} (lag {r['lag_to_confirm']} d, "
                         f"{(r['share_gone_at_confirm'] or float('nan')):.0%} gone, then {(r['rest_after_confirm_pct'] or float('nan')):+.1f}%){'  open' if r['open'] else ''}")
    with open(os.path.join(OUT, "phases11_daily.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["instrument"] + [k for k in allr[0] if k != "instrument"]); w.writeheader(); [w.writerow(r) for r in allr]
    open(os.path.join(OUT, "run_cycles11.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))


def sign_p(k, n):
    from math import comb
    m = max(k, n - k); return min(1.0, 2 * sum(comb(n, i) for i in range(m, n + 1)) / 2 ** n)


def fingerprint(F, dates, peaks, nfeat, L):
    """F: DataFrame of features indexed like dates. peaks: list of indices (peak months)."""
    n = len(dates); after = np.zeros(n, bool)
    for p in peaks:
        for t in range(max(0, p - 12), p): after[t] = True          # a bear peak within (t, t+12]
    L.append(f"    {'feature':<34}{'peaks':>6}{'median pct':>11}{'same side':>10}{'sign p':>9}  {'char?':<6}{'12m before':>11}"
             f"{'flagged':>9}{'precision':>10}{'base':>7}{'lift':>6}")
    for f in F.columns:
        v = F[f].to_numpy(float); ok = np.isfinite(v)
        if ok.sum() < 120: L.append(f"    {f:<34} too little data"); continue
        pct = lambda t: (np.sum(v[ok] < v[t]) + 0.5 * np.sum(v[ok] == v[t])) / ok.sum()
        P = [p for p in peaks if np.isfinite(v[p])]; pc = np.array([pct(p) for p in P])
        pb = np.array([pct(p - 12) for p in P if p >= 12 and np.isfinite(v[p - 12])])
        hi = int((pc > 0.5).sum()); side = 1 if hi >= len(pc) - hi else -1; same = max(hi, len(pc) - hi)
        p_ = sign_p(hi, len(pc)); ch = same >= 2 * len(pc) / 3 and p_ < 0.05 / nfeat
        q = np.nanquantile(v[ok], 0.8 if side > 0 else 0.2); flag = ok & ((v >= q) if side > 0 else (v <= q))
        prec = after[flag].mean(); base = after[ok].mean()
        L.append(f"    {f:<34}{len(pc):>6}{np.median(pc):>11.2f}{same:>6}/{len(pc):<3}{p_:>9.3f}  {'YES' if ch else 'no':<6}{np.median(pb):>11.2f}"
                 f"{flag.sum():>9}{prec:>10.1%}{base:>7.1%}{prec / base:>6.2f}")


def part_S():
    pin(); L = ["CYCLES2 Part S -- the fingerprint of bear-market peaks, Shiller variables (CYCLES1.1 monthly peaks)",
                "  percentiles are within all months where the feature exists; 'char?' = >= 2/3 same side AND sign p < 0.01 (0.05/5)",
                "  haystack: months in the extreme quintile on the peaks' side; precision = share followed by a bear peak within 12 months",
                "  I am not a financial adviser. This is a measurement, not a recommendation.", ""]
    S = shiller(); d = list(S["Date"]); x = S["SP500"].to_numpy(float)
    nz = lambda c: S[c].where(S[c] > 0)
    cape = nz("PE10"); s1 = pd.Series(np.nan, index=S.index)
    cv = cape.to_numpy(); fin = np.flatnonzero(np.isfinite(cv))
    for j, t in enumerate(fin):
        if j + 1 >= 120: h = cv[fin[:j + 1]]; s1[t] = (np.sum(h < cv[t]) + 0.5 * np.sum(h == cv[t])) / len(h)
    re_ = nz("Real Earnings"); lr = nz("Long Interest Rate"); cpi = nz("Consumer Price Index")
    F = pd.DataFrame({"S1 CAPE (expanding percentile)": s1,
                      "S2 real earnings 12m chg (lag 3m)": re_.shift(3) / re_.shift(15) - 1,
                      "S3 long rate 12m chg (pp)": lr - lr.shift(12),
                      "S4 CPI 12m chg": cpi / cpi.shift(12) - 1,
                      "S5 S&P 12m chg": pd.Series(x) / pd.Series(x).shift(12) - 1})
    ph, _ = date_phases(x); ph11 = merge(ph, x, d, lambda s, e: (e.year - s.year) * 12 + e.month - s.month < 8)
    peaks = [p["start"] for p in ph11 if p["kind"] == "bear"]
    full = [p for p in peaks if F.iloc[p].notna().all()]
    L.append(f"  bear peaks: {len(peaks)} in total; {len(full)} have all five features: " + ", ".join(str(d[p].date())[:7] for p in full) + "\n")
    fingerprint(F, d, full, 5, L)
    L.append("\n  CAPE level at each peak: " + ", ".join(f"{str(d[p].date())[:4]} {cape[p]:.0f}" for p in full))
    open(os.path.join(OUT, "run_cycles2_S.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))


def part_F():
    pin(); fd = os.path.join(OUT, "fred")
    if not os.path.isdir(fd): sys.exit("no data/cycles/fred/ -- run fred_cycles_pull.py on the Mac first")
    def m(s):
        z = pd.read_csv(os.path.join(fd, f"{s}.csv"), parse_dates=["date"]); z["value"] = pd.to_numeric(z["value"], errors="coerce")
        return z.set_index("date")["value"].resample("MS").mean()
    S = shiller(); idx = pd.DatetimeIndex(S["Date"]); x = S["SP500"].to_numpy(float); d = list(S["Date"])
    g = {s: m(s).reindex(idx) for s in ("BAA", "AAA", "GS10", "TB3MS", "FEDFUNDS", "UNRATE", "INDPRO", "WTISPLC", "CPIAUCSL", "UMCSENT", "PERMIT")}
    F = pd.DataFrame({"F1 Baa-Aaa 12m chg": (g["BAA"] - g["AAA"]) - (g["BAA"] - g["AAA"]).shift(12),
                      "F2 10y - 3m level": g["GS10"] - g["TB3MS"],
                      "F3 fed funds 12m chg": g["FEDFUNDS"] - g["FEDFUNDS"].shift(12),
                      "F4 unemployment minus 12m low": g["UNRATE"] - g["UNRATE"].rolling(12).min(),
                      "F5 industrial prod 12m chg": g["INDPRO"] / g["INDPRO"].shift(12) - 1,
                      "F6 real oil 12m chg": (g["WTISPLC"] / g["CPIAUCSL"]) / (g["WTISPLC"] / g["CPIAUCSL"]).shift(12) - 1,
                      "F7 sentiment 12m chg": g["UMCSENT"] - g["UMCSENT"].shift(12),
                      "F8 building permits 12m chg": g["PERMIT"] / g["PERMIT"].shift(12) - 1}).reset_index(drop=True)
    ph, _ = date_phases(x); ph11 = merge(ph, x, d, lambda s, e: (e.year - s.year) * 12 + e.month - s.month < 8)
    peaks = [p["start"] for p in ph11 if p["kind"] == "bear"]
    L = ["CYCLES2 Part F -- the fingerprint of bear-market peaks, FRED variables (each feature uses every peak where it exists)",
         "  'char?' = >= 2/3 same side AND sign p < 0.00625 (0.05/8)", "  I am not a financial adviser. This is a measurement, not a recommendation.", ""]
    fingerprint(F, d, peaks, 8, L)
    rec = m("USREC").reindex(idx).to_numpy()
    L.append("\n  USREC check vs the typed NBER table: " + ("MATCH" if all(rec[i] == (1 if any(pd.Timestamp(a) < idx[i] <= pd.Timestamp(b) for a, b in NBER) else 0)
                                                                    for i in range(len(idx)) if np.isfinite(rec[i])) else "MISMATCH -- inspect"))
    open(os.path.join(OUT, "run_cycles2_F.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else ""
    {"dating": dating, "S": part_S, "F": part_F}.get(a, lambda: print(__doc__))()
