#!/usr/bin/env python3
"""
macdff.py -- FLOWS-16: MACD "fake filter" exhaustion crosses on NQ futures.
Implements flows/PREREGISTRATION_MACDFF.md; refuses to run if it has changed.

    python3 macdff.py --self-test     synthetic checks only
    python3 macdff.py --run           the registered test, once

Bars: the FLOWS-15 5-minute RTH session cache (vehicle.prep, built from Databento 1m),
grouped 3:1 into 15-minute bars labelled by start (09:30 .. 15:45); roll sessions dropped
(vehicle.drop_rolls). The indicator runs on the RTH bars joined session to session.
Pine conventions: ta.ema / ta.rma seeded with an SMA; ta.atr = rma(true range);
ta.crossover(x, y) = x > y and x[1] <= y[1].
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, io, json, math, os, sys
import numpy as np
import common as C

NAME = "MACDFF"
DOC = os.path.join(C.HERE, "PREREGISTRATION_MACDFF.md")
PIN = "53b51890bb7774426e5a216618fea538f8be803223448696c8641caabaeeaa8f"
TICK, MULT, COMM = 0.25, 20.0, 2.50
FAST, SLOW, SIGL, ATRL, NW, MINW, THR = 12, 26, 9, 100, 50, 10, 1.0
T0, T1 = dt.date(2013, 1, 2), dt.date(2026, 8, 31)
ERAS = ((2013, 2017), (2018, 2021), (2022, 2026))
NPART, SEED, WIN = 20, 20261019, 250
LOG = os.path.join(C.FDATA, "macdff_run.log")
RES = os.path.join(C.FDATA, "macdff_result.json")
TRD = os.path.join(C.FDATA, "macdff_trades.csv")


def check_pin():
    got = hashlib.sha256(open(DOC, "rb").read()).hexdigest()
    if got != PIN:
        sys.exit(f"REFUSING: PREREGISTRATION_MACDFF.md changed ({got[:16]} != {PIN[:16]})")


# ------------------------------------------------------------------ bars
def sessions(root: str, minutes: int):
    """[(date, [labels], o, h, l, c arrays)] of RTH bars, roll sessions dropped."""
    import vehicle as V
    days, iid = V.prep(root)
    days, _ = V.drop_rolls(days, iid)
    out = []
    for d in sorted(days):
        b = days[d]
        g = {}
        for k in sorted(b):
            t = (int(k[:2]) * 60 + int(k[3:]) - 570) // minutes * minutes + 570
            g.setdefault(t, []).append(k)
        labels, o, h, l, c = [], [], [], [], []
        for t in sorted(g):
            x = g[t]
            labels.append(f"{t // 60:02d}:{t % 60:02d}")
            o.append(b[x[0]][0]); c.append(b[x[-1]][3])
            h.append(max(b[k][1] for k in x)); l.append(min(b[k][2] for k in x))
        minbars = 20 if minutes == 15 else 60
        if len(labels) >= minbars:
            out.append((d, labels, np.array(o), np.array(h), np.array(l), np.array(c)))
    return out


# ------------------------------------------------------------------ indicator (Pine conventions)
def _seeded(x, n, a):
    out = np.full(len(x), np.nan); s = None; buf = []
    for i, v in enumerate(x):
        if np.isnan(v):
            continue
        if s is None:
            buf.append(v)
            if len(buf) == n:
                s = sum(buf) / n; out[i] = s
            continue
        s = a * v + (1 - a) * s; out[i] = s
    return out


def ema(x, n):
    return _seeded(x, n, 2.0 / (n + 1))


def rma(x, n):
    return _seeded(x, n, 1.0 / n)


def indicator(h, l, c):
    pc = np.r_[np.nan, c[:-1]]
    tr = np.where(np.isnan(pc), h - l, np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc))))
    atr = rma(tr, ATRL)
    macd = (ema(c, FAST) - ema(c, SLOW)) / atr
    sig = ema(macd, SIGL)
    return macd, sig


def waves(macd, nw=NW, minw=MINW, thr=THR):
    """Average peak / trough over the last nw COMPLETED waves, known at each bar's close."""
    n = len(macd); ap = np.full(n, np.nan); at = np.full(n, np.nan)
    peaks, troughs = [], []; wave = 0; wp = wt = None
    for i in range(1, n):
        m, m1 = macd[i], macd[i - 1]
        if not (np.isnan(m) or np.isnan(m1)):
            if m > 0 and m1 <= 0:
                if wave == -1 and wt is not None:
                    troughs.append(wt); troughs = troughs[-nw:]
                wave, wp = 1, m
            elif m < 0 and m1 >= 0:
                if wave == 1 and wp is not None:
                    peaks.append(wp); peaks = peaks[-nw:]
                wave, wt = -1, m
            elif wave == 1:
                wp = max(wp, m)
            elif wave == -1:
                wt = min(wt, m)
        if len(peaks) >= minw and len(troughs) >= minw:
            ap[i] = sum(peaks) / len(peaks) * thr; at[i] = sum(troughs) / len(troughs) * thr
    return ap, at


