#!/usr/bin/env python3
"""UNGER BATCH (PREREGISTRATION_UNGER_BATCH.md, sha ce14205e...) sections 2-6: GOLDTREND1, CONTEXT1, MULTI1, ROTATE1, TURBO1.
PROBE1-OIL (section 1) already ran via probe1_oil.py.

    python3 unger_batch.py --self-test
    python3 unger_batch.py goldtrend|context|multi|rotate|turbo     -> data/unger/run_<name>.log

Mechanical readings of the frozen spec, fixed here BEFORE any run (logged in PROVENANCE):
  * Data, trading day, clean-day rule, policy rates, NW(5) t, Sharpe sqrt(252) and eras are exactly as in probe1_run.py / probe1_oil.py.
  * Index spread imputation: bars before 2012 on SPX/NAS/UK100 take that market's median 2012-2014 bar spread (spec). WTI/Brent
    (reported only) have zero spreads before 2013 in the source, so they take their 2013-2015 median; this is disclosed and does not gate anything.
  * "Next open" rules (GOLDTREND B/C, MULTI S1/S2) hold position P[d] from the first bar of day d. Daily gross = (P[d-1](O[d]-C[d-1]) + P[d](C[d]-O[d]))/C[d-1].
    The spread is charged as |dP| x half the quoted spread of day d's first bar. Financing is charged on the position held at day d's close
    (Friday = 3 nights), as in PROBE1.
  * Intraday stop rules (GOLDTREND A, CONTEXT1) use one generalised copy of PROBE1's probe(), with the levels passed in. With prior-day levels
    and no filters, it reproduces probe1_run.probe() exactly (self-test). Spread cost = |dP| x half spread, which is identical to PROBE1's 1.0 / 0.5 rule.
  * CONTEXT1: a filter undefined on day d (warm-up) counts as OFF. Under F6, a position held against day d's allowed direction is closed at
    day d's first bar, and a reversal against it goes flat instead.
  * MULTI1 S2: a signal at close d is taken only if no position is scheduled for day d+1, so a new trade may start at the open where the
    previous one exits. S3: when both stops are crossed in one bar, the level nearer the bar's open is taken first (PROBE1's rule).
    The fill is the stop level, or the bar open if it gapped through.
  * Vol targeting: w[t] = min(5, 0.10 / (sd(net[t-60..t-1]) x sqrt 252)); no position before 60 days. Systems are aligned on calendar date
    (a missing day = 0 return), and the portfolio is the mean of the systems that have started.
  * ROTATE1: on each month's last portfolio day, rank by the sum of scaled net returns over the trailing 6 (3, 12) calendar months; hold the top 4 at
    1/4 each for the next month. Switch cost on the first day of the new month, for each system entering or leaving = 1/4 x w x |P at prior close| x half its
    last-bar spread. Monthly paired difference vs hold-all-12; NW(5) t on months.
  * TURBO1: block starts uniform on [0, n-20]; 13 blocks truncated to 252 days; equity compounded daily; a day's return <= -100% takes equity to 0.
    Ruin (equity <= 10% of start) is absorbing. Common random numbers across settings. The contest uses fresh paths (seed 0 stream continued).
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, hashlib, math
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, HERE)
import probe1_run as P
from struct15 import load15
BATCH = os.path.join(FB, "PREREGISTRATION_UNGER_BATCH.md")
BATCH_SHA = "ce14205ed8219efd19f5190ab53dcfdb62dbb4f8fcda5bf59a2c1eb0c91f3716"
OUT = os.path.join(FB, "data", "unger"); END = P.END; ERAS = P.ERAS
CUR = {"spx500usd": "USD", "nas100usd": "USD", "uk100gbp": "GBP", "xauusd": "USD", "wticousd": "USD", "bcousd": "USD"}
IMPUTE = {"spx500usd": (2012, 2014, 2012), "nas100usd": (2012, 2014, 2012), "uk100gbp": (2012, 2014, 2012),
          "wticousd": (2013, 2015, 2013), "bcousd": (2013, 2015, 2013)}
CORE = ("spx500usd", "nas100usd", "uk100gbp", "xauusd"); OIL = ("wticousd", "bcousd")
DISC = "I am not a financial adviser. This is a measurement, not a recommendation."
nw_t, sharpe = P.nw_t, P.sharpe


def pin():
    P.pin()
    if hashlib.sha256(open(BATCH, "rb").read()).hexdigest() != BATCH_SHA: sys.exit("batch spec changed -- refused")


# ---------------------------------------------------------------- data
def market(stem):
    d = load15(stem); m = d["t"] < END; d = {k: v[m].copy() for k, v in d.items()}
    yr_bar = pd.DatetimeIndex(d["t"].astype("datetime64[ns]")).year.to_numpy()
    if stem in IMPUTE:
        a, b, cut = IMPUTE[stem]; med = float(np.median(d["spr"][(yr_bar >= a) & (yr_bar <= b)])); d["spr"][yr_bar < cut] = med
    ny = pd.DatetimeIndex(d["t"].astype("datetime64[ns]")).tz_localize("UTC").tz_convert("America/New_York")
    lab = (ny + pd.Timedelta(hours=7)).normalize().tz_localize(None)
    cnt = pd.Series(lab).value_counts(); good = set(cnt[(cnt >= 0.5 * cnt.median())].index)
    keep = np.array([(x in good) and x.weekday() < 5 for x in lab])
    d = {k: v[keep] for k, v in d.items()}; lab = lab[keep]
    labels, day = np.unique(lab.to_numpy(), return_inverse=True); labels = [pd.Timestamp(x) for x in labels]
    nd = day[-1] + 1; first = np.r_[0, np.flatnonzero(np.diff(day)) + 1]; last = np.r_[first[1:] - 1, len(day) - 1]
    H = np.full(nd, -np.inf); L = np.full(nd, np.inf); np.maximum.at(H, day, d["h"]); np.minimum.at(L, day, d["l"])
    R = P.rates(CUR[stem]); rate_of = lambda t: R.get(t.strftime("%Y-%m"), 0.02)
    r = np.array([rate_of(x) for x in labels]); nights = np.array([3 if x.weekday() == 4 else 1 for x in labels])
    return dict(stem=stem, bar=d, day=day, labels=labels, rate_of=rate_of, O=d["o"][first], H=H, L=L, C=d["c"][last],
                S0=d["spr"][first], S1=d["spr"][last], first=first, last=last, r=r, nights=nights,
                yr=np.array([x.year for x in labels]), date=np.array([x.date() for x in labels]))


def daily_engine(M, Pos):
    """Position Pos[d] held from day d's first bar. Returns dict of per-day fractions (CFD and futures routes)."""
    O, C, S0, r, n = M["O"], M["C"], M["S0"], M["r"], M["nights"]
    Pp = np.r_[0.0, Pos[:-1]]; Cp = np.r_[np.nan, C[:-1]]
    gross = (Pp * (O - Cp) + Pos * (C - O)) / Cp
    dP = np.abs(Pos - Pp); cost = dP * 0.5 * S0 * 1e-4
    fin = n / 365 * np.where(Pos > 0, (r + 0.025) * Pos, np.where(Pos < 0, -(r - 0.025) * np.abs(Pos), 0.0))
    cost_f = dP * 0.5e-4; fin_f = n / 365 * r * Pos
    return dict(gross=gross, cost=cost, fin=fin, net=gross - cost - fin, net_f=gross - cost_f - fin_f, pos=Pos.astype(float),
                rev=(dP > 0).astype(int))


