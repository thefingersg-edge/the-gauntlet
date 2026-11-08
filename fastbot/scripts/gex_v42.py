#!/usr/bin/env python3
"""PREREGISTRATION_v42 -- does intraday momentum live on days when dealers are
SHORT gamma? SqueezeMetrics GEX (data/gex/DIX.csv, downloaded by Dave
2026-09-27), prior trading day's value only (GEX is end-of-day).
  H1  last-30-minute momentum (Baltussen et al.): sign(prior close -> 15:30)
      sets a 15:30 open -> 15:55 close trade.
  H2  v36 noise-band rule N, per instrument-day.
SPX500, NAS100, US30 (OANDA 5m bid/ask), 2011-05 -> 2026-08-14.
"""
import argparse, bisect, csv, datetime as dt, hashlib, math, os, sys
import numpy as np
import momentum_v36 as M
from reactive import load
from timeline_v37 import cl_t

VERSION = "1.0"
DOC = ("PREREGISTRATION_v42.md", "bd1cb691f6d73bdbc3a37c6f268e118e61ac8c4f6e79698e39286475acb0b642")
GEX_FILE, GEX_SHA = "../data/gex/DIX.csv", "b64bccce84e585634f36fbb2793adc85a41048d05f8b0fce3aeec057caaed3b6"
ERAS = ((2011, 2016), (2017, 2021), (2022, 2026))
T_GATE = 2.24


def gex_series():
    if hashlib.sha256(open(GEX_FILE, "rb").read()).hexdigest() != GEX_SHA:
        sys.exit("DIX.csv changed since it was pinned -- refused")
    s = sorted((dt.date.fromisoformat(r["date"]), float(r["gex"])) for r in csv.DictReader(open(GEX_FILE)))
    return [d for d, _ in s], [g for _, g in s]


def prior_gex(ds, gs, d):
    """GEX of the last trading day strictly before d (it is published after the close)."""
    i = bisect.bisect_left(ds, d) - 1
    if i < 0 or (d - ds[i]).days > 5:
        return None
    return gs[i]


def rows(data_dir):
    ds, gs = gex_series()
    out = []
    for ins in M.INSTR:
        days = load(data_dir, ins)
        keys = sorted(days)
        n = {r["date"]: r for r in M.noise_rows(days, ins)}
        for i in range(1, len(keys)):
            d, bars, prev = keys[i], days[keys[i]], days[keys[i - 1]]
            if d < dt.date(2011, 5, 3):
                continue
            g = prior_gex(ds, gs, d)
            if g is None:
                continue
            r = dict(ins=ins, date=d, neg=g < 0, gex=g)
            if all(k in bars for k in ("15:30", "15:55")) and "15:55" in prev:
                rod = bars["15:30"][0] / prev["15:55"][3] - 1
                if rod != 0:
                    s = 1 if rod > 0 else -1
                    r["h1g"] = M.gross_open_to_close(bars["15:30"], bars["15:55"], s)
                    r["h1n"] = M.net_open_to_close(bars["15:30"], bars["15:55"], s)
            if d in n:
                r["h2g"], r["h2n"] = n[d]["Ng"], n[d]["Nn"]
            out.append(r)
    return out


def test(R, key):
    sel = [r for r in R if key in r]
    d = np.array([r["date"].isoformat() for r in sel]); x = np.array([r[key] for r in sel]); neg = np.array([r["neg"] for r in sel])
    X = np.column_stack([np.ones(len(x)), neg.astype(float)])
    from premarket_factor import regress, tstat
    b, V = regress(x, X, d)
    mneg, tneg = cl_t(d[neg], x[neg]); mpos, tpos = cl_t(d[~neg], x[~neg])
    eras = []
    for lo, hi in ERAS:
        m = np.array([lo <= r["date"].year <= hi for r in sel])
        eras.append((x[m & neg].mean() - x[m & ~neg].mean()) if (m & neg).sum() > 10 else float("nan"))
    return dict(diff=b[1], t=tstat(b, V, 1), mneg=mneg, tneg=tneg, nneg=int(neg.sum()),
                mpos=mpos, tpos=tpos, npos=int((~neg).sum()), eras=eras)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--budget", action="store_true"); ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(); here = os.path.dirname(os.path.abspath(__file__))
    if a.self_test:
        ds = [dt.date(2020, 1, 2), dt.date(2020, 1, 3)]; gs = [-1.0, 5.0]
        ok = prior_gex(ds, gs, dt.date(2020, 1, 3)) == -1.0 and prior_gex(ds, gs, dt.date(2020, 1, 2)) is None
        print(f"  [{'PASS' if ok else 'FAIL'}] GEX is the PRIOR day's value, never the same day's (planted: same-day +5 must not be used)")
        gex_series(); print("  [PASS] DIX.csv matches its pinned sha256"); sys.exit(0 if ok else 1)
    print(f"gex_v42.py v{VERSION}   PREREGISTRATION_v42\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    if not a.budget:
        if hashlib.sha256(open(os.path.join(here, "..", DOC[0]), "rb").read()).hexdigest() != DOC[1]:
            sys.exit("PREREGISTRATION_v42.md changed since frozen -- refused")
    R = rows(os.path.join(here, "../data"))
    if a.budget:
        for key, nm in (("h1g", "H1 last-30"), ("h2g", "H2 noise-band")):
            sel = [r for r in R if key in r]; neg = [r for r in sel if r["neg"]]
            rms = math.sqrt(np.mean([r[key] ** 2 for r in sel])); nd = len({r["date"] for r in neg})
            print(f"  {nm}: {len(sel)} instrument-days, negative-GEX {len(neg)} on {nd} dates; RMS {rms:.1f} bp;"
                  f" MDE for the neg-vs-pos difference ~ {(T_GATE + .84) * rms * math.sqrt(1 / nd + 1 / len({r['date'] for r in sel})):.1f} bp")
        return
    for key, nm in (("h1", "H1 last-30-minute momentum"), ("h2", "H2 noise-band N (per instrument-day)")):
        g = test(R, key + "g"); n = test(R, key + "n")
        ok = g["diff"] > 0 and g["t"] >= T_GATE and g["mneg"] > 0 and sum(e > 0 for e in g["eras"] if e == e) >= 2
        print(f"\n  {nm}  (gross)")
        print(f"    negative GEX: {g['mneg']:+.2f} bp (t {g['tneg']:+.2f}, n {g['nneg']})   positive GEX: {g['mpos']:+.2f} (t {g['tpos']:+.2f}, n {g['npos']})")
        print(f"    difference {g['diff']:+.2f} bp  t {g['t']:+.2f}   eras (neg - pos): " + "  ".join(f"{e:+.2f}" for e in g["eras"])
              + f"   -> {'PASS' if ok else 'FAIL'}")
        print(f"    (reported) NET on negative-GEX days {n['mneg']:+.2f} bp (t {n['tneg']:+.2f})")


if __name__ == "__main__":
    main()
