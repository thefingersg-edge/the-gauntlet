"""Budgets for PREREGISTRATIONS v44-v49 -- event counts and squared returns only.
No signed return, no split by condition, is computed here."""
import csv, datetime as dt, math, statistics as st, numpy as np
from zoneinfo import ZoneInfo
from reactive import load
import noise_v38 as N

def tf(y, m):
    d = dt.date(y, m, 15); return d + dt.timedelta(days=(4 - d.weekday()) % 7)

def rms(x): return math.sqrt(np.mean(np.square(x)))

out = []
spx = load("../data", "spx500usd"); ds = sorted(spx)
close = {d: spx[d]["15:55"][3] for d in ds if "15:55" in spx[d]}
cd = sorted(close)
# v44: weekly (Mon open-ish -> Fri close) returns: use Friday-to-Friday closes
fr = [d for d in cd if d.weekday() == 4]
wk = [(fr[i], (close[fr[i]] / close[fr[i-1]] - 1) * 1e4) for i in range(1, len(fr))]
opex = {tf(y, m) for y in range(2005, 2027) for m in range(1, 13)}
post = [w for d, w in wk if d - dt.timedelta(days=7) in opex and d >= dt.date(2011, 5, 9)]
allw = [w for d, w in wk if d >= dt.date(2011, 5, 9)]
out.append(f"v44 OPEX: {len(post)} post-OPEX weeks of {len(allw)} weeks (2011-05 on); weekly RMS {rms(allw):.0f} bp -> MDE diff ~ {(2.24+.84)*rms(allw)/math.sqrt(len(post)):.0f} bp")
# v45: quarterly third Fridays
q = [tf(y, m) for y in range(2005, 2027) for m in (3, 6, 9, 12) if tf(y, m) in close]
lh = []
for d in q:
    b = spx[d]
    if "15:00" in b and "15:55" in b: lh.append((b["15:55"][3] / b["15:00"][0] - 1) * 1e4)
out.append(f"v45 rebalance: {len(q)} quarterly Fridays with SPX data (2005-2026); last-hour RMS {rms(lh):.0f} bp -> ~{len(q)} events x3 indices, correlated")
# v46: turn of month, 5-day window from close(-2) to close(+3)
dd = [(cd[i], (close[cd[i]] / close[cd[i-1]] - 1) * 1e4) for i in range(1, len(cd))]
nm = len({(d.year, d.month) for d, _ in dd})
r5 = rms([r for _, r in dd]) * math.sqrt(5)
out.append(f"v46 turn of month: {nm} months (SPX 2005-2026); 5-day RMS ~{r5:.0f} bp -> MDE ~ {(2.0+.84)*r5/math.sqrt(nm):.0f} bp per window")
# v47: gold PM fix window 14:45->15:15 London, 15m
L = ZoneInfo("Europe/London"); win = []
b = {}; a = {}
for fn, dst in (("../data/v24/xauusd_bid_15m.csv", b), ("../data/v24/xauusd_ask_15m.csv", a)):
    for r in csv.reader(open(fn)):
        if r[0] == "time": continue
        dst[r[0]] = (float(r[1]), float(r[4]))
bars = {}
for k, v in b.items():
    if k not in a: continue
    t = dt.datetime.fromisoformat(k).replace(tzinfo=dt.timezone.utc).astimezone(L)
    bars[(t.date(), t.strftime("%H:%M"))] = ((v[0] + a[k][0]) / 2, (v[1] + a[k][1]) / 2)
days = sorted({d for d, _ in bars})
for d in days:
    if (d, "14:45") in bars and (d, "15:00") in bars:
        win.append((d, (bars[(d, "15:00")][1] / bars[(d, "14:45")][0] - 1) * 1e4))
pre = [w for d, w in win if d < dt.date(2015, 3, 20)]; pos = [w for d, w in win if d >= dt.date(2015, 3, 20)]
out.append(f"v47 gold PM fix: {len(pre)} pre-reform, {len(pos)} post-reform days; window RMS {rms([w for _, w in win]):.1f} bp -> post MDE ~ {(2.24+.84)*rms(pos)/math.sqrt(len(pos)):.2f} bp")
# v48: gold seasonality -- 2 events/yr x 20 years, 15-trading-day windows
gd = sorted({d for d, h in bars if h == "15:00"}); gc = [bars[(d, "15:00")][1] for d in gd]
g1 = np.diff(np.log(gc)) * 1e4
out.append(f"v48 gold seasonality: ~40 events (CNY + Diwali, 2006-2026); 15-day RMS ~{rms(g1)*math.sqrt(15):.0f} bp -> MDE ~ {(2.0+.84)*rms(g1)*math.sqrt(15)/math.sqrt(40):.0f} bp per window")
# v49: UK100 first hour
uk = N.load("../data/v38", "uk100gbp")
fh = [(uk[d]["08:55"][3] / uk[d]["08:00"][0] - 1) * 1e4 for d in uk if "08:00" in uk[d] and "08:55" in uk[d] and d >= dt.date(2013, 1, 1)]
out.append(f"v49 UK100 first hour: {len(fh)} days 2013-2026; RMS {rms(fh):.1f} bp -> MDE on a conditional trade (top fifth, ~{len(fh)//5} days) ~ {(2.24+.84)*rms(fh)/math.sqrt(len(fh)/5):.1f} bp")
print("\n".join(out))
