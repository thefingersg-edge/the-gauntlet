#!/usr/bin/env python3
"""PROBE1-OIL (PREREGISTRATION_UNGER_BATCH.md section 1): the frozen PROBE1 probe (scripts/probe1_run.py, imported unchanged)
on WTI and Brent, with the batch's clean-day rule (drop weekend labels and days with < 50% of median bars).
Mechanical wrapper only: same functions, same gates (Q1 |t|>=2 + every era; Q2 t>=2.50).
python3 probe1_oil.py   -> data/probe1/run_probe1_oil.log
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, hashlib
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import probe1_run as P
from struct15 import load15
BATCH = os.path.join(HERE, "..", "PREREGISTRATION_UNGER_BATCH.md")
BATCH_SHA = "ce14205ed8219efd19f5190ab53dcfdb62dbb4f8fcda5bf59a2c1eb0c91f3716"
STEMS = {"wticousd": "USD", "bcousd": "USD"}


def main():
    P.pin()
    if hashlib.sha256(open(BATCH, "rb").read()).hexdigest() != BATCH_SHA: sys.exit("batch spec changed -- refused")
    P.self_test(); os.makedirs(P.OUT, exist_ok=True)
    L = ["PROBE1-OIL -- PROBE1 (sha 1320a760…) on WTI and Brent, clean-day rule from PREREGISTRATION_UNGER_BATCH (sha ce14205e…)",
         "  I am not a financial adviser. This is a measurement, not a recommendation.", ""]
    for stem, cur in STEMS.items():
        d = load15(stem); m = d["t"] < P.END; d = {k: v[m] for k, v in d.items()}
        ny = pd.DatetimeIndex(d["t"].astype("datetime64[ns]")).tz_localize("UTC").tz_convert("America/New_York")
        lab = (ny + pd.Timedelta(hours=7)).normalize().tz_localize(None)
        cnt = pd.Series(lab).value_counts()
        good = set(cnt[(cnt >= 0.5 * cnt.median())].index); keep = np.array([(x in good) and x.weekday() < 5 for x in lab])
        ndrop = len(cnt) - sum(1 for x in good if x.weekday() < 5)
        d = {k: v[keep] for k, v in d.items()}; lab = lab[keep]
        labels, day = np.unique(lab.to_numpy(), return_inverse=True); labels = [pd.Timestamp(x) for x in labels]
        R = P.rates(cur); rate_of = lambda t: R.get(t.strftime("%Y-%m"), 0.02)
        res = {}
        for sg in (+1, -1):
            g, cst, fin, close, rev = P.probe(d["o"], d["h"], d["l"], d["c"], d["spr"], day, labels, sg, rate_of)
            pc = np.r_[np.nan, close[:-1]]; res[sg] = dict(gross=g / pc, cost=cst, fin=fin, net=g / pc - cst - fin, rev=rev)
        close = P.probe(d["o"], d["h"], d["l"], d["c"], d["spr"], day, labels, +1)[3]; pc = np.r_[np.nan, close[:-1]]
        bh = close / pc - 1 - np.array([((rate_of(x) + 0.025) * (3 if x.weekday() == 4 else 1) / 365) for x in labels])
        yr = np.array([x.year for x in labels]); ok = np.isfinite(res[1]["gross"]); G = res[1]["gross"]
        t_all = P.nw_t(G[ok]); ers = [np.nanmean(G[ok & (yr >= a) & (yr <= b)]) for a, b in P.ERAS]
        sgn = np.sign(np.nanmean(G[ok])); stable = abs(t_all) >= 2 and all(np.sign(e) == sgn for e in ers)
        char = ("TREND" if sgn > 0 else "MEAN-REVERTING") if stable else "UNSTABLE"
        L.append(f"  {stem}: {ok.sum():,} clean days ({ndrop} dropped), {res[1]['rev'].sum():,} reversals ({res[1]['rev'].sum() / ok.sum() * 252:.0f}/yr), median spread {np.median(d['spr']):.1f} bp")
        L.append(f"    Q1 gross probe: mean {np.nanmean(G[ok]) * 1e4:+.2f} bp/day (t {t_all:+.2f}, Sharpe {P.sharpe(G[ok]):+.2f});  eras "
                 + "  ".join(f"{a}-{b % 100:02d} {e * 1e4:+.2f}" for (a, b), e in zip(P.ERAS, ers)) + f"  -> character {char}")
        ins = ok & (yr <= 2015); oos = ok & (yr >= 2016)
        pick = +1 if np.nanmean(G[ins]) > 0 else -1; N = res[pick]["net"][oos]; tn = P.nw_t(N); passed = np.mean(N) > 0 and tn >= P.TQ2
        L.append(f"    Q2 chosen on 2005-15: {'TREND (probe)' if pick > 0 else 'FADE (reverse)'};  2016-26 gross {res[pick]['gross'][oos].mean() * 1e4:+.2f} bp/day, "
                 f"spread {-res[pick]['cost'][oos].mean() * 1e4:.2f}, financing {-res[pick]['fin'][oos].mean() * 1e4:+.2f} -> net {N.mean() * 1e4:+.2f} bp/day "
                 f"(t {tn:+.2f}, Sharpe {P.sharpe(N):+.2f})  -> {'PASS' if passed else 'FAIL'}")
        bo = bh[oos][np.isfinite(bh[oos])]
        L.append(f"       buy & hold 2016-26 net of financing: {np.mean(bo) * 1e4:+.2f} bp/day (Sharpe {P.sharpe(bo):+.2f})")
        L.append("       annual gross / net (probe direction): " + " ".join(f"{y}:{np.nansum(G[ok & (yr == y)]) * 100:+.0f}/{np.nansum(res[1]['net'][ok & (yr == y)]) * 100:+.0f}" for y in range(yr[ok].min(), yr[ok].max() + 1)) + "  (%)\n")
        with open(os.path.join(P.OUT, f"{stem}_daily.csv"), "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["day", "gross_probe", "net_probe", "net_reverse", "buyhold_net"])
            for i in np.flatnonzero(ok): w.writerow([labels[i].date(), f"{G[i]:.6f}", f"{res[1]['net'][i]:.6f}", f"{res[-1]['net'][i]:.6f}", f"{bh[i]:.6f}"])
    open(os.path.join(P.OUT, "run_probe1_oil.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