def probe_lv(M, HI, LO, sign=+1, active=None, allow=None):
    """PROBE1's probe() generalised: levels HI[d]/LO[d] for day d, optional active mask and allowed direction (+1/-1)."""
    b = M["bar"]; o, h, l, c, spr = b["o"], b["h"], b["l"], b["c"], b["spr"]; day = M["day"]; labels = M["labels"]; rate_of = M["rate_of"]
    nd = day[-1] + 1
    gross = np.zeros(nd); cost = np.zeros(nd); fin = np.zeros(nd); cost_f = np.zeros(nd); fin_f = np.zeros(nd)
    close = np.full(nd, np.nan); rev = np.zeros(nd, int); posc = np.zeros(nd)
    pos = 0; cur = -1
    for i in range(len(c)):
        d = day[i]; newday = d != cur
        if newday:
            if cur >= 0 and pos != 0:
                lab = labels[cur]; nights = 3 if lab.weekday() == 4 else 1; rr = rate_of(lab)
                fin[cur] = nights / 365 * ((rr + 0.025) if pos > 0 else -(rr - 0.025)); fin_f[cur] = nights / 365 * rr * pos
            cur = d
        ref = c[i - 1] if i > 0 else o[i]
        if newday and pos != 0 and ((active is not None and not active[d]) or (allow is not None and pos != allow[d])):
            gross[d] += pos * (o[i] - ref); ref = o[i]; cost[d] += 0.5 * spr[i] * 1e-4; cost_f[d] += 0.5e-4; rev[d] += 1; pos = 0
        if d >= 1 and np.isfinite(HI[d]) and (active is None or active[d]):
            PH, PL = HI[d], LO[d]; ev = []
            if h[i] >= PH: ev.append((abs(o[i] - PH), +1, (o[i] if o[i] >= PH else PH)))
            if l[i] <= PL: ev.append((abs(o[i] - PL), -1, (o[i] if o[i] <= PL else PL)))
            ev.sort(key=lambda e: e[0])
            for k, (_, side, fill) in enumerate(ev):
                if k == 1: fill = PH if side > 0 else PL
                tgt = sign * side
                if allow is not None and tgt != allow[d]: tgt = 0
                if tgt != pos:
                    gross[d] += pos * (fill - ref); ref = fill
                    cost[d] += abs(tgt - pos) * 0.5 * spr[i] * 1e-4; cost_f[d] += abs(tgt - pos) * 0.5e-4; rev[d] += 1; pos = tgt
        gross[d] += pos * (c[i] - ref); close[d] = c[i]; posc[d] = pos
    pc = np.r_[np.nan, close[:-1]]; g = gross / pc
    return dict(gross=g, cost=cost, fin=fin, net=g - cost - fin, net_f=g - cost_f - fin_f, pos=posc, rev=rev)


