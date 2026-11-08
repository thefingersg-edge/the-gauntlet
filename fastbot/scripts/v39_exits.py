#!/usr/bin/env python3
"""v39 CHECK 2 (descriptive, post-hoc, gates nothing) -- do tighter exits turn
the forest's direction signal into money, or just reshuffle wins and losses?
Entries: the frozen v39 FOREST's out-of-sample predictions, 2013-2026, long at
or above last year's 90th percentile, short at or below the 10th, one trade at
a time (same selection as v39). Each entry is then exited several ways.
Control: every decision point traded BOTH ways (no signal) under each exit --
the exit's own effect, which the signal must beat.
Barrier/stop fills at the level; a bar touching target and stop counts as the
stop; net = gross - the entry bar's quoted spread (as in v37/v39)."""
import numpy as np, math
from reactive import load
from timeline_v37 import simulate, cl_t

z = np.load("../data/timeline_v37/matrix.npz"); d, hms, bbp = z["date"], z["hm"], z["b_bp"]
spread = z["spread"]; pred = np.load("../data/v39/forest_oos_pred.npy")
days = load("../data", "spx500usd")
H = 24
paths = np.full((len(d), H, 3), np.nan, np.float32)   # (hi, lo, close) relative to entry, bp
for i, (dd, h) in enumerate(zip(d, hms)):
    import datetime as dt
    bars = days.get(dt.date.fromisoformat(dd))
    if not bars:
        continue
    ks = sorted(bars); j = ks.index(h)
    after = [bars[k] for k in ks[j + 1: j + 1 + H]]
    if len(after) < H:
        continue
    e = after[0][0]
    paths[i] = [((b[1] / e - 1) * 1e4, (b[2] / e - 1) * 1e4, (b[3] / e - 1) * 1e4) for b in after]

EXITS = {"TP 0.25σ": (0.25, 1.0, None), "TP 0.50σ": (0.50, 1.0, None), "TP 0.75σ": (0.75, 1.0, None),
         "TP 1.00σ (v37)": (1.00, 1.0, None), "TP 1.00σ + lock b/e at 0.5σ": (1.00, 1.0, 0.5),
         "no target, stop 1σ, 2h": (None, 1.0, None)}


def exit_pnl(p, b, side, tp, sl, lock):
    """p: (H,3) path in bp from entry; returns (gross bp, outcome) outcome: +1 target, -1 stop, 0 time."""
    stop = -sl * b
    for hi, lo, c in p:
        fav, adv = (hi, lo) if side > 0 else (-lo, -hi)
        if adv <= stop:
            return stop, -1
        if tp is not None and fav >= tp * b:
            return tp * b, 1
        if lock is not None and fav >= lock * b:
            stop = max(stop, 0.0)
    return side * p[-1][2], 0


ok = np.isfinite(paths[:, 0, 0]) & np.isfinite(pred)
yrs = np.array([int(x[:4]) for x in d])
sig = np.zeros(len(d), int)
for Y in range(2013, 2027):
    prev = ok & (yrs == Y - 1); cur = ok & (yrs == Y)
    lo, hi = np.quantile(pred[prev], [0.10, 0.90])
    sig[cur] = np.where(pred[cur] >= hi, 1, np.where(pred[cur] <= lo, -1, 0))
# entries: one at a time (same blocking as v39)
entries, block, lastd = [], 0, None
for i in np.where(ok & (yrs >= 2013))[0]:
    if d[i] != lastd: block, lastd = 0, d[i]
    if block > 0: block -= 1; continue
    if sig[i] != 0: entries.append(i); block = 8
entries = np.array(entries)
ctrl = np.where(ok & (yrs >= 2013))[0]
print(f"forest entries 2013-2026: {len(entries)}   control points: {len(ctrl)} (each traded long AND short)\n")
print(f"  {'exit':<30}{'win %':>7}{'avg win':>9}{'avg loss':>10}{'gross':>8}{'NET':>8}{'t':>7}{'control net':>13}{'signal adds':>13}")
for name, (tp, sl, lock) in EXITS.items():
    g, o = zip(*[exit_pnl(paths[i], bbp[i], sig[i], tp, sl, lock) for i in entries])
    g, o = np.array(g), np.array(o); n = g - spread[entries]
    mu, t = cl_t(d[entries], n)
    cg = np.array([exit_pnl(paths[i], bbp[i], s, tp, sl, lock)[0] - spread[i] for i in ctrl for s in (1, -1)])
    win = n > 0
    print(f"  {name:<30}{win.mean() * 100:>6.1f}%{n[win].mean():>+9.2f}{n[~win].mean():>+10.2f}{g.mean():>+8.2f}{mu:>+8.2f}{t:>+7.2f}"
          f"{cg.mean():>+13.2f}{mu - cg.mean():>+13.2f}")
# the 'bouncing' question, on the v37 exit
res = [exit_pnl(paths[i], bbp[i], sig[i], 1.0, 1.0, None) for i in entries]
o = np.array([r[1] for r in res])
mfe = np.array([max((paths[i][:, 0] if sig[i] > 0 else -paths[i][:, 1]).max(), 0) / bbp[i] for i in entries])
print(f"\n  v37 exit outcomes: target {np.mean(o == 1) * 100:.1f}%   stop {np.mean(o == -1) * 100:.1f}%   timed out {np.mean(o == 0) * 100:.1f}%")
for k in (0.25, 0.5, 0.75):
    touched = mfe >= k
    print(f"    trades that were +{k:.2f}σ in profit at some point: {touched.mean() * 100:.1f}%;"
          f" of those, {np.mean(o[touched] != 1) * 100:.1f}% did NOT reach the 1σ target"
          f" ({np.mean(o[touched] == -1) * 100:.1f}% ended at the stop)")
print(f"  median barrier 1σ(2h) = {np.median(bbp[entries]):.1f} bp; median spread {np.median(spread[entries]):.2f} bp")

print("\n  by era (reported): net per trade, and median spread paid")
for name in ("TP 0.50σ", "TP 1.00σ (v37)", "no target, stop 1σ, 2h"):
    tp, sl, lock = EXITS[name]
    g = np.array([exit_pnl(paths[i], bbp[i], sig[i], tp, sl, lock)[0] for i in entries]); n = g - spread[entries]
    ey = yrs[entries]
    print(f"    {name:<24}" + "   ".join(f"{lo}-{hi}: {n[(ey >= lo) & (ey <= hi)].mean():+.2f} (spread {np.median(spread[entries][(ey >= lo) & (ey <= hi)]):.2f})"
                                          for lo, hi in ((2013, 2017), (2018, 2021), (2022, 2026))))
for name in ("TP 1.00σ (v37)", "no target, stop 1σ, 2h"):
    tp, sl, lock = EXITS[name]
    m = yrs[entries] >= 2022
    g = np.array([exit_pnl(paths[i], bbp[i], sig[i], tp, sl, lock)[0] for i in entries[m]]); n = g - spread[entries[m]]
    mu, t = cl_t(d[entries[m]], n)
    print(f"    2022-2026 {name:<24} n {m.sum()}  net {mu:+.2f}  t {t:+.2f}")