def crosses(macd, sig):
    up = np.zeros(len(macd), bool); dn = np.zeros(len(macd), bool)
    ok = ~(np.isnan(macd) | np.isnan(sig))
    up[1:] = ok[1:] & ok[:-1] & (macd[1:] > sig[1:]) & (macd[:-1] <= sig[:-1])
    dn[1:] = ok[1:] & ok[:-1] & (macd[1:] < sig[1:]) & (macd[:-1] >= sig[:-1])
    return up, dn


# ------------------------------------------------------------------ trades
def net_bp(side, entry, exit_):
    comm = COMM / (entry * MULT) * 1e4
    if side > 0:
        return ((exit_ - TICK) / (entry + TICK) - 1) * 1e4 - comm
    return -((exit_ + TICK) / (entry - TICK) - 1) * 1e4 - comm


def simulate(sess, mode, thr=THR, last_entry="15:30"):
    """mode 'FF' or 'PLAIN'. One trade at a time; entry at the next bar's open; exit at the
    open after the next opposite cross, or the session's last bar close."""
    idx = []; O = []; H = []; L = []; Cc = []
    for s, (d, lab, o, h, l, c) in enumerate(sess):
        for j in range(len(lab)):
            idx.append((s, j)); O.append(o[j]); H.append(h[j]); L.append(l[j]); Cc.append(c[j])
    O, H, L, Cc = map(np.array, (O, H, L, Cc))
    macd, sig = indicator(H, L, Cc)
    ap, at = waves(macd, thr=thr)
    up, dn = crosses(macd, sig)
    trades = []; pos = 0; entry = None
    N = len(idx); i = 0
    while i < N:
        s, j = idx[i]; d, lab = sess[s][0], sess[s][1]
        last = j == len(lab) - 1
        if pos != 0:
            opp = dn[i] if pos > 0 else up[i]
            if opp and not last:
                trades.append(dict(entry, exit_i=i + 1, exit_px=O[i + 1], how="cross")); pos = 0
            elif last:
                trades.append(dict(entry, exit_i=i, exit_px=Cc[i], how="close")); pos = 0
            i += 1; continue                     # signals on a bar spent in a trade are ignored
        if mode == "FF":
            sl = up[i] and not np.isnan(at[i]) and macd[i] < at[i]
            ss = dn[i] and not np.isnan(ap[i]) and macd[i] > ap[i]
        else:
            sl, ss = bool(up[i]), bool(dn[i])
        if (sl or ss) and not last and lab[j + 1] <= last_entry and T0 <= d <= T1:
            side = 1 if sl else -1
            entry = dict(date=d, s=s, j=j + 1, side=side, entry_px=O[i + 1], entry_i=i + 1)
            pos = side                           # the entry bar is processed next (its cross counts)
        i += 1
    for t in trades:
        t["gross"] = t["side"] * (t["exit_px"] / t["entry_px"] - 1) * 1e4
        t["net"] = net_bp(t["side"], t["entry_px"], t["exit_px"])
        t["bars"] = t["exit_i"] - t["entry_i"] + (1 if t["how"] == "close" else 0)
    return trades, idx, O, Cc