def prior_day_levels(M): return np.r_[np.nan, M["H"][:-1]], np.r_[np.nan, M["L"][:-1]]


def prior_week_levels(M):
    wk = np.array([(x - pd.Timedelta(days=x.weekday())).value for x in M["labels"]])
    uw, wi = np.unique(wk, return_inverse=True)
    WH = np.full(len(uw), -np.inf); WL = np.full(len(uw), np.inf); np.maximum.at(WH, wi, M["H"]); np.minimum.at(WL, wi, M["L"])
    HI = np.where(wi >= 1, WH[np.maximum(wi - 1, 0)], np.nan); LO = np.where(wi >= 1, WL[np.maximum(wi - 1, 0)], np.nan)
    return HI, LO


def rule_close_confirm(M):
    C, H, L = M["C"], M["H"], M["L"]; Pos = np.zeros(len(C)); s = 0
    for d in range(1, len(C) - 1):
        if C[d] > H[d - 1]: s = 1
        elif C[d] < L[d - 1]: s = -1
        Pos[d + 1] = s
    return Pos


def rule_channel(M, n=20):
    C = M["C"]; Pos = np.zeros(len(C)); s = 0
    for d in range(n, len(C) - 1):
        w = C[d - n:d]
        if C[d] > w.max(): s = 1
        elif C[d] < w.min(): s = -1
        Pos[d + 1] = s
    return Pos


def rule_meanrev(M, look=5, hold=3):
    C = M["C"]; nd = len(C); Pos = np.zeros(nd)
    for d in range(look - 1, nd - 1):
        if Pos[d + 1] != 0: continue
        w = C[d - look + 1:d + 1]; side = 1 if C[d] <= w.min() else (-1 if C[d] >= w.max() else 0)
        if side: Pos[d + 1:min(nd, d + 1 + hold)] = side
    return Pos


def atr(M, n):
    H, L, C = M["H"], M["L"], M["C"]; Cp = np.r_[np.nan, C[:-1]]
    tr = np.nanmax(np.vstack([H - L, np.abs(H - Cp), np.abs(L - Cp)]), axis=0); tr[0] = H[0] - L[0]
    return pd.Series(tr).rolling(n).mean().to_numpy()            # ATR known at the close of day d


def vol_breakout(M, k=0.5, n=10):
    b = M["bar"]; o, h, l, c, spr = b["o"], b["h"], b["l"], b["c"], b["spr"]; A = atr(M, n); C = M["C"]
    nd = len(C); g = np.zeros(nd); cost = np.zeros(nd); cost_f = np.zeros(nd); rev = np.zeros(nd, int)
    for d in range(1, nd):
        if not np.isfinite(A[d - 1]): continue
        i0, i1 = M["first"][d], M["last"][d]; O = o[i0]; up, dn = O + k * A[d - 1], O - k * A[d - 1]
        for i in range(i0, i1 + 1):
            ev = []
            if h[i] >= up: ev.append((abs(o[i] - up), +1, max(o[i], up)))
            if l[i] <= dn: ev.append((abs(o[i] - dn), -1, min(o[i], dn)))
            if ev:
                ev.sort(key=lambda e: e[0]); _, side, fill = ev[0]
                g[d] = side * (c[i1] - fill) / C[d - 1]
                cost[d] = 0.5 * (spr[i] + spr[i1]) * 1e-4; cost_f[d] = 1e-4; rev[d] = 1; break
    return dict(gross=g, cost=cost, fin=np.zeros(nd), net=g - cost, net_f=g - cost_f, pos=np.zeros(nd), rev=rev)


def buyhold(M):
    C, r, n = M["C"], M["r"], M["nights"]; Cp = np.r_[np.nan, C[:-1]]
    return C / Cp - 1 - n / 365 * (r + 0.025)


def stats_line(x, yr, label):
    ok = np.isfinite(x); x, yr = x[ok], yr[ok]
    ers = [x[(yr >= a) & (yr <= b)].mean() for a, b in ERAS]
    return (f"{label}: mean {x.mean() * 1e4:+.2f} bp/day (t {nw_t(x):+.2f}, Sharpe {sharpe(x):+.2f}); eras "
            + "  ".join(f"{a}-{b % 100:02d} {e * 1e4:+.2f}" for (a, b), e in zip(ERAS, ers))), x.mean(), nw_t(x), ers


