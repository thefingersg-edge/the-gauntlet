"""STRAT1 portfolio simulation (rules fixed in PREREGISTRATION_STRAT1.md). Closing-auction execution, 20 equal slots,
60-day holds, priority insider > EAR+SUE > EAR > SUE, no re-buy of a held stock, overlay blocks new entries when SPX500 is
below its 200-day MA or VIX is in the top fifth of its prior 250 values (both as of the previous close).
I am not a financial adviser. This is a measurement tool, not a recommendation."""
import os, sys, bisect, math, csv, datetime as dt, pickle
import numpy as np
from collections import defaultdict
import ss_events2 as S, pead_engine as E
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, "..")
PRI = {"INS": 0, "EARSUE": 1, "EAR": 2, "SUE": 3}

def overlay():
    sys.path.insert(0, os.path.join(FB, "scripts"))
    from daily_close import daily
    spx = daily("spx500usd"); ds = sorted(spx); c = np.array([spx[d][0] for d in ds])
    ma = {ds[i]: c[i] > c[i - 199:i + 1].mean() for i in range(199, len(ds))}
    vix = {}
    for r in csv.DictReader(open(os.path.join(FB, "data", "VIXCLS.csv"))):
        try: vix[dt.date.fromisoformat(r["date"])] = float(r["vix"])
        except ValueError: pass
    vd = sorted(vix); vv = np.array([vix[d] for d in vd]); hot = {vd[i]: vv[i] > np.quantile(vv[i - 250:i], 0.8) for i in range(250, len(vd))}
    def ok(day_int):                                 # entry decided at the close of day_int using the previous close
        d = dt.date(1970, 1, 1) + dt.timedelta(days=int(day_int))
        i = bisect.bisect_left(ds, d) - 1; j = bisect.bisect_left(vd, d) - 1
        if i < 0 or j < 0: return True
        return bool(ma.get(ds[i], True)) and not bool(hot.get(vd[j], False))
    return ok

def signals(band, bench, bad, good, longs, sue, ins):
    sig = []
    ear_by = defaultdict(list)
    for e in longs: sig.append(("EAR", e["t"], e["known"], e["ear"])); ear_by[e["t"]].append(e["ad"])
    thr = S_thr = None
    from batch2_run import sue_threshold
    thr = sue_threshold(sue, 0.9)
    for t, d, rp, v in sue:
        if d < 13940: continue                       # 2008-03 onwards (insider data start); EAR/SUE from same date for comparability
        th = thr(d)
        if np.isfinite(th) and v >= th:
            lab = "EARSUE" if any(0 <= d - a <= 60 for a in ear_by.get(t, [])) else "SUE"
            sig.append((lab, t, d, v))
    for t, d in ins: sig.append(("INS", t, d, 0.0))
    sig = [s for s in sig if s[2] >= 13940]
    recs = S.study([(t, d, lab, v) for lab, t, d, v in sig], band, bench, bad, good, execution="close")
    return [r for r in recs if r["band"] in ("M", "S")]

def simulate(recs, slots=20, use_overlay=True, cost_frac=0.25, ok=None):
    S.costs(recs, cost_frac)
    byday = defaultdict(list)
    for r in recs: byday[r["entry"]].append(r)
    alldays = sorted({int(d) for r in recs for d in r["dates"]} | set(byday))
    held = []; out_l, out_h, npos = [], [], []
    for day in alldays:
        held = [h for h in held if h["i"] < len(h["r"]["dates"])]
        # returns realised today by positions bought on earlier closes
        rl = rh = 0.0
        for h in held:
            r = h["r"]
            if h["i"] < len(r["dates"]) and r["dates"][h["i"]] == day:
                rl += float(r["rpath"][h["i"]]) / slots; rh += float(r["path"][h["i"]]) / slots; h["i"] += 1
        held = [h for h in held if h["i"] < len(h["r"]["dates"])]
        # new entries at today's close
        cands = sorted(byday.get(day, []), key=lambda r: (PRI[r["extra"][0]], -float(r["extra"][1]) if r["extra"][0] != "INS" else 0))
        names = {h["r"]["t"] for h in held}
        if not use_overlay or ok(day):
            for r in cands:
                if len(held) >= slots: break
                if r["t"] in names or len(r["dates"]) == 0: continue
                held.append({"r": r, "i": 0}); names.add(r["t"]); rl -= r["cost"] / slots; rh -= r["cost"] / slots
        out_l.append((day, rl)); out_h.append((day, rh)); npos.append(len(held))
    return np.array(out_l), np.array(out_h), np.array(npos)