def partners(trades, sess, idx, O, Cc, rng):
    """For each trade: NPART same-clock, same-side, same-length trades on other sessions within +-WIN."""
    pos_of = {k: n for n, k in enumerate(idx)}
    in_sample = [s for s, x in enumerate(sess) if T0 <= x[0] <= T1]
    lo_s, hi_s = in_sample[0], in_sample[-1]
    out = []
    for t in trades:
        s, j = t["s"], t["j"]
        k_exit = t["exit_i"] - t["entry_i"]
        cand = [x for x in range(max(lo_s, s - WIN), min(hi_s, s + WIN) + 1) if x != s]
        rng.shuffle(cand)
        nets = []
        for x in cand:
            labx = sess[x][1]
            if j >= len(labx):
                continue
            n0 = pos_of[(x, j)]
            if t["how"] == "close":
                px = Cc[pos_of[(x, len(labx) - 1)]]
            else:
                je = j + k_exit
                px = Cc[pos_of[(x, len(labx) - 1)]] if je >= len(labx) else O[pos_of[(x, je)]]
            nets.append(net_bp(t["side"], O[n0], px))
            if len(nets) == NPART:
                break
        out.append(np.mean(nets) if nets else np.nan)
    return np.array(out)


# ------------------------------------------------------------------ statistics
def cl_mean(vals, dates):
    v = np.asarray(vals, float); ok = np.isfinite(v); v = v[ok]; ds = np.asarray(dates)[ok]
    n = len(v)
    if n < 3:
        return float("nan"), float("nan"), n
    m = v.mean(); g = {}
    for x, d in zip(v - m, ds):
        g[d] = g.get(d, 0.0) + x
    se = math.sqrt(sum(s * s for s in g.values())) / n
    return float(m), float(m / se) if se > 0 else float("nan"), n


def welch(a, b):
    a, b = np.asarray(a), np.asarray(b)
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return float(a.mean() - b.mean()), float((a.mean() - b.mean()) / se)


def pf(v):
    v = np.asarray(v); w = v[v > 0].sum(); l = -v[v <= 0].sum()
    return float(w / l) if l > 0 else float("inf")


def describe(tr):
    v = np.array([t["net"] for t in tr])
    if len(v) == 0:
        return dict(n=0)
    return dict(n=len(v), mean=float(v.mean()), pf=pf(v), win=float((v > 0).mean()),
                avg_w=float(v[v > 0].mean()) if (v > 0).any() else float("nan"),
                avg_l=float(v[v <= 0].mean()) if (v <= 0).any() else float("nan"),
                bars=float(np.mean([t["bars"] for t in tr])),
                close_share=float(np.mean([t["how"] == "close" for t in tr])))


