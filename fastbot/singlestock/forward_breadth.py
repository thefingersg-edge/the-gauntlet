#!/usr/bin/env python3
"""FORWARD_BREADTH1 recorder (paper only). After each Sharadar refresh:
    SS_DATA=<refresh root> SS_STORE=<store> python3 forward_breadth.py
Rebuilds the point-in-time S&P 500 breadth exactly as BREADTH2 (breadth2_run.build, unchanged) and appends every day
on/after 2026-10-05 whose 20-day outcome is complete. Append-only ledger data/breadth_forward.csv.
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, csv, datetime as dt
import breadth2_run as B2
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); LEDGER = os.path.join(FB, "data", "breadth_forward.csv")
START = dt.date(2026, 10, 5); COLS = ["date", "breadth", "coverage", "r20_bp", "r5_bp", "low", "recorded"]
def main():
    have = {r["date"] for r in csv.DictReader(open(LEDGER))} if os.path.exists(LEDGER) else set()
    DT, Bt, Rt, COV, R5 = B2.build(); new = []
    for d, b, r, c, r5 in zip(DT, Bt, Rt, COV, R5):
        ds = B2.todate(d)
        if ds < START or ds.isoformat() in have: continue
        new.append({"date": ds.isoformat(), "breadth": f"{b:.2f}", "coverage": f"{c:.3f}", "r20_bp": f"{r:.1f}", "r5_bp": f"{r5:.1f}",
                    "low": int(b < 20), "recorded": dt.date.today().isoformat()})
    w = csv.DictWriter(open(LEDGER, "a", newline=""), fieldnames=COLS)
    if not os.path.exists(LEDGER) or os.path.getsize(LEDGER) == 0: w.writeheader()
    for r in new: w.writerow(r)
    print(f"forward_breadth: {len(new)} new days (low-breadth {sum(r['low'] for r in new)})")
if __name__ == "__main__": main()
