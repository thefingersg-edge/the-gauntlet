import os, pickle, numpy as np, datetime as dt
import ss_lib, ss_events2 as S, batchB_engine as B, batchB_select as Sel
C = S.CACHE; band = pickle.load(open(os.path.join(C, "band.pkl"), "rb")); bench = pickle.load(open(os.path.join(C, "bench.pkl"), "rb"))
bad, good = ss_lib.delistings(ss_lib.find("actions")); ev = Sel.select()
lo = (dt.date(2005, 1, 1) - dt.date(1970, 1, 1)).days; hi = (dt.date(2023, 6, 30) - dt.date(1970, 1, 1)).days
import sys
for k in sys.argv[1:]:
    cp = os.path.join(C, f"batchB_{k}_main.pkl")
    if os.path.exists(cp): R = pickle.load(open(cp, "rb"))
    else:
        R = [r for r in B.run(ev[k], Sel.SPECS[k]["H"], band, bench, bad, good, lo, hi) if r["band"] in ("M", "S", "L" if k == "B1" else "M")]
        pickle.dump(R, open(cp, "wb"))
    x = np.array([r["x"] for r in R]); units = len({r["entry"] // Sel.SPECS[k]["unit"] for r in R})
    rms = float(np.sqrt(np.mean(x ** 2))); n = len(x)
    print(f"  {k}: events {n:,}  clusters {units:,}  {Sel.SPECS[k]['H']}-day excess RMS {rms*100:.1f}%  MDE {2.8*rms/np.sqrt(n)*100:.2f}% (event) .. {2.8*rms/np.sqrt(units)*100:.2f}% (cluster-level)  median EDGE {np.nanmedian([r['spread'] for r in R])*1e4:.0f} bp", flush=True)
