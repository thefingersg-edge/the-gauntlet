#!/usr/bin/env python3
"""
leads_posthoc.py -- POST-HOC, DESCRIPTIVE diagnostics of the two leads found
in FLOWS-4 and FLOWS-6. Gates nothing. Uses ONLY data up to 2026-08-31 (the
registered sample); nothing after that date is read into any statistic, so
2026-09-01 onward stays clean for the forward pre-registrations.

  Lead A  (FLOWS-4) non-FOMC announcement days pay on LOW-VIX days
  Lead B  (FLOWS-6) natgas falls on EIA report days (Thursdays)
"""
from __future__ import annotations
import io, os, sys
import numpy as np
import pandas as pd
import common as C
import announce as A
import natgas as N

LOG = os.path.join(C.FDATA, "leads_posthoc_run.log")
buf = io.StringIO()
def say(*a):
    print(*a); print(*a, file=buf)
bp = lambda x: f"{x*1e4:+.2f}"

def mt(x):
    m, t, n = C.mean_t(x); return f"{bp(m)} bp t {t:+.2f} n {n}"

# ---------------------------------------------------------------- lead A
ev, vix = A.load_events(), A.load_vix()
say("LEAD A -- announcement days on LOW-VIX evenings (post-hoc)")
res = {}
for inst in ("SPX500_USD", "NAS100_USD", "US30_USD", "DE30_EUR"):
    dly, ba = A.day_table(inst)
    df = A.design(dly, ev, vix)
    df = df[df.index <= C.END]
    P = A.primary(df)
    f = A._fit(df, ["A", "HIGH", "FOMC"])
    say(f"  {inst:10s} low-VIX b1 {bp(P['low'])} (t {P['low_t']:+.2f})  high {bp(P['theta'])} (t {P['theta_t']:+.2f})  "
        f"b3 {bp(P['b3'])} (t {P['b3_t']:+.2f})  unconditional A {bp(f['A']['b'])} (t {f['A']['t']:+.2f})")
    res[inst] = (dly, df)
dly, df = res["SPX500_USD"]
say("\n  SPX500 detail")
lo = df[(df["A"] == 1) & (df["HIGH"] == 0)]
ctl = df[(df["A"] == 0) & (df["FOMC"] == 0) & (df["HIGH"] == 0)]
say(f"    low-VIX A days raw {mt(lo['r'])};  low-VIX control days {mt(ctl['r'])}")
s = lo["r"].sort_values()
say(f"    drop the 10 best A days: {mt(s.iloc[:-10])};  drop 10 best and 10 worst: {mt(s.iloc[10:-10])}")
for k in A.TYPES:
    x = df[(df[k] == 1) & (df["FOMC"] == 0) & (df["HIGH"] == 0)]["r"]
    say(f"    {k:4s} low-VIX {mt(x)}")
# VIX terciles of the ratio VIX/median (known before t)
med = vix.rolling(252, min_periods=252).median()
ratio = (vix / med)
pos = ratio.index.searchsorted(df.index, side="left") - 1
df = df.assign(ratio=ratio.to_numpy()[pos])
q = df["ratio"].quantile([1/3, 2/3]).to_numpy()
df["terc"] = np.where(df["ratio"] <= q[0], "low", np.where(df["ratio"] <= q[1], "mid", "high"))
for tname in ("low", "mid", "high"):
    a = df[(df["terc"] == tname) & (df["A"] == 1)]["r"]; c = df[(df["terc"] == tname) & (df["A"] == 0) & (df["FOMC"] == 0)]["r"]
    say(f"    VIX/median tercile {tname:4s}: A {mt(a)}   minus control {bp(a.mean() - c.mean())}")
net = A.trade(dly, lo.index)["net"]
for e, a_, b_ in C.ERAS:
    x = net[(net.index >= a_) & (net.index <= b_)]
    say(f"    trade net (ask in, bid out) {e}: {mt(x)}")
say(f"    trade net, all: {mt(net)}  ~ {len(net)/21.66:.0f} trades a year")

# ---------------------------------------------------------------- lead B
say("\nLEAD B -- natgas on EIA Thursdays (post-hoc)")
keep, rep = N.load_calendar()
ba = C.load_bidask("NATGAS_USD")
ba = ba[ba.index < (pd.Timestamp(C.END.date(), tz=C.NY) + pd.Timedelta(hours=17)).tz_convert("UTC")]
td = C.trading_date(ba.index)
ny = ba.index.tz_convert(C.NY)
hm = ny.hour * 60 + ny.minute
seg = pd.cut(hm, [-1, 7*60+59, 10*60+29, 10*60+59, 14*60+29, 16*60+59, 24*60],
             labels=["00-08", "08-10:30", "10:30-11", "11-14:30", "14:30-17", "18-24"])
lr = np.log(ba["close_m"]).diff()
same = pd.Series(td, index=ba.index) == pd.Series(td, index=ba.index).shift(1)
lr = lr.where(same.to_numpy())                                  # within the trading date only
prof = pd.DataFrame({"lr": lr, "seg": seg, "td": td}).dropna()
prof = prof[prof["td"] >= pd.Timestamp("2005-02-01")]
wk = prof["td"] - pd.to_timedelta(prof["td"].dt.dayofweek, unit="D")
prof = prof[wk.isin(list(keep))]
prof["thu"] = prof["td"].isin(list(rep))
g = prof.groupby(["td", "seg", "thu"], observed=True)["lr"].sum().reset_index()
tab = g.groupby(["seg", "thu"], observed=True)["lr"].mean().unstack() * 1e4
say("  mean log return by ET clock segment (bp), report Thursdays vs other days:")
for s_, row in tab.iterrows():
    say(f"    {s_:9s}  Thu {row.get(True, np.nan):+7.2f}   other {row.get(False, np.nan):+7.2f}")
dly = C.daily(ba, 1); dly = dly[(dly["nbars"] >= 40) & (dly.index >= "2005-02-01")]
r = dly["close_m"] / dly["open_m"] - 1
# Thanksgiving weeks: excluded from the test; EIA normally publishes on the Wednesday
tg = [N.pd.Timestamp(d) for d in []]
thx = []
for y in range(2005, 2026):
    d = pd.Timestamp(y, 11, 1); d += pd.Timedelta(days=(3 - d.dayofweek) % 7); d += pd.Timedelta(weeks=3)
    thx.append(d)
wed_tg = r.reindex([d - pd.Timedelta(days=1) for d in thx]).dropna()
wed_other = r[(r.index.dayofweek == 2)]
say(f"  Thanksgiving-week Wednesdays (release usually moved there): {mt(wed_tg)}  vs all Wednesdays {bp(wed_other.mean())}")
rr = r[r.index.isin(list(rep))]
for lab, months in (("Nov-Mar (withdrawal)", (11, 12, 1, 2, 3)), ("Apr-Oct (injection)", (4, 5, 6, 7, 8, 9, 10))):
    x = rr[rr.index.month.isin(months)]; o = r[~r.index.isin(list(rep)) & r.index.month.isin(months)]
    say(f"  {lab}: report days {mt(x)}  excess {bp(x.mean() - o.mean())}")
open(LOG, "w").write(buf.getvalue())