# ------------------------------------------------------------------ run
def run():
    check_pin()
    buf = io.StringIO()
    def say(s=""):
        print(s); print(s, file=buf)
    sess = sessions("NQ", 15)
    say(f"FLOWS-16 MACDFF  prereg {PIN[:16]}  NQ 15m RTH sessions {len(sess)} ({sess[0][0]}..{sess[-1][0]})")
    ff, idx, O, Cc = simulate(sess, "FF")
    pl, _, _, _ = simulate(sess, "PLAIN")
    d_ff = [t["date"] for t in ff]
    m, t, n = cl_mean([x["net"] for x in ff], d_ff)
    say(f"  FF trades {n}  (long {sum(1 for x in ff if x['side'] > 0)}, short {sum(1 for x in ff if x['side'] < 0)}); PLAIN trades {len(pl)}")
    say(f"\n  G1 FF mean net {m:+.2f} bp/trade  t {t:+.2f}  (gross {np.mean([x['gross'] for x in ff]):+.2f})")
    eras = []
    for a, b in ERAS:
        x = [q for q in ff if a <= q["date"].year <= b]
        e = cl_mean([q["net"] for q in x], [q["date"] for q in x]); eras.append(e)
        say(f"  {a}-{b}: {e[0]:+.2f} bp (t {e[1]:+.2f}, n {e[2]})")
    diff3, t3 = welch([x["net"] for x in ff], [x["net"] for x in pl])
    say(f"  G3 FF - PLAIN: {diff3:+.2f} bp (Welch t {t3:+.2f}); PLAIN mean {np.mean([x['net'] for x in pl]):+.2f}")
    rng = np.random.default_rng(SEED)
    pm = partners(ff, sess, idx, O, Cc, rng)
    dd = np.array([x["net"] for x in ff]) - pm
    m4, t4, n4 = cl_mean(dd, d_ff)
    say(f"  G4 FF - random partners: {m4:+.2f} bp (t {t4:+.2f}); partner mean {np.nanmean(pm):+.2f}")
    G = {"G1": m > 0 and t >= 2.0,
         "G2": all(e[0] > 0 for e in eras) and eras[2][0] >= 0.5 * m,
         "G3": diff3 > 0 and t3 >= 1.65,
         "G4": m4 > 0 and t4 >= 2.0,
         "G5": n >= 300}
    p = {k: 0.5 * math.erfc(v / math.sqrt(2)) for k, v in (("G1", t), ("G3", t3), ("G4", t4))}
    q = C.bh(p)
    if not G["G5"]:
        verdict = "VOID (G5: fewer than 300 FF trades)"
    else:
        kill = [k for k, g in (("K1", "G1"), ("K2", "G2"), ("K3", "G4")) if not G[g]]
        verdict = ("DEAD " + ",".join(kill)) if kill else ("PASS" if G["G3"] else "EDGE IS PLAIN MACD'S (G3 fails)")
    say("\n  " + "  ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in G.items())
        + "   BH q " + " ".join(f"{k} {v:.3f}" for k, v in q.items()))
    say(f"  VERDICT: {verdict}")
    say("\n  secondary (descriptive):")
    sec = {}
    for lab, tr in (("FF", ff), ("FF long", [x for x in ff if x["side"] > 0]), ("FF short", [x for x in ff if x["side"] < 0]),
                    ("PLAIN", pl)):
        dsc = describe(tr); sec[lab] = dsc
        if dsc["n"]:
            say(f"    {lab:9s} n {dsc['n']:5d}  mean {dsc['mean']:+6.2f}  PF {dsc['pf']:.3f}  win {dsc['win']*100:4.1f}%  "
                f"avg win {dsc['avg_w']:+6.1f}  avg loss {dsc['avg_l']:+6.1f}  bars {dsc['bars']:.1f}  16:00 exits {dsc['close_share']*100:.0f}%")
    ff15, _, _, _ = simulate(sess, "FF", thr=1.5)
    d15 = describe(ff15); sec["FF thr 1.5"] = d15
    if d15["n"]:
        say(f"    FF thr 1.5 (reported only): n {d15['n']}  mean {d15['mean']:+.2f}  PF {d15['pf']:.3f}")
    for root, mins in (("NQ", 5), ("ES", 15)):
        s2 = sessions(root, mins)
        f2, _, _, _ = simulate(s2, "FF")
        p2, _, _, _ = simulate(s2, "PLAIN")
        a, b = describe(f2), describe(p2); sec[f"{root} {mins}m FF"] = a; sec[f"{root} {mins}m PLAIN"] = b
        mm, tt, _ = cl_mean([x["net"] for x in f2], [x["date"] for x in f2])
        say(f"    {root} {mins}m: FF n {a['n']} mean {mm:+.2f} (t {tt:+.2f}) PF {a['pf']:.3f}; PLAIN n {b['n']} mean {b['mean']:+.2f} PF {b['pf']:.3f}")
    with open(TRD, "w") as f:
        f.write("date,side,entry_px,exit_px,how,bars,gross,net,partner_mean\n")
        for x, pmv in zip(ff, pm):
            f.write(f"{x['date']},{x['side']},{x['entry_px']},{x['exit_px']},{x['how']},{x['bars']},{x['gross']:.4f},{x['net']:.4f},{pmv:.4f}\n")
    open(LOG, "w").write(buf.getvalue())
    json.dump(dict(pin=PIN, G1=[m, t, n], eras=eras, G3=[diff3, t3], G4=[m4, t4, n4], gates=G, bh_q=q, verdict=verdict,
                   secondary=sec), open(RES, "w"), indent=1, default=str)
    return 0


