#!/usr/bin/env python3
"""PROBE1 (PREREGISTRATION_PROBE1.md): Unger's daily prior-high/low stop-and-reverse probe on SPX500, NAS100, UK100, XAUUSD.
python3 probe1_run.py            -> data/probe1/run_probe1.log, data/probe1/<stem>_daily.csv
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, hashlib, math
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, HERE)
from struct15 import load15
PIN = {os.path.join(FB, "PREREGISTRATION_PROBE1.md"): "1320a760421c6029101d44fc85dd3cc5683e3aeb6366f87125aeea282c106eb6"}
OUT = os.path.join(FB, "data", "probe1"); END = np.datetime64("2026-09-26T00:00")
STEMS = {"spx500usd": "USD", "nas100usd": "USD", "uk100gbp": "GBP", "xauusd": "USD"}
ERAS = ((2005, 2012), (2013, 2019), (2020, 2026)); TQ2 = 2.50


def pin():
    for f, h in PIN.items():
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} changed -- refused")


def rates(cur):
    r = {}
    for row in csv.DictReader(open(os.path.join(FB, "data", "policy_rates.csv"))):
        if row["currency"] == cur: r[row["month"]] = float(row["rate_pct"]) / 100
    return r


def probe(o, h, l, c, spr_bp, day, labels, sign, rate_of=None):
    """Stop-and-reverse on prior-day high/low. day: int day index per bar (sorted). labels: list of day labels (Timestamp).
    Returns per-day arrays: gross_px (price-unit P&L), cost_frac (spread costs as fraction), fin_frac, close, reversals."""
    nd = day[-1] + 1
    D_hi = np.full(nd, -np.inf); D_lo = np.full(nd, np.inf)
    np.maximum.at(D_hi, day, h); np.minimum.at(D_lo, day, l)
    gross = np.zeros(nd); cost = np.zeros(nd); fin = np.zeros(nd); close = np.full(nd, np.nan); rev = np.zeros(nd, int)
    pos = 0; cur = -1; prev_close = np.nan
    for i in range(len(c)):
        d = day[i]
        if d != cur:
            if cur >= 0 and pos != 0 and rate_of is not None:            # held over the 17:00 roll that ended day `cur`
                lab = labels[cur]; nights = 3 if lab.weekday() == 4 else 1
                r = rate_of(lab); fin[cur] = nights / 365 * ((r + 0.025) if pos > 0 else -(r - 0.025))
            cur = d
        ref = c[i - 1] if i > 0 else o[i]
        if d >= 1 and np.isfinite(D_hi[d - 1]):
            PH, PL = D_hi[d - 1], D_lo[d - 1]
            ev = []
            if h[i] >= PH: ev.append((abs(o[i] - PH), +1, (o[i] if o[i] >= PH else PH)))
            if l[i] <= PL: ev.append((abs(o[i] - PL), -1, (o[i] if o[i] <= PL else PL)))
            ev.sort(key=lambda e: e[0])
            for k, (_, side, fill) in enumerate(ev):
                if k == 1: fill = PH if side > 0 else PL
                tgt = sign * side
                if tgt != pos:
                    gross[d] += pos * (fill - ref); ref = fill
                    cost[d] += spr_bp[i] * 1e-4 * (1.0 if pos != 0 else 0.5); rev[d] += 1; pos = tgt
        gross[d] += pos * (c[i] - ref); close[d] = c[i]
    return gross, cost, fin, close, rev


def self_test():
    def mk(path_days):   # each day: list of (o,h,l,c)
        o, h, l, c, day = [], [], [], [], []
        for di, bars in enumerate(path_days):
            for b in bars: o.append(b[0]); h.append(b[1]); l.append(b[2]); c.append(b[3]); day.append(di)
        return [np.array(x, float) for x in (o, h, l, c)] + [np.array(day)]
    up = [[(100 + 2 * d, 101 + 2 * d, 99.5 + 2 * d, 100.8 + 2 * d), (100.8 + 2 * d, 102.2 + 2 * d, 100.5 + 2 * d, 102 + 2 * d)] for d in range(30)]
    zz = [[(100, 103, 99.8, 102.8), (102.8, 102.9, 97, 97.5)] if d % 2 == 0 else [(97.5, 103.5, 97.2, 103.2), (103.2, 103.3, 96.5, 97)] for d in range(30)]
    lab = [pd.Timestamp("2010-01-04") + pd.Timedelta(days=i) for i in range(30)]
    o, h, l, c, dd = mk(up); g1 = probe(o, h, l, c, np.zeros(len(c)), dd, lab, +1)[0].sum(); g1r = probe(o, h, l, c, np.zeros(len(c)), dd, lab, -1)[0].sum()
    o, h, l, c, dd = mk(zz); g2 = probe(o, h, l, c, np.zeros(len(c)), dd, lab, +1)[0].sum()
    ok = g1 > 0 and g2 < 0 and abs(g1 + g1r) < 1e-9
    print(f"  self-test: trend path gross {g1:+.2f} (>0), zig-zag gross {g2:+.2f} (<0), probe+reverse {g1 + g1r:+.1e} (=0) -> {'OK' if ok else 'BROKEN'}")
    if not ok: sys.exit("self-test broken")


def nw_t(x, lags=5):
    x = np.asarray(x, float); x = x[np.isfinite(x)]; n = len(x)
    if n < 30: return float("nan")
    m = x.mean(); u = x - m; v = (u @ u) / n
    for k in range(1, lags + 1): v += 2 * (1 - k / (lags + 1)) * (u[k:] @ u[:-k]) / n
    return m / math.sqrt(v / n)


def sharpe(x): x = np.asarray(x, float); return x.mean() / x.std() * math.sqrt(252) if x.std() > 0 else float("nan")


def main():
    pin(); self_test(); os.makedirs(OUT, exist_ok=True)
    L = ["PROBE1 -- Unger's prior-day high/low stop-and-reverse probe (PREREGISTRATION_PROBE1.md sha 1320a760…)",
         "  I am not a financial adviser. This is a measurement, not a recommendation.", ""]
    q1pass = q2pass = 0
    for stem, cur in STEMS.items():
        d = load15(stem); m = d["t"] < END; d = {k: v[m] for k, v in d.items()}
        ny = pd.DatetimeIndex(d["t"].astype("datetime64[ns]")).tz_localize("UTC").tz_convert("America/New_York")
        lab_all = (ny + pd.Timedelta(hours=7)).normalize().tz_localize(None)
        labels, day = np.unique(lab_all.to_numpy(), return_inverse=True); labels = [pd.Timestamp(x) for x in labels]
        R = rates(cur); rate_of = lambda t: R.get(t.strftime("%Y-%m"), 0.02)
        res = {}
        for sg in (+1, -1):
            g, cst, fin, close, rev = probe(d["o"], d["h"], d["l"], d["c"], d["spr"], day, labels, sg, rate_of)
            pc = np.r_[np.nan, close[:-1]]
            res[sg] = dict(gross=g / pc, cost=cst, fin=fin, net=g / pc - cst - fin, rev=rev)
        close = probe(d["o"], d["h"], d["l"], d["c"], d["spr"], day, labels, +1)[3]; pc = np.r_[np.nan, close[:-1]]
        bh = close / pc - 1 - np.array([((rate_of(x) + 0.025) * (3 if x.weekday() == 4 else 1) / 365) for x in labels])
        yr = np.array([x.year for x in labels]); ok = np.isfinite(res[1]["gross"])
        G = res[1]["gross"]
        # Q1
        t_all = nw_t(G[ok]); ers = [np.nanmean(G[ok & (yr >= a) & (yr <= b)]) for a, b in ERAS]
        sgn = np.sign(np.nanmean(G[ok])); stable = abs(t_all) >= 2 and all(np.sign(e) == sgn for e in ers)
        q1pass += stable
        char = ("TREND" if sgn > 0 else "MEAN-REVERTING") if stable else "UNSTABLE"
        L.append(f"  {stem}: {ok.sum():,} days, {res[1]['rev'].sum():,} reversals ({res[1]['rev'].sum() / ok.sum() * 252:.0f}/yr)")
        L.append(f"    Q1 gross probe: mean {np.nanmean(G[ok]) * 1e4:+.2f} bp/day (t {t_all:+.2f}, Sharpe {sharpe(G[ok]):+.2f});  eras "
                 + "  ".join(f"{a}-{b % 100:02d} {e * 1e4:+.2f}" for (a, b), e in zip(ERAS, ers)) + f"  -> character {char}")
        # Q2
        ins = ok & (yr <= 2015); oos = ok & (yr >= 2016)
        pick = +1 if np.nanmean(G[ins]) > 0 else -1; N = res[pick]["net"][oos]
        tn = nw_t(N); passed = np.mean(N) > 0 and tn >= TQ2; q2pass += passed
        gross_o = res[pick]["gross"][oos]; spread_o = res[pick]["cost"][oos]; fin_o = res[pick]["fin"][oos]
        L.append(f"    Q2 chosen on 2005-15: {'TREND (probe)' if pick > 0 else 'FADE (reverse)'};  2016-26 gross {gross_o.mean() * 1e4:+.2f} bp/day, "
                 f"spread {-spread_o.mean() * 1e4:.2f}, financing {-fin_o.mean() * 1e4:+.2f} -> net {N.mean() * 1e4:+.2f} bp/day (t {tn:+.2f}, Sharpe {sharpe(N):+.2f})"
                 f"  -> {'PASS' if passed else 'FAIL'}")
        L.append(f"       buy & hold 2016-26 net of financing: {np.nanmean(bh[oos]) * 1e4:+.2f} bp/day (Sharpe {sharpe(bh[oos][np.isfinite(bh[oos])]):+.2f})")
        L.append("       annual gross / net (probe direction): " + " ".join(f"{y}:{np.nansum(G[ok & (yr == y)]) * 100:+.0f}/{np.nansum(res[1]['net'][ok & (yr == y)]) * 100:+.0f}" for y in range(yr[ok].min(), yr[ok].max() + 1)) + "  (%)\n")
        with open(os.path.join(OUT, f"{stem}_daily.csv"), "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["day", "gross_probe", "net_probe", "net_reverse", "buyhold_net"])
            for i in np.flatnonzero(ok): w.writerow([labels[i].date(), f"{G[i]:.6f}", f"{res[1]['net'][i]:.6f}", f"{res[-1]['net'][i]:.6f}", f"{bh[i]:.6f}"])
    L.append(f"  Q1 stable character: {q1pass} of 4 markets;   Q2 out-of-sample net PASS: {q2pass} of 4 (t >= {TQ2})")
    open(os.path.join(OUT, "run_probe1.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