def stats(x, lo=None):
    if lo: x = x[x[:, 0] >= lo]
    r = x[:, 1]; eq = np.cumprod(1 + r); dd = (eq / np.maximum.accumulate(eq) - 1).min()
    return r.mean() / r.std() * math.sqrt(252) if r.std() > 0 else float("nan"), dd, eq[-1] ** (252 / len(r)) - 1

def run(P, band, bench, bad, good):
    from batch2_run import pead1_longs, LOAD
    longs = pead1_longs(); sue = LOAD("sue_events.pkl"); ins = LOAD("insider_clusters.pkl")
    recs = signals(band, bench, bad, good, longs, sue, ins); ok = overlay()
    P(f"  candidate signals with outcomes (M+S, 2008-03+): {len(recs)}  by trigger " + str({k: sum(r['extra'][0] == k for r in recs) for k in PRI}))
    L, Hh, npos = simulate(recs, 20, True, 0.25, ok)
    y18 = (dt.date(2018, 1, 1) - dt.date(1970, 1, 1)).days
    # benchmark: equal-weight M+S (average of the two band benchmarks), same days
    bm = np.array([(d, np.mean([v for v in (bench.get((int(d), "M")), bench.get((int(d), "S"))) if v is not None] or [0.0])) for d in L[:, 0]])
    sh_h, dd_h, cg_h = stats(Hh); sh_h18, _, _ = stats(Hh, y18)
    g1 = sh_h >= 0.5 and sh_h18 >= 0.5
    P(f"  average positions held {npos.mean():.1f} of 20")
    P(f"  G1 hedged: Sharpe 2008-26 {sh_h:+.2f}, 2018-26 {sh_h18:+.2f}  (CAGR {cg_h*100:+.1f}%, max DD {dd_h*100:.1f}%)  -> {'PASS' if g1 else 'FAIL'}")
    sl, dl, cl = stats(L); sb, db, cb = stats(bm); sl18, dl18, _ = stats(L, y18); sb18, db18, _ = stats(bm, y18)
    g2 = sl > sb and dl > db and sl18 > sb18 and dl18 > db18
    P(f"  G2 long-only: 2008-26 Sharpe {sl:+.2f} vs benchmark {sb:+.2f}, max DD {dl*100:.1f}% vs {db*100:.1f}% (CAGR {cl*100:+.1f}% vs {cb*100:+.1f}%)")
    P(f"                2018-26 Sharpe {sl18:+.2f} vs {sb18:+.2f}, max DD {dl18*100:.1f}% vs {db18*100:.1f}%  -> {'PASS' if g2 else 'FAIL'}")
    eras = []
    for lo, hi in ((2008, 2012), (2013, 2019), (2020, 2026)):
        a = (dt.date(lo, 1, 1) - dt.date(1970, 1, 1)).days; b = (dt.date(hi + 1, 1, 1) - dt.date(1970, 1, 1)).days
        m = (Hh[:, 0] >= a) & (Hh[:, 0] < b); eras.append(float(np.prod(1 + Hh[m, 1]) - 1))
    g3 = all(e > 0 for e in eras)
    P("  G3 hedged total return by era: " + "  ".join(f"{e*100:+.1f}%" for e in eras) + f"  -> {'PASS' if g3 else 'FAIL'}")
    P(f"\n  VERDICT STRAT1 G1 {'P' if g1 else 'F'} G2 {'P' if g2 else 'F'} G3 {'P' if g3 else 'F'} -> {'PASS' if g1 and g2 and g3 else 'FAIL'}")
    P("\n  reported:")
    for sl_ in (10, 40):
        l_, h_, _ = simulate(recs, sl_, True, 0.25, ok); P(f"    {sl_} slots: hedged Sharpe {stats(h_)[0]:+.2f} (2018+ {stats(h_, y18)[0]:+.2f});  long-only Sharpe {stats(l_)[0]:+.2f}, DD {stats(l_)[1]*100:.1f}%")
    l_, h_, _ = simulate(recs, 20, False, 0.25, ok); P(f"    no overlay: hedged Sharpe {stats(h_)[0]:+.2f};  long-only Sharpe {stats(l_)[0]:+.2f}, DD {stats(l_)[1]*100:.1f}%")
    l_, h_, _ = simulate(recs, 20, True, 1.0, ok); P(f"    cost at 100% of EDGE: hedged Sharpe {stats(h_)[0]:+.2f} (2018+ {stats(h_, y18)[0]:+.2f});  long-only Sharpe {stats(l_)[0]:+.2f}")
    for k in PRI:
        sub = [r for r in recs if r["extra"][0] == k]
        if len(sub) > 100:
            l_, h_, _ = simulate(sub, 20, True, 0.25, ok); P(f"    {k:<6} alone: hedged Sharpe {stats(h_)[0]:+.2f} (2018+ {stats(h_, y18)[0]:+.2f})")