# ------------------------------------------------------------------ self-test
def self_test():
    import pandas as pd
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    rng = np.random.default_rng(1)
    x = 100 + np.cumsum(rng.normal(0, 1, 500))
    e = ema(x, 12)
    ref = pd.Series(x).ewm(span=12, adjust=False).mean().to_numpy()
    check("EMA: SMA seed at bar n-1, then the standard recursion (converges to pandas)",
          abs(e[11] - x[:12].mean()) < 1e-12 and abs(e[-1] - ref[-1]) < 1e-6)
    r = rma(np.ones(300) * 2.0, 100)
    check("RMA of a constant is that constant; undefined before n bars", np.nanmax(np.abs(r[99:] - 2.0)) < 1e-12 and np.isnan(r[98]))
    tt = np.arange(20000)
    m = np.sin(tt / 30.0) * (1 + (tt > 2000))
    ap, at = waves(m)
    check("average peak/trough of the last 50 waves: 1 early, 2 once the window holds only new waves",
          abs(ap[1900] - 1.0) < 0.01 and abs(at[1900] + 1.0) < 0.01 and abs(ap[19990] - 2.0) < 0.01 and 1.0 < ap[3990] < 2.0)
    check("nothing before 10 completed waves of each sign", np.isnan(ap[:int(30 * np.pi * 2 * 9)]).all())
    mac = np.array([0, 1, 2, 1, 0.5, 2.0]); sg = np.array([1, 0.5, 1.5, 1.5, 1.0, 1.0])
    up, dn = crosses(mac, sg)
    check("Pine crossover / crossunder", list(np.where(up)[0]) == [1, 5] and list(np.where(dn)[0]) == [3])
    check("costs: a flat price loses two ticks plus commission, both sides",
          net_bp(1, 20000.0, 20000.0) < 0 and net_bp(-1, 20000.0, 20000.0) < 0
          and abs(net_bp(1, 20000.0, 20000.0) - (((20000 - TICK) / (20000 + TICK) - 1) * 1e4 - COMM / (20000 * MULT) * 1e4)) < 1e-12)
    cc = 100 + np.cumsum(rng.normal(0, 1, 3000)); hh = cc + 0.5; ll = cc - 0.5
    m1, s1 = indicator(hh, ll, cc); a1, t1 = waves(m1)
    m2, s2 = indicator(hh[:2000], ll[:2000], cc[:2000]); a2, t2 = waves(m2)
    check("no look-ahead: cutting off the future changes nothing before it",
          np.allclose(m1[:2000], m2, equal_nan=True) and np.allclose(a1[:2000], a2, equal_nan=True))
    # a toy session series: a long signal enters next open and exits at the session close
    labs = [f"{(570 + 15 * k) // 60:02d}:{(570 + 15 * k) % 60:02d}" for k in range(26)]
    sess = []
    base = 100.0
    for dd in range(400):
        c = base + np.cumsum(rng.normal(0, 0.3, 26)); base = c[-1]
        sess.append((dt.date(2013, 1, 2) + dt.timedelta(days=dd), labs, c - 0.05, c + 0.2, c - 0.2, c))
    tr, idx, O, Cc = simulate(sess, "PLAIN")
    good = all(t["entry_i"] > 0 and t["exit_i"] >= t["entry_i"] for t in tr) and \
        all(sess[idx[t["entry_i"]][0]][0] == t["date"] for t in tr) and \
        all(idx[t["exit_i"]][0] == idx[t["entry_i"]][0] for t in tr)
    check(f"trades enter on the next bar and exit inside the same session ({len(tr)} toy trades)", good and len(tr) > 100)
    check("no entry after 15:30", all(sess[t["s"]][1][t["j"]] <= "15:30" for t in tr))
    pm = partners(tr[:20], sess, idx, O, Cc, np.random.default_rng(SEED))
    check("20 partners found for each toy trade", np.isfinite(pm).all())
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--self-test", action="store_true"); g.add_argument("--run", action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else run())
