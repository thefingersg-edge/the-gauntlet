#!/usr/bin/env python3
"""PREREGISTRATION_v45 -- index rebalancing days: last-hour pressure, next-morning reversal.

Interpretations fixed here, BEFORE the run:
 * Rebalance days = third Friday (Thursday if the Friday is not a session) of
   Mar/Jun/Sep/Dec. SPX500 and UK100: all four quarters. NAS100: December only
   (the pre-reg names the NDX December reconstitution); NAS100's Mar/Jun/Sep
   third Fridays are EXCLUDED from both rebalance and controls.
 * Control (a) = third Friday (Thu rule) of the other eight months.
   Control (b) = all other Fridays.
 * LH  US: close of 14:55 bar -> close of 15:55 bar.  UK: close of 15:25 -> close of 16:25 bar.
   NM  next session: open of first bar (US 09:30, UK 08:00) -> close of bar
   starting 55 min later (US 10:25, UK 08:55).  Mid prices.
 * UK100 from 2013-01-01 as written; US from 2005.
 * Gate: (i) NM = a + b*LH on rebalance days pooled, b<0 and t<=-2.0;
   (ii) on rebalance U control-a, NM = a + b*LH + c*R + d*R*LH, d<0 and t<=-2.0.
   SEs clustered by date. Both needed.
 * Reported: fade trade = -sign(LH)*NM - spread at NM entry (ask_o/bid_o-1).
I am not a financial adviser. This is a measurement, not a recommendation."""
import datetime as dt, hashlib, sys
import numpy as np
import reactive, noise_v38
from premarket_factor import regress, tstat

VERSION = "1.0"
DOC = ("PREREGISTRATION_v45.md", "69543678bcc92d7fc3ab4af4adeb6e94d84b72bdd03bcf1c4250f8a5426500ac")
INS = (("spx500usd", "../data", reactive.load, ("14:55", "15:55"), ("09:30", "10:25"), dt.date(2005, 1, 1), (3, 6, 9, 12)),
       ("nas100usd", "../data", reactive.load, ("14:55", "15:55"), ("09:30", "10:25"), dt.date(2005, 1, 1), (12,)),
       ("uk100gbp", "../data/v38", noise_v38.load, ("15:25", "16:25"), ("08:00", "08:55"), dt.date(2013, 1, 1), (3, 6, 9, 12)))


def third_fri(y, m):
    d = dt.date(y, m, 15); return d + dt.timedelta(days=(4 - d.weekday()) % 7)


def rows_for(ins, ddir, ld, lh, nm, start, rq):
    days = ld(ddir, ins)
    ses = sorted(d for d in days if d >= start and lh[0] in days[d] and lh[1] in days[d]
                 and nm[0] in days[d] and nm[1] in days[d])
    S = set(ses); nxt = {a: b for a, b in zip(ses, ses[1:])}
    tag = {}
    for y in range(start.year, 2027):
        for m in range(1, 13):
            f = third_fri(y, m); d = f if f in S else (f - dt.timedelta(days=1) if f - dt.timedelta(days=1) in S else None)
            if d is None: continue
            if m in rq: tag[d] = "R"
            elif m in (3, 6, 9, 12): tag[d] = "X"          # NAS100 non-December quarter: excluded
            else: tag[d] = "A"
    out = []
    for d in ses:
        if d not in nxt: continue
        g = tag.get(d, "B" if d.weekday() == 4 else None)
        if g in (None, "X"): continue
        b = days[d]; n = days[nxt[d]]
        LH = (b[lh[1]][3] / b[lh[0]][3] - 1) * 1e4
        NM = (n[nm[1]][3] / n[nm[0]][0] - 1) * 1e4
        sp = (n[nm[0]][5] / n[nm[0]][4] - 1) * 1e4
        out.append(dict(ins=ins, d=d, g=g, LH=LH, NM=NM, sp=sp))
    return out


