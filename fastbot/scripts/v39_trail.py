#!/usr/bin/env python3
"""v39 CHECK 3 (descriptive, post-hoc) -- "don't quit while you're ahead":
no take-profit, a stop that trails the best price and tightens as the trade
goes further in profit, held until the stop is hit or the session closes.
Same forest entries as v39_exits.py; same control (every decision point,
both ways). Trail updates only from COMPLETED bars (a bar that makes a new
high cannot also be the bar that stops you on its own low -- conservative:
the stop is checked against the bar before the trail moves). Net = gross -
entry spread; stop fills at the stop level."""
import numpy as np, datetime as dt
from reactive import load
from timeline_v37 import cl_t

z = np.load("../data/timeline_v37/matrix.npz"); d, hms, bbp, spread = z["date"], z["hm"], z["b_bp"], z["spread"]
pred = np.load("../data/v39/forest_oos_pred.npy")
days = load("../data", "spx500usd")
paths = {}
for i, (dd, h) in enumerate(zip(d, hms)):
    bars = days.get(dt.date.fromisoformat(dd))
    if not bars:
        continue
    ks = sorted(bars); j = ks.index(h)
    after = [bars[k] for k in ks[j + 1:]]            # to the 15:55 bar
    if len(after) < 24 or ks[-1] != "15:55":
        continue
    e = after[0][0]
    paths[i] = np.array([((b[1] / e - 1) * 1e4, (b[2] / e - 1) * 1e4, (b[3] / e - 1) * 1e4) for b in after], np.float32)


def run(p, b, side, rule, cap_bars=None):
    """rule(mfe_sigma) -> trail distance in sigma (None = no trail). Initial stop 1 sigma."""
    best, stop = 0.0, -1.0 * b
    for n, (hi, lo, c) in enumerate(p):
        if cap_bars and n >= cap_bars:
            return side * p[n - 1][2]
        fav, adv = (hi, lo) if side > 0 else (-lo, -hi)
        if adv <= stop:
            return stop
        best = max(best, fav)
        dist = rule(best / b)
        if dist is not None:
            stop = max(stop, best - dist * b)
    return side * p[-1][2]


RULES = {
    "fixed 2h, stop 1σ (v39 best)":           (lambda m: None, 24),
    "to close, stop 1σ, no trail":            (lambda m: None, None),
    "to close, trail 1.0σ":                   (lambda m: 1.0, None),
    "to close, trail 0.75σ":                  (lambda m: 0.75, None),
    "to close, trail 0.5σ":                   (lambda m: 0.5, None),
    "to close, tightening 1σ -> 0.3σ":        (lambda m: max(0.3, 1.0 - 0.5 * m), None),
    "to close, tightening + b/e after 0.5σ":  (lambda m: (max(0.3, 1.0 - 0.5 * m) if m < 0.5 else min(m, max(0.3, 1.0 - 0.5 * m))), None),
}

ok = np.array([i in paths for i in range(len(d))]) & np.isfinite(pred)
yrs = np.array([int(x[:4]) for x in d])
sig = np.zeros(len(d), int)
for Y in range(2013, 2027):
    prev, cur = ok & (yrs == Y - 1), ok & (yrs == Y)
    lo, hi = np.quantile(pred[prev], [0.10, 0.90])
    sig[cur] = np.where(pred[cur] >= hi, 1, np.where(pred[cur] <= lo, -1, 0))
entries, lastd = [], None
for i in np.where(ok & (yrs >= 2013))[0]:
    if d[i] == lastd:        # ONE trade per day at most: a to-the-close hold cannot overlap
        continue
    if sig[i] != 0:
        entries.append(i); lastd = d[i]
entries = np.array(entries)
rng = np.random.default_rng(5)
ctrl = rng.choice(np.where(ok & (yrs >= 2013))[0], 12000, replace=False)
print(f"forest entries (first signal each day) 2013-2026: {len(entries)}; control: 12,000 random points, both ways\n")
print(f"  {'exit':<40}{'win%':>6}{'avg win':>9}{'avg loss':>10}{'NET':>8}{'t':>7}{'22-26 NET':>11}{'t':>7}{'ctrl':>8}{'adds':>7}")
e22 = yrs[entries] >= 2022
for name, (rule, cap) in RULES.items():
    n = np.array([run(paths[i], bbp[i], sig[i], rule, cap) for i in entries]) - spread[entries]
    mu, t = cl_t(d[entries], n); m2, t2 = cl_t(d[entries][e22], n[e22])
    c = np.array([run(paths[i], bbp[i], s, rule, cap) - spread[i] for i in ctrl for s in (1, -1)])
    w = n > 0
    print(f"  {name:<40}{w.mean()*100:>5.1f}%{n[w].mean():>+9.2f}{n[~w].mean():>+10.2f}{mu:>+8.2f}{t:>+7.2f}{m2:>+11.2f}{t2:>+7.2f}{c.mean():>+8.2f}{mu - c.mean():>+7.2f}")
# how far do winners run if never cut?
mfe = np.array([max(0, (paths[i][:, 0] if sig[i] > 0 else -paths[i][:, 1]).max()) / bbp[i] for i in entries])
end = np.array([sig[i] * paths[i][-1][2] / bbp[i] for i in entries])
print(f"\n  best point reached before the close, in sigma: median {np.median(mfe):.2f}, 75th pct {np.quantile(mfe, .75):.2f}, 90th {np.quantile(mfe, .9):.2f}")
print(f"  where it stood at the close: median {np.median(end):+.2f}σ  -- average give-back from the best point {np.mean(mfe - end):.2f}σ")
