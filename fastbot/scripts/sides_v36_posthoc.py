#!/usr/bin/env python3
"""POST-HOC, DESCRIPTIVE ONLY -- v36 rule N split into longs and shorts.
Asked after the v36 result was seen, so it tests nothing and gates nothing.
Each trade also gets a DRIFT CONTROL: the average mid return of the same
clock window over all sessions of the same year (what just being long in
that window earned, with no signal)."""
import datetime as dt, statistics as st
import momentum_v36 as M
from reactive import load, hm, net_open_to_close, gross_open_to_close

def trades_for(bars, prev_close, sig):
    op = bars["09:30"][0]; ur, dr = max(op, prev_close), min(op, prev_close)
    side, ent, t_in, out = 0, None, None, []
    def close_at(b, t_out, s):
        out.append((s, t_in, t_out, gross_open_to_close(ent, b, s), net_open_to_close(ent, b, s)))
    for k in M.CHECKS:
        nxt = hm(k, 1)
        if k not in bars or nxt not in bars or sig.get(k) is None:
            continue
        c = bars[k][3]; U, L = ur*(1+sig[k]), dr*(1-sig[k]); vw = M.session_vwap(bars, k)
        if side == 1 and c < max(U, vw):
            close_at(M._as_close(bars[nxt]), nxt, 1); side = 0
        elif side == -1 and c > min(L, vw):
            close_at(M._as_close(bars[nxt]), nxt, -1); side = 0
        if side == 0:
            if c > U: side, ent, t_in = 1, bars[nxt], nxt
            elif c < L: side, ent, t_in = -1, bars[nxt], nxt
    if side:
        close_at(bars["15:55"], "16:00", side)
    return out

rows = []
for ins in M.INSTR:
    days = load("../data", ins); ds = sorted(days); hist = []
    # per-year mean 5m mid return by slot (open->next open; last bar open->close)
    slot_ret = {}
    for d in ds:
        b = days[d]; ks = sorted(b)
        for i, k in enumerate(ks):
            nx = ks[i+1] if i+1 < len(ks) else None
            r = (b[nx][0]/b[k][0]-1)*1e4 if nx else (b[k][3]/b[k][0]-1)*1e4
            slot_ret.setdefault((d.year, k), []).append(r)
    mean_slot = {k: st.mean(v) for k, v in slot_ret.items()}
    for i in range(1, len(ds)):
        d, bars, prev = ds[i], days[ds[i]], days[ds[i-1]]
        mv = {k: abs(bars[k][3]/bars["09:30"][0]-1) for k in M.CHECKS if k in bars} if "09:30" in bars else {}
        if len(hist) >= M.LOOKBACK and "15:55" in prev and "09:30" in bars and "15:55" in bars:
            sig = {}
            for k in M.CHECKS:
                xs = [h[k] for h in hist[-M.LOOKBACK:] if k in h]
                sig[k] = st.mean(xs) if len(xs) >= 10 else None
            for s, tin, tout, g, n in trades_for(bars, prev["15:55"][3], sig):
                # drift: sum of mean slot returns from entry bar up to (not incl.) exit bar
                ctrl = sum(v for (y, k), v in mean_slot.items() if y == d.year and tin <= k < tout) \
                       if tout != "16:00" else sum(v for (y, k), v in mean_slot.items() if y == d.year and k >= tin)
                rows.append(dict(ins=ins, date=d, side=s, g=g, n=n, ctrl=s*ctrl))
        if mv: hist.append(mv)

def show(label, rs):
    import math
    if len(rs) < 30: print(f"  {label:<34} n {len(rs)}"); return
    from premarket_factor import regress, tstat
    def cl(key):
        b, V = regress([r[key] for r in rs], [[1.0]]*len(rs), [r["date"] for r in rs]); return b[0], tstat(b, V, 0)
    g, n, c = cl("g"), cl("n"), cl("ctrl")
    ex = [dict(date=r["date"], x=r["g"]-r["ctrl"]) for r in rs]
    from premarket_factor import regress as R2
    b, V = R2([r["x"] for r in ex], [[1.0]]*len(ex), [r["date"] for r in ex])
    print(f"  {label:<34} n {len(rs):>5}  gross {g[0]:+6.2f} (t {g[1]:+5.2f})  net {n[0]:+6.2f} (t {n[1]:+5.2f})"
          f"  drift {c[0]:+6.2f}  gross-minus-drift {b[0]:+6.2f} (t {tstat(b, V, 0):+5.2f})")

for era, lo, hi in (("2005-12", 2005, 2012), ("2013-26", 2013, 2026), ("2022-26", 2022, 2026)):
    print(f"\n{era}  (per TRADE, bp; t clustered by date)")
    for sd, nm in ((1, "LONGS"), (-1, "SHORTS")):
        base = [r for r in rows if r["side"] == sd and lo <= r["date"].year <= hi and r["date"] <= dt.date(2026, 9, 17)]
        show(nm + " all three", base)
        for ins in M.INSTR:
            show(f"   {nm.lower()} {ins}", [r for r in base if r["ins"] == ins])
print("\nlong-only by holdout era, all three, net:")
for lo, hi in M.ERAS:
    show(f"  longs {lo}-{hi}", [r for r in rows if r["side"] == 1 and lo <= r["date"].year <= hi])