def gate(rows, verbose=False):
    R = [r for r in rows if r["g"] == "R"]
    y = np.array([r["NM"] for r in R]); X = np.column_stack([np.ones(len(y)), [r["LH"] for r in R]])
    b, V = regress(y, X, [r["d"].isoformat() for r in R]); t1 = tstat(b, V, 1)
    RA = [r for r in rows if r["g"] in ("R", "A")]
    isr = np.array([1.0 if r["g"] == "R" else 0.0 for r in RA]); lh = np.array([r["LH"] for r in RA])
    X2 = np.column_stack([np.ones(len(RA)), lh, isr, isr * lh])
    b2, V2 = regress(np.array([r["NM"] for r in RA]), X2, [r["d"].isoformat() for r in RA]); t2 = tstat(b2, V2, 3)
    ok = b[1] < 0 and t1 <= -2.0 and b2[3] < 0 and t2 <= -2.0
    return dict(b=b[1], t=t1, d=b2[3], td=t2, ok=ok, bA=b2[1], n=len(R), nA=len(RA) - len(R))


def slope(rows):
    if len(rows) < 5: return float("nan"), float("nan")
    y = np.array([r["NM"] for r in rows]); X = np.column_stack([np.ones(len(y)), [r["LH"] for r in rows]])
    b, V = regress(y, X, [r["d"].isoformat() for r in rows]); return b[1], tstat(b, V, 1)


def main():
    if hashlib.sha256(open("../" + DOC[0], "rb").read()).hexdigest() != DOC[1]:
        sys.exit("PREREGISTRATION_v45.md changed -- refused")
    print(f"rebal_v45.py v{VERSION}   PREREGISTRATION_v45 (sha {DOC[1][:8]}… matches)\n"
          "  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    rows = []
    for spec in INS:
        r = rows_for(*spec); rows += r
        c = {k: sum(1 for x in r if x["g"] == k) for k in "RAB"}
        print(f"  {spec[0]:<9} rebalance {c['R']:3d}   control-a {c['A']:3d}   control-b {c['B']:4d}")
    # self-test
    import copy
    p = copy.deepcopy(rows)
    for r in p:
        if r["g"] == "R": r["NM"] -= 0.8 * r["LH"]
    m = copy.deepcopy(rows)
    for r in m:
        if r["g"] == "R": r["NM"] += 0.8 * r["LH"]
    st = gate(p)["ok"] and not gate(m)["ok"]
    print(f"  self-test: planted reversal -> PASS, planted continuation -> FAIL: {'OK' if st else 'BROKEN'}")
    if not st: sys.exit("self-test broken -- no verdict")
    G = gate(rows)
    print(f"\n  (i)  rebalance days pooled: NM = a + b*LH   b {G['b']:+.3f}  t {G['t']:+.2f}  (n {G['n']})")
    print(f"  (ii) rebalance minus control-a slope   d {G['d']:+.3f}  t {G['td']:+.2f}   (control-a b {G['bA']:+.3f}, n {G['nA']})")
    print(f"  PRIMARY -> {'PASS' if G['ok'] else 'FAIL'}")
    print()
    for grp, lab in (("R", "rebalance"), ("A", "control-a"), ("B", "control-b")):
        rr = [r for r in rows if r["g"] == grp]; s, t = slope(rr)
        print(f"    reported {lab:<9}: slope {s:+.3f} (t {t:+.2f})  mean LH {np.mean([r['LH'] for r in rr]):+6.1f}  |LH| {np.mean([abs(r['LH']) for r in rr]):5.1f}  mean NM {np.mean([r['NM'] for r in rr]):+6.1f}")
    for ins, *_ in INS:
        rr = [r for r in rows if r["ins"] == ins and r["g"] == "R"]; s, t = slope(rr)
        f = np.array([-np.sign(r["LH"]) * r["NM"] - r["sp"] for r in rr])
        print(f"    reported {ins:<9}: rebalance slope {s:+.3f} (t {t:+.2f})  fade net {f.mean():+6.1f} bp  (n {len(rr)})")
    rr = [r for r in rows if r["g"] == "R"]
    f = np.array([-np.sign(r["LH"]) * r["NM"] - r["sp"] for r in rr]); fg = np.array([-np.sign(r["LH"]) * r["NM"] for r in rr])
    print(f"    reported pooled fade: gross {fg.mean():+.1f} bp  net {f.mean():+.1f} bp  hit {np.mean(f > 0):.0%}")
    print(f"\n  VERDICT  PRIMARY {'PASS' if G['ok'] else 'FAIL'}")


if __name__ == "__main__":
    main()