# ---------------------------------------------------------------- GOLDTREND1
def goldtrend():
    M = market("xauusd"); yr = M["yr"]; T = 2.13
    L = ["GOLDTREND1 -- slower, cheaper gold trend (PREREGISTRATION_UNGER_BATCH section 2, sha ce14205e...)", "  " + DISC, ""]
    oos = yr >= 2016; ok = np.isfinite(M["C"]) & (np.arange(len(yr)) >= 1)
    rules = {"A weekly probe": probe_lv(M, *prior_week_levels(M)),
             "B close-confirmed daily": daily_engine(M, rule_close_confirm(M)),
             "C 20-day channel": daily_engine(M, rule_channel(M))}
    npass = 0; bh = buyhold(M)
    for name, R in rules.items():
        net = R["net"]; v = ok & np.isfinite(net)
        line, mu, t, ers = stats_line(net[v], yr[v], "CFD net")
        g1 = mu > 0 and t >= T; g2 = all(e > 0 for e in ers); mo = net[v & oos]; g3 = mo.mean() > 0; ps = g1 and g2 and g3; npass += ps
        G = np.nansum(R["gross"][v]); yrs = v.sum() / 252
        L += [f"  {name}: {R['rev'][v].sum() / yrs:.1f} reversals/yr",
              f"    gross {np.nanmean(R['gross'][v]) * 1e4:+.2f} bp/day; spread {R['cost'][v].mean() * 1e4:.2f}, financing {R['fin'][v].mean() * 1e4:+.2f}"
              + (f"  (lost to spread {R['cost'][v].sum() / G * 100:.0f}% of gross, to financing {R['fin'][v].sum() / G * 100:.0f}%)" if G > 0 else "  (gross <= 0)"),
              "    " + line, f"    OOS 2016-26 CFD net {mo.mean() * 1e4:+.2f} bp/day (Sharpe {sharpe(mo):+.2f})",
              f"    futures-route net {np.nanmean(R['net_f'][v]) * 1e4:+.2f} bp/day (t {nw_t(R['net_f'][v]):+.2f}, Sharpe {sharpe(R['net_f'][v]):+.2f})",
              f"    G1 {'PASS' if g1 else 'FAIL'} (t >= {T})  G2 {'PASS' if g2 else 'FAIL'}  G3 {'PASS' if g3 else 'FAIL'}  -> {'PASS' if ps else 'FAIL'}", ""]
    b = bh[ok & np.isfinite(bh)]; bo = bh[ok & oos & np.isfinite(bh)]
    L += [f"  gold buy & hold net of CFD financing: Sharpe {sharpe(b):+.2f} (2006-26), {sharpe(bo):+.2f} (OOS)", f"  GOLDTREND1: {npass} of 3 rules PASS"]
    return L


# ---------------------------------------------------------------- CONTEXT1
def context():
    M = market("xauusd"); yr = M["yr"]; T = 2.39; nd = len(yr)
    HI, LO = prior_day_levels(M); base = probe_lv(M, HI, LO)
    A = atr(M, 20); med = pd.Series(A).rolling(250).median().to_numpy(); rng = M["H"] - M["L"]
    A1, m1 = np.r_[np.nan, A[:-1]], np.r_[np.nan, med[:-1]]
    F = {}
    F["F1 high vol (ATR20 > 250d median)"] = np.isfinite(m1) & (A1 > m1)
    F["F2 low vol (ATR20 < 250d median)"] = np.isfinite(m1) & (A1 < m1)
    nr4 = np.zeros(nd, bool); nr4[3:] = [rng[d] <= rng[d - 3:d].min() for d in range(3, nd)]
    F["F3 after NR4 day"] = np.r_[False, nr4[:-1]]
    ins = np.zeros(nd, bool); ins[1:] = (M["H"][1:] <= M["H"][:-1]) & (M["L"][1:] >= M["L"][:-1])
    F["F4 after inside day"] = np.r_[False, ins[:-1]]
    F["F5 opens inside prior range"] = np.r_[False, (M["O"][1:] >= M["L"][:-1]) & (M["O"][1:] <= M["H"][:-1])]
    sma = pd.Series(M["C"]).rolling(100).mean().to_numpy(); al = np.where(M["C"] > sma, 1, -1); al = np.r_[0, al[:-1]]
    ok6 = np.r_[False, np.isfinite(sma[:-1])]
    L = ["CONTEXT1 -- simple idea + context on the gold probe (PREREGISTRATION_UNGER_BATCH section 3, sha ce14205e...)", "  " + DISC, ""]
    v = np.isfinite(base["net"]) & (np.arange(nd) >= 1); ins_p = v & (yr <= 2015); oos = v & (yr >= 2016)
    bl, *_ = stats_line(base["net"][v], yr[v], "unfiltered probe CFD net")
    L += [f"  {bl}", f"    OOS {base['net'][oos].mean() * 1e4:+.2f} bp/day (t {nw_t(base['net'][oos]):+.2f}); 2006-15 {base['net'][ins_p].mean() * 1e4:+.2f}; "
          f"{base['rev'][v].sum() / (v.sum() / 252):.0f} reversals/yr", ""]
    npass = 0
    for name in list(F) + ["F6 with 100-day SMA direction"]:
        if name.startswith("F6"): R = probe_lv(M, HI, LO, active=ok6, allow=al)
        else: R = probe_lv(M, HI, LO, active=F[name])
        x = R["net"]; mo = x[oos]; t = nw_t(mo); g1 = mo.mean() > 0 and t >= T
        g2 = x[ins_p].mean() > base["net"][ins_p].mean() and mo.mean() > base["net"][oos].mean(); ps = g1 and g2; npass += ps
        tim = (R["pos"][v] != 0).mean()
        lifts = [(x[v & (yr >= a) & (yr <= b)].mean() - base["net"][v & (yr >= a) & (yr <= b)].mean()) * 1e4 for a, b in ERAS]
        L += [f"  {name}: in market at close {tim * 100:.0f}% of days, {R['rev'][v].sum() / (v.sum() / 252):.0f} position changes/yr",
              f"    OOS net {mo.mean() * 1e4:+.2f} bp/day (t {t:+.2f}, Sharpe {sharpe(mo):+.2f});  2006-15 {x[ins_p].mean() * 1e4:+.2f}",
              "    lift vs unfiltered by era: " + "  ".join(f"{a}-{b % 100:02d} {e:+.2f}" for (a, b), e in zip(ERAS, lifts)) + " bp/day",
              f"    G1 {'PASS' if g1 else 'FAIL'} (t >= {T})  G2 {'PASS' if g2 else 'FAIL'}  -> {'PASS' if ps else 'FAIL'}", ""]
    L.append(f"  CONTEXT1: {npass} of 6 filters PASS")
    return L, base


