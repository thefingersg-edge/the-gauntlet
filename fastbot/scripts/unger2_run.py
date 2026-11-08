#!/usr/bin/env python3
"""UNGER2 harness (PREREGISTRATION_UNGER2.md, sha ead63712...): Unger's published example systems tested from their publication dates.
    python3 unger2_run.py --self-test
    python3 unger2_run.py A | B | C | D | F       -> data/unger2/run_unger2_<part>.log   (each refuses to run twice)
Data: data/unger2/de30_5m.npz (unger2_build.py dax), data/v51/{xauusd,wticousd}_15m.npz (struct15), data/unger2/{CL,GC}_15m.npz (unger2_build.py futures).

Mechanical readings fixed here BEFORE any run (logged in PROVENANCE):
  * Times: OANDA and Databento timestamps are UTC bar starts. DAX uses Europe/Berlin; gold and crude use America/Chicago, both DST-aware.
  * Missing spreads: DAX before 2012 takes the 2012-14 median and WTI before 2013 the 2013-15 median (the UNGER batch rule). This touches only
    reported windows for DAX, and 2010-12 for crude C/D.
  * Futures costs per side: 1 tick + half the $2.50 round trip -> CL 0.01 + 0.00125 $/bbl, GC 0.10 + 0.0125 $/oz. Trades with a contract roll
    inside them are excluded from the stats (counted). The SMA in C runs on the unadjusted continuous series (disclosed).
  * A: the opening range needs >= 10 of its 12 5m bars. The previous trading day (08:00-21:55 Berlin) must exist and have high > low. A signal is a
    5m close beyond the level in bars starting 09:00-09:55, entered at the next bar's open. The stop is checked from the entry bar onward
    (fill = level, or the open if gapped). Flat at the close of the last bar starting before 22:00. Re-entry after a stop is allowed on later signal bars.
  * B: the session starts 17:00 CT; hour h = 1 + (minutes since 17:00 CT) // 60; 60m highs and lows come from the 15m bars. Long levels = the
    previous hour's high; short levels = the lowest low of the previous 3 hours. Entries trigger on 15m bars inside the window; the stop is entry
    -/+ $17; long exit at the first bar at or after 01:00 CT of the next session; short exit at the first bar of hour >= 17 (09:00 CT).
    In each bar: timed exit (at the open), then the stop, then a new entry, then a same-bar stop check (conservative).
  * D: the prior session needs >= 40 15m bars. Exit at the open of the first bar at or after 15:45 CT (else the session's last close).
    When both levels trigger in one bar, the level nearer that bar's open is taken.
  * CFD financing: each 17:00 New York roll held pays (r + 2.5%)/365 long or receives (r - 2.5%)/365 short; a roll on a Friday counts 3 nights. USD rates.
  * Day-clustered t: the per-trade mean divided by sqrt(sum over entry days of (sum of demeaned trade returns)^2) / n.
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, math, hashlib, csv
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, HERE)
SPEC = os.path.join(FB, "PREREGISTRATION_UNGER2.md"); SPEC_SHA = "ead637125fb9c3eb19bb2bb8ef51d479e466193e326b934cffb92f377ce972e4"
OUT = os.path.join(FB, "data", "unger2"); END = pd.Timestamp("2026-10-01")
DISC = "I am not a financial adviser. This is a measurement, not a recommendation."
T_FAM, T_D = 2.24, 2.81
FUT = {"CL": (0.01 + 0.00125, 1000), "GC": (0.10 + 0.0125, 100)}      # cost per side ($ per unit), contract units


def pin():
    if hashlib.sha256(open(SPEC, "rb").read()).hexdigest() != SPEC_SHA: sys.exit("spec changed -- refused")


# ------------------------------------------------------------------ data
def usd_rates():
    R = {}
    for r in csv.DictReader(open(os.path.join(FB, "data", "policy_rates.csv"))):
        if r["currency"] == "USD": R[r["month"]] = float(r["rate_pct"]) / 100
    return R


def bars_cfd(stem):
    from struct15 import load15
    d = load15(stem); m = d["t"] < np.datetime64(END); d = {k: v[m].copy() for k, v in d.items()}
    yr = pd.DatetimeIndex(d["t"].astype("datetime64[ns]")).year.to_numpy()
    if stem == "wticousd":
        med = float(np.median(d["spr"][(yr >= 2013) & (yr <= 2015)])); d["spr"][yr < 2013] = med
    return dict(t=d["t"], o=d["o"], h=d["h"], l=d["l"], c=d["c"], spr=d["spr"], roll=np.zeros(len(d["t"]), bool), kind="cfd")


def bars_dax():
    z = np.load(os.path.join(OUT, "de30_5m.npz")); d = {k: z[k] for k in z.files}
    m = d["t"] < np.datetime64(END); d = {k: v[m].copy() for k, v in d.items()}
    yr = pd.DatetimeIndex(d["t"].astype("datetime64[ns]")).year.to_numpy()
    med = float(np.median(d["spr"][(yr >= 2012) & (yr <= 2014) & (d["spr"] > 0)])); d["spr"][(yr < 2012) | (d["spr"] <= 0)] = med
    return dict(t=d["t"], o=d["o"], h=d["h"], l=d["l"], c=d["c"], spr=d["spr"], roll=np.zeros(len(d["t"]), bool), kind="cfd")


def bars_fut(root):
    z = np.load(os.path.join(OUT, f"{root}_15m.npz")); d = {k: z[k] for k in z.files}
    m = d["t"] < np.datetime64(END); d = {k: v[m] for k, v in d.items()}
    return dict(t=d["t"], o=d["o"], h=d["h"], l=d["l"], c=d["c"], spr=np.zeros(m.sum()), roll=d["roll"], kind="fut", root=root)


def local(t, tz):
    return pd.DatetimeIndex(t.astype("datetime64[ns]")).tz_localize("UTC").tz_convert(tz)


# ------------------------------------------------------------------ trade accounting
def side_cost(B, i, px):
    if B["kind"] == "cfd": return 0.5 * B["spr"][i] * 1e-4 * px
    return FUT[B["root"]][0]


def ny_rolls(t0, t1):
    """17:00 New York rolls strictly after t0 and at or before t1 (UTC numpy datetimes). Returns a list of (NY date of the roll, nights)."""
    a = pd.Timestamp(t0).tz_localize("UTC").tz_convert("America/New_York"); b = pd.Timestamp(t1).tz_localize("UTC").tz_convert("America/New_York")
    out = []; d = a.normalize() + pd.Timedelta(hours=17)
    if d <= a: d += pd.Timedelta(days=1)
    while d <= b:
        if d.weekday() < 5: out.append((d, 3 if d.weekday() == 4 else 1))
        d += pd.Timedelta(days=1)
    return out


def finance(B, R, t0, t1):
    """(fin_long, fin_short) as fractions of notional; zero for futures."""
    if B["kind"] != "cfd": return 0.0, 0.0
    fl = fs = 0.0
    for d, n in ny_rolls(t0, t1):
        r = R.get(d.strftime("%Y-%m"), 0.02); fl += n / 365 * (r + 0.025); fs += -n / 365 * (r - 0.025)
    return fl, fs


def trade(B, R, i0, px0, i1, px1, side):
    c = side_cost(B, i0, px0) + side_cost(B, i1, px1); fl, fs = finance(B, R, B["t"][i0], B["t"][i1])
    rl = bool(B["roll"][i0 + 1:i1 + 1].any()) if i1 > i0 else False
    return dict(t0=B["t"][i0], t1=B["t"][i1], side=side, p0=px0, p1=px1, cost=c, fl=fl, fs=fs, roll=rl)


def frame(trs):
    T = pd.DataFrame(trs)
    if not len(T): return T
    T["gross_bp"] = T["side"] * (T["p1"] - T["p0"]) / T["p0"] * 1e4
    T["fin"] = np.where(T["side"] > 0, T["fl"], T["fs"])
    T["net_bp"] = T["gross_bp"] - T["cost"] / T["p0"] * 1e4 - T["fin"] * 1e4
    T["net_px"] = T["side"] * (T["p1"] - T["p0"]) - T["cost"] - T["fin"] * T["p0"]
    T["day"] = pd.DatetimeIndex(T["t0"].astype("datetime64[ns]")).normalize()
    return T


def ct(x, days):
    x = np.asarray(x, float); n = len(x)
    if n < 3: return float("nan")
    u = x - x.mean(); S = pd.Series(u).groupby(np.asarray(days)).sum().to_numpy()
    se = math.sqrt((S ** 2).sum()) / n
    return x.mean() / se if se > 0 else float("nan")


def placebo(T, draws=1000, seed=0):
    rng = np.random.default_rng(seed); n = len(T)
    mv = (T["p1"] - T["p0"]).to_numpy(); p0 = T["p0"].to_numpy(); c = T["cost"].to_numpy(); fl, fs = T["fl"].to_numpy(), T["fs"].to_numpy()
    out = np.empty(draws)
    for k in range(draws):
        s = rng.choice([-1, 1], size=n)
        out[k] = np.mean(s * mv / p0 * 1e4 - c / p0 * 1e4 - np.where(s > 0, fl, fs) * 1e4)
    return out


def window(T, a, b):
    t = pd.DatetimeIndex(T["t0"].astype("datetime64[ns]")); return T[(t >= pd.Timestamp(a)) & (t < pd.Timestamp(b))]


def summarize(T, label, a, b, halves, tthr, gate=True):
    W = window(T, a, b); W = W[~W["roll"]]; nroll = int(window(T, a, b)["roll"].sum())
    if len(W) < 5: return [f"  {label}: {len(W)} trades -- too few"], False
    m, t = W["net_bp"].mean(), ct(W["net_bp"], W["day"])
    hs = [window(W, x, y)["net_bp"].mean() for x, y in halves]
    pl = placebo(W); p95 = float(np.percentile(pl, 95))
    yrs = (pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25
    g1 = m > 0 and t >= tthr; g2 = all(np.isfinite(h) and h > 0 for h in hs); g3 = m > p95
    L = [f"  {label}: {len(W)} trades ({len(W) / yrs:.0f}/yr{', ' + str(nroll) + ' excluded for a roll' if nroll else ''}); "
         f"gross {W['gross_bp'].mean():+.2f} bp, net {m:+.2f} bp/trade (day-clustered t {t:+.2f}); win rate {(W['net_bp'] > 0).mean() * 100:.0f}%",
         "     halves " + " / ".join(f"{h:+.2f}" for h in hs) + f";  random-side placebo mean {pl.mean():+.2f}, 95th pct {p95:+.2f}"]
    if gate: L.append(f"     G1 {'PASS' if g1 else 'FAIL'} (t >= {tthr})  G2 {'PASS' if g2 else 'FAIL'}  G3 {'PASS' if g3 else 'FAIL'}  -> {'PASS' if g1 and g2 and g3 else 'FAIL'}")
    return L, g1 and g2 and g3


# ------------------------------------------------------------------ A: DAX opening range
def sys_A(B, R, stop_fill=False, use_dfactor=True, skip_friday=True):
    lt = local(B["t"], "Europe/Berlin"); hm = (lt.hour * 60 + lt.minute).to_numpy(); day = lt.normalize().tz_localize(None).to_numpy()
    o, h, l, c = B["o"], B["h"], B["l"], B["c"]
    ud, start = np.unique(day, return_index=True); end = np.r_[start[1:], len(day)]
    trs = []; prev = None
    for di in range(len(ud)):
        s, e = start[di], end[di]; hmd = hm[s:e]
        sess = np.flatnonzero((hmd >= 480) & (hmd < 1320)) + s
        rng = np.flatnonzero((hmd >= 480) & (hmd < 540)) + s
        P = prev
        if len(sess): prev = (o[sess[0]], h[sess].max(), l[sess].min(), c[sess[-1]])
        wd = pd.Timestamp(ud[di]).weekday()
        if skip_friday and wd == 4: continue
        if len(rng) < 10 or P is None or not len(sess): continue
        if use_dfactor:
            if P[1] <= P[2] or abs(P[3] - P[0]) / (P[1] - P[2]) >= 0.5: continue
        HH, LL = h[rng].max(), l[rng].min(); dl = HH - LL
        if dl <= 0: continue
        up, dn = HH + dl, LL - dl
        bars = [i for i in range(s, e) if 540 <= hm[i] < 1320]
        pos = 0; ent = None; k = 0
        while k < len(bars):
            i = bars[k]
            if pos == 0:
                if hm[i] >= 600: break
                if stop_fill:
                    sd = 1 if h[i] >= up else (-1 if l[i] <= dn else 0)
                    if sd: pos, ent = sd, (i, max(o[i], up) if sd > 0 else min(o[i], dn))
                    else: k += 1; continue
                else:
                    sd = 1 if c[i] > up else (-1 if c[i] < dn else 0)
                    if sd and k + 1 < len(bars): k += 1; i = bars[k]; pos, ent = sd, (i, o[i])
                    else: k += 1; continue
            stop = HH if pos > 0 else LL
            hit = (l[i] <= stop) if pos > 0 else (h[i] >= stop)
            if hit:
                fill = (min(o[i], stop) if pos > 0 else max(o[i], stop)) if i != ent[0] else stop
                if i == ent[0] and ((pos > 0 and o[i] <= stop) or (pos < 0 and o[i] >= stop)): fill = o[i]
                trs.append(trade(B, R, ent[0], ent[1], i, fill, pos)); pos = 0; k += 1; continue
            k += 1
        if pos != 0:
            i = bars[-1]; trs.append(trade(B, R, ent[0], ent[1], i, c[i], pos))
    return frame(trs)


# ------------------------------------------------------------------ B: gold hourly breakout
def sys_B(B, R, stop_usd=17.0):
    lt = local(B["t"], "America/Chicago"); mm = (lt.hour * 60 + lt.minute).to_numpy()
    off = (mm - 1020) % 1440; hr = off // 60 + 1
    sid = (lt + pd.Timedelta(hours=7)).normalize().tz_localize(None).to_numpy()      # session label = the date it ends
    o, h, l, c = B["o"], B["h"], B["l"], B["c"]; n = len(o)
    key = sid.astype("datetime64[D]").astype(np.int64) * 100 + hr
    uk, kidx = np.unique(key, return_inverse=True)
    H60 = np.full(len(uk), -np.inf); L60 = np.full(len(uk), np.inf); np.maximum.at(H60, kidx, h); np.minimum.at(L60, kidx, l)
    trs = []; pos = 0; ent = None; esid = None; stop = None; took = set()
    for i in range(n):
        g = kidx[i]
        # 1. timed exit at this bar's open
        if pos > 0 and sid[i] > esid and hr[i] >= 9:
            trs.append(trade(B, R, ent[0], ent[1], i, o[i], 1)); pos = 0
        elif pos < 0 and (sid[i] != esid or hr[i] >= 17):
            trs.append(trade(B, R, ent[0], ent[1], i, o[i], -1)); pos = 0
        # 2. stop on a bar after entry
        if pos != 0 and i != ent[0]:
            if pos > 0 and l[i] <= stop: trs.append(trade(B, R, ent[0], ent[1], i, min(o[i], stop), 1)); pos = 0
            elif pos < 0 and h[i] >= stop: trs.append(trade(B, R, ent[0], ent[1], i, max(o[i], stop), -1)); pos = 0
        # 3. entries
        if pos == 0 and g >= 3:
            if 18 <= hr[i] <= 22 and (sid[i], 1) not in took:
                lv = H60[g - 1]
                if h[i] >= lv:
                    pos, ent, esid, stop = 1, (i, max(o[i], lv)), sid[i], max(o[i], lv) - stop_usd; took.add((sid[i], 1))
                    if l[i] <= stop: trs.append(trade(B, R, i, ent[1], i, stop, 1)); pos = 0
            elif 9 <= hr[i] <= 12 and (sid[i], -1) not in took:
                lv = min(L60[g - 1], L60[g - 2], L60[g - 3])
                if l[i] <= lv:
                    pos, ent, esid, stop = -1, (i, min(o[i], lv)), sid[i], min(o[i], lv) + stop_usd; took.add((sid[i], -1))
                    if h[i] >= stop: trs.append(trade(B, R, i, ent[1], i, stop, -1)); pos = 0
    return frame(trs)


# ------------------------------------------------------------------ C: crude SMA 30/140 stop-and-reverse
def sys_C(B, R):
    c, o = B["c"], B["o"]; f = pd.Series(c).rolling(30).mean().to_numpy(); s = pd.Series(c).rolling(140).mean().to_numpy()
    up = (f > s) & (np.r_[False, f[:-1] <= s[:-1]]); dn = (f < s) & (np.r_[False, f[:-1] >= s[:-1]])
    trs = []; pos = 0; ent = None
    for i in range(140, len(c) - 1):
        sd = 1 if up[i] else (-1 if dn[i] else 0)
        if sd and sd != pos:
            j = i + 1
            if pos != 0: trs.append(trade(B, R, ent[0], ent[1], j, o[j], pos))
            pos, ent = sd, (j, o[j])
    if pos != 0: trs.append(trade(B, R, ent[0], ent[1], len(c) - 1, c[-1], pos))
    return frame(trs)


# ------------------------------------------------------------------ D: crude prior-session breakout entered early
def sys_D(B, R, k_ticks, tick=0.01):
    lt = local(B["t"], "America/Chicago"); mm = (lt.hour * 60 + lt.minute).to_numpy(); off = (mm - 1020) % 1440
    sid = (lt + pd.Timedelta(hours=7)).normalize().tz_localize(None).to_numpy()
    o, h, l, c = B["o"], B["h"], B["l"], B["c"]
    us, st = np.unique(sid, return_index=True); en = np.r_[st[1:], len(sid)]
    trs = []
    for si in range(1, len(us)):
        ps, pe = st[si - 1], en[si - 1]
        if pe - ps < 40: continue
        PH, PL = h[ps:pe].max(), l[ps:pe].min(); BL, SL = PH - k_ticks * tick, PL + k_ticks * tick
        s, e = st[si], en[si]; pos = 0; ent = None
        for i in range(s, e):
            if off[i] >= 1365:
                if pos != 0: trs.append(trade(B, R, ent[0], ent[1], i, o[i], pos)); pos = 0
                break
            if pos == 0 and ent is None:
                ev = []
                if h[i] >= BL: ev.append((abs(o[i] - BL), 1, max(o[i], BL)))
                if l[i] <= SL: ev.append((abs(o[i] - SL), -1, min(o[i], SL)))
                if ev: ev.sort(key=lambda x: x[0]); _, pos, px = ev[0]; ent = (i, px)
        if pos != 0: trs.append(trade(B, R, ent[0], ent[1], e - 1, c[e - 1], pos))
    return frame(trs)


# ------------------------------------------------------------------ parts
def guard(part):
    p = os.path.join(OUT, f"run_unger2_{part}.log")
    if os.path.exists(p): sys.exit("already run")
    return p


def usd_per_contract(T, root):
    return T["net_px"].mean() * FUT[root][1], (T["side"] * (T["p1"] - T["p0"])).mean() * FUT[root][1]


def part_A():
    R = usd_rates(); B = bars_dax(); P = guard("A")
    L = ["UNGER2 A -- UNGERDAX1, DAX opening-range breakout (published 2016-06-10)", "  " + DISC, ""]
    T = sys_A(B, R); hv = (("2016-06-10", "2021-08-01"), ("2021-08-01", "2026-10-01"))
    l, ok = summarize(T, "PRIMARY 2016-06-10 -> 2026-09-30", "2016-06-10", "2026-10-01", hv, T_FAM); L += l
    L += summarize(T, "pre-publication 2005 -> 2016-06-09 (reported)", "2005-01-01", "2016-06-10", (("2005-01-01", "2010-12-31"), ("2011-01-01", "2016-06-10")), T_FAM, gate=False)[0]
    W = window(T, "2016-06-10", "2026-10-01")
    L.append(f"  long {W[W.side > 0]['net_bp'].mean():+.2f} bp (n {int((W.side > 0).sum())}), short {W[W.side < 0]['net_bp'].mean():+.2f} bp (n {int((W.side < 0).sum())})")
    for nm, kw in (("stop-order fills", dict(stop_fill=True)), ("no Dfactor filter", dict(use_dfactor=False)), ("Fridays included", dict(skip_friday=False))):
        L += summarize(sys_A(B, R, **kw), f"variant: {nm}", "2016-06-10", "2026-10-01", hv, T_FAM, gate=False)[0]
    L += ["", f"  UNGERDAX1: {'PASS' if ok else 'FAIL'}"]
    open(P, "w").write("\n".join(L) + "\n"); print("\n".join(L))


def gold_lines(T, label_root):
    L = []; hv = (("2022-01-13", "2024-05-15"), ("2024-05-15", "2026-10-01"))
    l, ok = summarize(T, f"{label_root} PRIMARY 2022-01-13 -> 2026-09-30", "2022-01-13", "2026-10-01", hv, T_FAM); L += l
    L += summarize(T, f"{label_root} source's backtest era 2010-01 -> 2022-01-12 (reported)", "2010-01-01", "2022-01-13",
                   (("2010-01-01", "2014-12-31"), ("2015-01-01", "2022-01-13")), T_FAM, gate=False)[0]
    W = window(T, "2022-01-13", "2026-10-01")
    L.append(f"     long {W[W.side > 0]['net_bp'].mean():+.2f} bp (n {int((W.side > 0).sum())}), short {W[W.side < 0]['net_bp'].mean():+.2f} bp (n {int((W.side < 0).sum())}); "
             f"stopped out {((W['p1'] - W['p0']).abs().round(6) >= 16.99).mean() * 100:.0f}%")
    return L, ok


def part_B():
    R = usd_rates(); B = bars_cfd("xauusd"); P = guard("B")
    L = ["UNGER2 B -- UNGERGOLD1, gold hourly breakout with time windows (published 2022-01-13), OANDA XAU CFD", "  " + DISC, ""]
    T = sys_B(B, R); l, ok = gold_lines(T, "CFD"); L += l
    W = window(T, "2022-01-13", "2026-10-01"); L.append(f"     per 100 oz (one GC contract): net ${W['net_px'].mean() * 100:+.0f}, gross ${(W['side'] * (W['p1'] - W['p0'])).mean() * 100:+.0f} vs the source's ~$52")
    L += ["", f"  UNGERGOLD1 (CFD): {'PASS' if ok else 'FAIL'}"]
    open(P, "w").write("\n".join(L) + "\n"); print("\n".join(L))


def cl_lines(T, tag):
    hv = (("2010-01-01", "2018-01-01"), ("2018-01-01", "2026-10-01"))
    a = "2010-06-07" if tag == "futures" else "2010-01-01"
    l, ok = summarize(T, f"{tag} PRIMARY {a} -> 2026-09-30", a, "2026-10-01", hv, T_FAM); return l, ok


def part_C():
    R = usd_rates(); B = bars_cfd("wticousd"); P = guard("C")
    L = ["UNGER2 C -- UNGERCL1, crude 15m SMA 30/140 stop-and-reverse, bare core (published 2025-04-04), OANDA WTI CFD", "  " + DISC, ""]
    T = sys_C(B, R); l, ok = cl_lines(T, "CFD"); L += l
    W = window(T, "2010-01-01", "2026-10-01")
    L.append(f"     per 1,000 bbl: net ${W['net_px'].mean() * 1000:+.2f}, gross ${(W['side'] * (W['p1'] - W['p0'])).mean() * 1000:+.2f}, win rate {(W['net_px'] > 0).mean() * 100:.1f}%"
             f"  vs his stated $219.66 and 27.69%  -> gap ${219.66 - W['net_px'].mean() * 1000:+.2f} per trade = what his withheld filters/session add (if his figure is net)")
    L += summarize(T, "since publication 2025-04-04 (descriptive)", "2025-04-04", "2026-10-01", (("2025-04-04", "2025-12-31"), ("2026-01-01", "2026-10-01")), T_FAM, gate=False)[0]
    L += ["", f"  UNGERCL1 (CFD): {'PASS' if ok else 'FAIL'}"]
    open(P, "w").write("\n".join(L) + "\n"); print("\n".join(L))


def d_lines(B, R, tag):
    L = []; anyok = False; hv = (("2010-01-01", "2018-01-01"), ("2018-01-01", "2026-10-01"))
    a = "2010-06-07" if tag == "futures" else "2010-01-01"
    for k in (0, 5, 10, 20, 40):
        T = sys_D(B, R, k); l, ok = summarize(T, f"{tag} k = {k:2d} ticks", a, "2026-10-01", hv, T_D); L += l; anyok |= ok
        W = window(T, a, "2026-10-01"); W = W[~W["roll"]]
        L.append(f"     per 1,000 bbl net ${W['net_px'].mean() * 1000:+.2f} (his stated $166.53)")
    return L, anyok


def part_D():
    R = usd_rates(); B = bars_cfd("wticousd"); P = guard("D")
    L = ["UNGER2 D -- UNGERCL2, crude prior-session breakout entered early (published 2025-04-04), OANDA WTI CFD; grid Bonferroni t >= 2.81", "  " + DISC, ""]
    l, ok = d_lines(B, R, "CFD"); L += l + ["", f"  UNGERCL2 (CFD): {'PASS' if ok else 'FAIL'} (any k passing G1-G3)"]
    open(P, "w").write("\n".join(L) + "\n"); print("\n".join(L))


def part_F():
    R = usd_rates(); P = guard("F")
    L = ["UNGER2 F -- B, C, D on CME futures (Databento CL.v.0 / GC.v.0, 1m -> 15m); 1 tick + $1.25 per side, no financing", "  " + DISC, ""]
    G = bars_fut("GC"); T = sys_B(G, R); l, okB = gold_lines(T, "GC futures"); L += l
    W = window(T, "2022-01-13", "2026-10-01"); W = W[~W["roll"]]; n_, g_ = usd_per_contract(W, "GC")
    L.append(f"     per GC contract: net ${n_:+.0f}, gross ${g_:+.0f} vs the source's ~$52"); L.append("")
    C = bars_fut("CL"); T = sys_C(C, R); l, okC = cl_lines(T, "futures"); L += l
    W = window(T, "2010-06-07", "2026-10-01"); W = W[~W["roll"]]; n_, g_ = usd_per_contract(W, "CL")
    L.append(f"     per CL contract: net ${n_:+.2f}, gross ${g_:+.2f}, win rate {(W['net_px'] > 0).mean() * 100:.1f}% vs his $219.66 / 27.69%  -> gap ${219.66 - n_:+.2f}"); L.append("")
    l, okD = d_lines(C, R, "futures"); L += l
    L += ["", f"  F verdicts: UNGERGOLD1 {'PASS' if okB else 'FAIL'}, UNGERCL1 {'PASS' if okC else 'FAIL'}, UNGERCL2 {'PASS' if okD else 'FAIL'}"]
    open(P, "w").write("\n".join(L) + "\n"); print("\n".join(L))


# ------------------------------------------------------------------ self-test
def mkB(times_utc, o, h, l, c, kind="cfd", spr=0.0):
    n = len(o); t = np.array(times_utc, dtype="datetime64[m]")
    B = dict(t=t, o=np.array(o, float), h=np.array(h, float), l=np.array(l, float), c=np.array(c, float), spr=np.full(n, spr), roll=np.zeros(n, bool), kind=kind)
    if kind == "fut": B["root"] = "CL"
    return B


def self_test():
    ok = True; R = {}
    def chk(name, cond):
        nonlocal ok; ok &= bool(cond); print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    # financing roll counting
    r = ny_rolls(np.datetime64("2026-01-08T20:00"), np.datetime64("2026-01-12T23:00"))       # Thu 15:00 NY -> Mon 18:00 NY
    chk("17:00 NY rolls Thu..Mon = Thu(1) + Fri(3) + Mon(1)", [n for _, n in r] == [1, 3, 1])
    # clustered t equals plain t when one trade per day
    x = np.random.default_rng(2).normal(1, 3, 400); days = np.arange(400)
    tp = x.mean() / (x.std(ddof=0) / math.sqrt(400)); chk("day-clustered t = plain t with one trade per day", abs(ct(x, days) - tp) < 1e-9)
    # A: build a Thursday (2026-01-08) with a prior Wednesday doji; Berlin = UTC+1 in January
    ts, O, H, Lo, C = [], [], [], [], []
    def add(day, hmB, op, hi, lo, cl):
        u = pd.Timestamp(f"{day} 00:00") + pd.Timedelta(minutes=hmB - 60); ts.append(u.to_datetime64()); O.append(op); H.append(hi); Lo.append(lo); C.append(cl)
    for m in range(480, 1320, 5): add("2026-01-07", m, 100, 101, 99, 100)                # Dfactor 0
    for m in range(480, 540, 5): add("2026-01-08", m, 100, 101, 99, 100)                 # range 99-101, delta 2 -> up 103
    add("2026-01-08", 540, 100, 102, 100, 101.5); add("2026-01-08", 545, 101.5, 103.5, 101.4, 103.2)   # close 103.2 > 103 -> enter next open
    add("2026-01-08", 550, 103.3, 104, 103, 103.8)
    for m in range(555, 1320, 5): add("2026-01-08", m, 104, 105, 103.5, 104.5)
    B = mkB(ts, O, H, Lo, C); T = sys_A(B, R)
    chk("A: close beyond HH + range enters at the next open, held to 22:00", len(T) == 1 and T.iloc[0]["p0"] == 103.3 and T.iloc[0]["p1"] == 104.5 and T.iloc[0]["side"] == 1)
    B2 = mkB(ts, O, H, Lo, [x if i != len(C) - 160 else x for i, x in enumerate(C)]); B2["l"][-150] = 100.5
    T2 = sys_A(B2, R); chk("A: stop at the range high (101) fills at the level", len(T2) >= 1 and abs(T2.iloc[0]["p1"] - 101) < 1e-9)
    # B: long window and timed exit (Chicago = UTC-6 in January)
    ts, O, H, Lo, C = [], [], [], [], []
    def addc(dt_ct, op, hi, lo, cl):
        ts.append((pd.Timestamp(dt_ct) + pd.Timedelta(hours=6)).to_datetime64()); O.append(op); H.append(hi); Lo.append(lo); C.append(cl)
    t0 = pd.Timestamp("2026-01-06 17:00")
    for q in range(0, 33 * 4):
        tt = t0 + pd.Timedelta(minutes=15 * q); hrs = q // 4 + 1
        if hrs == 17: addc(tt, 100, 100.5, 99.5, 100)                 # hour 17 (09:00-10:00 CT): high 100.5
        elif hrs == 18 and q % 4 == 1: addc(tt, 100.2, 101.0, 100.1, 100.9)   # breaks 100.5 -> long at 100.5
        else: addc(tt, 100, 100.4, 99.6, 100)
    B = mkB(ts, O, H, Lo, C); T = sys_B(B, R)
    lg = T[T.side > 0]; ex_ct = pd.Timestamp(lg.iloc[0]["t1"]) - pd.Timedelta(hours=6) if len(lg) else None
    chk("B: long at the previous hour's high, exit at 01:00 CT next session", len(lg) == 1 and abs(lg.iloc[0]["p0"] - 100.5) < 1e-9 and ex_ct == pd.Timestamp("2026-01-08 01:00"))
    # C: SAR
    c = np.r_[np.full(150, 100.0), np.linspace(100, 110, 60), np.linspace(110, 95, 120)]
    tt = (pd.Timestamp("2026-01-05") + pd.to_timedelta(np.arange(len(c)) * 15, unit="m")).to_numpy()
    B = mkB(tt, c, c + 0.1, c - 0.1, c); T = sys_C(B, R)
    chk("C: long on the up-cross, reversed short on the down-cross, closed at the end", list(T["side"]) == [1, -1] and T.iloc[0]["t1"] == T.iloc[1]["t0"])
    # D: first hit, k inside
    ts, O, H, Lo, C = [], [], [], [], []
    for q in range(0, 92):
        addc(pd.Timestamp("2026-01-06 17:00") + pd.Timedelta(minutes=15 * q), 60, 61, 59, 60)
    for q in range(0, 92):
        tt = pd.Timestamp("2026-01-07 17:00") + pd.Timedelta(minutes=15 * q)
        if q == 10: addc(tt, 60.5, 60.97, 60.4, 60.9)
        else: addc(tt, 60.9, 60.95, 60.85, 60.9)
    B = mkB(ts, O, H, Lo, C); T = sys_D(B, R, 5)
    chk("D: buy stop at prior high - 5 ticks (60.95) fills at the level; exit 15:45 CT", len(T) == 1 and abs(T.iloc[0]["p0"] - 60.95) < 1e-9
        and pd.Timestamp(T.iloc[0]["t1"]) - pd.Timedelta(hours=6) == pd.Timestamp("2026-01-08 15:45"))
    # futures cost + roll exclusion
    Bf = mkB(tt := (pd.Timestamp("2026-01-05") + pd.to_timedelta(np.arange(len(c)) * 15, unit="m")).to_numpy(), c, c + 0.1, c - 0.1, c, kind="fut")
    Bf["roll"][200] = True; Tf = sys_C(Bf, R)
    chk("futures: per-side cost 0.01125 and a roll inside a trade is flagged", abs(Tf.iloc[0]["cost"] - 0.0225) < 1e-12 and Tf["roll"].any())
    print("ALL PASS" if ok else "FAILURES"); return ok


if __name__ == "__main__":
    pin(); a = sys.argv[1:]
    if a == ["--self-test"]: sys.exit(0 if self_test() else 1)
    if not self_test(): sys.exit("self-test failed")
    {"A": part_A, "B": part_B, "C": part_C, "D": part_D, "F": part_F}[a[0]]()
