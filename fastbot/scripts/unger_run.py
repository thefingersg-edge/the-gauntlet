#!/usr/bin/env python3
"""UNGER batch sections 2-6 (PREREGISTRATION_UNGER_BATCH.md, sha ce14205e...): GOLDTREND1, CONTEXT1, MULTI1, ROTATE1, TURBO1.
Section 1 (PROBE1-OIL) ran earlier via probe1_oil.py.

    python3 unger_run.py --self-test
    python3 unger_run.py goldtrend | context | multi | rotate | turbo      -> data/unger/run_<test>.log  (each runs ONCE)

Shared rules implemented exactly as the spec's "Shared rules":
  17:00 NY trading days; clean days (drop weekend labels and days with < 50% of the market's median bars per day);
  mid OHLC from 15m bars; CFD costs = the quoted spread at each position change (half out, half in) + financing at
  policy rate +/- 2.5% per 17:00 roll held (Friday = 3 nights); index spreads before 2012 = that market's 2012-14 median;
  futures route (reported) = 0.5 bp per side + financing at the policy rate only.
Disclosed extension: WTI/Brent (MULTI1's separately reported oil portfolio) also have zero spreads before 2012 in the
source, so they get the same 2012-14 median imputation.
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, hashlib, math
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, HERE)
import probe1_run as P
from struct15 import load15

BATCH = os.path.join(FB, "PREREGISTRATION_UNGER_BATCH.md")
BATCH_SHA = "ce14205ed8219efd19f5190ab53dcfdb62dbb4f8fcda5bf59a2c1eb0c91f3716"
OUT = os.path.join(FB, "data", "unger")
CORE = {"spx500usd": "USD", "nas100usd": "USD", "uk100gbp": "GBP", "xauusd": "USD"}
OIL = {"wticousd": "USD", "bcousd": "USD"}
IMPUTE = {"spx500usd", "nas100usd", "uk100gbp", "wticousd", "bcousd"}
ERAS = ((2005, 2012), (2013, 2019), (2020, 2026)); OOS = 2016
DISC = "  I am not a financial adviser. This is a measurement, not a recommendation."


# ---------------------------------------------------------------- data
def load_clean(stem, cur):
    d = load15(stem); m = d["t"] < P.END; d = {k: v[m] for k, v in d.items()}
    spr = d["spr"].astype(float).copy(); y = d["t"].astype("datetime64[Y]").astype(int) + 1970
    if stem in IMPUTE:
        spr[y < 2012] = np.median(spr[(y >= 2012) & (y <= 2014)])
    d["spr"] = spr
    ny = pd.DatetimeIndex(d["t"].astype("datetime64[ns]")).tz_localize("UTC").tz_convert("America/New_York")
    lab = (ny + pd.Timedelta(hours=7)).normalize().tz_localize(None)
    cnt = pd.Series(lab).value_counts()
    good = set(cnt[(cnt >= 0.5 * cnt.median())].index); keep = np.array([(x in good) and x.weekday() < 5 for x in lab])
    ndrop = len(cnt) - sum(1 for x in good if x.weekday() < 5)
    d = {k: v[keep] for k, v in d.items()}; lab = lab[keep]
    labels, day = np.unique(lab.to_numpy(), return_inverse=True); labels = [pd.Timestamp(x) for x in labels]
    return daily(d, day, labels, cur, stem, ndrop)


def daily(d, day, labels, cur, stem="synthetic", ndrop=0, R=None):
    first = np.r_[0, np.flatnonzero(np.diff(day)) + 1]; last = np.r_[first[1:] - 1, len(day) - 1]
    if R is None: R = P.rates(cur)
    rate = np.array([R.get(x.strftime("%Y-%m"), 0.02) for x in labels])
    M = dict(stem=stem, bars=d, day=day, labels=labels, first=first, last=last, ndrop=ndrop,
             O=d["o"][first], C=d["c"][last], H=np.maximum.reduceat(d["h"], first), L=np.minimum.reduceat(d["l"], first),
             so=d["spr"][first], rate=rate, nights=np.array([3 if x.weekday() == 4 else 1 for x in labels]),
             yr=np.array([x.year for x in labels]), date=pd.DatetimeIndex(labels))
    M["rate_of"] = lambda t, R=R: R.get(t.strftime("%Y-%m"), 0.02)
    pc = np.r_[np.nan, M["C"][:-1]]
    TR = np.maximum(M["H"], np.nan_to_num(pc, nan=-np.inf)) - np.minimum(M["L"], np.nan_to_num(pc, nan=np.inf))
    M["TR"] = TR
    return M


# ---------------------------------------------------------------- engines
def probe_gen(M, PH, PL, allow, fut=False):
    """P.probe generalised: levels PH[d]/PL[d] supplied per day (nan = no orders), allow[d] in {2 both, +1 long only,
    -1 short only, 0 flat}. An OFF day (or a position against a one-sided filter) is closed at the first bar's open, half
    spread. With PH/PL = prior-day high/low and allow = 2 it reproduces P.probe exactly (self-test)."""
    b = M["bars"]; o, h, l, c, spr = b["o"], b["h"], b["l"], b["c"], b["spr"]; day = M["day"]; labels = M["labels"]
    nd = day[-1] + 1
    gross = np.zeros(nd); cost = np.zeros(nd); fin = np.zeros(nd); close = np.full(nd, np.nan); chg = np.zeros(nd, int); eod = np.zeros(nd)
    pos = 0; cur = -1
    sc = lambda i, n: (0.5e-4 * n) if fut else spr[i] * 1e-4 * 0.5 * n
    for i in range(len(c)):
        d = day[i]
        ref = c[i - 1] if i > 0 else o[i]
        if d != cur:
            if cur >= 0 and pos != 0:
                lab = labels[cur]; nights = 3 if lab.weekday() == 4 else 1; r = M["rate_of"](lab)
                fin[cur] = nights / 365 * ((pos * r) if fut else ((r + 0.025) if pos > 0 else -(r - 0.025)))
            cur = d
            a = allow[d]
            if pos != 0 and (a == 0 or (a in (1, -1) and pos == -a)):
                gross[d] += pos * (o[i] - ref); ref = o[i]; cost[d] += sc(i, 1); chg[d] += 1; pos = 0
        a = allow[d]
        if a != 0 and np.isfinite(PH[d]):
            ev = []
            if h[i] >= PH[d]: ev.append((abs(o[i] - PH[d]), +1, (o[i] if o[i] >= PH[d] else PH[d])))
            if l[i] <= PL[d]: ev.append((abs(o[i] - PL[d]), -1, (o[i] if o[i] <= PL[d] else PL[d])))
            ev.sort(key=lambda e: e[0])
            for k, (_, side, fill) in enumerate(ev):
                if k == 1: fill = PH[d] if side > 0 else PL[d]
                tgt = side if (a == 2 or a == side) else 0
                if tgt != pos:
                    gross[d] += pos * (fill - ref); ref = fill
                    cost[d] += sc(i, abs(tgt - pos)); chg[d] += 1; pos = tgt
        gross[d] += pos * (c[i] - ref); close[d] = c[i]; eod[d] = pos
    pc = np.r_[np.nan, close[:-1]]
    g = gross / pc; g[0] = 0.0
    return dict(gross=g, cost=cost, fin=fin, net=g - cost - fin, chg=chg, eod=eod)


def run_daily(M, pos, fut=False):
    """pos[d] = position held from the open of day d to the open of d+1 (decided from data to the close of d-1)."""
    O, C = M["O"], M["C"]; pc = np.r_[np.nan, C[:-1]]; pp = np.r_[0.0, pos[:-1]]
    g = (pp * (O - pc) + pos * (C - O)) / pc; g[0] = 0.0
    dp = np.abs(pos - pp)
    cost = dp * (0.5e-4 if fut else M["so"] * 1e-4 / 2)
    r, n = M["rate"], M["nights"]
    fin = n / 365 * (pos * r if fut else np.where(pos > 0, pos * (r + 0.025), np.where(pos < 0, pos * (r - 0.025), 0.0)))
    return dict(gross=g, cost=cost, fin=fin, net=g - cost - fin, chg=(dp > 0).astype(int), pos=pos)


def pos_close_break(M):                       # GOLDTREND1-B
    C, H, L = M["C"], M["H"], M["L"]; nd = len(C); pos = np.zeros(nd); st = 0
    for d in range(2, nd):
        k = d - 1
        if C[k] > H[k - 1]: st = 1
        elif C[k] < L[k - 1]: st = -1
        pos[d] = st
    return pos


def pos_channel(M, n=20):                     # GOLDTREND1-C and MULTI1-S1
    C = M["C"]; nd = len(C); pos = np.zeros(nd); st = 0
    for d in range(1, nd):
        k = d - 1
        if k >= n:
            w = C[k - n:k]
            if C[k] > w.max(): st = 1
            elif C[k] < w.min(): st = -1
        pos[d] = st
    return pos


def pos_meanrev(M):                           # MULTI1-S2
    C = M["C"]; nd = len(C); pos = np.zeros(nd); cur = 0; ex = -1
    for d in range(nd):
        if cur != 0 and d == ex: cur = 0
        if cur == 0 and d >= 5:
            w = C[d - 5:d]                    # closes d-5 .. d-1; signal at the close of d-1
            if C[d - 1] <= w.min(): cur, ex = 1, d + 3
            elif C[d - 1] >= w.max(): cur, ex = -1, d + 3
        pos[d] = cur
    return pos


def atr(M, n): return pd.Series(M["TR"]).rolling(n).mean().to_numpy()


def sys_volbreak(M, fut=False):              # MULTI1-S3: day trade, no financing
    b = M["bars"]; o, h, l, c, spr = b["o"], b["h"], b["l"], b["c"], b["spr"]
    A = atr(M, 10); nd = len(M["C"]); g = np.zeros(nd); cost = np.zeros(nd); chg = np.zeros(nd, int)
    for d in range(1, nd):
        a = A[d - 1]
        if not np.isfinite(a): continue
        Od = M["O"][d]; up, dn = Od + 0.5 * a, Od - 0.5 * a
        for i in range(M["first"][d], M["last"][d] + 1):
            ev = []
            if h[i] >= up: ev.append((abs(o[i] - up), +1, o[i] if o[i] >= up else up))
            if l[i] <= dn: ev.append((abs(o[i] - dn), -1, o[i] if o[i] <= dn else dn))
            if ev:
                ev.sort(key=lambda e: e[0]); side, fill = ev[0][1], ev[0][2]; j = M["last"][d]
                g[d] = side * (c[j] - fill) / M["C"][d - 1]
                cost[d] = 1e-4 if fut else (spr[i] + spr[j]) / 2 * 1e-4; chg[d] = 1
                break
    return dict(gross=g, cost=cost, fin=np.zeros(nd), net=g - cost, chg=chg, pos=np.zeros(nd))


def voltarget(r):
    s = pd.Series(r).rolling(60).std(ddof=1).shift(1).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        w = np.where(s > 0, np.minimum(5.0, 0.10 / (s * math.sqrt(252))), np.where(np.isfinite(s), 0.0, np.nan))
    return w


def bh(M):
    pc = np.r_[np.nan, M["C"][:-1]]; r = M["C"] / pc - 1 - (M["rate"] + 0.025) * M["nights"] / 365; r[0] = 0.0
    return r


# ---------------------------------------------------------------- stats
def t_(x): return P.nw_t(x)
def sh(x): x = np.asarray(x, float); x = x[np.isfinite(x)]; return P.sharpe(x) if len(x) > 2 else float("nan")
def bp(x): return np.nanmean(x) * 1e4
def era_means(x, yr): return [np.nanmean(x[(yr >= a) & (yr <= b)]) if ((yr >= a) & (yr <= b)).any() else np.nan for a, b in ERAS]
def fmt_eras(e, k=1e4, f="+.2f"): return "  ".join(f"{a}-{b % 100:02d} {v * k:{f}}" for (a, b), v in zip(ERAS, e))


def once(name):
    if hashlib.sha256(open(BATCH, "rb").read()).hexdigest() != BATCH_SHA: sys.exit("batch spec changed -- refused")
    os.makedirs(OUT, exist_ok=True); f = os.path.join(OUT, f"run_{name}.log")
    if os.path.exists(f): sys.exit(f"{f} exists -- {name} has already run once; refused")
    return f


def write(f, L): open(f, "w").write("\n".join(L) + "\n"); print("\n".join(L))


# ---------------------------------------------------------------- 2. GOLDTREND1
def goldtrend():
    f = once("goldtrend"); TG = 2.13
    M = load_clean("xauusd", "USD"); yr = M["yr"]; nd = len(M["C"])
    L = ["GOLDTREND1 -- slower gold trend rules (PREREGISTRATION_UNGER_BATCH.md sec 2, sha ce14205e...)", DISC,
         f"  gold: {nd:,} clean days ({M['ndrop']} dropped), {M['date'][0].date()} -> {M['date'][-1].date()}; gates per rule: "
         f"G1 full-sample net mean > 0 with t >= {TG}; G2 every era > 0; G3 2016-26 net > 0", ""]
    # A: weekly probe
    wk = np.array([x.isocalendar()[:2] for x in M["labels"]]); keys = [tuple(k) for k in wk]
    uniq = sorted(set(keys)); idx = {k: j for j, k in enumerate(uniq)}; wi = np.array([idx[k] for k in keys])
    WH = np.full(len(uniq), -np.inf); WL = np.full(len(uniq), np.inf)
    np.maximum.at(WH, wi, M["H"]); np.minimum.at(WL, wi, M["L"])
    PH = np.where(wi >= 1, WH[np.maximum(wi - 1, 0)], np.nan); PL = np.where(wi >= 1, WL[np.maximum(wi - 1, 0)], np.nan)
    allow = np.full(nd, 2)
    res = {"A weekly probe": (probe_gen(M, PH, PL, allow), probe_gen(M, PH, PL, allow, fut=True))}
    pB = pos_close_break(M); res["B close-confirmed daily"] = (run_daily(M, pB), run_daily(M, pB, True))
    pC = pos_channel(M, 20); res["C 20-day close channel"] = (run_daily(M, pC), run_daily(M, pC, True))
    npass = 0
    for name, (R, F) in res.items():
        N = R["net"]; ok = np.ones(nd, bool); ok[0] = False
        t = t_(N[ok]); e = era_means(N[ok], yr[ok]); oo = ok & (yr >= OOS)
        g1 = np.mean(N[ok]) > 0 and t >= TG; g2 = all(x > 0 for x in e); g3 = np.mean(N[oo]) > 0; p = g1 and g2 and g3; npass += p
        G = R["gross"][ok].sum()
        L.append(f"  {name}:  net {bp(N[ok]):+.2f} bp/day (t {t:+.2f}, Sharpe {sh(N[ok]):+.2f});  eras {fmt_eras(e)};  2016-26 {bp(N[oo]):+.2f}")
        L.append(f"      G1 {'PASS' if g1 else 'FAIL'}  G2 {'PASS' if g2 else 'FAIL'}  G3 {'PASS' if g3 else 'FAIL'}  -> {'PASS' if p else 'FAIL'}")
        L.append(f"      position changes {R['chg'][ok].sum() / ok.sum() * 252:.0f}/yr;  gross {bp(R['gross'][ok]):+.2f} bp/day, of which spread "
                 f"{R['cost'][ok].sum() / G * 100 if G > 0 else float('nan'):.0f}% and financing {R['fin'][ok].sum() / G * 100 if G > 0 else float('nan'):.0f}% of gross"
                 f"{'' if G > 0 else ' (gross <= 0: shares not meaningful)'}")
        L.append(f"      futures route (reported): net {bp(F['net'][ok]):+.2f} bp/day (t {t_(F['net'][ok]):+.2f}, Sharpe {sh(F['net'][ok]):+.2f});  eras {fmt_eras(era_means(F['net'][ok], yr[ok]))}")
        L.append("      annual net %: " + " ".join(f"{y}:{N[ok & (yr == y)].sum() * 100:+.0f}" for y in range(yr[ok].min(), yr[ok].max() + 1)))
    B = bh(M)[1:]
    L += ["", f"  gold buy & hold net of CFD financing: Sharpe {sh(B):+.2f} (2016-26 {sh(bh(M)[yr >= OOS]):+.2f}), {bp(B):+.2f} bp/day",
          f"  GOLDTREND1: {npass} of 3 rules PASS"]
    write(f, L)


# ---------------------------------------------------------------- 3. CONTEXT1
def context_filters(M):
    nd = len(M["C"]); C, H, L, O = M["C"], M["H"], M["L"], M["O"]
    A = atr(M, 20); med = pd.Series(A).rolling(250).median().to_numpy()
    rng = H - L; sma = pd.Series(C).rolling(100).mean().to_numpy()
    F = {k: np.zeros(nd, int) for k in ("F1 high vol", "F2 low vol", "F3 NR4", "F4 inside day", "F5 no gap", "F6 with 100d trend")}
    for d in range(1, nd):
        k = d - 1
        if np.isfinite(med[k]): F["F1 high vol"][d] = 2 if A[k] > med[k] else 0; F["F2 low vol"][d] = 2 if A[k] < med[k] else 0
        if k >= 3: F["F3 NR4"][d] = 2 if rng[k] <= rng[k - 3:k + 1].min() else 0
        if k >= 1: F["F4 inside day"][d] = 2 if (H[k] <= H[k - 1] and L[k] >= L[k - 1]) else 0
        F["F5 no gap"][d] = 2 if L[k] <= O[d] <= H[k] else 0
        if np.isfinite(sma[k]): F["F6 with 100d trend"][d] = 1 if C[k] > sma[k] else (-1 if C[k] < sma[k] else 0)
    return F


def gold_base(M):
    nd = len(M["C"]); PH = np.r_[np.nan, M["H"][:-1]]; PL = np.r_[np.nan, M["L"][:-1]]
    return PH, PL, probe_gen(M, PH, PL, np.full(nd, 2))


def context():
    f = once("context"); TG = 2.39
    M = load_clean("xauusd", "USD"); yr = M["yr"]; nd = len(M["C"]); ok = np.ones(nd, bool); ok[0] = False
    PH, PL, base = gold_base(M); B = base["net"]; oo = ok & (yr >= OOS); ins = ok & (yr <= 2015)
    L = ["CONTEXT1 -- 'simple idea + context' filters on the gold daily probe (PREREGISTRATION_UNGER_BATCH.md sec 3, sha ce14205e...)", DISC,
         f"  gold: {nd:,} clean days; gates per filter: G1 2016-26 net mean > 0 with t >= {TG}; G2 beats the unfiltered probe in 2006-15 AND 2016-26",
         "  mechanical reading (logged): a filter that cannot yet be computed (start of history) is OFF (flat); F6 closes a position that is against the trend at the first bar",
         f"  base (unfiltered probe, clean days): net {bp(B[ok]):+.2f} bp/day (t {t_(B[ok]):+.2f});  2006-15 {bp(B[ins]):+.2f};  2016-26 {bp(B[oo]):+.2f} (t {t_(B[oo]):+.2f});  "
         f"changes {base['chg'][ok].sum() / ok.sum() * 252:.0f}/yr", ""]
    npass = 0
    for name, allow in context_filters(M).items():
        R = probe_gen(M, PH, PL, allow); N = R["net"]
        t = t_(N[oo]); g1 = np.mean(N[oo]) > 0 and t >= TG; g2 = np.mean(N[ins]) > np.mean(B[ins]) and np.mean(N[oo]) > np.mean(B[oo])
        p = g1 and g2; npass += p
        lift = era_means(N[ok] - B[ok], yr[ok])
        L.append(f"  {name}:  2016-26 net {bp(N[oo]):+.2f} bp/day (t {t:+.2f});  2006-15 {bp(N[ins]):+.2f};  full {bp(N[ok]):+.2f} (Sharpe {sh(N[ok]):+.2f})")
        L.append(f"      G1 {'PASS' if g1 else 'FAIL'}  G2 {'PASS' if g2 else 'FAIL'}  -> {'PASS' if p else 'FAIL'};  active {np.mean(allow[ok] != 0) * 100:.0f}% of days, "
                 f"changes {R['chg'][ok].sum() / ok.sum() * 252:.0f}/yr;  lift vs base by era {fmt_eras(lift)} bp/day")
    L += ["", f"  CONTEXT1: {npass} of 6 filters PASS"]
    write(f, L)


# ---------------------------------------------------------------- 4. MULTI1
def systems(markets):
    S = {}
    for stem, cur in markets.items():
        M = load_clean(stem, cur)
        for nm, fn in (("S1 trend", lambda M, fu: run_daily(M, pos_channel(M, 20), fu)),
                       ("S2 meanrev", lambda M, fu: run_daily(M, pos_meanrev(M), fu)),
                       ("S3 volbreak", lambda M, fu: sys_volbreak(M, fu))):
            R, F = fn(M, False), fn(M, True)
            S[f"{stem} {nm}"] = dict(M=M, R=R, F=F, w=voltarget(R["net"]), wf=voltarget(F["net"]))
        S[f"{stem} BH"] = dict(M=M, R=dict(net=bh(M), pos=np.ones(len(M["C"]))), w=voltarget(bh(M)))
    return S


def frame(S, keys, col="R", wcol="w"):
    cols = {}
    for k in keys:
        s = S[k]; r = s[col]["net"] * s[wcol]
        cols[k] = pd.Series(r, index=s["M"]["date"])
    return pd.DataFrame(cols).sort_index()


def portfolio(df):
    started = df.notna().cummax(); n = started.sum(axis=1)
    p = df.fillna(0).where(started, 0).sum(axis=1) / n.replace(0, np.nan)
    return p.dropna()


def multi_report(S, mk, L, label, gate=True):
    sysk = [k for k in S if k.split()[0] in mk and not k.endswith("BH")]; bhk = [f"{m} BH" for m in mk]
    D = frame(S, sysk); Pf = portfolio(D); Pf = Pf[Pf.index.year >= 2006]
    DF = frame(S, sysk, "F", "wf"); PF = portfolio(DF); PF = PF[PF.index.year >= 2006]
    BH = portfolio(frame(S, bhk)); BH = BH[BH.index.year >= 2006]
    x = Pf.to_numpy(); yr = Pf.index.year.to_numpy(); t = t_(x); e = era_means(x, yr)
    so = sh(x[yr >= OOS]); sb = sh(BH[BH.index.year >= OOS].to_numpy())
    g1 = sh(x) > 0 and t >= 2.0; g2 = all(v > 0 for v in e); g3 = so > sb
    L.append(f"  {label}: {len(sysk)} systems; portfolio 2006-26 net Sharpe {sh(x):+.2f} (t {t:+.2f}), {np.mean(x) * 252 * 100:+.1f}%/yr;  eras {fmt_eras(e, 252 * 100, '+.1f')} %/yr")
    L.append(f"      2016-26 Sharpe {so:+.2f} vs equal-weight buy & hold (vol-targeted, net of financing) {sb:+.2f}")
    if gate: L.append(f"      G1 {'PASS' if g1 else 'FAIL'}  G2 {'PASS' if g2 else 'FAIL'}  G3 {'PASS' if g3 else 'FAIL'}  -> {'PASS' if (g1 and g2 and g3) else 'FAIL'}")
    L.append(f"      futures route (reported): portfolio Sharpe {sh(PF.to_numpy()):+.2f} (t {t_(PF.to_numpy()):+.2f})")
    Dc = D[D.index.year >= 2006]; C = Dc.corr().to_numpy(); iu = np.triu_indices(len(sysk), 1)
    vols = Dc.std(); L.append(f"      average pairwise correlation {np.nanmean(C[iu]):+.2f};  diversification ratio (portfolio vol / avg component vol) {Pf.std() / vols.mean():.2f}")
    L.append("      components (net Sharpe 2006-26, CFD | futures route):")
    for k in sysk:
        a = D[k][D.index.year >= 2006].dropna().to_numpy(); b = DF[k][DF.index.year >= 2006].dropna().to_numpy()
        L.append(f"        {k:<26} {sh(a):+.2f} | {sh(b):+.2f}   eras {fmt_eras(era_means(a, D[k][D.index.year >= 2006].dropna().index.year.to_numpy()), 252 * 100, '+.1f')} %/yr")
    return g1 and g2 and g3


def multi():
    f = once("multi")
    L = ["MULTI1 -- three simple systems per market, vol-targeted and combined (PREREGISTRATION_UNGER_BATCH.md sec 4, sha ce14205e...)", DISC,
         "  each system scaled to 10% vol on its own trailing 60-day net returns (lagged a day, cap 5x); portfolio = equal weight of started systems;",
         "  gates: G1 Sharpe > 0 with NW t >= 2.0 (2006-26); G2 every era > 0; G3 2016-26 Sharpe > equal-weight buy & hold. Rebalancing costs of the",
         "  vol-target weights are not charged (the spec charges the spread on position changes only).", ""]
    S = systems({**CORE, **OIL})
    p = multi_report(S, list(CORE), L, "CORE (SPX, NAS, UK100, gold)")
    L.append("")
    multi_report(S, list(CORE) + list(OIL), L, "WITH OIL (reported, not gated: + WTI, Brent)", gate=False)
    L += ["", f"  MULTI1: {'PASS' if p else 'FAIL'}"]
    keep = {}
    for k, s in S.items():
        if k.split()[0] in CORE and not k.endswith("BH"):
            keep[k] = dict(date=s["M"]["date"].values, net=s["R"]["net"], w=s["w"], pos=s["R"]["pos"], so=s["M"]["so"])
    np.save(os.path.join(OUT, "multi_core_systems.npy"), keep, allow_pickle=True)
    write(f, L)


# ---------------------------------------------------------------- 5. ROTATE1
def rotate_sim(sysd, lb, pick="top"):
    keys = sorted(sysd)
    D = pd.DataFrame({k: pd.Series(sysd[k]["net"] * sysd[k]["w"], index=pd.DatetimeIndex(sysd[k]["date"])) for k in keys}).sort_index()
    start = {k: D[k].first_valid_index() for k in keys}
    idx = D.index; ym = idx.year * 12 + idx.month; me = [idx[ym == v][-1] for v in np.unique(ym)]
    Z = D.fillna(0)
    def open_info(k, day):
        s = sysd[k]; dd = pd.DatetimeIndex(s["date"]); j = dd.searchsorted(day)
        if j >= len(dd): return 0.0
        w = s["w"][j]; return (0.0 if not np.isfinite(w) else w) * abs(s["pos"][j]) * s["so"][j] * 1e-4 / 2
    rows = []; prev = set()
    for m in range(lb, len(me) - 1):
        if not all(start[k] is not None and start[k] <= me[m - lb] for k in keys): continue
        tr = Z[(idx > me[m - lb]) & (idx <= me[m])].sum()
        order = tr.sort_values(ascending=(pick == "bottom")).index.tolist(); sel = set(order[:4])
        days = (idx > me[m]) & (idx <= me[m + 1]); seg = Z[days]
        rot = seg[list(sel)].mean(axis=1).to_numpy().copy(); allr = seg.mean(axis=1).to_numpy()
        if len(rot):
            d0 = idx[days][0]; rot[0] -= sum(open_info(k, d0) for k in (sel ^ prev)) / 4
        prev = sel
        rows.append((me[m + 1], rot.sum(), allr.sum()))
    R = pd.DataFrame(rows, columns=["month", "rot", "all"]).set_index("month"); R["diff"] = R["rot"] - R["all"]
    return R


def rotate():
    f = once("rotate")
    sysd = np.load(os.path.join(OUT, "multi_core_systems.npy"), allow_pickle=True).item()
    L = ["ROTATE1 -- monthly rotation to the 4 recent winners of MULTI1's 12 core systems (PREREGISTRATION_UNGER_BATCH.md sec 5, sha ce14205e...)", DISC,
         "  gate (6-month lookback, top 4): paired monthly (rotation - hold all 12) mean > 0 with NW t >= 2.0 AND positive in every era", ""]
    verdict = None
    for lb, pick in ((6, "top"), (3, "top"), (12, "top"), (6, "bottom")):
        R = rotate_sim(sysd, lb, pick); x = R["diff"].to_numpy(); yr = R.index.year.to_numpy(); t = t_(x); e = era_means(x, yr)
        tag = f"{'top' if pick == 'top' else 'BOTTOM'} 4, {lb:>2}-month lookback"
        L.append(f"  {tag}: {len(R)} months from {R.index[0].date()};  rotation {R['rot'].mean() * 1200:+.1f}%/yr (Sharpe {sh(R['rot']) / math.sqrt(252 / 12):+.2f})  "
                 f"vs hold all 12 {R['all'].mean() * 1200:+.1f}%/yr (Sharpe {sh(R['all']) / math.sqrt(252 / 12):+.2f})")
        L.append(f"      difference {x.mean() * 1e4:+.1f} bp/month (t {t:+.2f});  eras {fmt_eras(e, 1e4, '+.1f')} bp/month")
        if lb == 6 and pick == "top":
            verdict = x.mean() > 0 and t >= 2.0 and all(v > 0 for v in e)
            L.append(f"      GATE -> {'PASS' if verdict else 'FAIL'}")
    L += ["", f"  ROTATE1: {'PASS' if verdict else 'FAIL'}  (Sharpe figures are monthly, annualised)"]
    write(f, L)


# ---------------------------------------------------------------- 6. TURBO1
def gold_probe_net():
    M = load_clean("xauusd", "USD"); _, _, base = gold_base(M); yr = M["yr"]
    x = base["net"][1:]; return x[yr[1:] >= 2006]


def paths(z, n, rng, T=252, blk=20):
    nb = -(-T // blk); st = rng.integers(0, len(z) - blk + 1, size=(n, nb))
    ix = (st[:, :, None] + np.arange(blk)[None, None, :]).reshape(n, nb * blk)[:, :T]
    return z[ix]


def equity(Z, SR, V):
    mu = np.asarray(SR, float); mu = mu[:, None] if mu.ndim else mu
    r = mu * V / 252 + Z.astype(np.float64) * V / math.sqrt(252)
    n, T = r.shape; eq = np.ones(n); peak = np.ones(n); mdd = np.zeros(n); dead = np.zeros(n, bool)
    for t in range(T):
        e = np.where(dead, eq, np.maximum(eq * (1 + r[:, t]), 0.0))
        dead |= e <= 0.10; eq = e; peak = np.maximum(peak, eq); mdd = np.maximum(mdd, 1 - eq / peak)
    return eq, mdd, dead


def turbo(z=None, N=100_000, NC=10_000, log=True):
    f = once("turbo") if log else None
    if z is None:
        x = gold_probe_net(); z = (x - x.mean()) / x.std()
    rng = np.random.default_rng(0)
    L = ["TURBO1 -- how a trading contest is won (simulation, descriptive, no gates; PREREGISTRATION_UNGER_BATCH.md sec 6, sha ce14205e...)", DISC,
         f"  input: gold probe clean-day CFD-net daily returns 2006-26 ({len(z):,} days), demeaned and standardised, re-centred to true Sharpe 0 / 0.5 / 1.0",
         f"  {N:,} one-year paths per setting (20-day block bootstrap, seed 0, same paths for every setting); ruin = equity <= 10% of start", "",
         f"  {'Sharpe':>6} {'vol':>5} | {'median year':>11} {'P(>=+100%)':>10} {'P(>=+600%)':>10} {'P(DD>=50%)':>10} {'P(ruin)':>8}"]
    Zs = [paths(z, 10_000, rng).astype(np.float32) for _ in range(N // 10_000)]
    for SR in (0.0, 0.5, 1.0):
        for V in (0.10, 0.25, 0.50, 1.00, 2.00):
            out = [equity(Zc, SR, V) for Zc in Zs]
            eq = np.concatenate([o[0] for o in out]); mdd = np.concatenate([o[1] for o in out]); dead = np.concatenate([o[2] for o in out]); y = eq - 1
            L.append(f"  {SR:>6.1f} {V * 100:>4.0f}% | {np.median(y) * 100:>+10.1f}% {np.mean(y >= 1) * 100:>9.2f}% {np.mean(y >= 6) * 100:>9.3f}% "
                     f"{np.mean(mdd >= 0.5) * 100:>9.1f}% {np.mean(dead) * 100:>7.1f}%")
    del Zs
    L += ["", f"  CONTEST: 200 entrants at 100% vol, {NC:,} contests each"]
    CH = 100
    for SR in (0.0, 0.5, 1.0):
        W = []
        for c0 in range(0, NC, CH):
            eq, _, _ = equity(paths(z, CH * 200, rng), SR, 1.0); W.append(eq.reshape(CH, 200).max(axis=1) - 1)
        W = np.concatenate(W)
        L.append(f"    all Sharpe {SR:.1f}: winner's year median {np.median(W) * 100:+.0f}%, 5th pct {np.percentile(W, 5) * 100:+.0f}%, 95th pct {np.percentile(W, 95) * 100:+.0f}%")
    lucky = []; srs = np.tile(np.r_[np.zeros(190), np.ones(10)], CH)
    for c0 in range(0, NC, CH):
        eq, _, _ = equity(paths(z, CH * 200, rng), srs, 1.0); lucky.append(eq.reshape(CH, 200).argmax(axis=1) < 190)
    lucky = np.concatenate(lucky)
    L.append(f"    mixed field (190 at Sharpe 0 + 10 at Sharpe 1.0, all 100% vol): the winner was a Sharpe-0 trader in {lucky.mean() * 100:.0f}% of contests "
             f"(their share of the field is 95%)")
    if log: write(f, L)
    return L


# ---------------------------------------------------------------- self-test
def synth(seed=1, nd=60, bars=8, drift=0.0):
    rng = np.random.default_rng(seed); o, h, l, c, day = [], [], [], [], []; px = 100.0
    for d in range(nd):
        for b in range(bars):
            op = px; px = px * (1 + drift + rng.normal(0, 0.003)); hi = max(op, px) * (1 + abs(rng.normal(0, 0.001))); lo = min(op, px) * (1 - abs(rng.normal(0, 0.001)))
            o.append(op); h.append(hi); l.append(lo); c.append(px); day.append(d)
    d = dict(o=np.array(o), h=np.array(h), l=np.array(l), c=np.array(c), spr=np.full(len(c), 2.0))
    labels = list(pd.bdate_range("2010-01-04", periods=nd))
    R = {x.strftime("%Y-%m"): 0.01 for x in labels}
    return daily(d, np.array(day), labels, "USD", R=R)


def self_test():
    ok = True
    def chk(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print("unger_run.py self-test")
    M = synth(); nd = len(M["C"]); b = M["bars"]
    g, cst, fin, close, rev = P.probe(b["o"], b["h"], b["l"], b["c"], b["spr"], M["day"], M["labels"], +1, M["rate_of"])
    pc = np.r_[np.nan, close[:-1]]; ref = g / pc; ref[0] = 0
    G = probe_gen(M, np.r_[np.nan, M["H"][:-1]], np.r_[np.nan, M["L"][:-1]], np.full(nd, 2))
    chk("probe_gen with prior-day levels and no filter == frozen P.probe (gross, spread, financing, changes)",
        np.allclose(G["gross"], ref) and np.allclose(G["cost"], cst) and np.allclose(G["fin"], fin) and (G["chg"] == rev).all())
    Goff = probe_gen(M, np.r_[np.nan, M["H"][:-1]], np.r_[np.nan, M["L"][:-1]], np.zeros(nd, int))
    chk("filter always OFF -> no trades, zero P&L", Goff["chg"].sum() == 0 and abs(Goff["net"]).sum() == 0)
    Glong = probe_gen(M, np.r_[np.nan, M["H"][:-1]], np.r_[np.nan, M["L"][:-1]], np.full(nd, 1))
    chk("long-only filter never holds a short, and does trade", (Glong["eod"] >= 0).all() and Glong["chg"].sum() > 0)
    half = np.where(np.arange(nd) % 2 == 0, 2, 0); Gh = probe_gen(M, np.r_[np.nan, M["H"][:-1]], np.r_[np.nan, M["L"][:-1]], half)
    chk("OFF days end flat", (Gh["eod"][half == 0] == 0).all())
    # run_daily arithmetic
    T = dict(O=np.array([100, 100.5, 101.5]), C=np.array([100, 101, 102.0]), so=np.array([2.0, 2.0, 2.0]), rate=np.zeros(3), nights=np.ones(3, int))
    R = run_daily(T, np.array([0, 1.0, 1.0]))
    chk("run_daily: gross day1 = (101-100.5)/100, day2 = (102-101)/101, entry costs half spread",
        abs(R["gross"][1] - 0.005) < 1e-12 and abs(R["gross"][2] - 1 / 101) < 1e-12 and abs(R["cost"][1] - 1e-4) < 1e-12 and R["cost"][2] == 0)
    R = run_daily(T, np.array([0, 1.0, -1.0])); chk("run_daily: a reversal costs the full spread", abs(R["cost"][2] - 2e-4) < 1e-12)
    T["rate"] = np.full(3, 0.05); R = run_daily(T, np.array([0, -1.0, -1.0])); chk("short financing = -(r - 2.5%)", abs(R["fin"][1] - (-(0.05 - 0.025) / 365)) < 1e-15)
    # mean reversion timing
    MM = dict(C=np.array([10, 9, 8, 7, 6, 5, 6, 7, 8, 9, 10, 11.0]))
    p = pos_meanrev(MM); chk("S2: close of day 4 is the 5-day low -> long days 5,6,7, flat or new signal at 8", list(p[5:8]) == [1, 1, 1] and p[4] == 0)
    # channel: rising closes -> long from day 21 on
    MC = dict(C=np.arange(1, 41, dtype=float)); pc_ = pos_channel(MC, 20); chk("S1/C: rising closes -> long from day 21", pc_[21] == 1 and pc_[20] == 0)
    # vol target
    r = np.random.default_rng(3).normal(0, 0.01, 5000); w = voltarget(r); s = r * np.nan_to_num(w)
    chk("vol target: scaled vol ~ 10%/yr", abs(np.std(s[100:]) * math.sqrt(252) - 0.10) < 0.01 and np.isnan(w[:60]).all() and np.isfinite(w[60]))
    # volbreak on a synthetic rising path
    MV = synth(seed=2, nd=80, drift=0.002); V = sys_volbreak(MV); chk("S3 on a steadily rising path makes money gross", V["gross"].sum() > 0)
    # turbo calibration
    z = np.random.default_rng(5).normal(size=4000); z = (z - z.mean()) / z.std(); rng = np.random.default_rng(9); Z = paths(z, 4000, rng)
    rr = 1.0 * 0.10 / 252 + Z * 0.10 / math.sqrt(252); est = rr.mean() / rr.std() * math.sqrt(252)
    chk(f"turbo: re-centred Sharpe 1.0 paths measure ~1.0 ({est:.2f})", abs(est - 1.0) < 0.1)
    eq, mdd, dead = equity(Z[:500], 0.0, 3.0); chk("turbo: ruined paths stay at or below 10%", (eq[dead] <= 0.10 + 1e-12).all())
    print("ALL PASS" if ok else "FAILURES ABOVE"); return ok


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--self-test"]: sys.exit(0 if self_test() else 1)
    if len(a) == 1 and a[0] in ("goldtrend", "context", "multi", "rotate", "turbo"):
        P.pin()
        if not self_test(): sys.exit("self-test failed -- refused")
        globals()[a[0]]()
    else:
        sys.exit(__doc__)
