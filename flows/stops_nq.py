#!/usr/bin/env python3
"""
stops_nq.py -- DESCRIPTIVE (not pre-registered, gates nothing; FORWARD_NQ is unchanged).
Dave's question 2026-10-11: does a stop raise the PROFIT FACTOR of v36 rule N on NQ?
Rule N exactly as momentum_v36.noise_day (verified below to reproduce it when the stop
is off), plus an optional stop checked on every 5-minute bar while a trade is open:
  trail-pts : starts D points from the entry fill, follows the best high/low, never loosens
  fixed-pts : D points from the entry fill, never moves
  trail-pct / fixed-pct : the same with D as a % of the entry price
Stop fill = the stop level, or the bar's open if it gapped through, then one tick against.
Same costs as FLOWS-15 (one tick per fill + $2.50 round trip). NQ.v.0, 2013-01..2026-08.
Within a bar the stop is tested against the best price up to the PREVIOUS bar, then the
best is updated (conservative: no same-bar high-then-low credit).
"""
from __future__ import annotations
import io, json, math, os, statistics as st, sys
import vehicle as V
import momentum_v36 as M
from nq_stop_rule import day_with_stop, run_variant, TICK, MULT, COMM   # one copy of the logic
LOG = os.path.join(V.C.FDATA, "stops_nq_run.log")
ERAS = ((2013, 2017), (2018, 2021), (2022, 2026))


def stats(trades, rows):
    tr = [t for t in trades if V.G0 <= t["date"] <= V.G1]
    nets = [t["n"] for t in tr]
    wins = [x for x in nets if x > 0]; loss = [x for x in nets if x <= 0]
    pf = sum(wins) / -sum(loss) if loss and sum(loss) < 0 else float("inf")
    by = {}
    for t in tr:
        by.setdefault(t["date"], 0.0); by[t["date"]] += t["n"]
    sess = list(by.values())
    m = st.mean(sess); tt = m / (st.stdev(sess) / math.sqrt(len(sess)))
    eras = []
    for a, b in ERAS:
        x = [t["n"] for t in tr if a <= t["date"].year <= b]
        w = sum(v for v in x if v > 0); l = -sum(v for v in x if v <= 0)
        eras.append(w / l if l else float("inf"))
    return dict(trades=len(tr), win=len(wins) / len(nets), avg_w=st.mean(wins), avg_l=st.mean(loss), pf=pf,
                sess=m, t=tt, worst=min(sess), stops=sum(1 for t in tr if t["how"] == "stop") / len(tr),
                pf_eras=eras)


def main():
    days, iid = V.prep("NQ")
    days, _ = V.drop_rolls(days, iid)
    buf = io.StringIO()
    def say(s=""):
        print(s); print(s, file=buf)
    # 1. the stop-free simulator must reproduce v36 noise_rows exactly
    _, rows0 = run_variant(days, None, None)
    ref = M.noise_rows(days, "NQ")
    same = len(rows0) == len(ref) and all(a["date"] == b["date"] and a["n"] == b["n"] and abs(a["Ng"] - b["Ng"]) < 1e-9
                                         and abs(a["Nn"] - b["Nn"]) < 1e-9 for a, b in zip(rows0, ref))
    say(f"check: stop-free simulator reproduces momentum_v36.noise_rows exactly: {same} ({len(rows0)} vs {len(ref)} sessions)")
    if not same:
        sys.exit("STOP: simulator does not match the rule")
    variants = [("none", None, None)]
    variants += [("trail-pts", None, d) for d in (25, 50, 100, 150, 200, 300, 400, 495, 600)]
    variants += [("fixed-pts", None, d) for d in (25, 50, 100, 150, 200, 300, 400, 495, 600)]
    variants += [("trail-pct", None, d) for d in (0.1, 0.25, 0.5, 1.0, 2.0)]
    variants += [("fixed-pct", None, d) for d in (0.1, 0.25, 0.5, 1.0, 2.0)]
    say("\nNQ futures, v36 rule N, 2013-01..2026-08, NET of one tick per fill + $2.50 round trip (bp)")
    say(f"{'stop':10s} {'gap':>6s} {'trades':>6s} {'win%':>5s} {'avg win':>8s} {'avg loss':>8s} {'PF':>5s}   "
        f"{'PF 13-17':>8s} {'18-21':>6s} {'22-26':>6s}   {'bp/sess':>7s} {'t':>5s} {'worst sess':>10s} {'stopped':>7s}")
    res = []
    for kind, _, D in variants:
        trades, rows = run_variant(days, None if kind == "none" else kind, D)
        s = stats(trades, rows); s.update(kind=kind, D=D); res.append(s)
        unit = "" if D is None else (f"{D:g}pt" if kind.endswith("pts") else f"{D:g}%")
        say(f"{kind:10s} {unit:>6s} {s['trades']:6d} {s['win']*100:5.1f} {s['avg_w']:+8.1f} {s['avg_l']:+8.1f} {s['pf']:5.3f}   "
            f"{s['pf_eras'][0]:8.3f} {s['pf_eras'][1]:6.3f} {s['pf_eras'][2]:6.3f}   {s['sess']:+7.2f} {s['t']:+5.2f} "
            f"{s['worst']:+10.1f} {s['stops']*100:6.1f}%")
    open(LOG, "w").write(buf.getvalue())
    json.dump(res, open(LOG.replace("_run.log", "_result.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