# ---------------------------------------------------------------- MULTI1 / ROTATE1
def systems(stems):
    out = {}
    for s in stems:
        M = market(s)
        for k, R in (("S1 trend", daily_engine(M, rule_channel(M))), ("S2 meanrev", daily_engine(M, rule_meanrev(M))), ("S3 breakout", vol_breakout(M))):
            out[(s, k)] = dict(M=M, R=R)
        out[(s, "BH")] = dict(M=M, R=dict(net=buyhold(M), net_f=buyhold(M), pos=np.ones(len(M["C"]))))
    return out


def voltarget(x):
    x = np.nan_to_num(np.asarray(x, float)); sd = pd.Series(x).rolling(60).std(ddof=0).shift(1).to_numpy() * math.sqrt(252)
    w = np.where(np.isfinite(sd) & (sd > 0), np.minimum(5.0, 0.10 / np.where(sd > 0, sd, 1)), np.where(np.isfinite(sd), 5.0, 0.0))
    return w * x, w, np.isfinite(sd)


def frame(SY, keys, field="net"):
    cols, w_, st_ = {}, {}, {}
    for k in keys:
        M, R = SY[k]["M"], SY[k]["R"]; sc, w, started = voltarget(R[field])
        idx = pd.to_datetime(M["date"]); cols[k] = pd.Series(sc, idx); w_[k] = pd.Series(w, idx); st_[k] = pd.Series(started.astype(float), idx)
    X = pd.DataFrame(cols).sort_index(); W = pd.DataFrame(w_).reindex(X.index); S = pd.DataFrame(st_).reindex(X.index).ffill().fillna(0)
    X = X.fillna(0.0); X = X[(X.index >= "2006-01-01")]; S = S.reindex(X.index); W = W.reindex(X.index)
    port = (X * S).sum(1) / S.sum(1).replace(0, np.nan)
    return X, port.dropna(), W, S


def multi():
    SY = systems(CORE + OIL)
    core = [(s, k) for s in CORE for k in ("S1 trend", "S2 meanrev", "S3 breakout")]
    oilk = [(s, k) for s in OIL for k in ("S1 trend", "S2 meanrev", "S3 breakout")]
    X, port, W, S = frame(SY, core); Xf, portf, *_ = frame(SY, core, "net_f")
    _, bh, *_ = frame(SY, [(s, "BH") for s in CORE])
    yr = port.index.year.to_numpy(); x = port.to_numpy()
    line, mu, t, ers = stats_line(x, yr, "portfolio CFD net")
    oos = port.index >= "2016-01-01"; bo = bh[bh.index >= "2016-01-01"]
    g1 = mu > 0 and t >= 2.0; g2 = all(e > 0 for e in ers); g3 = sharpe(x[oos]) > sharpe(bo.to_numpy()); ps = g1 and g2 and g3
    L = ["MULTI1 -- three simple systems per market, combined (PREREGISTRATION_UNGER_BATCH section 4, sha ce14205e...)", "  " + DISC, "",
         "  component net Sharpe (vol-targeted, 2006-26; OOS in brackets):"]
    for k in core + oilk:
        sc, *_ = voltarget(SY[k]["R"]["net"]); dd = pd.Series(sc, pd.to_datetime(SY[k]["M"]["date"])); dd = dd[dd.index >= "2006-01-01"]
        raw = SY[k]["R"]
        L.append(f"    {k[0]:10s} {k[1]:12s} {sharpe(dd.to_numpy()):+.2f} ({sharpe(dd[dd.index >= '2016-01-01'].to_numpy()):+.2f})   "
                 f"trades/yr {raw.get('rev', np.zeros(1)).sum() / (len(raw['net']) / 252):.0f}" + ("   [oil, reported only]" if k in oilk else ""))
    C = X[[c for c in X.columns]].corr().to_numpy(); avgc = C[np.triu_indices_from(C, 1)].mean()
    dr = x.std() / X.std().mean()
    L += ["", "  " + line, f"  OOS 2016-26: portfolio Sharpe {sharpe(x[oos]):+.2f}  vs equal-weight buy & hold (vol-targeted, CFD financing) {sharpe(bo.to_numpy()):+.2f}",
          f"  buy & hold 2006-26 Sharpe {sharpe(bh.to_numpy()):+.2f}",
          f"  futures-route portfolio: Sharpe {sharpe(portf.to_numpy()):+.2f} (t {nw_t(portf.to_numpy()):+.2f})",
          f"  average pairwise correlation {avgc:+.2f};  diversification ratio (portfolio vol / average component vol) {dr:.2f}",
          f"  G1 {'PASS' if g1 else 'FAIL'} (t >= 2.0)  G2 {'PASS' if g2 else 'FAIL'}  G3 {'PASS' if g3 else 'FAIL'}  -> MULTI1 {'PASS' if ps else 'FAIL'}"]
    _, po, *_ = frame(SY, core + oilk); lo, *_ = stats_line(po.to_numpy(), po.index.year.to_numpy(), "with WTI+Brent (18 systems, reported)")
    L += ["  " + lo]
    return L, SY, core


