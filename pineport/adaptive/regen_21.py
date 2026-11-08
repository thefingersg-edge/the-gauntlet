#!/usr/bin/env python3
"""Regenerate BOTH geometric families on all 21 markets, from current data.

Two problems forced this:
  1. b1_shapes used core.MARKETS (11 markets); b2_reversals used all_markets()
     (21). So three of episode 1's seven shapes never ran on rates or softs,
     while the script claimed all seven did.
  2. Neither b1_events.csv nor b2_events.csv reproduces from the bars now on
     disk -- only ~66-69% of stored forward returns still match. The price
     history has been re-pulled since those files were written, so the figures
     in the episode come from a snapshot that no longer exists.

Writes *_events_21.csv and leaves the originals alone. Detectors are used
unchanged at their default parameters; the only thing that differs is the
market list and the vintage of the bars.
"""
import os, sys
import numpy as np, pandas as pd

os.chdir(os.path.expanduser("~/mnt/Claude/pineport/adaptive")); sys.path.insert(0, ".")
import core
import b1_shapes, b2_reversals

FWD = 21
MARKETS = sorted(f[:-7] for f in os.listdir("data") if f.endswith("_d1.csv"))
ERAS = {n: (pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC"))
        for n, (a, b) in core.ERAS.items()}

def run(mod, label):
    out = []
    for m in MARKETS:
        df = core.load(m)
        e = mod.detect(df)
        if not len(e): continue
        e["market"] = m
        e["era"] = [next((n for n, (a, b) in ERAS.items() if a <= d <= b), None)
                    for d in e.date]
        out.append(e)
    E = pd.concat(out, ignore_index=True)
    E["norm"] = E.fwd.abs() / (E.vol * np.sqrt(FWD))
    print(f"{label}: {len(E)} detections over {E.market.nunique()} markets", flush=True)
    return E

b1 = run(b1_shapes, "converging trendlines"); b1.to_csv("b1_events_21.csv", index=False)
b2 = run(b2_reversals, "level reversals");    b2.to_csv("b2_events_21.csv", index=False)

# one baseline now, because both families cover the same 21 markets
rows = []
for m in MARKETS:
    c = core.load(m)["close"]
    rows.append((c.shift(-FWD) / c - 1.0).dropna())
B = pd.concat(rows)
UP, MEAN = 100 * float((B > 0).mean()), 100 * float(B.mean())
print(f"\nbaseline over {len(B):,} market-days: P(up)={UP:.1f}%  mean={MEAN:+.3f}%\n")

E = pd.concat([b1.assign(fam="converging trendlines"),
               b2.assign(fam="level reversals")], ignore_index=True).dropna(subset=["fwd"])
E["signed"] = E.fwd * E.prior; E["hit"] = E.signed > 0

hdr = f"{'shape':<22}{'dir':>6}{'n':>7}{'hit':>8}{'base':>8}{'edge':>8}{'z':>7}{'mean21':>9}"
print(hdr); print("-" * len(hdr))
out = []
for kind, g in E.groupby("kind"):
    for d, gg in g.groupby("prior"):
        if d == 0 or len(gg) < 30: continue
        base = UP if d > 0 else 100 - UP
        hit = 100 * float(gg.hit.mean())
        se = 100 * np.sqrt((base/100)*(1-base/100)/len(gg))
        out.append(dict(kind=kind, d=int(d), n=len(gg), hit=hit, base=base,
                        z=(hit-base)/se, mean=100*float(gg.signed.mean())))
        print(f"{kind:<22}{'long' if d>0 else 'short':>6}{len(gg):>7}{hit:>7.1f}%"
              f"{base:>7.1f}%{hit-base:>+7.1f}{(hit-base)/se:>+7.2f}"
              f"{100*float(gg.signed.mean()):>+8.3f}%")
O = pd.DataFrame(out); w = O.n / O.n.sum()
edge = float(((O.hit-O.base)*w).sum()); se_all = 100*np.sqrt(0.25/O.n.sum())
print("-"*len(hdr))
print(f"{'ALL':<22}{'':>6}{int(O.n.sum()):>7}{float((O.hit*w).sum()):>7.1f}%"
      f"{float((O.base*w).sum()):>7.1f}%{edge:>+7.1f}{edge/se_all:>+7.2f}"
      f"{float((O['mean']*w).sum()):>+8.3f}%")
import math
thr = abs(__import__('statistics').NormalDist().inv_cdf(1-0.025/len(O)))
print(f"\n|z|>2: {int((O.z.abs()>2).sum())} of {len(O)}   "
      f"Bonferroni threshold |z|>{thr:.2f}: {int((O.z.abs()>thr).sum())} survive")
print("\nFOR THE NARRATION")
print(f"  converging trendlines : {len(b1)} detections")
print(f"  level reversals       : {len(b2)} detections")
print(f"  TOTAL                 : {len(b1)+len(b2)} detections, {len(MARKETS)} markets")
for k, g in E.groupby("kind"):
    print(f"    {k:<22}{len(g):>6}  hit {100*g.hit.mean():.1f}%  mean {100*g.signed.mean():+.3f}%")
