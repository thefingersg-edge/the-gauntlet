#!/usr/bin/env python3
"""PAIRS1 harness (PREREGISTRATION_PAIRS1). One run.  python3 pairs1_run.py
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, math, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tf1_run import load_ohlc
import engine as E
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); END = pd.Timestamp("2026-09-26", tz="UTC")
PAIRS = (("SPX500_USD", "NAS100_USD"), ("SPX500_USD", "US30_USD"), ("NAS100_USD", "US30_USD")); ERAS = ((2005, 2012), (2013, 2019), (2020, 2026))
SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 16) for m in (0, 15, 30, 45) if (h, m) >= (9, 30)]
def sessions(inst):
    D = load_ohlc(os.path.join(FB, "data", "v24"), inst, "15m", 900)
    df = pd.DataFrame({"O": D["O"], "C": D["C"], "spr": D["spread"]}, index=D["t"]); df = df[df.index < END]
    loc = df.index.tz_convert(E.TZ); df["day"] = loc.strftime("%Y-%m-%d"); df["slot"] = loc.strftime("%H:%M")
    df = df[df["slot"].isin(SLOTS)]
    return {d: g.set_index("slot") for d, g in df.groupby("day")}
def main():
    log = os.path.join(FB, "data", "run_pairs1.log")
    if os.path.exists(log): sys.exit("already run")
    OUT = []; P = lambda s="": (print(s, flush=True), OUT.append(s))
    P("pairs1_run.py  PREREGISTRATION_PAIRS1\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    S = {i: sessions(i) for i in {x for p in PAIRS for x in p}}
    for A, B in PAIRS:
        days = sorted(d for d in S[A] if d in S[B] and len(S[A][d]) == len(SLOTS) and len(S[B][d]) == len(SLOTS))
        hist_r, hist_x, rows = [], [], []
        for d in days:
            a, b = S[A][d], S[B][d]
            ra = np.log(a["C"] / a["C"].shift(1)).dropna().to_numpy(); rb = np.log(b["C"] / b["C"].shift(1)).dropna().to_numpy()
            if len(hist_r) >= 20:
                Ra = np.concatenate([h[0] for h in hist_r[-20:]]); Rb = np.concatenate([h[1] for h in hist_r[-20:]])
                beta = float(np.dot(Ra - Ra.mean(), Rb - Rb.mean()) / np.dot(Rb - Rb.mean(), Rb - Rb.mean()))
                x = np.log(a["C"] / a["O"].iloc[0]).to_numpy() - beta * np.log(b["C"] / b["O"].iloc[0]).to_numpy()
                H = np.array([h for h in hist_x[-20:] if h is not None])
                if len(H) >= 15:
                    sd = H.std(axis=0, ddof=1)
                    for k, sl in enumerate(SLOTS):
                        if sl < "10:00" or sl > "14:45" or sd[k] <= 0: continue
                        z = x[k] / sd[k]
                        if abs(z) >= 2.0:
                            e = k + 1; sg = -math.copysign(1, z)
                            ga = a["C"].iloc[-1] / a["O"].iloc[e] - 1; gb = b["C"].iloc[-1] / b["O"].iloc[e] - 1
                            cost = (a["spr"].iloc[e] + a["spr"].iloc[-1]) / 2 + abs(beta) * (b["spr"].iloc[e] + b["spr"].iloc[-1]) / 2
                            rows.append((int(d[:4]), sg * (ga - beta * gb) - cost, sg * (ga - beta * gb), beta)); break
                hist_x.append(np.log(a["C"] / a["O"].iloc[0]).to_numpy() - beta * np.log(b["C"] / b["O"].iloc[0]).to_numpy())
            else:
                hist_x.append(None)
            hist_r.append((ra, rb))
        r = np.array([x[1] for x in rows]); y = np.array([x[0] for x in rows]); g = np.array([x[2] for x in rows])
        m = r.mean(); t = m / (r.std(ddof=1) / math.sqrt(len(r))); er = [r[(y >= lo) & (y <= hi)].mean() for lo, hi in ERAS]
        ok = m > 0 and t >= 2.4 and all(e > 0 for e in er) and len(r) >= 200
        P(f"  {A[:6]}-{B[:6]}: trades {len(r)} (of {len(days)} days); mean net {m*1e4:+.2f} bp (gross {g.mean()*1e4:+.2f}) t {t:+.2f}; eras " + " ".join(f"{e*1e4:+.2f}" for e in er) + f"; median beta {np.median([x[3] for x in rows]):.2f} -> {'PASS' if ok else 'FAIL'}")
    open(log, "w").write("\n".join(OUT) + "\n")
if __name__ == "__main__": main()