def rotate(SY=None, core=None):
    if SY is None:
        SY = systems(CORE); core = [(s, k) for s in CORE for k in ("S1 trend", "S2 meanrev", "S3 breakout")]
    X, port, W, S = frame(SY, core)
    E, SP = {}, {}
    for k in core:
        M, R = SY[k]["M"], SY[k]["R"]; idx = pd.to_datetime(M["date"])
        E[k] = pd.Series(np.abs(R["pos"]), idx); SP[k] = pd.Series(M["S1"] * 1e-4, idx)
    E = pd.DataFrame(E).reindex(X.index).ffill().fillna(0) * W.fillna(0); SP = pd.DataFrame(SP).reindex(X.index).ffill()
    mon = X.index.to_period("M"); months = mon.unique()
    msum = X.groupby(mon).sum(); allm = port.groupby(port.index.to_period("M")).sum()
    started = S.groupby(mon).last()
    L = ["ROTATE1 -- monthly rotation to recent winners (PREREGISTRATION_UNGER_BATCH section 5, sha ce14205e...)", "  " + DISC, ""]
    res = {}
    for look in (6, 3, 12):
        for which in ("top", "bottom"):
            diffs, mi = [], []; prev = set()
            for j in range(look, len(months) - 1):
                m, nxt = months[j], months[j + 1]
                if started.loc[m].sum() < len(core): continue
                tr = msum.iloc[j - look + 1:j + 1].sum()
                pick = set((tr.sort_values(ascending=(which == "bottom")).index[:4]))
                rows = X.index[mon == nxt]; r = X.loc[rows, list(pick)].mean(1).sum()
                ch = (pick - prev) | (prev - pick) if prev else pick
                d0 = X.index[mon == m][-1]
                r -= sum(0.25 * E.loc[d0, k] * 0.5 * SP.loc[d0, k] for k in ch if np.isfinite(SP.loc[d0, k]))
                prev = pick; diffs.append(r - allm.loc[nxt]); mi.append(nxt)
            dfs = np.array(diffs); yrs = np.array([p.year for p in mi])
            ers = [dfs[(yrs >= a) & (yrs <= b)].mean() for a, b in ERAS]
            res[(look, which)] = (dfs.mean(), nw_t(dfs), ers, len(dfs))
    for (look, which), (mu, t, ers, n) in res.items():
        tag = "PRIMARY" if (look, which) == (6, "top") else ("check" if which == "bottom" else "reported")
        L.append(f"  {which:6s} 4, {look:2d}-month lookback ({tag}): rotation - hold-all {mu * 100:+.3f}%/month (t {t:+.2f}, n {n});  eras "
                 + "  ".join(f"{a}-{b % 100:02d} {e * 100:+.3f}" for (a, b), e in zip(ERAS, ers)))
    mu, t, ers, _ = res[(6, "top")]; ps = mu > 0 and t >= 2.0 and all(e > 0 for e in ers)
    L += ["", f"  ROTATE1 gate (top 4, 6 months: mean > 0, t >= 2.0, every era > 0) -> {'PASS' if ps else 'FAIL'}"]
    return L


