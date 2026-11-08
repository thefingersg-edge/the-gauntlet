#!/usr/bin/env python3
"""BUYBACK1 harness (PREREGISTRATION_BUYBACK1). One run.  SS_STORE=~/store python3 buyback1_run.py
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, io, bisect, subprocess, datetime as dt, numpy as np, pandas as pd
import ss_lib
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); sys.path.insert(0, os.path.join(FB, "scripts"))
from tsmom1_run import daily
from breadth_v56 import nw_ols
D0 = dt.date(1970, 1, 1)
def main():
    log = os.path.join(FB, "data", "run_buyback1.log")
    if os.path.exists(log): sys.exit("already run")
    OUT = []; P = lambda s="": (print(s, flush=True), OUT.append(s))
    P("buyback1_run.py  PREREGISTRATION_BUYBACK1\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    rows = list(csv.DictReader(io.StringIO(subprocess.run(["unzip", "-p", ss_lib.find("sp500")], capture_output=True, text=True).stdout)))
    snaps, evs = {}, []
    for r in rows:
        if r["action"] == "historical": snaps.setdefault(r["date"], set()).add(r["ticker"])
        elif r["action"] in ("added", "removed"): evs.append((r["date"], r["action"], r["ticker"]))
    items = sorted([(d, 0, a, t) for d, a, t in evs] + [(d, 1, "snap", d) for d in snaps])
    ann = {}
    for t, d in ss_lib.announcements(ss_lib.find("events")): ann.setdefault(t, []).append(d)
    for t in ann: ann[t].sort()
    spx = daily("SPX500_USD", os.path.join(FB, "data", "v24")); days = list(spx.index); c = spx["C"].to_numpy()
    tdays = np.array([(d.date() - D0).days for d in days])
    def blackout_end(t, qend):
        L = ann.get(t, []); i = bisect.bisect_right(L, qend)
        if i >= len(L) or L[i] > qend + 75: return None
        k = bisect.bisect_left(tdays, L[i]); return int(tdays[min(k + 2, len(tdays) - 1)])
    cur, k, B, cov = set(), 0, [], []
    for di, d in enumerate(days):
        s = d.date().isoformat()
        while k < len(items) and items[k][0] <= s:
            _, _, a, t = items[k]
            if a == "snap": cur = set(snaps[t])
            elif a == "added": cur.add(t)
            else: cur.discard(t)
            k += 1
        x = (d.date() - D0).days; dd = d.date(); inb = n = 0
        # relevant quarter end: the most recent quarter end, or the coming one if within 14 days
        qe_next = dt.date(dd.year + (dd.month > 9), ((dd.month - 1) // 3 * 3 + 3) % 12 or 12, 1)
        qe_next = (pd.Timestamp(qe_next) + pd.offsets.MonthEnd(0)).date()
        qe_prev = (pd.Timestamp(dd.replace(day=1)) - pd.offsets.QuarterEnd(1)).date() if dd != (pd.Timestamp(dd) + pd.offsets.QuarterEnd(0)).date() else dd
        for t in cur:
            if (qe_next - dd).days <= 14: inb += 1; n += 1; continue
            qx = (qe_prev - D0).days; e = blackout_end(t, qx)
            if e is None: continue
            n += 1; inb += x <= e
        B.append(100 * inb / n if n else np.nan); cov.append(n / max(len(cur), 1))
    B = np.array(B); r5 = np.full(len(c), np.nan); r20 = np.full(len(c), np.nan)
    r5[:-5] = (c[5:] / c[:-5] - 1) * 1e4; r20[:-20] = (c[20:] / c[:-20] - 1) * 1e4
    yr = np.array([d.year for d in days]); m = np.isfinite(B) & np.isfinite(r5) & (np.array(days) >= pd.Timestamp("2005-04-01"))
    b, t = nw_ols(r5[m], B[m] / 10, 5); g1 = b[1] < 0 and t[1] <= -2.0
    P(f"  days {m.sum()}; blackout share mean {np.nanmean(B[m]):.0f}% (range {np.nanmin(B[m]):.0f}-{np.nanmax(B[m]):.0f}%); members with an earnings date {100*np.mean(np.array(cov)[m]):.0f}%")
    P(f"  G1 5-day SPX return on blackout share: {b[1]:+.2f} bp per 10pp (NW t {t[1]:+.2f})  -> {'PASS' if g1 else 'FAIL'}")
    er = []
    for a, z in ((2005, 2012), (2013, 2019), (2020, 2026)):
        mm = m & (yr >= a) & (yr <= z); be, te = nw_ols(r5[mm], B[mm] / 10, 5); er.append((be[1], te[1]))
    g2 = all(e[0] < 0 for e in er); P("  G2 eras " + "  ".join(f"{e[0]:+.2f} (t {e[1]:+.2f})" for e in er) + f"  -> {'PASS' if g2 else 'FAIL'}")
    hi, lo = m & (B >= 60), m & (B <= 20)
    P(f"\n  reported: B>=60% days {hi.sum()}: mean 5d {np.nanmean(r5[hi]):+.1f} bp;  B<=20% days {lo.sum()}: {np.nanmean(r5[lo]):+.1f} bp")
    m20 = m & np.isfinite(r20); b2, t2 = nw_ols(r20[m20], B[m20] / 10, 20); P(f"  reported: 20-day horizon slope {b2[1]:+.2f} bp per 10pp (NW t {t2[1]:+.2f})")
    P(f"\n  VERDICT BUYBACK1 G1 {'P' if g1 else 'F'} G2 {'P' if g2 else 'F'} -> {'PASS' if g1 and g2 else 'FAIL'}")
    open(log, "w").write("\n".join(OUT) + "\n")
if __name__ == "__main__": main()