# ---------------------------------------------------------------- TURBO1
def turbo(base_net=None):
    if base_net is None:
        M = market("xauusd"); base_net = probe_lv(M, *prior_day_levels(M))["net"]
    r = base_net[np.isfinite(base_net)]; n = len(r); z = (r - r.mean()) / r.std()
    rng = np.random.default_rng(0); NP, B, D = 100_000, 20, 252
    nb = -(-D // B)

    def paths(k):
        st = rng.integers(0, n - B + 1, size=(k, nb)); idx = (st[:, :, None] + np.arange(B)).reshape(k, -1)[:, :D]; return z[idx]

    def run(Z, S, V):
        sd = V / math.sqrt(252); x = Z * sd + S * sd / math.sqrt(252)
        eq = np.cumprod(np.maximum(1 + x, 0.0), axis=1)
        ruined = eq <= 0.10; hit = ruined.any(1); fi = np.where(hit, ruined.argmax(1), D - 1)
        final = np.where(hit, eq[np.arange(len(eq)), fi], eq[:, -1])
        eqa = eq.copy()
        if hit.any():
            mask = np.arange(D)[None, :] > fi[:, None]; eqa = np.where(mask & hit[:, None], final[:, None], eq)
        peak = np.maximum.accumulate(np.c_[np.ones(len(eqa)), eqa], axis=1)[:, 1:]; mdd = (1 - eqa / peak).max(1)
        return final - 1, mdd, hit
    L = ["TURBO1 -- how a trading contest is won (PREREGISTRATION_UNGER_BATCH section 6, simulation, descriptive, no gates)", "  " + DISC, "",
         f"  input: gold probe clean-day CFD-net daily returns, {n:,} days; demeaned, re-centred; 100,000 one-year paths, 20-day blocks, seed 0", "",
         "  Sharpe  vol   median year  P(>=+100%)  P(>=+600%)  P(maxDD>=50%)  P(ruin)"]
    Z = paths(NP)
    for S in (0.0, 0.5, 1.0):
        for V in (0.10, 0.25, 0.50, 1.00, 2.00):
            ret, mdd, hit = run(Z, S, V)
            L.append(f"  {S:4.1f}  {V * 100:4.0f}%   {np.median(ret) * 100:+8.1f}%   {np.mean(ret >= 1) * 100:8.2f}%  {np.mean(ret >= 6) * 100:8.3f}%  "
                     f"{np.mean(mdd >= 0.5) * 100:10.1f}%  {np.mean(hit) * 100:7.1f}%")
    del Z
    L += ["", "  contest view: 200 entrants at 100% vol, 10,000 contests"]
    NC, E = 10_000, 200; CH = 250
    for S in (0.0, 0.5, 1.0):
        win = []
        for _ in range(NC // CH):
            ret, _, _ = run(paths(CH * E).astype(np.float32), S, 1.0); win.append(ret.reshape(CH, E).max(1))
        w = np.concatenate(win)
        L.append(f"    all Sharpe {S:.1f}: winner's year median {np.median(w) * 100:+.0f}%, 5th pct {np.percentile(w, 5) * 100:+.0f}%, "
                 f"95th pct {np.percentile(w, 95) * 100:+.0f}%;  winner >= +600% in {np.mean(w >= 6) * 100:.1f}% of contests")
    luck, wr = 0, []
    for _ in range(NC // CH):
        Z = paths(CH * E).astype(np.float32).reshape(CH, E, D)
        r0, *_ = run(Z[:, :190].reshape(-1, D), 0.0, 1.0); r1, *_ = run(Z[:, 190:].reshape(-1, D), 1.0, 1.0)
        r0 = r0.reshape(CH, 190); r1 = r1.reshape(CH, 10); luck += int((r0.max(1) > r1.max(1)).sum()); wr.append(np.maximum(r0.max(1), r1.max(1)))
    wr = np.concatenate(wr)
    L.append(f"    mix of 190 Sharpe-0 + 10 Sharpe-1.0: the winner had NO edge in {luck / NC * 100:.1f}% of contests "
             f"(chance alone if skill didn't matter: 95.0%);  winner's median year {np.median(wr) * 100:+.0f}%")
    return L


# ---------------------------------------------------------------- self-test
def self_test():
    print("unger_batch self-test")
    P.self_test()
    ok = True
    M = market("xauusd")
    sub = 400; i1 = M["last"][sub - 1] + 1
    Ms = dict(M); Ms["bar"] = {k: v[:i1] for k, v in M["bar"].items()}; Ms["day"] = M["day"][:i1]; Ms["labels"] = M["labels"][:sub]
    for k in ("O", "H", "L", "C", "S0", "S1", "first", "last", "r", "nights", "yr", "date"): Ms[k] = M[k][:sub]
    a = probe_lv(Ms, *prior_day_levels(Ms))
    g, cst, fin, close, rev = P.probe(Ms["bar"]["o"], Ms["bar"]["h"], Ms["bar"]["l"], Ms["bar"]["c"], Ms["bar"]["spr"], Ms["day"], Ms["labels"], +1, Ms["rate_of"])
    pc = np.r_[np.nan, close[:-1]]; net0 = g / pc - cst - fin
    eq = np.allclose(a["net"][1:], net0[1:], equal_nan=True, atol=1e-12); ok &= eq
    print(f"  [{'PASS' if eq else 'FAIL'}] probe_lv with prior-day levels reproduces PROBE1's probe() on 400 gold days")
    act = np.zeros(sub, bool); z = probe_lv(Ms, *prior_day_levels(Ms), active=act); e2 = np.nansum(np.abs(z["gross"])) == 0 and z["rev"].sum() == 0
    ok &= e2; print(f"  [{'PASS' if e2 else 'FAIL'}] all-OFF filter never trades")
    # synthetic daily engine checks
    T = dict(O=np.array([100, 100, 101, 102, 103.0]), C=np.array([100, 101, 102, 103, 104.0]), S0=np.full(5, 2.0), r=np.zeros(5), nights=np.ones(5))
    E = daily_engine(T, np.array([0, 1, 1, 1, 0.0])); want_g = np.array([np.nan, 1 / 100, 1 / 101, 1 / 102, 0.0])
    e3 = np.allclose(E["gross"][1:], want_g[1:]) and np.isclose(E["cost"].sum(), 2e-4) and np.isclose(E["fin"].sum(), 3 * 0.025 / 365)
    ok &= e3; print(f"  [{'PASS' if e3 else 'FAIL'}] daily engine: gross, spread (half per side) and financing on a planted path")
    T = dict(C=np.array([5, 4, 3, 2, 1, 2, 3, 4, 5, 6, 7.0]))
    mr = rule_meanrev(T); e4 = list(mr[:8]) == [0, 0, 0, 0, 0, 1, 1, 1] and mr[8] == -1
    ok &= e4; print(f"  [{'PASS' if e4 else 'FAIL'}] mean reversion: lowest-of-5 close -> long next 3 opens, then flat; highest -> short ({list(mr)})")
    T = dict(C=np.r_[np.full(20, 10.0), 11, 11, 9, 9.0])
    ch = rule_channel(T); e5 = ch[21] == 1 and ch[22] == 1 and ch[23] == -1
    ok &= e5; print(f"  [{'PASS' if e5 else 'FAIL'}] channel: breakout long next open, breakdown reverses")
    sc, w, st = voltarget(np.r_[np.full(60, 0.0), np.random.default_rng(1).normal(0, 0.01, 300)])
    e6 = w[:61].max() <= 5 and abs(np.std(sc[200:]) * math.sqrt(252) - 0.10) < 0.03 and not st[:60].any()
    ok &= e6; print(f"  [{'PASS' if e6 else 'FAIL'}] vol targeting: no position before 60 days, cap 5x, about 10% annual vol")
    HI, LO = prior_week_levels(M); wk = np.array([(x - pd.Timedelta(days=x.weekday())) for x in M["labels"]])
    j = 30; prev = wk[j] - pd.Timedelta(days=7); m = wk == prev
    e7 = np.isclose(HI[j], M["H"][m].max()) and np.isclose(LO[j], M["L"][m].min())
    ok &= e7; print(f"  [{'PASS' if e7 else 'FAIL'}] weekly levels = prior Mon-Fri week's high/low")
    # planted breakout: ATR10 = 2 from flat 2-point days; day 11 opens 100, rallies through 101, closes 103
    o_, h_, l_, c_, dy = [], [], [], [], []
    for dd_ in range(11):
        o_ += [100, 100]; h_ += [101, 101]; l_ += [99, 99]; c_ += [100, 100]; dy += [dd_, dd_]
    o_ += [100, 100.5, 102]; h_ += [100.6, 102, 103.2]; l_ += [99.8, 100.4, 101.9]; c_ += [100.5, 102, 103]; dy += [11, 11, 11]
    dy = np.array(dy); fi = np.r_[0, np.flatnonzero(np.diff(dy)) + 1]; la = np.r_[fi[1:] - 1, len(dy) - 1]
    Hh = np.array([max(h_[a:b + 1]) for a, b in zip(fi, la)]); Ll = np.array([min(l_[a:b + 1]) for a, b in zip(fi, la)])
    Mb = dict(bar=dict(o=np.array(o_, float), h=np.array(h_, float), l=np.array(l_, float), c=np.array(c_, float), spr=np.full(len(dy), 2.0)),
              first=fi, last=la, H=Hh, L=Ll, C=np.array(c_, float)[la])
    vb = vol_breakout(Mb); e8 = np.isclose(vb["gross"][11], (103 - 101) / 100) and np.isclose(vb["cost"][11], 2e-4) and vb["rev"][11] == 1
    ok &= e8; print(f"  [{'PASS' if e8 else 'FAIL'}] volatility breakout: buy stop at open + 0.5 ATR10 filled at the level, exit at the day's close")
    print("ALL PASS" if ok else "FAILURES"); return ok


def main():
    pin(); os.makedirs(OUT, exist_ok=True)
    if sys.argv[1:] == ["--self-test"]: sys.exit(0 if self_test() else 1)
    if not self_test(): sys.exit("self-test failed")
    what = sys.argv[1]
    if what == "goldtrend": L = goldtrend()
    elif what == "context": L, _ = context()
    elif what == "multi": L, *_ = multi()
    elif what == "rotate": L = rotate()
    elif what == "turbo": L = turbo()
    else: sys.exit("unknown")
    open(os.path.join(OUT, f"run_{what}.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
